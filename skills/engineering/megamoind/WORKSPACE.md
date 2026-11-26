# Workspace rules

Megamoind's rules for every agent that touches the branch: the orchestrator, the implementer, the finisher, the polisher and the verifier. `<skill-dir>` is megamoind's folder, the one holding this file; steps named below are megamoind's.

## Gates

The checks that must be green before any push: type-check, lint and tests for **every project the change touches**. In a monorepo that means each touched package's own `ci` (or equivalent) script as well as the root's.

- Read the commands from the project's `CLAUDE.md` / `CLAUDE.local.md`, else from `python3 <skill-dir>/scripts/preflight.py --base <base> --head <branch>`: its `touched_packages` lists every package the branch's diff touches, the root included, with the gate scripts each defines, and `package_manager` names the runner.
- Launch a long suite (several minutes) in the background from the start, so the foreground timeout can't kill it.
- If preflight reports `dev_doctor`, run `yarn dev:doctor --flow <flow> --no-services` before the first type-check and after any pull that touches `packages/`. It rebuilds stale workspace builds, which otherwise read as a red gate.
- A heavy spec that times out under full-suite load counts as red only after it fails again in isolation.
- Run checks as wide as the project's scripts do, but point every auto-fix (`--write`, `--fix`, a formatter) at the files of your branch's diff only. One aimed at a whole folder rewrites files outside the ticket and can break them, e.g. by dropping a `@ts-expect-error`.
- Before each commit, check it holds only your ticket's files (`but diff` under GitButler, `git diff --stat` otherwise). Under GitButler, other agents keep editing the same files after that check, so right after each commit read `git diff <base>...<branch>` for hunks that aren't your ticket's and take them out (`but uncommit <hunk ids>`).
- A commit hook that runs lint-staged reads the config in the working tree. When one change both adds a lint or format rule and fixes the files it flags, commit in the order fixes, then pure formatting, then the config, adding the new rule to the working tree only for that last commit.

Push only with every gate green or **foreign** (see "Sharing the workspace").

## Layers

The ticket's branch, plus a pre-PR `<name>-tidy-first` below it and a post-PR `<name>-tidy-after` above it when the plan has them, are the ticket's **layers**, bottom to top. `<top>` in the ranges is the top layer's branch name, never `HEAD`, which under GitButler is the workspace commit merging every applied branch. With plain git, after any later commit on a lower layer (a review fix, a CI fix), rebase each layer above onto it, bottom up (`git rebase <lower> <upper>`), then switch back to the top layer; once they are pushed, push them with `--force-with-lease`.

## Docs or skill changes

When the diff holds no code (a README, a skill, a recipe), the steps keep their shape and change what they test:

- **Gates**: links and anchors resolve.
- **Step 2**: the test is each claim the doc makes, checked against the code it documents and cited with `file:line`, plus its code snippets type-checked against the real types. A skill with a `benchmark/evals.json` gets one new eval per behaviour change, with the opposite case as a control. When the project defines a check its evals must pass, the implementer runs it in a fresh agent on the first draft, before committing and handing back, and again after each fix until it passes.
- **Step 3**: tidy after runs over prose a reader maintains (a SKILL.md, a README) and skips data files such as `evals.json`.
- **Step 4** runs only when the diff adds a command, script or snippet that runs code or touches credentials. Otherwise skip it and say so in the report.
- **Step 5**: run every command or snippet the doc adds exactly as written, in the real app. For a skill, run each new eval prompt in a fresh agent that reads only the skill. The evidence is each one's trace: the command or prompt and the output that proves it.
- **Step 6** is skipped.
- **Step 7**: with no such command, script or snippet, the `## Merge risk` section is one green line ("Docs only, no code runs") instead of a `merge-risk` run.

## Sharing the workspace

Under GitButler, other agents' branches may be applied in the same working directory, so their unfinished changes show up in your type-check, tests and dev server. Commit only your own hunks (`but commit -b <branch> <ids>`, ids from `but diff`) and edit only files your ticket needs. A red gate is **foreign** when every failure sits in a file outside your branch's diff that `but status` shows changed by another branch or uncommitted outside yours. A change you produced yourself, e.g. a formatter or codegen run, is never foreign, even uncommitted. Leave a foreign red alone (fixing it would mix two tickets in one branch), list it for the report and count the gate as green. Their edits also hot-reload into your dev server: a checker overlay naming files outside your diff is foreign, so remove it from the DOM and go on, and when the UI stops reacting after a burst of hot updates you didn't cause, reload the page before debugging.

The inverse is a **borrowed green**: another applied branch supplies hunks yours lacks (an import, a type, a helper), so your gates pass locally and CI, which builds your branch alone, fails. Your code may depend only on `<base>` and your own commits. When the base stays stale (step 0), check that each symbol you use from a file other branches touch exists in `<base>` (`git show <base>:<file>`).

Before pushing, whenever other branches are applied, run the gates on your branch alone: `python3 <skill-dir>/scripts/isolated_gates.py <branch> --base <base> --dir <scratchpad> --gate '<cmd>' …` (one `--gate` per type-check or test command, run from the repo root). It checks the branch out in a throwaway worktree, installs offline, builds the workspace packages the touched ones depend on from that copy, copies the untracked `.env*` files and removes the worktree after; exit 2 is a setup failure to report, not a red gate.

A change that belongs to the `<base>` branch's ticket goes on that branch. Stop and ask for it, naming the change. When told the base moved, re-run the gates and go on.
