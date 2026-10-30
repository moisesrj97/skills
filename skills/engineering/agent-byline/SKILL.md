---
name: agent-byline
description: Byline that marks a GitHub PR comment, review or reply as written by an agent on the user's behalf. Use before posting any of them, whether the user asked for the text or another skill posts it.
---

# Agent byline

Every body you post to a pull request under the user's account opens with the byline, so the reader knows an agent wrote it: PR comments, review bodies, each inline review comment and each reply in a thread. GitHub shows each of these on its own, so each carries its own byline.

```md
> [!NOTE]
> 🤖 **<model> responding on behalf of <name>**

<the comment>
```

- `<model>`: the model you run on, named as your system prompt names it, with its family: `Claude Opus 5.5`, not `claude-opus-5-5` or `Claude`.
- `<name>`: the `name` field of `~/.config/moisesrj97-skills/agent-byline.json`. When the file is missing, ask the user which name to sign with and write `{"name": "<name>"}` there.

Write the byline in the comment's language (`🤖 **Claude Opus 5.5 respondiendo en nombre de <name>**`). A fresh review, or an approval with no text, takes the language of the PR description; an approval with no text gets the byline as its whole body.

## Posting

Write the body to a file and pass the file: `gh pr comment --body-file`, `gh pr review --body-file`, `gh api … -F body=@<file>`, or `gh api … --input <file>.json` for a review with inline comments. Through `-f body="…"`, a `\n` reaches GitHub as a literal backslash-n and breaks the callout.

Done when every body in the call starts with the byline.
