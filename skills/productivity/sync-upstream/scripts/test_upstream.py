import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import upstream  # noqa: E402

OLD, HEAD, TOUCH, OLDER = "o" * 40, "h" * 40, "t" * 40, "x" * 40
PATH = "skills/eng/tdd"


class FakeGh:
    """Answers the GitHub endpoints by prefix; `latest` is the last commit touching PATH."""

    def __init__(self, latest=TOUCH, ahead=True, files=(), commits=()):
        self.latest, self.ahead, self.files, self.commits = latest, ahead, list(files), list(commits)
        self.calls = []

    def __call__(self, endpoint):
        self.calls.append(endpoint)
        if endpoint.startswith("repos/o/r/commits?"):
            if endpoint.endswith("per_page=1"):
                return [{"sha": self.latest}] if self.latest else []
            return [{"sha": c, "commit": {"message": f"msg {c[0]}\nbody"}} for c in self.commits]
        if endpoint.startswith("repos/o/r/commits/"):
            return {"sha": HEAD}
        if endpoint == f"repos/o/r/compare/{OLD}...{self.latest}":
            return {"status": "ahead" if self.ahead else "behind"}
        if endpoint == f"repos/o/r/compare/{OLD}...{HEAD}":
            return {"files": self.files, "commits": [{"sha": c} for c in self.commits],
                    "html_url": "https://github.com/o/r/compare"}
        raise AssertionError(endpoint)


class Upstream(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        self.write({"tdd": {"repo": "o/r", "path": PATH, "ref": "main", "imported": OLD, "checked": OLD,
                            "license": "MIT", "license_file": None}})
        self.real_gh = upstream.gh

    def tearDown(self):
        upstream.gh = self.real_gh

    def write(self, skills):
        (self.root / "upstream.json").write_text(json.dumps({"skills": skills}))

    def entry(self):
        return json.loads((self.root / "upstream.json").read_text())["skills"]["tdd"]

    def check(self, **kw):
        upstream.gh = FakeGh(**kw)
        return upstream.check(root=self.root)

    def test_head_equal_to_checked_is_unchanged_without_more_calls(self):
        self.write({"tdd": {**self.entry(), "checked": HEAD}})
        self.assertEqual(self.check(), [{"name": "tdd", "status": "unchanged"}])
        self.assertEqual(len(upstream.gh.calls), 1)

    def test_no_commit_on_the_path_since_checked_advances_checked(self):
        self.assertEqual(self.check(ahead=False)[0]["status"], "unchanged")
        self.assertEqual(self.entry()["checked"], HEAD)

    def test_path_with_no_history_advances_checked(self):
        self.assertEqual(self.check(latest=None)[0]["status"], "unchanged")
        self.assertEqual(self.entry()["checked"], HEAD)

    def test_reports_only_the_files_under_the_skill(self):
        files = [{"filename": f"{PATH}/SKILL.md", "status": "modified"},
                 {"filename": "skills/eng/tdd-extra/SKILL.md", "status": "added"},
                 {"filename": "README.md", "status": "modified"}]
        [item] = self.check(files=files)
        self.assertEqual(item["status"], "changed")
        self.assertEqual(item["files"], [{"filename": f"{PATH}/SKILL.md", "status": "modified"}])
        self.assertFalse(item["truncated"])
        self.assertEqual(self.entry()["checked"], OLD)

    def test_detects_a_removed_skill(self):
        [item] = self.check(files=[{"filename": f"{PATH}/SKILL.md", "status": "removed"}])
        self.assertEqual(item["status"], "removed")

    def test_detects_a_moved_skill(self):
        files = [{"filename": "skills/new/tdd/SKILL.md", "status": "renamed", "previous_filename": f"{PATH}/SKILL.md"}]
        [item] = self.check(files=files)
        self.assertEqual((item["status"], item["moved_to"]), ("moved", "skills/new/tdd"))

    def test_flags_a_compare_at_the_file_cap(self):
        files = [{"filename": f"{PATH}/f{i}", "status": "added"} for i in range(upstream.COMPARE_FILE_CAP)]
        self.assertTrue(self.check(files=files)[0]["truncated"])

    def test_diff_lists_commits_on_the_path_and_patches(self):
        upstream.gh = FakeGh(files=[{"filename": f"{PATH}/SKILL.md", "status": "modified", "patch": "@@ -1 +1 @@"},
                                    {"filename": f"{PATH}/big.png", "status": "added"},
                                    {"filename": "other/x", "status": "modified", "patch": "nope"}],
                             commits=[TOUCH])
        out = upstream.diff("tdd", root=self.root)
        self.assertIn(f"- {TOUCH[:7]} msg t\n", out)
        self.assertIn("@@ -1 +1 @@", out)
        self.assertIn("no patch", out)
        self.assertNotIn("nope", out)

    def test_mark_records_the_sha_and_a_new_path(self):
        upstream.gh = FakeGh()
        upstream.mark("tdd", path="skills/new/tdd", root=self.root)
        self.assertEqual((self.entry()["checked"], self.entry()["path"]), (HEAD, "skills/new/tdd"))

    def test_mark_drop_stops_tracking(self):
        upstream.mark("tdd", drop=True, root=self.root)
        self.assertEqual(json.loads((self.root / "upstream.json").read_text())["skills"], {})


if __name__ == "__main__":
    unittest.main()
