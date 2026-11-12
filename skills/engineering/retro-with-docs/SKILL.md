---
name: retro-with-docs
description: "Runs a retrospective on an agent session and writes the stoppers and environment fixes it finds to ~/.skill-docs/retros/, for retro-digest. Use only when the user or another skill explicitly asks for it."
---

# Retro with docs

A retro proposes changes to the agent's **environment** (skills, steering files, checks, tooling, access) so the next session goes better. It only writes proposals down for `retro-digest` to apply, and leaves the session's code untouched. It runs unattended, sometimes as the last step of another skill, so decide everything yourself.

## 1. Locate the session

Default to the current session unless the user names another. In Claude Code, `python3 <skill-dir>/scripts/locate.py [--session <id or path>]` prints the transcript (the newest of this directory's project by default), its subagent transcripts, the project name and the retro folder. Include the subagents that carried implementation or verification. Read each transcript only through the condenser (1 MB shrinks to about 20 KB):

```bash
python3 <skill-dir>/scripts/condense_session.py <session.jsonl> [--max 400]
```

Each line starts with its `[index]`, the evidence reference. `--max` caps each entry's length. To see more of a few entries, re-run with a larger `--max` and grep their indexes. Read other agents' logs in their own format.

## 2. Hunt stoppers first

A **stopper** is any moment the agent could not move forward on its own: it stopped to ask the user for help, worked around a broken step, skipped or faked a step (verification above all), retried in circles, or gave up. They usually fall in the first three categories below.

Then hunt the rest of the **friction**: user corrections, `ERROR` results, repeated calls, long searches for a file or fact, review findings the implementer should have avoided.

Several friction points with one cause are one finding citing all their indexes. A stop the flow plans for (a question to the user) counts only when its input claimed the answer was already settled. A flaw in what the session produced, even when the product is a skill or steering file, points at the real finding, whatever in the environment let it through. A friction point with no concrete change worth making is noise.

Classify each finding by where its fix lands:

- **flow**: the run hit a dead end or an order that did not fit reality (a gate that could never pass, a wait with no signal, a step that depended on one not yet done).
- **skill**: a skill step was wrong, ambiguous, missing or contradicted another skill or steering file.
- **verification**: the agent could not check its work because the app, tests or CI would not run, data, credentials or a test account were missing, or the page or flow could not be reached.
- **navigation**: the agent struggled to find something, fixed by a pointer in the nearest steering file or doc.
- **checks**: a lint, type-check, test, hook or CI job would have caught it. Read the project's scripts, hooks and CI first, since an existing check that is unwired or broken is the finding.
- **standards**: a rule the reviewer should enforce.
- **steering**: `CLAUDE.md` / `AGENTS.md` misled, bloated or contradicted itself, including **no-ops**, lines that changed nothing versus the model's default.
- **tool-economy**: an expensive call, or a tool that wastes tokens, that a script or flag would make cheaper.
- **information-access**: information the agent needed and could not reach (logs, a read-only service, a doc).

Kind is **mechanical** when a deterministic check (lint rule, hook, CI job, script) can catch or enforce it, so that check is the proposal, and **judgement** otherwise.

Severity is **blocker** when the run stopped for the user or a step was skipped or faked, **high** when it caused a wrong result, rework or a user correction, **medium** when it wasted notable time or tokens, and **low** for a minor detour. Rate a workaround the agent found alone by its cost.

The step is done when every stopper and friction point in the timeline is either a finding or listed as dismissed noise at the end of the file.

## 3. Write the file

Write `<retro_dir>/<YYYY-MM-DD>-<topic-slug>.md`, with the folder `locate.py` printed (`~/.skill-docs/retros/<project>`, the project being the main checkout's name, so a linked worktree files under its repo), creating it if needed, in this exact shape, since `retro-digest` parses it:

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

Order findings by severity. A field may continue on indented `  - ` lines below it. Then run `python3 <skill-dir>/scripts/validate_retro.py <file>` and fix every problem it prints. Done when it prints nothing. Finish by printing the file path and a table of `id | severity | problem`.
