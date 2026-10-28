---
name: gomander
description: Control the Gomander desktop app (the user's launcher for project shell commands) through its local API — list Commands and Command Groups with their running status, and start or stop them by name. Use this whenever the user asks to start, stop, restart or check a dev server, service, watcher or any process "in Gomander", or names one of their Gomander Commands or Groups ("levanta el panel", "para el grupo Editor", "¿qué tengo corriendo?", "arranca auth y payments", "reinicia new-api"), even if they don't say "Gomander" but refer to services they normally launch from it. Prefer this over spawning the process yourself with Bash, since Gomander owns those processes and shows their output to the user.
---

# Gomander

Gomander runs a small REST API on localhost (first free port in 9001–9100) that
exposes the Commands and Command Groups of the **currently open project**. The
bundled script handles port discovery and name → id resolution, so use it
instead of hand-rolling `curl` calls:

```bash
python3 <skill-dir>/scripts/gomander.py <action> [target]
```

| Action | What it does |
|---|---|
| `commands` | Every Command with `running`/`stopped` |
| `groups` | Every Group with `running/total` counts |
| `run <target>` / `stop <target>` | Start or stop one Command |
| `run-group <target>` / `stop-group <target>` | Start or stop every Command in a Group |

`<target>` is an id or a name. Names match case-insensitively, exact first, then
by unique substring — so `run panel` picks `panel` even though `panel (watch)`
also exists.

## Exit codes and what to do

- **0** — done.
- **2** — the name was unknown or ambiguous; the script prints the candidates.
  If one candidate obviously fits what the user meant, retry with its id and
  say which one you picked. If it is a genuine toss-up, ask. Two Commands can
  share the exact same name and the API gives nothing else to tell them apart,
  so in that case always ask.
- **3** — Gomander isn't reachable. Tell the user to open it; don't try to
  launch the processes yourself as a workaround, since they'd live outside
  Gomander and the user couldn't see or stop them there.
- **1** — Gomander returned an error. The API only ever answers a generic 500,
  so the cause could be no open project, a deleted Command, or a failure to
  spawn. Say so rather than guessing.

## Things the API does not tell you

- **Starting is fire-and-forget.** A successful `run` means the process was
  spawned, not that it's healthy. It can exit a second later. If the user cares
  whether it came up, wait ~2 s and run `commands` again; a Command that went
  back to `stopped` crashed or finished.
- **There is no output.** The API can't read logs. When something fails or the
  user wants to know *why*, point them to the Command's terminal in Gomander.
- **Only the open project is visible.** A Command the user remembers from
  another project won't be listed; ask them to switch project in Gomander.
- **Running an already-running Command is a no-op**, so there's no restart
  endpoint. To restart: `stop`, wait ~1 s, then `run`.
- A Group `run` starts its Commands in order and stops at the first one that
  fails to spawn, so after a Group error check `groups`/`commands` to see what
  actually came up.

Report back briefly: what you started/stopped and, if you checked, what's
running now.
