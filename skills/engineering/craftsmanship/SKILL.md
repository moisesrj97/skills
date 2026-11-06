---
name: craftsmanship
description: "Kent Beck's Tidy First and Test Desiderata as working rules for when and where to tidy around a behaviour change and which test properties to trade. Use before or after a behaviour change, when choosing test seams, or reviewing a diff's structure or tests."
---

# Craftsmanship

Two practices from Kent Beck, **Tidy First?** for the structure of the code a change touches and **Test Desiderata** for the tests that guard it. Callers use the section their step needs. Reviewers get the two reference files as standards.

## Tidy First

A **tidying** is a small structural change that preserves behaviour, committed apart from any behaviour change as a `refactor:`. Read the catalogue and its rules in [`tidy-first.md`](tidy-first.md) before tidying.

### When

The title carries a question mark because tidying is a decision taken per change.

- **First**: the tidying makes the behaviour change easier. Make the change easy, then make the easy change.
- **After**: the behaviour change left the code harder to read than before. Polishing the change's own new code is the refactor step of red-green-refactor and always lands here.
- **Later**: worth doing but unrelated to this change. Leave the code untouched and add the tidying to a list for the report.
- **Never**: code nobody will change again.

When unsure, leave the code as it is, since an unneeded tidying is more diff for a reviewer to read.

### Where: by area of impact

The **area of impact** is the set of files a tidying touches, compared with the files the behaviour change needs. A tidying is **mechanical** when an IDE refactoring or a codemod could do it: rename, move, extract, inline, reorder.

| Tidying | First | After |
|---|---|---|
| Touches only files the behaviour change needs | first `refactor:` commit of the PR | `refactor:` commit after the behaviour, same PR |
| Mechanical, reaches files the behaviour change doesn't need | **pre-PR**: branch `<branch>-tidy-first` off the base; the main branch stacks on it | **post-PR**: branch `<branch>-tidy-after` stacked on the main branch |
| Changes design or interfaces beyond the behaviour change | not a tidying. Later, or a question for the user when the change can't land without it | Later |

## Test Desiderata

Twelve properties of a good test, defined with their trade-offs in [`test-desiderata.md`](test-desiderata.md): isolated, composable, deterministic, fast, writable, readable, behavioral, structure-insensitive, automated, specific, predictive, inspiring. No test has all twelve at full strength. A test gives up a property only to buy another.

- **Choosing a seam**: name what each proposed seam buys and what it sells, e.g. "HTTP-level test on the endpoint: predictive and structure-insensitive; sells fast and specific".
- **Reviewing a test**: a finding is a property sold with nothing bought, e.g. a mocked clock nobody needed that makes the test less predictive.
