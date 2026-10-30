#!/usr/bin/env python3
"""Regression check for megamoind's entry rule and its routing to megamoind-batch.

Runs each prompt in cases.json through `claude -p` inside a throwaway git repo and
checks the routing decision in the transcript. It exercises what is installed:
the skill under ~/.agents/skills and the rule in ~/.claude/CLAUDE.md.

Usage: run.py [case-id ...]   env: RUNS (default 1), MODEL, MAX_TURNS (default 3)
"""

import json
import os
import re
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).parent
RUNS = int(os.environ.get("RUNS", "1"))
MAX_TURNS = os.environ.get("MAX_TURNS", "3")

# Outward-facing tools stay out: the routing decision happens before any of them.
DISALLOWED = ["Bash", "Agent", "Workflow", "WebFetch", "WebSearch"]

BRIEF = """# ABC-123 brief

- Plan: add a `--version` flag to cli.py, tested in test_cli.py.
- Branch: ABC-123-version-flag
- Verification: `python cli.py --version` prints the version.
"""

ASKS_ABOUT_MEGAMOIND = re.compile(r"megamoind[^\n]*\?|\?[^\n]*megamoind|(without|sin) megamoind", re.I)


def make_fixture() -> Path:
    root = Path(tempfile.mkdtemp(prefix="megamoind-entry-"))
    (root / "README.md").write_text("# demo\n\nThis tool will recieve a file and print it.\n")
    (root / "cli.py").write_text("import sys\nprint(open(sys.argv[1]).read())\n")
    (root / "ABC-123-brief.md").write_text(BRIEF)
    git = ["git", "-C", str(root), "-c", "user.name=eval", "-c", "user.email=eval@example.com"]
    subprocess.run([*git, "init", "-q", "-b", "main"], check=True)
    subprocess.run([*git, "add", "."], check=True)
    subprocess.run([*git, "commit", "-q", "-m", "init"], check=True)
    return root


def run_claude(prompt: str, cwd: Path) -> list[dict]:
    cmd = [
        "claude", "-p", prompt,
        "--output-format", "stream-json", "--verbose",
        "--max-turns", MAX_TURNS,
        "--permission-mode", "acceptEdits",
        "--strict-mcp-config",
        "--disallowedTools", *DISALLOWED,
    ]
    if model := os.environ.get("MODEL"):
        cmd += ["--model", model]
    out = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=600).stdout
    return [json.loads(line) for line in out.splitlines() if line.startswith("{")]


def tool_uses(events: list[dict]) -> list[dict]:
    return [
        block
        for e in events if e.get("type") == "assistant"
        for block in e["message"].get("content", []) if block.get("type") == "tool_use"
    ]


def final_text(events: list[dict]) -> str:
    texts = [
        block.get("text", "")
        for e in events if e.get("type") == "assistant"
        for block in e["message"].get("content", []) if block.get("type") == "text"
    ]
    return texts[-1] if texts else ""


def skills_invoked(events: list[dict]) -> list[str]:
    # A leading `/skill` in the prompt is expanded by the harness and leaves no event,
    # so this sees only the skills the model chose.
    return [u["input"].get("skill", "") for u in tool_uses(events) if u["name"] == "Skill"]


def skill_name(name: str) -> str:
    return name.split(":")[-1]


def observe(events: list[dict], fixture: Path) -> dict:
    uses = tool_uses(events)
    text = final_text(events)
    asked_tool = [u for u in uses if u["name"] == "AskUserQuestion"]
    asked_text = text + json.dumps([u["input"] for u in asked_tool])
    return {
        "megamoind_invoked": any(skill_name(s) == "megamoind" for s in skills_invoked(events)),
        "batch_invoked": any(skill_name(s) == "megamoind-batch" for s in skills_invoked(events)),
        "review_skill_invoked": any("review" in s for s in skills_invoked(events)),
        "asks_about_megamoind": bool(ASKS_ABOUT_MEGAMOIND.search(asked_text)),
        "asks_user": bool(asked_tool) or text.rstrip().endswith("?"),
        "edits": any(u["name"] in ("Edit", "Write", "NotebookEdit") for u in uses),
        "readme_fixed": "receive" in (fixture / "README.md").read_text(),
        "brief_read": any(
            u["name"] == "Read" and u["input"].get("file_path", "").endswith("ABC-123-brief.md")
            for u in uses
        ),
    }


def run_case(case: dict) -> tuple[dict, list[dict]]:
    results = []
    for _ in range(RUNS):
        fixture = make_fixture()
        events = run_claude(case["prompt"].replace("{fixture}", str(fixture)), fixture)
        seen = observe(events, fixture)
        failed = {k: seen[k] for k, want in case["checks"].items() if seen[k] != want}
        results.append({"failed": failed, "tools": [u["name"] for u in tool_uses(events)],
                        "skills": skills_invoked(events), "text": final_text(events)[:300],
                        "fixture": str(fixture)})
    return case, results


def main() -> int:
    cases = json.loads((HERE / "cases.json").read_text())
    if wanted := sys.argv[1:]:
        cases = [c for c in cases if c["id"] in wanted]
    with ThreadPoolExecutor(max_workers=len(cases)) as pool:
        outcomes = list(pool.map(run_case, cases))

    all_green = True
    for case, results in outcomes:
        passed = sum(not r["failed"] for r in results)
        all_green &= passed == len(results)
        print(f"{'PASS' if passed == len(results) else 'FAIL'}  {case['id']}  {passed}/{len(results)}  — {case['expect']}")
        for r in results:
            if r["failed"]:
                print(f"      failed: {r['failed']}")
                print(f"      skills: {r['skills']}  tools: {r['tools']}")
                print(f"      text:   {r['text']!r}")
                print(f"      fixture: {r['fixture']}")
    return 0 if all_green else 1


if __name__ == "__main__":
    sys.exit(main())
