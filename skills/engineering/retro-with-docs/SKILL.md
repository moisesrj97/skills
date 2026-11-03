---
name: retro-with-docs
description: "Runs a retrospective on an agent session and writes the stoppers and environment fixes it finds to ~/.skill-docs/retros/, for retro-digest. Use only when the user or another skill explicitly asks for it."
---

# Retro with docs

A retro proposes changes to the agent's **environment** (skills, steering files, checks, tooling, access) so the next session goes better. It never edits the code the session produced and never applies its own proposals: it writes them down, and `retro-digest` acts on them. It runs unattended, also as the last step of another skill: decide everything yourself.

## 1. Locate the session

Default to the current session unless the user names another. In Claude Code the transcripts live in `~/.claude/projects/<cwd with every non-alphanumeric char replaced by ->/<session-id>.jsonl` (the current one is the newest by mtime), with subagent transcripts in `<session-id>/subagents/*.jsonl` (include those that carried implementation or verification). Read them condensed, never raw (a 1 MB transcript condenses to ~20 KB):

```bash
python3 <skill-dir>/scripts/condense_session.py <session.jsonl> [--max 400]
```

Each line starts with its `[index]`, which is the evidence reference. `--max` caps each entry's length; to see more of a few entries, re-run with a larger `--max` and grep their indexes. Other agents' logs: read their own format.

## 2. Hunt stoppers first

A **stopper** is any moment the agent could not move forward on its own: it stopped to ask the user for help, worked around a broken step, skipped or faked a step (verification above all), retried in circles, or gave up. Typical sources:

- **flow**: the run hit a dead end or an order that did not fit reality (a gate that could never pass, a wait with no signal, a step that depended on one not yet done).
- **skill**: a skill step was wrong, ambiguous, missing or contradicted another skill or steering file.
- **verification**: the agent could not check its work: the app, tests or CI would not run, data, credentials or a test account were missing, the page or flow could not be reached.

Then the rest of the **friction**: user corrections, `ERROR` results, repeated calls, long searches for a file or fact, review findings the implementer should have avoided. The step is done when every stopper and friction point in the timeline is either a finding or listed as dismissed noise at the end of the file.

Several friction points with one cause are one finding citing all their indexes. A stop the flow plans for (a question to the user) counts only when its input claimed the answer was already settled.

A flaw in what the session produced is not a finding, even when the product is itself a skill or steering file: the finding is whatever in the environment let the flaw through. A friction point with no concrete change worth making is noise.

Classify each finding by where its fix lands. Besides **flow**, **skill** and **verification** above:

- **navigation**: the agent struggled to find something. Fix: a pointer in the nearest steering file or doc.
- **checks**: a lint, type-check, test, hook or CI job would have caught it. Read the project's existing scripts, hooks and CI first: a check that exists but is unwired or broken is the finding.
- **standards**: a rule the reviewer should enforce.
- **steering**: `CLAUDE.md` / `AGENTS.md` misled, bloated or contradicted itself, including **no-ops**: lines that changed nothing versus the model's default.
- **tool-economy**: an expensive call, or a tool that wastes tokens, that a script or flag would streamline.
- **information-access**: information the agent needed and could not reach (logs, a read-only service, a doc).

Kind: **mechanical** when a deterministic check (lint rule, hook, CI job, script) can catch or enforce it, so that is the proposal; **judgement** otherwise.

Severity: **blocker** when the run stopped for the user or a step was skipped or faked; a workaround the agent found alone is rated by its cost; **high** caused a wrong result, rework or a user correction; **medium** wasted notable time or tokens; **low** a minor detour.

## 3. Write the file

Project: the base name of the main checkout, `basename "$(dirname "$(git rev-parse --path-format=absolute --git-common-dir)")"`, so a linked worktree files under its main repo; outside git, the base name of the working directory. Write `~/.skill-docs/retros/<project>/<YYYY-MM-DD>-<topic-slug>.md`, creating the folder if needed, in this exact shape, since `retro-digest` parses it:

```markdown
---
date: <YYYY-MM-DD of the session>
project: <project>
session: <transcript path>
branch: <the session's branch, if any>
summary: <one line: what the session set out to do>
---

# Retro: <topic>

## R1: <the problem, one line>

- status: open
- severity: blocker | high | medium | low
- category: flow | skill | verification | navigation | checks | standards | steering | tool-economy | information-access
- kind: mechanical | judgement
- target: <file or system the change lands in; "guess: …" when the session does not show it>
- evidence: [<index>] <short quote from the session>
- proposal: <the concrete change, specific enough to apply without rereading the session>

Dismissed as noise: <[index] reason; …>
```

Order findings by severity. Finish by printing the file path and a table of `id | severity | problem`.
