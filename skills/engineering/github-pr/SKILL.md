---
name: github-pr
description: Writes a GitHub PR's Conventional Commits title and why-first description, then opens it as a draft. Use when the user asks to open, create or describe the PR for the current branch.
---

# GitHub PR

## 1. Gather

- **Base**: the default branch (`git symbolic-ref --short refs/remotes/origin/HEAD`, minus `origin/`), or the branch below this one in a stack. That name is `<base>` for `--base`. Compare the default branch through `origin/<base>` after `git fetch origin`: a local copy can be stale or missing.
- **Branch**: the PR's branch. Under GitButler `HEAD` merges every applied branch, so take the branch name from `but status` and use it, not `HEAD`. Read commits and diff from `git merge-base <base ref> <branch>` to `<branch>`, skipping merge commits; `<base ref>` is `origin/<base>`, or the lower branch itself in a stack.
- **Ticket link**: only from a `## Ticket tracker` section in the repo's `CLAUDE.local.md` or `CLAUDE.md`, which says how a branch carries a ticket ID and how to build its URL. No section, or the branch doesn't match it, means no link: never guess a tracker.
- **Why**: issue references in the commits (`Closes #123`) and what the conversation says about why the change was made.

No commits ahead of the base: stop and ask which base or commits the PR covers.

## 2. Write

Title: `type(scope): summary`. The type is the dominant commit type (feat > fix > perf > refactor > others), the scope the most specific unit most of the change sits in (the package, app or module), not a container folder like `packages/`.

Description, in English, with `##` headings and below:

```markdown
## Problem

This PR resolves <ticket URL>

<the need that motivated the change>

## Solution

<what a reviewer needs and the diff doesn't show: decisions, trade-offs, constraints, grouped by area in short bullets>
```

- The ticket line appears only with a ticket link.
- Add `## Next steps` for follow-ups or stacked PRs, and `## Related` for issue or PR references other than the ticket.
- The reviewer has the diff, so the description carries the *why*: no restated diff, file lists or code blocks.
- A testing section only when the user asks for one. Anything left unverified is one line in Solution.

## 3. Preview

Show the title and description and wait for explicit approval. An edit changes the text only: apply it and show it again, without re-reading git.

## 4. Open

Pass the description through a file; a shell-quoted body mangles backticks and newlines.

- GitButler repo (`but status` works): `but pr new <branch> -F <file> --draft`, with the title on the file's first line and the description below it. It pushes the branch and its ancestors and sets the right base in a stack. Then `gh pr edit <number> --add-assignee @me`.
- Otherwise: push the branch, then `gh pr create --draft --assignee @me --base <base> --title "<title>" --body-file <file>`, with the description alone in the file.

Drop `--draft` only when the user says the PR is ready for review. Print the PR URL.
