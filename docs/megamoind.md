# Megamoind flows

Reference diagrams for [`megamoind`](../skills/engineering/megamoind/SKILL.md) and [`megamoind-batch`](../skills/engineering/megamoind-batch/SKILL.md). The `SKILL.md` files are the source of truth; update these diagrams when a step changes.

## megamoind: one ticket

```mermaid
flowchart TD
    start(["/megamoind &lt;ticket&gt;"]) --> tid{"ticket ID given?"}
    tid -- yes --> brief{"brief= given?"}
    tid -- no --> ask["Ask: give the ID, or create it<br/>(in progress, assigned to the user)"]
    ask --> brief
    brief -- no --> s0["0. Brief and HITL check<br/>reuse search, craftsmanship, bug → diagnosing-bugs to phase 4<br/>plan (seams' Desiderata trade-offs, tidyings by area of impact),<br/>branch, base, verification, CODEOWNERS,<br/>required checks (draft / ready-only), gh for screenshots, brief to ticket?<br/>one round of questions, brief saved to a file"]
    brief -- yes --> fill["0. Settle what the brief leaves open<br/>reuse, tidyings, a bug's cause"]
    fill --> s1
    s0 --> s1["1. Branch<br/>GitButler or git, tidy-first pre-PR below if planned<br/>reinstall deps if the lockfile moved"]
    s1 --> s2["2. Implement<br/>tidy first (first commit or pre-PR)<br/>→ mattpocock-skills:tdd (bug: diagnosis loop is the first red, then its phase 6 cleanup)<br/>→ tidy after: craftsmanship's Tidy a diff, diff-review lens=cleanup<br/>(commit or post-PR above; else Later list)<br/>gates green; no tests in brief → failure-path checklist"]
    s2 --> s3["3. Security review<br/>diff-review lens=security, base...HEAD<br/>one round, fix with tests"]
    s3 --> s4["4. Pair review<br/>pair-review base...HEAD spec=brief standards=test-desiderata.md<br/>GPT reviewer via diff-review, fix, re-review until done"]
    s4 --> s5["5. Verify in the real app<br/>browser (frontend) or debug-trace (backend)<br/>injected states via fetch, screenshots for the PR"]
    s5 --> s6["6. Comment cleanup<br/>commit, gates"]
    s6 --> draft{"stop-at=draft?"}
    draft -- no --> s7r["7. One PR per layer, bottom first, ready for review<br/>merge-risk → github-pr (## Merge risk) + gh-attach screenshots,<br/>full CI starts"]
    draft -- yes --> s7d["7. One PR per layer, as drafts<br/>merge-risk → github-pr (## Merge risk)"]
    s7r --> s8["8. CI loop<br/>until every required check exists and is green<br/>(draft checks only with stop-at=draft;<br/>stacked layers: pending retarget)<br/>fix / re-run flaky / HITL if red on base<br/>HITL after 3 failed fix pushes"]
    s7d --> s8
    s8 --> s9["9. Report<br/>retro-with-docs first, then the report<br/>layers bottom to top with merge-risk color, Later tidyings<br/>report file written before any turn ends"]
    s9 --> stopdraft{"stop-at=draft?"}
    stopdraft -- no --> s10["10. Reviewers<br/>only after explicit yes"]
    stopdraft -- yes --> done([done])
    s10 --> done

    hitl[["HITL: user's decision<br/>or loop not converging"]]
    s0 -.-> hitl
    s4 -.-> hitl
    s5 -.-> hitl
    s8 -.-> hitl
```

## megamoind-batch: several tickets

```mermaid
flowchart TD
    start(["/megamoind-batch &lt;spec | tickets | query&gt;"]) --> s0["0. Read the tickets<br/>resolve the batch, comments for blockers,<br/>GitButler workspace clean"]
    s0 --> s1["1. Plan<br/>chains from blocking relations,<br/>shared files in one chain,<br/>one brief per ticket, one round of questions"]
    s1 --> s2["2. Prepare<br/>but pull once, reinstall deps,<br/>start shared dev servers"]
    s2 --> s3

    subgraph s3["3. Run the chains (max 3 agents at once)"]
        direction TD
        pick["Start bottom ticket of each chain<br/>base = default branch"] --> agent["megamoind &lt;ticket&gt; base=… brief=… stop-at=draft<br/>async: Herdr pane / T3 child / background subagent"]
        agent --> report{"report sealed<br/>END OF REPORT?"}
        report -- "open HITL" --> ask["Ask the user at once,<br/>chain waits, others keep running"]
        ask --> agent
        report -- ok --> next{"next ticket<br/>in chain?"}
        next -- yes --> stack["Start it with<br/>base = top layer just finished"]
        stack --> agent
        next -- "no, slot free" --> pick
        agent -. "needs lower-layer change" .-> lower["Lower layer's agent commits it,<br/>GitButler restacks, but push,<br/>tell the agent its base moved"]
        lower -.-> agent
    end

    s3 --> s4["4. All ready<br/>every draft green → but pull, but push,<br/>ask once + PushNotification → gh pr ready,<br/>bottom of each chain first"]
    s4 --> ci{"all checks green?<br/>(stacked layers: pending retarget)"}
    ci -- no --> fix["Red check → owning agent fixes,<br/>push the stack<br/>HITL after 3 rounds"]
    fix --> ci
    ci -- yes --> s5["5. Wrap up<br/>close panes / cancel children,<br/>stop servers, retro-with-docs, report table"]
    s5 --> s6["6. Reviewers<br/>only after explicit yes"]
    s6 --> done([done, user merges by hand])
```
