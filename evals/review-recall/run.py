#!/usr/bin/env python3
"""Recall and false-positive bench for diff-review's lenses.

Each fixture is a tiny TS repo: `base/` is committed on main, `head/` on feature. Seeds are
defects the reviewer should report; decoys are lines that look suspicious but are fine, or that
the lens must leave alone. A finding credits the entry its cited range contains, else the nearest
one in the same file within ±3 lines. A decoy with a `pattern` counts only when the finding matches it.

Arms per fixture:
  code      old: reviewer.md as of BASELINE_REF          new: reviewer.md + lenses/code.md + spec
  security  builtin: /security-review                     new: lenses/security.md reviewer + step-3 filter
  cleanup   builtin: /simplify (its edits are its hits)    new: lenses/cleanup.md with craftsmanship standards

Usage: run.py [fixture ...]   env: RUNS (default 2), WORKERS (default 6), BASELINE_REF (default d1499d7),
  OUT (a previous output dir: its transcripts are re-scored, not re-run)
One run per arm is noise: compare ranges, and when they overlap the bench can't separate the arms.
"""

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).parent
REPO = HERE.parent.parent
DIFF_REVIEW = REPO / "skills/engineering/diff-review/references"
CRAFT = REPO / "skills/engineering/craftsmanship"
RUNS = int(os.environ.get("RUNS", "2"))
WORKERS = int(os.environ.get("WORKERS", "6"))
BASELINE_REF = os.environ.get("BASELINE_REF", "d1499d7")
CLAUDE = "claude-opus-5-5"
GPT = "gpt-6.1-sol"
TIMEOUT = 1800
WINDOW = 3

EDITS = "=== EDITS ==="
FILTERED = "=== FILTERED ==="
LOCATION = re.compile(r"([\w./-]+\.(?:tsx?|jsx?)):(\d+)(?:-(\d+))?")


def sh(cmd, cwd, **kw):
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, **kw)


def make_repo(fixture: Path) -> Path:
    root = Path(tempfile.mkdtemp(prefix=f"review-recall-{fixture.name}-"))
    shutil.copytree(fixture / "base", root, dirs_exist_ok=True)
    for cmd in (
        ["git", "init", "-q", "-b", "main"],
        ["git", "add", "-A"],
        ["git", "-c", "user.name=bench", "-c", "user.email=bench@example.test", "commit", "-qm", "base"],
        ["git", "switch", "-qc", "feature"],
    ):
        sh(cmd, root, check=True)
    for path in root.iterdir():
        if path.name != ".git":
            shutil.rmtree(path) if path.is_dir() else path.unlink()
    shutil.copytree(fixture / "head", root, dirs_exist_ok=True)
    sh(["git", "add", "-A"], root, check=True)
    sh(["git", "-c", "user.name=bench", "-c", "user.email=bench@example.test", "commit", "-qm", "head"], root, check=True)
    sh(["git", "update-ref", "refs/remotes/origin/main", "main"], root, check=True)
    sh(["git", "symbolic-ref", "refs/remotes/origin/HEAD", "refs/remotes/origin/main"], root, check=True)
    return root


def run_claude(prompt: str, cwd: Path, effort: str, extra=()) -> str:
    cmd = ["claude", "-p", "--model", CLAUDE, "--effort", effort, *extra]
    return sh(cmd, cwd, input=prompt, timeout=TIMEOUT).stdout


def run_codex(prompt: str, cwd: Path, effort: str, out: Path) -> str:
    cmd = ["codex", "exec", "-m", GPT, "-c", f'model_reasoning_effort="{effort}"', "-s", "read-only", "-C", str(cwd), "-o", str(out), "-"]
    sh(cmd, cwd, input=prompt, timeout=TIMEOUT)
    return out.read_text() if out.exists() else ""


def reviewer_prompt(files, spec=None, standards=()):
    lines = [f"You are the reviewer. Read {' and '.join(str(f) for f in files)} and follow them.", ""]
    lines.append("Scope: the range main...feature. Show the diff with `git diff main...feature`. Read and quote the code from `git show feature:<file>`.")
    if spec:
        lines.append(f"Spec: {spec}. Read it before reviewing.")
    if standards:
        lines.append(f"Standards: {', '.join(str(s) for s in standards)}. Read them before reviewing.")
    lines.append("Write the round as your final message and nothing else, and write no files.")
    return "\n".join(lines)


def blocks(text: str):
    """Splits a report into (heading, body) blocks; without headings, the whole text is one block."""
    out, current = [], None
    for line in text.splitlines():
        if line.lstrip().startswith("#"):
            current = [line, []]
            out.append(current)
        elif current:
            current[1].append(line)
    return [(h, "\n".join(b)) for h, b in out] or [(text, text)]


def locations(text: str, only=None):
    found = []
    for heading, body in blocks(text):
        if only and not heading.startswith(only):
            continue
        for m in LOCATION.finditer(heading):
            start = int(m.group(2))
            found.append((m.group(1), start, int(m.group(3) or start), heading + "\n" + body))
    return found


def edited_locations(diff: str):
    found, file = [], None
    for line in diff.splitlines():
        if line.startswith("--- a/"):
            file = line[6:]
        elif line.startswith("@@") and file:
            m = re.match(r"@@ -(\d+)(?:,(\d+))?", line)
            start, count = int(m.group(1)), int(m.group(2) or "1")
            found.append([file, start, start + max(count, 1) - 1, ""])
        elif found and line[:1] in "+-" and not line.startswith(("+++", "---")):
            found[-1][3] += line + "\n"
    return found


def arm_code_old(fx, repo, scratch):
    old = scratch / "reviewer-old.md"
    old.write_text(sh(["git", "show", f"{BASELINE_REF}:skills/engineering/diff-review/references/reviewer.md"], REPO, check=True).stdout)
    return run_claude(reviewer_prompt([old]), repo, "high", ["--permission-mode", "plan"])


def arm_code_new(fx, repo, scratch):
    prompt = reviewer_prompt([DIFF_REVIEW / "reviewer.md", DIFF_REVIEW / "lenses/code.md"], spec=fx / "spec.md")
    return run_claude(prompt, repo, "high", ["--permission-mode", "plan"])


def arm_security_builtin(fx, repo, scratch):
    return run_claude("/security-review", repo, "high", ["--allowedTools", "Bash(git *) Read Grep Glob Task Agent"])


def arm_security_new(fx, repo, scratch):
    lens = DIFF_REVIEW / "lenses/security.md"
    prompt = reviewer_prompt([DIFF_REVIEW / "reviewer.md", lens])
    if shutil.which("codex"):
        round_text = run_codex(prompt, repo, "high", scratch / "security-round.md")
    else:
        round_text = run_claude(prompt, repo, "high", ["--permission-mode", "plan"])
    filter_prompt = (
        f"You check a security review round, as diff-review's step 3 does. Read {lens}. The round is below. "
        "For each finding, find its quote in `git show feature:<file>`, trace it there from the attacker's input to the sink, "
        "and test it against every exclusion and precedent. Discard one a rule rules out, naming the rule, and one the code refutes, naming the line. "
        "Your final message: the surviving findings exactly as written, then one line per discarded finding as "
        "`DISCARDED <file>:<line>: <reason>`, then `END OF ROUND`.\n\n---\n\n" + round_text
    )
    out = run_claude(filter_prompt, repo, "high", ["--permission-mode", "plan"])
    return round_text + f"\n\n{FILTERED}\n\n" + out


def arm_cleanup_builtin(fx, repo, scratch):
    out = run_claude("/simplify", repo, "medium", ["--permission-mode", "acceptEdits", "--allowedTools", "Bash(git *) Read Grep Glob Edit Agent"])
    return out + f"\n\n{EDITS}\n\n" + sh(["git", "diff", "-U0", "HEAD"], repo).stdout


def arm_cleanup_new(fx, repo, scratch):
    prompt = reviewer_prompt(
        [DIFF_REVIEW / "reviewer.md", DIFF_REVIEW / "lenses/cleanup.md"],
        standards=[CRAFT / "tidy-first.md", CRAFT / "simple-design.md"],
    )
    return run_claude(prompt, repo, "medium", ["--permission-mode", "plan"])


def found_in(fixture_name, arm, text):
    if EDITS in text:
        return edited_locations(text.split(EDITS, 1)[1])
    if FILTERED in text:
        return locations(text.split(FILTERED, 1)[1], only="### ")
    return locations(text)


ARMS = {
    "code": {"old": arm_code_old, "new": arm_code_new},
    "security": {"builtin": arm_security_builtin, "new": arm_security_new},
    "cleanup": {"builtin": arm_cleanup_builtin, "new": arm_cleanup_new},
}


def line_of(repo: Path, entry) -> int:
    head = sh(["git", "show", f"feature:{entry['file']}"], repo, check=True).stdout
    for n, text in enumerate(head.splitlines(), 1):
        if entry["match"] in text:
            return n
    raise ValueError(f"match not found: {entry}")


def credited(entries, found):
    """Entries inside a cited range all count; otherwise only the nearest one within WINDOW, seeds first on a tie.
    A decoy with a `pattern` counts only when the finding or edit matches it (e.g. proposes `pageSize ??`)."""
    hits = set()
    for f, start, end, body in found:
        same = [e for e in entries if f.endswith(e["file"]) and re.search(e.get("pattern", ""), body)]
        inside = [e for e in same if start <= e["line"] <= end]
        if inside:
            hits.update(e["id"] for e in inside)
            continue
        near = [(min(abs(e["line"] - start), abs(e["line"] - end)), e["kind"] != "seed", e["id"]) for e in same]
        near = [n for n in near if n[0] <= WINDOW]
        if near:
            hits.add(min(near)[2])
    return hits


def score(fixture_name, arm, run, text, repo):
    expected = json.loads((HERE / "fixtures" / fixture_name / "expected.json").read_text())
    found = found_in(fixture_name, arm, text)
    entries = [{**e, "kind": kind, "line": line_of(repo, e)} for kind in ("seed", "decoy") for e in expected[kind + "s"]]
    hits = credited(entries, found)
    seeds = [e["id"] for e in expected["seeds"] if e["id"] in hits]
    decoys = [e["id"] for e in expected["decoys"] if e["id"] in hits]
    sealed = "END OF ROUND" in text if arm == "new" else None
    return {"fixture": fixture_name, "arm": arm, "run": run, "seeds": seeds, "decoys": decoys,
            "n_seeds": len(expected["seeds"]), "n_decoys": len(expected["decoys"]), "sealed": sealed}


def one_run(fixture_name, arm, run, out_dir):
    fx = HERE / "fixtures" / fixture_name
    repo = make_repo(fx)
    scratch = Path(tempfile.mkdtemp(prefix="review-recall-scratch-"))
    try:
        transcript = out_dir / f"{fixture_name}-{arm}-{run}.md"
        if not transcript.exists():
            transcript.write_text(ARMS[fixture_name][arm](fx, repo, scratch))
        return score(fixture_name, arm, run, transcript.read_text(), repo)
    finally:
        shutil.rmtree(repo, ignore_errors=True)
        shutil.rmtree(scratch, ignore_errors=True)


def main(argv):
    out_dir = Path(os.environ["OUT"]) if os.environ.get("OUT") else Path(tempfile.mkdtemp(prefix="review-recall-out-"))
    fixtures = argv or list(ARMS)
    jobs = [(f, arm, r) for f in fixtures for arm in ARMS[f] for r in range(1, RUNS + 1)]
    with ThreadPoolExecutor(WORKERS) as pool:
        results = list(pool.map(lambda j: one_run(*j, out_dir), jobs))
    (out_dir / "results.json").write_text(json.dumps(results, indent=2))
    for f in fixtures:
        for arm in ARMS[f]:
            rows = [r for r in results if r["fixture"] == f and r["arm"] == arm]
            recall = sorted(len(r["seeds"]) for r in rows)
            noise = sorted(len(r["decoys"]) for r in rows)
            print(f"{f:9} {arm:8} seeds {recall[0]}-{recall[-1]}/{rows[0]['n_seeds']}  decoys hit {noise[0]}-{noise[-1]}/{rows[0]['n_decoys']}")
            for r in rows:
                seal = "" if r["sealed"] is None else ("  sealed" if r["sealed"] else "  NO SEAL")
                print(f"    run {r['run']}: seeds {r['seeds']}  decoys {r['decoys']}{seal}")
    print(f"\nTranscripts: {out_dir}")


if __name__ == "__main__":
    main(sys.argv[1:])
