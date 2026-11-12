---
name: debug-trace
description: >-
  Adds temporary debug points that dump runtime values to a dedicated trace
  file, reads only that file, then removes every point. Use for temporary
  logging, to see what code does at runtime, or to verify a change end to end in
  the real app, even when the user runs it.
---

# Debug Trace

A complex app's full logs bury the few values you need and burn context. A handful of debug points write only what answers the question into a file that holds nothing else, and cleanup removes every one of them.

This is for runtime questions. If reading the code answers it, read the code. If the app already logs exactly what you need, grep that instead.

## 1. Frame the question before touching code

Tell the user, in one or two sentences:

- **What you want to learn or prove** ("each stock slot gets a distinct photo").
- **What the trace must show to prove it, including the code path that has to execute.** A run can be green without exercising the path you care about. 9 distinct photos out of 9 proves nothing about dedup if no two slots ever wanted the same photo. Naming the path up front lets you spot that.

This decides where the points go and what you check the trace against.

## 2. Marker and trace file

Get a **session marker** and its trace file with `python3 <skill-dir>/scripts/dbg.py new`: `CLAUDE-DBG:` plus a fresh short token (`CLAUDE-DBG:7c1a`), and an empty `/tmp/claude-debug-<token>.log`. Every insertion carries this exact literal and fits on a single line. That makes cleanup a deterministic grep-and-delete of whole lines, so a point split across lines would leave half of itself behind.

The trace file sits outside the repo, so nobody can commit it. It goes in `/tmp` rather than a session scratchpad because the instrumented process, often one the user started, must be able to write it.

Tell the user both.

## 3. Who runs it decides how points emit

| Who runs | Emit with | Why |
|---|---|---|
| **You** (a test, a script, a CLI you launch) | a plain print, piped through `grep` for the marker into the trace file | no imports, works in any language |
| **The user** (a dev server, watch mode, a browser flow, anything e2e) | a **synchronous** append straight to the trace file | you can't capture their stdout, and a sync write lands each line even if the process dies |

E2e checks are usually user-driven. Use the append there from the start, rather than print+grep followed by asking the user to pipe their server output.

Print examples (marker in the string, one line):

```
console.log('CLAUDE-DBG:7c1a | after-fetch |', JSON.stringify(user));          // JS/TS
print('CLAUDE-DBG:7c1a | after-fetch |', json.dumps(user, default=str))         # Python
fmt.Printf("CLAUDE-DBG:7c1a | after-fetch | %s\n", func() []byte { b, _ := json.Marshal(user); return b }()) // Go
```

Run: `<cmd> 2>&1 | grep --line-buffered 'CLAUDE-DBG:7c1a' > /tmp/claude-debug-7c1a.log`. The pipe hides the command's exit code, so check it separately if it matters.

Append examples:

```
// JS/TS, ES module: the import once at the top of the file, then one call per point
import { appendFileSync } from 'node:fs'; // CLAUDE-DBG:7c1a
appendFileSync('/tmp/claude-debug-7c1a.log', `CLAUDE-DBG:7c1a | after-fetch | ${JSON.stringify(user)}\n`);

// JS, CommonJS: inline, with no import line
require('node:fs').appendFileSync('/tmp/claude-debug-7c1a.log', `CLAUDE-DBG:7c1a | after-fetch | ${JSON.stringify(user)}\n`);

# Python
open('/tmp/claude-debug-7c1a.log','a').write(f'CLAUDE-DBG:7c1a | after-fetch | {json.dumps(user, default=str)}\n')
```

An import you add is a second marked line, so cleanup catches it too. This holds in any language, e.g. `"encoding/json" // CLAUDE-DBG:7c1a` in a Go import block. Leave an import the file already had unmarked, or cleanup deletes it. Write synchronously. Async writes (`fs.promises`, dynamic `import()`) may not land before exit.

## 4. Instrument

Line format: `CLAUDE-DBG:<token> | <label> | <one-line JSON>`.

- **Labels** name the stage (`search`, `assignment`, `outcome`). You split the trace by them later, so keep them distinct.
- **One event per line, JSON on one line**, so a script can parse it.
- Include what correlates events across stages: a request or entity id, and a timestamp when ordering matters (concurrent work interleaves).
- Put points at **stage boundaries** (what went in, what was decided, what actually landed) rather than many inside a stage. Logging both what was chosen and what ended up in the output catches a correct decision that a later step drops.
- Dump only what answers the question, and truncate long arrays (`.slice(0, 8)`). Guard any point inside a hot loop.

Done when the type-checker or linter passes on the touched files, so a typo doesn't cost the user a broken run.

### Forcing a case (probes)

Sometimes the real inputs never reach the path you need to verify. Then add a **probe**, a marked line that overrides an input to provoke that path: forcing every search query to `"dogs"` so slots collide, pinning a flag, shrinking a limit.

- Same marker, same single line, so cleanup removes it with the rest.
- Insert it *after* the real assignment rather than editing that line, so deleting the marked line restores the original exactly.
- Tell the user it is there and that it changes behaviour. Note which logged fields still show the pre-override value.
- Prefer a probe to asking the user to hunt for real inputs that happen to hit the case. A probe is deterministic.

## 5. Hand off or run

If you run it, run it and go to step 6.

If the user runs it, tell them concisely:

- that the points are in (file:line per label) and type-check passes
- what to do (restart, or just re-trigger)
- what you'll look for, so they know whether the run was useful

Then stop and wait. Truncate the trace (`: > /tmp/claude-debug-<token>.log`) before each new run so runs don't mix.

## 6. Read the trace

Read the trace through summaries, keeping raw JSON lines out of context. `python3 <skill-dir>/scripts/dbg.py summary <token>` counts events per label with their keys; add `--label <label> --fields <a>,<b.c>` for one row per event with the fields that matter. Derived checks (distinct vs total, ranks, matches between stages) are specific to the question: write those as a short throwaway script (inline Python via heredoc, or `jq`).

Then **verify** rather than skim:

1. Did the path named in step 1 actually execute? If not, say plainly that the run is not evidence, and propose a probe or different input.
2. Recompute the expected result by hand for the interesting rows (sort order, which candidate should win, what a counter should total) and compare. Agreement on derived numbers is much stronger evidence than "looks fine".
3. Report what held, what didn't, and what remains unexercised.

Iterate with the same token: adjust points, truncate, re-run, re-read.

## 7. Clean up

When you ran it yourself, clean up as soon as you have the answer. When the user drives the runs, clean up when they say they're done, since they may want another run.

```bash
python3 <skill-dir>/scripts/dbg.py list <token> <root>    # check every match is a line you added
python3 <skill-dir>/scripts/dbg.py clean <token> <root>   # deletes them and the trace file, re-scans
```

`list` and `clean` skip `node_modules`, `.git`, build output and binary files. A match on a line you didn't add means someone else's code carries your token: remove your points by hand instead. `clean` exits 1 naming any marked line left, and prints `git status --short`, which must show none of your edits.

Done when `clean` exits 0 and the status shows none of your edits. Run it before you claim cleanup. Clean up before any commit, and before handing off mid-debug.
