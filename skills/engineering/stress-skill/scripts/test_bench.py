import json
import os
import stat
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import bench  # noqa: E402

# Replies to each stream-json user message with one assistant text and a result, like `claude -p` does.
FAKE_CLAUDE = """#!/usr/bin/env python3
import json, os, sys
for line in sys.stdin:
    text = json.loads(line)["message"]["content"]
    reply = f"heard {text} home={os.environ.get('FAKE_HOME', '')}"
    print(json.dumps({"type": "assistant", "message": {"content": [{"type": "text", "text": reply}]}}), flush=True)
    print(json.dumps({"type": "result", "result": reply}), flush=True)
"""


class Run(unittest.TestCase):
    def setUp(self):
        self.base = Path(tempfile.mkdtemp())
        bin_dir = self.base / "bin"
        bin_dir.mkdir()
        fake = bin_dir / "claude"
        fake.write_text(FAKE_CLAUDE)
        fake.chmod(fake.stat().st_mode | stat.S_IEXEC)
        self.old_path = os.environ["PATH"]
        os.environ["PATH"] = f"{bin_dir}:{self.old_path}"
        self.out = self.base / "out"

    def tearDown(self):
        os.environ["PATH"] = self.old_path

    def run_case(self, case):
        return bench.run_one(case, self.base, None, None, self.out, 1)

    def test_single_prompt_scores_the_final_reply(self):
        result = self.run_case({"id": "one", "prompt": "hi",
                                "checks": [{"id": "reply", "regex": "^heard hi"}]})
        self.assertEqual(result["failed"], [])

    def test_turns_are_sent_in_order_and_final_is_the_last_reply(self):
        case = {"id": "multi", "turns": ["first", "second", "third"], "checks": [
            {"id": "final", "regex": "^heard third"},
            {"id": "order", "regex": r"USER first.*heard first.*USER second.*heard second.*USER third", "in": "transcript"},
        ]}
        result = self.run_case(case)
        self.assertEqual(result["failed"], [])

    def test_env_expands_bench_repo(self):
        case = {"id": "env", "prompt": "x", "env": {"FAKE_HOME": "$BENCH_REPO/home"}, "checks": []}
        result = self.run_case(case)
        self.assertIn(f"home={result['repo']}/home", result["final"])

    def test_with_installs_companion_skills(self):
        companion = self.base / "helper"
        companion.mkdir()
        (companion / "SKILL.md").write_text("---\nname: helper\n---\nHelp.\n")
        case = {"id": "with", "prompt": "x", "with": ["helper"],
                "checks": [{"id": "installed", "cmd": "test -f .claude/skills/helper/SKILL.md"}]}
        self.assertEqual(self.run_case(case)["failed"], [])

    def test_failed_check_is_reported(self):
        result = self.run_case({"id": "red", "prompt": "hi", "checks": [{"id": "never", "regex": "absent"}]})
        self.assertEqual(result["failed"], ["never"])


class Variant(unittest.TestCase):
    def test_dropping_a_sections_last_unit_drops_its_heading(self):
        src = Path(tempfile.mkdtemp())
        (src / "SKILL.md").write_text("---\nname: x\n---\n\nIntro.\n\n## A\n\nKeep.\n\n## B\n\nGone.\n")
        _, units, _ = bench.split((src / "SKILL.md").read_text())
        gone = next(u["id"] for u in units if u["text"].startswith("Gone"))
        out = src / "variant"
        bench.cmd_variant(type("Args", (), {"skill_dir": str(src), "drop": gone, "out": str(out)}))
        text = (out / "SKILL.md").read_text()
        self.assertIn("## A", text)
        self.assertNotIn("## B", text)
        self.assertNotIn("Gone", text)


if __name__ == "__main__":
    unittest.main()
