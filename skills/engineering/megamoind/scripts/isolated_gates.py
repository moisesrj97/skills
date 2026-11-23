#!/usr/bin/env python3
"""Run gates on one branch alone, in a throwaway worktree, so other applied branches can't leak in.

Usage: isolated_gates.py <branch> --gate '<cmd>' [--gate '<cmd>']... [--base <ref>] [--dir <parent>] [--keep]

Checks <branch> out detached in a new directory (under --dir, default the system temp dir), installs
dependencies offline from the package manager's cache, builds every workspace package the touched
packages depend on (dependencies first, from the copy, so they never resolve to the shared checkout's
builds), copies the shared checkout's untracked .env* files, runs each gate from the copy's root, and
removes the worktree unless --keep. Touched packages come from the <base>...<branch> diff (--base
defaults to the default branch).

Exit 0: every gate passed. 1: a gate failed (each gate's exit code is printed). 2: setup failed.
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import preflight  # noqa: E402

SKIP_DIRS = {"node_modules", ".git", ".yarn", "build", "dist"}


class SetupError(Exception):
    pass


def sh(cmd, cwd, env=None, shell=False):
    result = subprocess.run(cmd, cwd=cwd, env=env, shell=shell, capture_output=True, text=True)
    if result.returncode != 0:
        shown = cmd if isinstance(cmd, str) else " ".join(cmd)
        raise SetupError(f"{shown} exited {result.returncode}\n{result.stdout[-2000:]}{result.stderr[-2000:]}")
    return result.stdout


def install_command(root):
    pm = preflight.package_manager(root)
    if pm == "yarn":
        if (root / ".yarnrc.yml").exists():
            return ["yarn", "install", "--immutable"], {"YARN_ENABLE_NETWORK": "0"}
        return ["yarn", "install", "--offline", "--frozen-lockfile"], {}
    return {
        "pnpm": (["pnpm", "install", "--offline", "--frozen-lockfile"], {}),
        "npm": (["npm", "ci", "--offline"], {}),
        "bun": (["bun", "install", "--frozen-lockfile"], {}),
    }.get(pm, (None, {}))


def workspace_packages(root):
    packages = {}
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not d.startswith(".")]
        if "package.json" in filenames:
            try:
                data = json.loads((Path(dirpath) / "package.json").read_text())
            except ValueError:
                continue
            if data.get("name"):
                packages[data["name"]] = {"dir": Path(dirpath), "data": data}
    return packages


def build_order(packages, touched_dirs):
    """Workspace dependencies of the touched packages, transitively, dependencies first."""
    def deps(name):
        data = packages[name]["data"]
        names = {**data.get("dependencies", {}), **data.get("devDependencies", {}), **data.get("peerDependencies", {})}
        return sorted(n for n in names if n in packages)

    touched = [n for n, p in packages.items() if p["dir"].resolve() in {d.resolve() for d in touched_dirs}]
    order, visiting, done = [], set(), set()

    def visit(name):
        if name in done or name in visiting:
            return
        visiting.add(name)
        for dep in deps(name):
            visit(dep)
        visiting.discard(name)
        done.add(name)
        order.append(name)

    for name in sorted(touched):
        for dep in deps(name):
            visit(dep)
    return order


def env_files(root):
    out = sh(["git", "ls-files", "--others", "--ignored", "--exclude-standard", "--directory", "-z"], root)
    return [f for f in filter(None, out.split("\0")) if not f.endswith("/") and Path(f).name.startswith(".env")]


def prepare(root, copy, branch, base):
    sh(["git", "worktree", "add", "--detach", str(copy), branch], root)
    for file in env_files(root):
        (copy / file).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(root / file, copy / file)
    cmd, extra_env = install_command(copy)
    if cmd:
        print(f"install: {' '.join(cmd)}", file=sys.stderr)
        sh(cmd, copy, env={**os.environ, **extra_env})
    touched = preflight.touched_packages(copy, base, "HEAD") or {}
    pm = preflight.package_manager(copy) or "npm"
    packages = workspace_packages(copy)
    for name in build_order(packages, [copy / d for d in touched]):
        if "build" in (packages[name]["data"].get("scripts") or {}):
            print(f"build: {name}", file=sys.stderr)
            sh([pm, "run", "build"], packages[name]["dir"])


def run_gates(copy, gates):
    results = []
    for gate in gates:
        print(f"gate: {gate}", file=sys.stderr)
        code = subprocess.run(gate, cwd=copy, shell=True).returncode
        results.append((gate, code))
    return results


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("branch")
    parser.add_argument("--gate", action="append", required=True, help="one shell command; repeat the flag")
    parser.add_argument("--base")
    parser.add_argument("--dir")
    parser.add_argument("--keep", action="store_true")
    parser.add_argument("--repo", default=".")
    args = parser.parse_args(argv)

    root = Path(sh(["git", "rev-parse", "--show-toplevel"], args.repo).strip())
    base = args.base or f"origin/{preflight.default_branch(root)}"
    copy = Path(tempfile.mkdtemp(prefix=f"gates-{args.branch.replace('/', '-')}-", dir=args.dir)) / "repo"
    try:
        prepare(root, copy, args.branch, base)
        results = run_gates(copy, args.gate)
    except SetupError as error:
        print(f"setup failed: {error}", file=sys.stderr)
        return 2
    finally:
        if args.keep:
            print(f"kept: {copy}", file=sys.stderr)
        else:
            subprocess.run(["git", "worktree", "remove", "--force", str(copy)], cwd=root, capture_output=True)
            shutil.rmtree(copy.parent, ignore_errors=True)
    for gate, code in results:
        print(f"{'PASS' if code == 0 else 'FAIL'} ({code}): {gate}")
    return 0 if all(code == 0 for _, code in results) else 1


if __name__ == "__main__":
    sys.exit(main())
