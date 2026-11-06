---
name: pr-review
description: Reviews a teammate's PR with two reviewers from different model families, verifies each finding against the wider code, the stack and the author's notes, and rates merge risk. Use when asked to review someone else's PR. Not for your own change; use pair-review.
argument-hint: "<PR number or URL>"
---

# PR review

You are the **coordinator**. Two reviewers produce raw findings, and you triage them into the list the user reads. You only read. The checkout may be a workspace other agents share, so fetch the PR (`git fetch origin pull/<n>/head`) and read it with `git show <sha>:<file>` instead of checking it out.

## 1. Context

Read the PR description, the issue or ticket it links (with the tracker the project's `## Ticket tracker` section names) and the stack: the PRs above it (`gh pr list --base <head branch>`, upwards) and, when its base isn't the default branch, the one below.

## 2. Review

Call the Skill tool with `diff-review` twice, launching both before waiting for either: reviewers `claude-opus-5-5:medium` and `gpt-6.1-sol:medium`, scope `<base>...<head sha>`, each with its own round file. Pass the trade-offs the author or ticket accepted as the already-decided list. When the GPT reviewer can't run (no Codex target in T3 Code and no `codex` CLI, or its round fails twice), go on with the Opus round alone and say so in the report.

## 3. Verify

Merge duplicates, noting which reviewer found each. Then trace every finding **wider** than the reviewer did. A reviewer reads the diff and its neighbours, and its scenario often breaks, or gets worse, against code it never opened. Follow it through callers, upstream validation, flags, the consumers of a changed contract, other services, and the tests. Start with the PLAUSIBLE findings, from what their `Confirm by` names; one the trace can't confirm is Discarded. Put each finding in one bucket:

- **Confirmed**: the scenario reaches the wrong result through the real code. Keep or correct its severity.
- **Fixed above**: a PR higher in the stack fixes it. Name the PR.
- **Accepted**: the author or ticket names it as a known trade-off or a planned follow-up. An open question the review answers goes to Confirmed or Discarded instead.
- **Discarded**: the scenario can't happen. Name the line that stops it.

Done when every finding has a bucket and the `path:line` that put it there.

## 4. Rate

Call the Skill tool with `merge-risk` for the PR. Each confirmed finding on an exposed path is a failure scenario it grades.

## 5. Report

Confirmed findings most severe first, each with its severity, `path:line`, scenario, what you traced beyond the diff and who found it (Opus, Sol, you). Then one line per finding in the other buckets with its reason. Then the merge-risk report.
