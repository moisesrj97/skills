---
name: megamoind
description: "Delegate a ticket end to end, unattended: TDD implementation, tidying, security review, pair-review, real-app verification, a PR ready for review and a CI loop until green. Use when the user hands over one ticket (a GitHub issue or a tracker ID such as a ClickUp task) to take all the way to a PR, e.g. \"megamoind PD-123\", or when another skill delegates one ticket's implementation. Several tickets go to megamoind-batch."
argument-hint: "[ticket ID] [base=<branch>] [brief=<file>] [stop-at=draft|pushed]"
---

# Megamoind

The user delegates a whole ticket and walks away. They come back to a PR that is implemented, reviewed, verified in the real app and green in CI, plus a report that says what was done and what wasn't. Every stop costs the user a context switch, so ask everything up front, then run on your own and stop only for **HITL**: a decision that is the user's (scope, product behaviour, a design trade-off, reversing something they decided) or a loop that isn't converging.

Invoking this skill is the user's approval to commit, push to the ticket's own branch and open the PR ready for review, each once the gates are green. Adding reviewers still waits for their explicit yes.

You are the **orchestrator**: you hold the brief, the branch, the PR and the CI, and five agents do the turn-heavy work in their own contexts (see "Agents"). Every turn re-reads your whole context, so what runs here stays small: you read their reports, not their work, and every code change goes through the implementer, then the finisher after step 2, then the polisher after step 4.

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
- **Implementer**: owns step 2. Start it after step 1 and close it once its report is accepted.
- **Finisher**: owns steps 3 and 4. Start it fresh after step 2 and close it once its report of step 4 is accepted. It starts with the brief, the implementer's report and the branch diff instead of the implementer's history, so every turn after step 2 re-reads a smaller context; the report's `## Decisions beyond the brief` carries what that history knew.
- **Polisher**: owns step 6 and every later code change (a verification failure, a red CI check). Start it fresh at its first piece of work (a failing flow in step 5, else step 6) and keep it alive until step 9. It starts with the brief, the implementer's and the finisher's reports and the branch diff, so the review history stays out of these mechanical turns.
- **Verifier**: owns step 5. Start it fresh once step 4 is done; it changes no code and reports per flow.

Start each with the Agent tool (`run_in_background: false`, model `opus`; the polisher and the verifier `sonnet`, since fixing a named failure and driving the browser are mechanical), and send it later work with SendMessage to the id it returns. Its prompt holds, in this order:

1. The tag line `megamoind-run: <run> role=<briefer|implementer|finisher|polisher|verifier>`, from step 0's `metrics.py start`.
2. The brief's path, the ticket, the branch, `<base>`, this skill's folder and the metrics state file.
3. This line, verbatim but for the role and the absolute path of the folder this skill loaded from: `You are the <role>. Read <skill-dir>/<ROLE>.md before anything else and follow it.`, where `<ROLE>.md` is [`BRIEF.md`](BRIEF.md), [`IMPLEMENT.md`](IMPLEMENT.md), [`FINISH.md`](FINISH.md), [`POLISH.md`](POLISH.md) or [`VERIFY.md`](VERIFY.md). The role file names what else the agent reads.
4. Where its report goes: `<scratchpad>/<ticket>-brief.md`, `<scratchpad>/<ticket>-implement.md`, `<scratchpad>/<ticket>-finish.md`, `<scratchpad>/<ticket>-polish.md` or `<scratchpad>/<ticket>-verify.md`, rewritten after each piece of work, starting with `Head: <sha of its branch tip>` and ending in `END OF REPORT`. Ending its turn kills its background jobs (review rounds, test suites), so it waits for them inside the turn and writes `END OF REPORT` only after they finish. Accept a report only when its `Head:` matches `git rev-parse <branch>`.
5. That a HITL question goes into the report and ends its turn instead of being asked. Relay it to the user, then send the answer back.

## Workspace rules

[`WORKSPACE.md`](WORKSPACE.md) holds the gates, the layers, the rules for docs or skill changes and for sharing the workspace. Read it now: it applies to you and to every agent but the briefer.

## Steps

### 0. Brief and HITL check

Each step starts with `python3 <skill-dir>/scripts/metrics.py mark <state> "<n> <name>"`, so the run's time and tokens split by step. The names are fixed, and `mark` rejects any other: `0 brief`, `1 branch`, `2 implement`, `3 review`, `4 security`, `5 verify`, `6 comments`, `7 pr`, `8 ci`, `9 report`, `10 reviewers`. The agent that owns a step marks it. Step 0 starts it instead, as soon as the ticket ID is known: `python3 <skill-dir>/scripts/metrics.py start <ticket> --dir <scratchpad>` prints the run's tag line and its state file.

With no ticket in the request, get one before anything else, in one question with two options:

- **Give the ID**: the user writes it.
- **Create it**: a ticket in the tracker, titled and described from the user's request, in the in-progress status, assigned to the user running this skill (GitHub: `gh issue create --assignee @me`). It goes where the `## Ticket tracker` section says new tickets go; when it names no place, ask for one. Its new ID is the ticket from here on.

Then start the briefer (see "Agents"), adding to its prompt the user's request and any plan already agreed in this conversation, and wait for its draft at `<scratchpad>/<ticket>-brief.md`: the round's items, each with its proposal, and which of MINIMOI.md's "Eligibility" conditions the ticket meets. You read only that file, so your context holds the brief and not the code behind it. With `brief=`, the briefer settles what it leaves open; go to step 1, or hand off when it says `mode: minimoi`. Otherwise ask the round as drafted, in **one** round, send the briefer any answer that needs more research, write the answers into the brief, then close the briefer. On a yes to the ticket description, write the brief's product decisions into the ticket's description, keeping its existing content, never as a comment.

Done when the user has confirmed the plan and you have everything needed to reach step 8 without asking again. Write the confirmed brief to `<scratchpad>/<ticket>-brief.md`, and re-read it whenever a later step needs a decision from step 0.

**Minimoi**: a trivial change runs the reduced flow in [`MINIMOI.md`](MINIMOI.md), inline, with no agents. Without `brief=`, once the brief is written and the ticket meets every condition in MINIMOI.md's "Eligibility", ask in a round of its own whether to hand off to minimoi, naming the conditions it meets; on a yes, add `mode: minimoi` to the brief. To hand off, run `metrics.py mark <state> "0 handoff" --skill minimoi` and follow MINIMOI.md from its step 1 instead of this file's.

### 1. Branch

If the repo uses GitButler (`but status` works), create the branch with `but branch new <name>`, or `but branch new <name> --above <base>` when `base=` is a branch in the workspace, and do every commit and push with `but`. Otherwise update `<base>` and `git switch -c <name> <base>`. Under GitButler, update from the target (`but pull`) when only your branches are applied or the user said yes in step 0, since moving other branches is their call. When updating the base changed a lockfile, reinstall dependencies with the project's package manager and restart any dev server already running, before anything else runs.

With a pre-PR, create `<name>-tidy-first` on `<base>` as above. Under GitButler, create the ticket's branch on top of it now (`--above <name>-tidy-first`), so commits to the lower branch restack it. With plain git, the implementer creates it once the pre-PR's commits are in. These branches, plus a post-PR's, are the ticket's **layers** (see WORKSPACE.md's "Layers").

Done when the branch exists. Then start the implementer (see "Agents") and wait for its report of step 2.

### 2. Implement (implementer)

The implementer follows IMPLEMENT.md. When it reports a user-approved bench, or a prompt run that needs the user's approval or credentials, run it yourself with the approval from step 0, since the permission layer refuses approval relayed to a subagent.

Once the report is accepted, close the implementer and start the finisher (see "Agents"), adding the implementer's report path to its prompt, and wait for its report of steps 3 and 4.

### 3. Tidy after and pair review, 4. Security review (finisher)

The finisher follows FINISH.md and reports once both are done. Once its report is accepted, close it.

### 5. Verify in the real app (verifier)

Start the verifier (see "Agents"), adding the finisher's report path to its prompt for the resolved flows and the implementer's for the failure-path checklist; it follows VERIFY.md. A flow that fails goes to the polisher as a fix, starting it (see "Agents") if it isn't running yet; once its report says the fix is in and the gates are green, send the verifier back to that flow and to the flows the fix's files reach.

Done when the verifier's report is final. Then send the polisher step 6, starting it if no flow failed.

### 6. Comment cleanup (polisher)

The polisher follows POLISH.md's step 6.

### 7. PR

With `stop-at=pushed`, push each layer bottom first (`but push <branch>`, else `git push -u origin <branch>`), run `merge-risk` over its range for the report, and skip the rest of this step but its interim report.

Otherwise open one PR per layer, bottom first. For each, call the Skill tool with `merge-risk` over the layer's range (`<layer below or base>...<layer>`), then with `github-pr`, handing it the merge-risk report for its `## Merge risk` section, anything left unverified in step 5, and step 5's evidence for the passing flows, each file with its one-line source.

`github-pr` writes the title and description and opens the PR **ready for review**, so the full CI runs (some checks skip drafts); with `stop-at=draft`, open it as a draft. Under GitButler, create the PR with `but pr new <branch> -F <file>` (first line title, rest description; add `--draft` with `stop-at=draft`) instead of `gh`, because it pushes the branch and its ancestors and sets the right base in a stack. Run `but status` right before it: a `<base>` marked `(merged upstream)` merged during the run, and `but pr new` fails on its deleted head. Update (`but pull`, under step 1's conditions) and open the PR against the default branch, saying so in the description and the report. `but pr new` also force-pushes every ancestor whose local tip GitButler rebased, so compare each branch below yours that isn't one of your layers (`git rev-parse <b> origin/<b>`). When one differs and has an open PR, push your branch alone: `git replay --onto origin/<base> <base>..<branch>` prints the rebased tip's SHA, then `git push origin <sha>:refs/heads/<branch>` and `gh pr create --base <base>`. While a branch below still differs from its origin, every later push of yours (a review or CI fix) repeats that replay and pushes the printed SHA the same way, since `but push` would publish the rebased ancestors. A tidy PR's description says it changes structure only and names the ticket's PR it serves.

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
   - **caused by this change**: send it to the polisher; once its report says the fix is committed and the gates are green, push (with step 7's replay when it applies);
   - **flaky or infrastructure**: re-run it once; red again is HITL;
   - **also red on `<base>`**: HITL, leave it alone;
   - **base staleness** (foreign): a scan that compares against a default branch newer than `<base>`, on a PR that touches no lockfile. Leave it and list it for the report; updating the base is the caller's.
3. Back to 1.

Stop with HITL after 3 fix pushes that haven't turned CI green: the loop isn't converging.

### 9. Report

When a caller passed a report path, write the report there before ending any turn, even with checks still pending (list them as open). Its first line is `STATUS: final` once every earlier step and the retro are done, else `STATUS: interim — <what is pending>`, followed by `Head: <top layer sha>` and `CI: <ci.py wait's last state, or pending>`, and its last line is `END OF REPORT` either way. End a turn only once every action you announced has run.

Close the polisher and the verifier. Run the retro in a fresh agent, so it doesn't re-read your whole context on every turn: `python3 <skill-dir>/scripts/metrics.py session <state>` prints this session's transcript, then start the agent with the Agent tool (`run_in_background: false`, model `sonnet`), its prompt the tag line `megamoind-run: <run> role=retro` and: "Call the Skill tool with `retro-with-docs` on the session `<transcript>`. It ran in `<repo>`, so pass both to `locate.py` (`--session <transcript> --cwd <repo>`). Reply with the retro file's path and its blockers, or that `retro-with-docs` is not available." When it isn't, say so in the report.

Then run `python3 <skill-dir>/scripts/metrics.py collect <state> --flows <n> --failures <n> --unverified <n>`, with the verifier's flow counts (leave the three flags out when step 5 never ran), which appends the run, retro included, to the metrics log and prints its time, cost, tokens and peak context per agent and per step. Then write the report from the agents' reports and your own steps:

- Each layer bottom to top: PR URL (or the pushed head with `stop-at=pushed`), branch, merge-risk color, final CI state.
- The Later tidyings, each with its files and why it waits.
- Each review pass (tidy after, pair-review rounds, security review): findings, what was fixed, what was discarded and why.
- What was verified in the real app and how, with each flow's evidence files; what wasn't, and why.
- CI failures met and how each was resolved.
- Open HITL questions.
- The retro file and its blockers.
- The metrics `collect` printed.

### 10. Reviewers (optional, skipped with `stop-at=draft` or `stop-at=pushed`)

First remind the user to fill the PR's `## TLDR Humano` block before reviewers see it. Then ask whether to add reviewers, proposing names from CODEOWNERS or the recent history of the touched files. Run `gh pr edit <number> --add-reviewer …` only after the user's explicit yes.
