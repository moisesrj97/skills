---
name: dream
description: "Consolidates a project's auto-memory: folds signal from recent sessions into the memory files, fixes or deletes stale ones and tightens MEMORY.md. Use to run a dream by hand or from `claude -p`, where auto-dream never fires."
disable-model-invocation: true
---

# Dream

A dream is a reflective pass over the memory directory: synthesize what recent sessions learned into durable, well-organized memories so future sessions orient quickly. It shares its bookkeeping with Claude Code's own auto-dream, so the two never consolidate the same sessions twice.

Write only inside the memory directory. CLAUDE.md files and code are read-only during a dream.

## Step 0: Take the lock

The memory directory is the one your system prompt's auto-memory section names. Pass it explicitly; without it the script derives it from the repo:

```bash
python3 <skill-dir>/scripts/dream.py start --memory-dir <memory-dir>
```

It prints the memory and transcripts directories, when the last consolidation ran, and the sessions modified since (the current one excluded). It stamps the lock as of now, which is all a finished dream needs. If you stop before finishing, restore it with `python3 <skill-dir>/scripts/dream.py rollback --memory-dir <memory-dir> --to <previous_lock_mtime>`. If it reports another dream holding the lock, stop and say so.

## Step 1: Orient

- `ls` the memory directory; read `MEMORY.md`.
- Skim the existing topic files so you improve them rather than create duplicates. They also show the file format when your system prompt has no auto-memory section.
- Read the project's `CLAUDE.md` / `AGENTS.md` from disk when they aren't already in your context: Step 4 reconciles against them.

## Step 2: Gather recent signal

In priority order:

1. **Drift**: memories that contradict what the code shows now.
2. **Decisions and corrections** in the listed sessions. Transcripts are multi-MB JSONL; read each through its digest, which keeps the user's messages, their answers to questions and Claude's replies:
   `python3 <skill-dir>/scripts/dream.py digest <session-id> --memory-dir <memory-dir>`
   For a detail the digest cut short (an error message, a value), grep the raw transcript for a narrow term: `grep -n "<term>" <transcripts_dir>/<session-id>.jsonl | tail -50`.

## Step 3: Consolidate

Write or update memory files at the top level of the memory directory, following the format and type rules of the auto-memory section (what to save and what not to).

- Merge new signal into the existing topic file instead of adding a near-duplicate.
- Turn relative dates ("yesterday", "last week") into absolute ones.
- Fix contradicted facts at the source: edit or delete the wrong file.

## Step 4: Prune and index

`MEMORY.md` is an index: one line per memory, `- [Title](file.md) — hook`, under ~150 characters, the whole file under 200 lines and ~25 KB.

- Remove pointers to stale, wrong or superseded memories, and add pointers for new ones.
- Shorten any line over ~200 characters, moving the detail into its topic file.
- When two files disagree, fix the wrong one.

**Reconcile against CLAUDE.md.** For each `feedback` or `project` memory that covers the same topic as an instruction in the global or project CLAUDE.md / AGENTS.md:

- **Memory is stale** (different procedure for the same task): CLAUDE.md is the maintained source. Delete the memory, or rewrite it to agree when its *why* is still worth keeping.
- **CLAUDE.md may be stale** (the memory is clearly dated after it and explicitly corrects it): annotate the memory "contradicts CLAUDE.md — verify which is current" and list it in your summary.
- **No conflict** (the memory adds detail, or narrows a rule with a stated reason): leave it.

A "the user corrected me" framing doesn't make a memory newer than CLAUDE.md, which may have changed since.

## Team memory

When a `team/` subdirectory exists, teammates' sessions write to it too. Skim it in Step 1; merge near-duplicates within it, and delete a personal memory that restates a team one. Delete or fix a team memory only when the current code clearly contradicts it or a newer team memory supersedes it; when unsure, leave it. Personal memories stay out of `team/`: promoting one is the user's call.

## Report

Done when every listed session has been considered and `MEMORY.md` points at exactly the files that exist. Reply with a brief summary of what you consolidated, updated or pruned, plus any memory annotated against CLAUDE.md. If nothing changed, say so.
