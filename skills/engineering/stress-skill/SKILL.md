---
name: stress-skill
description: Finds how much of a skill's body can be cut while its evals still pass, by benching variants with parts removed in fresh `claude -p` runs. Manual only; it spends many model runs.
disable-model-invocation: true
---

# Stress skill

Trimming a skill by feel keeps dead lines and cuts load-bearing ones. Whether a line changes behaviour depends on the model, and only a run settles it. This skill runs that test one unit at a time. Invoking it authorises the bench runs the user approves in step 1; changing the original skill needs a fresh yes.

The body is in scope; the description routes the skill and belongs to `skill-shaper`. Cases persist in `evals/<name>/` at the root of the repo that holds the skill: `cases.json` with its fixtures and fakes beside it, so the next bench starts from them. Runs and variants go in `<scratchpad>/stress-<name>/`. `bench.py` is `<skill-dir>/scripts/bench.py`; its docstring has the `cases.json` format.

## 1. Cases and checklist

When `evals/<name>/cases.json` exists, start from it and add the cases this bench lacks. Otherwise take the user's evals: a project harness (e.g. `evals/<x>/run.py`) runs the installed skill, not a variant, so port its cases. With neither, draft one case per **branch** of the skill, a situation it handles differently from the others. Read the whole skill, its sibling files and scripts first: the branches, the skills it calls and the paths it writes live there.

Shape each case to where its branch's behaviour shows:

- **First turn**: a single `prompt`.
- **Later turns**, a skill that asks and waits: `turns` scripts the user's replies, each one an answer that fits any question the skill could reasonably ask at that point.
- **Deep in a long run** (an orchestrator, a loop ending in a PR): a **decision-point** case. A fixture or `setup` leaves the repo as the earlier steps would, the prompt says where the run stands, a fake CLI logs the decision and a low `max_turns` ends the run once it's taken. One end-to-end case keeps the decision-point ones honest.
- **Judgement**, output no regex can grade: one `judge` check per unit, asking whether the agent did what the unit says.

Write each case's checklist now, before any run: checks on the target behaviour plus one that the task itself still got done. Note beside each check the units it defends (`bench.py units <SKILL.md>`). Prefer `regex` and `cmd` checks; a `judge` check costs a run.

- Open every prompt with `/<name>`, so a cut body can't hide behind the skill not loading.
- A case whose task reaches outside (GitHub, Slack, a deploy, `open`, another model's CLI) gets a fake CLI in `path_prefix` that logs what it would have sent to `$BENCH_REPO`, and its checks read that log. Children run in `auto` permission mode, the only mode where their Bash works under `claude -p`.
- The child sees only the skill under test. Skills it calls go in `with`; otherwise every case runs the skill's missing-dependency branch.
- A skill that writes under `$HOME` or another fixed path gets that path pointed at `$BENCH_REPO` through `env`. When the skill hardcodes the path, a run writes to the user's real files: propose an env var for it to the user before any run.
- A branch no case can reach (a live service no fake stands in for, a run that costs more than its cut could save) is **unbenchable**: name it and why. When every branch is, stop and report that.
- Bench on the model the skill runs on in practice, or on the session's model when that is unknown. The result holds for that model only.

Save the cases to `evals/<name>/` before the first run.

Send the user one message: the cases with their checklists, the model, and the worst-case run estimate: `cases × runs` for bare, full, each section and the combined variant, plus `defending cases × runs` for every unit. Wait for their go. When they set a cap below it, drop the cases that defend the fewest units first.

## 2. Bare and full

```bash
python3 bench.py run --skill none     --cases <repo>/evals/<name>/cases.json --out runs/bare
python3 bench.py run --skill <skill-dir> --cases <repo>/evals/<name>/cases.json --out runs/full
```

- When a check is red on full, read its transcript (`runs/full/<case>-<n>/transcript.txt`). Fix a harness fault (a fake that lost its log, a bad `setup`) and rerun. When the case or the skill is broken, stop the bench and take it to the user.
- A check green on bare in every run defends nothing; any cut keeps it green. Sharpen the case until bare fails it, or drop it from the verdicts and say so.

Done when every check is green on full in every run and red on bare in at least one.

## 3. Delete one, coarse to fine

Build one variant per section (`bench.py variant <skill-dir> --drop S<n> --out variants/S<n>`) and run it on every case. In each section whose drop fails a check, build one variant per unit and run it on the cases that defend it. Drop one unit per variant, since a variant missing several units only says one of them mattered. Headings aren't units; a section's heading goes when its last unit does.

Sort every unit into:

- **load-bearing**: dropping it turns a check red. Name the check.
- **no-op**: dropping it keeps green every check that defends it.
- **uncovered**: no check defends it, so it gets no run and the bench is silent on it. Find why it's there (`git log -S`, the skill's history) and offer a case that would test it.

Done when every unit has its label.

## 4. Combined

Drop every no-op at once and run the result with `--runs 3`. Cuts interact, and two lines that restate each other are each a no-op alone. If a check goes red, put back the no-ops that check defends, one per rerun, until the combined variant is green; each one put back is load-bearing in company. Done when it is green in every run.

## 5. Report

- A table: variant, words, passes per case as `x/runs`. Where two variants' ranges overlap, say the bench can't separate them.
- The trimmed `SKILL.md` (original minus the confirmed no-ops), its path, and words before and after.
- The load-bearing, no-op and uncovered lists, each unit with the check it hinged on.
- Limits: the model, the runs per arm, the unbenchable branches and the ones no case covers yet.

Leave the original as it is. Offer to apply the trimmed version or to cut the uncovered units after a case covers them.
