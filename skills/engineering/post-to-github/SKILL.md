---
name: post-to-github
description: Writes and posts a GitHub PR comment, review or reply on the user's behalf, with the agent byline, a teammate's voice and the posting command. Use before posting any of them, whether the user asked for the text or another skill posts it.
---

# Post to GitHub

Every body you post to a pull request under the user's account opens with the byline, so the reader knows an agent wrote it: PR comments, review bodies, each inline review comment and each reply in a thread. GitHub shows each of these on its own, so each carries its own byline.

```md
> [!NOTE]
> 🤖 **<model> responding on behalf of <name>**

<the comment>
```

- `<model>`: the model you run on, named as your system prompt names it, with its family: `Claude Opus 5.5`, not `claude-opus-5-5` or `Claude`.
- `<name>`: the `name` field of `~/.config/moisesrj97-skills/post-to-github.json`. When the file is missing, ask the user which name to sign with and write `{"name": "<name>"}` there.

Write the byline in the comment's language (`🤖 **Claude Opus 5.5 respondiendo en nombre de <name>**`). A fresh review, or an approval with no text, takes the language of the PR description; an approval with no text gets the byline as its whole body.

## The comment

A finding the user approved for posting, or a remark they asked for, is written for the author, who knows the code, so the review report's version doesn't go out as is. Before posting, rework it in this order:

1. **Synthesize.** The cause, what the user sees and one fix, in at most four sentences, or three when the user asked for a short comment. Several cases fold into one sentence, not a list. Leave out the trace through the code (which call sets what, which component unmounts), the test that would cover it and alternative fixes; the author asks if they want them.
2. **Humanize.** Write it the way a teammate would: plain sentences in the comment's language, no bold labels, no headers.
3. **Unslop.** Run the `unslop` skill on the result.

## Posting

Write the body to a file and pass the file: `gh pr comment --body-file`, `gh pr review --body-file`, `gh api … -F body=@<file>`, or `gh api … --input <file>.json` for a review with inline comments. Through `-f body="…"`, a `\n` reaches GitHub as a literal backslash-n and breaks the callout.

Done when every body in the call starts with the byline.
