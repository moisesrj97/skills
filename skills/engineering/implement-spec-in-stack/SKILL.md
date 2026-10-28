---
name: implement-spec-in-stack
description: "Implement the result of /to-spec and /to-tickets in code as a stack of PRs (one branch and PR per ticket) managed with gh stack. Each layer gets /comment-cleanup, a UI check when it renders something, and a /code-review high loop until clean before its draft PR opens; nothing is merged."
disable-model-invocation: true
---

You have been provided a spec. This spec should have tickets associated with it, describing how to implement the spec.

The issue tracker should have been provided to you. If not, tell the user to run `/setup-matt-pocock-skills`.

The goal is the entire spec implemented as a **single linear stack** of branches managed with `gh stack` (load the `gh-stack` skill for its agent rules — every command must run non-interactively). Each ticket becomes one branch and one PR, based on the branch below it. Every PR is opened only after its layer has passed `comment-cleanup` and `code-review high`. **Nothing is merged** — the user merges every PR by hand, so never run `gh stack merge` or `gh pr merge`.

The tickets are not a list of steps. They are a **task graph** with blocking relationships between them. A stack is linear, so the graph is flattened into a **topological order**: every ticket sits above all the tickets it depends on. Independent tickets are still stacked one on top of the other — that is the price of one stack, and it is fine.

Communication to and from subagents should be sparse. Communicate primarily through **context pointers**: to the spec, tickets, research notes, and previous commits. Don't duplicate information already available via pointers.

## Why the work is sequential and in place

Implementation runs **one ticket at a time, in the user's checkout** — no worktrees. A worktree needs its own install, and a linear stack gains little from parallelism: each layer has to sit on the finished layer below.

A layer is **pushed only once it is final** (implemented, cleaned up, reviewed, fixed). Pushed branches are never rewritten: rewriting one would force-push every branch above it and churn the PRs the user may already be reviewing. If a later ticket turns out to need a change that belongs in a lower, already-pushed layer, make the change in the current layer and mention it in that PR's description and in the final report, rather than going back down the stack.

## When a skill is not available

This skill delegates to other skills (`gh-stack`, `tdd`, `comment-cleanup`, `code-review`, `github-pr`), and so do its subagents. If the Skill tool reports one of them as not available, **stop and ask the user**. Do not reproduce the skill by hand. Usually the skill has model invocation disabled, and only the user can run it or re-enable it. An improvised version would quietly skip whatever the real skill enforces. Implementer subagents must report this back instead of working around it.

## Branch names

If the repo's `CLAUDE.local.md` or `CLAUDE.md` has a `## Ticket tracker` section, follow its branch format: it is what links the PR to the ticket. Otherwise use `<ticket-id>-<short-kebab-description>` with 2–5 words and no `/`, e.g. `42-doc-language-detection`.

## Steps

1. Read the spec and tickets to understand the task graph. Fix the topological order and the branch name of every ticket, and show the planned stack (bottom → top) to the user before writing code.

2. Check the starting point: the working tree must be clean (stop and ask if it isn't). Then `git fetch origin`, check out the default branch and fast-forward it.

   If a stack for this spec already exists (`gh stack view --json` from one of its branches, or branches named with the tickets' IDs), you are resuming: tickets whose branch already has an open PR are done. Continue from the top of the stack.

3. (optional) Use an **exploration subagent** to conduct any exploration required by the tickets — relevant codebase files or external documentation. It saves its markdown notes in a directory outside the repo (the scratchpad), accessible by all future subagents. This lets the **implementer subagent** focus on implementation rather than exploration.

4. For each ticket, in topological order:

   a. **Create the layer.** For the first ticket, `gh stack init <branch>` from the default branch. For the rest, from the top of the stack, `gh stack add <branch>`.

   b. **Implement.** Spawn an **implementer subagent** with pointers to the spec, the ticket, and the research notes. It:
      - works on the branch that is already checked out — it does not switch branches, create worktrees or push;
      - calls the Skill tool with `tdd` to build the ticket;
      - commits with Conventional Commits subject lines only (no body, no attribution trailers);
      - calls the Skill tool with `comment-cleanup` on the layer's own diff (`<parent-branch>...HEAD`) and commits the result.

      Keep its agent ID: it is the one that fixes the review findings.

   c. **Check the UI.** Only for a layer that changes what a screen renders. Render every touched screen at 375, 900 and 1440 px, through the screenshot harness the repo's `CLAUDE.md` names or, failing that, `claude-in-chrome` on the dev server. Hand the screenshots and the ticket to a **design-review subagent** that reports overlaps, clipped or mixed-language copy and anything the ticket didn't ask for, each with a P0–P3 severity. P0 and P1 go to the implementer (SendMessage); re-render after each fix. Done when no P0 or P1 is open. If the app can't be run, say so in the PR description instead.

   d. **Review loop.** Repeat until a round leaves no confirmed finding:
      1. Call the Skill tool with `code-review` at level `high`, scoped to this layer only (`<parent-branch>...<branch>`), over the whole layer every round. The lower layers have already been reviewed, so reviewing against the default branch would only produce noise. Do not pass `--comment`: no PR exists yet, and comments are never posted without the user's approval.
      2. Vet each finding: re-open the cited lines and quote them. **Confirmed** needs the quote and a failure scenario you can trace in it; everything else is discarded with a one-line reason, kept for the final report.
      3. Send the confirmed ones to the same implementer (SendMessage) to fix on this branch, then run `comment-cleanup` on the fix commits.

      Stop and ask the user instead of looping when a finding is their call (scope, a design trade-off, reversing a decision they made), or when round 4 still has confirmed findings: the loop isn't converging.

   e. **Open the PR.** `gh stack push` to push the layer, then call the Skill tool with `github-pr` to open its PR as a stacked **draft** PR (`--base <parent-branch>`). The user has authorised opening PRs without asking inside this skill, so that authorisation is the approval `github-pr` asks for: generate the title and description, print them, and create the PR without waiting for `approve`. Then `gh stack submit --auto` to register the new PR in the stack on GitHub. Every branch already has a PR at that point, so it creates nothing new.

5. Do not run `gh stack sync` or `gh stack rebase` during the run, even if the user merges lower PRs in the meantime. Both rewrite branches that are already pushed. Restacking after merges is the user's call.

6. Once all tickets are done, report:
   - the stack, bottom → top: ticket, branch and PR URL;
   - the review findings that were discarded, and why;
   - any change that landed in a higher layer than where it belonged (see above).

   Leave the tickets untouched in the issue tracker — no status, tags or other metadata. They are closed when the user merges.
