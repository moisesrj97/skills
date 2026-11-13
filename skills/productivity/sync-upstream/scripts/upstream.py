#!/usr/bin/env python3
"""Check the skills recorded in upstream.json against their upstream repos."""
import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
MANIFEST = "upstream.json"
COMPARE_FILE_CAP = 300


def gh(*args):
    return json.loads(subprocess.run(["gh", "api", *args], check=True, capture_output=True).stdout)


def load_manifest(root):
    return json.loads((root / MANIFEST).read_text())


def save_manifest(root, manifest):
    (root / MANIFEST).write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")


def under(path, filename):
    return bool(filename) and filename.startswith(path.rstrip("/") + "/")


def touched_files(entry, files):
    return [f for f in files if under(entry["path"], f["filename"]) or under(entry["path"], f.get("previous_filename"))]


def classify(entry, files):
    skill_md = entry["path"].rstrip("/") + "/SKILL.md"
    for f in files:
        if f.get("previous_filename") == skill_md and f["status"] == "renamed":
            return "moved", f["filename"].rsplit("/", 1)[0]
        if f["filename"] == skill_md and f["status"] == "removed":
            return "removed", None
    return "changed", None


def check(root=ROOT):
    manifest = load_manifest(root)
    heads, compares, report = {}, {}, []
    for name, entry in sorted(manifest["skills"].items()):
        key = (entry["repo"], entry["ref"])
        if key not in heads:
            heads[key] = gh(f"repos/{entry['repo']}/commits/{entry['ref']}")["sha"]
        head = heads[key]
        if head == entry["checked"]:
            report.append({"name": name, "status": "unchanged"})
            continue
        # The last commit touching the path tells whether anything changed since `checked` without
        # depending on the compare endpoint, which caps its file list.
        latest = gh(f"repos/{entry['repo']}/commits?sha={head}&path={entry['path']}&per_page=1")
        moved_on = latest and latest[0]["sha"] != entry["checked"] and gh(
            f"repos/{entry['repo']}/compare/{entry['checked']}...{latest[0]['sha']}")["status"] == "ahead"
        if not moved_on:
            entry["checked"] = head
            report.append({"name": name, "status": "unchanged"})
            continue
        compare_key = (entry["repo"], entry["checked"], head)
        if compare_key not in compares:
            compares[compare_key] = gh(f"repos/{entry['repo']}/compare/{entry['checked']}...{head}")
        compare = compares[compare_key]
        files = touched_files(entry, compare["files"])
        status, moved_to = classify(entry, files)
        report.append({
            "name": name, "status": status, "moved_to": moved_to, "repo": entry["repo"], "path": entry["path"],
            "checked": entry["checked"], "head": head,
            "files": [{k: f[k] for k in ("filename", "status", "previous_filename") if k in f} for f in files],
            "compare_url": compare.get("html_url"),
            "truncated": len(compare["files"]) >= COMPARE_FILE_CAP,
        })
    save_manifest(root, manifest)
    return report


def diff(name, root=ROOT):
    entry = load_manifest(root)["skills"][name]
    head = gh(f"repos/{entry['repo']}/commits/{entry['ref']}")["sha"]
    compare = gh(f"repos/{entry['repo']}/compare/{entry['checked']}...{head}")
    in_range = {c["sha"] for c in compare["commits"]}
    commits = [c for c in gh(f"repos/{entry['repo']}/commits?sha={head}&path={entry['path']}&per_page=100")
               if c["sha"] in in_range]
    lines = [f"# {name}: {entry['repo']}/{entry['path']} {entry['checked'][:7]}...{head[:7]}", "", "## Commits"]
    lines += [f"- {c['sha'][:7]} {c['commit']['message'].splitlines()[0]}" for c in commits]
    lines += ["", "## Files"]
    for f in touched_files(entry, compare["files"]):
        moved = f" (from {f['previous_filename']})" if f.get("previous_filename") else ""
        lines += ["", f"### {f['status']}: {f['filename']}{moved}"]
        patch = f.get("patch")
        lines += ["```diff", patch, "```"] if patch else [
            f"(no patch: binary or too large; read it with `gh api repos/{entry['repo']}/contents/{f['filename']}?ref={head}`)"]
    return "\n".join(lines) + "\n"


def mark(name, sha=None, path=None, drop=False, root=ROOT):
    manifest = load_manifest(root)
    if drop:
        del manifest["skills"][name]
    else:
        entry = manifest["skills"][name]
        entry["checked"] = sha or gh(f"repos/{entry['repo']}/commits/{entry['ref']}")["sha"]
        if path:
            entry["path"] = path
    save_manifest(root, manifest)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("check", help="report each skill as unchanged, changed, moved or removed upstream")
    p = sub.add_parser("diff", help="upstream commits and patches touching one skill since its checked commit")
    p.add_argument("name")
    p = sub.add_parser("mark", help="record a skill as reviewed up to a commit")
    p.add_argument("name")
    p.add_argument("--sha", help="defaults to the head of the skill's ref")
    p.add_argument("--path", help="new upstream path, for a moved skill")
    p.add_argument("--drop", action="store_true", help="stop tracking the skill's upstream")
    args = parser.parse_args(argv)
    if args.command == "check":
        print(json.dumps(check(), indent=2))
    elif args.command == "diff":
        sys.stdout.write(diff(args.name))
    else:
        mark(args.name, args.sha, args.path, args.drop)


if __name__ == "__main__":
    sys.exit(main())
