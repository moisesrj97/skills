#!/usr/bin/env python3
"""Read and update the retro files retro-with-docs writes under ~/.skill-docs/retros/.

Usage:
  retros.py collect [--all] [--root <dir>]
      Prints a JSON list of findings, each with ref (<project>/<file>#R<n>), date, its fields
      and weight (blocker 4, high 3, medium 2, low 1). Without --all, only open and rejected ones.
  retros.py set <ref> <status> [--root <dir>]
  retros.py set --from <file.json> [--root <dir>]       {"<ref>": "<status>", ...}
      Rewrites each finding's `- status:` line. A status is `applied (<where>)`,
      `rejected (<reason>)`, `duplicate of <ref>` or `open`; anything else is refused.
"""
import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path.home() / ".skill-docs" / "retros"
WEIGHT = {"blocker": 4, "high": 3, "medium": 2, "low": 1}
STATUS = re.compile(r"^(open|applied \(.+\)|rejected \(.+\)|duplicate of [^/\s]+/[^#\s]+\.md#R\d+[a-z]?)$")
FINDING = re.compile(r"^## (R\d+[a-z]?): (.+)$")
FIELD = re.compile(r"^- ([a-z-]+):\s*(.*)$")
REF = re.compile(r"^([^/]+)/([^#]+\.md)#(R\d+[a-z]?)$")


def frontmatter(text):
    meta = {}
    if text.startswith("---\n"):
        end = text.find("\n---\n", 4)
        for line in text[4:end if end >= 0 else 0].splitlines():
            key, sep, value = line.partition(":")
            if sep:
                meta[key.strip()] = value.strip()
    return meta


def findings_of(text):
    findings, current, last = [], None, None
    for line in text.splitlines():
        header = FINDING.match(line)
        if header:
            current = {"id": header.group(1), "title": header.group(2)}
            findings.append(current)
            last = None
            continue
        field = FIELD.match(line)
        if current is not None and field and field.group(1) not in current:
            last = field.group(1)
            current[last] = field.group(2).strip()
        elif current is not None and last and line[:1].isspace() and line.strip():
            current[last] = f"{current[last]} {line.strip()}".strip()
        elif not line.strip() or not line[:1].isspace():
            last = None
    return findings


def collect(root, everything=False):
    out = []
    for path in sorted(Path(root).glob("*/*.md")):
        text = path.read_text(errors="replace")
        meta = frontmatter(text)
        for finding in findings_of(text):
            status = finding.get("status", "")
            if not everything and not (status == "open" or status.startswith("rejected")):
                continue
            out.append({
                "ref": f"{path.parent.name}/{path.name}#{finding['id']}",
                "date": meta.get("date"),
                **finding,
                "weight": WEIGHT.get(finding.get("severity"), 0),
            })
    return out


def set_status(root, ref, status):
    match = REF.match(ref)
    if not match:
        raise ValueError(f"{ref}: not a <project>/<file>#R<n> ref")
    if not STATUS.match(status):
        raise ValueError(f"{ref}: status {status!r} is not open, applied (…), rejected (…) or duplicate of <ref>")
    project, file, finding_id = match.groups()
    path = Path(root) / project / file
    if not path.exists():
        raise ValueError(f"{ref}: no file {path}")
    lines = path.read_text().splitlines(keepends=True)
    inside = False
    for i, line in enumerate(lines):
        header = FINDING.match(line.rstrip("\n"))
        if header:
            inside = header.group(1) == finding_id
        elif inside and line.startswith("- status:"):
            end = i + 1
            while end < len(lines) and lines[end][:1].isspace() and lines[end].strip():
                end += 1
            lines[i:end] = [f"- status: {status}\n"]
            path.write_text("".join(lines))
            return
    raise ValueError(f"{ref}: no `- status:` line under ## {finding_id}")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    c = sub.add_parser("collect")
    c.add_argument("--all", action="store_true")
    c.add_argument("--root", default=str(ROOT))
    s = sub.add_parser("set")
    s.add_argument("ref", nargs="?")
    s.add_argument("status", nargs="?")
    s.add_argument("--from", dest="from_file")
    s.add_argument("--root", default=str(ROOT))
    args = parser.parse_args(argv)

    if args.command == "collect":
        print(json.dumps(collect(args.root, args.all), indent=2, ensure_ascii=False))
        return 0
    if args.from_file:
        updates = json.loads(Path(args.from_file).read_text())
    elif args.ref and args.status:
        updates = {args.ref: args.status}
    else:
        parser.error("set needs <ref> <status> or --from <file.json>")
    failed = False
    for ref, status in updates.items():
        try:
            set_status(args.root, ref, status)
            print(f"{ref}: {status}")
        except ValueError as error:
            print(error, file=sys.stderr)
            failed = True
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
