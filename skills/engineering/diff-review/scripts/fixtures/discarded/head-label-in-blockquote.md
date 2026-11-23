### 1. src/flows.ts:684: the step list is built twice with the same filter

Cost: a new step has to be added in both places.

Fix: build it once in `stepsFor` and pass it down.

> flows.ts:296-297 (head)
> const steps = all.filter((step) => step.enabled);
> const names = steps.map((step) => step.name);

> flows.ts:684-685 (head)
> const enabled = all.filter((step) => step.enabled);
> report(enabled.map((step) => step.name));

END OF ROUND
