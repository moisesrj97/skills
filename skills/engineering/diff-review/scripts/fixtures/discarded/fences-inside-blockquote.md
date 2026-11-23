### 1. src/cart.spec.ts:12: the new assertion casts the result to reach a private field

Severity: P3

Verdict: CONFIRMED

Scenario: renaming `_meta` compiles, and the test fails at runtime instead of at type-check.

> ```ts
>   it('sends the source under its new name', async () => {
>     const sent = dataOf(await total(items)) as {
>       _meta: Record<string, unknown>;
>     };
>
>     expect(sent._meta.source).toBe('design-1');
>   });
> ```
> ```ts
> const dataOf = (value: unknown): unknown => {
> ```

END OF ROUND
