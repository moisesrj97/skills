---
name: notify-user
description: Sends the user a push notification through their ntfy server. Use when the user asks to be notified, pinged or alerted, now or when a task finishes.
---

# Notify user

Send a notification only when the user asked for one in this conversation. One request covers the notifications it names, such as "avísame cuando acabe".

## Setup

The settings live in `~/.config/moisesrj97-skills/notify-user.json`:

```json
{"server": "https://ntfy.example.com", "topic": "claude", "token_file": "~/.config/ntfy/claude-token"}
```

When the file is missing, ask the user for the server URL and the topic, and write it. The token file holds a bare ntfy access token (`tk_…`). The user writes it with `! printf '%s' '<token>' > <file> && chmod 600 <file>`, so the token never appears in the conversation. Never read or print it yourself.

## Send

`<skill-dir>/scripts/publish.sh` adds the server, the topic and the token, and passes every other argument to curl. Build the notification with ntfy's headers (https://docs.ntfy.sh/publish/):

```bash
<skill-dir>/scripts/publish.sh -H "Title: Build finished" -H "Priority: high" -H "Tags: white_check_mark" -d "All 312 tests pass."
```

To attach a local file, send it as the body with `-T <file> -H "Filename: <name>"` and put the text in a `Message` header. The server must have `attachment-cache-dir` set. If it doesn't, the server answers 400 `attachments not allowed` and drops the whole message. Resend without the file, or with `-H "Attach: <url>"` when the file is already online.

## Errors

- **401** means the server does not know the token, usually because the user saved a new one before the server loaded it. Tell the user and stop.
- **403** means the token's user cannot write to the topic. Tell the user and stop.

The send is done when the script prints the message JSON with an `id`.
