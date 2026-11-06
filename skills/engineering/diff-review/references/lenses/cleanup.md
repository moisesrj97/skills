# Lens: cleanup

You look for code that works but costs: knowledge written twice, elements nobody needs, intent the reader has to dig for, work done for nothing. Bugs belong to the `code` lens, and comments to `comment-cleanup`, so leave both out.

Apply every rule of the standards in the brief to every hunk of the diff. They rank the angles, and a lower rule never wins over a higher one. Without standards, use reuse (grep the shared modules and the files next to the change for a helper that already does it) and simplification (derivable state, copy-paste with small variations, deep nesting, dead code).

Then **efficiency**, which no design rule covers: repeated computation or I/O, independent operations run one after another, blocking work added to startup or a hot path, and a long-lived object built from a closure, which keeps its whole enclosing scope alive (a class that copies only the fields it needs avoids it).

Every finding names the concrete fix (the helper to call, the simpler form, the cheaper alternative), and the fix must keep behaviour exactly as it is. A cleanup that changes behaviour, even one that looks harmless (`||` to `??`, a reordered side effect), is not a cleanup.

You are done when every rule and efficiency have covered every hunk.

## Fields

```markdown
Rule: <the standard or angle it breaks>

Cost: <what is duplicated, wasted or harder to read or change>

Fix: <the concrete change>
```

Most costly first.
