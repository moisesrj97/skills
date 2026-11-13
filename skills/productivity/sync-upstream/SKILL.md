---
name: sync-upstream
description: "Checks the skills pulled from other repos (upstream.json) for upstream changes and offers to fold the useful ones into our adapted versions."
disable-model-invocation: true
---

# Sync upstream

Our copies are adaptations to our workflow; the upstream is inspiration. A change upstream is an idea to weigh, never a patch to apply.

## Step 1: Check

```bash
python3 <skill-dir>/scripts/upstream.py check
```

It prints one entry per skill in `upstream.json`: `unchanged`, `changed`, `moved` or `removed`, with the upstream `head` and the files touched since the `checked` commit. For an `unchanged` skill, the script has already moved its `checked` commit to the head.

When every skill is `unchanged`, report that and go to Step 4.

## Step 2: Weigh each changed skill, one at a time

1. Read what changed upstream: `python3 <skill-dir>/scripts/upstream.py diff <name>` prints the commits on the skill's path and the patch of every file. When `truncated` is true, the file list was capped, so open the `compare_url` too.
2. Read our version of the same files under `skills/*/<name>/`.
3. Group the upstream patch into **ideas** (what each change does and why, from its commit message). For each idea say whether ours already has it, contradicts it by design, or would gain from it, and for the last kind sketch how it would read in our version.
4. Ask the user which ideas to take. Write each accepted one into our version in our own wording and shape.
5. Record the skill as reviewed, whatever the user took: `python3 <skill-dir>/scripts/upstream.py mark <name> --sha <head>`.

## Step 3: Moved and removed skills

- **moved**: show the user the new path (`moved_to`), then `upstream.py mark <name> --path <moved_to> --sha <head>`, and weigh its changes as in Step 2.
- **removed**: our skill stays. Ask the user whether to stop tracking it (`upstream.py mark <name> --drop`) or point it at another path.

## Step 4: Ship

Done when you have marked or dropped every entry the check reported as anything but `unchanged`. Commit `upstream.json` and the skills you changed following this repo's `CLAUDE.md`.
