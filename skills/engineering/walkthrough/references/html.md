# The guide

The artifact `walkthrough` produces: a single self-contained HTML file, opened
from disk, thrown away when it stops being useful.

## Where it lands

`/tmp/walkthroughs/<repo>-<slug>-<genid>.html`

- `<slug>` comes from what the human asked for (`pr-1234`, `working-tree`), so
  the file stays findable.
- `<genid>` is a short random id generated per run
  (`openssl rand -hex 2`). Every run is a new file and a fresh read.

## Written in Spanish

The human reading the guide works in Spanish. Code
identifiers, paths and commands keep their original form.

## Three blocks

**1. Impacto.** What this change means for the user, or for the system. It is
what someone gets from 30 seconds of reading. Stamp the SHA it was generated
against, and the branch, so a reader can tell when the guide is out of date.

**2. Mapa.** The shape of the change, the ordered list of stops with the one
line saying why that order, and **de dónde venimos**: the context that lives
outside the diff and without which the change reads as half-information.

**3. Recorrido.** The stops, each with its prose, its links, and a cited
fragment only where a sentence is unreadable without seeing that exact line.
Three to five lines, as an anchor. The reader opens the full code in the IDE.

Close with **Resto**: every file of the changeset that earned no stop, each with
one line saying why (mechanical rename, snapshot, lockfile). This keeps the
walk a narrative while still covering every file.

## Visuals

Every diagram, table or badge replaces a paragraph that would otherwise have to
be written. Pick the ones that fit *this* change.

Everything renders offline from a `file://` page: inline SVG, native CSS, no
external library, font or request.

## Typography and layout

- A reading measure, generous line height, real typographic hierarchy. This is
  a long read, not a dashboard.
- Light and dark, following the system.
- Wide content (tables, diagrams, code) scrolls inside its own container; the
  page never scrolls sideways.

## Links into the IDE

Write source references as relative paths in the markup and let one helper build
the hrefs:

```html
<span data-src="apps/foo/src/core/GetAnnotationDiff.ts:42"></span>

<script>
  const ROOT = '<git rev-parse --show-toplevel>/';
  document.querySelectorAll('[data-src]').forEach(el => {
    const [path, line] = el.dataset.src.split(':');
    const a = document.createElement('a');
    a.href = `webstorm://open?file=${ROOT}${path}` + (line ? `&line=${line}` : '');
    a.textContent = el.dataset.src;
    el.replaceWith(a);
  });
</script>
```

`webstorm://open` needs an **absolute** path, hence the baked `ROOT`. The
browser asks for confirmation the first time it launches the external app.

When step 2 of the skill settled on GitHub links instead, the same `data-src`
markup builds `https://github.com/<owner>/<repo>/blob/<sha>/<path>#L<line>`,
and the header says the links go to GitHub and why.

## Progress

Stops are checkable, with a progress indicator. State lives in `localStorage`
under `walkthrough:<genid>`, so:

- reloading or reopening the tab keeps the progress,
- regenerating the guide starts clean, because `genid` is new.

Store a timestamp beside the state, and on load drop any `walkthrough:` key
older than 30 days.
