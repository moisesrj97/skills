---
name: diff-review
description: Runs one review round of a diff in a separate reviewer agent of the chosen model and returns quote-backed findings without fixing. Use to find bugs in a diff, for a security review of a diff, a review by another model, or when a skill calls for one.
argument-hint: "[scope] [lens=code|security|cleanup] [reviewer=<model>[:<effort>]] [spec=<file>] [standards=<file>,…] [tag=<line>]"
---

# Diff review

A reviewer that shares the author's context shares its blind spots. The reviewer runs in its own agent, from another model family when the caller asks for one, and every finding it returns has to quote the code it cites. Round 1 starts it fresh.

## Arguments

- **scope**: a PR number, a ref range (`base...head`) or `diff` (uncommitted work). When omitted, the current branch's PR (`gh pr view --json number`), else the diff against its base. For a stacked PR the meaningful diff is `<parent-branch>...<branch>`.
- **lens**: what the reviewer looks for, from `references/lenses/<lens>.md`. `code` (default): bugs, each with a failure scenario. `security`: exploitable vulnerabilities, filtered by numbered exclusions and precedents. `cleanup`: code that works but costs, each with that cost.
- **reviewer**: `<model id>[:<effort>]`. Default `claude-opus-5-5:high`, for `security` too; `claude-opus-5-5:medium` for `cleanup`. A `claude-*` model runs on Claude, a `gpt-*` model on Codex, e.g. `gpt-6.1-sol:medium`.
- **spec**: a file with what the change must do (a ticket, a brief). The `code` lens checks the change against it.
- **standards**: files of rules the change is held to, on top of the project's own.
- **tag**: a line that marks the reviewer's session as part of a caller's run, e.g. `megamoind-run: <run> role=review-security`.
- From a calling skill: the round number, the already-decided list and, after round 1, the **reviewer handle** this skill returned in round 1, what changed since and the findings not acted on with their reasons.

## 1. Brief

The round file is `<scratch>/review-round-<N>.md`, in the session scratchpad when the system prompt lists one, else a fresh `mktemp -d`. Write the reviewer's prompt to `<scratch>/review-prompt-<N>.md`, with every item below that applies:

- First line: `You are the reviewer. Read <skill-dir>/references/reviewer.md and <skill-dir>/references/lenses/<lens>.md and follow them.`, with the absolute path of the folder this skill loaded from.
- The scope and the diff as patch files. Resolve a branch name in the range to its SHA first (`git rev-parse <branch>`), so a branch that moves mid-round doesn't change what is reviewed, and a PR number to `<base>...<head sha>`. Slice the diff, keeping the range as given since `a..b` and `a...b` differ, and paste the listing the script prints:

  ```bash
  python3 <skill-dir>/scripts/slice_diff.py <range> --out <scratch>/review-diff-<N>   # scope `diff`: --worktree
  ```
- Which version of the code to read and quote. For a range, that is its head (`git show <head>:<file>`), since the checkout can hold other changes. For `diff`, it is the working tree.
- Where the round goes: the round file, or, for a CLI reviewer (step 2), the final message and no file writes.
- With `tag=`, the tag as the prompt's last line, in every round.
- With `spec=` and `standards=`, each file's contents pasted under its own heading. A file you can't read ends the round before launch: return the missing path to the caller.
- The already-decided list, phrased as "do not reopen unless you find new evidence that changes its severity". A PLAUSIBLE finding the author declined belongs on it.
- After round 1, the commits since (say if they are amended or unpushed, since the reviewer reads the local branch), which findings each resolves, and the findings not acted on with their reasons. Tell the reviewer to review the **whole** scope again, since fixes can break things elsewhere, and to write the new round where the fourth bullet says.

A continued reviewer already holds its instructions, the scope, the spec, the standards and its earlier rounds, so its prompt from round 2 on carries only where the round goes, the new patch listing, the already-decided list and the items of the last bullet. A fresh reviewer gets every item, plus the previous round file.

## 2. Launch

Round 1, or a round with no handle, starts a fresh reviewer and records its **reviewer handle**. A round with a handle continues that reviewer. Continuing the same reviewer is deliberate: it remembers what it already reported and checks the fixes against its own findings, so do it even where a harness suggests a new agent for every re-check.

- **T3 Code** (`delegate_task` is available). Fresh: `delegate_task` with `role: "review"`, `isolation: "shared"` and the target from `orchestrator_capabilities`, which is provider `claudeAgent` with option `effort`, or `codex` with option `reasoningEffort`. The handle is the child's thread id. Continue: `t3_thread_send` to that thread with the prompt. The child writes the round file.
- **Otherwise**: run the reviewer's CLI through the script, in the background, from the repo root:

  ```bash
  python3 <skill-dir>/scripts/run_round.py --reviewer <model>:<effort> --prompt <prompt file> --round-file <round file> [--handle <handle>]
  ```

  A `claude-*` model runs on `claude -p`, a `gpt-*` model on `codex exec`, both read-only, so the reviewer can't edit, commit or post whatever the prompt says. The script runs an unsealed round once more and prints `{"handle", ...}`: keep the handle. On exit 1 the round failed twice; return its log tail (on stderr) to the caller. A `gpt-*` reviewer that exits 1 or 5 (CLI not installed) means Codex can't run, and a `claude-*` one that exits 5 means Claude can't: rerun the round on the other family, the lens's default reviewer from **reviewer** for a `gpt-*` one and `gpt-6.1-sol` at the same effort for a `claude-*` one, and tell the caller the round ran on the fallback and why, so a same-family review is never reported as cross-family. Exit 6 means the prompt names the round file: fix the prompt (step 1, fourth bullet) and run again. Its log is `<round file>` with `.log`; read only its tail, since the whole log floods the context.

When a continue fails (the T3 thread is gone, or the script exits 3), start a fresh reviewer for this round with the full prompt, and return its new handle.

Then wait for the round in the background, so its exit wakes you, with one call over every round file launched together:

```bash
python3 <skill-dir>/scripts/wait_rounds.py <round file>... [--timeout <seconds, default 1800>]
```

It exits 0 once every file ends with `END OF ROUND`, and 1 at the timeout with the unsealed ones. Wait with nothing else: a completion notice, a task wait or a `pgrep` loop can return before the round is sealed, or never. When `run_round.py` exits non-zero first, handle its exit as above.

## 3. Check the round

Check every finding's quote against the version the reviewer was told to read:

```bash
python3 <skill-dir>/scripts/check_quotes.py <round file> --ref <head>   # scope `diff`: --worktree
```

Exit 2 means the round file doesn't end with `END OF ROUND`, so the round was cut: run it once more, and return a second failure to the caller with the error. Otherwise the script prints each finding as CONFIRMED or DISCARDED with the reason, or UNPARSED when its header or its quotes aren't in the shape `reviewer.md` sets: check those quotes by hand. A quote found at other lines of its file stands; the reason names where. A CONFIRMED finding with a block to check by hand has another block that matched: check that one before keeping the finding.

For `security`, trace each remaining finding yourself in that version, from the attacker's input to the sink, and test it against every exclusion and precedent in `references/lenses/security.md`. Discard one that a rule rules out, naming the rule (`E4`, `P2`), and one the code refutes, naming the line.

Done when every finding is confirmed or discarded.

## 4. Return

Called by a skill, return the round file, the discarded findings and the reviewer handle. Called by the user, list the confirmed findings most severe first, then the discarded ones with their reasons. When the `ReportFindings` tool is available, also report the confirmed findings with it, carrying each one's verdict and scenario.
