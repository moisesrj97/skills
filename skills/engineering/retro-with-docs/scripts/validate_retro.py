#!/usr/bin/env python3
"""Check a retro file against the shape retro-digest parses.

Usage: validate_retro.py <retro.md> [...]
Prints each problem as <file>: <problem>. Exit 1 when any file has one.
"""
import re
import sys
from pathlib import Path

REQUIRED_META = ["date", "project", "session", "summary"]
FIELDS = ["status", "severity", "category", "kind", "target", "evidence", "proposal"]
ENUMS = {
    "severity": ["blocker", "high", "medium", "low"],
    "category": ["flow", "skill", "verification", "navigation", "checks", "standards", "steering",
                 "tool-economy", "information-access"],
    "kind": ["mechanical", "judgement"],
}
STATUS = re.compile(r"^(open|applied \(.+\)|rejected \(.+\)|duplicate of [^/\s]+/[^#\s]+\.md#R\d+[a-z]?)$")
FINDING = re.compile(r"^## (R\d+[a-z]?): (.+)$")
FIELD = re.compile(r"^- ([a-z-]+):\s*(.*)$")
DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def parse(text):
    """Return (meta, title, findings, dismissed). Findings are dicts of their fields plus id and title."""
    meta, body = {}, text
    if text.startswith("---\n"):
        end = text.find("\n---\n", 4)
        if end >= 0:
            for line in text[4:end].splitlines():
                key, sep, value = line.partition(":")
                if sep:
                    meta[key.strip()] = value.strip()
            body = text[end + 5:]
    title = next((l[2:].strip() for l in body.splitlines() if l.startswith("# ")), None)
    findings, current, dismissed, last = [], None, None, None
    for line in body.splitlines():
        header = FINDING.match(line)
        if line.startswith("## ") and not header:
            findings.append({"id": None, "title": line})
            current = None
            continue
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
        if line.startswith("Dismissed as noise:"):
            dismissed = line.split(":", 1)[1].strip()
    return meta, title, findings, dismissed


def problems(text):
    meta, title, findings, dismissed = parse(text)
    out = []
    if not meta:
        out.append("no frontmatter between --- lines")
    for key in REQUIRED_META:
        if not meta.get(key):
            out.append(f"frontmatter: missing {key}")
    if meta.get("date") and not DATE.match(meta["date"]):
        out.append(f"frontmatter: date {meta['date']!r} is not YYYY-MM-DD")
    if not (title or "").startswith("Retro: "):
        out.append("missing the `# Retro: <topic>` heading")
    if dismissed is None:
        out.append("missing the `Dismissed as noise:` line")
    seen = set()
    for f in findings:
        if f["id"] is None:
            out.append(f"heading {f['title']!r} is not `## R<n>: <problem>`")
            continue
        where = f"{f['id']}"
        if f["id"] in seen:
            out.append(f"{where}: duplicate id")
        seen.add(f["id"])
        for key in FIELDS:
            if not f.get(key):
                out.append(f"{where}: missing `- {key}:`")
        for key, allowed in ENUMS.items():
            if f.get(key) and f[key] not in allowed:
                out.append(f"{where}: {key} {f[key]!r} is not one of {' | '.join(allowed)}")
        if f.get("status") and not STATUS.match(f["status"]):
            out.append(f"{where}: status {f['status']!r} is not open, applied (…), rejected (…) "
                       "or duplicate of <project>/<file>#R<n>")
    order = [ENUMS["severity"].index(f["severity"]) for f in findings if f.get("severity") in ENUMS["severity"]]
    if order != sorted(order):
        out.append("findings are not ordered by severity")
    return out


def main(argv=None):
    paths = (argv if argv is not None else sys.argv[1:])
    if not paths:
        print(__doc__.strip(), file=sys.stderr)
        return 2
    failed = False
    for path in paths:
        for problem in problems(Path(path).read_text()):
            print(f"{path}: {problem}")
            failed = True
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
