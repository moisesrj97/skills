import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import ci  # noqa: E402


def check(name, bucket, state="X"):
    return {"name": name, "bucket": bucket, "state": state, "link": f"https://ci.example.test/{name}"}


class Evaluate(unittest.TestCase):
    def test_green_counts_skipped_as_green(self):
        self.assertEqual(ci.evaluate([check("lint", "pass"), check("deploy", "skipping")])[0], "green")

    def test_pending_wins_over_red_until_everything_settles(self):
        state, details = ci.evaluate([check("lint", "fail"), check("test", "pending")])
        self.assertEqual(state, "pending")
        self.assertEqual([c["name"] for c in details["red"]], ["lint"])

    def test_red_once_settled(self):
        self.assertEqual(ci.evaluate([check("lint", "fail"), check("test", "pass")])[0], "red")
        self.assertEqual(ci.evaluate([check("lint", "cancel")])[0], "red")

    def test_all_green_with_a_required_check_missing_is_still_pending(self):
        state, details = ci.evaluate([check("lint", "pass")], required_names=["jenkins"])
        self.assertEqual(state, "pending")
        self.assertEqual(details["missing"], ["jenkins"])

    def test_no_checks_reported_yet_is_pending_not_green(self):
        self.assertEqual(ci.evaluate([])[0], "pending")

    def test_no_checks_after_the_grace_period_is_green_unless_something_required_is_left(self):
        self.assertEqual(ci.evaluate([], settled=True)[0], "green")
        self.assertEqual(ci.evaluate([], ["jenkins"], skip={"jenkins"}, settled=True)[0], "green")
        state, details = ci.evaluate([], ["jenkins"], settled=True)
        self.assertEqual((state, details["missing"]), ("pending", ["jenkins"]))

    def test_skipped_names_leave_the_wait(self):
        checks = [check("lint", "pass"), check("jenkins", "pending")]
        self.assertEqual(ci.evaluate(checks, ["jenkins"], skip={"jenkins"})[0], "green")


class Wait(unittest.TestCase):
    def test_polls_until_settled(self):
        rounds = iter([[check("lint", "pending")], [check("lint", "pass"), check("jenkins", "pass")]])
        sleeps = []
        state, _ = ci.wait(1, ["jenkins"], set(), 30, 3600, fetch=lambda pr: next(rounds),
                           sleep=sleeps.append, now=lambda: 0)
        self.assertEqual(state, "green")
        self.assertEqual(sleeps, [30])

    def test_times_out_naming_what_is_missing(self):
        clock = iter([0, 0, 100])
        state, details = ci.wait(1, ["jenkins"], set(), 30, 50, fetch=lambda pr: [check("lint", "pass")],
                                 sleep=lambda s: None, now=lambda: next(clock))
        self.assertEqual(state, "timeout")
        self.assertEqual(details["missing"], ["jenkins"])


    def test_rides_out_transient_gh_errors_but_not_three_in_a_row(self):
        def flaky(results):
            it = iter(results)
            def fetch(pr):
                r = next(it)
                if isinstance(r, Exception):
                    raise r
                return r
            return fetch
        blip = RuntimeError("HTTP 502")
        state, _ = ci.wait(1, [], set(), 1, 99, fetch=flaky([blip, blip, [check("lint", "pass")]]),
                           sleep=lambda s: None, now=lambda: 0)
        self.assertEqual(state, "green")
        with self.assertRaises(RuntimeError):
            ci.wait(1, [], set(), 1, 99, fetch=flaky([blip, blip, blip]), sleep=lambda s: None, now=lambda: 0)


class Required(unittest.TestCase):
    def setUp(self):
        self.real = (ci.gh, ci.wait)

    def tearDown(self):
        ci.gh, ci.wait = self.real

    def test_a_failed_lookup_raises_instead_of_returning_a_partial_list(self):
        rules = '[{"type": "required_status_checks", "parameters": {"required_status_checks": [{"context": "lint"}]}}]'
        ci.gh = lambda *a, cwd=None: (0, rules, "") if "rules/branches/main" in a[1] else (1, "", "HTTP 500")
        with self.assertRaises(RuntimeError):
            ci.required("origin/main")

    def test_check_names_with_commas_pass_intact(self):
        args = []
        ci.wait = lambda pr, req, skip, *rest: args.append((req, skip)) or ("green", {"red": [], "pending": [], "missing": []})
        ci.main(["wait", "1", "--required", "test (ubuntu-latest, 20)", "--required", "lint", "--skip", "e2e (a, b)"])
        self.assertEqual(args, [(["test (ubuntu-latest, 20)", "lint"], {"e2e (a, b)"})])

    def test_reads_rulesets_and_classic_protection(self):
        rules = [{"type": "pull_request"},
                 {"type": "required_status_checks",
                  "parameters": {"required_status_checks": [{"context": "lint"}, {"context": "test"}]}}]
        self.assertEqual(ci.required_from_rules(rules), ["lint", "test"])
        branch = {"protection": {"required_status_checks": {"contexts": ["build"], "checks": [{"context": "e2e"}]}}}
        self.assertEqual(ci.required_from_protection(branch), ["build", "e2e"])
        self.assertEqual(ci.required_from_protection({"protected": False}), [])


if __name__ == "__main__":
    unittest.main()
