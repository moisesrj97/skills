---
name: diff-review
description: Runs one review round of a diff in a fresh reviewer agent of the chosen model (default Claude Opus 5.5) and returns quote-backed findings, without fixing. Use when asked for a diff-review or a review by a named or different model, or when a skill calls for one.
argument-hint: "[scope] [reviewer=<model>[:<effort>]] [standards=<file>,…]"
---

# Diff review

A reviewer that shares the author's context shares its blind spots. Each round runs in a fresh agent, from another model family when the caller asks for one, and every finding it returns has to quote the code it cites.

## Arguments

- **scope**: a PR number, a ref range (`base...head`) or `diff` (uncommitted work). When omitted, the current branch's PR (`gh pr view --json number`), else the diff against its base. For a stacked PR the meaningful diff is `<parent-branch>...<branch>`.
- **reviewer**: `<model id>[:<effort>]`, default `claude-opus-5-5:high`. A `claude-*` model runs on Claude, a `gpt-*` model on Codex, e.g. `gpt-6.1-sol:medium`.
- **standards**: files of rules the change is held to, on top of the project's own.
- From a calling skill: the round number, the already-decided list and, after round 1, the previous round's file, what changed since and the findings not acted on with their reasons.

## 1. Brief

The round file is `<scratch>/review-round-<N>.md`, in the session scratchpad when the system prompt lists one, else a fresh `mktemp -d`. Write the reviewer's prompt to `<scratch>/review-prompt-<N>.md`, with every item below that applies:

- First line: `You are the reviewer. Read <skill-dir>/references/reviewer.md and follow it.`, with the absolute path of the folder this skill loaded from.
- The scope and the exact command that shows the diff, with the range as given, since `a..b` and `a...b` differ.
- Which version of the code to read and quote. For a range, that is its head (`git show <head>:<file>`), since the checkout can hold other changes. For `diff`, it is the working tree.
- Where the round goes: the round file, or, for a CLI reviewer (step 2), the final message and no file writes.
- With `standards=`, their absolute paths, to read before reviewing. A breach is a finding that cites the rule.
- The already-decided list, phrased as "do not reopen unless you find new evidence that changes its severity".
- After round 1, the previous round file, the commits since (say if they are amended or unpushed, since the reviewer reads the local branch), which findings each resolves, and the findings not acted on with their reasons. Tell the reviewer to review the **whole** scope again, since fixes can break things elsewhere.

## 2. Launch

Every round gets a fresh reviewer, and earlier rounds reach it through the brief.

- **T3 Code** (`delegate_task` is available): `delegate_task` with `role: "review"`, `isolation: "shared"` and the target from `orchestrator_capabilities`, which is provider `claudeAgent` with option `effort`, or `codex` with option `reasoningEffort`. The child writes the round file. Wait for its completion notification.
- **Otherwise**: run the reviewer's CLI in the background from the repo root and wait for it to exit. The reviewer returns the round as its final message, and the command writes that to the round file. Its log goes to `<scratch>/review-round-<N>.log`; read only its tail, since the whole log floods the context.
  - Claude: `claude -p --model <model> --effort <effort> --permission-mode plan < <prompt file> > <round file> 2> <log>`
  - Codex: `codex exec -m <model> -c model_reasoning_effort='"<effort>"' -s read-only -C <repo> -o <round file> - < <prompt file> > /dev/null 2> <log>`

  Both modes are read-only, so the reviewer can't edit, commit or post whatever the prompt says.

## 3. Check the round

The round is complete when the round file ends with `END OF ROUND`. Without that seal the round was cut. Check the tail of the log and run it once more, and return a second failure to the caller with the error.

Then find each finding's quote in the version the reviewer was told to read. Discard a finding whose quote is missing or matches nothing there, with a one-line reason. A quote that matches at another line number stands. Done when every finding is confirmed or discarded.

## 4. Return

Called by a skill, return the round file and the discarded findings. Called by the user, list the confirmed findings most severe first, then the discarded ones with their reasons.
