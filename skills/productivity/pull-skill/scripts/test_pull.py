import io
import json
import sys
import tarfile
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import pull  # noqa: E402

SHA = "a" * 40
MIT = b"MIT License\n\nPermission is hereby granted, free of charge, to any person...\n"


def tarball(files):
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as tar:
        for rel, data in files.items():
            info = tarfile.TarInfo(f"owner-repo-{SHA[:7]}/{rel}")
            info.size = len(data)
            tar.addfile(info, io.BytesIO(data))
    return buffer.getvalue()


class FakeGh:
    def __init__(self, files, api_license=None):
        self.tar = tarball(files)
        self.api_license = api_license

    def __call__(self, endpoint, raw=False):
        if "/tarball/" in endpoint:
            return self.tar
        if endpoint.endswith("/license"):
            return {"license": {"spdx_id": self.api_license}} if self.api_license else {}
        return {"sha": SHA}


SKILL = b"---\nname: tdd\ndescription: Test first.\n---\n\nBody\n"


class Pull(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        (self.root / "skills" / "engineering" / "mine").mkdir(parents=True)
        (self.root / "skills" / "engineering" / "mine" / "SKILL.md").write_text("---\nname: mine\n---\n")
        self.real_gh = pull.gh

    def tearDown(self):
        pull.gh = self.real_gh

    def run_pull(self, files, paths, **kw):
        pull.gh = FakeGh(files, kw.pop("api_license", None))
        args = {"ref": "main", "category": "engineering", "as_name": None, "license_override": None}
        args.update(kw)
        return pull.pull("owner/repo", paths, root=self.root, **args)

    def manifest(self):
        return json.loads((self.root / "upstream.json").read_text())["skills"]

    def test_copies_the_whole_folder_and_records_the_commit(self):
        self.run_pull({"LICENSE": MIT, "skills/eng/tdd/SKILL.md": SKILL, "skills/eng/tdd/refs/a.md": b"A",
                       "skills/eng/other/SKILL.md": b"x"}, ["skills/eng/tdd"])
        dest = self.root / "skills" / "engineering" / "tdd"
        self.assertEqual((dest / "SKILL.md").read_bytes(), SKILL)
        self.assertEqual((dest / "refs" / "a.md").read_bytes(), b"A")
        self.assertFalse((self.root / "skills" / "engineering" / "other").exists())
        self.assertEqual(self.manifest()["tdd"], {
            "repo": "owner/repo", "path": "skills/eng/tdd", "ref": "main", "imported": SHA, "checked": SHA,
            "license": "MIT", "license_file": "licenses/owner-repo"})
        self.assertEqual((self.root / "licenses" / "owner-repo").read_bytes(), MIT)

    def test_takes_the_license_nearest_to_the_skill(self):
        self.run_pull({"README.md": b"r", "pstack/LICENSE": MIT, "pstack/skills/unslop/SKILL.md": SKILL},
                      ["pstack/skills/unslop"])
        self.assertEqual(self.manifest()["unslop"]["license_file"], "licenses/owner-repo-pstack")

    def test_falls_back_to_the_api_license_for_non_mit_text(self):
        self.run_pull({"LICENSE": b"Apache License 2.0", "s/tdd/SKILL.md": SKILL}, ["s/tdd"], api_license="Apache-2.0")
        self.assertEqual(self.manifest()["tdd"]["license"], "Apache-2.0")

    def test_refuses_a_skill_without_a_license(self):
        with self.assertRaisesRegex(SystemExit, "no license"):
            self.run_pull({"s/tdd/SKILL.md": SKILL}, ["s/tdd"])
        self.assertFalse((self.root / "skills" / "engineering" / "tdd").exists())

    def test_license_override_lets_a_checked_license_through(self):
        self.run_pull({"s/tdd/SKILL.md": SKILL}, ["s/tdd"], license_override="MIT")
        self.assertEqual(self.manifest()["tdd"]["license"], "MIT")
        self.assertIsNone(self.manifest()["tdd"]["license_file"])

    def test_renames_the_skill_and_its_frontmatter(self):
        self.run_pull({"LICENSE": MIT, "s/tdd/SKILL.md": SKILL}, ["s/tdd"], as_name="test-first")
        text = (self.root / "skills" / "engineering" / "test-first" / "SKILL.md").read_text()
        self.assertIn("name: test-first\n", text)
        self.assertEqual(self.manifest()["test-first"]["path"], "s/tdd")

    def test_refuses_a_name_already_taken_and_writes_nothing(self):
        files = {"LICENSE": MIT, "s/ok/SKILL.md": SKILL, "s/mine/SKILL.md": SKILL}
        with self.assertRaisesRegex(SystemExit, "mine already exists"):
            self.run_pull(files, ["s/ok", "s/mine"])
        self.assertFalse((self.root / "skills" / "engineering" / "ok").exists())
        self.assertFalse((self.root / "upstream.json").exists())

    def test_refuses_a_path_without_skill_md(self):
        with self.assertRaisesRegex(SystemExit, "no SKILL.md"):
            self.run_pull({"LICENSE": MIT, "s/tdd/README.md": b"x"}, ["s/tdd"])

    def test_skips_entries_escaping_the_repo(self):
        files = pull.read_tarball(tarball({"../evil": b"x", "s/a": b"y"}))
        self.assertEqual(files, {"s/a": b"y"})


if __name__ == "__main__":
    unittest.main()
