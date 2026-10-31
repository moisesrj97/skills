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
| engineering | `debug-trace` | Temporary tagged debug points dumped to an isolated trace file, then removed. |
| engineering | `diff-review` | One review round in a fresh reviewer agent of any model, with findings backed by quoted code. |
| engineering | `gh-attach` | Attaches local images and videos to GitHub issues, PRs and comments with `gh --attach`. |
| engineering | `github-pr` | Draft PR with a Conventional Commits title and a "why"-first description. |
| engineering | `megamoind` | Takes a ticket end to end: TDD, reviews, real-app check, PR, CI loop. |
| engineering | `megamoind-batch` | Takes a batch of tickets (a spec, a list, a label) to PRs, one async megamoind agent per ticket, stacked by dependency. |
| engineering | `pair-review` | Review → fix → re-review loop with a reviewer from another model family, through `diff-review`. |
| engineering | `review-comment` | Evaluates a PR review comment, fixes it and replies with the commit. Manual only. |
| productivity | `gomander` | Starts and stops [Gomander](https://github.com/lazylabz/gomander-app) commands through its local API. |
| productivity | `karakeep-inbox-triage` | Tags and files the bookmarks in a Karakeep "Inbox" list, after approval. |

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
