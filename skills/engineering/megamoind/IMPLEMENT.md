# Step 2: Implement (implementer)

You build megamoind's ticket from the confirmed brief. `<skill-dir>` is megamoind's folder, the one holding this file. [`WORKSPACE.md`](WORKSPACE.md) applies throughout. Start with `python3 <skill-dir>/scripts/metrics.py mark <state> "2 implement"`.

Two passes, with structure and behaviour always in separate commits:

1. **Tidy first**: the plan's first tidyings, as the PR's first `refactor:` commit or on the pre-PR branch, following `craftsmanship`. With plain git and a pre-PR, create the ticket's branch once its commits are in (`git switch -c <name> <name>-tidy-first`), since a branch created earlier stays on the old commit.
2. **Behaviour**: call the Skill tool with `tdd` and build the ticket at the seams the brief agreed, reusing what the brief found. For a bug, the diagnosis loop from step 0 is the first red test; once it is green, run `diagnosing-bugs` phase 6 (its instrumentation and throwaway harnesses removed, the original reproduction rerun) before committing.

Everything you read stays in your context and is re-read on every later turn, so read narrow and in batches:

- **Ranges**: locate with `rg -n`, then read the lines you need (`sed -n '<a>,<b>p' <file>`, a function or a test block with a few lines around it). Read a whole file only when you will rewrite most of it.
- **Batches**: send the reads and searches that don't depend on each other as parallel tool calls in one turn, e.g. the file you will change, its test and the helper the brief names to reuse.

Run type-check and the single test files you are touching as you go, and the gates once at the end. Commit locally at each working checkpoint.

When the brief rules out tests, write a **failure-path checklist** to the scratchpad: for every async call or batch, its partial failure, total failure and empty result, plus the id types that cross a `String()`/`Number()` conversion. Each item is handled in code or marked accepted.

When the ticket adds or ports an LLM prompt, or a new eval of one, run it 5 times on a real input, even when the brief rules out a bench, plus once on an opposite case as a control. Score each sample against a per-case checklist written before the run, and report the pass count (5/5); anything less is red. A user-approved bench, or any run that needs the user's approval or credentials, is the orchestrator's: write the script and per-case checklist into your report.

## Report

Your commits, the failure-path checklist, and a `## Decisions beyond the brief` section: a short paragraph naming each choice the code makes that the brief doesn't settle (an edge case's behaviour, a name or shape a test pins, a library or helper picked over another, something left out on purpose), each with its why and `file:line`; "None" when there are none. A reviewer will question exactly these, and the finisher has only this paragraph to defend them.

Done when every point of the ticket is implemented, every planned tidying first has landed, every checklist item is handled or accepted, the gates are green and the report has its `## Decisions beyond the brief` section.
