# skills repo

Public repo of skills installed with `npx skills add moisesrj97/skills`. Load `writing-for-agents` before writing or editing a `SKILL.md`.

## Layout

- `skills/<category>/<name>/SKILL.md`. `npx skills` installs by name and ignores the category, so every name is unique across categories.
- Categories: `engineering/`, `productivity/`. Open a new one only when at least two skills belong in it.
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
2. Commit (subject line only) and push. Ask before pushing.
3. `npx skills update` installs it. Edits are invisible to the agent until then.
4. A **new** skill also needs a `"moisesrj97/skills <name> <name>"` line in `THIRD_PARTY_SKILLS` of `~/dot-files/claude/install.sh`, plus `npx skills add moisesrj97/skills -g -y -a claude-code -s <name>`.

Add the skill to the table in `README.md` in the same commit.

A change to a step of `megamoind` or `megamoind-spec` updates the diagrams in `docs/megamoind.md` in the same commit.
