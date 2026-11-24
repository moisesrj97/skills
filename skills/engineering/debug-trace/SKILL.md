---
name: debug-trace
description: >-
  Adds temporary debug points that dump runtime values to a dedicated trace
  file, reads only that file, then removes every point. Use for temporary
  logging, to see what code does at runtime, or to verify a change end to end in
  the real app, even when the user runs it.
---

# Debug Trace

A few debug points write only the values that answer the question into a file that holds nothing else, so you read that instead of the app's full logs, and cleanup removes every point.

## 1. Marker and trace file

`python3 <skill-dir>/scripts/dbg.py new` prints a session marker (`CLAUDE-DBG:7c1a`) and an empty trace file (`/tmp/claude-debug-7c1a.log`). Tell the user both, and the path the run must execute to answer the question: a green run that never took it proves nothing.

## 2. Instrument

Every inserted line carries the marker and fits on one line, since cleanup deletes whole marked lines. That includes an import you add (`import { appendFileSync } from 'node:fs'; // CLAUDE-DBG:7c1a`); an import the file already had stays unmarked.

Each point emits `CLAUDE-DBG:<token> | <label> | <one-line JSON>`:

- **You run it** (a test, a script, a CLI): print the line and run `<cmd> 2>&1 | grep --line-buffered '<marker>' > <trace file>`. The pipe hides the exit code; check it separately when it matters.
- **The user runs it** (a dev server, a browser flow, anything e2e): append the line to the trace file with a synchronous write (`appendFileSync`, Python's `open(…, 'a')`), so each line lands even if the process dies.

When real inputs never reach the path, add a **probe**: a marked line right after the real assignment that overrides the input (`query = 'dogs'`), so deleting it restores the original. Tell the user it changes behaviour.

Done when the type-checker or linter passes on the touched files. If the user runs it, tell them where the points are and what to trigger, then wait. Truncate the trace (`: > <trace file>`) before each run.

## 3. Read the trace

`python3 <skill-dir>/scripts/dbg.py summary <token>` counts events per label; `--label <label> --fields <a>,<b.c>` gives one row per event. Read through it, not the raw file, and write any derived check as a throwaway script. If the path from step 1 didn't execute, the run is not evidence: say so and add a probe or change the input.

## 4. Clean up

As soon as you have the answer when you ran it, when the user says they're done when they did, and always before a commit or a hand-off:

```bash
python3 <skill-dir>/scripts/dbg.py list <token> <root>    # every match must be a line you added
python3 <skill-dir>/scripts/dbg.py clean <token> <root>   # deletes them and the trace file, re-scans
```

A match on a line you didn't add means other code carries your token: remove your points by hand. Done when `clean` exits 0 and its `git status --short` shows none of your edits.
