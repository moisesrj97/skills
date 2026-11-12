#!/usr/bin/env python3
"""Run one diff-review round through the reviewer's CLI (claude or codex) and check its seal.

Usage: run_round.py --reviewer <model>:<effort> --prompt <file> --round-file <file>
                    [--handle <id>] [--repo <dir>]

A fresh round (no --handle) starts a new reviewer; with --handle it continues that one.
An unsealed round is run once more. Prints a JSON line {"handle", "round_file", "attempts"}.
Exit 1: still unsealed after the retry (stderr has the log tail).
Exit 3: the continued reviewer is gone (the resume command failed); start a fresh one.
Exit 5: the reviewer's CLI is not installed.
The CLIs are looked up as `claude` and `codex`, or DIFF_REVIEW_CLAUDE / DIFF_REVIEW_CODEX.
"""
import argparse
import json
import os
import subprocess
import sys
import uuid
from pathlib import Path

SEAL = "END OF ROUND"


def family(model):
    if model.startswith("claude"):
        return "claude"
    if model.startswith("gpt"):
        return "codex"
    raise ValueError(f"unknown model family for {model!r}: expected claude-* or gpt-*")


def parse_reviewer(spec):
    model, _, effort = spec.partition(":")
    if not model or not effort:
        raise ValueError(f"reviewer must be <model>:<effort>, got {spec!r}")
    return model, effort


def build(model, effort, handle, repo, round_file, events_file):
    """Return (argv, stdout target, cwd, handle). stdout target is a path or None for /dev/null."""
    kind = family(model)
    if kind == "claude":
        cli = os.environ.get("DIFF_REVIEW_CLAUDE", "claude")
        session = handle or str(uuid.uuid4())
        flag = "--resume" if handle else "--session-id"
        argv = [cli, "-p", flag, session, "--model", model, "--effort", effort, "--permission-mode", "plan"]
        return argv, round_file, repo, session
    cli = os.environ.get("DIFF_REVIEW_CODEX", "codex")
    reasoning = f'model_reasoning_effort="{effort}"'
    if handle:
        argv = [cli, "exec", "resume", "-m", model, "-c", reasoning, "-c", 'sandbox_mode="read-only"',
                "-o", str(round_file), handle, "-"]
        return argv, None, repo, handle
    argv = [cli, "exec", "-m", model, "-c", reasoning, "-s", "read-only", "-C", str(repo),
            "--json", "-o", str(round_file), "-"]
    return argv, events_file, repo, None


def codex_thread_id(events_file):
    for line in Path(events_file).read_text().splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if event.get("type") == "thread.started":
            return event.get("thread_id")
    return None


def sealed(round_file):
    try:
        lines = Path(round_file).read_text().rstrip().splitlines()
    except OSError:
        return False
    return bool(lines) and lines[-1].strip() == SEAL


def tail(path, n=20):
    try:
        return "\n".join(Path(path).read_text(errors="replace").splitlines()[-n:])
    except OSError:
        return "(no log)"


class CliMissing(Exception):
    pass


def attempt(model, effort, handle, repo, prompt, round_file, log, events_file):
    argv, stdout_target, cwd, new_handle = build(model, effort, handle, repo, round_file, events_file)
    Path(round_file).write_text("")
    with open(prompt) as stdin, open(log, "a") as stderr, \
            open(stdout_target or os.devnull, "w") as stdout:
        try:
            code = subprocess.run(argv, stdin=stdin, stdout=stdout, stderr=stderr, cwd=cwd).returncode
        except FileNotFoundError:
            raise CliMissing(argv[0])
    if new_handle is None:
        new_handle = codex_thread_id(events_file)
    return code, new_handle


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--reviewer", required=True, help="<model>:<effort>")
    parser.add_argument("--prompt", required=True)
    parser.add_argument("--round-file", required=True)
    parser.add_argument("--handle")
    parser.add_argument("--repo", default=".")
    args = parser.parse_args(argv)

    try:
        model, effort = parse_reviewer(args.reviewer)
        family(model)
    except ValueError as error:
        print(error, file=sys.stderr)
        return 2
    round_file = Path(args.round_file).resolve()
    log = round_file.with_suffix(".log")
    events_file = round_file.with_name(round_file.stem + "-events.jsonl")
    repo = Path(args.repo).resolve()

    for attempts in (1, 2):
        try:
            code, handle = attempt(model, effort, args.handle, repo, args.prompt, round_file, log, events_file)
        except CliMissing as missing:
            print(f"{missing} is not installed or not on PATH", file=sys.stderr)
            return 5
        if sealed(round_file):
            print(json.dumps({"handle": handle, "round_file": str(round_file), "attempts": attempts}))
            return 0
    if args.handle and code != 0:
        print(f"reviewer {args.handle} could not be continued (exit {code}); start a fresh reviewer "
              f"with the full prompt.\n--- {log} tail ---\n{tail(log)}", file=sys.stderr)
        return 3
    print(f"round unsealed after 2 attempts (exit {code}).\n--- {log} tail ---\n{tail(log)}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
