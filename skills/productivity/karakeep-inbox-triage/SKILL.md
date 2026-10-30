---
name: karakeep-inbox-triage
description: Triage the user's Karakeep "Inbox" list — fetch the bookmarks sitting there, propose tags and a final destination list for each one, present all proposed changes in a table for approval, and apply only what the user confirms. May propose new tags or new lists when nothing existing fits. Use this whenever the user asks to organize, classify, clean up, sort, tag or process their Karakeep/bookmarks inbox, or says things like "ordena mis marcadores", "procesa el inbox de karakeep", "clasifica lo que tengo pendiente en karakeep", "etiqueta mis bookmarks", even if they don't say "triage".
---

# Karakeep Inbox Triage

Goal: empty the `Inbox` list of the user's self-hosted Karakeep by giving every bookmark good tags and moving it to its definitive list — without changing anything the user hasn't approved.

## Connection

The bundled scripts handle auth: the API key is read from `~/.karakeep` (a file containing only the key) and the server URL from `~/.config/moisesrj97-skills/karakeep.json` (`{"server": "https://…"}`, overridable with `KARAKEEP_SERVER_ADDR`). Both live outside the skill folder so a reinstall doesn't wipe them. Never print or echo the key. For ad-hoc CLI calls, export the same values first:

```bash
export KARAKEEP_API_KEY="$(tr -d '[:space:]' < ~/.karakeep)" KARAKEEP_SERVER_ADDR="${KARAKEEP_SERVER_ADDR:-$(jq -r .server ~/.config/moisesrj97-skills/karakeep.json)}"
```

**First run:** if either file is missing, set it up before anything else.
- Server: ask the user for their Karakeep URL and write the JSON file.
- Key: don't ask for it in the chat. Tell the user to run `! printf '%s' '<key>' > ~/.karakeep && chmod 600 ~/.karakeep` themselves, so the key never passes through the conversation.

If a call fails with `UNAUTHORIZED`, the key or server is wrong — tell the user rather than retrying.

## Workflow

### 1. Fetch context

```bash
python3 <skill-dir>/scripts/fetch_context.py > <scratchpad>/karakeep_ctx.json
```

It outputs:
- `inbox`: each bookmark with title, url, description, existing tags, note, and `alsoInLists` (other lists it already belongs to).
- `lists`: every manual list except Inbox, with its full path (`Tech / Frontend`), icon, and a few sample bookmarks (title + tags). The samples are how you learn what each list is *actually* used for — names alone are ambiguous (e.g. `Whishlist` holds things to buy; `Tools` vs `Tech / Resources`).
- `tagsInUse` (name → count) and `tagsUnused`.

If Inbox is empty, say so and stop.

### 2. Understand each bookmark

Title + URL + description are usually enough. When they aren't (generic title like "YouTube", missing description, failed crawl), read a bit of content:

```bash
karakeep bookmarks content <id> --format text --max-chars 1500
```

Don't do this for every bookmark — only the ambiguous ones; it's slow and adds noise.

### 3. Decide tags and list

**Tags** — 2–4 per bookmark, describing topic/type (e.g. `path-of-exile`, `guide`, `shopping`).
- Reuse `tagsInUse` first, favouring higher counts. The tag vocabulary is messy (many unused tags, near-duplicates like `cyberpunk2077`/`cyberpunk-2077`, `cheatsheet`/`cheat-sheet`, `torrent`/`torrents`); always pick the most-used spelling instead of adding another variant.
- An unused tag that fits exactly is fine to reuse, since it already exists.
- Propose a new tag only when nothing fits and it's likely to be reused. Follow the existing convention: lowercase, kebab-case, English (except established Spanish ones like `uoc`).
- Keep tags the bookmark already has unless clearly wrong; don't propose removals unless there's a real reason (and say it).

**List** — exactly one definitive list per bookmark.
- Prefer the most specific fitting list (a child like `Games / PoE` over `Games`).
- If `alsoInLists` is non-empty, the bookmark was already classified; default to keeping that list and just taking it out of Inbox — unless it's clearly misfiled, in which case flag it.
- `Read Later` is a destination only if the content is genuinely "to read" with no better topical home.
- Propose a new list (optionally as a child of an existing one) when several bookmarks — or one clearly recurring interest — don't fit anywhere. Don't create a list for a single one-off item; use the closest parent instead and mention the option.
- If you're genuinely unsure, say so in the table rather than guessing confidently.

### 4. Draft the plan and verify what's new

Before showing anything, write your proposal as a plan (format in step 6) to `<scratchpad>/karakeep_plan.json` and dry-run it:

```bash
python3 <skill-dir>/scripts/apply_plan.py <scratchpad>/karakeep_plan.json
```

The first lines of the output are the source of truth for what's new:

```
NEW TAGS: peripherals, cheat-sheets
  WARN tag 'cheat-sheets' looks like existing: cheatsheet, cheat-sheet
NEW LISTS: none
```

Your own judgment about which tags exist is unreliable with a vocabulary this large — that's why this check exists. Put 🆕 exactly on the tags/lists the script reports as new, nowhere else. For every `WARN` about a similar existing tag, switch to the existing tag unless there's a real distinction, and re-run the dry run. A `WARN` about a list name clash means pick a different name.

### 5. Present the proposal

Use exactly this structure:

```
## Propuesta de triage — N marcadores en Inbox

| # | Marcador | Tags actuales | Tags propuestos | Lista destino | Motivo |
|---|----------|---------------|-----------------|---------------|--------|
| 1 | [Título corto](url) | — | `path-of-exile`, `guide`, `🆕 video` | 🎮 Games / PoE | Playlist de guías de PoE 2 |
| 2 | ... | `shopping` | `shopping`, `hardware` | ✨ Whishlist *(ya estaba)* | Ya clasificado; solo sale de Inbox |

**🆕 Tags nuevos:** `video` · **🆕 Listas nuevas:** ninguna

### 🆕 Nuevos tags
- `video` — no existe ningún tag para vídeos/playlists; útil para YouTube.

### 🆕 Nuevas listas
- 🛒 **Whishlist / Tech** (hija de Whishlist) — agruparía los periféricos (#3, #4).

### Dudas
- #5: no está claro si es … o …
```

Details that matter for readability:
- Truncate titles to ~50 chars; link them to the URL.
- Mark new tags and new lists with 🆕 inline so they're spotted at a glance.
- The "🆕 Tags nuevos / Listas nuevas" line always appears, saying "ninguno/ninguna" when empty — so the user can tell "nothing new" apart from "forgot to mark it".
- Mark `*(ya estaba)*` when the destination is a list the bookmark already belongs to.
- Omit the "Nuevos tags", "Nuevas listas" or "Dudas" detail sections when empty.

Then ask: apply all, or which rows to change (e.g. "3: lista Tools", "quita el tag video", "no crees la lista"). After each change, update the plan and re-run the dry run so the 🆕 marks stay accurate. Nothing is written to Karakeep before explicit approval.

### 6. Apply

The plan in `<scratchpad>/karakeep_plan.json` has this format:

```json
{
  "newLists": [{"key": "wishlist-tech", "name": "Tech", "icon": "🛒", "parent": "<existing list id or another newLists key, or null>"}],
  "bookmarks": [
    {"id": "<bookmark id>", "addTags": ["path-of-exile", "guide"], "list": "<list id or newLists key>"}
  ]
}
```

`addTags` only needs the tags to add (new tag names are created automatically; existing ones are matched case-insensitively to their stored spelling). Skipped rows are simply left out — they stay in Inbox.

Once approved, execute:

```bash
python3 <skill-dir>/scripts/apply_plan.py <scratchpad>/karakeep_plan.json --execute
```

The script creates new lists, adds tags, adds each bookmark to its list, and only then removes it from Inbox — if an earlier step fails for a bookmark it stays in Inbox. It never archives or deletes.

### 7. Report

Summarize briefly: how many bookmarks moved, lists/tags created, and any `ERR` lines from the script with what they mean. If anything failed, those bookmarks are still in Inbox — say so.
