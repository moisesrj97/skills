import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import preflight  # noqa: E402


def git(repo, *args):
    subprocess.run(["git", "-C", str(repo), "-c", "user.name=t", "-c", "user.email=t@example.test", *args],
                   check=True, capture_output=True)


class TouchedPackages(unittest.TestCase):
    def test_maps_changed_files_to_their_nearest_package_and_its_gate_scripts(self):
        root = Path(tempfile.mkdtemp())
        (root / "package.json").write_text(json.dumps({"scripts": {"ci": "turbo ci", "dev": "vite"}}))
        (root / "yarn.lock").write_text("")
        for pkg in ("apps/web", "packages/ui"):
            (root / pkg / "src").mkdir(parents=True)
            (root / pkg / "package.json").write_text(json.dumps(
                {"scripts": {"ci:lint": "biome", "check-types": "tsc", "test-unit": "vitest", "start": "node ."}}))
            (root / pkg / "src/a.ts").write_text("1")
        (root / "lang").mkdir()
        (root / "lang/package.json").write_text(json.dumps({"scripts": {"test": "node --test"}}))
        git(root, "init", "-q", "-b", "main")
        git(root, "add", "-A")
        git(root, "commit", "-qm", "base")
        git(root, "switch", "-qc", "feature")
        (root / "apps/web/src/a.ts").write_text("2")
        git(root, "commit", "-qam", "change")

        (root / "lang/café.ts").write_text("1")
        git(root, "add", "-A")
        git(root, "commit", "-qm", "unicode")
        git(root, "mv", "packages/ui/src/a.ts", "apps/web/src/moved.ts")
        git(root, "commit", "-qm", "move")
        touched = preflight.touched_packages(root, "main", "feature")
        self.assertEqual(touched, {".": {"ci": "turbo ci"},
                                   "apps/web": {"ci:lint": "biome", "check-types": "tsc", "test-unit": "vitest"},
                                   "lang": {"test": "node --test"},
                                   "packages/ui": {"ci:lint": "biome", "check-types": "tsc", "test-unit": "vitest"}})
        self.assertEqual(preflight.package_manager(root), "yarn")


class IsGate(unittest.TestCase):
    def test_reading_scripts_are_gates_and_writing_ones_are_not(self):
        gates = ["ci", "ci:build", "lint", "test", "test-unit", "e2e", "check-types", "type-check", "typecheck", "tsc",
                 "format:check", "lint:format", "test:db"]
        not_gates = ["deploy:ci", "db:migrate:ci", "release:ci", "publish:ci", "typeorm:migration:run", "format",
                     "lint:fix", "test:watch", "test:update", "dev", "build", "start"]
        self.assertEqual([g for g in gates if not preflight.is_gate(g)], [])
        self.assertEqual([g for g in not_gates if preflight.is_gate(g)], [])


if __name__ == "__main__":
    unittest.main()
