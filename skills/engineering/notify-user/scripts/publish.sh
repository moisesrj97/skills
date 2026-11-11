#!/usr/bin/env bash
# Usage: publish.sh [curl options...]
# Publishes to the configured ntfy topic with the token from the configured file.
set -euo pipefail

config="${XDG_CONFIG_HOME:-$HOME/.config}/moisesrj97-skills/notify-user.json"
if [[ ! -f "$config" ]]; then
  echo "notify-user: missing $config" >&2
  exit 2
fi

{
  IFS= read -r server
  IFS= read -r topic
  IFS= read -r token_file
} < <(python3 -I -c '
import json, os, sys
c = json.load(open(sys.argv[1]))
print(c["server"].rstrip("/"))
print(c["topic"])
print(os.path.expanduser(c["token_file"]))
' "$config")

if [[ ! -s "$token_file" ]]; then
  echo "notify-user: token file $token_file is missing or empty" >&2
  exit 2
fi

curl -sS --fail-with-body \
  -H @<(printf 'Authorization: Bearer %s\n' "$(tr -d '\n' < "$token_file")") \
  "$@" "$server/$topic"
