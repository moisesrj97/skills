---
name: review-comment
description: "Evaluates a GitHub PR review comment from its URL: makes the fix, commits, pushes and replies with the commit, or explains why no change is needed. Use when the user hands over a review comment link to address."
disable-model-invocation: true
---

# Review Comment Handler

You help developers handle GitHub PR review comments efficiently. Given a comment URL, you read what the reviewer said, look at the relevant code, and decide: is this change worth making? Then you act accordingly — either fix it and close the loop, or arm the developer with a clear explanation to push back.

## Step 1: Parse the URL and fetch the comment

PR comment URLs come in two forms:

- **Review (inline) comment**: `https://github.com/owner/repo/pull/123#discussion_r789012`
  → Fetch: `gh api repos/owner/repo/pulls/comments/789012`
- **General PR comment**: `https://github.com/owner/repo/pull/123#issuecomment-789012`
  → Fetch: `gh api repos/owner/repo/issues/comments/789012`

Extract `owner`, `repo`, the PR number (e.g. `123`), and the comment ID from the URL — the PR number is needed when posting a reply to an inline comment. Run the appropriate `gh api` call and collect:
- `body`: the reviewer's message
- `path`: file path (review comments only)
- `line` or `original_line`: the line number (review comments only)
- `diff_hunk`: surrounding diff context (review comments only)

Also fetch the PR's base branch for commit context:
```bash
gh pr view 123 --repo owner/repo --json baseRefName,headRefName
```

## Step 2: Read the relevant code

If it's an inline review comment (has `path`), read the file around the flagged line. Provide enough context — at least 20 lines before and after — to understand what the code does and why it's written that way.

If it's a general PR comment with no specific file, use `git diff` against the base branch to understand what changed in the PR.

## Step 3: Evaluate the suggestion

Now think carefully. Ask yourself:

- **Is the reviewer right?** Does the change improve correctness, safety, readability, or maintainability?
- **Is it already handled?** Sometimes the concern is addressed elsewhere, or the code does handle the case the reviewer is worried about.
- **Is it a matter of style vs. substance?** Style disagreements that don't affect quality are weaker reasons to change.
- **Does the change break anything?** Would it introduce regressions, violate project conventions, or contradict other recent changes?

Be honest. Don't default to "yes, fix it" just because a reviewer asked. Don't default to "no" just because the change is extra work. Read the code, understand the intent, and make a genuine judgment call.

## Step 4a: If the change IS needed — make it

1. Make the change. Be surgical: only touch what the comment is about.
2. Run the project's lint, type-check and the tests covering the change, with the commands from its `CLAUDE.md` / `CLAUDE.local.md` or `package.json`. Fix anything red before going on.
3. **Show the human the diff, the commit message and the reply you will post, and wait for one explicit approval** before committing. The commit message follows the project's convention, subject line only.
4. Commit and push to the PR's head branch. Under GitButler (`but status` works): `but commit -b <branch> -m "<message>" <ids>` with the ids from `but diff`, then `but push <branch>`: without a branch it pushes every branch with unpushed commits, other agents' included. Otherwise `git add`, `git commit`, `git push`. Take the full hash of the pushed commit: the reply cites a commit the reviewer can open.
5. Reply in **the reviewer's language**, opening with the byline from the `agent-byline` skill, then `Fixed in <full hash>` (`Arreglado en <full hash>` in Spanish) and no reasoning.
   Write the body to a file and reply to the original comment with `gh api`:
    - For review (inline) comments: `gh api repos/owner/repo/pulls/PR_NUMBER/comments/COMMENT_ID/replies -F body=@<file>` — note the PR number is required; `repos/owner/repo/pulls/comments/ID/replies` (without the PR number) returns 404.
    - For general PR comments (issuecomment): GitHub does not support threaded replies on issue comments, so post a new comment on the PR that quotes the original: `gh api repos/owner/repo/issues/PR_NUMBER/comments -F body=@<file>`, with the quoted excerpt between the byline and `Fixed in <full hash>`.

## Step 4b: If the change is NOT needed — brief the developer

Don't reply to the comment yourself — the developer needs to do it in their own voice and with appropriate context. Instead, give them a clear, honest explanation they can use:

- What the reviewer was concerned about
- Why the current code is actually correct / why the change isn't warranted
- A suggested reply they can post (in the same language as the reviewer's comment), short and respectful

Example structure:
```
The reviewer is concerned about [X]. The current code handles this because [Y].
You could reply with something like:

"[Suggested reply in reviewer's language]"
```

Keep the explanation direct. The developer will take it from here.

## Key behaviors

- **Language matching**: match the reviewer's language in any reply you post or draft.
- **Scope**: change only what the comment is about; when the change is clearly right, make it without hedging.
- **Push before replying**: the hash in the reply must already be on the remote.
- **Reply in the thread**: an inline comment gets a threaded reply through `gh api`, never a new comment from `gh pr comment`.