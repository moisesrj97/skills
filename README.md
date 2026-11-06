# skills

My personal and engineering skills for coding agents, installable with [`npx skills`](https://github.com/vercel-labs/skills).

## Install

```bash
npx skills add moisesrj97/skills --list            # see what's here
npx skills add moisesrj97/skills -g -s debug-trace # install one globally
npx skills update                                  # pull new versions
```

## Skills

| Category | Skill | What it does |
|---|---|---|
| engineering | `agent-byline` | Marks the PR comments, reviews and replies an agent posts on your behalf. |
| engineering | `comment-cleanup` | Prunes the comments a change added down to the non-obvious "why". |
| engineering | `craftsmanship` | Kent Beck's Tidy First (where each tidying goes by area of impact) and Test Desiderata (the trade-offs between test properties). |
| engineering | `debug-trace` | Temporary tagged debug points dumped to an isolated trace file, then removed. |
| engineering | `diff-review` | One review round in a separate reviewer agent of any model, continued across the rounds of a loop, with findings backed by quoted code. |
| engineering | `gh-attach` | Attaches local images and videos to GitHub issues, PRs and comments with `gh --attach`. |
| engineering | `github-pr` | Draft PR with a Conventional Commits title and a "why"-first description. |
| engineering | `megamoind` | Takes a ticket end to end: tidy first, TDD, reviews, real-app check, PR, CI loop. |
| engineering | `megamoind-batch` | Takes a batch of tickets (a spec, a list, a label) to PRs, one async megamoind agent per ticket, stacked by dependency. |
| engineering | `merge-risk` | Traffic-light rating of how risky a PR is to merge, by what users would suffer if it fails, with the reasons. |
| engineering | `pr-review` | Reviews a teammate's PR with Opus and Sol through `diff-review`, verifies each finding against the wider code, the stack and the author's notes, and rates it with `merge-risk`. |
| engineering | `pair-review` | Review → fix → re-review loop with a reviewer from another model family, through `diff-review`. |
| engineering | `retro-digest` | Groups the open retro findings across projects, applies the approved ones and records each outcome. Manual only. |
| engineering | `retro-with-docs` | Retro of an agent session: stoppers and environment fixes, written to `~/.skill-docs/retros/<project>/`. |
| engineering | `review-comment` | Evaluates a PR review comment, fixes it and replies with the commit. Manual only. |

The `megamoind` flows are diagrammed in [`docs/megamoind.md`](docs/megamoind.md).

## Configuration

Nothing personal or company-specific is hardcoded. Skills that need it read it from outside the repo:

- **Per user** (URLs, keys): `~/.config/moisesrj97-skills/<skill>.json`. The skill asks on first run and writes it. Secrets are written by you, never pasted into the chat.
- **Per project** (ticket tracker, branch format): a `## Ticket tracker` section in the project's `CLAUDE.local.md` or `CLAUDE.md`. Without it, `github-pr` and the `megamoind` skills work with no tracker. Example:

  ```markdown
  ## Ticket tracker

  - ClickUp. Ticket IDs look like `ABC-<number>`.
  - Branch: `ABC-<number>-<short-kebab-description>`, never a `/`.
  - Ticket URL: `https://app.clickup.com/t/<workspace>/ABC-<number>`.
  ```
