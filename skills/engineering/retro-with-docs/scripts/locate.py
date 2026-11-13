#!/usr/bin/env python3
"""Find a Claude Code session's transcripts and where its retro goes.

Usage: locate.py [--session <id or .jsonl path>] [--cwd <dir>]

Prints JSON: session (the newest transcript of the cwd's project unless --session names one),
subagents (its subagent transcripts), project (the main checkout's name, so a linked worktree
files under its repo) and retro_dir (~/.skill-docs/retros/<project>).
"""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

PROJECTS = Path.home() / ".claude" / "projects"
RETROS = Path.home() / ".skill-docs" / "retros"


def transcripts_dir(cwd, projects=PROJECTS):
    return projects / re.sub(r"[^A-Za-z0-9]", "-", str(cwd))


T3 = Path.home() / ".t3"


def project_name(cwd, t3=T3):
    cwd = Path(cwd)
    if cwd.is_dir():
        result = subprocess.run(["git", "rev-parse", "--path-format=absolute", "--git-common-dir"],
                                cwd=cwd, capture_output=True, text=True)
        if result.returncode == 0 and result.stdout.strip():
            return Path(result.stdout.strip()).parent.name
    # A T3 worktree may be gone by the time its session is swept, and a T3 scratch folder is
    # one per thread: neither names a project.
    worktrees = t3 / "worktrees"
    if cwd.is_relative_to(worktrees) and cwd != worktrees:
        return cwd.relative_to(worktrees).parts[0]
    if cwd.is_relative_to(t3 / "scratch"):
        return "scratch"
    return cwd.name or "unknown"


def newest(paths):
    return max(paths, key=lambda p: p.stat().st_mtime, default=None)


def locate(cwd, session=None, projects=PROJECTS):
    cwd = Path(cwd).resolve()
    if session and session.endswith(".jsonl"):
        transcript = Path(session).expanduser()
    else:
        folder = transcripts_dir(cwd, projects)
        if session:
            transcript = folder / f"{session}.jsonl"
        else:
            transcript = newest(folder.glob("*.jsonl"))
    if transcript is None or not transcript.exists():
        return None
    subagents = sorted(str(p) for p in (transcript.with_suffix("") / "subagents").glob("*.jsonl"))
    project = project_name(cwd)
    return {
        "session": str(transcript),
        "subagents": subagents,
        "project": project,
        "retro_dir": str(RETROS / project),
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--session")
    parser.add_argument("--cwd", default=".")
    args = parser.parse_args(argv)
    found = locate(args.cwd, args.session)
    if found is None:
        print(f"no transcript found under {transcripts_dir(Path(args.cwd).resolve())}", file=sys.stderr)
        return 1
    print(json.dumps(found, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
