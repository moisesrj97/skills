import json
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import sweep  # noqa: E402

NOW = time.time()
HOUR = 3600


def transcript(cwd, prompt, meta_first=False):
    lines = []
    if meta_first:
        lines.append({"type": "user", "isMeta": True, "cwd": cwd, "message": {"content": "skill body"}})
    lines.append({"type": "user", "cwd": cwd, "message": {"content": [{"type": "text", "text": prompt}]}})
    lines.append({"type": "assistant", "cwd": cwd, "message": {"content": [{"type": "text", "text": "done"}]}})
    return "\n".join(json.dumps(line) for line in lines) + "\n"


class Candidates(unittest.TestCase):
    def setUp(self):
        base = Path(tempfile.mkdtemp())
        self.projects, self.retros, self.out = base / "projects", base / "retros", base / "out"
        self.ledger = base / "retro-sweep.json"
        (self.retros / "shop").mkdir(parents=True)

    def session(self, name, hours_ago, cwd="/code/shop", prompt="fix the cart", **kw):
        folder = self.projects / "-code-shop"
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / f"{name}.jsonl"
        path.write_text(transcript(cwd, prompt, **kw))
        os.utime(path, (NOW - hours_ago * HOUR, NOW - hours_ago * HOUR))
        return str(path)

    def run_candidates(self, **kw):
        return sweep.candidates(self.out, projects=self.projects, retros=self.retros, ledger=self.ledger, now=NOW, **kw)

    def test_leaves_out_active_old_temp_self_and_reviewed_sessions(self):
        keep = self.session("keep", 10, meta_first=True)
        self.session("active", 1)
        self.session("old", 24 * 5)
        self.session("eval", 10, cwd="/private/var/folders/tr/T/megamoind-entry-q91")
        self.session("sweep", 10, prompt="<command-name>/retro-sweep</command-name> run it")
        reviewed = self.session("reviewed", 10)
        (self.retros / "shop" / "2026-11-12-cart.md").write_text(f"---\ndate: 2026-11-12\nsession: {reviewed}\n---\n")
        found = self.run_candidates()
        self.assertEqual([c["session"] for c in found], [keep])
        self.assertEqual((found[0]["cwd"], found[0]["first_prompt"], found[0]["triage"]), ("/code/shop", "fix the cart", None))
        self.assertIn("USER: fix the cart", Path(found[0]["condensed"]).read_text())

    def test_pending_friction_first_unlimited_then_oldest_new_ones_up_to_the_limit(self):
        newer, older = self.session("newer", 5), self.session("older", 30)
        pending = self.session("pending", 40)
        clean = self.session("clean", 20)
        sweep.record({pending: {"verdict": "friction", "why": "retried"}, clean: {"verdict": "clean"}}, self.ledger)
        found = self.run_candidates(limit=1)
        self.assertEqual([(c["session"], c["triage"]) for c in found], [(pending, "friction"), (older, None)])
        self.assertNotIn(newer, [c["session"] for c in found])

    def test_record_refuses_an_unknown_verdict_and_writes_nothing(self):
        with self.assertRaises(ValueError):
            sweep.record({"a.jsonl": {"verdict": "clean"}, "b.jsonl": {"verdict": "maybe"}}, self.ledger)
        self.assertFalse(self.ledger.exists())


class SharedCondenser(unittest.TestCase):
    def test_both_skills_carry_the_same_condenser(self):
        twin = Path(__file__).parents[2] / "retro-with-docs" / "scripts" / "condense_session.py"
        if not twin.exists():
            self.skipTest("retro-with-docs is not installed beside retro-sweep")
        self.assertEqual((Path(__file__).parent / "condense_session.py").read_text(), twin.read_text(),
                         "copy retro-with-docs/scripts/condense_session.py over this one")


if __name__ == "__main__":
    unittest.main()
