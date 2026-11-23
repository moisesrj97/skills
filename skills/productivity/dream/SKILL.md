---
name: dream
description: "Consolidates a project's auto-memory: folds what recent sessions learned into the memory files, fixes or deletes stale ones and trims MEMORY.md. Use to run a dream by hand or from `claude -p`, where auto-dream never fires."
disable-model-invocation: true
---

# Dream

A dream folds what recent sessions learned into the memory files and trims the index, so the next session loads fewer and more accurate memories. It uses the same lock file as Claude Code's auto-dream, so the two never consolidate the same sessions twice.

Write only inside the memory directory. Leave CLAUDE.md files and code untouched.

A dream runs unattended, end to end. Settle every conflict yourself with the rule in **Conflicts**, and report each decision as made.

To dream every project (a scheduled run), `python3 <skill-dir>/scripts/dream.py projects` lists the memory dirs with sessions past their lock, every session for one with no lock yet, leaving out scratch and temp dirs and counting T3 worktree sessions toward their repo. Run this skill on each with its `--memory-dir`, one subagent per project, and keep every session `start` lists: the lock is stamped past them all, so a session left out never comes back.

## Step 0: Take the lock

Pass the memory directory that your system prompt's auto-memory section names. Without `--memory-dir`, the script derives it from the repo.

```bash
python3 <skill-dir>/scripts/dream.py start --memory-dir <memory-dir>
```

It prints the memory and transcripts directories, when the last consolidation ran, and the sessions modified since then, without the current one; a session from a T3 worktree carries its own `transcripts_dir`. It also stamps the lock with the current time, so a finished dream needs no further script call. If you stop before finishing, restore the lock with `python3 <skill-dir>/scripts/dream.py rollback --memory-dir <memory-dir> --to <previous_lock_mtime>`. If the script reports that another dream holds the lock, stop and say so.

## Step 1: Orient

- `ls` the memory directory and read `MEMORY.md`.
- Skim the existing topic files, so you update them instead of writing duplicates. They also show the file format when your system prompt has no auto-memory section.
- If the project's `CLAUDE.md` or `AGENTS.md` isn't in your context, read it from disk. Step 4 compares memories against it.

## Step 2: Gather recent signal

In priority order:

1. **Drift.** Memories that contradict what the code shows now.
2. **Decisions and corrections in the listed sessions.** Transcripts are JSONL files of several MB. Read each one through its digest, which keeps the user's messages, their answers to questions and Claude's replies.
   `python3 <skill-dir>/scripts/dream.py digest <session-id> --memory-dir <memory-dir>`
   When the digest cuts a detail short, such as an error message or a value, grep the raw transcript for a narrow term: `grep -n "<term>" <transcripts_dir>/<session-id>.jsonl | tail -50`, with the session's own `transcripts_dir` when it has one.

## Step 3: Consolidate

Write or update memory files at the top level of the memory directory. Follow the auto-memory section's rules on format, types, and what to save.

- Merge new information into the existing topic file instead of adding a near-duplicate.
- Turn relative dates ("yesterday", "last week") into absolute ones.
- When a newer statement contradicts a memory, resolve it with **Conflicts**.

## Step 4: Prune and index

Delete a memory that a future session wouldn't act on differently: one that repeats a CLAUDE.md, AGENTS.md, skill or repo doc; records ticket status or finished work; describes code that no longer exists; or captures a one-off. Merge files on the same topic, and cut narrative down to the fact, its **Why:** and its **How to apply:**.

`MEMORY.md` is an index with one line per memory, `- [Title](file.md) — hook`, each under ~150 characters. The whole file stays under 200 lines and ~25 KB.

- Remove pointers to deleted or merged memories, and add pointers for new ones.
- Shorten any line over ~200 characters and move the detail into its topic file.

Check each `feedback` or `project` memory against the global and project CLAUDE.md, AGENTS.md and the skills it touches, and against the other memories. Where two say different things for the same case, resolve it with **Conflicts**. A memory that adds detail, or narrows a rule with a stated reason, is no conflict: leave it.

## Conflicts

The latest statement wins: the user can change their mind. Date each side:

- A session statement: the session's date.
- A memory: the date in its body, else its file's mtime.
- A line of CLAUDE.md, AGENTS.md or a skill: `git blame -L <n>,<n> --date=short <file>`. When the file is generated or symlinked from another, blame the source. Outside git, use the file's mtime.

Then:

- **The memory is older:** delete it, or rewrite it to agree when its *why* still adds something.
- **The memory is newer than an instruction file:** keep it, and open its body with "Supersedes <file>: \"<quoted line>\" since <date>", so the next session follows the memory. The instruction file stays untouched.
- **Two memories, or two sessions:** keep the newer meaning in one file and delete the other.

**Outlier.** When the newest statement goes against a rule the user stated in 3 or more earlier sessions, and it carries no sign of a change of mind ("from now on", "no longer", "I changed my mind", or a reason that applies beyond the case at hand), it is an exception, not a reversal. Keep the rule and add the exception to the same file, scoped to the context it came from. With such a sign, the newest statement wins outright.

## Team memory

When a `team/` subdirectory exists, teammates' sessions write to it too. Skim it in Step 1. Merge near-duplicates within it, and delete any personal memory that repeats a team one. Delete or fix a team memory only when the current code clearly contradicts it or a newer team memory replaces it. When unsure, leave it. Only the user moves a personal memory into `team/`.

## Report

You are done when you have considered every listed session and `MEMORY.md` points at exactly the files that exist. Reply with a short summary of what you created, updated, merged and deleted, and each conflict you settled: which side won and why. Every item is a decision already applied; the report is complete without any reply from the user. If nothing changed, say so.
