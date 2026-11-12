---
name: review-comment
description: "Takes a GitHub PR review comment URL and either makes the fix, pushes it and replies with the commit, or explains why no change is needed. Use when the user hands over a review comment link to address."
disable-model-invocation: true
---

# Review comment

## Step 1: Fetch the comment and its code

```bash
python3 <skill-dir>/scripts/comment.py fetch <url>
```

It takes an inline review comment (`…/pull/123#discussion_r789012`) or a general PR comment (`…/pull/123#issuecomment-789012`) and prints the reviewer's `body`, the PR's base, head and `head_sha`. An inline comment adds its `path`, `line` (flagged `outdated` when the code moved on), `diff_hunk`, and `context`: the file at the PR's head, 20 lines each side of the flagged one, read from GitHub because the local checkout may hold another branch.

## Step 2: Read the relevant code

For an inline comment, read the `context`, and further at the head when it isn't enough to see what the code does and why it is written that way. For a general comment with no file, read what the PR changed with `gh pr diff <pr> --repo <owner>/<repo>`.

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
   Write the body to a file and post it with `python3 <skill-dir>/scripts/comment.py reply <url> <body file>`. It refuses a body without the byline, replies in the thread of an inline comment (to its top comment, the only one GitHub takes replies on), and posts a new PR comment for a general one, since those have no threads. For a general comment, put a quoted excerpt of the original between the byline and `Fixed in <full hash>`.

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
