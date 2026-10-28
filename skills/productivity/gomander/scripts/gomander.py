#!/usr/bin/env python3
"""Talk to the local Gomander integrations API.

Usage:
  gomander.py commands                 list commands with status
  gomander.py groups                   list command groups with running counts
  gomander.py run <name|id>            start a command
  gomander.py stop <name|id>           stop a command
  gomander.py run-group <name|id>      start every command in a group
  gomander.py stop-group <name|id>     stop every command in a group

Targets resolve by exact id, then case-insensitive exact name, then unique
case-insensitive substring. Ambiguous or unknown targets exit 2 and print the
candidates so the caller can pick one.

Set GOMANDER_PORT to skip port discovery.
"""
import json
import os
import sys
import urllib.error
import urllib.request

PORT_RANGE = range(9001, 9101)


def request(port, method, path, timeout=2.0):
    req = urllib.request.Request(f"http://127.0.0.1:{port}{path}", method=method)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        body = resp.read().decode()
        return json.loads(body) if body.strip() else None


def discover_port():
    if os.environ.get("GOMANDER_PORT"):
        return int(os.environ["GOMANDER_PORT"])
    for port in PORT_RANGE:
        try:
            if (request(port, "GET", "/discovery", timeout=0.3) or {}).get("app") == "Gomander":
                return port
        except (OSError, ValueError):
            continue
    fail("Gomander is not reachable on ports 9001-9100. Is the app open?", code=3)


def fail(message, code=1):
    print(message, file=sys.stderr)
    sys.exit(code)


def resolve(items, target, kind):
    by_id = [i for i in items if i["id"] == target]
    if by_id:
        return by_id[0]
    lowered = target.casefold()
    exact = [i for i in items if i["name"].casefold() == lowered]
    if len(exact) == 1:
        return exact[0]
    partial = exact or [i for i in items if lowered in i["name"].casefold()]
    if len(partial) == 1:
        return partial[0]
    if not partial:
        names = ", ".join(i["name"] for i in items)
        fail(f"No {kind} matches '{target}'. Available: {names}", code=2)
    listing = "\n".join(f"  {i['name']}  ({i['id']})" for i in partial)
    fail(f"'{target}' matches several {kind}s:\n{listing}", code=2)


def print_commands(commands):
    for c in commands:
        print(f"{c['status']:<8} {c['name']}  ({c['id']})")


def print_groups(groups):
    for g in groups:
        print(f"{g['runningCommands']}/{g['commands']} running  {g['name']}  ({g['id']})")


def main(argv):
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return
    action, rest = argv[0], argv[1:]
    port = discover_port()

    try:
        if action == "commands":
            print_commands(request(port, "GET", "/commands"))
        elif action == "groups":
            print_groups(request(port, "GET", "/command-groups"))
        elif action in ("run", "stop"):
            if not rest:
                fail(f"Usage: gomander.py {action} <name|id>")
            cmd = resolve(request(port, "GET", "/commands"), " ".join(rest), "command")
            request(port, "POST", f"/commands/{cmd['id']}/{action}")
            print(f"{action} sent to command '{cmd['name']}'")
        elif action in ("run-group", "stop-group"):
            if not rest:
                fail(f"Usage: gomander.py {action} <name|id>")
            verb = action.split("-")[0]
            group = resolve(request(port, "GET", "/command-groups"), " ".join(rest), "group")
            request(port, "POST", f"/command-groups/{group['id']}/{verb}")
            print(f"{verb} sent to group '{group['name']}'")
        else:
            fail(f"Unknown action '{action}'. Run with --help.")
    except urllib.error.HTTPError as e:
        fail(f"Gomander answered {e.code}: {e.read().decode().strip()}")
    except urllib.error.URLError as e:
        fail(f"Gomander stopped answering on port {port}: {e.reason}. Is the app open?", code=3)


if __name__ == "__main__":
    main(sys.argv[1:])
