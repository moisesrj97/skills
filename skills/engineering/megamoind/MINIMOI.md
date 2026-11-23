# Minimoi

Megamoind cut down for a trivial change: the same brief, branch, PR and CI loop, run inline in this session with one review instead of a loop. `<skill-dir>` is megamoind's folder, the one holding this file; every section and step named below is in its `SKILL.md`.

## Eligibility

A change qualifies when **every** condition holds. Name which ones it meets whenever you propose or accept minimoi.

- **Small or mechanical**: a small diff (about 30 lines, at most 3 files, one package), or a structure-only change produced by a reproducible command (a codemod, an ast-grep rewrite, an IDE rename) with no hand edits beyond the command's output and tests changed only by the rename. A mechanical change has no size bound.
- **Settled**: the ticket states the exact change, with no open product or design decision. A bug's cause is already confirmed.
- **One layer**: no tidy-first or tidy-after PR.
- **Outside the sensitive areas**: it touches no auth or permissions, payments, schema or migrations, public API contracts, jobs, queues or concurrency, user-input handling, LLM prompts, CI, build or dependencies, or third-party services.

## Flow

You run every step yourself, with no briefer, implementer or verifier agent. megamoind's "When a skill is not available", "Gates", "Docs or skill changes" and "Sharing the workspace" apply as written. Each step starts with `python3 <skill-dir>/scripts/metrics.py mark <state> "<n> <name>"`, as in megamoind, with this flow's names: `0 brief`, `1 branch`, `2 implement`, `3 review`, `4 evidence`, `5 comments`, `6 pr`.

### 0. Brief (direct runs)

megamoind's step 0, started with `metrics.py start <ticket> --dir <scratchpad> --skill minimoi`, on the ticket `minimoi` already fetched and found eligible: no second fetch and no "Minimoi" question. The plan names no tidyings and, for a bug, cites the confirmed cause instead of running `diagnosing-bugs`. Write the brief with the line `mode: minimoi`.

### 1. Branch

megamoind's step 1, for one branch.

### 2. Implement

- **Behaviour change**: call the Skill tool with `tdd`, starting from a red test at the seam the brief names.
- **Mechanical change**: run the command, commit its output as a `refactor:` commit whose message names the command, and keep the command for the PR description.

Done when the ticket is implemented, committed on the branch, and the gates are green.

### 3. Review

One round, with no loop: call the Skill tool with `diff-review` over `<base>...<branch>` with `spec=<brief>`, `tag=megamoind-run: <run> role=review-code` and `reviewer=` the default `pair-review` names under its **reviewer** argument (the other model family than yours). Fix each finding within its scope, or discard it with a one-line reason. When diff-review reports it ran on the fallback, the report and the PR description say so.

Done when every finding is fixed or discarded and the gates are green.

### 4. Evidence

When the change shows in the UI, one screenshot of the touched screen at the width it matters most, following [`EVIDENCE.md`](EVIDENCE.md). It is what step 6 hands `github-pr` as megamoind step 7's "step 5's evidence", attached to the PR through `gh-attach`. Without UI, the run's tests and the review stand in for megamoind's step 5.

### 5. Comment cleanup

megamoind's step 6, run inline.

### 6. PR, CI and report

megamoind's steps 7 to 9, with `merge-risk` over the branch. The report lists tidy after, pair-review, security review and real-app verification as skipped by minimoi, and step 3's round in place of the review passes.

## Escalation

The run stays minimoi only while every eligibility condition holds. Escalate the moment any one breaks (the diff outgrows the size bound, it reaches a sensitive area, an open product or design decision or an unconfirmed cause turns up, a second layer becomes necessary), and also when a red gate has no obvious cause or CI needs a third fix push. Say which condition broke, remove `mode: minimoi` from the brief, run `metrics.py mark <state> "<n> <name>" --skill megamoind`, and continue as megamoind with the same brief: start the implementer (megamoind's "Agents") at megamoind's step 2 on the branch as it stands, so every step minimoi skipped runs before shipping. A PR already open stays open and is updated.
