---
name: pair-review
description: "Iterative review loop: a reviewer from another model family reviews the change through diff-review, you fix what it finds, and it re-reviews until nothing notable is left or a human decision is needed; then recap. Arguments: scope (PR number, ref range, or 'diff') and reviewer (default gpt-6.1-sol:medium)."
argument-hint: "[scope] [reviewer=<model>[:<effort>]]"
---

# Pair review

You are the **author**. A **reviewer**, by default from another model family, reviews your change through the `diff-review` skill. You triage what it finds, fix what deserves fixing, tell it what changed, and it reviews again. The point of a separate agent is an independent read: it has none of your context, so it doesn't share your blind spots. Your job is to keep that independence useful — fix real problems, don't relitigate settled ones, and stop when the reviews stop paying off.

## Arguments

- **scope**: what to review. A PR number (`34847`), a ref range (`base...head`), or `diff` (uncommitted work). If omitted, use the current branch's open PR (`gh pr view --json number`), else the diff against its base. For a stacked PR the meaningful diff is `<parent-branch>...<branch>`, not `master...`.
- **reviewer**: `<model id>[:<effort>]`, passed to `diff-review`. Default `gpt-6.1-sol:medium`.

State the resolved scope and reviewer in one line before starting.

## Round 0 — collect what is already decided

Before round 1, gather decisions the user has already made about this change in the conversation: findings they declined, trade-offs they accepted, things explicitly out of scope ("no cap for now", "one FF shared", "fallback not needed").

Why: a fresh reviewer will rediscover every accepted trade-off and report it again. Without this list, round 1 is mostly noise and you spend it explaining yourself.

## Each round

### Run the round

Call the Skill tool with `diff-review`, passing the scope, the reviewer, the round number and the already-decided list. From round 2 on, also pass the previous round file, the commits since (amended or unpushed included) with the findings each resolves, and the findings you did **not** act on, each with its reason (decided by the user / out of scope / disagree because …). Each round is a fresh reviewer that sees earlier rounds only through what you pass.

### Triage each finding

Read the round file `diff-review` returns, with the findings it discarded. Then put every finding into one bucket:

- **Fix**: a real defect or cheap, clearly-right improvement inside the scope of the change. Includes defects in the tests you wrote in an earlier round — those are common and the reviewer is good at catching them.
- **Already decided**: matches a user decision. Don't fix, don't ask again; add it to the already-decided list for the next round.
- **Needs the human (HITL)**: anything that is the user's call — reverses a decision they made, changes scope (a second concern in the PR), is a design alternative with real trade-offs, needs product/ops input, or new evidence makes a declined finding more severe. Stop the loop and ask, with your recommendation. Resume after they answer.
- **Disagree**: you believe it's wrong. Verify before dismissing (read the code, run it). If it still looks wrong, say why in the next round's not-acted-on list; if the next reviewer reports it again with a concrete scenario, treat it as HITL.

Report each round to the user briefly: counts per bucket, what you fixed, what you skipped and why.

### Fix

- Follow the project's own conventions (CLAUDE.md, lint, type-check, test commands) and the user's commit rules.
- Write or adjust tests with each fix. When a fix is a test, **prove it can fail**: break the code it guards (remove the middleware, corrupt the input) in a temporary copy, run it, see red, restore. A test that stays green under the mutation the reviewer described is the bug. Restore from a backup copy, and confirm with `git diff` that nothing leaked.
- Run type-check, lint and the relevant tests; the full suite before handing back.
- Commit locally. Amending your own unpushed commits from this loop is fine; never rewrite pushed history.
- Push once the loop ends **Done**, only to the change's own branch (`--force-with-lease` after amends), and only with type-check, lint and tests green. Posting to GitHub (comments, reviews, ready-for-review) still waits for the user.

## Stop conditions

- **Done**: the reviewer writes `NO FINDINGS`, or what remains is only nits you'd decline anyway.
- **HITL**: stop and ask (see triage). Keep the reviewer to message again when you resume.
- **Not converging**: after ~5 rounds, or when two consecutive rounds only produce findings about your previous round's fixes without the count falling, stop and tell the user — something structural is off, and more rounds won't fix it.

## Recap

Finish with:

| Round | Findings | Outcome |
|---|---|---|
| 1 | n | fixed X (what), skipped Y (decided / why) |
| … | | |
| last | 0 | done |

Then: commits created or amended (hashes, pushed or not), verification run (type-check, lint, tests, mutation checks), anything left pending (push, HITL questions), and one or two lines on how the loop itself went — what the reviewer caught that a single pass wouldn't, and anything to brief better next time.
