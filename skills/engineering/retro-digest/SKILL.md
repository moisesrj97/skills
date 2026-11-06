---
name: retro-digest
description: "Reviews the open findings in ~/.skill-docs/retros/ across all projects, groups recurring ones, applies those the user approves and records each outcome. Use only when the user or a scheduled task explicitly asks for it."
---

# Retro digest

Single retros are noisy. A stopper that shows up in several sessions, or in several projects, is the signal worth fixing. This pass turns the retros written by `retro-with-docs` into a short, ranked list of changes and records in the files what happened to each one.

## 1. Collect

Read every `~/.skill-docs/retros/<project>/*.md`. Each `## R<n>` is a finding, referenced as `<project>/<file>#R<n>`, and its `- status:` line is its state. Take every `open` finding, plus the `rejected` ones so recurrences are visible. If none is open, say so and stop.

## 2. Cluster and rank

A **cluster** is a set of findings with the same root cause and the same fix, even if worded differently, from any project. Its **canonical** member, the earliest finding by date, carries the cluster's status. For each cluster:

- **Scope** is **global** when the fix lands in shared setup (user-level steering files, skills, hooks, tooling) or when the same friction shows up in more than one project, which moves even a project-level fix there. It is **project** when the fix lands in one repo.
- **Score** = occurrences × the highest severity (blocker 4, high 3, medium 2, low 1).
- **Already in place**: read its target. If the change is already there, mark the cluster resolved in step 4 without asking.
- **Recurring after rejection**: a cluster with a `rejected` member is not proposed again. List it apart with its count and the rejection reason, for the user to reopen it or fold its open members into the rejected one.

## 3. Ask

Show one table, highest score first: `cluster (member ids) | scope | projects | score | target | proposal`, then the recurring-after-rejection ones. Ask what to do with each in one self-contained message, since the user may read it hours later in a scheduled thread: apply, reject (with a reason) or leave open, and for the recurring ones, reopen or fold (default fold). Wait for the answer.

## 4. Apply and record

Apply each approved cluster as its own change, in the repo that owns its target and following that repo's own workflow (branch, commit and PR rules). Implement a `mechanical` finding as a deterministic check (lint rule, hook, CI job) instead of prose.

Then rewrite the `- status:` line of every member of every cluster you touched:

- `applied (<commit, PR or file>)`, including the already-in-place ones.
- `rejected (<reason>)`.
- `duplicate of <project>/<file>#R<n>` for every non-canonical member, pointing at the canonical one.

Done when every finding you collected has its new status or was left `open` by the user. Finish with what was applied, where, and what is still open.
