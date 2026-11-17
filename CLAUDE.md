# skills repo

Public repo of skills installed with `npx skills add moisesrj97/skills`. Load `writing-for-agents` before writing or editing a `SKILL.md`.

## Layout

- `skills/<category>/<name>/SKILL.md`, always two levels deep: `install.sh` links `skills/*/*/`. `npx skills` installs by name and ignores the category, so every name is unique across categories.
- Categories for our own skills: `engineering/`, `productivity/`. Open a new one only when at least two skills belong in it.
- Skills taken from other repos live in `upstream/`. They come in through `pull-skill`, which records their source and commit in `upstream.json` and their license in `licenses/`. They are ours to adapt: edit them like any other skill, without flagging the drift from upstream; `sync-upstream` weighs upstream changes later. Keep each entry's `licenses/` file: the MIT notice must ship with the copy.
- Scripts live in the skill's `scripts/` and are referenced as `<skill-dir>/scripts/…`: installs land in different paths per agent.

## Public by default

Everything committed here is public. Keep skills generic and read the specifics at runtime:

- **User data** (server URLs, account IDs): `~/.config/moisesrj97-skills/<skill>.json`, outside the skill folder, because `npx skills update` replaces that folder. The skill checks for it first and, when missing, asks the user and writes it.
- **Secrets**: a file the user writes themselves with `! printf '%s' '<secret>' > <file>`, so the value stays out of the conversation. The skill only reads it.
- **Project data** (ticket tracker, branch rules): the project's `CLAUDE.local.md` / `CLAUDE.md`, e.g. its `## Ticket tracker` section. The skill falls back to generic behaviour when it is absent.
- **Default branch**: resolve it (`git symbolic-ref --short refs/remotes/origin/HEAD`) rather than assuming `main` or `master`.

Before committing, grep the diff for URLs, IDs and absolute home paths.

## Shipping a change

1. `npx skills add . --list` lists every skill with its description: the discovery check.
2. Ship straight to `main`, without asking and without a PR. In the GitButler workspace every commit lands on a branch, so commit to a session branch (subject line only), push that branch's tip onto `main`, then integrate it:
   ```sh
   but commit -b <short-kebab-description> -m "<subject>" <ids>
   git push origin <short-kebab-description>:main
   but pull
   ```
   `but push` publishes the branch itself, not `main`.
3. Only when the user asks for a PR: a GitButler branch (`but branch new <short-kebab-description>`, no `PD-` prefix, never a `/`) and a draft PR with `but pr new <branch> -F <file> --draft`. Ask before marking it ready or merging.

`~/dot-files/claude/install.sh` symlinks every skill in this checkout into `~/.claude/skills`, so edits are live as soon as they are on disk, in every session, before any merge. Don't install these skills with `npx skills add`: a copy in its lock gets rewritten through the symlink by `npx skills update`. A **new** or renamed skill needs one run of `install.sh` to get its link.

Add the skill to the table in `README.md` in the same commit.

A change to the description or body of `megamoind` or `megamoind-batch`, or to the megamoind rule in `~/.claude/CLAUDE.md`, reruns `python3 evals/megamoind-entry/run.py`. One run per case is noisy; confirm a failure with `RUNS=3`.

A change to `diff-review`'s `reviewer.md` or `lenses/`, or to `craftsmanship`'s `tidy-first.md` or `simple-design.md`, reruns `python3 evals/review-recall/run.py` and compares each arm's range with the previous version's.
