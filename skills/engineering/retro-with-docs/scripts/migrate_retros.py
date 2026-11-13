#!/usr/bin/env python3
"""Convert retro files from the pre-friction format, where noise was one `Dismissed as noise:` line.

Usage: migrate_retros.py [--root <dir>] [--file <project>/<file>.md] [--write] [--diff]
Dry run by default: prints what each file would change and the problems left after it.
--write applies it. Files already carrying `migrated:` are left alone, so a rerun is a no-op.

Per file: adds `migrated: <today>`, gives every finding `expected`, `cost` and `cause` set to
`unrecorded`, turns each dismissed item into a `skipped` finding, rewrites the stray
`resolved (…)` status to `applied (…)`, and orders findings by severity, skipped last.
Ids never change, so every ref stays valid.
"""
import argparse
import datetime
import difflib
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from retro_file import FINDING, ROOT, SEVERITIES, UNRECORDED, parse, problems  # noqa: E402

DISMISSED = "Dismissed as noise:"
LEADING_INDEXES = re.compile(r"^((?:\[[^\]]*\][\s/,\-–]*(?:and\s+)?)+)")
SKIPPED_STATUS = "skipped (dismissed as noise in the pre-friction format)"


def dismissed_items(text):
    items = []
    for part in re.split(r";\s+", text.strip()):
        items += [p.strip() for p in re.split(r"(?<=\.)\s+(?=\[)", part) if p.strip()]
    out = []
    for item in items:
        lead = LEADING_INDEXES.match(item)
        evidence = re.sub(r"[\s/,\-–]+$", "", lead.group(1)).strip() if lead else UNRECORDED
        title = (item[lead.end():] if lead else item).strip().rstrip(".") or item.rstrip(".")
        out.append((title, evidence))
    return out


def migrate(text, today):
    meta, _, findings = parse(text)
    if meta.get("migrated") or not text.startswith("---\n"):
        return text
    head_end = text.find("\n---\n", 4)
    frontmatter, body = text[:head_end], text[head_end + 5:]
    lines = body.splitlines()

    dismissed = None
    for i, line in enumerate(lines):
        if line.startswith(DISMISSED):
            dismissed = line[len(DISMISSED):].strip()
            del lines[i]
            break

    starts = [i for i, line in enumerate(lines) if line.startswith("## ")]
    preamble = lines[:starts[0]] if starts else lines
    blocks = [lines[a:b] for a, b in zip(starts, starts[1:] + [len(lines)])]

    severity = {f["id"]: f.get("severity") for f in findings if f["id"]}
    ids = []
    for block in blocks:
        header = FINDING.match(block[0])
        ids.append(header.group(1) if header else None)
        for j, line in enumerate(block):
            if line.startswith("- status: resolved ("):
                block[j] = line.replace("- status: resolved (", "- status: applied (", 1)
        if header and not any(l.startswith("- cause:") for l in block):
            at = next((j for j, l in enumerate(block) if l.startswith("- proposal:")), None)
            if at is None:
                at = len(block)
                while at > 1 and not block[at - 1].strip():
                    at -= 1
            block[at:at] = [f"- expected: {UNRECORDED}", f"- cost: {UNRECORDED}", f"- cause: {UNRECORDED}"]

    def rank(pair):
        finding_id, _ = pair
        level = severity.get(finding_id)
        return SEVERITIES.index(level) if level in SEVERITIES else len(SEVERITIES)

    ordered = [block for _, block in sorted(zip(ids, blocks), key=rank)]

    numbers = [int(re.match(r"R(\d+)", i).group(1)) for i in ids if i]
    next_id = max(numbers, default=0) + 1
    for title, evidence in dismissed_items(dismissed or ""):
        ordered.append([f"## R{next_id}: {title}", "", f"- status: {SKIPPED_STATUS}", f"- evidence: {evidence}"])
        next_id += 1

    out = [*preamble]
    while out and not out[-1].strip():
        out.pop()
    for block in ordered:
        while block and not block[-1].strip():
            block = block[:-1]
        out += ["", *block]
    return f"{frontmatter}\nmigrated: {today}\n---\n\n" + "\n".join(out).lstrip("\n") + "\n"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", default=str(ROOT))
    parser.add_argument("--file")
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--diff", action="store_true")
    args = parser.parse_args(argv)
    root = Path(args.root)
    paths = [root / args.file] if args.file else sorted(root.glob("*/*.md"))
    today = datetime.date.today().isoformat()
    changed = 0
    for path in paths:
        before = path.read_text()
        after = migrate(before, today)
        rel = path.relative_to(root)
        if after == before:
            print(f"{rel}: unchanged")
            continue
        changed += 1
        skipped = after.count(f"- status: {SKIPPED_STATUS}")
        print(f"{rel}: {skipped} skipped findings from the dismissed line")
        for problem in problems(after):
            print(f"{rel}: still a problem: {problem}")
        if args.diff:
            sys.stdout.writelines(difflib.unified_diff(
                before.splitlines(keepends=True), after.splitlines(keepends=True), str(rel), str(rel)))
        if args.write:
            path.write_text(after)
    print(f"{changed} of {len(paths)} files {'migrated' if args.write else 'would change (dry run)'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
