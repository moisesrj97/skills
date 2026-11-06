# Tidy First: catalogue and rules

From Kent Beck, *Tidy First?* (2023). [`SKILL.md`](SKILL.md) says when to tidy and where each tidying goes.

## Catalogue

Each tidying takes minutes and preserves behaviour.

- **Guard clauses**: preconditions become early returns, so the main path reads unnested.
- **Dead code**: delete code nothing calls. Version control keeps it.
- **Normalize symmetries**: the same thing done one way everywhere, so a reader sees real differences instead of accidental ones.
- **New interface, old implementation**: write the interface the change wishes it had, implemented by calling the old one; callers migrate to it.
- **Reading order**: reorder a file so a reader meets each element where they need it.
- **Cohesion order**: elements that change together sit together, in one file or next to each other in it.
- **Declaration and initialization together**: a variable is declared where it gets its value.
- **Explaining variable**: a subexpression with a meaning gets a named variable.
- **Explaining constant**: a literal with a meaning gets a named constant.
- **Explicit parameters**: a routine receives what it uses instead of reading it from a bag of options, a global or the environment.
- **Chunk statements**: a blank line between the parts of a block that do different things.
- **Extract helper**: a block with one purpose becomes a function named for it.
- **One pile**: code split so finely that the logic hides is inlined back into one place, read whole, then split along the lines that make sense.
- **Explaining comment**: record what you had to learn to change the code, the non-obvious "why".
- **Delete redundant comment**: delete a comment that restates the code.

## Rules

- **Small batches**: tidyings chain (a guard clause exposes an explaining variable, which exposes a helper). Stop the chain once the behaviour change is easy, before the code is perfect.
- **One kind per commit** when the batch is large: a reviewer scans "rename X to Y across 12 files" in seconds, and a mix of five kinds in minutes.
- **Coupling is the target**: tidy first what cuts the coupling the behaviour change would otherwise work across.
- **Structure and behaviour never share a commit.** A tidying commit keeps tests green and assertions intact. A test may follow a rename or move (an import path, a symbol's name); needing a different assertion makes it a behaviour change.
