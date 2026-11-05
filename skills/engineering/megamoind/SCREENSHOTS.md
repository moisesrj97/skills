# Screenshots for the PR

Taken in step 5, in the verification tab, once the screen behaves as the ticket asks. They end in a `## Screenshots` section at the end of the PR description, one image per relevant state.

1. **Pick the states.** One capture per state a reviewer needs to see: the default, plus each state the ticket adds (loading, empty, error, each status). States local data can't produce are injected through `fetch` as step 5 says.
2. **Freeze animations.** A capture can land on an empty frame of a spinner or transition. Inject a `<style>` that sets `animation: none !important; transition: none !important` on everything, and give SVG spinners a visible stroke (e.g. MUI's `CircularProgress` circle needs a `stroke-dasharray` such as `80px, 200px`). Remove it when done.
   When the change *is* the motion (a spinner starting, polling, a transition), a still shows nothing: record a short clip with the browser tool's recorder (`preview_recording_start` / `preview_recording_stop`) instead, and attach it as a video, `![](./clip.mp4)` alone in its own paragraph.
3. **Capture** with `save: true` into `<scratchpad>/pr-shots/`, named after the state (`table-local-data.png`).
4. **Crop to the change.** Read the image's real size first (`sips -g pixelWidth -g pixelHeight <file>` on macOS): the capture can come out at the browser's real viewport rather than the width you resized the tab to. Measure the changed region's bounding box in the page and scale it by the ratio between the image size and the page's `innerWidth`/`innerHeight`. On macOS crop with `sips -c <height> <width> --cropOffset <y> <x> <file>`. Elsewhere, use whatever image tool the machine has (ImageMagick's `convert`/`magick` with `-crop WxH+X+Y`, or a few lines of Python with Pillow); without one, crop in the browser instead: capture only the element's bounding box when the browser tooling supports a clip, or temporarily hide everything around the region before capturing. Open the result to check it shows the change.
5. **Note each source** in one line for the PR, e.g. "Local data" or "Queued and failed states, injected into the list response in the browser". An injected state always says so.

Hand the files and their lines to `github-pr` in step 7.
