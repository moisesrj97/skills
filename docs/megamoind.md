# Megamoind flows

Reference diagrams for [`megamoind`](../skills/engineering/megamoind/SKILL.md) and [`megamoind-spec`](../skills/engineering/megamoind-spec/SKILL.md). The `SKILL.md` files are the source of truth; update these diagrams when a step changes.

## megamoind: one ticket

```mermaid
flowchart TD
    start(["/megamoind &lt;ticket&gt;"]) --> brief{"brief= given?"}
    brief -- no --> s0["0. Brief and HITL check<br/>plan, branch, base, verification, CODEOWNERS<br/>one round of questions"]
    brief -- yes --> s1
    s0 --> s1["1. Branch<br/>GitButler or git"]
    s1 --> s2["2. Implement<br/>mattpocock-skills:tdd, gates green"]
    s2 --> s3["3. Quick review<br/>mattpocock-skills:code-review<br/>standards + spec, base...HEAD"]
    s3 --> s4["4. Pair review<br/>pair-review base...HEAD high<br/>fix, re-review until done"]
    s4 --> s5["5. Verify in the real app<br/>browser (frontend) or debug-trace (backend)"]
    s5 --> s6["6. Comment cleanup<br/>commit, gates"]
    s6 --> draft{"stop-at=draft?"}
    draft -- no --> s7r["7. PR ready for review<br/>github-pr, full CI starts"]
    draft -- yes --> s7d["7. PR as draft"]
    s7r --> s8["8. CI loop<br/>fix / re-run flaky / HITL if red on base<br/>HITL after 3 failed fix pushes"]
    s7d --> s8
    s8 --> s9["9. Report"]
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

## megamoind-spec: a whole spec

```mermaid
flowchart TD
    start(["/megamoind-spec &lt;spec&gt;"]) --> s0["0. Read the spec<br/>tickets, GitButler workspace clean"]
    s0 --> s1["1. Plan<br/>chains from blocking relations,<br/>shared files in one chain,<br/>one brief per ticket, one round of questions"]
    s1 --> s2["2. Prepare<br/>but pull once, start shared dev servers"]
    s2 --> s3

    subgraph s3["3. Run the chains (max 3 agents at once)"]
        direction TD
        pick["Start bottom ticket of each chain<br/>base = default branch"] --> agent["megamoind &lt;ticket&gt; base=… brief=… stop-at=draft<br/>(Herdr pane / T3 child / subagent)"]
        agent --> report{"report sealed<br/>END OF REPORT?"}
        report -- "open HITL" --> ask["Ask the user,<br/>chain waits"]
        ask --> agent
        report -- ok --> next{"next ticket<br/>in chain?"}
        next -- yes --> stack["Start it with<br/>base = branch just finished"]
        stack --> agent
        next -- "no, slot free" --> pick
        agent -. "needs lower-layer change" .-> lower["Lower layer's agent commits it,<br/>GitButler restacks, but push,<br/>tell the agent its base moved"]
        lower -.-> agent
    end

    s3 --> s4["4. All ready<br/>every draft green → gh pr ready,<br/>bottom of each chain first"]
    s4 --> ci{"all checks green?"}
    ci -- no --> fix["Red check → owning agent fixes,<br/>push the stack<br/>HITL after 3 rounds"]
    fix --> ci
    ci -- yes --> s5["5. Wrap up<br/>close panes / cancel children,<br/>stop servers, report table"]
    s5 --> s6["6. Reviewers<br/>only after explicit yes"]
    s6 --> done([done, user merges by hand])
```
