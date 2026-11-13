---
name: pull-skill
description: "Copies a skill from another GitHub repo into this one, recording its source repo, path, commit and license in upstream.json so sync-upstream can follow it."
disable-model-invocation: true
---

# Pull skill

The pulled copy becomes ours to adapt; the upstream stays as inspiration that `sync-upstream` checks later.

## Step 1: Pin down the source

For each skill, get the GitHub `owner/repo`, the folder holding its `SKILL.md` inside that repo, and the branch to follow (the repo's default branch unless the user names one). An installed copy usually records its source: `~/.agents/.skill-lock.json` for `npx skills` installs, `.claude-plugin/plugin.json` for plugins.

When a repo holds two copies of a skill (a per-harness variant and a canonical one), take the one the user picked; ask when the choice is unclear.

Pick the local category: one that already exists under `skills/`, or a new one only when at least two skills land in it.

## Step 2: Pull

```bash
python3 <skill-dir>/scripts/pull.py <owner/repo> <path> [<path>…] --category <category> [--ref <branch>] [--as <new-name>]
```

Several paths from the same repo go in one call. `--as` renames a single skill and rewrites its frontmatter `name`.

The script copies each skill folder at the branch's current commit, copies the license nearest to the skill into `licenses/`, and records the entry in `upstream.json`. It refuses, writing nothing, when:

- a skill with that name already exists here: rerun with `--as`;
- it finds no license: tell the user the skill may not allow redistribution. Pass `--license <SPDX id>` only after the user confirms they read a license that allows it.

## Step 3: Wire it in

1. **After a rename**, update every reference to the old name, in the pulled skills and the rest of this repo (`rg -n '<old-name>'`), so they invoke the new one.
2. **Add a row per skill** to the table in `README.md`, with its upstream in the Source column.
3. **Remove the original install** so the skill doesn't load twice: a plugin, an `npx skills` install or a dotfiles installer that lists it. Show the user what you will remove and wait for their yes.

Done when every pulled skill has its `upstream.json` entry, its `README.md` row and no second copy installed.
