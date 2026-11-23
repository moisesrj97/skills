import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import run  # noqa: E402


class FilteredFindings(unittest.TestCase):
    def test_any_level_three_or_deeper_title_counts_after_the_filter_marker(self):
        text = "\n".join([
            "### src/ignored.ts:1 before the marker",
            run.FILTERED,
            "## Summary src/summary.ts:9",
            "### src/a.ts:10 level three",
            "body",
            "#### src/b.ts:20-22 level four",
            "body",
        ])
        self.assertEqual([(f, s, e) for f, s, e, _ in run.found_in("security", "new", text)],
                         [("src/a.ts", 10, 10), ("src/b.ts", 20, 22)])


if __name__ == "__main__":
    unittest.main()
