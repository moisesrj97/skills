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

SOURCE = textwrap.dedent("""\
    export function total(items: Item[]) {
      let sum = 0;
      for (const item of items) {
        sum += item.price * item.qty;
      }
      return sum;
    }
    """)

ROUND = textwrap.dedent("""\
    ### 1. src/cart.ts:4: price ignores discounts

    Severity: P1

    Verdict: CONFIRMED

    Scenario: a discounted item → full price

    > for (const item of items) {
    >     sum += item.price * item.qty;

    ### 2. src/cart.ts:2: quoted at a moved line

    > return sum;

    ### 3. src/cart.ts:5: invented code

    > sum -= item.discount;

    ### 4. src/missing.ts:1: file not in head

    > anything

    ### 5. src/cart.ts:1: no quote at all

    Scenario: none

    ### 6. src/cart.ts:1: elided quote

    > export function total(items: Item[]) {
    > ...
    > return sum;

    ### 7. `./src/cart.ts`:4-5: diff-marked quote under a backticked path

    > +    sum += item.price * item.qty;
    > +  }

    ### 8. src/cart.ts:6: second block quotes another file

    > return sum;

    Evidence from the caller:

    > checkout(total(items));

    ### 9. src/cart.ts:4–5: en-dash range and a fenced quote

    > ```ts
    > sum += item.price * item.qty;
    > ```

    ### 10 src/cart.ts line 4 malformed header

    > for (const item of items) {

    ### 12. Off-by-one in the loop (src/cart.ts:4)

    > for (const item of items) {

    ### 13. src/cart.ts:4: a quote whose inner whitespace differs

    > sum  += item.price * item.qty;

    ### 14. README.md:1: a fence that is itself the evidence

    > ```bash

    ### 11. `src/my file.ts`:1: a path with a space

    > const spaced = true;

    END OF ROUND
    """)


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
        (Path(self.repo) / "README.md").write_text("```bash\nnpm test\n```\n")
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-qm", "head")
        (Path(self.repo) / "src/cart.ts").write_text("// the working tree moved on\n")

    def verdicts(self, ref):
        _, findings = check_quotes.parse_round(ROUND)
        return {(verdict if verdict == "UNPARSED" else label.split()[0]): (verdict, reason)
                for verdict, label, reason in
                check_quotes.check(findings, ref, self.repo)}

    def test_reads_the_given_ref_not_the_working_tree(self):
        v = self.verdicts("main")
        self.assertEqual(v["1"], ("CONFIRMED", ""))
        self.assertEqual(v["2"], ("CONFIRMED", "quote found at line 6"))
        self.assertEqual(v["3"][0], "DISCARDED")
        self.assertIn("matches nothing in main:src/cart.ts", v["3"][1])
        self.assertIn("does not exist", v["4"][1])
        self.assertEqual(v["5"], ("DISCARDED", "no quote"))
        self.assertEqual(v["6"][0], "CONFIRMED")
        self.assertEqual(v["7"][0], "CONFIRMED")
        self.assertEqual(v["8"][0], "CONFIRMED")
        self.assertIn("quote block 2 of 2 is not in src/cart.ts", v["8"][1])
        self.assertEqual(v["9"], ("CONFIRMED", ""))
        self.assertEqual(v["UNPARSED"][0], "UNPARSED")
        self.assertEqual(v["11"], ("CONFIRMED", ""))
        self.assertEqual(v["13"][0], "DISCARDED")
        self.assertEqual(v["14"], ("CONFIRMED", ""))
        _, findings = check_quotes.parse_round(ROUND)
        unparsed = [r for r in check_quotes.check(findings, "main", self.repo) if r[0] == "UNPARSED"]
        self.assertEqual(len(unparsed), 2)

    def test_worktree_mode_reads_disk(self):
        self.assertEqual(self.verdicts(None)["1"][0], "DISCARDED")

    def test_unsealed_round_exits_2(self):
        path = Path(self.repo) / "round.md"
        path.write_text(ROUND.replace("END OF ROUND", ""))
        self.assertEqual(check_quotes.main([str(path), "--ref", "main", "--repo", self.repo]), 2)

    def test_no_findings(self):
        sealed, findings = check_quotes.parse_round("NO FINDINGS\nEND OF ROUND\n")
        self.assertTrue(sealed)
        self.assertEqual(findings, [])


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

    def test_rejects_unknown_family_and_missing_effort(self):
        self.assertEqual(self.run_script("--reviewer", "llama-3:high").returncode, 2)
        self.assertEqual(self.run_script("--reviewer", "claude-opus-5-5").returncode, 2)


if __name__ == "__main__":
    unittest.main()
