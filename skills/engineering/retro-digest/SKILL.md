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

It reads every `~/.skill-docs/retros/<project>/*.md` and splits into batch files every `open` finding, plus the `rejected` ones so recurrences show and the `skipped` ones so recurring noise shows. Each finding carries its ref (`<project>/<file>#R<n>`), date and fields. The script leaves out skipped findings older than four weeks, since a one-off that has not recurred in that long is not a pattern. It sorts batches by where each change would land, so related findings tend to share one. Skipped findings name no target, so they land in batches of their own, apart from the open findings they may repeat; step 3 joins them. If it writes no batch, say so and stop.

## 2. Cluster each batch

A **cluster** is a set of findings with the same root cause and the same fix, even if worded differently, from any project. A `matches:` ref is the writer's claim that two findings are one; confirm it against both.

Launch one subagent per batch with the Agent tool, `model: "sonnet"`, at most 5 at a time. Brief each with the cluster definition above and its batch file, and ask for every finding placed in exactly one cluster, singletons included, written as valid JSON only to `clusters-<n>.json` beside its `batch-<n>.json`, replying with just that path. The file holds `[{"owner": "<the skill, script, app or file the change lands in>", "cause": "<root cause, one line>", "proposal": "<the change, one line>", "members": ["<ref>", ...]}]`.

Done when every batch has its `clusters-<n>.json`.

## 3. Merge and rank

Batches split some clusters, skipped findings above all, so merge across batches the clusters that share an owner and a cause:

```bash
python3 <skill-dir>/scripts/retros.py merge <scratchpad>/digest
```

It ids each cluster `<batch>.<n>` and writes `index.txt`, one line per cluster sorted by owner. Read it whole and write `<scratchpad>/merges.json`, one group per set of clusters with the same owner and cause, a skipped-only one included when it repeats an open one: `[{"ids": ["3.7", "12.2"], "owner": "…", "cause": "…", "proposal": "…"}]` (text left out comes from the first id). Rerun with `--merges <scratchpad>/merges.json`. It refuses, naming each, a finding missing or placed twice and a cluster without text; fix the file it names (resume that batch's subagent for its own clusters) and rerun until it writes `merged.json`.

Each cluster in `merged.json` comes with its **canonical** member, the earliest finding by date, which carries the cluster's status; its `score`, the occurrences (skipped members count) times the highest weight among them (blocker 4, high 3, medium 2, low 1; 1 for a skipped member without a severity); its `rejected` members; and `forward`, false for a cluster of only skipped members with fewer than 3, which stays skipped and out of the digest. For each forward cluster:

- **Scope** is **global** when the fix lands in shared setup (user-level steering files, skills, hooks, tooling) or when the same friction shows up in more than one project, which moves even a project-level fix there. It is **project** when the fix lands in one repo.
- **Already in place**: read its target. If the change is already there, mark the cluster resolved in step 7 without asking.
- **Recurring after rejection**: a cluster with a `rejected` member is not proposed again. List it apart with its count and the rejection reason, for the user to reopen it or fold its open members into the rejected one.

## 4. Decide

The user decides each cluster on a standalone HTML page; everything else waits for step 5.

Write the digest to `<scratchpad>/retro-digest.json`, shaped like [`scripts/example-digest.json`](scripts/example-digest.json):

- `clusters`, highest score first, with ids `C1…`: a title naming the change and the friction it removes, members (the canonical one marked `*`), scope, projects, score, target (the owner) and proposal, plus your `observation` (why apply or reject, what it overlaps, what a past attempt showed) and your `recommend`. A cluster of skipped members needs the proposal its members never had: write it from their evidence. A proposal fixes the owner, correcting the step, rule or check that misled; recommend reject for one that adds a second way beside it (an exception paragraph, an alias, a fallback), and name the owner text to fix instead.
- `recurring`, with ids `R-A…`: the open members, the rejected member with its reason, your observation, and `recommend` (`fold` unless you argue otherwise).
- `legend` for the id prefixes, a `title` with today's date, and `reviewFile`: `retro-review-<date>.json`.

Build the page with `node <skill-dir>/scripts/build-review-page.mjs <scratchpad>/retro-digest.json <scratchpad>/retro-digest.html`.

**Themes.** With more than 15 clusters, the user decides by theme, and the cluster page stays as reference for looking into one. Group every cluster into 10–15 themes: a theme holds the clusters whose change lands in the same place (one skill, repo, hook or steering file). Noise (harness behaviour, guards working as intended, guessed owners) is a theme of its own, recommended reject. Check that every cluster sits in exactly one theme, none left out or repeated, before going on. Write `<scratchpad>/retro-themes.json`, shaped like the digest with the themes as `clusters`, ids `T1…` highest score first, and `recurring` copied as is:

- `title`: the change and the friction it removes, one line. `target`: the owning repo or file. `scope` and `projects`: the union of its clusters'.
- `members`: one string, `"N clusters, M findings"`. `score`: the sum of its clusters' scores.
- `proposal`: one line per cluster you recommend applying (title and occurrences), then `Leave open: …` and `Reject: …` with the rest, lines separated by `\n`.
- `observation`: why the theme is worth it, which items weigh most, what you drop and why, ending with: "apply" accepts your recommendation on each line, "reject" drops the whole theme, "open" defers it.
- `recommend`: `apply` when any line is to apply, else `reject`.

Write `<scratchpad>/retro-themes-map.json`, `{"T1": {"apply": ["C3", …], "open": […], "reject": […]}}` from your recommendations, and build `retro-themes.html` from the themes digest.

Open the page the user decides on in the browser (`open` on macOS). Every row starts on your `recommend`; the user changes what they disagree with and saves `reviewFile` to the browser's downloads folder, or copies it for the chat. Send one self-contained message, since the user may read it hours later in a scheduled thread: the page's path (and the cluster page's, with themes), the cluster count, the top three by score or, with themes, a table of every theme (id, theme, clusters and findings, your recommendation), the clusters already marked resolved, the recurring ones, and that answering in chat works too. Wait.

Done when the user says they're done or answers in chat. Read `decisions` from the newest `~/Downloads/retro-review-<date>*.json` (the browser appends ` (1)` to a repeat save); if there is none, ask where it was saved. With themes, turn each theme's decision into its clusters' through the map: `apply` takes the map's split, `reject` rejects every cluster in it, `open` leaves every one open.

## 5. Plan the changes

In one message, for the decided clusters:

- **Applied and reopened.** Group them by the repo or file that owns each target, and give the commits or PRs each group becomes, their order and dependencies, and which need a ticket. Ask for the ticket ids or "create them", and for any adjustment to a proposal.
- **Rejected.** Give a reason for each, with your observation as the default.

Before writing a group's ticket or brief, check every concrete claim its proposals make (paths, response shapes, flag names, ports) with a grep or read of the target repo and write it with `file:line`; mark the rest "unverified: …".

Done when every group has its tickets and every rejection its reason.

## 6. Apply through agents

You are the orchestrator here: each group from step 5 goes to its own implementation agent, and only its report comes back, so the diffs stay out of this context and it keeps room for the record.

Brief each agent with its group: the target repo's path, its ticket id, and per cluster the id, member refs, proposal with the user's adjustments and the verified claims with `file:line`. The agent applies each cluster as its own change, following that repo's own workflow (branch, commit and PR rules, ticket workflow), implements a `mechanical` finding as a deterministic check (lint rule, hook, CI job) instead of prose, and reports per cluster `applied (<commit, PR or file>)` or why it was not applied. A question only the user can settle comes back as its report; ask the user and resume that same agent with SendMessage.

Launch them with the Agent tool: groups in different repos in parallel, in one message; groups in the same repo one after another, in step 5's order, since they share a working tree.

Done when every agent has reported each of its clusters.

## 7. Record

Set the status of every member of every cluster you touched, in one call with a JSON file of `{"<ref>": "<status>"}`: `python3 <skill-dir>/scripts/retros.py set --from <file>`. Each status is one of these, and the script refuses any other shape or a ref it can't find, naming each:

- `applied (<commit, PR or file>)`, from the agents' reports and for the already-in-place ones.
- `rejected (<reason>)`.
- `duplicate of <project>/<file>#R<n>` for every non-canonical member, pointing at the canonical one.

A cluster an agent did not apply keeps its members `open`. Done when every finding in a cluster you put on the page has its new status or was left `open`; skipped findings left out of the digest keep theirs. Finish with what was applied, where, and what is still open and why.
