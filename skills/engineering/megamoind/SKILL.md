---
name: megamoind
description: "Delegate a ticket end to end, unattended: TDD implementation, tidying, security review, pair-review, real-app verification, a PR ready for review and a CI loop until green. Use when the user hands over one ticket (a GitHub issue or a tracker ID such as a ClickUp task) to take all the way to a PR, e.g. \"megamoind PD-123\", \"llévate el #42 hasta la PR\", or when another skill delegates one ticket's implementation. Several tickets go to megamoind-batch."
argument-hint: "<ticket ID> [base=<branch>] [brief=<file>] [stop-at=draft]"
---

# Megamoind

The user delegates a whole ticket and walks away. They come back to a PR that is implemented, reviewed, verified in the real app and green in CI, plus a report that says exactly what was done and what wasn't. Every stop costs the user a context switch, so ask everything up front, then run on your own and stop only for **HITL**: a decision that is the user's (scope, product behaviour, a design trade-off, reversing something they decided) or a loop that isn't converging.

Invoking this skill is the user's approval to commit, push to the ticket's own branch and open the PR ready for review, each once the gates are green. Adding reviewers still waits for their explicit yes.

**One ticket per run.** More than one (a list, a label or other tracker query, a spec) is a **batch**: call the Skill tool with `megamoind-batch`, passing the user's request, and follow it instead of this skill.

## Arguments

- `<ticket>`: a GitHub issue or an ID from the tracker the project's `## Ticket tracker` section names (e.g. ClickUp).
- `base=<branch>`: the branch to build on, e.g. the ticket below in a stack. Default: the default branch (`git symbolic-ref --short refs/remotes/origin/HEAD`). Every `<base>` below means this.
- `brief=<file>`: step 0 already answered by whoever delegated the ticket. Read it instead of asking; only what it leaves open is HITL.
- `stop-at=draft`: the caller owns ready-for-review and reviewers. Step 7 opens the PR as a draft, step 8 loops on the checks that run on drafts, and step 10 is skipped.

## When a skill is not available

This skill hands off to `megamoind-batch`, `craftsmanship`, `mattpocock-skills:diagnosing-bugs`, `mattpocock-skills:tdd`, `diff-review`, `debug-trace`, `merge-risk`, `github-pr`, `pair-review` and `comment-cleanup`, called by these exact names. If the Skill tool reports one as not available, stop and ask. An improvised copy silently skips whatever the real skill enforces.

## Gates

The checks that must be green before any push: type-check, lint and tests for **every project the change touches**. In a monorepo that means each touched package's own `ci` (or equivalent) script as well as the root's.

- Read the commands from the project's `CLAUDE.md` / `CLAUDE.local.md`, else from each `package.json`. The lockfile names the package manager.
- Launch a long suite (several minutes) in the background from the start, so the foreground timeout can't kill it.
- If the project has `yarn dev:doctor`, run `yarn dev:doctor --flow <flow> --no-services` before the first type-check and after any pull that touches `packages/`. It rebuilds stale workspace builds, which otherwise read as a red gate.
- A heavy spec that times out under full-suite load counts as red only after it fails again in isolation.
- Run checks as wide as the project's scripts do, but point every auto-fix (`--write`, `--fix`, a formatter) at the files of your branch's diff only. One aimed at a whole folder rewrites files outside the ticket and can break them, e.g. by dropping a `@ts-expect-error`.
- Before each commit, check it holds only your ticket's files (`but diff` under GitButler, `git diff --stat` otherwise).
- A commit hook that runs lint-staged reads the config in the working tree. When one change both adds a lint or format rule and fixes the files it flags, commit in the order fixes, then pure formatting, then the config, adding the new rule to the working tree only for that last commit.

Push only with every gate green or **foreign** (see "Sharing the workspace").

## Docs or skill changes

When the diff holds no code (a README, a skill, a recipe), the steps keep their shape and change what they test:

- **Gates**: links and anchors resolve.
- **Step 2**: the test is each claim the doc makes, checked against the code it documents and cited with `file:line`, plus its code snippets type-checked against the real types. A skill with a `benchmark/evals.json` gets one new eval per behaviour change, with the opposite case as a control.
- **Step 5**: run every command or snippet the doc adds exactly as written, in the real app. For a skill, run each new eval prompt in a fresh agent that reads only the skill.
- **Step 6** is skipped.

## Steps

### 0. Brief and HITL check

Fetch the ticket (`gh issue view` for a GitHub issue, the tracker's tools otherwise); a tracker you can't reach is HITL. Read the ticket and the code it touches, and look for what the change can **reuse**: helpers, a similar feature, how the neighbouring tests are written. Call the Skill tool with `craftsmanship`. For a bug, call the Skill tool with `mattpocock-skills:diagnosing-bugs` and take it through phase 4, so the plan names the confirmed cause; its fix waits for step 2.

With `brief=`, read it, settle on your own whatever of the plan below it leaves open (only the user's decisions are HITL), and go to step 1. Otherwise ask everything in **one** round, with your proposal for each. Each option states only consequences you checked in code or data this session: grep the consumer before claiming "with X, Y happens", and mark anything unchecked "unverified: …". An option that extends scope to a sibling case ("X has the same bug") quotes the routing line that sends the user's action into that code, found by tracing every call site.

- **Plan**: the approach in a few lines, what it reuses, the seams where tests go with what each buys and sells (Test Desiderata), the tidyings worth doing first or after and where each goes by area of impact (Tidy First), and anything ambiguous in the ticket. When the ticket replaces or reproduces something already visible in the product, the plan keeps its current look, cites the **visual reference** (the screenshot, the live screen), and checks that the shape of the data (copy keys, props) can carry that look, e.g. one copy key can't style half its text.
- **Branch name**: the format in the project's `## Ticket tracker` section, else `<ticket-id>-<short-kebab-description>`, with no `/`. A pre-PR or post-PR from the plan adds `<name>-tidy-first` or `<name>-tidy-after`.
- **Base** (GitButler): run `but pull --check`. When the workspace is behind and updating would move other branches, ask: "the workspace is N commits behind; updating would move X and Y. Update?". A no leaves the base stale, so guard against a **borrowed green** (see "Sharing the workspace").
- **Verification**: how to run the app or service (the dev commands, required env, data or login, ports), and which flows prove the change works.
- **CODEOWNERS**: if the repo has one, opening the PR ready for review requests those reviewers automatically. Say so, since it defeats waiting to add reviewers.
- **Required checks**: the names CI must turn green, from the project's `CLAUDE.md` / `CLAUDE.local.md`, else the base's rules (`gh api repos/{owner}/{repo}/rules/branches/<base>`, the `required_status_checks` entries). If neither gives them, ask. `gh pr checks --required` lists only the checks already reported, so it can't tell you one is missing. Split them into checks that run on drafts and ready-only ones (e.g. a Jenkins job that builds only non-draft PRs whose base is the default branch).
- **Screenshots** (frontend changes): the PR gets them through `gh-attach`, which needs gh ≥ 2.99. Check `gh --version` now; if it is older, ask the user to upgrade.
- **Ticket description**: ask whether to copy the brief's product decisions (what changes, UI choices, acceptance criteria) into the ticket's description. On a yes, write them into the description, keeping its existing content, never as a comment.

Done when the user has confirmed the plan and you have everything needed to reach step 8 without asking again. Write the confirmed brief to `<scratchpad>/<ticket>-brief.md`, and re-read it whenever a later step needs a decision from step 0.

### 1. Branch

If the repo uses GitButler (`but status` works), create the branch with `but branch new <name>`, or `but branch new <name> --above <base>` when `base=` is a branch in the workspace, and do every commit and push with `but`. Otherwise update `<base>` and `git switch -c <name> <base>`. Under GitButler, update from the target (`but pull`) when only your branches are applied or the user said yes in step 0, since moving other branches is their call. When updating the base changed a lockfile, reinstall dependencies with the project's package manager and restart any dev server already running, before anything else runs.

With a pre-PR, create `<name>-tidy-first` on `<base>` as above. Under GitButler, create the ticket's branch on top of it now (`--above <name>-tidy-first`), so commits to the lower branch restack it. With plain git, create it once the pre-PR's commits are in (`git switch -c <name> <name>-tidy-first`, end of step 2's first pass), since a branch created earlier stays on the old commit. These branches, plus a post-PR's, are the ticket's **layers**, bottom to top; `HEAD` in the ranges below is the top layer. With plain git, after any later commit on a lower layer (a review fix, a CI fix), rebase each layer above onto it, bottom up (`git rebase <lower> <upper>`), then switch back to the top layer; once they are pushed, push them with `--force-with-lease`.

### Sharing the workspace

Under GitButler, other agents' branches may be applied in the same working directory, so their unfinished changes show up in your type-check, tests and dev server. Commit only your own hunks (`but commit -b <branch> <ids>`, ids from `but diff`) and edit only files your ticket needs. A red gate is **foreign** when every failure sits in a file outside your branch's diff that `but status` shows changed by another branch or uncommitted outside yours. A change you produced yourself, e.g. a formatter or codegen run, is never foreign, even uncommitted. Leave a foreign red alone (fixing it would mix two tickets in one branch), list it for the report and count the gate as green. Their edits also hot-reload into your dev server: a checker overlay naming files outside your diff is foreign, so remove it from the DOM and go on, and when the UI stops reacting after a burst of hot updates you didn't cause, reload the page before debugging.

The inverse is a **borrowed green**: another applied branch supplies hunks yours lacks (an import, a type, a helper), so your gates pass locally and CI, which builds your branch alone, fails. Your code may depend only on `<base>` and your own commits. A branch still applied but marked `(merged upstream)` in `but status` means your base is stale, so update before implementing. When you can't update, check that each symbol you use from a file other branches touch exists in `<base>` (`git show <base>:<file>`). CI settles both doubts, but only after the push; this check comes before it.

A change that belongs to the `<base>` branch's ticket goes on that branch. Stop and ask for it, naming the change. When told the base moved, re-run the gates and go on.

### 2. Implement

Three passes, with structure and behaviour always in separate commits:

1. **Tidy first**: the plan's first tidyings, as the PR's first `refactor:` commit or on the pre-PR branch, following `craftsmanship`.
2. **Behaviour**: call the Skill tool with `mattpocock-skills:tdd` and build the ticket at the seams agreed in step 0, reusing what step 0 found. For a bug, the diagnosis loop from step 0 is the first red test; once it is green, run `diagnosing-bugs` phase 6 (its instrumentation and throwaway harnesses removed, the original reproduction rerun) before committing.
3. **Tidy after**: run `craftsmanship`'s *Tidy a diff* over `<base>...HEAD`. It places each tidying by area of impact: a `refactor:` commit on the ticket's branch, or the post-PR branch `<name>-tidy-after` on top of it. One that is Later goes on a list for the report.

Run type-check and the single test files you are touching as you go, and the gates once at the end. Commit locally at each working checkpoint.

When the brief rules out tests, write a **failure-path checklist** to the scratchpad before step 3: for every async call or batch, its partial failure, total failure and empty result, plus the id types that cross a `String()`/`Number()` conversion. Each item is handled in code or marked accepted.

Done when every point of the ticket is implemented, every planned tidying has landed or moved to Later, every checklist item is handled or accepted, and the gates are green.

### 3. Security review

Call the Skill tool with `diff-review` with `lens=security` over `<base>...HEAD`. One round, with no loop: step 4 reviews the whole change again, these fixes included.

Done when every finding it returns is fixed with a test that fails without the fix, or discarded with a one-line reason for the report, and the gates are green.

### 4. Pair review

Call the Skill tool with `pair-review` with args `<base>...HEAD spec=<scratchpad>/<ticket>-brief.md standards=<craftsmanship's test-desiderata.md, absolute path>`, passing the user's decisions from step 0 and any HITL answers as its already-decided list. A finding fixed by a tidying goes on the layer its area of impact picks. It fixes and re-reviews until done; its HITL stops are this skill's HITL stops.

### 5. Verify in the real app

Start what the app needs as background subshells (`run_in_background`) with the commands from step 0, and stop every one you started when done. When the brief says the servers are already running, use them, since a second copy fights for the same ports.

- **Frontend or fullstack**: drive the dev server in a real browser with whatever browser tooling this harness gives you (a browser-control skill, extension or MCP server; Playwright when there is nothing else). No way to drive a browser counts as an environment that won't come up. This step is an explicit request for browser verification, so tools a harness keeps for user-requested browser work (T3 Code's `preview_*`) apply here. Other agents may share the browser, so open a tab of your own, act only in it and close it when done.
  - Walk every flow the ticket touches and check each touched screen at 375, 900 and 1440 px for overlaps, clipped or mixed-language copy, and anything the ticket didn't ask for. Compare each screen against the visual reference from step 0 as well as the ticket's text.
  - To measure (bounding boxes, computed styles, visibility) or read text, evaluate a script in the page (`preview_evaluate`). A snapshot carries console, network and the accessibility tree, 10 to 20 KB each, so take one only for a capture you keep (`save: true`).
  - **States local data can't produce** (in progress, queued, failed): inject them in the page by intercepting `fetch` and rewriting the response. Keep the datastore to states the app produced itself: background jobs act on what it holds, so a stuck-job cron picks up a fake running job and a fake queue entry can start real work.
  - **Async or time-based UI** (polling, timers, text that may never appear): have the page record what happens (patch `fetch` or add a `MutationObserver` that pushes `{t, what}` into `window.__log`), then read it back with short `preview_evaluate` calls, each well under its 15 s timeout, returning what the page actually shows. `preview_wait_for` on exact text that never appears fails only after 60 s and tells you nothing, so read state this way instead of chaining it.
  - **Screenshots**: capture each touched screen in its relevant states for the PR, following [`SCREENSHOTS.md`](SCREENSHOTS.md).
- **Backend**: call the Skill tool with `debug-trace` and drive the changed paths through the running service, reading the trace to confirm the values the ticket expects.

Fix what you find, then re-verify. If the environment won't come up after one honest attempt, that's HITL; if it still can't run, record what went unverified for the PR description and the report.

Done when every flow from step 0 and every item of the failure-path checklist has been exercised and behaves as the ticket asks.

### 6. Comment cleanup

Call the Skill tool with `comment-cleanup` over the whole branch diff (`<base>...HEAD`). Done when its result is committed and the gates are green.

### 7. PR

Open one PR per layer, bottom first. For each, call the Skill tool with `merge-risk` over the layer's range (`<layer below or base>...<layer>`), then with `github-pr`, handing it the merge-risk report for its `## Merge risk` section, anything left unverified in step 5, and any screenshots from step 5, each file with its one-line source.

`github-pr` writes the title and description and opens the PR **ready for review**, so the full CI runs (some checks skip drafts); with `stop-at=draft`, open it as a draft. Its approval is already given, so print the title, description and files and go on without waiting for `approve`. Under GitButler, create the PR with `but pr new <branch> -F <file>` (first line title, rest description; add `--draft` with `stop-at=draft`) instead of `gh`, because it pushes the branch and its ancestors and sets the right base in a stack. A tidy PR's description says it changes structure only and names the ticket's PR it serves.

Done when every layer has its PR. Keep each one current through steps 6 and 8: a fix that changes a captured screen means capturing it again and re-attaching it, and a step 8 fix that changes exposed code means rerunning `merge-risk` and updating the section (`gh pr edit <number> --body-file <file>`).

### 8. CI loop

Loop until every check is green:

1. Wait for the checks to finish with `Monitor` or an until-loop on `gh pr checks <number>` rather than a tight poll. The wait ends when every check on the PR is green, required or not, and every required check from step 0 exists. Some required checks appear minutes after the others, so "all checks passed" with one missing is still pending. With `stop-at=draft`, that means the draft checks only, and the report lists the ready-only ones as pending for the caller. A layer stacked on another gets the checks that run only on PRs based on the default branch once the layer below merges: list those as "pending retarget" and leave them out of the wait. When T3 Code delegated the ticket, wait inside the turn (`t3_background_wait` on the Monitor or loop task) rather than ending it.
2. On any red check, required or not, diagnose with the tools at hand: a CI skill the project or the user has installed, `gh pr checks`, the job logs. Classify it:
   - **caused by this change**: fix it, run the gates, push;
   - **flaky or infrastructure**: re-run it once; red again is HITL;
   - **also red on `<base>`**: HITL, leave it alone;
   - **base staleness** (foreign): a scan that compares against a default branch newer than `<base>`, on a PR that touches no lockfile. Leave it and list it for the report; updating the base is the caller's.
3. Back to 1.

Stop with HITL after 3 fix pushes that haven't turned CI green: the loop isn't converging.

### 9. Report

When a caller passed a report path, write the report there before ending any turn, even with checks still pending (list them as open). End a turn only once every action you announced has run.

First call the Skill tool with `retro-with-docs` on this session; if it is not available, skip it and say so in the report. Then write the report:

- Each layer bottom to top: PR URL, branch, merge-risk color, final CI state.
- The Later tidyings, each with its files and why it waits.
- Each review pass (tidy after, security review, pair-review rounds): findings, what was fixed, what was discarded and why.
- What was verified in the real app and how; what wasn't, and why.
- CI failures met and how each was resolved.
- Open HITL questions.
- The retro file and its blockers.

### 10. Reviewers (optional, skipped with `stop-at=draft`)

Ask whether to add reviewers, proposing names from CODEOWNERS or the recent history of the touched files. Run `gh pr edit <number> --add-reviewer …` only after the user's explicit yes.
