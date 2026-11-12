#!/usr/bin/env python3
"""Collect the repo facts megamoind's step 0 and gates need, as one JSON object.

Usage: preflight.py [--base <ref> [--head <branch>]] [--repo <dir>]

Keys: default_branch, gitbutler, gh_version, gh_attach_ok, codeowners, package_manager,
dev_doctor, steering (files and their sections), required_checks (of --base, else of the
default branch; null with required_checks_error when a lookup failed), and with --base, touched_packages: each package.json directory the
<base>...<head> diff touches, with the gate scripts it defines. Under GitButler HEAD merges
every applied branch, so pass your branch as --head.
"""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import ci  # noqa: E402

GH_ATTACH_MIN = (2, 99)
LOCKFILES = [("yarn.lock", "yarn"), ("pnpm-lock.yaml", "pnpm"), ("bun.lockb", "bun"), ("bun.lock", "bun"),
             ("package-lock.json", "npm")]
CODEOWNERS = [".github/CODEOWNERS", "CODEOWNERS", "docs/CODEOWNERS"]
STEERING = ["CLAUDE.md", "CLAUDE.local.md", "AGENTS.md"]
GATE_WORDS = {"ci", "lint", "test", "tests", "e2e", "type", "types", "typecheck", "tsc", "check"}
# A gate only reads the code: these words mark scripts that write files or touch the outside world.
WRITE_WORDS = {"fix", "write", "watch", "dev", "deploy", "release", "publish", "migrate", "migration", "seed", "push",
               "update"}


def is_gate(script):
    words = set(re.split(r"[:\-_.]", script.lower()))
    return bool(words & GATE_WORDS) and not words & WRITE_WORDS


def run(cmd, cwd):
    try:
        result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    except FileNotFoundError:
        return 127, ""
    return result.returncode, result.stdout.strip()


def default_branch(repo):
    code, out = run(["git", "symbolic-ref", "--short", "refs/remotes/origin/HEAD"], repo)
    if code == 0 and out:
        return out.removeprefix("origin/")
    code, out = run(["gh", "repo", "view", "--json", "defaultBranchRef", "-q", ".defaultBranchRef.name"], repo)
    return out if code == 0 and out else None


def gh_version(repo):
    code, out = run(["gh", "--version"], repo)
    match = re.search(r"gh version (\d+)\.(\d+)\.(\d+)", out)
    return tuple(int(x) for x in match.groups()) if match else None


def package_manager(root):
    return next((pm for lock, pm in LOCKFILES if (root / lock).exists()), None)


def scripts_of(package_dir):
    try:
        data = json.loads((package_dir / "package.json").read_text())
    except (OSError, ValueError):
        return {}
    return data.get("scripts") or {}


def sections(path):
    return [line[3:].strip() for line in path.read_text(errors="replace").splitlines() if line.startswith("## ")]


def touched_packages(root, base, head):
    code, out = run(["git", "diff", "--name-only", "--no-renames", "-z", f"{base}...{head}"], root)
    if code != 0:
        return None
    packages = {}
    for file in filter(None, out.split("\0")):
        directory = (root / file).parent
        while directory != root and not (directory / "package.json").exists():
            directory = directory.parent
        if (directory / "package.json").exists():
            packages[str(directory.relative_to(root)) or "."] = directory
    if (root / "package.json").exists():
        packages.setdefault(".", root)
    return {
        name: {k: v for k, v in scripts_of(path).items() if is_gate(k)}
        for name, path in sorted(packages.items())
    }


def collect(root, base=None, head="HEAD"):
    root = Path(root).resolve()
    code, toplevel = run(["git", "rev-parse", "--show-toplevel"], root)
    if code == 0:
        root = Path(toplevel)
    branch = default_branch(root)
    version = gh_version(root)
    facts = {
        "default_branch": branch,
        "gitbutler": run(["but", "status"], root)[0] == 0,
        "gh_version": ".".join(map(str, version)) if version else None,
        "gh_attach_ok": bool(version and version[:2] >= GH_ATTACH_MIN),
        "codeowners": next((p for p in CODEOWNERS if (root / p).exists()), None),
        "package_manager": package_manager(root),
        "dev_doctor": "dev:doctor" in scripts_of(root),
        "steering": {p: sections(root / p) for p in STEERING if (root / p).exists()},
    }
    try:
        facts["required_checks"] = ci.required(base or branch, cwd=root) if (base or branch) else []
    except RuntimeError as error:
        facts["required_checks"] = None
        facts["required_checks_error"] = str(error)
    if base:
        facts["touched_packages"] = touched_packages(root, base, head)
    return facts


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--base")
    parser.add_argument("--head", default="HEAD")
    parser.add_argument("--repo", default=".")
    args = parser.parse_args(argv)
    print(json.dumps(collect(args.repo, args.base, args.head), indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
