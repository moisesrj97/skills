import os
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import known  # noqa: E402
import locate  # noqa: E402
import migrate_retros  # noqa: E402
import retro_file  # noqa: E402
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
    - expected: a seeded account ready for the browser check
    - cost: the browser check was skipped; no workaround
    - cause: no seed script exists [12]
    - proposal: add a seed script
    - matches: shop/2026-11-01-x.md#R2

    ## R2: The test command was hard to find

    - status: duplicate of shop/2026-11-01-x.md#R3
    - severity: low
    - category: navigation
    - kind: judgement
    - target: unknown
    - evidence: [7] searched for 10 calls
    - expected: the command named where the agent looks first
    - cost: 10 calls
    - cause: suspicion: CLAUDE.md predates the test runner
    - proposal: none yet

    ## R3: A typo the agent fixed at once

    - status: skipped (one-off slip, fixed in the next call)
    - evidence: [3]
    """)


class Validate(unittest.TestCase):
    def test_a_conforming_retro_has_no_problems(self):
        self.assertEqual(validate_retro.problems(GOOD), [])

    def test_names_each_problem(self):
        bad = (GOOD.replace("- severity: blocker", "- severity: critical")
               .replace("- status: open", "- status: resolved")
               .replace("- cause: no seed script exists [12]", "- cause: the seed script is missing")
               .replace("date: 2026-11-10", "date: 10/11/2026"))
        found = validate_retro.problems(bad)
        self.assertIn("R1: severity 'critical' is not one of blocker | high | medium | low", found)
        self.assertTrue(any(p.startswith("R1: status 'resolved'") for p in found))
        self.assertIn("R1: cause cites the evidence ([<index>]), starts with `suspicion: ` or is `unknown`", found)
        self.assertIn("frontmatter: date '10/11/2026' is not YYYY-MM-DD", found)

    def test_a_malformed_finding_heading_is_a_problem(self):
        self.assertIn("heading '## R1 - The app could not start without a seeded account' is not `## R<n>: <problem>`",
                      validate_retro.problems(GOOD.replace("## R1: The app", "## R1 - The app")))

    def test_missing_field_and_order(self):
        swapped = GOOD.replace("- severity: blocker", "- severity: TMP").replace(
            "- severity: low", "- severity: blocker").replace("- severity: TMP", "- severity: low")
        self.assertIn("findings are not ordered by severity", validate_retro.problems(swapped))
        dropped = GOOD.replace("- cost: 10 calls\n", "")
        self.assertIn("R2: missing `- cost:`", validate_retro.problems(dropped))

    def test_skipped_needs_only_evidence_and_goes_last(self):
        self.assertIn("R3: missing `- evidence:`", validate_retro.problems(GOOD.replace("- evidence: [3]\n", "")))
        r3 = GOOD[GOOD.index("## R3"):]
        first = GOOD[:GOOD.index("## R1")] + r3 + "\n" + GOOD[GOOD.index("## R1"):GOOD.index("## R3")]
        self.assertIn("skipped findings go after every other finding", validate_retro.problems(first))

    def test_old_dismissed_line_and_unrecorded_need_migration(self):
        old = GOOD + "\nDismissed as noise: [3] a typo\n"
        self.assertTrue(any("Dismissed as noise:" in p for p in validate_retro.problems(old)))
        unrecorded = GOOD.replace("- cost: 10 calls", "- cost: unrecorded")
        self.assertIn("R2: cost `unrecorded` is only for migrated files", validate_retro.problems(unrecorded))
        migrated = unrecorded.replace("summary: fix", "migrated: 2026-11-13\nsummary: fix")
        self.assertEqual(validate_retro.problems(migrated), [])

    def test_wasted_context_names_lines_and_matches_are_refs(self):
        wasted = GOOD.replace("- category: navigation", "- category: wasted-context")
        self.assertIn("R2: a wasted-context target names the lines, as `path:start-end`",
                      validate_retro.problems(wasted))
        self.assertEqual(validate_retro.problems(wasted.replace("- target: unknown", "- target: CLAUDE.md:10-40")), [])
        bad_ref = GOOD.replace("- matches: shop/2026-11-01-x.md#R2", "- matches: R2")
        self.assertTrue(any(p.startswith("R1: matches 'R2'") for p in validate_retro.problems(bad_ref)))


OLD = textwrap.dedent("""\
    ---
    date: 2026-11-04
    project: shop
    session: /tmp/s.jsonl
    summary: fix the cart total
    ---

    # Retro: cart total

    ## R1: Test command hard to find

    - status: resolved (CLAUDE.md fixed)
    - severity: low
    - category: navigation
    - kind: judgement
    - target: CLAUDE.md
    - evidence: [7] searched
    - proposal: name it

    ## R2: No seeded account

    - status: open
    - severity: blocker
    - category: verification
    - kind: mechanical
    - target: scripts/seed.ts
    - evidence:
      - [12] "login failed"
    - proposal:
      - add a seed script

    Dismissed as noise: [167]/[169] Edit before Read, fixed next call; [42] a zsh glob. [about 5] a slow boot; one transient fetch error
    """)


class Migrate(unittest.TestCase):
    def test_converts_to_a_valid_file_keeping_ids(self):
        new = migrate_retros.migrate(OLD, "2026-11-13")
        self.assertEqual(validate_retro.problems(new), [])
        meta, _, findings = retro_file.parse(new)
        self.assertEqual(meta["migrated"], "2026-11-13")
        self.assertEqual([f["id"] for f in findings], ["R2", "R1", "R3", "R4", "R5", "R6"])
        r1 = findings[1]
        self.assertEqual((r1["status"], r1["cause"], r1["proposal"]), ("applied (CLAUDE.md fixed)", "unrecorded", "name it"))
        self.assertEqual(findings[0]["proposal"], "- add a seed script")
        skipped = [(f["title"], f["evidence"]) for f in findings[2:]]
        self.assertEqual(skipped, [("Edit before Read, fixed next call", "[167]/[169]"), ("a zsh glob", "[42]"),
                                   ("a slow boot", "[about 5]"), ("one transient fetch error", "unrecorded")])

    def test_a_semicolon_inside_parentheses_stays_in_its_item(self):
        self.assertEqual(migrate_retros.dismissed_items("[486] a ticket mismatch (not environment; reported); [629] a slip"),
                         [("a ticket mismatch (not environment; reported)", "[486]"), ("a slip", "[629]")])

    def test_a_second_run_changes_nothing(self):
        once = migrate_retros.migrate(OLD, "2026-11-13")
        self.assertEqual(migrate_retros.migrate(once, "2026-11-14"), once)

    def test_write_only_with_the_flag(self):
        root = Path(tempfile.mkdtemp())
        (root / "shop").mkdir()
        path = root / "shop" / "2026-11-04-cart.md"
        path.write_text(OLD)
        migrate_retros.main(["--root", str(root)])
        self.assertEqual(path.read_text(), OLD)
        migrate_retros.main(["--root", str(root), "--file", "shop/2026-11-04-cart.md", "--write"])
        self.assertEqual(validate_retro.problems(path.read_text()), [])


class Known(unittest.TestCase):
    def test_lists_open_and_rejected_and_searches_skipped_by_term(self):
        root = Path(tempfile.mkdtemp())
        (root / "shop").mkdir()
        (root / "shop" / "2026-11-10-cart.md").write_text(GOOD.replace("- status: duplicate of shop/2026-11-01-x.md#R3",
                                                                       "- status: rejected (one-off)"))
        self.assertEqual(known.known(root, []), [
            "shop/2026-11-10-cart.md#R1 | open | verification | The app could not start without a seeded account",
            "shop/2026-11-10-cart.md#R2 | rejected | navigation | The test command was hard to find",
        ])
        self.assertEqual(known.known(root, ["TYPO"]),
                         ["shop/2026-11-10-cart.md#R3 | skipped | - | A typo the agent fixed at once"])


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
