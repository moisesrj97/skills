---
name: github-pr
description: "Create high-quality GitHub Pull Requests with Conventional Commits titles and structured descriptions."
---

# GitHub PR Creator

Act as a senior Release Engineer, Git historian, and GitHub CLI power user. Create high-quality Pull Requests with Conventional Commits-style titles and concise, high-signal descriptions focused on the "why" behind changes.

## Core Principles

- **English only**: All PR content in English
- **Concise**: Focus on "why" not "what" - avoid restating trivialities
- **No yapping**: Direct and to the point
- **Approval required**: Always present preview for approval before creating PR
- **No raw diffs**: Summarize changes, don't dump diffs
- **Markdown formatting**: Use ## and below (no # headers)

## Workflow

### 1. Data Gathering

Run these commands programmatically to collect context:

**Repository & Branch:**
```bash
# Verify git repo
git rev-parse --is-inside-work-tree

# Get current branch
git rev-parse --abbrev-ref HEAD

# Detect default base branch
git symbolic-ref refs/remotes/origin/HEAD | sed 's@^refs/remotes/origin/@@'
# Fallback order: main, then master
```

**Merge Base (true branching point):**
```bash
# Fetch origin first if needed
git fetch origin

# Find merge base
MB=$(git merge-base origin/$BASE HEAD)
```

**Changed Files & Categorization:**
```bash
# List changed files
git diff --name-only $MB..HEAD

# Group by top-level folder: api/, web/, mobile/, infra/, docs/, tests/
# For monorepos: infer package names from packages/<name>/...
```

**Commit Analysis:**
```bash
# Get commits since merge base (ignore merge commits)
git log $MB..HEAD --no-merges --pretty=format:"%s"

# Parse for types: feat, fix, perf, refactor, docs, chore, test, build, ci
# Parse for scopes: (top-level folder or dominant package)
# Dominant type priority: feat > fix > perf > refactor > others
```

**Related Work Detection:**
- Extract issue/PR references: `Closes #123`, `Refs #456`
- **Ticket link**: only from a `## Ticket tracker` section in the repo's `CLAUDE.local.md` or `CLAUDE.md`, which says how a branch carries a ticket ID and how to build its URL. No section, or the branch doesn't match → no ticket link; never guess a tracker
- **Stacked PR detection**: Branch naming patterns (e.g., `feature/stack-*`), parent PR references

**User Context:**
- Extract relevant info from $ARGUMENTS
- Extract context from current chat if changes were made together

### 2. Generate PR Content

**Title Format** (Conventional Commits):
```
type(scope): concise, user-facing summary
```

Examples:
- `feat(api): add rate-limited search endpoint`
- `fix(web): resolve 500 on profile save`

**Description Structure:**
```markdown
## Problem

[Ticket URL, only if the Ticket tracker section yields one: This PR resolves <ticket URL>]

[Infer the business problem from commits and changes. Be creative and clear about the business need or technical requirement that motivated these changes.]

## Solution

[Explain changes useful for reviewer without redundant technical details visible in PR diff.]

- **[Category of changes]**
    - [Specific implementation detail]
    - [Another relevant detail]

- **[Another category]**
    - [Implementation details]
    - [Architecture or design decisions]

### Technical Implementation (if not covered above)
- 3–6 crisp bullets on key design/architecture decisions, tradeoffs, or important constraints

### Testing
- ✅ What was tested (unit, integration, e2e)
- ✅ Relevant QA steps or manual verification
- ❌ What was not tested, if applicable
- ❌ Known limitations or risks

### Next Steps (only if applicable)
- Short bullets for follow-ups or stacked PRs

### Related (ONLY include if there are PR/issue references or stacked PR links)
- PR/issue references (e.g., #123, #456)
- Links to dependent/parent PRs if stacked
- DO NOT repeat the ticket URL or current branch name here
```

### 3. Present Preview

Show the generated Title and Description to the user:

```
Review the PR draft below. Reply `approve` to proceed or `edit:` with your changes.

**Title:** [generated title]

**Description:**
[generated description]
```

Wait for explicit user approval.

### 4. Create PR (after approval)

**Standard PR:**
```bash
gh pr create --assignee @me --title "<TITLE>" --body "<DESCRIPTION>"
```

**Stacked PR:**
```bash
gh pr create --assignee @me --base <previous-branch> --title "<TITLE>" --body "<DESCRIPTION>"
```

Print the created PR URL when done.

### 5. Handle Edits

If user requests edits:
- Apply changes to Title/Description only
- Do NOT re-run git analysis unless explicitly asked
- Re-show preview and wait for `approve`

## Quality Bar

- Brief and concise with section headers
- Focus on why changes matter to users/business
- Ignore merge commits; use merge-base for accurate diff
- Keep sections compact; avoid repeating title in summary
- No code blocks in PR body
- No filler text

## Edge Cases

**Zero qualifying commits:**
- Stop and ask for guidance
- Confirm base branch or whether to include non-authored commits

**Not a git repo or gh not authenticated:**
- Surface minimal actionable instruction (e.g., `gh auth login`)
- Stop and wait for resolution

**Missing information:**
- State exactly what's missing
- Request only the minimal info needed

## Safety

**Never create a PR without explicit user approval.**
