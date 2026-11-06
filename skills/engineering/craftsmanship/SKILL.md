---
name: craftsmanship
description: "Kent Beck's Tidy First, simple design and Test Desiderata as working rules for tidying around a behaviour change and trading test properties. Use before or after a behaviour change, when choosing test seams, or to review, simplify or tidy a diff."
---

# Craftsmanship

Three practices from Kent Beck: **Tidy First?** for the structure of the code a change touches, the **rules of simple design** for judging that structure, and **Test Desiderata** for the tests that guard it. Callers use the section their step needs. Reviewers get the reference files as standards.

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

## Simple design

Four rules in priority order: passes the tests, reveals intention, no duplication, fewest elements. They decide which tidyings are worth making and which one wins when two pull against each other. Read them, with how each applies, in [`simple-design.md`](simple-design.md).

## Tidy a diff

Simplifies a change's code after the behaviour works, with a reviewer outside your context, since an author misses their own duplication.

1. Call the Skill tool with `diff-review` with `lens=cleanup` over the change's range (with uncommitted work, `diff`), and `standards=` the absolute paths of `tidy-first.md` and `simple-design.md` in the folder this skill loaded from. One round.
2. Place each finding: **Apply** when it keeps behaviour and touches only files the behaviour change needs; **post-PR** or **Later** by the area-of-impact table above; **Skip** when it would change behaviour or is wrong, with a one-line reason. Done when every finding has a place.
3. Apply in `refactor:` commits apart from behaviour, one kind per commit when the batch is large, with the tests green after each. When no test covers the code a tidying touches, say so in the report.
4. Report what was applied, moved to post-PR or Later, and skipped with why.

## Test Desiderata

Twelve properties of a good test, defined with their trade-offs in [`test-desiderata.md`](test-desiderata.md): isolated, composable, deterministic, fast, writable, readable, behavioral, structure-insensitive, automated, specific, predictive, inspiring. No test has all twelve at full strength. A test gives up a property only to buy another.

- **Choosing a seam**: name what each proposed seam buys and what it sells, e.g. "HTTP-level test on the endpoint: predictive and structure-insensitive; sells fast and specific".
- **Reviewing a test**: a finding is a property sold with nothing bought, e.g. a mocked clock nobody needed that makes the test less predictive.
