#!/usr/bin/env python3
"""Bookkeeping for the dream skill, shared with Claude Code's native auto-dream.

Claude Code keeps `<memory-dir>/.consolidate-lock`: its mtime is the time of the
last consolidation, its content the PID of the process holding it. A lock younger
than an hour whose PID is alive means a dream is running.
"""
import argparse
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

LOCK = ".consolidate-lock"
LOCK_TTL_S = 3600
THROWAWAY = ("-private-var-folders-", "-t3-scratch-")
WORKTREE = re.compile(r"^(?P<home>.+)--t3-worktrees-(?P<repo>.+)-t3-[0-9a-f]{8}(-[0-9a-f]{16})?$")


def default_memory_dir() -> Path:
    cwd = Path.cwd()
    try:
        common = subprocess.run(
            ["git", "rev-parse", "--path-format=absolute", "--git-common-dir"],
            capture_output=True, text=True, check=True,
        ).stdout.strip()
        root = Path(common).parent
    except (subprocess.CalledProcessError, FileNotFoundError):
        root = cwd
    project = re.sub(r"[^A-Za-z0-9]", "-", str(root))
    return Path.home() / ".claude" / "projects" / project / "memory"


def pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def iso(ts: float | None) -> str | None:
    if not ts:
        return None
    return datetime.fromtimestamp(ts, timezone.utc).isoformat(timespec="seconds")


def worktree_dirs(project: Path) -> list[Path]:
    """T3 worktree sessions land in a project dir of their own; they belong to the repo's memory."""
    out = []
    for path in project.parent.iterdir():
        match = WORKTREE.match(path.name)
        if match and project.name.startswith(match["home"]) and project.name.endswith(f"-{match['repo']}"):
            out.append(path)
    return sorted(out)


def sessions_since(memory_dir: Path, last: float, skip: str | None = None) -> list[Path]:
    project = memory_dir.parent
    found = (p for d in [project, *worktree_dirs(project)] for p in d.glob("*.jsonl"))
    return sorted((p for p in found if p.stat().st_mtime > last and p.stem != skip), key=lambda p: p.stat().st_mtime)


def lock_mtime(memory_dir: Path) -> float:
    lock = memory_dir / LOCK
    return lock.stat().st_mtime if lock.exists() else 0.0


def projects(root: Path) -> int:
    due = []
    for project in sorted(root.iterdir()):
        memory_dir = project / "memory"
        if any(mark in project.name for mark in THROWAWAY) or WORKTREE.match(project.name) or not memory_dir.is_dir():
            continue
        last = lock_mtime(memory_dir)
        count = len(sessions_since(memory_dir, last))
        if count:
            due.append({"memory_dir": str(memory_dir), "sessions": count, "last_consolidated_at": iso(last)})
    print(json.dumps(due, indent=2))
    return 0


def start(memory_dir: Path) -> int:
    if not memory_dir.is_dir():
        print(json.dumps({"error": f"memory dir not found: {memory_dir}"}))
        return 1
    lock = memory_dir / LOCK
    owner = int(os.environ.get("CLAUDE_PID") or os.getppid())
    last = 0.0
    if lock.exists():
        last = lock.stat().st_mtime
        holder = lock.read_text().strip()
        if (
            holder.isdigit()
            and int(holder) != owner
            and time.time() - last < LOCK_TTL_S
            and pid_alive(int(holder))
        ):
            print(json.dumps({"error": f"another dream holds the lock (PID {holder})"}))
            return 1

    transcripts = memory_dir.parent
    sessions = sessions_since(memory_dir, last, skip=os.environ.get("CLAUDE_CODE_SESSION_ID"))
    lock.write_text(str(owner))
    print(json.dumps({
        "memory_dir": str(memory_dir),
        "transcripts_dir": str(transcripts),
        "last_consolidated_at": iso(last),
        "previous_lock_mtime": last,
        "sessions": [{"id": p.stem, "modified": iso(p.stat().st_mtime)}
                     | ({} if p.parent == transcripts else {"transcripts_dir": str(p.parent)}) for p in sessions],
    }, indent=2))
    return 0


def rollback(memory_dir: Path, to: float) -> int:
    lock = memory_dir / LOCK
    if to == 0:
        lock.unlink(missing_ok=True)
    else:
        lock.write_text("")
        os.utime(lock, (to, to))
    print(json.dumps({"rolled_back_to": iso(to)}))
    return 0


def text_of(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(b.get("text", "") for b in content if isinstance(b, dict) and b.get("type") == "text")
    return ""


def digest(transcript: Path, width: int) -> int:
    for line in transcript.open(encoding="utf-8", errors="replace"):
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        if rec.get("isSidechain") or rec.get("isMeta"):
            continue
        kind = rec.get("type")
        stamp = (rec.get("timestamp") or "")[:16]
        answers = (rec.get("toolUseResult") or {}).get("answers") if isinstance(rec.get("toolUseResult"), dict) else None
        if answers:
            for question, answer in answers.items():
                print(f"[{stamp}] ANSWER {question[:width]} -> {answer[:width]}")
            continue
        if kind not in ("user", "assistant"):
            continue
        text = text_of((rec.get("message") or {}).get("content")).strip()
        if not text or text.startswith("<"):
            continue
        label = "USER" if kind == "user" else "CLAUDE"
        flat = " ".join(text.split())
        print(f"[{stamp}] {label} {flat[:width]}{'…' if len(flat) > width else ''}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["projects", "start", "rollback", "digest"])
    parser.add_argument("session", nargs="?", help="digest: session id")
    parser.add_argument("--memory-dir", type=Path)
    parser.add_argument("--to", type=float, help="rollback: previous_lock_mtime printed by start")
    parser.add_argument("--width", type=int, default=500, help="digest: characters kept per message")
    parser.add_argument("--projects-dir", type=Path, default=Path.home() / ".claude" / "projects")
    args = parser.parse_args()
    if args.command == "projects":
        return projects(args.projects_dir.expanduser())
    memory_dir = (args.memory_dir or default_memory_dir()).expanduser()
    if args.command == "digest":
        if not args.session:
            parser.error("digest needs a session id")
        project = memory_dir.parent
        found = [d / f"{args.session}.jsonl" for d in [project, *worktree_dirs(project)]]
        return digest(next((p for p in found if p.exists()), found[0]), args.width)
    if args.command == "start":
        return start(memory_dir)
    if args.to is None:
        parser.error("rollback needs --to")
    return rollback(memory_dir, args.to)


if __name__ == "__main__":
    sys.exit(main())
