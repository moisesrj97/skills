#!/usr/bin/env python3
"""Block until every review round file is sealed with END OF ROUND.

Usage: wait_rounds.py <round file>... [--timeout <seconds>] [--interval <seconds>]

Exit 0 once every file's last line is END OF ROUND. Exit 1 at the timeout, naming the unsealed files.
"""
import argparse
import sys
import time
from pathlib import Path

from run_round import sealed


def wait(paths, timeout, interval, sleep=time.sleep, now=time.monotonic):
    """The paths still unsealed when the wait ends: empty once all are sealed."""
    deadline = now() + timeout
    while True:
        unsealed = [p for p in paths if not sealed(p)]
        if not unsealed or now() >= deadline:
            return unsealed
        sleep(interval)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("round_files", nargs="+")
    parser.add_argument("--timeout", type=float, default=1800)
    parser.add_argument("--interval", type=float, default=10)
    args = parser.parse_args(argv)

    unsealed = wait([Path(p) for p in args.round_files], args.timeout, args.interval)
    if unsealed:
        for path in unsealed:
            state = "missing" if not path.exists() else "last line is not END OF ROUND"
            print(f"unsealed after {args.timeout:g}s: {path} ({state})", file=sys.stderr)
        return 1
    print(f"sealed: {len(args.round_files)} round file(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
