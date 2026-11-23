import contextlib
import io
import json
import os
import stat
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import check_quotes  # noqa: E402
import run_round  # noqa: E402
import slice_diff  # noqa: E402
import wait_rounds  # noqa: E402

SOURCE = textwrap.dedent("""\
    export function total(items: Item[]) {
      let sum = 0;
      for (const item of items) {
        sum += item.price * item.qty;
      }
      return sum;
    }
    """)

FENCE = "`" * 3

ROUND = textwrap.dedent(f"""\
    ### 1. src/cart.ts:4: price ignores discounts

    Severity: P1

    Verdict: CONFIRMED

    Scenario: a discounted item → full price

    `src/cart.ts:3-4`
    {FENCE}ts
      for (const item of items) {{
        sum += item.price * item.qty;
    {FENCE}

    ### 2. src/cart.ts:2: quoted at a moved line

    `src/cart.ts:2`
    {FENCE}
    return sum;
    {FENCE}

    ### 3. src/cart.ts:5: invented code

    `src/cart.ts:5`
    {FENCE}
    sum -= item.discount;
    {FENCE}

    ### 4. src/missing.ts:1: file not in head

    `src/missing.ts:1`
    {FENCE}
    anything
    {FENCE}

    ### 5. src/cart.ts:1: no quote at all

    Scenario: none

    ### 6. `./src/cart.ts`:4-5: diff-marked quote under a backticked path

    `./src/cart.ts:4-5`
    {FENCE}diff
    +    sum += item.price * item.qty;
    +  }}
    {FENCE}

    ### 7. src/cart.ts:6: second block quotes another file

    `src/cart.ts:6`
    {FENCE}
      return sum;
    {FENCE}

    Evidence from the caller:

    `src/state.ts:1`:
    {FENCE}
    export const state = 'idle';
    {FENCE}

    ### 8. src/cart.ts:4: one block is invented

    `src/cart.ts:4`
    {FENCE}
    sum += item.price * item.qty;
    {FENCE}

    `src/state.ts:1`
    {FENCE}
    export const state = 'busy';
    {FENCE}

    ### 10 src/cart.ts line 4 malformed header

    ### 11. `src/my file.ts`:1: a path with a space

    `src/my file.ts:1`
    {FENCE}
    const spaced = true;
    {FENCE}

    ### 12. README.md:1: a quote that holds a fence

    `README.md:1-3`
    ~~~~
    {FENCE}bash
    npm test
    {FENCE}
    ~~~~

    END OF ROUND
    """)

FIXTURES = Path(__file__).parent / "fixtures"


def git(repo, *args):
    subprocess.run(["git", "-C", repo, "-c", "user.name=t", "-c", "user.email=t@example.test", *args],
                   check=True, capture_output=True)


class CheckQuotes(unittest.TestCase):
    def setUp(self):
        self.repo = tempfile.mkdtemp()
        git(self.repo, "init", "-q", "-b", "main")
        (Path(self.repo) / "src").mkdir()
        (Path(self.repo) / "src/cart.ts").write_text(SOURCE)
        (Path(self.repo) / "src/my file.ts").write_text("const spaced = true;\n")
        (Path(self.repo) / "src/state.ts").write_text("export const state = 'idle';\n")
        (Path(self.repo) / "README.md").write_text(f"{FENCE}bash\nnpm test\n{FENCE}\n")
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-qm", "head")
        (Path(self.repo) / "src/cart.ts").write_text("// the working tree moved on\n")

    def verdicts(self, ref, text=ROUND):
        _, findings = check_quotes.parse_round(text)
        return {label.split()[0]: (verdict, reason) for verdict, label, reason in check_quotes.check(findings, ref, self.repo)}

    def check_one(self, quote, header="src/cart.ts:4"):
        round_text = f"### 1. {header}: x\n\n{quote}\n\nEND OF ROUND\n"
        _, findings = check_quotes.parse_round(round_text)
        [(verdict, _, reason)] = check_quotes.check(findings, "main", self.repo)
        return verdict, reason

    def test_reads_the_given_ref_not_the_working_tree(self):
        v = self.verdicts("main")
        self.assertEqual(v["1"], ("CONFIRMED", ""))
        self.assertEqual(v["2"], ("CONFIRMED", "`src/cart.ts:2` found at lines 6-6"))
        self.assertEqual(v["3"], ("DISCARDED", "`src/cart.ts:5` matches nothing in main:src/cart.ts"))
        self.assertIn("does not exist", v["4"][1])
        self.assertEqual(v["5"][0], "UNPARSED")
        self.assertIn("header is not", v["10"][1])
        self.assertEqual(v["6"], ("CONFIRMED", ""))
        self.assertEqual(v["7"], ("CONFIRMED", ""))
        self.assertEqual(v["8"][0], "CONFIRMED")
        self.assertIn("`src/state.ts:1` matches nothing in main:src/state.ts: check that block by hand", v["8"][1])
        self.assertEqual(v["11"], ("CONFIRMED", ""))
        self.assertEqual(v["12"], ("CONFIRMED", ""))

    def test_worktree_mode_reads_disk(self):
        self.assertEqual(self.verdicts(None)["1"][0], "DISCARDED")

    def test_strips_read_line_number_prefixes(self):
        arrow = f"`src/cart.ts:3-4`\n{FENCE}\n     3→  for (const item of items) {{\n     4→    sum += item.price * item.qty;\n{FENCE}"
        tab = f"`src/cart.ts:3-4`\n{FENCE}\n3\t  for (const item of items) {{\n4\t    sum += item.price * item.qty;\n{FENCE}"
        self.assertEqual(self.check_one(arrow), ("CONFIRMED", ""))
        self.assertEqual(self.check_one(tab), ("CONFIRMED", ""))

    def test_ignores_whitespace_differences_inside_lines(self):
        quote = f"`src/cart.ts:4`\n{FENCE}\nsum  +=   item.price * item.qty;\n{FENCE}"
        self.assertEqual(self.check_one(quote), ("CONFIRMED", ""))

    def test_an_elided_block_is_not_verbatim(self):
        quote = f"`src/cart.ts:1-6`\n{FENCE}\nexport function total(items: Item[]) {{\n...\nreturn sum;\n{FENCE}"
        self.assertEqual(self.check_one(quote)[0], "DISCARDED")

    def test_a_label_without_a_fence_is_no_quote(self):
        self.assertEqual(self.check_one("`src/cart.ts:4`\n> sum += item.price * item.qty;")[0], "UNPARSED")

    def test_unsealed_round_exits_2(self):
        path = Path(self.repo) / "round.md"
        path.write_text(ROUND.replace("END OF ROUND", ""))
        self.assertEqual(check_quotes.main([str(path), "--ref", "main", "--repo", self.repo]), 2)

    def test_no_findings(self):
        sealed, findings = check_quotes.parse_round("NO FINDINGS\nEND OF ROUND\n")
        self.assertTrue(sealed)
        self.assertEqual(findings, [])

    def test_quotes_that_were_wrongly_discarded_are_now_unparsed(self):
        fixtures = sorted((FIXTURES / "discarded").glob("*.md"))
        self.assertGreater(len(fixtures), 5)
        for fixture in fixtures:
            sealed, findings = check_quotes.parse_round(fixture.read_text())
            self.assertTrue(sealed, fixture.name)
            verdicts = {verdict for verdict, _, _ in check_quotes.check(findings, "main", self.repo)}
            self.assertEqual(verdicts, {"UNPARSED"}, fixture.name)


FAKE_CLAUDE = """#!/bin/sh
echo "$@" >> "$FAKE_CALLS"
cat > /dev/null
n=$(wc -l < "$FAKE_CALLS")
if [ "$n" -ge "${FAKE_SEAL_FROM:-1}" ]; then printf '### 1. a.ts:1: x\\n\\n> y\\n\\nEND OF ROUND\\n'; else echo partial; fi
"""

FAKE_CODEX = """#!/bin/sh
echo "$@" >> "$FAKE_CALLS"
cat > /dev/null
out=""; prev=""
for a in "$@"; do [ "$prev" = "-o" ] && out="$a"; prev="$a"; done
[ "$FAKE_GONE" = 1 ] && { echo "no such thread" >&2; exit 1; }
printf 'NO FINDINGS\\nEND OF ROUND\\n' > "$out"
echo '{"type":"thread.started","thread_id":"th-123"}'
"""


class RunRound(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp())
        self.calls = self.dir / "calls"
        self.prompt = self.dir / "prompt.md"
        self.prompt.write_text("review this")
        self.round = self.dir / "review-round-1.md"
        for name, body in (("claude", FAKE_CLAUDE), ("codex", FAKE_CODEX)):
            path = self.dir / name
            path.write_text(body)
            path.chmod(path.stat().st_mode | stat.S_IEXEC)
        self.env = {**os.environ, "FAKE_CALLS": str(self.calls),
                    "DIFF_REVIEW_CLAUDE": str(self.dir / "claude"), "DIFF_REVIEW_CODEX": str(self.dir / "codex")}

    def run_script(self, *args, **env):
        return subprocess.run(
            [sys.executable, str(Path(run_round.__file__)), "--prompt", str(self.prompt),
             "--round-file", str(self.round), "--repo", str(self.dir), *args],
            env={**self.env, **env}, capture_output=True, text=True)

    def calls_made(self):
        return self.calls.read_text().splitlines()

    def test_claude_fresh_then_continue(self):
        out = self.run_script("--reviewer", "claude-opus-5-5:high")
        self.assertEqual(out.returncode, 0, out.stderr)
        handle = json.loads(out.stdout)["handle"]
        self.assertIn(f"--session-id {handle} --model claude-opus-5-5 --effort high --permission-mode plan",
                      self.calls_made()[0])
        out = self.run_script("--reviewer", "claude-opus-5-5:high", "--handle", handle)
        self.assertEqual(json.loads(out.stdout)["handle"], handle)
        self.assertIn(f"--resume {handle}", self.calls_made()[1])

    def test_unsealed_round_is_retried_fresh_once(self):
        out = self.run_script("--reviewer", "claude-opus-5-5:high", FAKE_SEAL_FROM="2")
        self.assertEqual(json.loads(out.stdout)["attempts"], 2)
        first, second = self.calls_made()
        self.assertIn("--session-id", second)
        self.assertNotEqual(first.split()[2], second.split()[2])

    def test_unsealed_twice_exits_1(self):
        out = self.run_script("--reviewer", "claude-opus-5-5:high", FAKE_SEAL_FROM="9")
        self.assertEqual(out.returncode, 1)
        self.assertIn("unsealed", out.stderr)

    def test_codex_fresh_reads_thread_id_and_continue_omits_sandbox_flags(self):
        out = self.run_script("--reviewer", "gpt-6.1-sol:medium")
        self.assertEqual(json.loads(out.stdout)["handle"], "th-123")
        self.assertIn("-s read-only", self.calls_made()[0])
        out = self.run_script("--reviewer", "gpt-6.1-sol:medium", "--handle", "th-123")
        self.assertEqual(out.returncode, 0, out.stderr)
        resume = self.calls_made()[1]
        self.assertTrue(resume.startswith("exec resume"))
        self.assertNotIn("-s ", resume)
        self.assertNotIn("-C ", resume)

    def test_gone_reviewer_exits_3(self):
        out = self.run_script("--reviewer", "gpt-6.1-sol:medium", "--handle", "th-old", FAKE_GONE="1")
        self.assertEqual(out.returncode, 3)
        self.assertIn("start a fresh reviewer", out.stderr)

    def test_unsealed_continue_with_a_live_session_is_exit_1_not_gone(self):
        out = self.run_script("--reviewer", "claude-opus-5-5:high", "--handle", "abc", FAKE_SEAL_FROM="9")
        self.assertEqual(out.returncode, 1)

    def test_missing_cli_exits_5(self):
        out = self.run_script("--reviewer", "gpt-6.1-sol:high", DIFF_REVIEW_CODEX="/nonexistent/codex")
        self.assertEqual(out.returncode, 5)

    def test_prompt_naming_the_round_file_exits_6_without_launching(self):
        self.prompt.write_text(f"review this and write the round to {self.round}")
        out = self.run_script("--reviewer", "claude-opus-5-5:high")
        self.assertEqual(out.returncode, 6)
        self.assertIn("final message", out.stderr)
        self.assertFalse(self.calls.exists())

    def test_prompt_naming_the_previous_round_file_still_runs(self):
        self.prompt.write_text(f"previous round: {self.dir / 'review-round-0.md'}")
        out = self.run_script("--reviewer", "claude-opus-5-5:high")
        self.assertEqual(out.returncode, 0, out.stderr)

    def test_rejects_unknown_family_and_missing_effort(self):
        self.assertEqual(self.run_script("--reviewer", "llama-3:high").returncode, 2)
        self.assertEqual(self.run_script("--reviewer", "claude-opus-5-5").returncode, 2)


class SliceDiff(unittest.TestCase):
    BUDGET = 2000

    def setUp(self):
        self.repo = tempfile.mkdtemp()
        self.out = Path(tempfile.mkdtemp()) / "slices"
        git(self.repo, "init", "-q", "-b", "main")
        root = Path(self.repo)
        (root / "big.txt").write_text("".join(f"line {i}\n" for i in range(400)))
        for name in ("a.txt", "b.txt", "gone.txt"):
            (root / name).write_text("one\ntwo\n")
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-qm", "base")
        (root / "big.txt").write_text("".join(f"line {i} changed\n" if i % 3 else f"line {i}\n" for i in range(400)))
        (root / "a.txt").write_text("one\nTWO\n")
        (root / "gone.txt").unlink()
        (root / "new.txt").write_text("fresh\n")
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-qm", "head")

    def slice(self, *args, budget=BUDGET):
        with contextlib.redirect_stdout(io.StringIO()) as listing:
            code = slice_diff.main([*args, "--out", str(self.out), "--repo", self.repo, "--budget", str(budget)])
        return code, listing.getvalue()

    def patches(self):
        return sorted(self.out.glob("diff-*.patch"))

    def test_every_slice_fits_the_budget_and_applies_on_its_own(self):
        code, listing = self.slice("main~1...main")
        self.assertEqual(code, 0)
        self.assertGreater(len(self.patches()), 2)
        for patch in self.patches():
            self.assertLessEqual(len(patch.read_text()), self.BUDGET, patch.name)
            subprocess.run(["git", "-C", self.repo, "apply", "--check", "-R", "--unidiff-zero", str(patch)], check=True)
        self.assertIn("big.txt (+", listing)
        self.assertIn("part 1/", listing)
        self.assertIn("gone.txt (+0 -2)", listing)

    def test_slices_hold_the_whole_diff_once(self):
        self.slice("main~1...main")
        whole = subprocess.run(["git", "-C", self.repo, "diff", "main~1...main"], capture_output=True, text=True).stdout
        changed = lambda text: sorted(l for l in text.splitlines() if l[:1] in "+-" and l[:3] not in ("+++", "---"))
        self.assertEqual(changed("".join(p.read_text() for p in self.patches())), changed(whole))

    def test_worktree_includes_untracked_files(self):
        (Path(self.repo) / "a.txt").write_text("uncommitted\n")
        (Path(self.repo) / "untracked.txt").write_text("brand new\n")
        code, listing = self.slice("--worktree")
        self.assertEqual(code, 0)
        self.assertIn("a.txt (+1 -2)", listing)
        self.assertIn("untracked.txt (+1 -0)", listing)

    def test_rerun_replaces_stale_slices(self):
        self.slice("main~1...main")
        self.slice("main~1...main", budget=100_000)
        self.assertEqual([p.name for p in self.patches()], ["diff-01.patch"])

    def test_empty_diff_exits_1(self):
        self.assertEqual(self.slice("main...main")[0], 1)


class WaitRounds(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp())
        self.done = self.dir / "review-round-1.md"
        self.done.write_text("NO FINDINGS\nEND OF ROUND\n")
        self.running = self.dir / "review-round-2.md"
        self.running.write_text("### 1. a.ts:1: x\n")

    def test_returns_once_every_round_is_sealed(self):
        def seal_on_sleep(seconds):
            self.running.write_text("NO FINDINGS\nEND OF ROUND\n")
        clock = iter(range(100))
        self.assertEqual(wait_rounds.wait([self.done, self.running], 60, 5, sleep=seal_on_sleep,
                                          now=lambda: next(clock)), [])

    def test_times_out_with_the_unsealed_and_missing_files(self):
        missing = self.dir / "review-round-3.md"
        clock = iter([0, 30, 61])
        unsealed = wait_rounds.wait([self.done, self.running, missing], 60, 30, sleep=lambda s: None,
                                    now=lambda: next(clock))
        self.assertEqual(unsealed, [self.running, missing])

    def test_cli_exit_codes(self):
        script = str(Path(wait_rounds.__file__))
        ok = subprocess.run([sys.executable, script, str(self.done)], capture_output=True, text=True)
        self.assertEqual(ok.returncode, 0, ok.stderr)
        late = subprocess.run([sys.executable, script, str(self.done), str(self.running), "--timeout", "0"],
                              capture_output=True, text=True)
        self.assertEqual(late.returncode, 1)
        self.assertIn("review-round-2.md (last line is not END OF ROUND)", late.stderr)
        self.assertNotIn("review-round-1.md", late.stderr)


if __name__ == "__main__":
    unittest.main()
