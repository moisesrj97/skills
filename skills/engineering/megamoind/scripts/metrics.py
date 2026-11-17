#!/usr/bin/env python3
"""Time, tokens and context of a megamoind run, logged for later comparison.

Usage:
  metrics.py start <ticket> --dir <scratchpad>
      Writes <scratchpad>/<ticket>-metrics.json and prints the run tag line. Every agent the
      run starts carries that line in its prompt, with its role (`role=implementer`).
  metrics.py mark <state file> <phase>
  metrics.py collect <state file> [--log <file>]
      Finds every Claude transcript and Codex session carrying the tag, measures each one and
      the main agent's phases, and appends the run as one line to the log.
  metrics.py report [--log <file>] [--baseline <file>] [--min-runs N]
      Summarises the runs logged since the last report; prints nothing and exits 3 while
      there are fewer than N.
"""
import argparse
import json
import re
import statistics
import sys
from datetime import datetime, timezone
from pathlib import Path

HOME = Path.home()
LOG = HOME / ".skill-docs/megamoind/metrics.jsonl"
BASELINE = HOME / ".skill-docs/megamoind/baseline.json"
SEEN = HOME / ".skill-docs/megamoind/last-report.json"
PROJECTS = HOME / ".claude/projects"
CODEX = HOME / ".codex/sessions"
TAG = re.compile(r"megamoind-run: ([\w.-]+)(?: role=([\w-]+))?")
NOTICES = ("Delegated task node", "Another Claude session sent", "<task-notification", "Update on pull request")
TOKENS = ("cache_read", "cache_write", "input", "output")


def parse_time(stamp):
    return datetime.fromisoformat(stamp.replace("Z", "+00:00")).timestamp()


def now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")


def read_jsonl(path):
    with path.open(errors="replace") as f:
        for line in f:
            try:
                yield json.loads(line)
            except ValueError:
                continue


def tagged_files(root, run, since):
    if not root.exists():
        return []
    needle = f"megamoind-run: {run}"
    return [p for p in root.rglob("*.jsonl") if p.stat().st_mtime >= since and needle in p.read_text(errors="replace")]


def blocks(record):
    content = record.get("message", {}).get("content")
    return content if isinstance(content, list) else [{"type": "text", "text": content or ""}]


def text_of(record):
    return " ".join(str(b.get("text") or b.get("content") or "") for b in blocks(record))


def tag_in(obj):
    return TAG.search(json.dumps(obj).replace("\\n", "\n"))


def token_sums(turns):
    return {k: sum(x[k] for x in turns) for k in TOKENS}


def peak_context(turns):
    return max((x["cache_read"] + x["cache_write"] + x["input"] for x in turns), default=0)


def working_seconds(phase):
    return phase["seconds"] - phase["human_seconds"]


def claude_agent(path, run):
    records = sorted((r for r in read_jsonl(path) if r.get("type") in ("user", "assistant") and "timestamp" in r),
                     key=lambda r: parse_time(r["timestamp"]))
    tags = ((i, tag_in(r.get("message", {}))) for i, r in enumerate(records))
    start, match = next(((i, m) for i, m in tags if m and m.group(1) == run), (None, None))
    if start is None:
        return None
    role = match.group(2) or "child"
    records = records[start:]
    turns, models, seen, human, asking = [], set(), set(), [], {}
    for prev, rec in zip([None] + records, records):
        t = parse_time(rec["timestamp"])
        if rec["type"] == "assistant":
            for b in blocks(rec):
                if b.get("type") == "tool_use" and b.get("name") == "AskUserQuestion":
                    asking[b["id"]] = t
            msg = rec["message"]
            if msg.get("id") in seen:
                continue
            seen.add(msg.get("id"))
            u = msg.get("usage") or {}
            models.add(msg.get("model", "?"))
            turns.append({"t": t, "model": msg.get("model", "?"), "cache_read": u.get("cache_read_input_tokens", 0), "cache_write": u.get("cache_creation_input_tokens", 0),
                          "input": u.get("input_tokens", 0), "output": u.get("output_tokens", 0)})
        elif prev is not None:
            results = [b for b in blocks(rec) if b.get("type") == "tool_result"]
            answered = [asking[b["tool_use_id"]] for b in results if b.get("tool_use_id") in asking]
            if answered:
                human.append((min(answered), t))
            elif not results and prev["type"] == "assistant" and not text_of(rec).startswith(NOTICES):
                human.append((parse_time(prev["timestamp"]), t))
    first, last = parse_time(records[0]["timestamp"]), parse_time(records[-1]["timestamp"])
    agent = {"role": role, "kind": "claude", "models": sorted(models), "file": str(path), "seconds": round(last - first),
             "turns": len(turns), "peak_context": peak_context(turns), **token_sums(turns),
             "by_model": {m: token_sums([x for x in turns if x["model"] == m]) for m in sorted(models)}}
    return agent, turns, human


def codex_agent(path, run):
    role, models, total, turns, times = "review", set(), {}, [], []
    for r in read_jsonl(path):
        p = r.get("payload") or {}
        if "timestamp" in r:
            times.append(parse_time(r["timestamp"]))
        settings = p.get("thread_settings") or {}
        if settings.get("model"):
            models.add(settings["model"])
        match = tag_in(p)
        if match and match.group(1) == run and match.group(2):
            role = match.group(2)
        if p.get("type") == "token_count" and p.get("info"):
            total = p["info"].get("total_token_usage") or total
            last = p["info"].get("last_token_usage") or {}
            cached = last.get("cached_input_tokens", 0)
            turns.append({"t": parse_time(r["timestamp"]), "cache_read": cached, "cache_write": last.get("cache_write_input_tokens", 0),
                          "input": last.get("input_tokens", 0) - cached, "output": last.get("output_tokens", 0)})
    cached = total.get("cached_input_tokens", 0)
    tokens = {"cache_read": cached, "cache_write": total.get("cache_write_input_tokens", 0),
              "input": total.get("input_tokens", 0) - cached, "output": total.get("output_tokens", 0)}
    return {"role": role, "kind": "codex", "models": sorted(models), "file": str(path),
            "seconds": round(max(times) - min(times)) if times else 0, "turns": len(turns), "peak_context": peak_context(turns), **tokens,
            "by_model": {", ".join(sorted(models)) or "?": tokens}}, turns


def phases_of(marks, end, turns, human):
    bounds = [(m["phase"], parse_time(m["t"])) for m in marks]
    out = []
    for i, (name, start) in enumerate(bounds):
        stop = bounds[i + 1][1] if i + 1 < len(bounds) else end
        mine = [x for x in turns if start <= x["t"] < stop]
        waited = sum(max(0, min(b, stop) - max(a, start)) for a, b in human)
        out.append({"phase": name, "seconds": round(stop - start), "human_seconds": round(waited), "turns": len(mine),
                    "peak_context": peak_context(mine), **token_sums(mine)})
    return out


def collect(state_file, projects=PROJECTS, codex=CODEX, now=None):
    state = json.loads(Path(state_file).read_text())
    run, stamp = state["run"], now or now_iso()
    since = parse_time(state["marks"][0]["t"]) - 60
    agents, turns, human = [], [], []
    for path in tagged_files(Path(projects), run, since):
        found = claude_agent(path, run)
        if found:
            agents.append(found[0])
            turns += found[1]
            if found[0]["role"] == "main":
                human = found[2]
    for path in tagged_files(Path(codex), run, since):
        agent, codex_turns = codex_agent(path, run)
        agents.append(agent)
        turns += codex_turns
    agents.sort(key=lambda a: (a["role"] != "main", a["role"]))
    phases = phases_of(state["marks"], parse_time(stamp), turns, human)
    return {"run": run, "ticket": state["ticket"], "repo": state.get("repo"), "start": state["marks"][0]["t"],
            "end": stamp, "phases": phases, "agents": agents}


def quantiles(values):
    values = sorted(values)
    return values[len(values) // 4], statistics.median(values), values[3 * len(values) // 4]


def summarise(runs):
    def per_run(value, keep, scale):
        return [sum(value(a) for a in r["agents"] if keep(a)) / scale for r in runs]

    main, claude, codex = (lambda a: a["role"] == "main"), (lambda a: a["kind"] == "claude"), (lambda a: a["kind"] == "codex")
    rows = {
        "run minutes": [sum(map(working_seconds, r["phases"])) / 60 for r in runs],
        "main peak context (k)": per_run(lambda a: a["peak_context"], main, 1000),
        "main cache read (M)": per_run(lambda a: a["cache_read"], main, 1e6),
        "main output (k)": per_run(lambda a: a["output"], main, 1000),
        "claude cache read, all agents (M)": per_run(lambda a: a["cache_read"], claude, 1e6),
        "claude output, all agents (k)": per_run(lambda a: a["output"], claude, 1000),
        "codex input, all reviewers (M)": per_run(lambda a: a["cache_read"] + a["input"], codex, 1e6),
    }
    return {k: quantiles(v) for k, v in rows.items()}


def report(log=LOG, baseline=BASELINE, seen=SEEN, min_runs=10):
    log, seen = Path(log), Path(seen)
    done = set(json.loads(seen.read_text())) if seen.exists() else set()
    latest = {r["run"]: r for r in read_jsonl(log)} if log.exists() else {}
    runs = [r for run, r in latest.items() if run not in done]
    if not runs or len(runs) < min_runs:
        return None
    base = json.loads(Path(baseline).read_text()) if baseline and Path(baseline).exists() else {}
    lines = [f"megamoind metrics: {len(runs)} runs since the last report (p25 / median / p75)"]
    for name, (lo, mid, hi) in summarise(runs).items():
        ref = f"   baseline {base[name][1]:.0f}" if name in base else ""
        lines.append(f"  {name}: median {mid:.0f}  ({lo:.0f}–{hi:.0f}){ref}")
    phase_share = {}
    for r in runs:
        total = sum(map(working_seconds, r["phases"])) or 1
        for p in r["phases"]:
            phase_share.setdefault(p["phase"], []).append(working_seconds(p) / total * 100)
    lines.append("  share of run time per phase (median %):")
    for name, shares in sorted(phase_share.items()):
        lines.append(f"    {name}: {statistics.median(shares):.0f}")
    seen.parent.mkdir(parents=True, exist_ok=True)
    seen.write_text(json.dumps(sorted(done | {r["run"] for r in runs})))
    return "\n".join(lines)


def main(argv):
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("start")
    s.add_argument("ticket")
    s.add_argument("--dir", required=True)
    m = sub.add_parser("mark")
    m.add_argument("state")
    m.add_argument("phase")
    c = sub.add_parser("collect")
    c.add_argument("state")
    c.add_argument("--log", default=LOG)
    r = sub.add_parser("report")
    r.add_argument("--log", default=LOG)
    r.add_argument("--baseline", default=BASELINE)
    r.add_argument("--min-runs", type=int, default=10)
    args = parser.parse_args(argv)

    if args.cmd == "start":
        run = f"{args.ticket}-{datetime.now(timezone.utc):%Y%m%d%H%M%S}"
        state = Path(args.dir) / f"{args.ticket}-metrics.json"
        state.write_text(json.dumps({"run": run, "ticket": args.ticket, "repo": str(Path.cwd()),
                                     "marks": [{"phase": "0 brief", "t": now_iso()}]}))
        print(f"megamoind-run: {run} role=main\nstate: {state}")
    elif args.cmd == "mark":
        state = json.loads(Path(args.state).read_text())
        state["marks"].append({"phase": args.phase, "t": now_iso()})
        Path(args.state).write_text(json.dumps(state))
    elif args.cmd == "collect":
        run = collect(args.state)
        log = Path(args.log)
        log.parent.mkdir(parents=True, exist_ok=True)
        with log.open("a") as f:
            f.write(json.dumps(run) + "\n")
        for a in run["agents"]:
            print(f"{a['role']:14} {a['kind']:6} {a['seconds'] / 60:5.1f} min  peak {a['peak_context'] / 1000:4.0f}k  "
                  f"cache read {a['cache_read'] / 1e6:5.1f}M  output {a['output'] / 1000:5.0f}k")
        for p in run["phases"]:
            print(f"  {p['phase']:12} {working_seconds(p) / 60:5.1f} min  cache read {p['cache_read'] / 1e6:5.1f}M")
    else:
        text = report(args.log, args.baseline, min_runs=args.min_runs)
        if text is None:
            return 3
        print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
