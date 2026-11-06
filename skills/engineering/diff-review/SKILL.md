---
name: diff-review
description: Runs one review round of a diff in a separate reviewer agent of the chosen model and returns quote-backed findings, without fixing. Use when asked for a diff-review or a review by a named or different model, or when a skill calls for one.
argument-hint: "[scope] [lens=code|security|cleanup] [reviewer=<model>[:<effort>]] [spec=<file>] [standards=<file>,…]"
---

# Diff review

A reviewer that shares the author's context shares its blind spots. The reviewer runs in its own agent, from another model family when the caller asks for one, and every finding it returns has to quote the code it cites. Round 1 starts it fresh. Later rounds of a loop continue the same reviewer, so it remembers what it already reported and checks the fixes against its own findings.

## Arguments

- **scope**: a PR number, a ref range (`base...head`) or `diff` (uncommitted work). When omitted, the current branch's PR (`gh pr view --json number`), else the diff against its base. For a stacked PR the meaningful diff is `<parent-branch>...<branch>`.
- **lens**: what the reviewer looks for, from `references/lenses/<lens>.md`. `code` (default): bugs, each with a failure scenario. `cleanup`: code that works but costs, each with that cost.
- **reviewer**: `<model id>[:<effort>]`. Default `claude-opus-5-5:high`, or `claude-opus-5-5:medium` for `cleanup`. A `claude-*` model runs on Claude, a `gpt-*` model on Codex, e.g. `gpt-6.1-sol:medium`.
- **spec**: a file with what the change must do (a ticket, a brief). The `code` lens checks the change against it.
- **standards**: files of rules the change is held to, on top of the project's own.
- From a calling skill: the round number, the already-decided list and, after round 1, the **reviewer handle** this skill returned in round 1, what changed since and the findings not acted on with their reasons.

## 1. Brief

The round file is `<scratch>/review-round-<N>.md`, in the session scratchpad when the system prompt lists one, else a fresh `mktemp -d`. Write the reviewer's prompt to `<scratch>/review-prompt-<N>.md`, with every item below that applies:

- First line: `You are the reviewer. Read <skill-dir>/references/reviewer.md and <skill-dir>/references/lenses/<lens>.md and follow them.`, with the absolute path of the folder this skill loaded from.
- The scope and the exact command that shows the diff, with the range as given, since `a..b` and `a...b` differ.
- Which version of the code to read and quote. For a range, that is its head (`git show <head>:<file>`), since the checkout can hold other changes. For `diff`, it is the working tree.
- Where the round goes: the round file, or, for a CLI reviewer (step 2), the final message and no file writes.
- With `spec=` and `standards=`, their absolute paths, to read before reviewing.
- The already-decided list, phrased as "do not reopen unless you find new evidence that changes its severity". A PLAUSIBLE finding the author declined belongs on it.
- After round 1, the commits since (say if they are amended or unpushed, since the reviewer reads the local branch), which findings each resolves, and the findings not acted on with their reasons. Tell the reviewer to review the **whole** scope again, since fixes can break things elsewhere, and to write the new round file.

A continued reviewer already holds its instructions, the scope, the spec, the standards and its earlier rounds, so its prompt from round 2 on carries only the round file path, the already-decided list and the items of the last bullet. A fresh reviewer gets every item, plus the previous round file.

## 2. Launch

Round 1, or a round with no handle, starts a fresh reviewer and records its **reviewer handle**. A round with a handle continues that reviewer. Continuing the same reviewer is deliberate, so do it even where a harness suggests a new agent for every re-check.

- **T3 Code** (`delegate_task` is available). Fresh: `delegate_task` with `role: "review"`, `isolation: "shared"` and the target from `orchestrator_capabilities`, which is provider `claudeAgent` with option `effort`, or `codex` with option `reasoningEffort`. The handle is the child's thread id. Continue: `t3_thread_send` to that thread with the prompt. The child writes the round file. Wait for its completion notification.
- **Otherwise**: run the reviewer's CLI in the background from the repo root and wait for it to exit. The reviewer returns the round as its final message, and the command writes that to the round file. Its log goes to `<scratch>/review-round-<N>.log`; read only its tail, since the whole log floods the context.
  - Claude, fresh: generate a UUID (`uuidgen`), which is the handle, and run `claude -p --session-id <uuid> --model <model> --effort <effort> --permission-mode plan < <prompt file> > <round file> 2> <log>`. Continue: the same command with `--resume <uuid>` in place of `--session-id <uuid>`.
  - Codex, fresh: `codex exec -m <model> -c model_reasoning_effort='"<effort>"' -s read-only -C <repo> --json -o <round file> - < <prompt file> > <scratch>/review-events.jsonl 2> <log>`. The handle is `jq -r 'select(.type=="thread.started").thread_id' <scratch>/review-events.jsonl`. Continue: `codex exec resume -m <model> -c model_reasoning_effort='"<effort>"' -c sandbox_mode='"read-only"' -o <round file> <handle> - < <prompt file> > /dev/null 2> <log>`, run from the repo root, since `resume` takes no `-s` or `-C`.

  Every mode is read-only, so the reviewer can't edit, commit or post whatever the prompt says.

When a continue fails (the session or thread is gone), start a fresh reviewer for this round with the full prompt, and return its new handle.

## 3. Check the round

The round is complete when the round file ends with `END OF ROUND`. Without that seal the round was cut. Check the tail of the log and run it once more, and return a second failure to the caller with the error.

Then find each finding's quote in the version the reviewer was told to read. Discard a finding whose quote is missing or matches nothing there, with a one-line reason. A quote that matches at another line number stands. Done when every finding is confirmed or discarded.

## 4. Return

Called by a skill, return the round file, the discarded findings and the reviewer handle. Called by the user, list the confirmed findings most severe first, then the discarded ones with their reasons. When the `ReportFindings` tool is available, also report the confirmed findings with it, carrying each one's verdict and scenario.
