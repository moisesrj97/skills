#!/usr/bin/env python3
"""Pick the Claude Code sessions a retro sweep reviews, and remember what their triage found.

Usage:
  sweep.py candidates --out <dir> [--days 3] [--idle-hours 2]
      Prints a JSON list of sessions to review, each with session, cwd, first_prompt,
      size_kb, condensed (its timeline, written to <dir>) and triage: "friction" for one an
      earlier run triaged whose retro is still missing (listed first, however old), null for
      a new one from the last --days (oldest first).
  sweep.py record --from <file.json>        {"<session path>": {"verdict": "clean" | "friction", "why": "…"}}
      Adds the verdicts to the ledger, ~/.skill-docs/retro-sweep.json.

A session is left out while it is still active (written to within --idle-hours), when it ran
outside a real checkout (a temp folder: evals, benches), when it is a sweep itself, when a
retro already names it, and when the ledger already has it as clean.
"""
import argparse
import datetime
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

PROJECTS = Path.home() / ".claude" / "projects"
SKILL_DOCS = Path(os.environ.get("SKILL_DOCS_DIR", Path.home() / ".skill-docs"))
RETROS = SKILL_DOCS / "retros"
LEDGER = SKILL_DOCS / "retro-sweep.json"
CONDENSE = Path(__file__).parent / "condense_session.py"
TEMP = re.compile(r"^/(private/)?(var/folders|tmp)/")
SELF = "/retro-sweep"


def head(path):
    """The session's cwd and its first prompt, read only as far as both are known."""
    cwd = prompt = None
    with open(path, errors="replace") as handle:
        for line in handle:
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            cwd = cwd or entry.get("cwd")
            if prompt is None and entry.get("type") == "user" and not entry.get("isMeta"):
                content = entry.get("message", {}).get("content")
                if isinstance(content, list):
                    content = " ".join(p.get("text", "") for p in content if p.get("type") == "text")
                prompt = " ".join((content or "").split())
            if cwd and prompt is not None:
                break
    return cwd, prompt


def retro_sessions(retros=RETROS):
    stems = set()
    for path in Path(retros).glob("*/*.md"):
        for line in path.read_text(errors="replace").splitlines()[:12]:
            if line.startswith("session:"):
                stems.add(Path(line.split(":", 1)[1].strip()).stem)
    return stems


def load_ledger(ledger=LEDGER):
    return json.loads(Path(ledger).read_text()) if Path(ledger).exists() else {}


def candidates(out, days=3, idle_hours=2, projects=PROJECTS, retros=RETROS, ledger=LEDGER, now=None):
    now = now or time.time()
    known = load_ledger(ledger)
    reviewed = retro_sessions(retros)
    pending, fresh = [], []
    for path in Path(projects).glob("*/*.jsonl"):
        age = now - path.stat().st_mtime
        verdict = known.get(str(path), {}).get("verdict")
        if age < idle_hours * 3600 or path.stem in reviewed or verdict == "clean":
            continue
        if verdict != "friction" and age > days * 86400:
            continue
        cwd, prompt = head(path)
        if not cwd or prompt is None or TEMP.match(cwd) or SELF in prompt[:300]:
            continue
        item = {"session": str(path), "cwd": cwd, "first_prompt": prompt[:120],
                "size_kb": path.stat().st_size // 1024, "triage": verdict, "mtime": path.stat().st_mtime}
        (pending if verdict == "friction" else fresh).append(item)
    chosen = sorted(pending, key=lambda i: i["mtime"]) + sorted(fresh, key=lambda i: i["mtime"])
    Path(out).mkdir(parents=True, exist_ok=True)
    for item in chosen:
        condensed = Path(out) / f"{Path(item['session']).stem}.txt"
        with open(condensed, "w") as handle:
            subprocess.run([sys.executable, str(CONDENSE), item["session"], "--max", "300"],
                           stdout=handle, check=False)
        item["condensed"] = str(condensed)
        del item["mtime"]
    return chosen


def record(verdicts, ledger=LEDGER):
    data = load_ledger(ledger)
    today = datetime.date.today().isoformat()
    for session, found in verdicts.items():
        if found.get("verdict") not in ("clean", "friction"):
            raise ValueError(f"{session}: verdict {found.get('verdict')!r} is not clean or friction")
        data[session] = {"verdict": found["verdict"], "why": found.get("why", ""), "date": today}
    Path(ledger).parent.mkdir(parents=True, exist_ok=True)
    Path(ledger).write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    c = sub.add_parser("candidates")
    c.add_argument("--out", required=True)
    c.add_argument("--days", type=float, default=3)
    c.add_argument("--idle-hours", type=float, default=2)
    r = sub.add_parser("record")
    r.add_argument("--from", dest="from_file", required=True)
    args = parser.parse_args(argv)
    if args.command == "candidates":
        print(json.dumps(candidates(args.out, args.days, args.idle_hours), indent=2, ensure_ascii=False))
        return 0
    try:
        record(json.loads(Path(args.from_file).read_text()))
    except ValueError as error:
        print(error, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
