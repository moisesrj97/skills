---
name: pair-review
description: "Reviews your own change in a loop: a reviewer from another model family reviews it through diff-review, you fix its findings, and it re-reviews until done or a human must decide. Use when asked for a pair-review or a review-and-fix loop. Not for a teammate's PR; use pr-review."
argument-hint: "[scope] [reviewer=<model>[:<effort>]] [spec=<file>] [standards=<file>,…]"
---

# Pair review

You are the **author**. A **reviewer**, by default from another model family, reviews your change through the `diff-review` skill. You triage what it finds, fix what deserves fixing, tell it what changed, and it reviews again. Its value is an independent read from an agent without your context or your blind spots. Every round goes to the **same reviewer**, so it remembers what it reported and judges your fixes against its own findings. Keep that read useful: fix real problems, leave settled ones settled, hold every round to the change's scope, and stop when the reviews stop paying off. Scope creep is what breaks the loop: every edit beyond a finding is new diff the reviewer re-reads and new findings it can raise, so the rounds stop converging.

## Arguments

- **scope**: what to review. A PR number (`34847`), a ref range (`base...head`), or `diff` (uncommitted work). If omitted, use the current branch's open PR (`gh pr view --json number`), else the diff against its base. For a stacked PR the meaningful diff is `<parent-branch>...<branch>`, not `master...`.
- **reviewer**: `<model id>[:<effort>]`, passed to `diff-review`. Default `gpt-6.1-sol:medium`.
- **spec**: a file with what the change must do (a ticket, a brief), passed to `diff-review` every round.
- **standards**: files of rules the change is held to, passed to `diff-review` every round.

State the resolved scope and reviewer in one line before starting.

## Round 0. Collect the already-decided list

Before round 1, gather the decisions the user has already made about this change in the conversation: findings they declined, trade-offs they accepted, things explicitly out of scope ("no cap for now", "one FF shared", "fallback not needed").

The reviewer starts fresh in round 1 and rediscovers every accepted trade-off and reports it again. Without this list, round 1 is mostly noise and you spend it explaining yourself.

## Each round

### Run the round

Call the Skill tool with `diff-review`, passing the scope, the reviewer, the spec, the standards, the round number and the already-decided list. Keep the reviewer handle `diff-review` returns in round 1. From round 2 on, also pass that handle, the commits since (amended or unpushed included) with the findings each resolves, and the findings you did **not** act on, each with its reason (decided by the user / out of scope / disagree because …). When a round returns a new handle (the old reviewer was gone), keep the new one.

### Triage each finding

Read the round file `diff-review` returns, with the findings it discarded. A PLAUSIBLE finding comes with a `Confirm by`: check that first, so it reaches its bucket confirmed or refuted. Then put every finding into one bucket:

- **Fix**: a defect the change introduced, or a cheap, clearly right improvement to lines the change itself adds or modifies. This includes defects in the tests you wrote in an earlier round, which are common and which the reviewer catches well.
- **Out of scope**: a real issue the change did not introduce: pre-existing code, a neighbouring module, a wider refactor the finding suggests. Leave the code as it is, record it as a follow-up for the recap, and pass it in the next round's not-acted-on list as out of scope.
- **Already decided**: matches a user decision. Leave it unfixed without asking again, and add it to the already-decided list for the next round.
- **Needs the human (HITL)**: anything that is the user's call. It reverses a decision they made, needs an out-of-scope change for this change to be correct (a second concern in the PR), is a design alternative with real trade-offs, needs product or ops input, or new evidence makes a declined finding more severe. Stop the loop and ask, with your recommendation. Resume after they answer.
- **Disagree**: you believe it's wrong. Verify before dismissing (read the code, run it). If it still looks wrong, say why in the next round's not-acted-on list. If the reviewer reports it again with a concrete scenario after reading your reason, treat it as HITL.

Done when every finding sits in one bucket. Report each round to the user briefly: counts per bucket, what you fixed, what you skipped and why.

### Fix

- Make the smallest fix that closes the finding. Refactors, renames and tidying the finding doesn't ask for wait for a follow-up, even when cheap. Before committing, read the fix's diff and revert every hunk no finding asks for.
- Follow the project's own conventions (CLAUDE.md, lint, type-check, test commands) and the user's commit rules.
- Write or adjust tests with each fix. When a fix is a test, **prove it can fail**. Break the code it guards (remove the middleware, corrupt the input) in a temporary copy, run the test, see red, and restore. A test that stays green under the mutation the reviewer described is the bug. Restore from a backup copy, and confirm with `git diff` that nothing leaked.
- Run type-check, lint and the relevant tests, and the full suite before handing back.
- Commit locally. You may amend your own unpushed commits from this loop, and pushed history stays as it is.
- Push once the loop ends **Done**, only to the change's own branch (`--force-with-lease` after amends), and only with type-check, lint and tests green. Posting to GitHub (comments, reviews, ready-for-review) still waits for the user.

## Stop conditions

- **Done**: the reviewer writes `NO FINDINGS`, or what remains is only nits you'd decline anyway.
- **HITL**: stop and ask (see triage). Keep the reviewer handle and continue the same reviewer when you resume.
- **Not converging**: after about 5 rounds, or when two consecutive rounds only produce findings about your previous round's fixes without the count falling, stop and tell the user. Something structural is off, and more rounds won't fix it.

## Recap

Finish with:

| Round | Findings | Outcome |
|---|---|---|
| 1 | n | fixed X (what), skipped Y (decided / why) |
| … | | |
| last | 0 | done |

Then list the commits created or amended (hashes, pushed or not), the verification run (type-check, lint, tests, mutation checks), anything left pending (push, HITL questions), the out-of-scope follow-ups, and one or two lines on how the loop went, including what the reviewer caught that a single pass wouldn't and anything to brief better next time.
