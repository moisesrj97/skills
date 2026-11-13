#!/usr/bin/env python3
"""Check a retro file against the shape retro-digest parses.

Usage: validate_retro.py <retro.md> [...]
Prints each problem as <file>: <problem>. Exit 1 when any file has one.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from retro_file import problems  # noqa: E402


def main(argv=None):
    paths = argv if argv is not None else sys.argv[1:]
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
