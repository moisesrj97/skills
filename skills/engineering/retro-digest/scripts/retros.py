#!/usr/bin/env python3
"""Read and update the retro files retro-with-docs writes under ~/.skill-docs/retros/.

Usage:
  retros.py collect [--all] [--root <dir>]
      Prints a JSON list of findings, each with ref (<project>/<file>#R<n>), date, its fields
      and weight (blocker 4, high 3, medium 2, low 1; 1 without a severity). Without --all,
      only open, rejected and skipped ones.
  retros.py set <ref> <status> [--root <dir>]
  retros.py set --from <file.json> [--root <dir>]       {"<ref>": "<status>", ...}
      Rewrites each finding's `- status:` line. A status is `applied (<where>)`,
      `rejected (<reason>)`, `skipped (<reason>)`, `duplicate of <ref>` or `open`; anything
      else is refused.
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from retro_file import ROOT, collect, set_status  # noqa: E402


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
