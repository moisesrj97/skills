# Simple design: the four rules

Kent Beck's rules for simple design, in priority order. A higher rule wins over a lower one. Source: https://martinfowler.com/bliki/BeckDesignRules.html

1. **Passes the tests.** The code works as intended. Tidying keeps behaviour exactly as it is, with the tests green and assertions intact. A change that alters behaviour, however small, is not a tidying.
2. **Reveals intention.** A reader sees what the code is for without reconstructing it: names, guard clauses, explaining variables, reading order.
3. **No duplication.** Every piece of knowledge lives in one place (once and only once). Look for the hidden kinds too: copy-paste with small variations, parallel structures that change together, a helper the codebase already has that new code re-implements. Grep the shared modules and the files next to the change before calling something new.
4. **Fewest elements.** Anything that serves none of the rules above goes: dead code, flexibility added for a future that hasn't come, an abstraction with one user, a special case layered on a shared mechanism where a change to the mechanism would serve every case.

## When rules pull against each other

- **2 and 3 refine each other.** When removing duplication makes the code harder to read, the reader wins. In tests especially, a repeated setup that keeps each test readable on its own stays.
- **4 limits tidying itself.** A helper extracted for its own sake is one more element. When splitting hides the logic, put it back in one pile (`tidy-first.md`).
