---
name: to-spec
description: Turn the current conversation into a spec and publish it to the project issue tracker, synthesizing what you've already discussed without interviewing the user.
disable-model-invocation: true
---

Write a spec from the current conversation and your understanding of the codebase. Synthesize what you already know instead of interviewing the user.

If you don't have the issue tracker and triage label vocabulary, tell the user to run `/setup-repo`.

## Process

1. Explore the repo to understand the current state of the codebase, if you haven't already. Use the project's domain glossary vocabulary throughout the spec, and respect any ADRs in the area you're touching.

2. Sketch out the seams at which you're going to test the feature. Prefer existing seams to new ones. Use the highest seam possible. If new seams are needed, propose them at the highest point you can. The fewer seams across the codebase, the better; the ideal number is one.

Check with the user that these seams match their expectations.

3. Write the spec using the template below, then publish it to the project issue tracker. Apply the `ready-for-agent` triage label; it needs no further triage.

<spec-template>

## Problem statement

The problem that the user is facing, from the user's perspective.

## Solution

The solution to the problem, from the user's perspective.

## User stories

A LONG, numbered list of user stories. Write each user story in this format:

1. As an <actor>, I want a <feature>, so that <benefit>

<user-story-example>
1. As a mobile bank customer, I want to see balance on my accounts, so that I can make better informed decisions about my spending
</user-story-example>

The list should cover every aspect of the feature.

## Implementation decisions

The implementation decisions made, such as:

- The modules that will be built/modified
- The interfaces of those modules that will be modified
- Technical clarifications from the developer
- Architectural decisions
- Schema changes
- API contracts
- Specific interactions

Leave out specific file paths and code snippets; they go stale fast.

Exception: if a prototype produced a snippet that encodes a decision more precisely than prose can (state machine, reducer, schema, type shape), inline it within the relevant decision and note briefly that it came from a prototype. Trim it to the parts that carry the decision, not a working demo.

## Testing decisions

The testing decisions made. Include:

- A description of what makes a good test (only test external behavior, not implementation details)
- Which modules will be tested
- Prior art for the tests (i.e. similar types of tests in the codebase)

## Out of scope

What this spec leaves out of scope.

## Further notes

Any further notes about the feature.

</spec-template>
