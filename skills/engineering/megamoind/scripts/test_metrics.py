import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import metrics  # noqa: E402

TAG = "megamoind-run: PD-1-20261117100000"


def at(second):
    return f"2026-11-17T10:{second // 60:02d}:{second % 60:02d}.000Z"


def assistant(second, msg_id, read, write, out, *, model="claude-opus-5-5", tool=None, text=""):
    content = [{"type": "text", "text": text}] if text else []
    if tool:
        content.append({"type": "tool_use", "id": tool[0], "name": tool[1], "input": tool[2] if len(tool) > 2 else {}})
    usage = {"input_tokens": 0, "cache_read_input_tokens": read, "cache_creation_input_tokens": write, "output_tokens": out}
    return {"type": "assistant", "timestamp": at(second),
            "message": {"id": msg_id, "model": model, "content": content, "usage": usage}}


def user(second, text=None, result_for=None, result=""):
    if result_for:
        content = [{"type": "tool_result", "tool_use_id": result_for, "content": result}]
    else:
        content = [{"type": "text", "text": text}]
    return {"type": "user", "timestamp": at(second), "message": {"role": "user", "content": content}}


def write_jsonl(path, records):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(r) for r in records) + "\n")


class Collect(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        self.projects = self.root / "projects"
        self.codex = self.root / "codex"
        self.state = self.root / "PD-1-metrics.json"
        self.state.write_text(json.dumps({
            "run": "PD-1-20261117100000", "ticket": "PD-1", "repo": "/repo",
            "marks": [{"phase": "0 brief", "t": at(0)}, {"phase": "2 implement", "t": at(100)}],
        }))

    def collect(self):
        return metrics.collect(self.state, self.projects, self.codex, now=at(300))

    def test_main_agent_phases_split_time_and_tokens_at_the_marks(self):
        write_jsonl(self.projects / "repo/main.jsonl", [
            user(0, text="unrelated earlier work"),
            assistant(1, "m0", 900, 0, 9),
            user(5, result_for="t0", result=TAG + " role=main"),
            assistant(10, "m1", 1000, 50, 10, tool=("t1", "Bash")),
            user(40, result_for="t1"),
            assistant(60, "m2", 2000, 100, 20),
            assistant(150, "m3", 5000, 200, 30, tool=("t2", "Bash")),
            user(200, result_for="t2"),
        ])
        run = self.collect()
        main = run["agents"][0]
        self.assertEqual(main["role"], "main")
        brief, implement = run["phases"]
        self.assertEqual((brief["phase"], brief["seconds"]), ("0 brief", 100))
        self.assertEqual(brief["cache_read"], 3000)
        self.assertEqual(implement["cache_read"], 5000)
        self.assertEqual(implement["output"], 30)
        self.assertEqual(main["peak_context"], 5200)
        self.assertEqual(main["cache_read"], 8000)

    def test_each_step_keeps_its_own_peak_context(self):
        write_jsonl(self.projects / "repo/main.jsonl", [
            user(1, result_for="t0", result=TAG + " role=main"),
            assistant(10, "m1", 20_000, 0, 1),
            assistant(150, "m2", 100_000, 0, 1),
        ])
        brief, implement = self.collect()["phases"]
        self.assertEqual((brief["peak_context"], implement["peak_context"]), (20_000, 100_000))

    def test_tokens_stay_split_by_model(self):
        write_jsonl(self.projects / "repo/main.jsonl", [
            user(1, result_for="t0", result=TAG + " role=main"),
            assistant(10, "m1", 0, 0, 10, model="claude-opus-5-5"),
            assistant(20, "m2", 0, 0, 20, model="claude-sonnet-5-5"),
        ])
        by_model = self.collect()["agents"][0]["by_model"]
        self.assertEqual((by_model["claude-opus-5-5"]["output"], by_model["claude-sonnet-5-5"]["output"]), (10, 20))

    def test_a_question_answered_beside_other_tool_results_still_counts_as_waiting(self):
        write_jsonl(self.projects / "repo/main.jsonl", [
            user(1, result_for="t0", result=TAG + " role=main"),
            {**assistant(10, "m1", 10, 0, 1, tool=("read", "Read")), "message": {**assistant(10, "m1", 10, 0, 1)["message"], "content": [
                {"type": "tool_use", "id": "read", "name": "Read", "input": {}},
                {"type": "tool_use", "id": "ask", "name": "AskUserQuestion", "input": {}}]}},
            {"type": "user", "timestamp": at(50), "message": {"role": "user", "content": [
                {"type": "tool_result", "tool_use_id": "read", "content": ""},
                {"type": "tool_result", "tool_use_id": "ask", "content": "yes"}]}},
        ])
        self.assertEqual(self.collect()["phases"][0]["human_seconds"], 40)

    def test_file_reads_are_counted_apart_from_other_tool_output(self):
        write_jsonl(self.projects / "repo/main.jsonl", [
            user(1, result_for="t0", result=TAG + " role=main"),
            assistant(10, "m1", 0, 0, 1, tool=("cat", "Bash", {"command": "cd /repo && cat src/a.ts"})),
            user(11, result_for="cat", result="x" * 100),
            assistant(12, "m2", 0, 0, 1, tool=("test", "Bash", {"command": "heavy -- yarn test"})),
            user(13, result_for="test", result="y" * 50),
            assistant(14, "m3", 0, 0, 1, tool=("read", "Read", {"file_path": "/repo/b.ts"})),
            user(15, result_for="read", result="z" * 30),
            assistant(16, "m4", 0, 0, 1, tool=("show", "Bash", {"command": "git show master:src/c.ts | sed -n '1,40p'"})),
            user(17, result_for="show", result="w" * 20),
        ])
        main = self.collect()["agents"][0]
        self.assertEqual((main["read_chars"], main["result_chars"]), (150, 200))

    def test_finds_the_main_session_transcript(self):
        write_jsonl(self.projects / "repo/child.jsonl", [user(1, text=TAG + " role=retro")])
        write_jsonl(self.projects / "repo/main.jsonl", [user(1, result_for="t0", result=TAG + " role=main")])
        self.assertEqual(metrics.main_session(self.state, self.projects), self.projects / "repo/main.jsonl")

    def test_a_streamed_message_counts_its_usage_once(self):
        write_jsonl(self.projects / "repo/main.jsonl", [
            user(1, result_for="t0", result=TAG + " role=main"),
            assistant(2, "m1", 1000, 0, 10, text="thinking"),
            assistant(3, "m1", 1000, 0, 10, tool=("t1", "Read")),
        ])
        self.assertEqual(self.collect()["agents"][0]["cache_read"], 1000)

    def test_time_waiting_on_the_human_is_left_out_of_the_phase(self):
        write_jsonl(self.projects / "repo/main.jsonl", [
            user(1, result_for="t0", result=TAG + " role=main"),
            assistant(10, "m1", 10, 0, 1, text="Which option?"),
            user(70, text="the first"),
            assistant(80, "m2", 10, 0, 1, tool=("t1", "AskUserQuestion")),
            user(95, result_for="t1"),
        ])
        brief = self.collect()["phases"][0]
        self.assertEqual(brief["seconds"], 100)
        self.assertEqual(brief["human_seconds"], 75)

    def test_children_and_codex_reviewers_carrying_the_tag_join_the_run(self):
        write_jsonl(self.projects / "repo/main.jsonl", [user(1, result_for="t0", result=TAG + " role=main")])
        write_jsonl(self.projects / "repo/child.jsonl", [
            user(110, text=f"Implement the ticket.\n{TAG} role=implementer"),
            assistant(120, "c1", 4000, 300, 40, tool=("x", "Edit")),
            user(130, result_for="x"),
        ])
        write_jsonl(self.projects / "other/unrelated.jsonl", [user(110, text="no tag"), assistant(120, "u1", 9, 9, 9)])
        write_jsonl(self.codex / "2026/11/17/rollout.jsonl", [
            {"timestamp": at(150), "type": "event_msg", "payload": {"type": "thread_settings_applied", "thread_settings": {"model": "gpt-6.1-sol"}}},
            {"timestamp": at(151), "type": "response_item", "payload": {"type": "message", "role": "user", "content": [{"type": "input_text", "text": f"Review.\n{TAG} role=review-code"}]}},
            {"timestamp": at(160), "type": "event_msg", "payload": {"type": "token_count", "info": {
                "total_token_usage": {"input_tokens": 500, "cached_input_tokens": 300, "output_tokens": 20},
                "last_token_usage": {"input_tokens": 500}}}},
            {"timestamp": at(190), "type": "event_msg", "payload": {"type": "token_count", "info": {
                "total_token_usage": {"input_tokens": 1500, "cached_input_tokens": 1100, "output_tokens": 60},
                "last_token_usage": {"input_tokens": 1000}}}},
        ])
        agents = {a["role"]: a for a in self.collect()["agents"]}
        self.assertEqual(set(agents), {"main", "implementer", "review-code"})
        self.assertEqual(agents["implementer"]["cache_read"], 4000)
        self.assertEqual(agents["implementer"]["seconds"], 20)
        codex = agents["review-code"]
        self.assertEqual((codex["kind"], codex["models"]), ("codex", ["gpt-6.1-sol"]))
        self.assertEqual((codex["cache_read"], codex["input"], codex["output"]), (1100, 400, 60))
        self.assertEqual(codex["peak_context"], 1000)

    def test_a_step_counts_the_tokens_of_every_claude_agent_working_in_it(self):
        write_jsonl(self.projects / "repo/main.jsonl", [user(1, result_for="t0", result=TAG + " role=main"), assistant(150, "m1", 100, 0, 1)])
        write_jsonl(self.projects / "repo/child.jsonl", [user(110, text=f"Implement.\n{TAG} role=implementer"), assistant(120, "c1", 4000, 0, 40)])
        implement = self.collect()["phases"][1]
        self.assertEqual((implement["cache_read"], implement["turns"]), (4100, 2))

    def test_a_step_counts_the_codex_reviewers_working_in_it(self):
        write_jsonl(self.projects / "repo/main.jsonl", [user(1, result_for="t0", result=TAG + " role=main")])
        write_jsonl(self.codex / "2026/11/17/rollout.jsonl", [
            {"timestamp": at(110), "type": "response_item", "payload": {"type": "message", "role": "user", "content": [{"type": "input_text", "text": f"{TAG} role=review-code"}]}},
            {"timestamp": at(120), "type": "event_msg", "payload": {"type": "token_count", "info": {
                "total_token_usage": {"input_tokens": 1000, "cached_input_tokens": 300, "output_tokens": 50},
                "last_token_usage": {"input_tokens": 1000, "cached_input_tokens": 300, "output_tokens": 50}}}},
        ])
        implement = self.collect()["phases"][1]
        self.assertEqual((implement["cache_read"], implement["input"], implement["output"], implement["peak_context"]), (300, 700, 50, 1000))

    def test_a_subagent_transcript_counts_even_though_it_is_a_sidechain(self):
        write_jsonl(self.projects / "repo/main.jsonl", [user(1, result_for="t0", result=TAG + " role=main")])
        records = [user(110, text=f"Verify the flows.\n{TAG} role=verifier"), assistant(120, "v1", 700, 0, 7)]
        write_jsonl(self.projects / "repo/main/subagents/agent-1.jsonl", [{**r, "isSidechain": True} for r in records])
        agents = {a["role"]: a for a in self.collect()["agents"]}
        self.assertEqual(agents["verifier"]["cache_read"], 700)


class Skill(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        self.state = self.root / "PD-1-metrics.json"

    def state_after(self, *argv):
        with contextlib.redirect_stdout(io.StringIO()):
            metrics.main(list(argv))
        return json.loads(self.state.read_text())

    def test_a_direct_minimoi_run_starts_with_its_skill(self):
        state = self.state_after("start", "PD-1", "--dir", str(self.root), "--skill", "minimoi")
        self.assertEqual(state["skill"], "minimoi")

    def test_a_run_started_without_a_skill_is_megamoind(self):
        self.assertEqual(self.state_after("start", "PD-1", "--dir", str(self.root))["skill"], "megamoind")

    def test_a_handoff_marks_the_run_as_minimoi_from_then_on(self):
        self.state_after("start", "PD-1", "--dir", str(self.root))
        state = self.state_after("mark", str(self.state), "0 handoff", "--skill", "minimoi")
        self.assertEqual((state["skill"], state["marks"][-1]["phase"]), ("minimoi", "0 handoff"))

    def test_a_plain_mark_keeps_the_skill(self):
        self.state_after("start", "PD-1", "--dir", str(self.root), "--skill", "minimoi")
        self.assertEqual(self.state_after("mark", str(self.state), "2 implement")["skill"], "minimoi")

    def test_collect_copies_the_skill_into_the_record(self):
        self.state.write_text(json.dumps({"run": "PD-1-20261117100000", "ticket": "PD-1", "skill": "minimoi",
                                          "marks": [{"phase": "0 brief", "t": at(0)}]}))
        self.assertEqual(metrics.collect(self.state, self.root / "p", self.root / "c", now=at(10))["skill"], "minimoi")

    def test_collect_reads_a_state_from_before_the_field_as_megamoind(self):
        self.state.write_text(json.dumps({"run": "PD-1-20261117100000", "ticket": "PD-1",
                                          "marks": [{"phase": "0 brief", "t": at(0)}]}))
        self.assertEqual(metrics.collect(self.state, self.root / "p", self.root / "c", now=at(10))["skill"], "megamoind")


class Phases(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        self.state = self.root / "PD-1-metrics.json"
        with contextlib.redirect_stdout(io.StringIO()):
            metrics.main(["start", "PD-1", "--dir", str(self.root)])

    def mark(self, *argv):
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()) as err:
            code = metrics.main(["mark", str(self.state), *argv])
        return code, err.getvalue()

    def phases(self):
        return [m["phase"] for m in json.loads(self.state.read_text())["marks"]]

    def test_every_megamoind_step_can_be_marked(self):
        for phase in metrics.PHASES["megamoind"]:
            self.assertEqual(self.mark(phase)[0], 0, phase)

    def test_a_phase_outside_the_list_is_rejected_naming_the_valid_ones(self):
        code, err = self.mark("6 comment cleanup")
        self.assertNotEqual(code, 0)
        self.assertIn("6 comments", err)
        self.assertEqual(self.phases(), ["0 brief"])

    def test_a_minimoi_run_checks_against_its_own_steps(self):
        self.assertEqual(self.mark("0 handoff", "--skill", "minimoi")[0], 0)
        self.assertEqual(self.mark("4 evidence")[0], 0)
        self.assertNotEqual(self.mark("5 verify")[0], 0)

    def test_an_escalation_checks_against_the_skill_it_moves_to(self):
        self.mark("0 handoff", "--skill", "minimoi")
        self.assertEqual(self.mark("2 implement", "--skill", "megamoind")[0], 0)
        self.assertEqual(self.mark("5 verify")[0], 0)


class Verify(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        self.state = self.root / "PD-1-metrics.json"
        self.log = self.root / "metrics.jsonl"
        self.state.write_text(json.dumps({"run": "PD-1-20261117100000", "ticket": "PD-1", "marks": [{"phase": "0 brief", "t": at(0)}]}))

    def collected(self, *flags):
        with contextlib.redirect_stdout(io.StringIO()):
            metrics.main(["collect", str(self.state), "--log", str(self.log), *flags])
        return json.loads(self.log.read_text().splitlines()[-1])

    def test_collect_records_the_verify_outcome(self):
        run = self.collected("--flows", "6", "--failures", "2", "--unverified", "1")
        self.assertEqual(run["verify"], {"flows": 6, "failures": 2, "unverified": 1})

    def test_a_run_without_verify_records_none(self):
        self.assertNotIn("verify", self.collected())


class Report(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        self.log = self.root / "metrics.jsonl"
        self.seen = self.root / "last-report.json"

    def run_with(self, minutes):
        return {"run": f"r{minutes}", "end": at(0), "phases": [{"phase": "2 implement", "seconds": minutes * 60, "human_seconds": 0,
                "cache_read": 0, "cache_write": 0, "input": 0, "output": 0, "turns": 1}],
                "agents": [{"role": "main", "kind": "claude", "models": ["claude-opus-5-5"], "seconds": minutes * 60, "cache_read": 1_000_000,
                            "cache_write": 0, "input": 0, "output": 0, "peak_context": 100_000, "turns": 1}]}

    def test_says_nothing_until_enough_new_runs(self):
        self.log.write_text(json.dumps(self.run_with(10)) + "\n")
        self.assertIsNone(metrics.report(self.log, None, self.seen, min_runs=2))
        self.log.write_text("".join(json.dumps(self.run_with(m)) + "\n" for m in (10, 20, 30)))
        text = metrics.report(self.log, None, self.seen, min_runs=2)
        self.assertIn("3 runs", text)
        self.assertIn("run minutes: median 20", text)
        self.assertIsNone(metrics.report(self.log, None, self.seen, min_runs=2))

    def test_a_run_collected_twice_counts_once_with_its_latest_figures(self):
        self.log.write_text("".join(json.dumps(self.run_with(m)) + "\n" for m in (10, 20)).replace('"r20"', '"r10"'))
        self.assertIsNone(metrics.report(self.log, None, self.seen, min_runs=2))
        text = metrics.report(self.log, None, self.seen, min_runs=1)
        self.assertIn("1 runs", text)
        self.assertIn("run minutes: median 20", text)

    def test_reports_only_the_runs_of_the_skill_asked_for(self):
        runs = [self.run_with(10), {**self.run_with(20), "skill": "megamoind"}, {**self.run_with(40), "skill": "minimoi"}]
        self.log.write_text("".join(json.dumps(r) + "\n" for r in runs))
        text = metrics.report(self.log, None, self.seen, min_runs=1)
        self.assertIn("megamoind metrics: 2 runs", text)
        self.assertIn("run minutes: median 15", text)
        text = metrics.report(self.log, None, self.seen, min_runs=1, skill="minimoi")
        self.assertIn("minimoi metrics: 1 runs", text)
        self.assertIn("run minutes: median 40", text)

    def test_compares_the_verifier_by_model(self):
        def run(name, model, read, failures):
            r = self.run_with(10)
            r["run"] = name
            r["agents"].append({**r["agents"][0], "role": "verifier", "models": [model], "cache_read": read})
            r["verify"] = {"flows": 5, "failures": failures, "unverified": 0}
            return r
        runs = [run("a", "claude-opus-5-5", 4_000_000, 2), run("b", "claude-opus-5-5", 6_000_000, 2),
                run("c", "claude-sonnet-5-5", 3_000_000, 1), self.run_with(30)]
        self.log.write_text("".join(json.dumps(r) + "\n" for r in runs))
        text = metrics.report(self.log, None, self.seen, min_runs=1)
        self.assertIn("claude-opus-5-5: 2 runs, cache read median 5.0M, failures found median 2, unverified median 0", text)
        self.assertIn("claude-sonnet-5-5: 1 runs, cache read median 3.0M, failures found median 1, unverified median 0", text)

    def test_compares_each_role_by_model(self):
        def run(name, model, read, write, out):
            r = self.run_with(10)
            r["run"] = name
            r["agents"].append({**r["agents"][0], "role": "finisher", "models": [model], "cache_read": read, "cache_write": write,
                                "output": out, "turns": 40, "peak_context": 150_000, "read_chars": 30, "result_chars": 100})
            return r
        runs = [run("a", "claude-opus-5-5", 10_000_000, 0, 0), run("b", "claude-opus-5-5", 20_000_000, 0, 0),
                run("c", "claude-sonnet-5-5", 5_000_000, 400_000, 100_000)]
        self.log.write_text("".join(json.dumps(r) + "\n" for r in runs))
        text = metrics.report(self.log, None, self.seen, min_runs=1)
        self.assertIn("finisher       claude-opus-5-5      2 runs  cost 1.5M  cache read 15.0M  turns 40  peak 150k  reads 30%", text)
        self.assertIn("finisher       claude-sonnet-5-5    1 runs  cost 1.5M  cache read 5.0M  turns 40  peak 150k  reads 30%", text)

    def test_an_empty_log_says_nothing_whatever_the_threshold(self):
        self.log.write_text("")
        self.assertIsNone(metrics.report(self.log, None, self.seen, min_runs=0))


if __name__ == "__main__":
    unittest.main()
