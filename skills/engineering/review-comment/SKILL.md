---
name: review-comment
description: "Takes a GitHub PR review comment URL and either makes the fix, pushes it and replies with the commit, or explains why no change is needed. Use when the user hands over a review comment link to address."
disable-model-invocation: true
---

# Review comment

## Step 1: Parse the URL and fetch the comment

PR comment URLs come in two forms:

- **Inline review comment** `https://github.com/owner/repo/pull/123#discussion_r789012`, fetched with `gh api repos/owner/repo/pulls/comments/789012`.
- **General PR comment** `https://github.com/owner/repo/pull/123#issuecomment-789012`, fetched with `gh api repos/owner/repo/issues/comments/789012`.

Take `owner`, `repo`, the PR number (`123`) and the comment ID from the URL. The reply to an inline comment needs the PR number. From the `gh api` call, collect:
- `body`: the reviewer's message
- `path`: file path (review comments only)
- `line` or `original_line`: the line number (review comments only)
- `diff_hunk`: surrounding diff context (review comments only)

Fetch the PR's base and head branches:
```bash
gh pr view 123 --repo owner/repo --json baseRefName,headRefName
```

## Step 2: Read the relevant code

For an inline comment (it has `path`), read the file around the flagged line, at least 20 lines on each side, enough to see what the code does and why it is written that way.

For a general comment with no file, read `git diff` against the base branch to see what the PR changed.

## Step 3: Evaluate the suggestion

- **Is the reviewer right?** Does the change improve correctness, safety, readability or maintainability?
- **Is it already handled?** The concern may be addressed elsewhere, or the code may already handle the case the reviewer worries about.
- **Style or substance?** A style disagreement that doesn't affect quality is a weaker reason to change.
- **Does the change break anything?** Would it introduce regressions, violate project conventions or contradict other recent changes?

Judge from the code and its intent. A reviewer asking is no reason to say yes, and extra work is no reason to say no.

## Step 4a: The change is needed, so make it

When the change is clearly right, make it without hedging.

1. Make the change on the PR's head branch. Under GitButler the branch must be applied (`but status`); otherwise check it out first (`gh pr checkout <number>`). Be surgical and touch only what the comment is about.
2. Run the project's lint, type-check and the tests covering the change, with the commands from its `CLAUDE.md` / `CLAUDE.local.md` or `package.json`. Fix anything red before going on.
3. **Show the human the diff, the commit message and the reply you will post, and wait for one explicit approval** before committing. The commit message follows the project's convention, subject line only.
4. Commit and push to the PR's head branch, before replying, so the hash in the reply is already on the remote. Under GitButler (`but status` works), run `but commit -b <branch> -m "<message>" <ids>` with the ids from `but diff`, then `but push <branch>`. A bare `but push` pushes every branch with unpushed commits, other agents' included. Otherwise `git add`, `git commit`, `git push`. Take the full hash of the pushed commit with `git rev-parse <branch>`; under GitButler `HEAD` is the workspace commit, which the reviewer can't open.
5. Reply in **the reviewer's language**, opening with the byline from the `agent-byline` skill, then `Fixed in <full hash>` (`Arreglado en <full hash>` in Spanish) and no reasoning.
   Write the body to a file and reply to the original comment with `gh api`:
    - For an inline review comment, reply in its thread with `gh api repos/owner/repo/pulls/PR_NUMBER/comments/COMMENT_ID/replies -F body=@<file>`, never with a new comment from `gh pr comment`. The path needs the PR number; `repos/owner/repo/pulls/comments/ID/replies` returns 404.
    - For a general PR comment (issuecomment), GitHub has no threaded replies, so post a new comment on the PR that quotes the original, `gh api repos/owner/repo/issues/PR_NUMBER/comments -F body=@<file>`, with the quoted excerpt between the byline and `Fixed in <full hash>`.

Done when the reply with the pushed hash is posted.

## Step 4b: The change is not needed, so brief the developer

Post nothing. The developer replies in their own voice and with context you lack. Give them a direct brief:

- What the reviewer was concerned about
- Why the current code is correct, or why the change isn't warranted
- A short, respectful reply they can post, in the reviewer's language

Example structure:
```
The reviewer is concerned about [X]. The current code handles this because [Y].
You could reply with something like:

"[Suggested reply in reviewer's language]"
```
