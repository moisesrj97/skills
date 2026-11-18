---
name: minimoi
description: "Takes a trivial ticket to a PR with megamoind's reduced flow: inline, one review round, no agents or tidy layers."
disable-model-invocation: true
argument-hint: "[ticket ID] [base=<branch>]"
---

# Minimoi

The reduced flow lives beside megamoind, in `../megamoind/MINIMOI.md` (the `megamoind` skill folder next to this one). Read it now.

1. **Ticket**: with no ticket in the request, get one as megamoind's step 0 does (give the ID or create it). Fetch and read it, and read the code it touches.
2. **Eligibility**: check the change against every condition in MINIMOI.md's "Eligibility". When one fails, edit nothing: name the condition it fails and point the user to `/megamoind <ticket>`, then end the turn.
3. **Run**: follow MINIMOI.md's "Flow" from step 0 as a direct run; `base=` means what it means in megamoind's "Arguments".
