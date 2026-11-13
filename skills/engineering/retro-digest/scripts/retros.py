#!/usr/bin/env python3
"""Read and update the retro files retro-with-docs writes under ~/.skill-docs/retros/.

Usage:
  retros.py collect [--all] [--skipped-days 28] [--root <dir>]
      Prints a JSON list of findings, each with ref (<project>/<file>#R<n>), date, its fields
      and weight (blocker 4, high 3, medium 2, low 1; 1 without a severity). Without --all,
      only open, rejected and skipped ones, and no skipped one older than --skipped-days:
      a one-off that has not recurred in that long is not a pattern.
  retros.py batches --out <dir> [--size 40] [--skipped-days 28] [--root <dir>]
      Splits what collect prints into <dir>/batch-<n>.json, sorted by where each change would
      land so related findings share a batch, each field clipped. Prints the batch files.
  retros.py set <ref> <status> [--root <dir>]
  retros.py set --from <file.json> [--root <dir>]       {"<ref>": "<status>", ...}
      Rewrites each finding's `- status:` line. A status is `applied (<where>)`,
      `rejected (<reason>)`, `skipped (<reason>)`, `duplicate of <ref>` or `open`; anything
      else is refused.
"""
import argparse
import datetime
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from retro_file import ROOT, collect, is_skipped, set_status  # noqa: E402

BATCH_FIELDS = ["ref", "date", "status", "severity", "category", "kind", "target", "title", "evidence",
                "cause", "proposal", "matches"]
CLIP = 300


def digestible(root, skipped_days, today=None):
    cutoff = ((today or datetime.date.today()) - datetime.timedelta(days=skipped_days)).isoformat()
    return [f for f in collect(root) if not (is_skipped(f) and (f.get("date") or "") < cutoff)]


def owner(target):
    """Where a change would land, coarsely: a skill, an app or package, else the file's name."""
    token = (target or "").split(" ")[0].strip("`,;()")
    if not token or token in ("unknown", "guess:"):
        return "~unknown"
    parts = Path(re.sub(r":\d+(-\d+)?$", "", token)).parts
    if "scripts" in parts[1:-1]:
        return parts[parts.index("scripts") - 1]
    if len(parts) > 1 and parts[-1] == "SKILL.md":
        return parts[-2]
    for marker in ("apps", "packages", "services"):
        if marker in parts[:-1]:
            return parts[parts.index(marker) + 1]
    return parts[-1].lower() if parts else "~unknown"


def batches(findings, size):
    ordered = sorted(findings, key=lambda f: (owner(f.get("target")), f.get("category", ""), f.get("date") or ""))
    clipped = [{k: (f[k] if len(str(f[k])) <= CLIP else str(f[k])[:CLIP] + "…") for k in BATCH_FIELDS if f.get(k)}
               for f in ordered]
    return [clipped[i:i + size] for i in range(0, len(clipped), size)]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    c = sub.add_parser("collect")
    c.add_argument("--all", action="store_true")
    c.add_argument("--skipped-days", type=int, default=28)
    c.add_argument("--root", default=str(ROOT))
    b = sub.add_parser("batches")
    b.add_argument("--out", required=True)
    b.add_argument("--size", type=int, default=40)
    b.add_argument("--skipped-days", type=int, default=28)
    b.add_argument("--root", default=str(ROOT))
    s = sub.add_parser("set")
    s.add_argument("ref", nargs="?")
    s.add_argument("status", nargs="?")
    s.add_argument("--from", dest="from_file")
    s.add_argument("--root", default=str(ROOT))
    args = parser.parse_args(argv)

    if args.command == "collect":
        found = collect(args.root, everything=True) if args.all else digestible(args.root, args.skipped_days)
        print(json.dumps(found, indent=2, ensure_ascii=False))
        return 0
    if args.command == "batches":
        out = Path(args.out)
        out.mkdir(parents=True, exist_ok=True)
        for i, batch in enumerate(batches(digestible(args.root, args.skipped_days), args.size), 1):
            path = out / f"batch-{i}.json"
            path.write_text(json.dumps(batch, indent=1, ensure_ascii=False))
            print(f"{path} ({len(batch)} findings)")
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
