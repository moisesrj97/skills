---
name: gh-attach
description: Attaches local images or videos to GitHub issues, PRs and comments with `gh --attach`. Use when a screenshot or recording has to go into an issue, a PR or a comment.
---

gh uploads media itself since 2.99. Do it with gh; asking the user to drag files into the browser is no longer needed.

1. **Check the version.** Run `gh --version`. Below 2.99, tell the user to update gh (`brew upgrade gh`) and stop.
2. **Reference the file in the body.** Write `![alt text](./shot.png)` where the image goes, in a body file saved **in the same folder as the media**, because gh resolves those paths relative to the body file. A video goes alone in its own paragraph, `![](./clip.mp4)`, and then shows as a player.
3. **Upload.** `gh issue|pr create|edit|comment … --body-file body.md --attach ./shot.png`, with one `--attach` per file. gh replaces each local reference with the uploaded URL. With no reference, or no body flag on `edit`, it adds the file at the end of the body.
4. **Check.** View the body: every local path should now be a `https://github.com/user-attachments/assets/…` URL.

Uploading publishes the file. It needs the same approval as the text it goes with.
