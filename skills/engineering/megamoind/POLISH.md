# Step 6 and later fixes (polisher)

You make every code change on megamoind's branch after the reviews: a failing verification flow, step 6, a red CI check. `<skill-dir>` is megamoind's folder, the one holding this file. [`WORKSPACE.md`](WORKSPACE.md) applies throughout.

The finisher's report lists the review findings it discarded and why, and the implementer's `## Decisions beyond the brief` lists choices made on purpose. Keep both: a fix that would reverse one of them is HITL.

## Fixes

A failing flow (with the verifier's evidence) or a red check (with the orchestrator's diagnosis): fix that failure alone, with a test that fails without the fix when the failure is behavioural. Done when the fix is committed and the gates are green.

## 6. Comment cleanup

Start with `python3 <skill-dir>/scripts/metrics.py mark <state> "6 comments"`. Call the Skill tool with `comment-cleanup` over the whole branch diff (`<base>...<top>`). Done when its result is committed and the gates are green.

## Report

After each piece of work: your commits, each with the failure or step it answers.
