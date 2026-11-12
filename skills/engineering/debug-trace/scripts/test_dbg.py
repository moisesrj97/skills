import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import dbg  # noqa: E402

TOKEN = "t3st"


class Clean(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        (self.root / "src").mkdir()
        (self.root / "node_modules").mkdir()
        self.original = "import { a } from './a';\nexport const x = a();\n"
        (self.root / "src/app.ts").write_text(
            "import { a } from './a';\n"
            "import { appendFileSync } from 'node:fs'; // CLAUDE-DBG:t3st\n"
            "export const x = a();\n"
            "appendFileSync('/tmp/claude-debug-t3st.log', `CLAUDE-DBG:t3st | x | ${JSON.stringify(x)}\\n`);"
        )
        (self.root / "src/other.ts").write_text("// CLAUDE-DBG:0ther stays: another session's token\n")
        (self.root / "node_modules/dep.js").write_text("// CLAUDE-DBG:t3st inside node_modules\n")
        (self.root / "src/coverage").mkdir()
        (self.root / "src/coverage/report.ts").write_text("x(); // CLAUDE-DBG:t3st\n")
        (self.root / "logo.png").write_bytes(b"\x89PNG\0CLAUDE-DBG:t3st")

    def test_list_skips_vendored_and_binary_files(self):
        hits = dbg.find(TOKEN, self.root)
        self.assertEqual({(p.name, n) for p, n, _ in hits}, {("app.ts", 2), ("app.ts", 4), ("report.ts", 1)})

    def test_clean_restores_the_file_byte_for_byte_and_keeps_other_tokens(self):
        dbg.trace_file(TOKEN).write_text("x")
        self.assertEqual(dbg.main(["clean", TOKEN, str(self.root)]), 0)
        self.assertEqual((self.root / "src/app.ts").read_text(), self.original.rstrip("\n") + "\n")
        self.assertIn("0ther", (self.root / "src/other.ts").read_text())
        self.assertFalse(dbg.trace_file(TOKEN).exists())


class Summary(unittest.TestCase):
    def setUp(self):
        dbg.trace_file(TOKEN).write_text(
            'CLAUDE-DBG:t3st | search | {"slot": 1, "query": "dogs"}\n'
            'CLAUDE-DBG:t3st | search | {"slot": 2, "query": "cats"}\n'
            'CLAUDE-DBG:t3st | outcome | {"slot": 1, "photo": {"id": "p9"}}\n'
            "CLAUDE-DBG:t3st | outcome | not json\n"
            'api-1  | CLAUDE-DBG:t3st | search | {"slot": 3, "query": "owls"}\n'
            "unrelated server noise\n"
        )

    def tearDown(self):
        dbg.trace_file(TOKEN).unlink(missing_ok=True)

    def test_counts_per_label_with_keys(self):
        out = dbg.summary(TOKEN)
        self.assertIn("5 events", out)
        self.assertIn("1 not one-line JSON", out)
        self.assertIn("search: 3  keys: query, slot", out)

    def test_rows_with_dotted_fields(self):
        out = dbg.summary(TOKEN, "outcome", ["slot", "photo.id"])
        self.assertIn("1 | p9", out)


class New(unittest.TestCase):
    def test_new_creates_an_empty_trace_file(self):
        out = subprocess.run([sys.executable, dbg.__file__, "new"], capture_output=True, text=True).stdout
        path = Path(out.split("trace file: ")[1].strip())
        self.assertTrue(path.exists())
        self.assertEqual(path.read_text(), "")
        path.unlink()


if __name__ == "__main__":
    unittest.main()
