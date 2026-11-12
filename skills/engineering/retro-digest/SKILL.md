---
name: retro-digest
description: "Reviews the open findings in ~/.skill-docs/retros/ across all projects, groups recurring ones, applies those the user approves and records each outcome. Manual only."
disable-model-invocation: true
---

# Retro digest

Single retros are noisy. A stopper that shows up in several sessions, or in several projects, is the signal worth fixing. This pass turns the retros written by `retro-with-docs` into a short, ranked list of changes and records in the files what happened to each one.

## 1. Collect

Run `python3 <skill-dir>/scripts/retros.py collect`. It reads every `~/.skill-docs/retros/<project>/*.md` and prints every `open` finding, plus the `rejected` ones so recurrences are visible, each with its ref (`<project>/<file>#R<n>`), date, fields and severity weight. If none is open, say so and stop.

## 2. Cluster and rank

A **cluster** is a set of findings with the same root cause and the same fix, even if worded differently, from any project. Its **canonical** member, the earliest finding by date, carries the cluster's status. For each cluster:

- **Scope** is **global** when the fix lands in shared setup (user-level steering files, skills, hooks, tooling) or when the same friction shows up in more than one project, which moves even a project-level fix there. It is **project** when the fix lands in one repo.
- **Score** = occurrences × the highest `weight` among its members.
- **Already in place**: read its target. If the change is already there, mark the cluster resolved in step 5 without asking.
- **Recurring after rejection**: a cluster with a `rejected` member is not proposed again. List it apart with its count and the rejection reason, for the user to reopen it or fold its open members into the rejected one.

## 3. Decide

The user decides each cluster on a standalone HTML page; everything else waits for step 4.

Write the digest to `<scratchpad>/retro-digest.json`, shaped like [`scripts/example-digest.json`](scripts/example-digest.json):

- `clusters`, highest score first, with ids `C1…`: members (the canonical one marked `*`), scope, projects, score, target and proposal, plus your `observation` (why apply or reject, what it overlaps, what a past attempt showed) and your `recommend`.
- `recurring`, with ids `R-A…`: the open members, the rejected member with its reason, your observation, and `recommend` (`fold` unless you argue otherwise).
- `legend` for the id prefixes, a `title` with today's date, and `reviewFile`: `retro-review-<date>.json`.

Build the page with `node <skill-dir>/scripts/build-review-page.mjs <scratchpad>/retro-digest.json <scratchpad>/retro-digest.html` and open it in the browser (`open` on macOS). Every row starts on your `recommend`; the user changes what they disagree with and saves `reviewFile` to the browser's downloads folder, or copies it for the chat. Send one self-contained message, since the user may read it hours later in a scheduled thread: the page's path, the cluster count, the top three by score, the clusters already marked resolved, and that answering in chat works too. Wait.

Done when the user says they're done or answers in chat. Read `decisions` from the newest `~/Downloads/retro-review-<date>*.json` (the browser appends ` (1)` to a repeat save); if there is none, ask where it was saved.

## 4. Plan the changes

In one message, for the decided clusters:

- **Applied and reopened**: grouped by the repo or file that owns each target, the commits or PRs each group becomes, their order and dependencies, and which need a ticket. Ask for the ticket ids or "create them", and for any adjustment to a proposal.
- **Rejected**: a reason for each, offering your observation as the default.

Before writing a group's ticket or brief, check every concrete claim its proposals make (paths, response shapes, flag names, ports) with a grep or read of the target repo and write it with `file:line`; mark the rest "unverified: …".

Done when every group has its tickets and every rejection its reason.

## 5. Apply and record

Apply each approved cluster as its own change, in the repo that owns its target and following that repo's own workflow (branch, commit and PR rules). Implement a `mechanical` finding as a deterministic check (lint rule, hook, CI job) instead of prose.

Then set the status of every member of every cluster you touched, in one call with a JSON file of `{"<ref>": "<status>"}`: `python3 <skill-dir>/scripts/retros.py set --from <file>`. Each status is one of these, and the script refuses any other shape or a ref it can't find, naming each:

- `applied (<commit, PR or file>)`, including the already-in-place ones.
- `rejected (<reason>)`.
- `duplicate of <project>/<file>#R<n>` for every non-canonical member, pointing at the canonical one.

Done when every finding you collected has its new status or was left `open` by the user. Finish with what was applied, where, and what is still open.
