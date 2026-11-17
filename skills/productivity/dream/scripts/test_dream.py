import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

SCRIPT = Path(__file__).parent / "dream.py"
OLD = time.time() - 5 * 86400


def run(*args, env_extra=None):
    env = {**os.environ, "CLAUDE_CODE_SESSION_ID": "current", "CLAUDE_PID": str(os.getpid()), **(env_extra or {})}
    out = subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True, text=True, env=env)
    return out.returncode, out.stdout


class Start(unittest.TestCase):
    def setUp(self):
        self.project = Path(tempfile.mkdtemp())
        self.memory = self.project / "memory"
        self.memory.mkdir()
        self.lock = self.memory / ".consolidate-lock"
        for name, mtime in [("before", OLD - 60), ("after", time.time()), ("current", time.time())]:
            path = self.project / f"{name}.jsonl"
            path.write_text("")
            os.utime(path, (mtime, mtime))

    def stamp_lock(self, content, mtime):
        self.lock.write_text(content)
        os.utime(self.lock, (mtime, mtime))

    def test_lists_sessions_since_the_lock_without_the_current_one_and_stamps_it(self):
        self.stamp_lock("", OLD)
        code, out = run("start", "--memory-dir", str(self.memory))
        report = json.loads(out)
        self.assertEqual(code, 0)
        self.assertEqual([s["id"] for s in report["sessions"]], ["after"])
        self.assertEqual(report["previous_lock_mtime"], OLD)
        self.assertEqual(self.lock.read_text(), str(os.getpid()))
        self.assertGreater(self.lock.stat().st_mtime, OLD)

    def test_without_a_lock_every_session_counts(self):
        code, out = run("start", "--memory-dir", str(self.memory))
        self.assertEqual(code, 0)
        self.assertEqual(len(json.loads(out)["sessions"]), 2)

    def test_refuses_a_recent_lock_held_by_another_live_process(self):
        self.stamp_lock("1", time.time())
        code, out = run("start", "--memory-dir", str(self.memory))
        self.assertEqual(code, 1)
        self.assertIn("another dream", json.loads(out)["error"])

    def test_takes_over_a_stale_lock(self):
        self.stamp_lock("1", OLD)
        code, _ = run("start", "--memory-dir", str(self.memory))
        self.assertEqual(code, 0)

    def test_rollback_restores_the_previous_mtime_or_removes_the_lock(self):
        self.stamp_lock("", OLD)
        run("start", "--memory-dir", str(self.memory))
        run("rollback", "--memory-dir", str(self.memory), "--to", str(OLD))
        self.assertAlmostEqual(self.lock.stat().st_mtime, OLD, delta=1)
        run("rollback", "--memory-dir", str(self.memory), "--to", "0")
        self.assertFalse(self.lock.exists())


class Digest(unittest.TestCase):
    def test_keeps_user_and_claude_text_and_answers_and_drops_tool_traffic(self):
        project = Path(tempfile.mkdtemp())
        (project / "memory").mkdir()
        records = [
            {"type": "user", "timestamp": "2026-11-17T10:00:00Z", "message": {"content": "fix the build"}},
            {"type": "user", "message": {"content": "<system-reminder>noise</system-reminder>"}},
            {"type": "user", "isMeta": True, "message": {"content": "meta"}},
            {"type": "assistant", "message": {"content": [{"type": "tool_use", "name": "Bash"}]}},
            {"type": "assistant", "isSidechain": True, "message": {"content": [{"type": "text", "text": "subagent"}]}},
            {"type": "assistant", "message": {"content": [{"type": "text", "text": "Fixed it."}]}},
            {"type": "user", "toolUseResult": {"answers": {"Which branch?": "main"}}, "message": {"content": [{"type": "tool_result"}]}},
        ]
        (project / "s1.jsonl").write_text("\n".join(json.dumps(r) for r in records) + "\nnot json\n")
        code, out = run("digest", "s1", "--memory-dir", str(project / "memory"))
        self.assertEqual(code, 0)
        self.assertEqual(out.splitlines(), [
            "[2026-11-17T10:00] USER fix the build",
            "[] CLAUDE Fixed it.",
            "[] ANSWER Which branch? -> main",
        ])


if __name__ == "__main__":
    unittest.main()
