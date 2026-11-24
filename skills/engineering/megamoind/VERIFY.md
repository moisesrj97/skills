# Step 5: Verify in the real app (verifier)

You prove megamoind's change works in the running app; you change no code. `<skill-dir>` is megamoind's folder, the one holding this file. [`WORKSPACE.md`](WORKSPACE.md)'s "Sharing the workspace" applies. Start with `python3 <skill-dir>/scripts/metrics.py mark <state> "5 verify"`.

Work from the flows the finisher's report resolved and the implementer's failure-path checklist. Read code only to fill a gap they leave, naming the gap in your report.

Start what the app needs as background subshells (`run_in_background`) with the commands from the brief, and stop every one you started when done. When the brief says the servers are already running, use them, since a second copy fights for the same ports.

- **Frontend or fullstack**: drive the dev server in a real browser with whatever browser tooling this harness gives you (a browser-control skill, extension or MCP server; Playwright when there is nothing else). No way to drive a browser counts as an environment that won't come up. This step is an explicit request for browser verification, so tools a harness keeps for user-requested browser work (T3 Code's `preview_*`) apply here. Other agents may share the browser, so open a tab of your own, act only in it and close it when done.
  - Walk every flow the ticket touches and check each touched screen at 375, 900 and 1440 px for overlaps, clipped or mixed-language copy, and anything the ticket didn't ask for. Compare each screen against the brief's visual reference as well as the ticket's text.
  - To measure (bounding boxes, computed styles, visibility) or read text, evaluate a script in the page (`preview_evaluate`). A snapshot carries console, network and the accessibility tree, 10 to 20 KB each, so take one only for a capture you keep (`save: true`).
  - **States local data can't produce** (in progress, queued, failed): inject them in the page by intercepting `fetch` and rewriting the response. Keep the datastore to states the app produced itself: background jobs act on what it holds, so a stuck-job cron picks up a fake running job and a fake queue entry can start real work.
  - **Async or time-based UI** (polling, timers, text that may never appear): have the page record what happens (patch `fetch` or add a `MutationObserver` that pushes `{t, what}` into `window.__log`), then read it back with short `preview_evaluate` calls, each well under its 15 s timeout, returning what the page actually shows. `preview_wait_for` on exact text that never appears fails only after 60 s and tells you nothing, so read state this way instead of chaining it.
- **Backend**: call the Skill tool with `debug-trace` and drive the changed paths through the running service, reading the trace to confirm the values the ticket expects.

Each flow leaves evidence (a screenshot, a recording or a trace excerpt) following [`EVIDENCE.md`](EVIDENCE.md), failing flows too, so the finisher sees what broke.

If the environment won't come up after one attempt, that's HITL; if it still can't run, record what went unverified for the PR description and the report.

## Report

The flow counts (verified, failed at least once, unverified), each flow with pass or fail and its evidence files (paths and one-line sources), and what went unverified and why.

Done when every flow from the brief and every item of the failure-path checklist has been exercised, behaves as the ticket asks and has its evidence file, re-captured after any fix it went through.
