import datetime
import json
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import retros  # noqa: E402

RETRO = textwrap.dedent("""\
    ---
    date: 2026-11-10
    project: shop
    session: /tmp/s.jsonl
    summary: fix the cart total
    ---

    # Retro: cart total

    ## R1: No seeded account

    - status: open
    - severity: blocker
    - category: verification
    - kind: mechanical
    - target: scripts/seed.ts
    - evidence:
      - [12] "login failed"
    - proposal: add a seed script

    ## R2: Test command hard to find

    - status: applied (CLAUDE.md)
    - severity: low
    - category: navigation
    - kind: judgement
    - target: CLAUDE.md
    - evidence: [7] searched
    - proposal: name it

    ## R2b: Same command, other package

    - status: rejected (one-off,
      - reopen if it recurs)
    - severity: medium
    - category: navigation
    - kind: judgement
    - target: CLAUDE.md
    - evidence: [9] searched again
    - proposal: name it there too

    ## R3: A zsh glob with no match

    - status: skipped (fixed in the next call)
    - evidence: [4]
    """)


class Retros(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        (self.root / "shop").mkdir()
        self.file = self.root / "shop" / "2026-11-10-cart.md"
        self.file.write_text(RETRO)

    def test_collect_keeps_open_rejected_and_skipped_with_weights(self):
        found = {f["ref"]: f for f in retros.collect(self.root)}
        self.assertEqual(set(found), {"shop/2026-11-10-cart.md#R1", "shop/2026-11-10-cart.md#R2b",
                                      "shop/2026-11-10-cart.md#R3"})
        r1 = found["shop/2026-11-10-cart.md#R1"]
        self.assertEqual((r1["weight"], r1["date"], r1["evidence"]), (4, "2026-11-10", '- [12] "login failed"'))
        self.assertEqual(found["shop/2026-11-10-cart.md#R3"]["weight"], 1)
        self.assertEqual(len(retros.collect(self.root, everything=True)), 4)

    def test_set_rewrites_only_that_findings_status(self):
        retros.set_status(self.root, "shop/2026-11-10-cart.md#R2b", "duplicate of shop/2026-11-10-cart.md#R2")
        text = self.file.read_text()
        self.assertIn("- status: duplicate of shop/2026-11-10-cart.md#R2\n- severity: medium", text)
        self.assertIn("- status: applied (CLAUDE.md)", text)
        self.assertEqual(text.count("- status:"), 4)

    def test_set_replaces_a_multiline_status_whole(self):
        retros.set_status(self.root, "shop/2026-11-10-cart.md#R2b", "open")
        r2b = [f for f in retros.collect(self.root) if f["id"] == "R2b"][0]
        self.assertEqual(r2b["status"], "open")
        self.assertNotIn("reopen if it recurs", self.file.read_text())

    def test_set_refuses_unknown_status_ref_and_finding(self):
        for ref, status in [("shop/2026-11-10-cart.md#R1", "resolved"),
                            ("shop/2026-11-10-cart.md", "open"),
                            ("shop/2026-11-10-cart.md#R9", "open"),
                            ("shop/nope.md#R1", "open"),
                            ("shop/2026-11-10-cart.md#R1", "applied (<commit or PR for seed>)")]:
            with self.assertRaises(ValueError):
                retros.set_status(self.root, ref, status)
        self.assertEqual(self.file.read_text(), RETRO)


class Digest(unittest.TestCase):
    def test_owner_names_the_skill_app_or_file_a_change_lands_in(self):
        for target, expected in [("skills/engineering/megamoind/SKILL.md:12-40", "megamoind"),
                                 ("skills/engineering/retro-sweep/scripts/sweep.py", "retro-sweep"),
                                 ("apps/panel/src/a.ts", "panel"),
                                 ("CLAUDE.md:26 (step 2)", "claude.md"),
                                 ("unknown", "~unknown"), (None, "~unknown")]:
            self.assertEqual(retros.owner(target), expected, target)

    def test_old_skipped_findings_age_out_of_the_digest(self):
        root = Path(tempfile.mkdtemp())
        (root / "shop").mkdir()
        (root / "shop" / "2026-11-10-cart.md").write_text(RETRO)
        today = datetime.date(2026, 11, 20)
        self.assertIn("shop/2026-11-10-cart.md#R3", [f["ref"] for f in retros.digestible(root, 28, today)])
        aged = [f["ref"] for f in retros.digestible(root, 7, today)]
        self.assertNotIn("shop/2026-11-10-cart.md#R3", aged)
        self.assertIn("shop/2026-11-10-cart.md#R1", aged)

    def test_batches_keep_findings_of_one_owner_together_and_clip_fields(self):
        findings = [{"ref": f"p/f.md#R{i}", "target": target, "evidence": "x" * 500}
                    for i, target in enumerate(["skills/a/zeta/SKILL.md", "apps/web/x.ts", "skills/a/zeta/scripts/s.py",
                                                "apps/web/y.ts"])]
        split = retros.batches(findings, 2)
        self.assertEqual([[f["ref"] for f in b] for b in split], [["p/f.md#R1", "p/f.md#R3"], ["p/f.md#R0", "p/f.md#R2"]])
        self.assertEqual(len(split[0][0]["evidence"]), retros.CLIP + 1)


class Merge(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp())
        self.write("batch-1", [{"ref": "a/x.md#R1", "date": "2026-11-12", "status": "open", "severity": "medium"},
                               {"ref": "b/y.md#R1", "date": "2026-11-10", "status": "open", "severity": "low"}])
        self.write("batch-2", [{"ref": "a/x.md#R2", "date": "2026-11-11", "status": "skipped (one-off)"},
                               {"ref": "c/z.md#R4", "date": "2026-11-09", "status": "skipped (one-off)"},
                               {"ref": "c/z.md#R5", "date": "2026-11-09", "status": "rejected (no)"}])
        self.write("clusters-1", [{"owner": "hook", "cause": "pipes", "proposal": "block", "members": ["a/x.md#R1"]},
                                  {"owner": "zsh", "cause": "globs", "proposal": "quote", "members": ["b/y.md#R1"]}])
        self.write("clusters-2", [{"owner": "Hook", "cause": " pipes ", "proposal": "-", "members": ["a/x.md#R2"]},
                                  {"owner": "zsh lint", "cause": "unquoted globs", "proposal": "-",
                                   "members": ["c/z.md#R4"]},
                                  {"owner": "x", "cause": "y", "proposal": "z", "members": ["c/z.md#R5"]}])

    def write(self, name, data):
        (self.dir / f"{name}.json").write_text(json.dumps(data))

    def test_merges_the_given_groups_and_ranks_them(self):
        merged, problems = retros.merge(self.dir, [{"ids": ["1.2", "2.2"], "cause": "unquoted globs"},
                                                   {"ids": ["1.1", "2.1"]}])
        self.assertEqual(problems, [])
        by_id = {c["id"]: c for c in merged}
        self.assertEqual(set(by_id), {"1.1", "1.2", "2.3"})
        hook, zsh = by_id["1.1"], by_id["1.2"]
        self.assertEqual((hook["src"], hook["members"], hook["canonical"]),
                         (["1.1", "2.1"], ["a/x.md#R2", "a/x.md#R1"], "a/x.md#R2"))
        self.assertEqual((hook["statuses"], hook["weight"], hook["score"]), ({"skipped": 1, "open": 1}, 2, 4))
        self.assertEqual((zsh["owner"], zsh["cause"], zsh["projects"]), ("zsh", "unquoted globs", ["b", "c"]))
        self.assertEqual(by_id["2.3"]["rejected"], ["c/z.md#R5"])
        self.assertEqual([c["id"] for c in merged], ["1.1", "1.2", "2.3"])

    def test_a_skipped_only_cluster_goes_forward_from_three_members(self):
        self.write("batch-1", [{"ref": f"a/x.md#R{i}", "date": "2026-11-10", "status": "skipped (x)"} for i in range(5)])
        self.write("clusters-1", [{"owner": "o", "cause": "c", "proposal": "p",
                                   "members": ["a/x.md#R0", "a/x.md#R1", "a/x.md#R2"]},
                                  {"owner": "o", "cause": "d", "proposal": "p", "members": ["a/x.md#R3", "a/x.md#R4"]}])
        (self.dir / "batch-2.json").unlink()
        (self.dir / "clusters-2.json").unlink()
        merged, _ = retros.merge(self.dir)
        self.assertEqual({c["id"]: c["forward"] for c in merged}, {"1.1": True, "1.2": False})

    def test_names_every_offender_in_one_pass(self):
        self.write("batch-3", [{"ref": "d/w.md#R1", "date": "2026-11-10", "status": "open"}])
        self.write("clusters-1", [{"owner": "hook", "cause": "pipes", "proposal": "", "members": ["a/x.md#R1", "q/q.md#R1"]},
                                  {"owner": "zsh", "cause": "globs", "proposal": "quote",
                                   "members": ["b/y.md#R1", "a/x.md#R1"]}])
        merged, problems = retros.merge(self.dir, [{"ids": ["1.1", "9.9"]}, {"ids": ["1.1"]}])
        self.assertEqual(merged, [])
        self.assertEqual(sorted(problems), sorted([
            "batch-3.json: no clusters-3.json",
            "1.1: no proposal",
            "merges[1]: unknown cluster 9.9",
            "merges[2]: 1.1 is already in merges[1]",
            "1.1: q/q.md#R1 is in no batch",
            "a/x.md#R1: in 1.1, 1.2",
            "d/w.md#R1: in no cluster",
        ]))

    def test_cli_writes_merged_and_an_index_sorted_by_owner(self):
        self.assertEqual(retros.main(["merge", str(self.dir)]), 0)
        self.assertEqual(len(json.loads((self.dir / "merged.json").read_text())), 5)
        self.assertEqual([line.split(" | ")[2] for line in (self.dir / "index.txt").read_text().splitlines()],
                         ["hook", "Hook", "x", "zsh", "zsh lint"])
        (self.dir / "clusters-2.json").write_text("[{")
        self.assertEqual(retros.main(["merge", str(self.dir)]), 1)


class SharedFormat(unittest.TestCase):
    def test_both_skills_carry_the_same_retro_file_module(self):
        here = Path(__file__).parent / "retro_file.py"
        twin = Path(__file__).parents[2] / "retro-with-docs" / "scripts" / "retro_file.py"
        if not twin.exists():
            self.skipTest("retro-with-docs is not installed beside retro-digest")
        self.assertEqual(here.read_text(), twin.read_text(),
                         "copy retro-with-docs/scripts/retro_file.py over this one, or the other way round")


if __name__ == "__main__":
    unittest.main()
