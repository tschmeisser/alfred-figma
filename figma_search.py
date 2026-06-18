#!/usr/bin/env python3
"""Alfred Script Filter backend for Figma Search.

Reads files.json (next to this script, inside the workflow) and emits Alfred
items plus a "Resync" item. Each file item's arg is a figma:// deep link so the
desktop app opens it.

First-run behaviour: if the list is empty but a token + team id are configured,
a background sync is kicked off automatically (non-blocking) so the workflow
populates itself the first time it's used. The explicit "Resync" action is
unchanged and always available.
"""
import json
import os
import subprocess
import time

HERE = os.path.dirname(os.path.abspath(__file__))
FILES = os.path.join(HERE, "files.json")
SYNC = os.path.join(HERE, "sync_files.py")
LOCK = os.path.join(HERE, ".sync.lock")
SYNC_TIMEOUT = 180  # seconds a sync is assumed to still be running

WEB_PREFIXES = (
    "https://www.figma.com",
    "https://figma.com",
    "http://www.figma.com",
)


def to_deeplink(url):
    """Convert a figma.com web URL into a figma:// desktop deep link."""
    url = (url or "").strip()
    if url.startswith("figma://"):
        return url
    for prefix in WEB_PREFIXES:
        if url.startswith(prefix):
            return "figma:/" + url[len(prefix):]
    return url


def load_files():
    try:
        with open(FILES) as f:
            data = json.load(f)
    except (OSError, ValueError):
        return []
    return data if isinstance(data, list) else []


def creds_present():
    def has(name):
        return bool(os.environ.get(name) or os.environ.get(name.upper()))
    return has("figma_token") and has("figma_team_id")


def sync_running():
    try:
        return (time.time() - os.path.getmtime(LOCK)) < SYNC_TIMEOUT
    except OSError:
        return False


def start_background_sync():
    """Fire-and-forget sync that survives this script exiting."""
    try:
        open(LOCK, "w").close()
        subprocess.Popen(
            ["/usr/bin/python3", SYNC],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        return True
    except OSError:
        return False


def file_item(entry):
    url = entry.get("url", "")
    if not url:
        return None
    name = entry.get("name") or url
    return {
        "title": name,
        "subtitle": entry.get("subtitle")
        or "↩ open in Figma desktop   ·   ⌘↩ open in browser",
        "arg": to_deeplink(url),
        "match": name,
        "valid": True,
        "icon": {"type": "fileicon", "path": "/Applications/Figma.app"},
        "mods": {"cmd": {"subtitle": "Open in browser", "arg": url}},
    }


def empty_state_item():
    """Shown when there are no files yet — drives the first-run auto-sync."""
    if sync_running():
        return {
            "title": "Syncing your Figma files…",
            "subtitle": "This takes about a minute — search again shortly",
            "valid": False,
        }
    if creds_present():
        start_background_sync()
        return {
            "title": "Fetching your Figma files now…",
            "subtitle": "First-time sync started — search again in a moment",
            "valid": False,
        }
    return {
        "title": "Add your Figma token to begin",
        "subtitle": "Open the workflow config ([𝓍]) and set your token + team id",
        "valid": False,
    }


def main():
    items = [it for it in (file_item(e) for e in load_files()
                           if isinstance(e, dict)) if it]

    if not items:
        items.append(empty_state_item())

    items.append({
        "title": "Resync files from Figma",
        "subtitle": "↩ refresh the file list from your team",
        "arg": "resync",
        "match": "resync refresh reload sync update",
        "valid": True,
    })

    print(json.dumps({"items": items}))


if __name__ == "__main__":
    main()
