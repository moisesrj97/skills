Reviewed the diff and quoted each cited line from the head commit. I wrote no files.

### 1. skills/engineering/megamoind/SKILL.md:97: the `mode: minimoi` hand-off rule for a delegated brief is stated three times in one file

Rule: Simple design 3, no duplication (the same knowledge lives in one place)

Cost: The `brief=` routing to minimoi appears in the argument list (line 21), in step 0's `brief=` sentence (line 84), and again in the "Minimoi" paragraph (line 97). A change to the trigger, such as a different marker or a new condition, has to be made in three places. If the three disagree, the agent has to decide which one wins.

Fix: Keep line 21 as the argument's pointer and line 84 as the routing sentence. Delete the sentence on line 97 that starts "With `brief=`, ask nothing: hand off only when the brief already says `mode: minimoi`." Line 84 already sends that case to the hand-off, and the rest of line 97 (the no-`brief=` question and the `metrics.py mark … --skill minimoi` hand-off) stays as it is.

> 21: - `brief=<file>`: step 0 already answered by whoever delegated the ticket. Read it instead of asking; only what it leaves open is HITL. A brief that says `mode: minimoi` runs the reduced flow (see step 0's "Minimoi").
> 84: With `brief=`, read it, settle on your own whatever of the plan below it leaves open (only the user's decisions are HITL), and go to step 1, or hand off when it says `mode: minimoi`. …
> 97: **Minimoi**: … With `brief=`, ask nothing: hand off only when the brief already says `mode: minimoi`. To hand off, run `metrics.py mark <state> "0 handoff" --skill minimoi` and follow MINIMOI.md from its step 1 instead of this file's.

### 2. skills/engineering/megamoind/MINIMOI.md:20: the "Handed off by megamoind" branch of step 0 only repeats the hand-off and is never the entry point

Rule: Simple design 4, fewest elements; Simple design 3, no duplication

Cost: megamoind's hand-off sends the run to "MINIMOI.md from its step 1" (SKILL.md:97), so a handed-off run never enters step 0. This bullet restates what megamoind already did (brief written, run marked as minimoi) and only says "Go to step 1". That gives MINIMOI.md two entry rules where one would do, and the hand-off contract now lives in both files.

Fix: Delete the "Handed off by megamoind" bullet and make step 0 the direct run's step alone (fold the "Direct" bullet into plain text). Alternatively, keep the bullet and have SKILL.md:97 say "follow MINIMOI.md from its step 0". Either way, only one file says where a handed-off run enters.

> 20: - **Handed off by megamoind**: the brief exists and says `mode: minimoi`, and the run is already marked as minimoi. Go to step 1.
> 21: - **Direct**: megamoind's step 0, started with `metrics.py start <ticket> --dir <scratchpad> --skill minimoi`. …

### 3. skills/engineering/minimoi/SKILL.md:12: a direct `/minimoi` fetches the ticket twice and checks eligibility twice

Rule: Efficiency (repeated I/O and repeated work); Simple design 3

Cost: Steps 1 and 2 of minimoi/SKILL.md fetch the ticket, read the code it touches, and check it against "Eligibility". Step 3 then runs MINIMOI.md step 0 "Direct", which is "megamoind's step 0". That step fetches the ticket again (megamoind/SKILL.md:80). Its "Minimoi" paragraph also checks eligibility again and asks "in a round of its own whether to hand off to minimoi" (SKILL.md:97). The result is a second tracker call, a second eligibility judgement, and a possible hand-off question about a run that is already minimoi.

Fix: In MINIMOI.md:21, say the direct step 0 is megamoind's step 0 on the ticket already fetched, with the eligibility already checked, so its "Minimoi" question is not asked. Alternatively, move the fetch and eligibility check out of minimoi/SKILL.md steps 1–2 into MINIMOI.md's direct step 0, so they happen in one place. The refusal path stays the same: edit nothing, name the failed condition, point to `/megamoind <ticket>`.

> minimoi/SKILL.md 12: 1. **Ticket**: with no ticket in the request, get one as megamoind's step 0 does (give the ID or create it). Fetch and read it, and read the code it touches.
> minimoi/SKILL.md 13: 2. **Eligibility**: check the change against every condition in MINIMOI.md's "Eligibility". …
> megamoind/SKILL.md 80: Fetch the ticket (`gh issue view` for a GitHub issue, the tracker's tools otherwise); …
> megamoind/SKILL.md 97: … Without `brief=`, once the brief is written and the ticket meets every condition in MINIMOI.md's "Eligibility", ask in a round of its own whether to hand off to minimoi, …

### 4. skills/engineering/megamoind/scripts/test_metrics.py:189: the same `redirect_stdout` wrapper is repeated in four tests around `metrics.main`

Rule: Simple design 3, no duplication; Tidy First, extract helper

Cost: Every `Skill` test that runs `start` wraps it in `with contextlib.redirect_stdout(io.StringIO()):`. Two tests also call `metrics.main` directly next to the existing `state_after` helper. The silencing is noise in each test and is spread over two call styles.

Fix: Add a `run(self, *argv)` method to `Skill` that calls `metrics.main(list(argv))` under `redirect_stdout`. Make `state_after` call it, and replace the four `with` blocks and the bare `metrics.main([...])` calls with `self.run(...)`. The assertions stay the same.

> 189:         with contextlib.redirect_stdout(io.StringIO()):
> 190:             state = self.state_after("start", "PD-1", "--dir", str(self.root), "--skill", "minimoi")
> 199:         with contextlib.redirect_stdout(io.StringIO()):
> 200:             metrics.main(["start", "PD-1", "--dir", str(self.root)])
> 205:         with contextlib.redirect_stdout(io.StringIO()):
> 206:             metrics.main(["start", "PD-1", "--dir", str(self.root), "--skill", "minimoi"])

END OF ROUND
