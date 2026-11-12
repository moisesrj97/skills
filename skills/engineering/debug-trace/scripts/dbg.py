#!/usr/bin/env python3
"""Session marker, trace summary and cleanup for debug-trace.

Usage:
  dbg.py new                      fresh token: prints the marker and an empty trace file
  dbg.py list <token> [root]      every line carrying the marker, as path:line: text
  dbg.py summary <token> [--label L --fields a,b.c] [--limit 20]
                                    counts per label; with --label, one row per event
  dbg.py clean <token> [root]     deletes every marked line and the trace file, re-scans,
                                    prints `git status --short`; exit 1 if a marker survives
"""
import argparse
import json
import os
import secrets
import subprocess
import sys
from collections import Counter
from pathlib import Path

PREFIX = "CLAUDE-DBG:"
SKIP_DIRS = {"node_modules", ".git", "dist", "build"}


def marker(token):
    return f"{PREFIX}{token}"


def trace_file(token):
    return Path(f"/tmp/claude-debug-{token}.log")


def walk(root):
    for directory, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for name in files:
            yield Path(directory) / name


def read_bytes(path):
    try:
        data = path.read_bytes()
    except OSError:
        return None
    return None if b"\0" in data[:8192] else data


def find(token, root):
    needle = marker(token).encode()
    hits = []
    for path in walk(root):
        data = read_bytes(path)
        if data is None or needle not in data:
            continue
        for number, line in enumerate(data.splitlines(), 1):
            if needle in line:
                hits.append((path, number, line.decode(errors="replace").strip()))
    return hits


def strip_markers(token, root):
    needle = marker(token).encode()
    changed = []
    for path in {hit[0] for hit in find(token, root)}:
        data = path.read_bytes()
        kept = [line for line in data.splitlines(keepends=True) if needle not in line]
        path.write_bytes(b"".join(kept))
        changed.append(path)
    return sorted(changed)


def parse_trace(token, text):
    events, malformed = [], 0
    for line in text.splitlines():
        at = line.find(marker(token))
        if at < 0:
            continue
        parts = line[at:].split("|", 2)
        if len(parts) < 3:
            malformed += 1
            continue
        label, payload = parts[1].strip(), parts[2].strip()
        try:
            events.append((label, json.loads(payload)))
        except ValueError:
            events.append((label, payload))
            malformed += 1
    return events, malformed


def field(value, dotted):
    for key in dotted.split("."):
        if isinstance(value, dict):
            value = value.get(key)
        elif isinstance(value, list) and key.isdigit() and int(key) < len(value):
            value = value[int(key)]
        else:
            return None
    return value


def short(value, width=60):
    text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)
    return text if len(text) <= width else text[: width - 1] + "…"


def summary(token, label=None, fields=(), limit=20):
    path = trace_file(token)
    if not path.exists():
        return f"no trace file at {path}"
    events, malformed = parse_trace(token, path.read_text(errors="replace"))
    out = [f"{len(events)} events in {path}" + (f", {malformed} not one-line JSON" if malformed else "")]
    if label is None:
        for name, count in Counter(l for l, _ in events).most_common():
            keys = next((sorted(p) for l, p in events if l == name and isinstance(p, dict)), [])
            out.append(f"{name}: {count}" + (f"  keys: {', '.join(keys)}" if keys else ""))
        return "\n".join(out)
    rows = [p for l, p in events if l == label]
    out.append(f"{label}: {len(rows)}")
    for payload in rows[:limit]:
        cells = [short(field(payload, f)) for f in fields] if fields else [short(payload, 160)]
        out.append(" | ".join(cells))
    if len(rows) > limit:
        out.append(f"… {len(rows) - limit} more")
    return "\n".join(out)


def git_status(root):
    result = subprocess.run(["git", "status", "--short"], cwd=root, capture_output=True, text=True)
    return result.stdout.strip() if result.returncode == 0 else "(not a git repo)"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("new")
    for name in ("list", "clean"):
        p = sub.add_parser(name)
        p.add_argument("token")
        p.add_argument("root", nargs="?", default=".")
    s = sub.add_parser("summary")
    s.add_argument("token")
    s.add_argument("--label")
    s.add_argument("--fields", default="")
    s.add_argument("--limit", type=int, default=20)
    args = parser.parse_args(argv)

    if args.command == "new":
        token = secrets.token_hex(2)
        trace_file(token).write_text("")
        print(f"marker: {marker(token)}\ntrace file: {trace_file(token)}")
        return 0
    if args.command == "summary":
        fields = [f.strip() for f in args.fields.split(",") if f.strip()]
        print(summary(args.token, args.label, fields, args.limit))
        return 0
    if args.command == "list":
        for path, number, text in find(args.token, args.root):
            print(f"{path}:{number}: {text}")
        return 0
    changed = strip_markers(args.token, args.root)
    trace_file(args.token).unlink(missing_ok=True)
    left = find(args.token, args.root)
    print(f"removed marked lines from {len(changed)} file(s)")
    for path, number, text in left:
        print(f"LEFT {path}:{number}: {text}")
    print("git status --short:\n" + (git_status(args.root) or "(clean)"))
    return 1 if left else 0


if __name__ == "__main__":
    sys.exit(main())
