---
name: pr-comment
description: Reworks a review finding or a remark the user asked for into the comment a teammate would post on a PR. Use before posting one as a PR comment, review or reply, whether the user asked for it or another skill posts it.
---

# PR comment

A finding the user approved for posting, or a remark they asked for, is written for the author, who knows the code, so the review report's version doesn't go out as is. Before posting, rework it in this order:

1. **Synthesize.** The cause, what the user sees and one fix, in at most four sentences, or three when the user asked for a short comment. Several cases fold into one sentence, not a list. Leave out the trace through the code (which call sets what, which component unmounts), the test that would cover it and alternative fixes; the author asks if they want them.
2. **Humanize.** Write it the way a teammate would: plain sentences in the comment's language, no bold labels, no headers.
3. **Unslop.** Run the `unslop` skill on the result.

Done when every comment in the post went through the three steps. The byline from `agent-byline` goes on top afterwards.
