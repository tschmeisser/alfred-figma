#!/usr/bin/env python3
"""Regenerate files.json from your Figma account via the REST API.

The Figma API has no "search my files" endpoint, so this walks
teams -> folders (recursively) -> files -> pages and caches the result locally.
Pages are only re-fetched for files whose last_modified changed since the last
sync, which keeps resyncs fast and inside Figma's rate limits. Run it whenever
you want to refresh the list; Alfred then searches the cache instantly.

Usage:
    python3 sync_files.py            # uses token + team from .env
    python3 sync_files.py TEAM_ID    # override the team id explicitly

Reads .env in this folder, expecting:
    figma_token=figd_...
    figma_team_id=1234567890

Find a team id in the Figma URL while viewing a team in the browser:
    figma.com/files/team/<TEAM_ID>/...
"""
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
# Regenerable data lives in Alfred's cache dir, never inside the workflow bundle.
# Falls back to a local .cache/ when run directly from the repo (no Alfred env).
CACHE = os.environ.get("alfred_workflow_cache") or os.path.join(HERE, ".cache")
FILES = os.path.join(CACHE, "files.json")
LOCK = os.path.join(CACHE, ".sync.lock")


def load_env():
    env = {}
    path = os.path.join(HERE, ".env")
    if os.path.exists(path):
        with open(path) as f:
            for line in f:
                line = line.strip()
                if "=" in line and not line.startswith("#"):
                    k, v = line.split("=", 1)
                    env[k.strip().lower()] = v.strip().strip('"').strip("'")
    return env


def api(path, token, retries=3):
    req = urllib.request.Request(
        "https://api.figma.com" + path,
        headers={"X-Figma-Token": token},
    )
    for attempt in range(retries + 1):
        try:
            with urllib.request.urlopen(req) as resp:
                return json.load(resp)
        except urllib.error.HTTPError as e:
            if e.code != 429 or attempt == retries:
                raise
            # Rate limited: wait as long as Figma asks (capped), then retry.
            wait = min(int(e.headers.get("Retry-After") or 30), 120)
            touch_lock()
            time.sleep(wait)


def touch_lock():
    """Keep the lock fresh so figma_search.py still sees a long sync running."""
    try:
        os.utime(LOCK)
    except OSError:
        pass


def load_cache():
    """Previous files.json, keyed by file key, so unchanged files reuse pages."""
    try:
        with open(FILES) as f:
            data = json.load(f)
    except (OSError, ValueError):
        return {}
    if not isinstance(data, list):
        return {}
    return {e["key"]: e for e in data if isinstance(e, dict) and e.get("key")}


def fetch_pages(key, token):
    """Page (canvas) ids + names for a file. depth=1 returns only the pages."""
    doc = api(f"/v1/files/{key}?depth=1", token).get("document", {})
    return [
        {"id": c["id"], "name": c["name"]}
        for c in doc.get("children", [])
        if c.get("type") == "CANVAS"
        # skip divider pages like "-----" that have no real name
        and re.search(r"\w", c.get("name", ""))
    ]


def resolve(key, env):
    """Look up a value from the environment (set by Alfred's workflow config),
    then fall back to .env (for running this script directly from the repo)."""
    return os.environ.get(key) or os.environ.get(key.upper()) or env.get(key)


def main():
    # The lock lets figma_search.py show a "syncing…" state and avoid
    # spawning a second background sync; always clear it when we finish.
    try:
        _sync()
    finally:
        try:
            os.remove(LOCK)
        except OSError:
            pass


def _sync():
    args = sys.argv[1:]
    env = load_env()

    token = resolve("figma_token", env)
    if not token:
        sys.exit("No token. Set it in the workflow config (figma_token) or .env")

    team_id = args[0] if args else resolve("figma_team_id", env)
    if not team_id:
        sys.exit(
            "No team id. Set figma_team_id in .env, or pass it:\n"
            "    python3 sync_files.py TEAM_ID\n"
            "Find it in figma.com/files/team/<TEAM_ID>/..."
        )

    # Figma renamed projects to folders; folders can nest. Needs folders:read.
    try:
        data = api(f"/v2/teams/{team_id}/folders", token)
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")
        sys.exit(f"team {team_id}: {e} — {body}")

    out = []
    stack = [(f, f.get("name", "")) for f in data.get("folders", [])]
    while stack:
        folder, path = stack.pop()
        fid = folder["id"]
        for fobj in api(f"/v2/folders/{fid}/files", token).get("files", []):
            out.append({
                "name": fobj["name"],
                "subtitle": path,
                "key": fobj["key"],
                "last_modified": fobj.get("last_modified", ""),
                "url": f"https://www.figma.com/design/{fobj['key']}/",
            })
        subs = api(f"/v2/folders/{fid}/folders", token).get("folders", [])
        stack.extend((sub, f"{path} / {sub.get('name', '')}") for sub in subs)
        touch_lock()

    # Pages need file_content:read. Reuse cached pages for unchanged files;
    # on a permission error, stop asking (every file would fail the same way).
    cache = load_cache()
    pages_ok = True
    for entry in out:
        old = cache.get(entry["key"], {})
        if "pages" in old and old.get("last_modified") == entry["last_modified"]:
            entry["pages"] = old["pages"]
            continue
        if not pages_ok:
            continue
        try:
            entry["pages"] = fetch_pages(entry["key"], token)
        except urllib.error.HTTPError as e:
            if e.code in (401, 403):
                pages_ok = False
        except (urllib.error.URLError, ValueError):
            pass
        touch_lock()

    out.sort(key=lambda e: e["name"].lower())
    os.makedirs(CACHE, exist_ok=True)
    tmp = FILES + ".tmp"
    with open(tmp, "w") as f:
        json.dump(out, f, indent=2)
        f.write("\n")
    os.replace(tmp, FILES)  # atomic: a concurrent reader never sees a half file
    pages = sum(len(e.get("pages", [])) for e in out)
    note = "" if pages_ok else " (no pages: token needs file_content:read)"
    print(f"Wrote {len(out)} files, {pages} pages from team {team_id}{note}")


if __name__ == "__main__":
    main()
