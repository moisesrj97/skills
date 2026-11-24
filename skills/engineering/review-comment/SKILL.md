---
name: review-comment
description: "Takes a GitHub PR review comment URL and either fixes it, pushes and replies with the commit, or briefs you on why no change is needed."
disable-model-invocation: true
---

# Review comment

## 1. Fetch

`python3 <skill-dir>/scripts/comment.py fetch <url>` takes an inline review comment (`…#discussion_r<id>`) or a general PR comment (`…#issuecomment-<id>`) and prints the reviewer's body, the PR's base and head, and for an inline comment the code around the flagged line at the PR's head, read from GitHub since the checkout may hold another branch. For a general comment, read what the PR changed with `gh pr diff <pr> --repo <owner>/<repo>`.

## 2. Judge on the merits

Decide from the code and its intent whether the change is needed. A reviewer asking is no reason to say yes, and extra work is no reason to say no. An `outdated` line, or a case the code handles elsewhere, may already answer the comment.

## 3a. Needed: fix it

1. Make the change on the PR's head branch, touching only what the comment is about. Under GitButler the branch must be applied (`but status`); otherwise `gh pr checkout <number>`.
2. Run the project's lint, type-check and the tests covering the change, until green.
3. Show the user the diff, the commit message (the project's convention, subject line only) and the reply, and wait for one explicit approval, which covers the commit, the push and the reply.
4. Commit and push before replying, so the hash in the reply exists on the remote. Under GitButler: `but commit -b <branch> -m "<message>" <ids>`, then `but push <branch>`, since a bare `but push` pushes other agents' branches too. Take the hash with `git rev-parse <branch>`; under GitButler `HEAD` is the workspace commit, which the reviewer can't open.
5. Write the reply to a file in the reviewer's language: the `post-to-github` byline, then `Fixed in <full hash>` (`Arreglado en <full hash>`) and no reasoning. For a general comment, put a quoted excerpt of the original between the two. Post it with `python3 <skill-dir>/scripts/comment.py reply <url> <body file>`.

Done when the reply with the pushed hash is posted.

## 3b. Not needed: brief the user

Post nothing: the user replies in their own voice, with context you lack. Tell them what the reviewer is concerned about, why the current code is right or the change isn't worth it, and a short reply they can post, in the reviewer's language.
