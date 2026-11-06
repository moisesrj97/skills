---
name: merge-risk
description: Rates how risky a PR is to merge as a traffic light, green, yellow or red, by what users would suffer if it fails, with the reasons behind the color. Use when asked how risky a PR or a merge is. Not for finding bugs; use diff-review.
argument-hint: "[PR number, URL or ref range]"
---

# Merge risk

The color measures **exposure**, which is what a user sees if the change fails in production. The user is whoever runs what the PR ships: end users for a product, the callers of a library or service, the people running a tool. A 2,000-line feature behind a flag that is off is green. A one-line change to a shared query can be red. The color informs the merge decision, which stays with the user.

## 1. Gather

- The scope is the PR or ref range (`<base>...<branch>`) given, else the current branch's PR (`gh pr view --json number`), else the diff against the default branch (`git symbolic-ref --short refs/remotes/origin/HEAD`).
- Read the diff, the PR description and `gh pr checks`.
- Read the `## Merge risk` section of the project's `CLAUDE.local.md` or `CLAUDE.md` if it has one. Its main flows and critical areas override your own guess. Without it, infer the main flows from the product and mark them as inferred in the report.

## 2. Split gated from exposed

Every change is **gated**, running only when a flag is on, or **exposed**, running in production with the default config. A flag gates only the code behind its check, so check these yourself whatever the PR description says:

- The flag's default in production. An unknown default makes the change exposed.
- The code that runs with the flag off, such as migrations, shared helpers and queries, refactors of existing paths, config, dependency bumps, API or event contracts, and the flag check itself.

Gated changes are green. Done when every change in the diff sits on one side.

## 3. Grade each exposed change

Answer two questions from the code. If it fails, what does the user see? How do you undo it?

- 🟢 **Low.** The user doesn't notice, or their flow carries on. The containment has to be in the code, for example a `catch` with a fallback, an error boundary, a retried async job or a secondary widget that doesn't block the page. A failure that propagates is not contained.
- 🟡 **Medium.** A secondary flow breaks or a main one degrades, and a revert fixes it.
- 🔴 **High.** A main flow breaks, data is lost or corrupted, or the fix takes more than a revert because of a migration, data already written, or a contract that other services or clients consume.

Tests on the exposed path and a green CI make a failure less likely. List them as reasons, and grade by what a failure would break. When two levels fit, take the higher one and name what would settle it.

## 4. Report

The PR takes the color of its worst exposed change. Reply with this shape and nothing else:

```markdown
**Merge risk: 🟡 Medium**

- 🟡 <what the user sees if it fails, and how to undo it> (`path:line`)
- 🟢 <reason> (`path:line`)
- Gated: <the changes behind a flag, in one line>
- Unknown: <what could raise the color, and what would settle it>
```

Give one reason for each exposed change that set the color or came close, most severe first, each citing the code it rests on. Keep each reason to one or two sentences, so the color can be checked at a glance. Drop the `Gated` or `Unknown` line when it would be empty.
