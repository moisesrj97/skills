---
name: retro-digest
description: "Reviews the open findings in ~/.skill-docs/retros/ across all projects, groups recurring ones, applies those the user approves and records each outcome. Manual only."
disable-model-invocation: true
---

# Retro digest

Single retros are noisy. Friction that shows up in several sessions, or in several projects, is the signal worth fixing, even when each retro skipped it as a one-off. This pass turns the retros written by `retro-with-docs` into a short, ranked list of changes and records in the files what happened to each finding.

## 1. Collect

```bash
python3 <skill-dir>/scripts/retros.py batches --out <scratchpad>/digest
```

It reads every `~/.skill-docs/retros/<project>/*.md` and splits into batch files every `open` finding, plus the `rejected` ones so recurrences show and the `skipped` ones so recurring noise shows. Each finding carries its ref (`<project>/<file>#R<n>`), date and fields. The script leaves out skipped findings older than four weeks, since a one-off that has not recurred in that long is not a pattern. It sorts batches by where each change would land, so related findings tend to share one. If it writes no batch, say so and stop.

## 2. Cluster each batch

A **cluster** is a set of findings with the same root cause and the same fix, even if worded differently, from any project. A `matches:` ref is the writer's claim that two findings are one; confirm it against both.

Launch one subagent per batch with the Agent tool, `model: "sonnet"`, at most 5 at a time. Brief each with the cluster definition above and its batch file, and ask for every finding placed in exactly one cluster, singletons included, returned as JSON: `[{"owner": "<the skill, script, app or file the change lands in>", "cause": "<root cause, one line>", "proposal": "<the change, one line>", "members": ["<ref>", ...]}]`.

Done when every batch has its clusters back.

## 3. Merge and rank

Batches split some clusters, so merge the returned ones that share an owner and a cause into one. The result can differ slightly from last week's; that is fine.

Each merged cluster's **canonical** member, the earliest finding by date, carries the cluster's status. Skipped members count as occurrences. A cluster made only of skipped members goes forward once it has 3 members; a smaller one stays skipped and out of the digest. For each cluster:

- **Scope** is **global** when the fix lands in shared setup (user-level steering files, skills, hooks, tooling) or when the same friction shows up in more than one project, which moves even a project-level fix there. It is **project** when the fix lands in one repo.
- **Score** is the occurrences times the highest `weight` among its members (blocker 4, high 3, medium 2, low 1; 1 for a skipped member without a severity).
- **Already in place**: read its target. If the change is already there, mark the cluster resolved in step 6 without asking.
- **Recurring after rejection**: a cluster with a `rejected` member is not proposed again. List it apart with its count and the rejection reason, for the user to reopen it or fold its open members into the rejected one.

## 4. Decide

The user decides each cluster on a standalone HTML page; everything else waits for step 5.

Write the digest to `<scratchpad>/retro-digest.json`, shaped like [`scripts/example-digest.json`](scripts/example-digest.json):

- `clusters`, highest score first, with ids `C1…`: a title naming the change and the friction it removes, members (the canonical one marked `*`), scope, projects, score, target (the owner) and proposal, plus your `observation` (why apply or reject, what it overlaps, what a past attempt showed) and your `recommend`. A cluster of skipped members needs the proposal its members never had: write it from their evidence. A proposal fixes the owner, correcting the step, rule or check that misled; recommend reject for one that adds a second way beside it (an exception paragraph, an alias, a fallback), and name the owner text to fix instead.
- `recurring`, with ids `R-A…`: the open members, the rejected member with its reason, your observation, and `recommend` (`fold` unless you argue otherwise).
- `legend` for the id prefixes, a `title` with today's date, and `reviewFile`: `retro-review-<date>.json`.

Build the page with `node <skill-dir>/scripts/build-review-page.mjs <scratchpad>/retro-digest.json <scratchpad>/retro-digest.html` and open it in the browser (`open` on macOS). Every row starts on your `recommend`; the user changes what they disagree with and saves `reviewFile` to the browser's downloads folder, or copies it for the chat. Send one self-contained message, since the user may read it hours later in a scheduled thread: the page's path, the cluster count, the top three by score, the clusters already marked resolved, and that answering in chat works too. Wait.

Done when the user says they're done or answers in chat. Read `decisions` from the newest `~/Downloads/retro-review-<date>*.json` (the browser appends ` (1)` to a repeat save); if there is none, ask where it was saved.

## 5. Plan the changes

In one message, for the decided clusters:

- **Applied and reopened.** Group them by the repo or file that owns each target, and give the commits or PRs each group becomes, their order and dependencies, and which need a ticket. Ask for the ticket ids or "create them", and for any adjustment to a proposal.
- **Rejected.** Give a reason for each, with your observation as the default.

Before writing a group's ticket or brief, check every concrete claim its proposals make (paths, response shapes, flag names, ports) with a grep or read of the target repo and write it with `file:line`; mark the rest "unverified: …".

Done when every group has its tickets and every rejection its reason.

## 6. Apply and record

Apply each approved cluster as its own change, in the repo that owns its target and following that repo's own workflow (branch, commit and PR rules). Implement a `mechanical` finding as a deterministic check (lint rule, hook, CI job) instead of prose.

Then set the status of every member of every cluster you touched, in one call with a JSON file of `{"<ref>": "<status>"}`: `python3 <skill-dir>/scripts/retros.py set --from <file>`. Each status is one of these, and the script refuses any other shape or a ref it can't find, naming each:

- `applied (<commit, PR or file>)`, including the already-in-place ones.
- `rejected (<reason>)`.
- `duplicate of <project>/<file>#R<n>` for every non-canonical member, pointing at the canonical one.

Done when every finding in a cluster you put on the page has its new status or was left `open` by the user; skipped findings left out of the digest keep theirs. Finish with what was applied, where, and what is still open.

## One-time check

This section is temporary. In the final message, answer: did step 3 merge clusters that the batches had split? Name one merged cluster and how many batches its members came from, and say whether the zsh `$H:path` / `$B:path` modifier friction, seen in several reviewer sessions, came out as one cluster. Then delete this section from this file and commit the deletion in the repo that holds the skill, following that repo's workflow.
