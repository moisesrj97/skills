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

    Dismissed as noise: none
    """)


class Retros(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        (self.root / "shop").mkdir()
        self.file = self.root / "shop" / "2026-11-10-cart.md"
        self.file.write_text(RETRO)

    def test_collect_keeps_open_and_rejected_with_weights(self):
        found = {f["ref"]: f for f in retros.collect(self.root)}
        self.assertEqual(set(found), {"shop/2026-11-10-cart.md#R1", "shop/2026-11-10-cart.md#R2b"})
        r1 = found["shop/2026-11-10-cart.md#R1"]
        self.assertEqual((r1["weight"], r1["date"], r1["evidence"]), (4, "2026-11-10", '- [12] "login failed"'))
        self.assertEqual(len(retros.collect(self.root, everything=True)), 3)

    def test_set_rewrites_only_that_findings_status(self):
        retros.set_status(self.root, "shop/2026-11-10-cart.md#R2b", "duplicate of shop/2026-11-10-cart.md#R2")
        text = self.file.read_text()
        self.assertIn("- status: duplicate of shop/2026-11-10-cart.md#R2\n- severity: medium", text)
        self.assertIn("- status: applied (CLAUDE.md)", text)
        self.assertEqual(text.count("- status:"), 3)

    def test_set_replaces_a_multiline_status_whole(self):
        retros.set_status(self.root, "shop/2026-11-10-cart.md#R2b", "open")
        r2b = [f for f in retros.collect(self.root) if f["id"] == "R2b"][0]
        self.assertEqual(r2b["status"], "open")
        self.assertNotIn("reopen if it recurs", self.file.read_text())

    def test_set_refuses_unknown_status_ref_and_finding(self):
        for ref, status in [("shop/2026-11-10-cart.md#R1", "resolved"),
                            ("shop/2026-11-10-cart.md", "open"),
                            ("shop/2026-11-10-cart.md#R9", "open"),
                            ("shop/nope.md#R1", "open")]:
            with self.assertRaises(ValueError):
                retros.set_status(self.root, ref, status)
        self.assertEqual(self.file.read_text(), RETRO)


if __name__ == "__main__":
    unittest.main()
