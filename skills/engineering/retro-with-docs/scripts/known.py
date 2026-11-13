#!/usr/bin/env python3
"""List the friction already recorded under ~/.skill-docs/retros/, one line each.

Usage: known.py [<term> ...] [--root <dir>]
Without terms, prints the open and rejected friction. With terms, prints every open, rejected
or skipped friction whose title, target or proposal contains any of them (case-insensitive).
Each line: <ref> | <status> | <category> | <title>
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from retro_file import ROOT, collect, is_skipped  # noqa: E402

TITLE_MAX = 140


def known(root, terms):
    terms = [t.lower() for t in terms]
    lines = []
    for f in collect(root):
        if terms:
            haystack = " ".join(f.get(k, "") for k in ("title", "target", "proposal")).lower()
            if not any(t in haystack for t in terms):
                continue
        elif is_skipped(f):
            continue
        title = f["title"] if len(f["title"]) <= TITLE_MAX else f["title"][:TITLE_MAX - 1] + "…"
        status = f.get("status", "").split(" (")[0]
        lines.append(f"{f['ref']} | {status} | {f.get('category', '-')} | {title}")
    return lines


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("terms", nargs="*")
    parser.add_argument("--root", default=str(ROOT))
    args = parser.parse_args(argv)
    print("\n".join(known(args.root, args.terms)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
