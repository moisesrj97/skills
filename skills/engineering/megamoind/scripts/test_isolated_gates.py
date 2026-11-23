import io
import json
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import isolated_gates  # noqa: E402
from test_preflight import git  # noqa: E402


def package(root, path, name, deps=(), scripts=None):
    (root / path).mkdir(parents=True, exist_ok=True)
    (root / path / "package.json").write_text(json.dumps(
        {"name": name, "dependencies": {d: "workspace:*" for d in deps}, "scripts": scripts or {}}))


class BuildOrder(unittest.TestCase):
    def test_builds_the_touched_packages_dependencies_transitively_dependencies_first(self):
        root = Path(tempfile.mkdtemp())
        package(root, "packages/contracts", "@x/contracts")
        package(root, "packages/commons", "@x/commons", deps=["@x/contracts"])
        package(root, "packages/unused", "@x/unused")
        package(root, "apps/web", "@x/web", deps=["@x/commons", "react"])
        package(root, "apps/web/node_modules/@x/stale", "@x/stale")
        packages = isolated_gates.workspace_packages(root)
        self.assertNotIn("@x/stale", packages)
        self.assertEqual(isolated_gates.build_order(packages, [root / "apps/web"]), ["@x/contracts", "@x/commons"])


class EndToEnd(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        root = self.root
        (root / ".gitignore").write_text(".env*\nnode_modules\nbuild\n")
        package(root, ".", "monorepo")
        package(root, "packages/lib", "@x/lib", scripts={"build": "mkdir -p build && cp src.txt build/out.txt"})
        (root / "packages/lib/src.txt").write_text("base")
        package(root, "apps/web", "@x/web", deps=["@x/lib"])
        (root / "apps/web/index.txt").write_text("base")
        git(root, "init", "-q", "-b", "main")
        git(root, "add", "-A")
        git(root, "commit", "-qm", "base")
        git(root, "switch", "-qc", "feature")
        (root / "apps/web/index.txt").write_text("feature")
        git(root, "commit", "-qam", "feature")
        (root / "packages/lib/src.txt").write_text("another branch's change")
        (root / ".env.test").write_text("KEY=1")

    def run_gates(self, *gates):
        out = io.StringIO()
        with redirect_stdout(out), redirect_stderr(io.StringIO()):
            code = isolated_gates.main(["feature", "--base", "main", "--repo", str(self.root),
                                        *[a for g in gates for a in ("--gate", g)]])
        return code, out.getvalue()

    def test_gates_see_the_branch_alone_with_dependencies_built_from_the_copy_and_env_files(self):
        code, out = self.run_gates("grep -qx feature apps/web/index.txt",
                                   "grep -qx base packages/lib/build/out.txt",
                                   "test -f .env.test")
        self.assertEqual((code, out.count("PASS")), (0, 3), out)
        worktrees = subprocess.run(["git", "-C", str(self.root), "worktree", "list"], capture_output=True, text=True)
        self.assertEqual(len(worktrees.stdout.splitlines()), 1)

    def test_a_failing_gate_exits_1_and_names_its_code(self):
        code, out = self.run_gates("true", "exit 3")
        self.assertEqual(code, 1)
        self.assertIn("FAIL (3): exit 3", out)


if __name__ == "__main__":
    unittest.main()
