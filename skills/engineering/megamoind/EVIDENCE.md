# Evidence for the PR

Every flow the verifier reports, pass or fail, carries evidence: a file that shows the observable step 0 named as that flow's proof. A verdict without one counts as unverified. The files go in `<scratchpad>/pr-evidence/`, named after the flow and state (`export-queued.png`, `export-retry.mp4`, `export-retry.log`), and the passing ones end up in the PR's `## Evidence` section.

## Pick the kind

- **Screenshot**: a state a reviewer needs to see (the default, plus each state the ticket adds: loading, empty, error, each status).
- **Recording**: a flow whose proof is the sequence (click → result, a spinner starting, polling, a transition), where a still shows nothing. Record with the browser tool's recorder (`preview_recording_start` / `preview_recording_stop`), one short clip per flow, starting right before the action.
- **Trace**: a flow whose proof is a value no screen shows (a backend path, a job, a request's payload, a command's output). An excerpt of the `debug-trace` file, a request and its response, or the command and its output.

A frontend flow that also changes what the backend stores or sends gets both a capture and a trace.

## Screenshots and recordings

1. **Freeze animations** before a screenshot. A capture can land on an empty frame of a spinner or transition. Inject a `<style>` that sets `animation: none !important; transition: none !important` on everything, and give SVG spinners a visible stroke (e.g. MUI's `CircularProgress` circle needs a `stroke-dasharray` such as `80px, 200px`). Remove it before recording.
2. **Capture** with `save: true`. States local data can't produce are injected through `fetch` as step 5 says.
3. **Crop to the change.** Read the image's real size first (`sips -g pixelWidth -g pixelHeight <file>` on macOS), since the capture can come out at the browser's real viewport rather than the width you resized the tab to. Measure the changed region's bounding box in the page and scale it by the ratio between the image size and the page's `innerWidth`/`innerHeight`. Crop with `ffmpeg -loglevel error -y -i <in> -vf "crop=<w>:<h>:<x>:<y>" <out>`, offsets from the top-left (the same filter crops a clip). Without ffmpeg, use ImageMagick (`magick <in> -crop WxH+X+Y <out>`); without either, capture only the element's bounding box when the browser tooling supports a clip, or temporarily hide everything around the region. Open the result to check it shows the change.

## Traces

1. **Copy before cleanup.** `dbg.py clean` deletes the trace file, so copy the lines that prove the flow into `pr-evidence/<flow>.log` first.
2. **Trim to the proof**: the lines that show the expected value and the code path that produced it, at most 20, each long JSON cut to the fields that matter. Head the excerpt with the command or action that produced it.
3. **Redact** tokens, cookies, auth headers, emails and user or account IDs to `<redacted>`. The PR outlives the session and reaches everyone with repo access.

## Source line

Each file gets one line for the PR: the flow, then the source, e.g. "Retry after a failed export: local data" or "Queued and failed states, injected into the list response in the browser". An injected state always says so.

Hand the files and their lines to `github-pr` in step 7. A fix after verification that changes what a file shows means capturing it again.
