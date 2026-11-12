import os
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import locate  # noqa: E402
import validate_retro  # noqa: E402

GOOD = textwrap.dedent("""\
    ---
    date: 2026-11-10
    project: shop
    session: /tmp/s.jsonl
    branch: ABC-1-cart
    summary: fix the cart total
    ---

    # Retro: cart total

    ## R1: The app could not start without a seeded account

    - status: open
    - severity: blocker
    - category: verification
    - kind: mechanical
    - target: scripts/seed.ts
    - evidence:
      - [12] "login failed"
      - [40] the agent skipped the browser check
    - proposal: add a seed script

    ## R2: The test command was hard to find

    - status: duplicate of shop/2026-11-01-x.md#R3
    - severity: low
    - category: navigation
    - kind: judgement
    - target: CLAUDE.md
    - evidence: [7] searched for 10 calls
    - proposal: name the test command in CLAUDE.md

    Dismissed as noise: [3] a typo the agent fixed at once
    """)


class Validate(unittest.TestCase):
    def test_a_conforming_retro_has_no_problems(self):
        self.assertEqual(validate_retro.problems(GOOD), [])

    def test_names_each_problem(self):
        bad = (GOOD.replace("- severity: blocker", "- severity: critical")
               .replace("- status: open", "- status: resolved")
               .replace("    - proposal: name the test command in CLAUDE.md\n", "")
               .replace("Dismissed as noise:", "Noise:")
               .replace("date: 2026-11-10", "date: 10/11/2026"))
        found = validate_retro.problems(bad)
        self.assertIn("R1: severity 'critical' is not one of blocker | high | medium | low", found)
        self.assertTrue(any(p.startswith("R1: status 'resolved'") for p in found))
        self.assertIn("missing the `Dismissed as noise:` line", found)
        self.assertIn("frontmatter: date '10/11/2026' is not YYYY-MM-DD", found)

    def test_a_malformed_finding_heading_is_a_problem(self):
        self.assertIn("heading '## R1 - The app could not start without a seeded account' is not `## R<n>: <problem>`",
                      validate_retro.problems(GOOD.replace("## R1: The app", "## R1 - The app")))

    def test_missing_field_and_order(self):
        swapped = GOOD.replace("- severity: blocker", "- severity: TMP").replace(
            "- severity: low", "- severity: blocker").replace("- severity: TMP", "- severity: low")
        self.assertIn("findings are not ordered by severity", validate_retro.problems(swapped))
        dropped = GOOD.replace("- proposal: name the test command in CLAUDE.md\n", "")
        self.assertIn("R2: missing `- proposal:`", validate_retro.problems(dropped))


class Locate(unittest.TestCase):
    def test_newest_transcript_its_subagents_and_the_main_checkout_name(self):
        projects = Path(tempfile.mkdtemp())
        repo = Path(tempfile.mkdtemp()) / "shop"
        repo.mkdir()
        subprocess.run(["git", "init", "-q", str(repo)], check=True)
        folder = locate.transcripts_dir(repo.resolve(), projects)
        folder.mkdir(parents=True)
        old, new = folder / "old.jsonl", folder / "new.jsonl"
        old.write_text("{}")
        new.write_text("{}")
        os.utime(old, (1, 1))
        (folder / "new" / "subagents").mkdir(parents=True)
        (folder / "new" / "subagents" / "a.jsonl").write_text("{}")

        found = locate.locate(repo, projects=projects)
        self.assertEqual(found["session"], str(new))
        self.assertEqual(found["subagents"], [str(folder / "new" / "subagents" / "a.jsonl")])
        self.assertEqual(found["project"], "shop")
        self.assertEqual(locate.locate(repo, "old", projects=projects)["session"], str(old))


if __name__ == "__main__":
    unittest.main()
