---
name: megamoind
description: "Delegate a ticket end to end, unattended: TDD implementation, quick review, real-app verification, draft PR, pair-review, ready for review and a CI loop until green. Use when the user hands over a ticket (a GitHub issue or a tracker ID such as a ClickUp task) to take all the way to a PR, e.g. \"megamoind PD-123\", \"llévate el #42 hasta la PR\", or when another skill delegates one ticket's implementation."
argument-hint: "<ticket ID: GitHub issue or tracker ID>"
---

# Megamoind

The user is delegating a whole ticket and walking away. The value is in coming back to a PR that is implemented, reviewed, verified in the real app and green in CI, plus a report that says exactly what was done and what wasn't. Every stop costs the user a context switch, so ask everything up front, then run on your own and stop only for **HITL**: a decision that is the user's (scope, product behaviour, a design trade-off, reversing something they decided) or a loop that isn't converging.

Invoking this skill is the user's approval to commit, push to the ticket's own branch, open the draft PR and mark it ready for review, each once the gates are green. Adding reviewers still waits for their explicit yes.

## When a skill is not available

This skill delegates to `tdd`, `code-review`, `mattpocock-skills:code-review`, `claude-in-chrome`, `debug-trace`, `github-pr`, `pair-review` and `comment-cleanup`. If the Skill tool reports one as not available, stop and ask. An improvised copy silently skips whatever the real skill enforces.

## Gates

The checks that must be green before any push: type-check, lint and tests for **every project the change touches**. In a monorepo that means each touched package's own `ci` (or equivalent) script, not just the root. Read the commands from the project's `CLAUDE.md` / `CLAUDE.local.md`, else from each `package.json`; the package manager comes from the lockfile. Fix a red gate before pushing; never push past one.

## Steps

### 0. Brief and HITL check

Fetch the ticket: a GitHub issue with `gh issue view`, any other ID from the tracker the project's `## Ticket tracker` section names (e.g. ClickUp). No ticket ID, or a tracker you can't reach: ask for it. Read the ticket and the code it touches. Then ask everything in **one** round, with your proposal for each:

- **Plan**: the approach in a few lines, the seams where tests go, and anything ambiguous in the ticket.
- **Branch name**: the format in the project's `## Ticket tracker` section, else `<ticket-id>-<short-kebab-description>`, never a `/`.
- **Verification**: how to run the app or service (the dev commands, required env, data or login, ports), and which flows prove the change works.
- **CODEOWNERS**: if the repo has one, marking the PR ready requests those reviewers automatically. Say so, since it defeats waiting to add reviewers.

Done when the user has confirmed the plan and you have everything needed to reach step 8 without asking again.

### 1. Branch

Update the default branch (`git symbolic-ref --short refs/remotes/origin/HEAD`). If the repo uses GitButler (`but status` works), create the branch with `but branch new <name>` and do every commit and push with `but`; otherwise `git switch -c <name>`. Other agents may be working in the same repo: touch only this ticket's changes.

### 2. Implement

Call the Skill tool with `tdd` and build the ticket at the seams agreed in step 0. Run type-check and the single test files you are touching as you go; run the gates once at the end. Commit locally as you reach working checkpoints.

Done when every point of the ticket is implemented and the gates are green.

### 3. Quick review

Spawn two background subagents in the same turn, one per review, so they run in parallel:

- `code-review` at level `low` over `<default-branch>...HEAD`;
- `mattpocock-skills:code-review` over the same range, pointed at the ticket as the spec.

Each writes its findings to its own file in the scratchpad, and **quotes** the cited lines under every finding. Neither edits code, posts anything, or uses `--fix` / `--comment`. Read both files: a finding is confirmed when the quote is there and you can trace its failure scenario in it; discard the rest with a one-line reason for the report. Fix the confirmed ones, with tests, and re-run the gates.

### 4. Verify in the real app

Start what the app needs as background subshells (`run_in_background`) with the commands from step 0, and stop every one you started when done.

- **Frontend or fullstack**: call the Skill tool with `claude-in-chrome`. Walk every flow the ticket touches on the dev server, and check each touched screen at 375, 900 and 1440 px for overlaps, clipped or mixed-language copy, and anything the ticket didn't ask for.
- **Backend**: call the Skill tool with `debug-trace` and drive the changed paths through the running service, reading the trace to confirm the values the ticket expects.

Fix what you find, then re-verify. If the environment won't come up after one honest attempt, that's HITL; if it still can't run, record what went unverified for the PR description and the report.

Done when every flow from step 0 has been exercised and behaves as the ticket asks.

### 5. Draft PR

Push the branch, then call the Skill tool with `github-pr` to open it as a **draft**. The approval it asks for is already given: print the title and description and create the PR without waiting for `approve`. Mention anything left unverified from step 4.

### 6. Pair review

Call the Skill tool with `pair-review` with args `<PR number> high`. Collect the user's decisions from step 0 and any HITL answers as its already-decided list. It fixes, re-reviews and pushes the branch when done; its HITL stops are this skill's HITL stops.

### 7. Comment cleanup

Call the Skill tool with `comment-cleanup` over the whole branch diff (`<default-branch>...HEAD`). Commit, run the gates, push.

### 8. Ready and CI loop

Mark the PR ready (`gh pr ready <number>`): some checks only run on ready PRs, so this is what launches the full CI. Then loop until every check is green:

1. Wait for the checks to finish with `Monitor` or an until-loop on `gh pr checks <number>`, not a tight poll.
2. On a red check, diagnose with the tools at hand: a CI skill the project or the user has installed, `gh pr checks`, the job logs. Classify it:
   - **caused by this change**: fix it, run the gates, push;
   - **flaky or infrastructure**: re-run it once; red again is HITL;
   - **also red on the default branch**: HITL, leave it alone.
3. Back to 1.

Stop with HITL after 3 fix pushes that haven't turned CI green: the loop isn't converging.

### 9. Report

- PR URL, branch, final CI state.
- Each review pass (quick review, pair-review rounds): findings, what was fixed, what was discarded and why.
- What was verified in the real app and how; what wasn't, and why.
- CI failures met and how each was resolved.
- Open HITL questions.

### 10. Reviewers (optional)

Ask whether to add reviewers, proposing names from CODEOWNERS or the recent history of the touched files. Run `gh pr edit <number> --add-reviewer …` only after the user's explicit yes.
