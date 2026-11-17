import subprocess
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).parent / "find_comments.sh"


def git(repo, *args):
    subprocess.run(["git", "-C", repo, "-c", "user.name=t", "-c", "user.email=t@example.test", *args],
                   check=True, capture_output=True)


class FindComments(unittest.TestCase):
    def setUp(self):
        self.repo = tempfile.mkdtemp()
        git(self.repo, "init", "-q", "-b", "main")
        (Path(self.repo) / "a.ts").write_text("const a = 1;\n// old note\n")
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-qm", "base")

    def run_script(self, *args):
        return subprocess.run([str(SCRIPT), *args], cwd=self.repo, capture_output=True, text=True, check=True).stdout

    def test_lists_only_added_comment_lines_with_their_line_numbers(self):
        (Path(self.repo) / "a.ts").write_text("const a = 1;\n// old note\n// new note\nconst b = 2;\n  # hash\n")
        (Path(self.repo) / "notes.md").write_text("<!-- skipped -->\n")
        git(self.repo, "add", "-A")
        self.assertEqual(self.run_script("--staged"), "a.ts:3: // new note\na.ts:5:   # hash\n")

    def test_defaults_to_the_merge_base_with_the_default_branch(self):
        git(self.repo, "update-ref", "refs/remotes/origin/main", "HEAD")
        git(self.repo, "symbolic-ref", "refs/remotes/origin/HEAD", "refs/remotes/origin/main")
        git(self.repo, "switch", "-q", "-c", "feature")
        (Path(self.repo) / "b.ts").write_text("/* added */\n")
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-qm", "feature")
        self.assertEqual(self.run_script(), "b.ts:1: /* added */\n")


if __name__ == "__main__":
    unittest.main()
