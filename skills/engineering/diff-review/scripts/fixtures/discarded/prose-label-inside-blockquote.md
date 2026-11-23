### 1. src/cart.spec.ts:46: `RejectedAgent` copies `BlockedAgent` almost line for line

Cost: two fakes drift apart the next time the agent's constructor changes.

Fix: one factory that takes the fetch stub.

> ```ts
> class RejectedAgent extends Agent {
>   constructor(code: string) {
>     super(fakeModel({ fetch: rejection(code) }), logger);
>   }
> }
> ```
>
> (`BlockedAgent`, line 31:)
>
> ```ts
> class BlockedAgent extends Agent {
>   constructor() {
>     super(fakeModel({ fetch: blockedResponse }), logger);
>   }
> }
> ```

END OF ROUND
