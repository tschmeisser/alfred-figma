#!/bin/bash
# Action behind the Figma Search script filter.
#   "resync"      -> refresh files.json in place (inside the workflow), then notify
#   anything else -> open the figma:// or https:// URL
#
# On resync, the Figma token + team id arrive as environment variables
# (figma_token / figma_team_id) from the workflow's own configuration,
# so nothing is read from disk and the token never touches a Terminal or argv.
arg="$1"
here="$(cd "$(dirname "$0")" && pwd)"

if [ "$arg" = "resync" ]; then
  /usr/bin/osascript -e 'display notification "Fetching files from Figma — this takes about a minute…" with title "Figma Search" subtitle "Resyncing"'
  result="$(/usr/bin/python3 "$here/sync_files.py" 2>&1 | tail -1 | tr -d '"\\')"
  [ -z "$result" ] && result="Sync finished."
  /usr/bin/osascript -e "display notification \"$result\" with title \"Figma Search\" subtitle \"Resync complete\" sound name \"Glass\""
else
  open "$arg"
fi
