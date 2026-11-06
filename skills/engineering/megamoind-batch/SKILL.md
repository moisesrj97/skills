---
name: megamoind-batch
description: "Delegate a batch of tickets end to end, unattended: one megamoind agent per ticket, independent tickets in parallel, dependent ones stacked, ending in draft PRs that go ready together once every one is green. Use when the user hands over more than one ticket to take to PRs: a spec ID (the output of /to-spec and /to-tickets), a list of tickets or a tracker query such as a label, e.g. \"megamoind-batch PD-120\", \"megamoind #12 #14 #15\", \"implementa los issues con ready-for-agent\"."
argument-hint: "<spec ID | ticket IDs | tracker query>"
---

# Megamoind batch

You are the **orchestrator**. The user hands over a batch of tickets (a spec's, a list, or what a tracker query returns) and walks away. One **megamoind** agent takes each ticket end to end; you plan the order, brief the agents, keep them moving and land the whole set as PRs. You write no code yourself.

The result is a set of PRs: tickets that depend on each other are **stacked** (one branch per ticket, each based on the one below), independent ones are separate PRs off the default branch. Everything runs in **one GitButler workspace**, with no worktrees, because the repos are too heavy to install twice and GitButler keeps several branches applied side by side.

Invoking this skill is the user's approval to commit, push the batch's branches (`--force-with-lease` included, until reviewers are added), and open draft PRs, each once its gates are green. Marking PRs ready and adding reviewers wait for their explicit yes. **The user merges by hand**; you merge nothing.

Stop only for **HITL**: a decision that is the user's (scope, product behaviour, a design trade-off, reversing something they decided) or a loop that isn't converging.

## When a skill is not available

This skill delegates to `megamoind`, which delegates further. If the Skill tool reports it as not available, or an agent reports one of its skills missing, stop and ask. An improvised copy silently skips whatever the real skill enforces.

## Agents

Every agent runs **async**: you start it, go on with the others, and its report or question reaches you on its own. A synchronous launch blocks you until the slowest agent returns, so a fast one's HITL question sits unread. Relay each HITL to the user the moment it arrives, naming the ticket, while the other agents keep running.

Each ticket runs in its own agent, prompted with `/megamoind <ticket> base=<branch> brief=<file> stop-at=draft` plus one line asking it to write its step 9 report to `<scratch>/<ticket>-report.md` and end the file with `END OF REPORT`.

A ticket can land as several **layers**: a tidy pre-PR below its branch, a post-PR above it. They belong to the ticket's place in its chain, and its report lists them bottom to top.

- **Inside Herdr** (`HERDR_ENV=1`): one pane per agent in a **column to the right** of your pane. The first splits your pane right (`herdr pane split --current --direction right --cwd "$PWD" --no-focus`); each next one splits the bottom pane of that column down. Start it with `herdr agent start <ticket> --kind claude --pane <id> -- --name <ticket>` and prompt it with `herdr agent prompt <ticket> "<prompt>" --wait --timeout 7200000`, run in the background. An agent asking a question in its pane is HITL: tell the user which pane needs them; they answer there.
- **Inside T3 Code** (`mcp__t3-code__delegate_task` available): one child per ticket with `delegate_task` (not the Agent tool, which T3 keeps in the foreground), `isolation: "shared"` so it works in this same checkout. Each child is a thread the user can open; a child asking a question is HITL: tell the user which thread needs them (its link); they answer there. T3 notifies you whenever a child's turn ends, even while it still waits on a Monitor, so only a report file sealed with `END OF REPORT` means done. On any other notice, check the file and reply only if the child is stuck, without polling. Later work for a child (step 3's lower-layer changes, step 4's red checks) goes to its thread with `t3_thread_send`, which keeps its history.
- **Otherwise**: a subagent per ticket with the Agent tool and `run_in_background: true`. It stops and reports a HITL question instead of asking; ask the user and resume the same agent with SendMessage.

Keep each agent alive until step 4 ends, since CI failures after ready go back to the agent that wrote the code. Step 5 closes them.

## Sharing the workspace

All agents write to the same working directory, so each one's type-check, tests and dev server see the others' unfinished changes. `megamoind` already commits only its own hunks and leaves a red gate in another branch's files to its PR's CI. What you control is how much the agents collide:

- Tickets likely to touch the same files go in the **same chain**, one after the other: two agents editing one file fight over its hunks.
- Run at most **3 agents** at once; more chains wait their turn. One workspace, one dev server and one browser don't scale past that.
- While agents run, the workspace is theirs. Run `but pull` or move branches only for a lower-layer change (step 3), with the agent above stopped, and for step 4's update, with every agent idle.

## Steps

### 0. Read the tickets

Resolve the batch through GitHub (`gh issue view`, `gh issue list --label …`) or the tracker the project's `## Ticket tracker` section names:

- a spec ID: the spec and its tickets (sub-issues, subtasks or the tickets it links);
- a list: those tickets;
- a query (a label, a status): the tickets it returns.

Read each ticket with its comments, where blocking relations are often written ("blocked by #195"). A tracker you can't reach is HITL. Check the repo uses GitButler (`but status` works) and the workspace has no uncommitted changes; if not, stop and ask. GitButler-managed hook files (`.githook/*` marked `GITBUTLER_MANAGED_HOOK`) and installed-skill dirs (`.agents/`) don't count. Before deleting any untracked dir, check for inbound symlinks (`find . -maxdepth 4 -type l -lname '*<dir>*'`) and references under `.claude/`.

Done when you have read every ticket in the batch with its comments and the workspace is clean.

### 1. Plan

Turn the tickets' blocking relationships into **chains**:

- a ticket sits above everything it depends on;
- a ticket with several parents linearises them into one chain (A, then B, then C), noted in the plan;
- tickets likely to share files join one chain (see above);
- each chain becomes one GitButler stack off the default branch; chains with one ticket are a plain branch.

For every ticket, prepare the brief `megamoind` step 0 would ask for: plan and test seams (with the visual reference when the ticket reproduces something already in the product), branch name, and how to verify it. The agent settles what the brief leaves open of the plan (reuse, tidyings, a bug's cause), so a brief carries the user's decisions, not that legwork. Work out once how to run the app (env, data or login) and which servers to share, and write into each brief the exact command that brings up the stack (e.g. `yarn dev:doctor --flow <flow>`, plus the services that flow leaves out), not a skill's name. Each brief also says that reds from a stale base are the orchestrator's, not HITL. If the repo has CODEOWNERS, say that marking the PRs ready will request those reviewers automatically.

Show it all in **one** round: the tickets the batch resolved to, the chains bottom to top with branch names, which chains run in parallel, and each ticket's brief. Done when the user has confirmed it; then write each brief to `<scratch>/<ticket>-brief.md`, adding their answers.

### 2. Prepare

Update the workspace from the target once (`but pull`), before any agent starts. When that changed a lockfile, reinstall dependencies with the project's package manager. Start the shared dev servers as background subshells, and add to every brief that they are already running.

### 3. Run the chains

Start the bottom ticket of each chain, up to 3 agents, with `base=` the default branch. When an agent's report file is sealed with `END OF REPORT`, read it and start the next ticket of that chain with `base=` the top layer it lists, or the next waiting chain if a slot is free. A report with an open HITL question stops that chain until the user answers; the other chains keep running. Done when every ticket's report is sealed.

If a ticket turns out to need a change in a lower layer of its chain, the change belongs there. The ticket's agent stops and asks for it; leave it stopped until the change lands. Send the change to that layer's agent, which commits it on its own branch and runs its gates; GitButler restacks the branches above. Push the stack (`but push`), then tell the waiting agent its base moved. No one has reviewed the drafts yet, so rewriting them is fine.

### 4. All ready

Once every ticket's draft PR is green, bring the stacks up to date while the agents are idle: `but pull --check`, then `but pull`, reinstall dependencies if the lockfile changed, and `but push`. Then ask the user **once** whether to mark all the PRs ready, listing them, and send a `PushNotification` as the question goes out, because a question waiting in a thread goes unnoticed. On a yes, `gh pr ready <number>` each, tidy layers included, bottom of each chain first.

Some checks only run on ready PRs, and some only on PRs whose base is the default branch (e.g. Jenkins): a stacked layer gets those only once the layer below merges and GitHub retargets it. Report such layers as "pending retarget" and leave them out of every wait's exit condition. Loop until every other check of every PR is green, required or not:

1. Wait with `Monitor` or an until-loop on `gh pr checks` rather than a tight poll.
2. Diagnose each red check enough to classify it as in `megamoind` step 8.
   - **Base staleness** (a scan comparing against a default branch newer than the PR's base): yours. Update the stacks as at the start of this step (`but pull --check`, `but pull`, reinstall if the lockfile changed, `but push`).
   - **Anything else**: send it to the agent that owns the branch, which handles it as its step 8 says and pushes a fix. A fix in a lower layer restacks the layers above; push the stack.

Stop with HITL after 3 fix rounds that haven't turned CI green.

### 5. Wrap up

Close every pane you opened (`herdr pane close <id>`), cancel any T3 child still running (`task_cancel`), and stop the dev servers you started. Call the Skill tool with `retro-with-docs` on this orchestrating session (each agent already ran its own); if it is not available, skip it and say so. Then report:

| Chain | Ticket | Branch | PR | CI |
|---|---|---|---|---|

One row per layer. Then, from the agents' reports: Later tidyings, findings discarded and why, what went unverified in the real app, changes that landed in a different layer than planned, and open HITL questions. Leave the tickets untouched in the tracker; they close when the user merges.

### 6. Reviewers (optional)

Ask once whether to add reviewers to the PRs, proposing names from CODEOWNERS or the recent history of the touched files. Run `gh pr edit <number> --add-reviewer …` only after the user's explicit yes.
