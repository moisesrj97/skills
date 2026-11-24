# Steps 3, 4 and 6 (finisher)

You take megamoind's branch from the implementer's last commit to a reviewed, cleaned-up change, and make every later code change the orchestrator sends you (a failing verification flow, a red CI check). `<skill-dir>` is megamoind's folder, the one holding this file. [`WORKSPACE.md`](WORKSPACE.md) applies throughout. Start each step with `python3 <skill-dir>/scripts/metrics.py mark <state> "<n> <name>"`: `3 review`, `4 security`, `6 comments`. Pass `tag=megamoind-run: <run> role=review-<lens>` to every `diff-review` you run, directly or through `pair-review`.

## 3. Tidy after and pair review

Two reviews of the same commit, launched together so neither waits for the other:

- **Tidy after**: call the Skill tool with `diff-review` with `lens=cleanup` over `<base>...<top>` and `standards=<skill-dir>/../craftsmanship/tidy-first.md,<skill-dir>/../craftsmanship/simple-design.md`. One round. Place each finding by `craftsmanship`'s area-of-impact table: a `refactor:` commit on the ticket's branch when it keeps behaviour and touches only files the behaviour change needs, the post-PR branch `<name>-tidy-after` on top of it, or Later on a list for the report. Skip one that would change behaviour or is wrong, with a one-line reason. Commit tidyings one kind per commit when the batch is large, with the tests green after each, and name in the report any tidying over code no test covers.
- **Pair review**: call the Skill tool with `pair-review` with args `<base>...<top> spec=<scratchpad>/<ticket>-brief.md standards=<skill-dir>/../craftsmanship/test-desiderata.md`, passing the user's decisions from the brief, any HITL answers and the implementer's decisions beyond the brief as its already-decided list. It fixes and re-reviews until done; its HITL stops are megamoind's HITL stops. A finding against one of the implementer's decisions keeps the decision and is discarded with the decision's why, unless it shows the decision breaks the ticket: that is HITL.

Land the tidyings before pair-review's round 2, so that round reviews them too. A tidying that lands after pair-review's last round, a clean round 1 included, gets one more round over the new tip. A finding fixed by a tidying goes on the layer its area of impact picks. A review fix in hunks that a later tidying commit also touches goes in its own `fix:` commit on top, since GitButler refuses to amend or squash it below that commit; the tidying commit stays behaviour-free.

Done when pair-review ends Done, every tidying has landed or moved to Later, and the gates are green.

## 4. Security review

Call the Skill tool with `diff-review` with `lens=security` over `<base>...<top>`, now that the code has settled. One round, with no loop: no review follows it, so each fix stays within its finding.

Done when every finding it returns is fixed with a test that fails without the fix, or discarded with a one-line reason for the report, and the gates are green. Then report and wait. The report resolves each verification flow from the brief, so the verifier starts driving instead of reading code: the URL or command that starts it, the data, account or fixture it needs and how to get it, the steps, the observable to check, and the files it exercises.

## 6. Comment cleanup

Call the Skill tool with `comment-cleanup` over the whole branch diff (`<base>...<top>`). Done when its result is committed and the gates are green.

## Later fixes

A failing flow or a red check the orchestrator sends you: fix it and report once the fix is committed and the gates are green.

## Report

Your commits, each review pass (findings fixed, discarded and why) and the Later tidyings, each with its files and why it waits.
