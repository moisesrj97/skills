---
name: megamoind
description: "Delegate a ticket end to end, unattended: TDD implementation, tidying, security review, pair-review, real-app verification, a PR ready for review and a CI loop until green. Use when the user hands over one ticket (a GitHub issue or a tracker ID such as a ClickUp task) to take all the way to a PR, e.g. \"megamoind PD-123\", or when another skill delegates one ticket's implementation. Several tickets go to megamoind-batch."
argument-hint: "[ticket ID] [base=<branch>] [brief=<file>] [stop-at=draft|pushed]"
---

# Megamoind

The user delegates a whole ticket and walks away. They come back to a PR that is implemented, reviewed, verified in the real app and green in CI, plus a report that says what was done and what wasn't. Every stop costs the user a context switch, so ask everything up front, then run on your own and stop only for **HITL**: a decision that is the user's (scope, product behaviour, a design trade-off, reversing something they decided) or a loop that isn't converging.

Invoking this skill is the user's approval to commit, push to the ticket's own branch and open the PR ready for review, each once the gates are green. Adding reviewers still waits for their explicit yes.

You are the **orchestrator**: you hold the brief, the branch, the PR and the CI, and three agents do the turn-heavy work in their own contexts (see "Agents"). Every turn re-reads your whole context, so what runs here stays small: you read their reports, not their work, and every code change goes through the implementer.

**One ticket per run.** More than one (a list, a label or other tracker query, a spec) is a **batch**: call the Skill tool with `megamoind-batch`, passing the user's request, and follow it instead of this skill.

## Arguments

- `<ticket>`: a GitHub issue or an ID from the tracker the project's `## Ticket tracker` section names (e.g. ClickUp). Missing, step 0 gets one first.
- `base=<branch>`: the branch to build on, e.g. the ticket below in a stack. Default: the default branch (`git symbolic-ref --short refs/remotes/origin/HEAD`). Every `<base>` below means this.
- `brief=<file>`: step 0 already answered by whoever delegated the ticket. Read it instead of asking; only what it leaves open is HITL. A brief that says `mode: minimoi` runs the reduced flow (see step 0's "Minimoi").
- `stop-at=draft`: the caller owns ready-for-review and reviewers. Step 7 opens the PR as a draft, step 8 loops on the checks that run on drafts, and step 10 is skipped.
- `stop-at=pushed`: the project lands changes without a PR, and landing is the user's. Step 7 pushes each layer instead of opening a PR, step 8 waits on the branch's checks, and step 10 is skipped.

## When a skill is not available

This skill hands off to `megamoind-batch`, `craftsmanship`, `diagnosing-bugs`, `tdd`, `diff-review`, `debug-trace`, `merge-risk`, `github-pr`, `pair-review` and `comment-cleanup`, called by these exact names. If the Skill tool reports one as not available, stop and ask. An improvised copy silently skips whatever the real skill enforces.

## Agents

- **Briefer**: owns step 0's research and drafts the brief. Start it once the ticket ID is known, and close it once the brief is confirmed.
- **Implementer**: owns steps 2, 3, 4 and 6, and every later code change (a verification failure, a red CI check). Start it after step 1 and keep it alive until step 9, so each fix lands with the context that wrote the code.
- **Verifier**: owns step 5. Start it fresh once step 4 is done; it changes no code and reports per flow.

Start each with the Agent tool (`run_in_background: false`, model `opus`; the verifier `sonnet`, since driving the browser and capturing evidence is mechanical), and send it later work with SendMessage to the id it returns. Its prompt holds, in this order:

1. The tag line `megamoind-run: <run> role=<briefer|implementer|verifier>`, from step 0's `metrics.py start`.
2. The brief's path, the ticket, the branch, `<base>`, this skill's folder and the metrics state file.
3. What to follow: this file's "Gates", "Docs or skill changes" and "Sharing the workspace" sections and its own steps, read from `<skill-dir>/SKILL.md`, marking the start of each step it owns (see step 0). The implementer passes `tag=megamoind-run: <run> role=review-<lens>` to every `diff-review` it runs, directly or through `pair-review` or `craftsmanship`.
4. Where its report goes: `<scratchpad>/<ticket>-brief.md`, `<scratchpad>/<ticket>-implement.md` or `<scratchpad>/<ticket>-verify.md`, rewritten after each piece of work, ending in `END OF REPORT`.
5. That a HITL question goes into the report and ends its turn instead of being asked. Relay it to the user, then send the answer back.

Each report carries what step 9 needs: the implementer's commits, review passes (findings fixed, discarded and why), Later tidyings and failure-path checklist; the verifier's flow counts (verified, failed at least once, unverified) and its flows with pass or fail, each with its evidence files (paths and one-line sources, see [`EVIDENCE.md`](EVIDENCE.md)), and what went unverified and why.

## Gates

The checks that must be green before any push: type-check, lint and tests for **every project the change touches**. In a monorepo that means each touched package's own `ci` (or equivalent) script as well as the root's.

- Read the commands from the project's `CLAUDE.md` / `CLAUDE.local.md`, else from `python3 <skill-dir>/scripts/preflight.py --base <base> --head <branch>`: its `touched_packages` lists every package the branch's diff touches, the root included, with the gate scripts each defines, and `package_manager` names the runner.
- Launch a long suite (several minutes) in the background from the start, so the foreground timeout can't kill it.
- If preflight reports `dev_doctor`, run `yarn dev:doctor --flow <flow> --no-services` before the first type-check and after any pull that touches `packages/`. It rebuilds stale workspace builds, which otherwise read as a red gate.
- A heavy spec that times out under full-suite load counts as red only after it fails again in isolation.
- Run checks as wide as the project's scripts do, but point every auto-fix (`--write`, `--fix`, a formatter) at the files of your branch's diff only. One aimed at a whole folder rewrites files outside the ticket and can break them, e.g. by dropping a `@ts-expect-error`.
- Before each commit, check it holds only your ticket's files (`but diff` under GitButler, `git diff --stat` otherwise). Under GitButler, other agents keep editing the same files after that check, so right after each commit read `git diff <base>...<branch>` for hunks that aren't your ticket's and take them out (`but uncommit <hunk ids>`).
- A commit hook that runs lint-staged reads the config in the working tree. When one change both adds a lint or format rule and fixes the files it flags, commit in the order fixes, then pure formatting, then the config, adding the new rule to the working tree only for that last commit.

Push only with every gate green or **foreign** (see "Sharing the workspace").

## Docs or skill changes

When the diff holds no code (a README, a skill, a recipe), the steps keep their shape and change what they test:

- **Gates**: links and anchors resolve.
- **Step 2**: the test is each claim the doc makes, checked against the code it documents and cited with `file:line`, plus its code snippets type-checked against the real types. A skill with a `benchmark/evals.json` gets one new eval per behaviour change, with the opposite case as a control. When the project defines a check its evals must pass, run it in a fresh agent on the first draft, before committing, and again after each fix until it passes.
- **Step 3**: tidy after runs over prose a reader maintains (a SKILL.md, a README) and skips data files such as `evals.json`.
- **Step 4** runs only when the diff adds a command, script or snippet that runs code or touches credentials. Otherwise skip it and say so in the report.
- **Step 5**: run every command or snippet the doc adds exactly as written, in the real app. For a skill, run each new eval prompt in a fresh agent that reads only the skill. The evidence is each one's trace: the command or prompt and the output that proves it.
- **Step 6** is skipped.
- **Step 7**: with no such command, script or snippet, the `## Merge risk` section is one green line ("Docs only, no code runs") instead of a `merge-risk` run.

## Steps

### 0. Brief and HITL check

Each step starts with `python3 <skill-dir>/scripts/metrics.py mark <state> "<n> <name>"`, so the run's time and tokens split by step. The names are fixed, and `mark` rejects any other: `0 brief`, `1 branch`, `2 implement`, `3 review`, `4 security`, `5 verify`, `6 comments`, `7 pr`, `8 ci`, `9 report`, `10 reviewers`. The agent that owns a step marks it. Step 0 starts it instead, as soon as the ticket ID is known: `python3 <skill-dir>/scripts/metrics.py start <ticket> --dir <scratchpad>` prints the run's tag line and its state file.

With no ticket in the request, get one before anything else, in one question with two options:

- **Give the ID**: the user writes it.
- **Create it**: a ticket in the tracker, titled and described from the user's request, in the in-progress status, assigned to the user running this skill (GitHub: `gh issue create --assignee @me`). It goes where the `## Ticket tracker` section says new tickets go; when it names no place, ask for one. Its new ID is the ticket from here on.

Then start the briefer (see "Agents"), adding to its prompt the user's request and any plan already agreed in this conversation, and wait for its draft. The briefer runs the research below and writes the draft to `<scratchpad>/<ticket>-brief.md`: each item of the round with its proposal, and which of MINIMOI.md's "Eligibility" conditions the ticket meets. You read only that file, so your context holds the brief and not the code behind it. Ask the round, send the briefer any answer that needs more research, write the answers into the brief, then close the briefer.

**Briefer's research.** Fetch the ticket (`gh issue view` for a GitHub issue, the tracker's tools otherwise); a tracker you can't reach is HITL. Read the ticket and quote each decision in it that the request, or a plan already agreed in this conversation, contradicts: that conflict is HITL. Then read the code it touches as it is on `<base>` (`git show <base>:<file>`, `git grep <pattern> <base>`), since under GitButler the working tree merges every applied branch and its symbols and line numbers may not exist on `<base>`; every `file:line` the brief cites comes from there. Look for what the change can **reuse**: helpers, a similar feature, how the neighbouring tests are written. When the ticket relies on how a third-party service behaves (an embed, a player, an API), read that service's terms or policy for the behaviour and cite it in the plan: a design its terms forbid is HITL before any code. Call the Skill tool with `craftsmanship`. For a bug, call the Skill tool with `diagnosing-bugs` and take it through phase 4, so the plan names the confirmed cause; its fix waits for step 2.

Run `python3 <skill-dir>/scripts/preflight.py --files <paths the plan changes>` once for the repo facts below (default branch, GitButler, CODEOWNERS, required checks, gh version, the sections of each steering file). A path in its `files_in_other_branches` with a branch listed collides with that in-flight branch: the plan names it and proposes basing on that branch or waiting for it.

With `brief=`, the briefer reads it and settles on its own whatever of the plan below it leaves open (only the user's decisions are HITL); then go to step 1, or hand off when it says `mode: minimoi`. Otherwise the round asks everything in **one** round, with your proposal for each. When the ticket already states the approach, files and validation, the plan is one short question that restates it and names only where you deviate, with no fallbacks or conditional plans. Each option states only consequences you checked in code or data this session: grep the consumer before claiming "with X, Y happens", and mark anything unchecked "unverified: …". An option that extends scope to a sibling case ("X has the same bug") quotes the routing line that sends the user's action into that code, found by tracing every call site.

- **Plan**: the approach in a few lines, what it reuses, the seams where tests go with what each buys and sells (Test Desiderata), the tidyings worth doing first or after and where each goes by area of impact (Tidy First), and anything ambiguous in the ticket. When the ticket replaces or reproduces something already visible in the product, the plan keeps its current look, cites the **visual reference** (the screenshot, the live screen), and checks that the shape of the data (copy keys, props) can carry that look, e.g. one copy key can't style half its text.
- **Branch name**: the format in the project's `## Ticket tracker` section, else `<ticket-id>-<short-kebab-description>`, with no `/`. A pre-PR or post-PR from the plan adds `<name>-tidy-first` or `<name>-tidy-after`.
- **Landing**: when the project's `CLAUDE.md` / `CLAUDE.local.md` says changes land without a PR, the run is `stop-at=pushed`; state it in the plan rather than asking.
- **Base** (GitButler): run `but pull --check`. When the workspace is behind and updating would move other branches, ask: "the workspace is N commits behind; updating would move X and Y. Update?". A no leaves the base stale, so guard against a **borrowed green** (see "Sharing the workspace").
- **Verification**: how to run the app or service (the dev commands, required env, data or login, ports), and which flows prove the change works, each with its route or entry point and the data it needs. Each observable named as proof (a status, a field, an endpoint's answer, an eval's expected output) cites the handler that produces it (`file:line`) and, when the app runs, has been seen once.
- **CODEOWNERS**: if preflight names one, opening the PR ready for review requests those reviewers automatically. Say so, since it defeats waiting to add reviewers.
- **Required checks**: the names CI must turn green, from the project's `CLAUDE.md` / `CLAUDE.local.md`, else preflight's `required_checks` (the base's rulesets and branch protection; pass `--base <base>` when it isn't the default branch). If neither gives them, or preflight reports `required_checks_error`, ask. Split them into checks that run on drafts and ready-only ones (e.g. a Jenkins job that builds only non-draft PRs whose base is the default branch).
- **Evidence media** (screenshots, recordings): the PR gets them through `gh-attach`, which needs gh ≥ 2.99. When preflight reports `gh_attach_ok: false`, ask the user to upgrade.
- **Ticket description**: ask whether to copy the brief's product decisions (what changes, UI choices, acceptance criteria) into the ticket's description. On a yes, write them into the description, keeping its existing content, never as a comment.

Done when the user has confirmed the plan and you have everything needed to reach step 8 without asking again. Write the confirmed brief to `<scratchpad>/<ticket>-brief.md`, and re-read it whenever a later step needs a decision from step 0.

**Minimoi**: a trivial change runs the reduced flow in [`MINIMOI.md`](MINIMOI.md), inline, with no agents. Without `brief=`, once the brief is written and the ticket meets every condition in MINIMOI.md's "Eligibility", ask in a round of its own whether to hand off to minimoi, naming the conditions it meets; on a yes, add `mode: minimoi` to the brief. To hand off, run `metrics.py mark <state> "0 handoff" --skill minimoi` and follow MINIMOI.md from its step 1 instead of this file's.

### 1. Branch

If the repo uses GitButler (`but status` works), create the branch with `but branch new <name>`, or `but branch new <name> --above <base>` when `base=` is a branch in the workspace, and do every commit and push with `but`. Otherwise update `<base>` and `git switch -c <name> <base>`. Under GitButler, update from the target (`but pull`) when only your branches are applied or the user said yes in step 0, since moving other branches is their call. When updating the base changed a lockfile, reinstall dependencies with the project's package manager and restart any dev server already running, before anything else runs.

With a pre-PR, create `<name>-tidy-first` on `<base>` as above. Under GitButler, create the ticket's branch on top of it now (`--above <name>-tidy-first`), so commits to the lower branch restack it. With plain git, create it once the pre-PR's commits are in (`git switch -c <name> <name>-tidy-first`, end of step 2's first pass), since a branch created earlier stays on the old commit. These branches, plus a post-PR's, are the ticket's **layers**, bottom to top; `HEAD` in the ranges below is the top layer. With plain git, after any later commit on a lower layer (a review fix, a CI fix), rebase each layer above onto it, bottom up (`git rebase <lower> <upper>`), then switch back to the top layer; once they are pushed, push them with `--force-with-lease`.

Done when the branch exists. Then start the implementer (see "Agents") and wait for its report of steps 2 to 4.

### Sharing the workspace

Under GitButler, other agents' branches may be applied in the same working directory, so their unfinished changes show up in your type-check, tests and dev server. Commit only your own hunks (`but commit -b <branch> <ids>`, ids from `but diff`) and edit only files your ticket needs. A red gate is **foreign** when every failure sits in a file outside your branch's diff that `but status` shows changed by another branch or uncommitted outside yours. A change you produced yourself, e.g. a formatter or codegen run, is never foreign, even uncommitted. Leave a foreign red alone (fixing it would mix two tickets in one branch), list it for the report and count the gate as green. Their edits also hot-reload into your dev server: a checker overlay naming files outside your diff is foreign, so remove it from the DOM and go on, and when the UI stops reacting after a burst of hot updates you didn't cause, reload the page before debugging.

The inverse is a **borrowed green**: another applied branch supplies hunks yours lacks (an import, a type, a helper), so your gates pass locally and CI, which builds your branch alone, fails. Your code may depend only on `<base>` and your own commits. A branch still applied but marked `(merged upstream)` in `but status` means your base is stale, so update before implementing. When you can't update, check that each symbol you use from a file other branches touch exists in `<base>` (`git show <base>:<file>`).

Before pushing, whenever other branches are applied, run the gates on your branch alone: `git archive <branch> | tar -x -C <scratchpad>/<new-dir>`, symlink the root's and each touched package's `node_modules` into it, copy the untracked env files the tests read (e.g. `.env.test`), `git init -q` there when a tool reads the VCS (biome's `vcs.useIgnoreFile`), and run the type-check and tests in that copy.

A change that belongs to the `<base>` branch's ticket goes on that branch. Stop and ask for it, naming the change. When told the base moved, re-run the gates and go on.

### 2. Implement (implementer)

Two passes, with structure and behaviour always in separate commits:

1. **Tidy first**: the plan's first tidyings, as the PR's first `refactor:` commit or on the pre-PR branch, following `craftsmanship`.
2. **Behaviour**: call the Skill tool with `tdd` and build the ticket at the seams agreed in step 0, reusing what step 0 found. For a bug, the diagnosis loop from step 0 is the first red test; once it is green, run `diagnosing-bugs` phase 6 (its instrumentation and throwaway harnesses removed, the original reproduction rerun) before committing.

Run type-check and the single test files you are touching as you go, and the gates once at the end. Commit locally at each working checkpoint.

When the brief rules out tests, write a **failure-path checklist** to the scratchpad before step 3: for every async call or batch, its partial failure, total failure and empty result, plus the id types that cross a `String()`/`Number()` conversion. Each item is handled in code or marked accepted.

When the ticket adds or ports an LLM prompt, run it 5 times on a real input before step 5, even when the brief rules out a bench, plus once on an opposite case as a control. Score each sample against a per-case checklist written before the run.

Done when every point of the ticket is implemented, every planned tidying first has landed, every checklist item is handled or accepted, and the gates are green.

### 3. Tidy after and pair review (implementer)

Two reviews of the same commit, launched together so neither waits for the other:

- **Tidy after**: `craftsmanship`'s *Tidy a diff* over `<base>...HEAD`. It places each tidying by area of impact: a `refactor:` commit on the ticket's branch, or the post-PR branch `<name>-tidy-after` on top of it. One that is Later goes on a list for the report.
- **Pair review**: call the Skill tool with `pair-review` with args `<base>...HEAD spec=<scratchpad>/<ticket>-brief.md standards=<absolute path of the test-desiderata.md beside craftsmanship's SKILL.md>`, passing the user's decisions from step 0 and any HITL answers as its already-decided list. It fixes and re-reviews until done; its HITL stops are this skill's HITL stops.

Land the tidyings before pair-review's round 2, so that round reviews them too. A tidying that lands after pair-review's last round, a clean round 1 included, gets one more round over the new tip. A finding fixed by a tidying goes on the layer its area of impact picks.

Done when pair-review ends Done, every tidying has landed or moved to Later, and the gates are green.

### 4. Security review (implementer)

Call the Skill tool with `diff-review` with `lens=security` over `<base>...HEAD`, now that the code has settled. One round, with no loop: no review follows it, so each fix stays within its finding.

Done when every finding it returns is fixed with a test that fails without the fix, or discarded with a one-line reason for the report, and the gates are green. Then the implementer reports and waits. Its report resolves each verification flow from the brief, so the verifier starts driving instead of reading code: the URL or command that starts it, the data, account or fixture it needs and how to get it, the steps, the observable to check, and the files it exercises.

### 5. Verify in the real app (verifier)

Start the verifier (see "Agents"), adding the implementer's report path to its prompt for the resolved flows and the failure-path checklist. The verifier works from those flows and reads code only to fill a gap they leave, naming the gap in its report. A flow that fails goes to the implementer as a fix; once its report says the fix is in and the gates are green, send the verifier back to that flow and to the flows the fix's files reach.

The rest of this step is the verifier's. Start what the app needs as background subshells (`run_in_background`) with the commands from step 0, and stop every one you started when done. When the brief says the servers are already running, use them, since a second copy fights for the same ports.

- **Frontend or fullstack**: drive the dev server in a real browser with whatever browser tooling this harness gives you (a browser-control skill, extension or MCP server; Playwright when there is nothing else). No way to drive a browser counts as an environment that won't come up. This step is an explicit request for browser verification, so tools a harness keeps for user-requested browser work (T3 Code's `preview_*`) apply here. Other agents may share the browser, so open a tab of your own, act only in it and close it when done.
  - Walk every flow the ticket touches and check each touched screen at 375, 900 and 1440 px for overlaps, clipped or mixed-language copy, and anything the ticket didn't ask for. Compare each screen against the visual reference from step 0 as well as the ticket's text.
  - To measure (bounding boxes, computed styles, visibility) or read text, evaluate a script in the page (`preview_evaluate`). A snapshot carries console, network and the accessibility tree, 10 to 20 KB each, so take one only for a capture you keep (`save: true`).
  - **States local data can't produce** (in progress, queued, failed): inject them in the page by intercepting `fetch` and rewriting the response. Keep the datastore to states the app produced itself: background jobs act on what it holds, so a stuck-job cron picks up a fake running job and a fake queue entry can start real work.
  - **Async or time-based UI** (polling, timers, text that may never appear): have the page record what happens (patch `fetch` or add a `MutationObserver` that pushes `{t, what}` into `window.__log`), then read it back with short `preview_evaluate` calls, each well under its 15 s timeout, returning what the page actually shows. `preview_wait_for` on exact text that never appears fails only after 60 s and tells you nothing, so read state this way instead of chaining it.
- **Backend**: call the Skill tool with `debug-trace` and drive the changed paths through the running service, reading the trace to confirm the values the ticket expects.

Each flow leaves evidence (a screenshot, a recording or a trace excerpt) following [`EVIDENCE.md`](EVIDENCE.md), failing flows too, so the implementer sees what broke.

If the environment won't come up after one attempt, that's HITL; if it still can't run, record what went unverified for the PR description and the report.

Done when every flow from step 0 and every item of the failure-path checklist has been exercised, behaves as the ticket asks and has its evidence file, re-captured after any fix it went through. Then send the implementer step 6.

### 6. Comment cleanup (implementer)

Call the Skill tool with `comment-cleanup` over the whole branch diff (`<base>...HEAD`). Done when its result is committed and the gates are green.

### 7. PR

With `stop-at=pushed`, push each layer bottom first (`but push <branch>`, else `git push -u origin <branch>`), run `merge-risk` over its range for the report, and skip the rest of this step but its interim report.

Otherwise open one PR per layer, bottom first. For each, call the Skill tool with `merge-risk` over the layer's range (`<layer below or base>...<layer>`), then with `github-pr`, handing it the merge-risk report for its `## Merge risk` section, anything left unverified in step 5, and step 5's evidence for the passing flows, each file with its one-line source.

`github-pr` writes the title and description and opens the PR **ready for review**, so the full CI runs (some checks skip drafts); with `stop-at=draft`, open it as a draft. Its approval is already given, so print the title, description and files and go on without waiting for `approve`. Under GitButler, create the PR with `but pr new <branch> -F <file>` (first line title, rest description; add `--draft` with `stop-at=draft`) instead of `gh`, because it pushes the branch and its ancestors and sets the right base in a stack. Run `but status` right before it: a `<base>` marked `(merged upstream)` merged during the run, and `but pr new` fails on its deleted head. Update (`but pull`, under step 1's conditions) and open the PR against the default branch, saying so in the description and the report. `but pr new` also force-pushes every ancestor whose local tip GitButler rebased, so compare each branch below yours that isn't one of your layers (`git rev-parse <b> origin/<b>`). When one differs and has an open PR, push your branch alone: `git replay --onto origin/<base> <base>..<branch>` prints the rebased tip's SHA, then `git push origin <sha>:refs/heads/<branch>` and `gh pr create --base <base>`. A tidy PR's description says it changes structure only and names the ticket's PR it serves.

Then write the step 9 report as `STATUS: interim — CI pending`, to the caller's report path or else `<scratchpad>/<ticket>-report.md`, and, unless a caller passed a path, tell the user with `PushNotification` that the PR (or the pushed branch) is ready to look at. Most runs need no CI fix, so the user can start reviewing while CI runs. Notify again only when the run stops on a HITL; a green CI ends quietly in the final report.

Done when every layer has its PR. Keep each one current through steps 6 and 8: a fix that changes what an evidence file shows means capturing it again and re-attaching it, and a step 8 fix that changes exposed code means rerunning `merge-risk` and updating the section (`gh pr edit <number> --body-file <file>`).

### 8. CI loop

Loop until every check is green:

1. Wait for the checks to settle, in the background (`run_in_background`, with a time limit above the script's hour, e.g. `timeout: 3900000`), so its exit wakes you:

   ```bash
   python3 <skill-dir>/scripts/ci.py wait <number> --required "<name>" … [--skip "<name>" …]   # one flag per check
   ```

   With `stop-at=pushed`, pass `--branch <branch> --sha <pushed head>` instead of the PR number.

   It exits 0 once every check on the PR is green, required or not, and every required check has reported (some appear minutes after the others, and `gh pr checks --required` can't show one missing), or once a PR with no checks at all has had 5 minutes to get some and requires none; 1 with the red checks named; 3 when a required check still hasn't appeared 15 minutes after the rest settled, with the names it saw (fix the name and wait again); 4 after an hour with what is still pending or missing; 2 when `gh` failed three polls in a row. With `stop-at=draft`, pass the ready-only checks in `--skip` and list them in the report as pending for the caller. A layer stacked on another gets the checks that run only on PRs based on the default branch once the layer below merges: pass those in `--skip` too and list them as "pending retarget". When T3 Code delegated the ticket, wait inside the turn (`t3_background_wait({"taskIds": ["<task id>"]})`) rather than ending it.
2. On any red check, required or not, diagnose with the tools at hand: a CI skill the project or the user has installed, `gh pr checks`, the job logs. Classify it:
   - **caused by this change**: send it to the implementer; once its report says the fix is committed and the gates are green, push;
   - **flaky or infrastructure**: re-run it once; red again is HITL;
   - **also red on `<base>`**: HITL, leave it alone;
   - **base staleness** (foreign): a scan that compares against a default branch newer than `<base>`, on a PR that touches no lockfile. Leave it and list it for the report; updating the base is the caller's.
3. Back to 1.

Stop with HITL after 3 fix pushes that haven't turned CI green: the loop isn't converging.

### 9. Report

When a caller passed a report path, write the report there before ending any turn, even with checks still pending (list them as open). Its first line is `STATUS: final` once every earlier step and the retro are done, else `STATUS: interim — <what is pending>`, and its last line is `END OF REPORT` either way. End a turn only once every action you announced has run.

Close the implementer and the verifier. Run `python3 <skill-dir>/scripts/metrics.py collect <state> --flows <n> --failures <n> --unverified <n>`, with the verifier's flow counts (leave the three flags out when step 5 never ran), which appends the run to the metrics log and prints its time, tokens and peak context per agent and per step. Then call the Skill tool with `retro-with-docs` on this session; if it is not available, skip it and say so in the report. Then write the report from the agents' reports and your own steps:

- Each layer bottom to top: PR URL (or the pushed head with `stop-at=pushed`), branch, merge-risk color, final CI state.
- The Later tidyings, each with its files and why it waits.
- Each review pass (tidy after, pair-review rounds, security review): findings, what was fixed, what was discarded and why.
- What was verified in the real app and how, with each flow's evidence files; what wasn't, and why.
- CI failures met and how each was resolved.
- Open HITL questions.
- The retro file and its blockers.
- The metrics `collect` printed.

### 10. Reviewers (optional, skipped with `stop-at=draft` or `stop-at=pushed`)

Ask whether to add reviewers, proposing names from CODEOWNERS or the recent history of the touched files. Run `gh pr edit <number> --add-reviewer …` only after the user's explicit yes.
