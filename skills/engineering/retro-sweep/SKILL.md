---
name: retro-sweep
description: "Sweeps the recent agent sessions that have no retro: a cheap model triages each for friction and a stronger one runs retro-with-docs on those that had some. Manual only; meant for a daily schedule."
disable-model-invocation: true
---

# Retro sweep

Friction is worth recording wherever it happened, not only in the sessions someone remembered to run `retro-with-docs` on. This sweep finds the sessions with none, keeps the cheap model on the cheap question (was there friction at all?) and spends the stronger one only on the retros. It runs unattended: decide everything yourself and ask nothing.

## 1. Pick the sessions

```bash
python3 <skill-dir>/scripts/sweep.py candidates --out <scratchpad>/sweep
```

It prints the sessions to review, each with its condensed timeline already written. `triage: "friction"` marks one an earlier run triaged whose retro is still missing; `null` marks a new one. The script leaves out active sessions, evals and benches, earlier sweeps, sessions a retro already names and sessions already triaged clean. If the list is empty, say so in one line and stop.

## 2. Triage the new ones

Launch subagents with the Agent tool, `model: "haiku"`, in parallel, five new sessions each. Each reads its sessions' `condensed` files and answers one line per session: `<session path> | friction | <what cost the agent, with an [index]>` or `<session path> | clean`.

Give them the bar: **friction** is anything that cost the agent time, tokens or correctness: an `ERROR` it had to get around, a retry, a user correction or interruption, a stop to ask the user, a skipped or faked step, a long search for a file or fact. **Clean** means the work went straight to its result. When unsure, answer friction: the retro decides whether it clears its own bar.

Record every verdict in one call, with a JSON file of `{"<session path>": {"verdict": "clean" | "friction", "why": "<the line>"}}`:

```bash
python3 <skill-dir>/scripts/sweep.py record --from <file>
```

Done when every new session has its verdict recorded.

## 3. Write the retros

For the sessions with friction, earlier ones first, up to 10 per run: launch subagents with the Agent tool, `model: "sonnet"`, in parallel, one session each, with this brief:

> Call the Skill tool with `retro-with-docs` on the session `<session path>`. It ran in `<cwd>`: pass both to `locate.py` (`--session <session path> --cwd <cwd>`). The triage flagged: `<why>`. Reply with the retro file's path and its count of open and skipped findings.

The rest stay pending for the next run. A retro that fails stays pending too: note its error for the report.

## 4. Report

One message: sessions triaged (clean / friction), retros written (path and open/skipped counts each), sessions still pending, and any failure with its error.
