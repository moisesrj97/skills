import io
import json
import sys
from contextlib import redirect_stderr
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


    def test_fails_naming_seen_checks_when_a_required_one_never_appears(self):
        clock = iter(range(0, 3600, 300))
        state, details = ci.wait(1, ["lintCodeQuality"], set(), 300, 3600,
                                 fetch=lambda pr: [check("Jenkins Lint CodeQuality", "pass"), check("test", "skipping")],
                                 sleep=lambda s: None, now=lambda: next(clock))
        self.assertEqual(state, "missing")
        self.assertEqual(details["missing"], ["lintCodeQuality"])
        self.assertEqual(details["seen"], ["Jenkins Lint CodeQuality", "test"])

    def test_a_late_required_check_inside_the_grace_period_still_counts(self):
        rounds = iter([[check("lint", "pass")]] * 3 + [[check("lint", "pass"), check("jenkins", "pending")]] * 3
                      + [[check("lint", "pass")]] * 3 + [[check("lint", "pass"), check("jenkins", "pass")]])
        clock = iter(range(0, 36000, 300))
        state, _ = ci.wait(1, ["jenkins"], set(), 300, 36000, fetch=lambda pr: next(rounds),
                           sleep=lambda s: None, now=lambda: next(clock))
        self.assertEqual(state, "green")

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


class BranchWait(unittest.TestCase):
    def setUp(self):
        self.real = (ci.gh, ci.wait)

    def tearDown(self):
        ci.gh, ci.wait = self.real

    def stub_gh(self, responses):
        self.calls = []

        def gh(*args, cwd=None):
            self.calls.append(args[1])
            return next((0, json.dumps(body), "") for path, body in responses.items() if path in args[1])
        ci.gh = gh

    def test_maps_check_runs_and_commit_statuses_to_buckets(self):
        runs = [{"name": "check", "status": "completed", "conclusion": "success", "html_url": "u1"},
                {"name": "e2e", "status": "in_progress", "conclusion": None},
                {"name": "deploy", "status": "completed", "conclusion": "skipped"},
                {"name": "lint", "status": "completed", "conclusion": "timed_out"},
                {"name": "old", "status": "completed", "conclusion": "cancelled"}]
        statuses = [{"context": "Jenkins", "state": "pending", "target_url": "u2"},
                    {"context": "scan", "state": "error"}]
        self.stub_gh({"/check-runs": {"check_runs": runs}, "/status": {"statuses": statuses}})
        buckets = {c["name"]: c["bucket"] for c in ci.fetch_commit_checks("abc")}
        self.assertEqual(buckets, {"check": "pass", "e2e": "pending", "deploy": "skipping", "lint": "fail",
                                   "old": "cancel", "Jenkins": "pending", "scan": "fail"})

    def test_branch_waits_on_the_tip_resolved_once_at_start(self):
        self.stub_gh({"commits/feature": {"sha": "abc123"}})
        args = []
        ci.wait = lambda target, req, skip, *rest, fetch=None: args.append((target, req, fetch)) or (
            "red", {"red": [{"name": "check", "state": "failure"}], "pending": [], "missing": []})
        self.assertEqual(ci.main(["wait", "--branch", "feature", "--required", "check"]), 1)
        self.assertEqual(args, [("abc123", ["check"], ci.fetch_commit_checks)])

    def test_sha_pins_the_commit_without_a_lookup(self):
        self.stub_gh({})
        args = []
        ci.wait = lambda target, *rest, fetch=None: args.append(target) or (
            "green", {"red": [], "pending": [], "missing": []})
        self.assertEqual(ci.main(["wait", "--branch", "feature", "--sha", "def456"]), 0)
        self.assertEqual((args, self.calls), (["def456"], []))

    def test_wait_takes_exactly_one_of_pr_and_branch(self):
        for argv in (["wait"], ["wait", "1", "--branch", "feature"]):
            with self.assertRaises(SystemExit), redirect_stderr(io.StringIO()):
                ci.main(argv)


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
