# skills

My personal and engineering skills for coding agents.

## Skills

| Category | Skill | What it does | Source |
|---|---|---|---|
| engineering | `agent-byline` | Marks the PR comments, reviews and replies an agent posts on your behalf. | own |
| engineering | `codebase-design` | Shared vocabulary for designing deep modules: interfaces, seams, testability. | [mattpocock/skills](https://github.com/mattpocock/skills) |
| engineering | `comment-cleanup` | Prunes the comments a change added down to the non-obvious "why". | own |
| engineering | `craftsmanship` | Kent Beck's Tidy First (where each tidying goes by area of impact), the four rules of simple design, and Test Desiderata (the trade-offs between test properties). Tidies a diff through `diff-review`'s cleanup lens. | own |
| engineering | `debug-trace` | Temporary tagged debug points dumped to an isolated trace file, then removed. | own |
| engineering | `diagnosing-bugs` | Diagnosis loop for hard bugs and performance regressions. | [mattpocock/skills](https://github.com/mattpocock/skills) |
| engineering | `diff-review` | One review round in a separate reviewer agent of any model, through a lens (bugs, security or cleanup), continued across the rounds of a loop, with findings backed by quoted code and checked against a spec when given. | own |
| engineering | `domain-modeling` | Builds and sharpens a project's domain model: glossary and ADRs. | [mattpocock/skills](https://github.com/mattpocock/skills) |
| engineering | `gh-attach` | Attaches local images and videos to GitHub issues, PRs and comments with `gh --attach`. | own |
| engineering | `github-pr` | Draft PR with a Conventional Commits title and a "why"-first description. | own |
| engineering | `improve-codebase-architecture` | Scans a codebase for deepening opportunities as an HTML report, then grills through the one you pick. Manual only. | [mattpocock/skills](https://github.com/mattpocock/skills) |
| engineering | `megamoind` | Takes a ticket end to end: tidy first, TDD, reviews, real-app check, PR, CI loop. | own |
| engineering | `megamoind-batch` | Takes a batch of tickets (a spec, a list, a label) to PRs, one async megamoind agent per ticket, stacked by dependency. | own |
| engineering | `merge-risk` | Traffic-light rating of how risky a PR is to merge, by what users would suffer if it fails, with the reasons. | own |
| engineering | `pair-review` | Review → fix → re-review loop with a reviewer from another model family, through `diff-review`. | own |
| engineering | `pr-review` | Reviews a teammate's PR with Opus, Sol and a security pass through `diff-review`, checks it against its ticket, verifies each finding against the wider code, the stack and the author's notes, and rates it with `merge-risk`. | own |
| engineering | `prototype` | Throwaway prototype to answer a design question. | [mattpocock/skills](https://github.com/mattpocock/skills) |
| engineering | `release-decide` | Turns post-release signals into one verb per finding group with cited evidence, checks the metric sees the real work, and brings the owner only their calls. | own |
| engineering | `retro-digest` | Groups the open retro findings across projects, applies the approved ones and records each outcome. Manual only. | own |
| engineering | `retro-sweep` | Daily sweep of the sessions with no retro: a cheap model triages them for friction, a stronger one runs `retro-with-docs` on those that had some. Manual only. | own |
| engineering | `retro-with-docs` | Retro of an agent session: its friction, stoppers first, as open or skipped findings in `~/.skill-docs/retros/<project>/`. | own |
| engineering | `review-comment` | Evaluates a PR review comment, fixes it and replies with the commit. Manual only. | own |
| engineering | `setup-repo` | Configures a repo's issue tracker, triage labels and domain docs for the tracker skills. Manual only. | [mattpocock/skills](https://github.com/mattpocock/skills) (`setup-matt-pocock-skills`) |
| engineering | `tdd` | Test-driven development, red-green at the agreed seams. | [mattpocock/skills](https://github.com/mattpocock/skills) |
| engineering | `to-spec` | Turns the conversation into a spec on the issue tracker. Manual only. | [mattpocock/skills](https://github.com/mattpocock/skills) |
| engineering | `to-tickets` | Breaks a plan or spec into tracer-bullet tickets with blocking edges. Manual only. | [mattpocock/skills](https://github.com/mattpocock/skills) |
| engineering | `triage` | Moves issues and external PRs through triage roles and writes agent-ready briefs. Manual only. | [mattpocock/skills](https://github.com/mattpocock/skills) |
| engineering | `walkthrough` | Throwaway HTML reading guide through a set of changes. Manual only. | [noel-lopez/skills](https://github.com/noel-lopez/skills) |
| engineering | `wayfinder` | Plans work too big for one session as a map of decision tickets, resolved one at a time. Manual only. | [mattpocock/skills](https://github.com/mattpocock/skills) |
| productivity | `grill-me` | Relentless interview to sharpen a plan or design. Manual only. | [mattpocock/skills](https://github.com/mattpocock/skills) |
| productivity | `grilling` | Grills you about a plan, decision or idea. | [mattpocock/skills](https://github.com/mattpocock/skills) |
| productivity | `pull-skill` | Copies a skill from another repo and records its source in `upstream.json`. Manual only. | own |
| productivity | `skill-shaper` | Creates a skill or reshapes one that triggers on the wrong requests. | [overment/skills](https://github.com/overment/skills) |
| productivity | `sync-upstream` | Checks pulled skills for upstream changes and offers to fold the useful ones in. Manual only. | own |
| productivity | `teach` | Teaches you a new skill or concept, within the workspace. Manual only. | [mattpocock/skills](https://github.com/mattpocock/skills) |
| productivity | `unslop` | Cuts AI tells from any writing. Manual only. | [cursor/plugins](https://github.com/cursor/plugins) |
| productivity | `writing-for-agents` | Reference for writing skills, AGENTS.md and CLAUDE.md. | [mattpocock/skills](https://github.com/mattpocock/skills) |

Skills with a source other than `own` were pulled with `pull-skill` and adapted; `upstream.json` records the commit each one came from and its license is in `licenses/`. `sync-upstream` checks them for upstream changes.

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
