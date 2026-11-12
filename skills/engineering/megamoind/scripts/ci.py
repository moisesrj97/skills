#!/usr/bin/env python3
"""Read a base branch's required checks, or wait for a PR's checks to settle.

Usage:
  ci.py required <base>
      Prints the required check names from the branch rulesets and the classic branch
      protection, one per line. Nothing printed means neither declares any; exit 2 when a
      lookup fails.
  ci.py wait <pr> [--required <name>]... [--skip <name>]... [--interval 30] [--timeout 3600]
      Polls `gh pr checks` until nothing is pending and every --required check has reported.
      --skip leaves checks out of the wait (e.g. ready-only ones on a draft, pending retarget).
      Exit 0: all green. 1: some check red (named on stdout). 4: timeout (pending and
      missing named). 2: gh failed 3 polls in a row. A PR with no checks at all counts as
      pending for 5 minutes, then green when nothing it requires is left to wait for.
"""
import argparse
import json
import subprocess
import sys
import time

GREEN = {"pass", "skipping"}
RED = {"fail", "cancel"}


def gh(*args, cwd=None):
    result = subprocess.run(["gh", *args], capture_output=True, text=True, cwd=cwd)
    return result.returncode, result.stdout, result.stderr


def required_from_rules(rules):
    names = []
    for rule in rules or []:
        if rule.get("type") == "required_status_checks":
            for check in rule.get("parameters", {}).get("required_status_checks", []):
                names.append(check["context"])
    return names


def required_from_protection(branch):
    checks = ((branch or {}).get("protection") or {}).get("required_status_checks") or {}
    return list(checks.get("contexts") or []) + [c["context"] for c in checks.get("checks") or []]


def required(base, cwd=None):
    """Raise RuntimeError when a lookup fails, since a partial list would let the wait pass early."""
    base = base.removeprefix("origin/")
    names = []
    for endpoint, parse, empty in (("rules/branches", required_from_rules, "[]"),
                                   ("branches", required_from_protection, "{}")):
        code, out, err = gh("api", f"repos/{{owner}}/{{repo}}/{endpoint}/{base}", cwd=cwd)
        if code != 0:
            raise RuntimeError(f"{endpoint}/{base}: {err.strip() or f'gh exited {code}'}")
        names += parse(json.loads(out or empty))
    return list(dict.fromkeys(names))


def evaluate(checks, required_names=(), skip=(), settled=False):
    """Return (state, details): state is green, red or pending.

    No checks at all is pending until `settled` (the grace period passed): right after a push GitHub
    has registered none yet, while a repo without CI never will.
    """
    considered = [c for c in checks if c["name"] not in skip]
    red = [c for c in considered if c["bucket"] in RED]
    pending = [c for c in considered if c["bucket"] not in GREEN | RED]
    reported = {c["name"] for c in considered}
    if not checks:
        waiting_for = [n for n in required_names if n not in skip]
        if not waiting_for and settled:
            return "green", {"red": [], "pending": [], "missing": []}
        return "pending", {"red": [], "pending": [{"name": "(no checks reported yet)"}], "missing": waiting_for}
    missing = [n for n in required_names if n not in reported and n not in skip]
    if pending or missing:
        return "pending", {"red": red, "pending": pending, "missing": missing}
    if red:
        return "red", {"red": red, "pending": [], "missing": []}
    return "green", {"red": [], "pending": [], "missing": []}


def fetch_checks(pr):
    code, out, err = gh("pr", "checks", str(pr), "--json", "name,bucket,state,link")
    if out.strip().startswith("["):
        return json.loads(out)
    if "no checks reported" in err:
        return []
    raise RuntimeError(err.strip() or f"gh pr checks exited {code}")


def wait(pr, required_names, skip, interval, timeout, fetch=fetch_checks, sleep=time.sleep, now=time.monotonic,
         max_errors=3, grace=300):
    start = now()
    deadline = start + timeout
    errors = 0
    while True:
        try:
            checks = fetch(pr)
            errors = 0
        except RuntimeError:
            errors += 1
            if errors >= max_errors:
                raise
            sleep(interval)
            continue
        state, details = evaluate(checks, required_names, skip, settled=now() - start >= grace)
        if state != "pending" or now() >= deadline:
            return state if state != "pending" else "timeout", details
        sleep(interval)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    req = sub.add_parser("required")
    req.add_argument("base")
    w = sub.add_parser("wait")
    w.add_argument("pr")
    w.add_argument("--required", action="append", default=[], help="one check name; repeat the flag")
    w.add_argument("--skip", action="append", default=[], help="one check name; repeat the flag")
    w.add_argument("--interval", type=int, default=30)
    w.add_argument("--timeout", type=int, default=3600)
    args = parser.parse_args(argv)

    try:
        if args.command == "required":
            print("\n".join(required(args.base)))
            return 0
        state, details = wait(args.pr, args.required, set(args.skip), args.interval, args.timeout)
    except RuntimeError as error:
        print(f"gh failed: {error}", file=sys.stderr)
        return 2
    print(state.upper())
    for check in details["red"]:
        print(f"red: {check['name']} ({check['state']}) {check.get('link', '')}".rstrip())
    for check in details["pending"]:
        print(f"pending: {check['name']}")
    for name in details["missing"]:
        print(f"missing: {name} (required, not reported yet)")
    return {"green": 0, "red": 1, "timeout": 4}[state]


if __name__ == "__main__":
    sys.exit(main())
