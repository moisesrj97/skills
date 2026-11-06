# Lens: code

Every finding is a **failure scenario**: a concrete input, state or sequence of calls, and the wrong result it produces. Without a scenario there is no finding. Read past the diff (callers, callees, the tests, the code it replaced) to find them, along these angles:

- **Correctness**: logic that is wrong for some input or state, in the changed lines and in the unchanged lines of every function the diff touches, since the change re-exposes them. Try to break it with empty, zero and negative values, missing optional fields, null, off-by-one bounds, implicit coercions, error paths, and repeated or concurrent calls.
- **Removed behaviour**: for every line the diff deletes or replaces, name what it enforced (a guard, an error path, a validation, a case a deleted test covered), then find where the new code enforces it again. Not finding it is a finding.
- **Contracts**: for every changed function, type, API, CLI flag or config key, grep its callers and consumers and check each one against the change: a new precondition, a changed return shape, a new exception, an ordering it now depends on, a doc or instruction that describes the old behaviour.
- **Fixes**: when the change fixes a bug, whether it covers the reported case and the same bug's other paths.
- **Spec**: with a spec in the brief, every acceptance criterion it states, and anything the diff does that it doesn't ask for. The scenario is "the spec asks X; with this input the code does Y".
- **Conventions**: the `CLAUDE.md` and `CLAUDE.local.md` at the repo root and in each directory above a changed file, plus the standards in the brief. A breach quotes the rule, names its file, and quotes the line that breaks it.
- **Security and data**: injection, leaked secrets, missing authorisation, data loss, irreversible actions taken without a guard, each with a concrete scenario. Weighing exploitability against exclusions is the `security` lens's job.
- **Tests**: a test that stays green with the bug it claims to guard, and a changed branch no test exercises.

Leave out style, naming, formatting, anything a linter catches, and design alternatives with no failure scenario.

Then **sweep for gaps**: one more pass over the whole scope, looking only for what the angles tend to miss. Moved code that lost a guard on the way, a setup without its teardown, a config default inverted, a lock or transaction whose scope shrank, a default value created once and shared between calls, a wrapper that forwards to the wrong object.

You are done when every angle and the sweep have covered every change in the scope.

## Fields

```markdown
Severity: <P0–P3>

Verdict: <CONFIRMED | PLAUSIBLE>

Confirm by: <what would confirm it; PLAUSIBLE only>

Scenario: <input or state → wrong result>
```

The severity follows the scenario:

- **P0**: data loss, a security hole, or a crash on the main path.
- **P1**: wrong behaviour in a common case, or a spec criterion missing.
- **P2**: wrong behaviour in an edge case.
- **P3**: a real but minor defect, or a conventions breach.
