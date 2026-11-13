---
name: retro-sweep
description: "Sweeps the recent agent sessions that have no retro: a cheap model triages each for friction and a stronger one runs retro-with-docs on those that had some. Manual only; meant for a daily schedule."
disable-model-invocation: true
---

# Retro sweep

Friction is worth recording wherever it happened, not only in the sessions someone remembered to run `retro-with-docs` on. This sweep finds the sessions with none, keeps the cheap model on the cheap question (was there friction at all?) and spends the stronger one only on the retros. Over-reporting is fine: the retro drops what it cannot back with evidence, and `retro-digest` drops the one-offs. Every flagged session gets its retro, however many there are. It runs unattended: decide everything yourself and ask nothing.

Run at most 5 subagents at a time; launch the next wave when one finishes.

## 1. Pick the sessions

```bash
python3 <skill-dir>/scripts/sweep.py candidates --out <scratchpad>/sweep
```

It prints the sessions to review, each with its condensed timeline already written. `triage: "friction"` marks one an earlier run triaged whose retro is still missing, however old; `null` marks a new one. The script leaves out active sessions, evals and benches, earlier sweeps, sessions a retro already names and sessions already triaged clean. If the list is empty, say so in one line and stop.

## 2. Triage the new ones

Launch subagents with the Agent tool, `model: "haiku"`, five new sessions each. Each reads its sessions' `condensed` files and answers one line per session: `<session path> | friction | <what cost the agent, with an [index]>` or `<session path> | clean`.

Give them the bar: **friction** is anything that cost the agent time, tokens or correctness: an `ERROR` it had to get around, a retry, a user correction or interruption, a stop to ask the user, a skipped or faked step, a long search for a file or fact. **Clean** means the work went straight to its result. When unsure, answer friction: the retro decides whether it clears its own bar.

Record every verdict in one call, with a JSON file of `{"<session path>": {"verdict": "clean" | "friction", "why": "<the line>"}}`:

```bash
python3 <skill-dir>/scripts/sweep.py record --from <file>
```

Done when every new session has its verdict recorded.

## 3. Write the retros

For every session with friction, earlier ones first: launch subagents with the Agent tool, `model: "sonnet"`, one session each, with this brief:

> Call the Skill tool with `retro-with-docs` on the session `<session path>`. It ran in `<cwd>`: pass both to `locate.py` (`--session <session path> --cwd <cwd>`). The triage flagged: `<why>`. Write the retro file even when it ends with no findings: the file is what marks the session reviewed. Reply with its path and its count of open and skipped findings.

A retro may find nothing worth a finding: that is a valid result. A retro that fails stays pending for the next run: note its error for the report.

Done when every session with friction has its retro or a noted failure.

## 4. Report

One message: sessions triaged (clean / friction), retros written (path and open/skipped counts each), how many flagged sessions the retro found nothing in (a rising share means the triage is spending too much), and any failure with its error.
