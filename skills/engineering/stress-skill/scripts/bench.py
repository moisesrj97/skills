#!/usr/bin/env python3
"""Ablation bench for a skill: split it into units, build variants without some, run eval cases on each.

  bench.py units   <SKILL.md>
  bench.py variant <skill-dir> --drop S2,U7 --out <dir>
  bench.py run     --skill <variant-dir | none> --cases <cases.json> --out <dir> [--runs 2] [--model M] [--workers 6]

`run` puts the variant at .claude/skills/<name>/ of a throwaway git repo and runs `claude -p` there with
`--setting-sources project,local`, so the child sees that copy and none of the user's skills or CLAUDE.md.
cases.json is a list of:
  {"id", "prompt" | "turns": [...], "checks": [...], "fixture"?: dir relative to cases.json,
   "setup"?: shell run in the repo, "path_prefix"?: dir relative to cases.json put first on PATH (fake CLIs),
   "env"?: {name: value}, "with"?: [skill dirs relative to cases.json], "max_turns"?: n}
"turns" are user messages sent one per turn, each once the child ends the previous turn: a scripted user for
a skill that asks questions. max_turns caps each turn's agentic steps, not the number of turns.
The child and its fakes get BENCH_REPO, the repo's path: a fake logs there, since the child may cd elsewhere.
"with" installs other skills whole beside the one under test, for a skill that calls them.
"env" values may contain $BENCH_REPO, e.g. to point a skill that writes under $HOME at the throwaway repo.
A check is {"id", "want"?: true, and one of:
  "regex": pattern, "in": "final" | "transcript"   (transcript = every text and tool call, as JSON)
  "cmd": shell run in the repo after the run; exit 0 passes
  "judge": a yes/no question a cheap model answers from the transcript}
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

JUDGE_MODEL = "haiku"
TIMEOUT = 1800


def split(text: str):
    """Frontmatter, then units: each block (U) and the heading section it sits in (S; S0 before any heading)."""
    fm = ""
    if text.startswith("---\n"):
        end = text.index("\n---\n", 4) + 5
        fm, text = text[:end], text[end:]
    # A unit keeps its trailing blank lines, so joining the kept units reproduces the file minus the dropped ones.
    blocks, cur, fence, after_blank, after_heading = [], [], False, False, False
    for line in text.splitlines(keepends=True):
        blank = not line.strip()
        opens_fence = line.lstrip().startswith("```") and not fence
        starts = not fence and not blank and (
            after_blank or after_heading or opens_fence or re.match(r"#{1,6} |[-*] |\d+\. ", line))
        if starts and any(l.strip() for l in cur):
            blocks.append("".join(cur))
            cur = []
        cur.append(line)
        if line.lstrip().startswith("```"):
            fence = not fence
        after_blank = blank and not fence
        after_heading = not fence and bool(re.match(r"#{1,6} ", line))
    if cur:
        blocks.append("".join(cur))
    units, sections, section = [], [], "S0"
    for b in blocks:
        if re.match(r"#{1,6} ", b.lstrip()):
            section = f"S{len(sections) + 1}"
            sections.append((section, b.strip()))
        heading = bool(re.match(r"#{1,6} ", b.lstrip()))
        units.append({"id": f"U{len(units) + 1}", "section": section, "text": b, "heading": heading})
    return fm, units, sections


def cmd_units(args):
    _, units, sections = split(Path(args.skill_md).read_text())
    for u in units:
        head = " ".join(u["text"].split())[:90]
        if not u["heading"]:
            print(f"{u['id']:>4} {u['section']:>4}  {head}")
    print("\n" + "\n".join(f"{sid:>4}  {title}" for sid, title in sections))


def cmd_variant(args):
    src = Path(args.skill_dir)
    drop = set(filter(None, args.drop.split(",")))
    fm, units, _ = split((src / "SKILL.md").read_text())
    kept = [u for u in units if u["id"] not in drop and u["section"] not in drop]
    bodied = {u["section"] for u in kept if not u["heading"]}
    kept = [u["text"] for u in kept if not u["heading"] or u["section"] in bodied]
    out = Path(args.out)
    shutil.copytree(src, out, dirs_exist_ok=True)
    (out / "SKILL.md").write_text(fm + "".join(kept))
    print(out)


def claude(prompt: str, cwd: Path, flags: list[str], env=None) -> str:
    cmd = ["claude", "-p", "--setting-sources", "project,local", "--strict-mcp-config", "--no-session-persistence", *flags]
    return subprocess.run(cmd, cwd=cwd, input=prompt, capture_output=True, text=True, timeout=TIMEOUT, env=env).stdout


def converse(turns: list[str], cwd: Path, flags: list[str], env: dict) -> list[dict]:
    cmd = ["claude", "-p", "--setting-sources", "project,local", "--strict-mcp-config", "--no-session-persistence",
           "--input-format", "stream-json", "--output-format", "stream-json", "--verbose", *flags]
    with subprocess.Popen(cmd, cwd=cwd, env=env, text=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                          stderr=subprocess.DEVNULL) as proc:
        timer = threading.Timer(TIMEOUT, proc.kill)
        timer.start()
        pending, events = list(turns), []

        def send():
            text = pending.pop(0)
            # stream-json doesn't echo user messages, so the transcript gets them from here.
            events.append({"type": "user_turn", "text": text})
            proc.stdin.write(json.dumps({"type": "user", "message": {"role": "user", "content": text}}) + "\n")
            proc.stdin.flush()

        try:
            send()
            for line in proc.stdout:
                if not line.startswith("{"):
                    continue
                event = json.loads(line)
                events.append(event)
                if event.get("type") != "result":
                    continue
                if pending:
                    send()
                else:
                    proc.stdin.close()
        finally:
            timer.cancel()
    return events


def make_repo(case: dict, base: Path, skill: Path | None) -> Path:
    repo = Path(tempfile.mkdtemp(prefix=f"stress-{case['id']}-"))
    if fixture := case.get("fixture"):
        shutil.copytree(base / fixture, repo, dirs_exist_ok=True)
    for d in ([skill] if skill else []) + [(base / w).resolve() for w in case.get("with", [])]:
        name = re.search(r"^name:\s*(\S+)", (d / "SKILL.md").read_text(), re.M).group(1)
        shutil.copytree(d, repo / ".claude" / "skills" / name)
    git = ["git", "-c", "user.name=bench", "-c", "user.email=bench@example.test"]
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=repo, check=True)
    if setup := case.get("setup"):
        subprocess.run(setup, shell=True, cwd=repo, check=True)
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True)
    subprocess.run([*git, "commit", "-qm", "fixture", "--allow-empty"], cwd=repo, check=True)
    return repo


def transcript(events: list[dict]) -> tuple[str, str]:
    parts, final = [], ""
    for e in events:
        if e.get("type") == "user_turn":
            parts.append("USER " + e["text"])
        if e.get("type") == "user" and isinstance(e["message"].get("content"), list):
            for b in e["message"]["content"]:
                if b.get("type") == "tool_result":
                    content = b.get("content")
                    parts.append("RESULT " + (content if isinstance(content, str) else json.dumps(content))[:2000])
        if e.get("type") != "assistant":
            continue
        for b in e["message"].get("content", []):
            if b.get("type") == "text":
                parts.append("TEXT " + b["text"])
                final = b["text"]
            elif b.get("type") == "tool_use":
                parts.append(f"TOOL {b['name']} " + json.dumps(b["input"], ensure_ascii=False))
    return "\n".join(parts), final


def score(check: dict, repo: Path, full: str, final: str) -> bool:
    if "regex" in check:
        got = bool(re.search(check["regex"], final if check.get("in", "final") == "final" else full, re.S | re.M))
    elif "cmd" in check:
        got = subprocess.run(check["cmd"], shell=True, cwd=repo, capture_output=True).returncode == 0
    else:
        q = (f"Transcript of an agent run (USER = the user's messages, TEXT = what it wrote, TOOL = its tool calls, RESULT = their output):\n\n"
             f"{full[-60000:]}\n\nQuestion: {check['judge']}\nAnswer with exactly YES or NO.")
        got = claude(q, repo, ["--model", JUDGE_MODEL, "--tools", ""]).strip().upper().startswith("YES")
    return got == check.get("want", True)


def run_one(case: dict, base: Path, skill: Path | None, model: str | None, out: Path, n: int) -> dict:
    repo = make_repo(case, base, skill)
    env = dict(os.environ, BENCH_REPO=str(repo))
    env.update({k: v.replace("$BENCH_REPO", str(repo)) for k, v in case.get("env", {}).items()})
    if prefix := case.get("path_prefix"):
        env["PATH"] = f"{(base / prefix).resolve()}:{env['PATH']}"
    flags = ["--permission-mode", "auto", "--max-turns", str(case.get("max_turns", 30))]
    if model:
        flags += ["--model", model]
    events = converse(case.get("turns") or [case["prompt"]], repo, flags, env)
    full, final = transcript(events)
    run_dir = out / f"{case['id']}-{n}"
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "transcript.txt").write_text(full)
    failed = [c["id"] for c in case["checks"] if not score(c, repo, full, final)]
    return {"case": case["id"], "run": n, "failed": failed, "repo": str(repo), "final": final[:400]}


def cmd_run(args):
    cases_path = Path(args.cases).resolve()
    cases = json.loads(cases_path.read_text())
    skill = None if args.skill == "none" else Path(args.skill).resolve()
    out = Path(args.out).resolve()
    jobs = [(c, n) for c in cases for n in range(1, args.runs + 1)]
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        results = list(pool.map(lambda j: run_one(j[0], cases_path.parent, skill, args.model, out, j[1]), jobs))
    (out / "results.json").write_text(json.dumps(results, indent=1, ensure_ascii=False))
    for c in cases:
        rs = [r for r in results if r["case"] == c["id"]]
        passed = sum(not r["failed"] for r in rs)
        failed = sorted({f for r in rs for f in r["failed"]})
        print(f"{c['id']:<28} {passed}/{len(rs)}  {'failed: ' + ', '.join(failed) if failed else ''}")


def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(required=True)
    u = sub.add_parser("units")
    u.add_argument("skill_md")
    u.set_defaults(fn=cmd_units)
    v = sub.add_parser("variant")
    v.add_argument("skill_dir")
    v.add_argument("--drop", default="")
    v.add_argument("--out", required=True)
    v.set_defaults(fn=cmd_variant)
    r = sub.add_parser("run")
    r.add_argument("--skill", required=True)
    r.add_argument("--cases", required=True)
    r.add_argument("--out", required=True)
    r.add_argument("--runs", type=int, default=2)
    r.add_argument("--model")
    r.add_argument("--workers", type=int, default=6)
    r.set_defaults(fn=cmd_run)
    args = p.parse_args()
    args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
