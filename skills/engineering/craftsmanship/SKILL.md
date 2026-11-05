---
name: craftsmanship
description: "Kent Beck's Tidy First and Test Desiderata as working rules: whether and where a tidying goes (first commit, pre-PR, after commit, post-PR or later) by its area of impact, and the twelve test properties to trade when choosing test seams or reviewing tests. Use before or after a behaviour change, when choosing where tests go, when reviewing a diff's structure or tests, or when another skill calls for it."
---

# Craftsmanship

Two practices from Kent Beck: **Tidy First?** for the structure of the code a change touches, **Test Desiderata** for the tests that guard it. Callers use the section their step needs; reviewers get the two reference files as standards.

## Tidy First

A **tidying** is a small structural change that preserves behaviour: the catalogue and its rules are in [`tidy-first.md`](tidy-first.md), read before tidying. Structure and behaviour never share a commit. A tidying commit is a `refactor:` that passes the existing tests with every assertion intact: it may follow a rename or move into a test (an import path, a symbol's name), and a commit that changes what a test asserts changed behaviour.

### When

The title carries a question mark: tidying is a decision, taken per change.

- **First**: the tidying makes the behaviour change easier. Make the change easy, then make the easy change.
- **After**: the behaviour change left its code harder to read than it found it. Polishing the change's own new code is the refactor step of red → green → refactor and always lands here.
- **Later**: worth doing, unrelated to this change. It goes on a list for the report, untouched.
- **Never**: code nobody will change again.

When unsure, leave the code as it is: an unneeded tidying is diff for a reviewer to read.

### Where: by area of impact

The **area of impact** is the set of files a tidying touches, compared with the files the behaviour change needs. A tidying is **mechanical** when an IDE refactoring or a codemod could do it: rename, move, extract, inline, reorder.

| Tidying | First | After |
|---|---|---|
| Touches only files the behaviour change needs | first `refactor:` commit of the PR | `refactor:` commit after the behaviour, same PR |
| Mechanical, reaches files the behaviour change doesn't need | **pre-PR**: branch `<branch>-tidy-first` off the base; the main branch stacks on it | **post-PR**: branch `<branch>-tidy-after` stacked on the main branch |
| Changes design or interfaces beyond the behaviour change | not a tidying: Later, or a question for the user when the change can't land without it | Later |

## Test Desiderata

Twelve properties of a good test, defined with their trade-offs in [`test-desiderata.md`](test-desiderata.md): isolated, composable, deterministic, fast, writable, readable, behavioral, structure-insensitive, automated, specific, predictive, inspiring. No test has all twelve at full strength: a test gives up a property only to buy another.

- **Choosing a seam**: name what each proposed seam buys and what it sells, e.g. "HTTP-level test on the endpoint: predictive and structure-insensitive; sells fast and specific".
- **Reviewing a test**: a finding is a property sold with nothing bought, e.g. a mocked clock nobody needed that makes the test less predictive.
