---
name: pair-review
description: "Iterative review loop with a dedicated reviewer agent (a Herdr pane, or a subagent outside Herdr): it runs /code-review at the given effort over the given scope, you fix what it finds, it re-reviews, until nothing notable is left or a human decision is needed; then recap. Arguments: scope (PR number, ref range, or 'diff') and effort (low|medium|high|xhigh|max; default high)."
disable-model-invocation: true
argument-hint: "[scope] [effort]"
---

# Pair review

You are the **author**. A second Claude, the **reviewer**, lives in a sibling Herdr pane and reviews your change with `/code-review`. You triage what it finds, fix what deserves fixing, tell it what changed, and it reviews again. The point of a separate agent is an independent read: it has none of your context, so it doesn't share your blind spots. Your job is to keep that independence useful — fix real problems, don't relitigate settled ones, and stop when the reviews stop paying off.

## Arguments

- **scope**: what to review. A PR number (`34847`), a ref range (`base...head`), or `diff` (uncommitted work). If omitted, use the current branch's open PR (`gh pr view --json number`), else the diff against its base. For a stacked PR the meaningful diff is `<parent-branch>...<branch>`, not `master...` — say so in the prompt.
- **effort**: passed straight to `/code-review` (`low|medium|high|xhigh|max`). Default `high`.

State the resolved scope and effort in one line before starting.

## Preconditions

- Check for Herdr: `test "${HERDR_ENV:-}" = 1`. Inside Herdr, run `herdr --skill` once if you haven't got its CLI conventions in context. Outside Herdr, use subagent mode (below) — never drive a Herdr session from outside it.
- Pick a scratchpad directory for the round files (the session scratchpad if the system prompt lists one, else a fresh `mktemp -d`). Findings travel through files, not through reading the reviewer's terminal: terminal scrollback is noisy, truncated and expensive to read.

## Round 0 — collect what is already decided

Before the first prompt, gather decisions the user has already made about this change in the conversation: findings they declined, trade-offs they accepted, things explicitly out of scope ("no cap for now", "one FF shared", "fallback not needed"). Put them in the first prompt.

Why: a fresh reviewer will rediscover every accepted trade-off and report it again. Without this list, round 1 is mostly noise and you spend it explaining yourself.

## Spawn the reviewer

1. Inspect the layout: `herdr pane layout --pane "$HERDR_PANE_ID"`. Split right if the pane is wide, down if tall.
   `herdr pane split --current --direction <right|down> --cwd "$PWD" --no-focus` → read `.result.pane.pane_id`.
2. Start it with matching Herdr and session names (use `reviewer`, or `reviewer-2` etc. if the name is taken in `herdr agent list`):
   `herdr agent start reviewer --kind claude --pane <pane-id> -- --name reviewer`

### Subagent mode (outside Herdr)

Same loop, different transport. Spawn one background subagent (Agent tool, `general-purpose`, named `reviewer`) whose prompt is the round 1 prompt below, telling it to invoke the `code-review` skill via the Skill tool with `<effort> <scope>`. You're notified when it finishes; read the round file. For each later round, continue **the same** agent with SendMessage rather than spawning a new one, so it keeps its earlier findings and your explanations. There's no pane to close: just stop messaging it.

## Each round

### Prompt the reviewer

In Herdr, send with `herdr agent prompt reviewer "<prompt>" --wait --timeout 1500000`, run in the **background** (reviews take minutes; you'll be notified), then read the round file. In subagent mode, use the Agent tool / SendMessage as above.

Round 1 prompt contains:
- `/code-review <effort> <scope>` as the first line, so the skill actually runs.
- The exact diff to review (for stacks: `<parent>...<branch>`).
- Hard rules: do not edit files, commit, push, or post anything on GitHub (no `--fix`, no `--comment`). The reviewer reports; you change code.
- The already-decided list from round 0, phrased as "do not reopen unless you find new evidence that changes its severity".
- Where to write: `<scratch>/review-round-1.md` — verified findings most severe first, each with `file:line`, summary, concrete failure scenario, severity; or the literal `NO FINDINGS`.

Round N+1 prompt contains:
- What changed since its last review: commit hashes (say if amended or unpushed — the reviewer reads the local branch), and which of its findings each change resolves.
- Findings you did **not** act on, each with the reason (decided by the user / out of scope / disagree because …).
- Ask for a fresh `/code-review <effort>` over the **whole** scope, not just the new commits — fixes can break things elsewhere.
- New output file `<scratch>/review-round-<N+1>.md`.

### Triage each finding

Read the round file and put every finding into one bucket:

- **Fix**: a real defect or cheap, clearly-right improvement inside the scope of the change. Includes defects in the tests you wrote in an earlier round — those are common and the reviewer is good at catching them.
- **Already decided**: matches a user decision. Don't fix, don't ask again; tell the reviewer it's settled.
- **Needs the human (HITL)**: anything that is the user's call — reverses a decision they made, changes scope (a second concern in the PR), is a design alternative with real trade-offs, needs product/ops input, or new evidence makes a declined finding more severe. Stop the loop and ask, with your recommendation. Resume after they answer.
- **Disagree**: you believe it's wrong. Verify before dismissing (read the code, run it). If it still looks wrong, say why in the next prompt; if the reviewer insists with a concrete scenario, treat it as HITL.

Report each round to the user briefly: counts per bucket, what you fixed, what you skipped and why.

### Fix

- Follow the project's own conventions (CLAUDE.md, lint, type-check, test commands) and the user's commit rules.
- Write or adjust tests with each fix. When a fix is a test, **prove it can fail**: break the code it guards (remove the middleware, corrupt the input) in a temporary copy, run it, see red, restore. A test that stays green under the mutation the reviewer described is the bug. Restore from a backup copy, and confirm with `git diff` that nothing leaked.
- Run type-check, lint and the relevant tests; the full suite before handing back.
- Commit locally. Amending your own unpushed commits from this loop is fine; never rewrite pushed history.
- **Never push or post to GitHub during the loop** without asking the user — the loop's approval doesn't extend to outward actions.

## Stop conditions

- **Done**: the reviewer writes `NO FINDINGS`, or what remains is only nits you'd decline anyway. Close the pane: `herdr pane close <pane-id>`.
- **HITL**: stop and ask (see triage). Keep the pane alive while you wait.
- **Not converging**: after ~5 rounds, or when two consecutive rounds only produce findings about your previous round's fixes without the count falling, stop and tell the user — something structural is off, and more rounds won't fix it.

In Herdr, if the reviewer errors out, stalls (`agent_prompt_stalled`), or sits `blocked` on an approval dialog, inspect it with `herdr agent read reviewer` and tell the user instead of answering dialogs for it.

## Recap

Finish with:

| Round | Findings | Outcome |
|---|---|---|
| 1 | n | fixed X (what), skipped Y (decided / why) |
| … | | |
| last | 0 | pane closed |

Then: commits created or amended (hashes, pushed or not), verification run (type-check, lint, tests, mutation checks), anything left pending (push, HITL questions), and one or two lines on how the loop itself went — what the reviewer caught that a single pass wouldn't, and anything to brief better next time.
