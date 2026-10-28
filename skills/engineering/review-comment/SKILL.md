---
name: review-comment
description: "Handle GitHub PR review comments: given a PR comment URL, reads the comment and evaluates whether the suggested change is needed. If it is, makes the change, commits it, and replies to the comment with the commit hash. If it isn't, explains why so the user can respond. Use this skill whenever the user pastes a GitHub PR comment link and wants help handling, addressing, or responding to a code review comment — even if they just say 'handle this', 'address this comment', 'fix this review comment', or 'do I need to change this?'"
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
2. Run `yarn lint:fix` if available (this project uses Biome), then verify with `yarn ci:lint`.
3. **Show the diff to the human and wait for explicit approval before proceeding.** Present the changes clearly and ask "Does this look good?" — do not commit until they confirm.
4. Draft a commit message and **show it to the human for approval before committing.** Wait for their confirmation or corrections.
5. Once both the diff and message are approved, commit and push:
   ```bash
   git add <file>
   git commit -m "<approved message>"
   git push
   ```
   Get the commit hash after pushing: `git rev-parse --short HEAD`
6. Reply to the comment in **the same language the reviewer used**:
   ```
   Fixed in <hash>
   ```
   Use the appropriate `gh api` command — **NEVER use `gh pr comment`**, always reply to the original comment:
    - For review (inline) comments: `gh api repos/owner/repo/pulls/PR_NUMBER/comments/COMMENT_ID/replies -f body="Fixed in <whole commit hash>"` — note the PR number is required; `repos/owner/repo/pulls/comments/ID/replies` (without the PR number) returns 404.
    - For general PR comments (issuecomment): GitHub does not support threaded replies on issue comments, so post a new comment on the PR that quotes the original: `gh api repos/owner/repo/issues/PR_NUMBER/comments -f body="> <quoted excerpt>\n\nFixed in <whole commit hash>"`

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

- **Language matching**: Always detect the language of the reviewer's comment and match it in any reply you post or draft.
- **Don't over-fix**: Only change what the comment is about. No cleanup, no refactoring beyond scope.
- **Don't under-fix**: If the change is clearly right, don't hedge — just make it.
- **Commit message quality**: Follow the project's commit style. In this project, prefix with `fix:`, `refactor:`, etc. No body, just subject line.
- **Verify before committing**: If there's a linter or type-checker, run it. Don't commit broken code.
- **Always push before replying**: Never reply with a commit hash that hasn't been pushed — run `git push` right after the commit.
- **Always reply to the original comment**: Never use `gh pr comment` to post a new comment. Always use `gh api` to reply within the original comment thread.