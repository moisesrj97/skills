---
name: retro-with-docs
description: "Runs a retrospective on an agent session and writes the friction it finds, stoppers first, to ~/.skill-docs/retros/, for retro-digest. Use only when the user or another skill explicitly asks for it."
---

# Retro with docs

A retro proposes changes to the agent's **environment** (skills, steering files, checks, tooling, access) so the next session goes better. It only writes proposals down for `retro-digest` to apply, and leaves the session's code untouched. It runs unattended, sometimes as the last step of another skill, so decide everything yourself.

## 1. Locate the session

Default to the current session unless the user names another. In Claude Code, `python3 <skill-dir>/scripts/locate.py [--session <id or path>] [--cwd <dir the session ran in>]` prints the transcript (the newest of this directory's project by default), its subagent transcripts, the project name and the retro folder. Include the subagents that carried implementation or verification. Read each transcript only through the condenser (1 MB shrinks to about 20 KB):

```bash
python3 <skill-dir>/scripts/condense_session.py <session.jsonl> [--max 400]
```

Each line starts with its `[index]`, the evidence reference. `--max` caps each entry's length. To see more of a few entries, re-run with a larger `--max` and grep their indexes. Read other agents' logs in their own format.

## 2. Hunt the friction

**Friction** is anything in the timeline that cost the agent time, tokens or correctness. Hunt **stoppers** first, the friction that rates blocker: any moment the agent could not move forward on its own, because it stopped to ask the user for help, worked around a broken step, skipped or faked a step (verification above all), retried in circles, or gave up. Then the rest: user corrections, `ERROR` results, repeated calls, long searches for a file or fact, review findings the implementer should have avoided.

Several friction points with one cause are one finding citing all their indexes. A stop the flow plans for (a question to the user) is friction only when its input claimed the answer was already settled. When the session produced something flawed, even a skill or steering file, the finding is whatever in the environment let the flaw through.

A finding is **open** when it clears the bar:

- **durable**: its cause stays in the environment, so the next session hits it too;
- **owned**: there is a file, check or system where the change lands;
- **reproducible**: the evidence shows the gap (a missing step, a doc that disagrees with the code, a broken harness).

The rest (a one-off slip, a transient outage, a guard working as designed) is **skipped**, with the reason it misses the bar. Write skipped friction down too: `retro-digest` promotes it once it recurs.

Look each finding up among the friction already recorded, with two or three distinctive terms (a tool, a file, an error):

```bash
python3 <skill-dir>/scripts/known.py <term> [<term> ...]
```

When one is the same friction, add `- matches: <ref>` to yours.

Classify each open finding by where its fix lands:

- **flow**: the run hit a dead end or an order that did not fit reality (a gate that could never pass, a wait with no signal, a step that depended on one not yet done).
- **skill**: a skill step was wrong, ambiguous, missing or contradicted another skill or steering file.
- **verification**: the agent could not check its work because the app, tests or CI would not run, data, credentials or a test account were missing, or the page or flow could not be reached.
- **navigation**: the agent struggled to find something, fixed by a pointer in the nearest steering file or doc.
- **checks**: a lint, type-check, test, hook or CI job would have caught it. Read the project's scripts, hooks and CI first, since an existing check that is unwired or broken is the finding.
- **standards**: a rule the reviewer should enforce.
- **steering**: `CLAUDE.md` / `AGENTS.md` misled or contradicted itself.
- **wasted-context**: always-loaded text (a steering file, a skill description, a doc read every run) that spends context without changing behaviour: a no-op versus the model's default, a duplicate, a stale line. Its target names the lines, as `path:start-end`.
- **tool-economy**: an expensive call, or a tool that wastes tokens, that a script or flag would make cheaper.
- **information-access**: information the agent needed and could not reach (logs, a read-only service, a doc).

Kind is **mechanical** when a deterministic check (lint rule, hook, CI job, script) can catch or enforce it, so that check is the proposal, and **judgement** otherwise.

Severity is **blocker** when the run stopped for the user or a step was skipped or faked, **high** when it caused a wrong result, rework or a user correction, **medium** when it wasted notable time or tokens, and **low** for a minor detour. Rate a workaround the agent found alone by its cost.

The step is done when every friction point in the timeline is a finding, open or skipped, and you have looked each one up with `known.py`.

## 3. Write the file

Write `<retro_dir>/<YYYY-MM-DD>-<topic-slug>.md` in the folder `locate.py` printed, creating it if needed. That folder is `~/.skill-docs/retros/<project>`, where the project is the main checkout's name, so a linked worktree files under its repo. Use this exact shape, since `retro-digest` parses it:

```markdown
---
date: <YYYY-MM-DD of the session>
project: <project>
session: <transcript path>
branch: <the session's branch, if any>
summary: <one line: what the session set out to do>
---

# Retro: <topic>

## R1: <the friction, one line>

- status: open
- severity: blocker | high | medium | low
- category: flow | skill | verification | navigation | checks | standards | steering | wasted-context | tool-economy | information-access
- kind: mechanical | judgement
- target: <file or system the change lands in, or unknown>
- evidence: [<index>] <short quote from the session>
- expected: <the path the agent should have had>
- cost: <what it cost (time, calls, rework) and the workaround, if any>
- cause: <what the evidence shows, citing [<index>]> | suspicion: <a guess> | unknown
- proposal: <the concrete change, specific enough to apply without rereading the session> | none yet
- matches: <ref of the same recorded friction, only when known.py found one>

## R5: <skipped friction, one line>

- status: skipped (<why it misses the bar>)
- evidence: [<index>] <short quote>
```

Put what happened in `evidence`, and keep `cause` and `proposal` to what the evidence supports. A proposal fixes the owner: it corrects the step, rule or check that misled instead of adding a special case beside it.

Order open findings by severity, then the skipped ones. A field may continue on indented `  - ` lines below it. Then run `python3 <skill-dir>/scripts/validate_retro.py <file>` and fix every problem it prints. Done when it prints nothing. Finish by printing the file path and a table of `id | severity | problem` for the open findings, plus the count of skipped ones.
