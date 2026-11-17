---
name: dream
description: "Consolidates a project's auto-memory: folds what recent sessions learned into the memory files, fixes or deletes stale ones and trims MEMORY.md. Use to run a dream by hand or from `claude -p`, where auto-dream never fires."
disable-model-invocation: true
---

# Dream

A dream folds what recent sessions learned into the memory files and trims the index, so the next session loads fewer and more accurate memories. It uses the same lock file as Claude Code's auto-dream, so the two never consolidate the same sessions twice.

Write only inside the memory directory. Leave CLAUDE.md files and code untouched.

## Step 0: Take the lock

Pass the memory directory that your system prompt's auto-memory section names. Without `--memory-dir`, the script derives it from the repo.

```bash
python3 <skill-dir>/scripts/dream.py start --memory-dir <memory-dir>
```

It prints the memory and transcripts directories, when the last consolidation ran, and the sessions modified since then, without the current one. It also stamps the lock with the current time, so a finished dream needs no further script call. If you stop before finishing, restore the lock with `python3 <skill-dir>/scripts/dream.py rollback --memory-dir <memory-dir> --to <previous_lock_mtime>`. If the script reports that another dream holds the lock, stop and say so.

## Step 1: Orient

- `ls` the memory directory and read `MEMORY.md`.
- Skim the existing topic files, so you update them instead of writing duplicates. They also show the file format when your system prompt has no auto-memory section.
- If the project's `CLAUDE.md` or `AGENTS.md` isn't in your context, read it from disk. Step 4 compares memories against it.

## Step 2: Gather recent signal

In priority order:

1. **Drift.** Memories that contradict what the code shows now.
2. **Decisions and corrections in the listed sessions.** Transcripts are JSONL files of several MB. Read each one through its digest, which keeps the user's messages, their answers to questions and Claude's replies.
   `python3 <skill-dir>/scripts/dream.py digest <session-id> --memory-dir <memory-dir>`
   When the digest cuts a detail short, such as an error message or a value, grep the raw transcript for a narrow term: `grep -n "<term>" <transcripts_dir>/<session-id>.jsonl | tail -50`.

## Step 3: Consolidate

Write or update memory files at the top level of the memory directory. Follow the auto-memory section's rules on format, types, and what to save.

- Merge new information into the existing topic file instead of adding a near-duplicate.
- Turn relative dates ("yesterday", "last week") into absolute ones.
- When a newer fact contradicts a memory, edit or delete that memory's file.

## Step 4: Prune and index

`MEMORY.md` is an index with one line per memory, `- [Title](file.md) — hook`, each under ~150 characters. The whole file stays under 200 lines and ~25 KB.

- Remove pointers to stale, wrong or superseded memories, and add pointers for new ones.
- Shorten any line over ~200 characters and move the detail into its topic file.
- When two files disagree, fix the wrong one.

**Compare memories against CLAUDE.md.** Check each `feedback` or `project` memory that covers the same topic as an instruction in the global or project CLAUDE.md or AGENTS.md.

- **The memory is stale** when it describes a different procedure for the same task. CLAUDE.md is the maintained source, so delete the memory, or rewrite it to agree when its *why* is still worth keeping.
- **CLAUDE.md may be stale** when the memory is clearly dated after it and corrects it explicitly. Annotate the memory with "contradicts CLAUDE.md, verify which is current" and list it in your summary.
- **There is no conflict** when the memory adds detail, or narrows a rule with a stated reason. Leave it.

A memory that says "the user corrected me" isn't necessarily newer than CLAUDE.md, which may have changed since.

## Team memory

When a `team/` subdirectory exists, teammates' sessions write to it too. Skim it in Step 1. Merge near-duplicates within it, and delete any personal memory that repeats a team one. Delete or fix a team memory only when the current code clearly contradicts it or a newer team memory replaces it. When unsure, leave it. Only the user moves a personal memory into `team/`.

## Report

You are done when you have considered every listed session and `MEMORY.md` points at exactly the files that exist. Reply with a short summary of what you consolidated, updated or pruned, and list any memory you annotated against CLAUDE.md. If nothing changed, say so.
