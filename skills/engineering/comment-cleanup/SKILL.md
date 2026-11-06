---
name: comment-cleanup
description: >-
  Prunes the comments and JSDoc a change added or modified to the few a reader
  needs, and rewrites unclear code so it explains itself. Use when asked to
  clean up or trim comments, and as the final pass after implementing a change,
  before committing.
---

# Comment cleanup

First drafts narrate, especially ones written while reasoning out loud. Comments are not compiled or tested and rot when the code moves, so each one you keep must buy something the code cannot say. Remove the narration before the change lands.

## 1. Find the comments in scope

Scope is the comments this change added or modified. Leave pre-existing ones unless the user asks for a wider sweep.

```bash
base=$(git symbolic-ref --short refs/remotes/origin/HEAD 2>/dev/null) \
  || base="origin/$(gh repo view --json defaultBranchRef -q .defaultBranchRef.name)"
git diff --merge-base "$base" -U0 -- . ':!*.md' ':!*.lock' ':!*-lock.*' | awk '
/^\+\+\+ b\// { file=substr($0,7) }
/^@@/ { match($0, /\+[0-9]+/); n=substr($0, RSTART+1, RLENGTH-1) }
/^\+/ && !/^\+\+\+/ { l=$0; sub(/^\+/,"",l); if (l ~ /^[ \t]*(\/\/|\/\*|\*|#|--|<!--)/) print file":"n": "l; n++ }'
```

It covers every language whose comments start with `//`, `/*`, `#`, `--` or `<!--`, and skips Markdown and lockfiles. For a language with another marker, add it to the pattern.

Swap the base for whatever the change is measured against (`HEAD`, `--staged`, a commit). The script catches comment-only lines, so also skim the diff for trailing comments (`doThing(); // why`) and doc blocks an edit shifted. Then open each file, because a comment can only be judged next to its code.

Done when you have every in-scope comment and have read each one beside its code.

## 2. Judge each one by what a reader loses without it

- **Nothing, because the code already says it.** Delete. Most comments land here.
- **Why the code is like this.** Keep it and condense it. Rationale, a rejected alternative, an external constraint, an ordering requirement, a deliberate fail-open, a ticket deferral, a workaround for someone else's bug. Reading the code recovers none of these.
- **What the code does.** The code is unclear. Fix the code (step 4), then delete the comment.

Recognise these on sight and cut them: restatements of a name or type (`/** The session id. */`), narration of the next line, section banners (`// --- Helpers ---`), `// Arrange / // Act / // Assert`, changelog notes about the change itself (`// added this to fix the crash`), and commented-out code.

- **Match the siblings.** A JSDoc block on one new member of an interface whose siblings have none goes. If every method in the file has a full JSDoc block, the new method without one is the inconsistency.
- **Uncertainty argues for keeping.** Keep a comment that claims a constraint you cannot verify. Deleting a true warning costs far more than leaving a stale line. Rewrite a comment only into claims you have confirmed.

Done when every in-scope comment has a verdict.

## 3. Condense the keepers

A keeper is one line, two at most, and states the constraint. The code below it is the mechanism. Cut the hedging, the recap, and any second half that re-explains the first.

Before:

```ts
// Runs from before versioning overwrote a single artifact at the root, and the import minted a
// version of its own rather than reusing the run that wrote it: nothing below the import has an
// annotation left to read or to publish. `runs` is descending, so this is the highest import.
// Sound only because the migration refuses to import the root over a run that wrote a folder of
// its own; otherwise a re-annotated legacy Design would hide a version that is there.
```

After:

```ts
// Pre-versioning runs shared one root artifact that the import consumed, so nothing below the
// highest import (`runs` is descending) still has an annotation to publish.
```

## 4. When the code needs the comment, change the code

Prefer this over keeping a "what" comment. The compiler checks a good name, and the name travels with the call sites. Keep behaviour identical and the edit small:

- rename a variable, function or parameter to say what the comment said
- extract a magic number, regex or string into a named constant
- extract a commented block into a helper whose name is the comment
- replace a positional boolean with a named argument or a union type
- narrow a type so an "assumes X" comment becomes unrepresentable

If the code needs a real refactor to explain itself (moving responsibilities, changing a signature used across modules), keep the comment and say so. A cleanup pass leaves the design as it is.

## 5. Keep the comments that are code

Tools read these, so they stay:

- linter and compiler directives: `eslint-disable*`, `biome-ignore`, `@ts-expect-error`, `@ts-ignore`, `prettier-ignore`
- coverage pragmas: `istanbul ignore`, `c8 ignore`, `v8 ignore`
- bundler magic comments: `/* webpackChunkName: … */`, `/* @vite-ignore */`, `/*#__PURE__*/`
- `/** @jsxImportSource … */`, license and copyright headers, generated-file banners
- annotations a tool reads: OpenAPI/Swagger blocks, decorators' docs, i18n extraction hints
- `@deprecated` and `@see` tags pointing at a replacement

Give a `@ts-expect-error` that lacks a reason a one-line reason. It is the rare case where this pass adds a comment.

## 6. Apply, verify, report

Apply the edits. If step 4 renamed anything, grep the repo for the old name and run the touched package's typecheck (`yarn tsc --noEmit` or the package's own script) and its tests. Renames break call sites, and comment deletions do not.

Report tersely:

- per file, how many comments you cut and how many you condensed
- every surviving comment, one line each. This list is the point of the report. It lets the user veto a keeper and makes an over-eager deletion visible.
- anything you kept because you could not verify it, and any step 4 code change you declined

Done when the edits are applied, any rename leaves no old name behind and passes typecheck and tests, and the report lists every surviving comment.
