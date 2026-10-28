---
name: comment-cleanup
description: >-
  Prunes the comments and JSDoc a change added or modified down to the minimum a
  reader actually needs, rewriting unclear code so it explains itself instead of
  being narrated.

  Use this skill whenever the user asks to clean up, reduce, trim, review or
  remove comments or JSDoc — including phrasings like "revisa los comentarios",
  "elimina los comentarios redundantes", "resume los comentarios", "el código
  debería ser autoexplicativo", "too many comments", "drop the JSDoc", "make
  this self-documenting" — and run it proactively as the final pass after
  implementing a feature or before committing, since added comments are almost
  always over-written on the first draft.
---

# Comment cleanup

Comments are the least reliable part of a codebase: they are not compiled, not tested, and they
rot the moment the code moves. Every one you keep is a small permanent liability, so it has to
buy something the code cannot express on its own. This pass exists because first drafts —
especially ones written while reasoning out loud — narrate. The narration has to go before the
change lands.

## 1. Find the comments in scope

Only comments this change added or modified. Pre-existing ones are someone else's decision;
leave them unless the user asks for a wider sweep.

```bash
git diff --merge-base "$(git symbolic-ref --short refs/remotes/origin/HEAD)" -U0 -- '*.ts' '*.tsx' '*.js' | awk '
/^\+\+\+ b\// { file=substr($0,7) }
/^@@/ { match($0, /\+[0-9]+/); n=substr($0, RSTART+1, RLENGTH-1) }
/^\+/ && !/^\+\+\+/ { l=$0; sub(/^\+/,"",l); if (l ~ /^[ \t]*(\/\/|\/\*|\*|#)/) print file":"n": "l; n++ }'
```

Swap the base for whatever the change is measured against (`HEAD`, `--staged`, a commit). This
catches comment-only lines; trailing comments (`doThing(); // why`) and doc blocks that shifted
by an edit need a read of the diff itself, so skim it too. Then open each file — a comment can
only be judged next to the code it sits on.

## 2. Judge each one: what does a reader lose if it disappears?

- **Nothing — the code already says it.** Delete. This is the majority.
- **The reason it is like this.** Keep it, condensed. Rationale, a rejected alternative, an
  external constraint, an ordering requirement, a deliberate fail-open, a ticket deferral, a
  workaround for someone else's bug — none of that is recoverable by reading the code.
- **What the code does.** The comment is a symptom: the code is unclear. Fix the code (step 4),
  then delete the comment.

Recognise on sight and cut: restatements of a name or type (`/** The session id. */`), narration
of the next line, section banners (`// --- Helpers ---`), `// Arrange / // Act / // Assert`,
changelog notes about the change itself (`// added this to fix the crash`), commented-out code,
and a JSDoc block on one new member of an interface whose siblings have none.

Two judgment calls worth naming:

- **Match the surrounding convention, don't impose this one.** If every method in the file has a
  full JSDoc block, a new one without it is the inconsistency. Look at the siblings first.
- **Uncertainty argues for keeping.** If a comment claims a constraint you cannot verify, keep
  it. Deleting a true warning is far more expensive than leaving a stale line, and you must
  never rewrite a comment into a claim you have not confirmed.

## 3. Condense the keepers

A surviving comment should be one line, two at most, and should state the constraint rather than
walk through the mechanism — the code below it is the mechanism. Cut the hedging, the
recapitulation, and the second half that re-explains the first.

Before:

```ts
// Runs from before versioning overwrote a single artifact at the root, and the import minted a
// version of its own rather than reusing the run that wrote it: nothing below the import has an
// annotation left to read or to publish. `runs` is descending, so this is the highest import.
// Sound only because the migration refuses to import the root over a run that wrote a folder of
// its own — otherwise a re-annotated legacy Design would hide a version that is there.
```

After:

```ts
// Pre-versioning runs shared one root artifact that the import consumed, so nothing below the
// highest import (`runs` is descending) still has an annotation to publish.
```

## 4. When the code needs the comment, change the code

Prefer this over keeping a "what" comment — a good name is checked by the compiler and travels
with the call sites. Behaviour must stay identical, and the edit must stay small:

- rename a variable, function or parameter to say what the comment said
- extract a magic number, regex or string into a named constant
- extract a commented block into a helper whose name is the comment
- replace a positional boolean with a named argument or a union type
- narrow a type so an "assumes X" comment becomes unrepresentable

If making the code self-explaining needs a real refactor (moving responsibilities, changing a
signature used across modules), say so and leave the comment — a cleanup pass is not the place
to reshape a design.

## 5. Never delete these

They look like comments but are code:

- linter and compiler directives: `eslint-disable*`, `biome-ignore`, `@ts-expect-error`,
  `@ts-ignore`, `prettier-ignore`
- coverage pragmas: `istanbul ignore`, `c8 ignore`, `v8 ignore`
- bundler magic comments: `/* webpackChunkName: … */`, `/* @vite-ignore */`, `/*#__PURE__*/`
- `/** @jsxImportSource … */`, license and copyright headers, generated-file banners
- annotations a tool reads: OpenAPI/Swagger blocks, decorators' docs, i18n extraction hints
- `@deprecated` and `@see` tags pointing at a replacement

`@ts-expect-error` also deserves a one-line reason if it lacks one — that is the rare case where
this pass adds a comment.

## 6. Apply, verify, report

Apply the edits. If step 4 renamed anything, grep for the old name across the repo and run the
touched package's typecheck (`yarn tsc --noEmit` or the package's own script) plus its tests —
renames break call sites, comment deletions do not.

Then report tersely: per file, how many comments were cut and how many condensed, followed by a
flat list of every surviving comment as a single line each. The list is the point of the report —
it is the user's chance to veto a keeper, and it makes an over-eager deletion visible. Call out
separately anything you left because you could not verify it, and any code change you declined
to make in step 4.
