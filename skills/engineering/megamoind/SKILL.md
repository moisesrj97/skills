---
name: megamoind
description: "Delegate a ticket end to end, unattended: TDD implementation, quick review, real-app verification, draft PR, pair-review, ready for review and a CI loop until green. Use when the user hands over a ticket (a GitHub issue or a tracker ID such as a ClickUp task) to take all the way to a PR, e.g. \"megamoind PD-123\", \"llévate el #42 hasta la PR\", or when another skill delegates one ticket's implementation."
argument-hint: "<ticket ID> [base=<branch>] [brief=<file>] [stop-at=draft]"
---

# Megamoind

The user is delegating a whole ticket and walking away. The value is in coming back to a PR that is implemented, reviewed, verified in the real app and green in CI, plus a report that says exactly what was done and what wasn't. Every stop costs the user a context switch, so ask everything up front, then run on your own and stop only for **HITL**: a decision that is the user's (scope, product behaviour, a design trade-off, reversing something they decided) or a loop that isn't converging.

Invoking this skill is the user's approval to commit, push to the ticket's own branch, open the draft PR and mark it ready for review, each once the gates are green. Adding reviewers still waits for their explicit yes.

## Arguments

- `<ticket>`: a GitHub issue or an ID from the tracker the project's `## Ticket tracker` section names (e.g. ClickUp).
- `base=<branch>`: the branch to build on, e.g. the ticket below in a stack. Default: the default branch (`git symbolic-ref --short refs/remotes/origin/HEAD`). Every `<base>` below means this.
- `brief=<file>`: step 0 already answered by whoever delegated the ticket. Read it instead of asking; only what it leaves open is HITL.
- `stop-at=draft`: the caller owns ready-for-review and reviewers. Step 8 waits for the draft PR's CI instead, and step 10 is skipped.

## When a skill is not available

This skill delegates to `mattpocock-skills:tdd`, `code-review`, `mattpocock-skills:code-review`, `debug-trace`, `github-pr`, `pair-review` and `comment-cleanup`, called by these exact names. The two reviews are distinct: `code-review` takes an effort level and hunts bugs, `mattpocock-skills:code-review` checks standards and spec. If the Skill tool reports one as not available, stop and ask. An improvised copy silently skips whatever the real skill enforces.

## Gates

The checks that must be green before any push: type-check, lint and tests for **every project the change touches**. In a monorepo that means each touched package's own `ci` (or equivalent) script, not just the root. Read the commands from the project's `CLAUDE.md` / `CLAUDE.local.md`, else from each `package.json`; the package manager comes from the lockfile. Launch a long suite (several minutes) in the background from the start, so the foreground timeout can't kill it. Fix a red gate before pushing; never push past one, unless the red is **foreign** (see below).

## Steps

### 0. Brief and HITL check

Fetch the ticket (`gh issue view` for a GitHub issue, the tracker's tools otherwise); a tracker you can't reach is HITL. Read the ticket and the code it touches. With `brief=`, read it and go to step 1. Otherwise ask everything in **one** round, with your proposal for each:

- **Plan**: the approach in a few lines, the seams where tests go, and anything ambiguous in the ticket. When the ticket replaces or reproduces something already visible in the product, the plan keeps its current look and cites the **visual reference** (the screenshot, the live screen), and checks that the shape of the data (copy keys, props) can carry that look, e.g. one copy key can't style half its text.
- **Branch name**: the format in the project's `## Ticket tracker` section, else `<ticket-id>-<short-kebab-description>`, never a `/`.
- **Base** (GitButler): run `but pull --check`. When the workspace is behind and updating would move other branches, ask: "the workspace is N commits behind; updating would move X and Y. Update?". A no leaves the base stale: guard against a **borrowed green** (see "Sharing the workspace").
- **Verification**: how to run the app or service (the dev commands, required env, data or login, ports), and which flows prove the change works.
- **CODEOWNERS**: if the repo has one, marking the PR ready requests those reviewers automatically. Say so, since it defeats waiting to add reviewers.

Done when the user has confirmed the plan and you have everything needed to reach step 8 without asking again.

### 1. Branch

If the repo uses GitButler (`but status` works), create the branch with `but branch new <name>`, or `but branch new <name> --above <base>` when `base=` is a branch in the workspace, and do every commit and push with `but`. Otherwise update `<base>` and `git switch -c <name> <base>`. Under GitButler, update from the target (`but pull`) when only your branches are applied or the user said yes in step 0: moving other branches is their call.

### Sharing the workspace

Under GitButler, other agents' branches may be applied in the same working directory, so their unfinished changes show up in your type-check, tests and dev server. Commit only your own hunks (`but commit -b <branch> <ids>`, ids from `but diff`) and edit only files your ticket needs. A red gate is **foreign** when every failure sits in a file outside your branch's diff that `but status` shows changed by another branch or uncommitted outside yours. Leave a foreign red alone (fixing it would mix two tickets in one branch), list it for the report and count the gate as green.

The inverse is a **borrowed green**: another applied branch supplies hunks yours lacks (an import, a type, a helper), so your gates pass locally and CI, which builds your branch alone, fails. Your code may depend only on `<base>` and your own commits. A branch still applied but marked `(merged upstream)` in `but status` means your base is stale: update before implementing. When you can't update, check each symbol you use from a file other branches touch exists in `<base>` (`git show <base>:<file>`). CI settles both doubts, but only after the push; this check comes before it.

A change that belongs to the `<base>` branch's ticket goes on that branch, not yours: stop and ask for it, naming the change. When told the base moved, re-run the gates and go on.

### 2. Implement

Call the Skill tool with `mattpocock-skills:tdd` and build the ticket at the seams agreed in step 0. Run type-check and the single test files you are touching as you go; run the gates once at the end. Commit locally as you reach working checkpoints.

Done when every point of the ticket is implemented and the gates are green.

### 3. Quick review

Run two reviewers in parallel, each in its own agent: inside Herdr (`HERDR_ENV=1`), a pane split from yours (right if your pane is wide, down if tall) started with `herdr agent start <name> --kind claude --pane <id> -- --name <name>`, closed when its file is read; outside Herdr, two subagents launched in the same message.

- `code-review` at level `low` over `<base>...HEAD`;
- `mattpocock-skills:code-review` over the same range, pointed at the ticket as the spec.

Each writes its findings to its own file in the scratchpad, and **quotes** the cited lines under every finding. Neither edits code, posts anything, or uses `--fix` / `--comment`. Read both files: a finding is confirmed when the quote is there and you can trace its failure scenario in it; discard the rest with a one-line reason for the report. Fix the confirmed ones, with tests, and re-run the gates.

### 4. Verify in the real app

Start what the app needs as background subshells (`run_in_background`) with the commands from step 0, and stop every one you started when done. When the brief says the servers are already running, use them: a second copy fights for the same ports.

- **Frontend or fullstack**: drive the dev server in a real browser with whatever browser tooling this harness gives you (a browser-control skill, extension or MCP server; Playwright when there is nothing else). No way to drive a browser counts as an environment that won't come up. This step is an explicit request for browser verification, so tools a harness keeps for user-requested browser work (T3 Code's `preview_*`) apply here. Open a tab of your own, act only in it and close it when done: other agents may share the browser. Walk every flow the ticket touches on the dev server, and check each touched screen at 375, 900 and 1440 px for overlaps, clipped or mixed-language copy, and anything the ticket didn't ask for. Compare each screen against the visual reference from step 0, not just the ticket's text. To measure (bounding boxes, computed styles, visibility) or read text, evaluate a script in the page (`preview_evaluate`): a snapshot carries console, network and the accessibility tree, 10–20 KB each. Take a snapshot only for the final capture shown to the user (`save: true`).
- **Backend**: call the Skill tool with `debug-trace` and drive the changed paths through the running service, reading the trace to confirm the values the ticket expects.

Fix what you find, then re-verify. If the environment won't come up after one honest attempt, that's HITL; if it still can't run, record what went unverified for the PR description and the report.

Done when every flow from step 0 has been exercised and behaves as the ticket asks.

### 5. Draft PR

Call the Skill tool with `github-pr` to write the title and description and open the PR as a **draft**. The approval it asks for is already given: print them and go on without waiting for `approve`. Under GitButler, create the PR with `but pr new <branch> --draft -F <file>` (first line title, rest description) instead of `gh`: it pushes the branch and its ancestors and sets the right base in a stack. Mention anything left unverified from step 4.

### 6. Pair review

Call the Skill tool with `pair-review` with args `<PR number> high`. Collect the user's decisions from step 0 and any HITL answers as its already-decided list. It fixes, re-reviews and pushes the branch when done; its HITL stops are this skill's HITL stops.

### 7. Comment cleanup

Call the Skill tool with `comment-cleanup` over the whole branch diff (`<base>...HEAD`). Commit, run the gates, push.

### 8. Ready and CI loop

Mark the PR ready (`gh pr ready <number>`): some checks only run on ready PRs, so this is what launches the full CI. With `stop-at=draft`, leave it in draft and loop on the checks that run there. Loop until every check is green:

1. Wait for the checks to finish with `Monitor` or an until-loop on `gh pr checks <number>`, not a tight poll.
2. On a red check, diagnose with the tools at hand: a CI skill the project or the user has installed, `gh pr checks`, the job logs. Classify it:
   - **caused by this change**: fix it, run the gates, push;
   - **flaky or infrastructure**: re-run it once; red again is HITL;
   - **also red on `<base>`**: HITL, leave it alone.
3. Back to 1.

Stop with HITL after 3 fix pushes that haven't turned CI green: the loop isn't converging.

### 9. Report

- PR URL, branch, final CI state.
- Each review pass (quick review, pair-review rounds): findings, what was fixed, what was discarded and why.
- What was verified in the real app and how; what wasn't, and why.
- CI failures met and how each was resolved.
- Open HITL questions.

### 10. Reviewers (optional, skipped with `stop-at=draft`)

Ask whether to add reviewers, proposing names from CODEOWNERS or the recent history of the touched files. Run `gh pr edit <number> --add-reviewer …` only after the user's explicit yes.
