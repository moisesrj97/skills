---
name: debug-trace
description: >-
  Inject temporary, tagged debug points that dump structured values (and, when
  needed, force inputs) into an isolated trace file, read only that file instead
  of the app's noisy logs, then remove every insertion. Use it to see what code
  actually does at runtime — unexpected state, data that doesn't add up, a flow
  you can't follow by reading — and to verify a change end-to-end in the real
  app, including when the user drives the run (a dev server, a browser flow) and
  you only read the result. Trigger on "debug trace", "scoped debug logging",
  "instrument and run", "vuelca a un log", "inyecta un dump", "mete unos logs
  temporales", "verifica que funciona e2e", "comprueba en real qué devuelve X",
  or any request to log intermediate values temporarily, even if they don't say
  "trace".
---

# Debug Trace

## Why

A complex app's full log output buries the few values you need under thousands
of irrelevant lines, and reading it burns context. Scoped instrumentation fixes
that: a handful of debug points emit only what answers the question, into a
file that holds nothing else, and every one of them is removed afterwards.

It is for *runtime* questions. If reading the code answers it, read the code. If
the app already logs exactly what you need, grep that instead of adding points.

## 1. Frame the question before touching code

Write down, in one or two sentences to the user:

- **What you want to learn or prove** ("each stock slot gets a distinct photo").
- **What the trace must show to prove it, including which code path has to
  execute.** A run can be green without exercising the path you care about —
  9 distinct photos out of 9 proves nothing about dedup if no two slots ever
  wanted the same photo. Naming the path up front is what lets you spot that.

This decides where the points go and is what you'll check the trace against.

## 2. Marker and trace file

Pick a **session marker**: `CLAUDE-DBG:` plus a fresh short token
(`CLAUDE-DBG:7c1a`). Every insertion carries this exact literal, on a single
line. That invariant is what makes cleanup a deterministic grep-and-delete —
never split a point across lines, or the delete leaves half of it behind.

Trace file: `/tmp/claude-debug-<token>.log`. It lives outside the repo so it can
never be committed, and in `/tmp` rather than a session scratchpad because the
instrumented process (often one the user started) must be able to write it.

Tell the user both.

## 3. Who runs it decides how points emit

| Who runs | Emit with | Why |
|---|---|---|
| **You** (a test, a script, a CLI you launch) | a plain print, piped through `grep` for the marker into the trace file | no imports, works in any language |
| **The user** (a dev server, watch mode, a browser flow, anything e2e) | a **synchronous** append straight to the trace file | you can't capture their stdout; sync flushes each line even if the process dies |

The user-driven case is the common one for e2e checks — don't default to
print+grep and then ask the user to pipe their server output.

Print examples (marker in the string, one line):

```
console.log('CLAUDE-DBG:7c1a | after-fetch |', JSON.stringify(user));          // JS/TS
print('CLAUDE-DBG:7c1a | after-fetch |', json.dumps(user, default=str))         # Python
fmt.Printf("CLAUDE-DBG:7c1a | after-fetch | %+v\n", user)                       // Go
```

Run: `<cmd> 2>&1 | grep --line-buffered 'CLAUDE-DBG:7c1a' > /tmp/claude-debug-7c1a.log`
(grep swallows the exit code — check it separately if it matters).

Append examples:

```
// JS/TS: the import once, then one call per point
import { appendFileSync } from 'node:fs'; // CLAUDE-DBG:7c1a
appendFileSync('/tmp/claude-debug-7c1a.log', `CLAUDE-DBG:7c1a | after-fetch | ${JSON.stringify(user)}\n`);

# Python
open('/tmp/claude-debug-7c1a.log','a').write(f'CLAUDE-DBG:7c1a | after-fetch | {json.dumps(user, default=str)}\n')
```

The import is a second marked line, so cleanup catches it too. Avoid async
writes (`fs.promises`, dynamic `import()`): they may not land before exit.

## 4. Instrument

Line format: `CLAUDE-DBG:<token> | <label> | <one-line JSON>`.

- **Labels** name the stage (`search`, `assignment`, `outcome`). They are how
  you split the trace later, so keep them distinct.
- **One event per line, JSON on one line**, so a script can parse it.
- Include what correlates events across stages: a request/entity id, and a
  timestamp when ordering matters (concurrent work interleaves).
- Prefer points at **stage boundaries** — what went in, what was decided, what
  actually landed — over many points inside a stage. Logging both "what was
  chosen" and "what ended up in the output" catches a correct decision that a
  later step drops.
- Dump only what answers the question; truncate long arrays (`.slice(0, 8)`).
  Never inside a hot loop without a guard.

After inserting, run the type-checker or linter on the touched files so a typo
doesn't cost the user a broken run.

### Forcing a case (probes)

Sometimes the real inputs never reach the path you need to verify. Then add a
**probe**: a marked line that overrides an input to provoke it — forcing every
search query to `"dogs"` so slots collide, pinning a flag, shrinking a limit.

- Same marker, same single line, so cleanup removes it with the rest.
- Insert it *after* the real assignment rather than editing that line, so
  deleting the marked line restores the original exactly.
- Tell the user it is there and that it changes behaviour; note which logged
  fields still show the pre-override value.
- Prefer it over asking the user to hunt for real inputs that happen to hit the
  case — it's deterministic.

## 5. Hand off or run

If you run it: run, then go to step 6.

If the user runs it, tell them concisely:
- that the points are in (file:line per label) and type-check passes;
- what to do (restart? just re-trigger?);
- what you'll be looking for, so they know whether the run was useful.

Then stop and wait. Truncate the trace (`: > /tmp/claude-debug-<token>.log`)
before each new run so runs don't mix.

## 6. Read the trace

Don't read raw JSON lines into context. Write a short throwaway script (python
inline via heredoc, or `jq`) that prints a compact per-stage summary: counts per
label, one row per entity with the fields that matter, and derived checks
(distinct vs total, ranks, matches between stages).

Then **verify, don't skim**:
1. Did the path named in step 1 actually execute? If not, say so plainly — the
   run is not evidence — and propose a probe or different input.
2. Recompute the expected result by hand for the interesting rows (sorting
   order, which candidate should win, what a counter should total) and compare.
   Agreement on derived numbers is much stronger evidence than "looks fine".
3. Report what held, what didn't, and what remains unexercised.

Iterate with the same token: adjust points, truncate, re-run, re-read.

## 7. Clean up

When you ran it yourself, clean up as soon as you have the answer. When the
user drives the runs, clean up when they say they're done — they may want
another run.

```bash
grep -rn --exclude-dir={node_modules,.git,dist,build} 'CLAUDE-DBG:<token>' <root>
grep -rl --exclude-dir={node_modules,.git,dist,build} 'CLAUDE-DBG:<token>' <root> \
  | xargs sed -i '' '/CLAUDE-DBG:<token>/d'   # GNU sed: sed -i '/…/d'
rm -f /tmp/claude-debug-<token>.log
grep -rn --exclude-dir={node_modules,.git,dist,build} 'CLAUDE-DBG:<token>' <root>   # must print nothing
git status --short && git diff --stat   # must show none of your edits
```

Eyeball the first grep before deleting in case a match sits on a line you didn't
add. The empty final grep plus a clean diff is the proof — don't claim cleanup
without running both. Never commit with a point still in; if you must hand off
mid-debug, clean up first.
