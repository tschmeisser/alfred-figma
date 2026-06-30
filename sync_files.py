#!/usr/bin/env python3
"""Regenerate files.json from your Figma account via the REST API.

The Figma API has no "search my files" endpoint, so this walks
teams -> projects -> files and caches the result locally. Run it whenever
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
import sys
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


def api(path, token):
    req = urllib.request.Request(
        "https://api.figma.com/v1" + path,
        headers={"X-Figma-Token": token},
    )
    with urllib.request.urlopen(req) as resp:
        return json.load(resp)


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

    try:
        projects = api(f"/teams/{team_id}/projects", token).get("projects", [])
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")
        sys.exit(f"team {team_id}: {e} — {body}")

    out = []
    for proj in projects:
        files = api(f"/projects/{proj['id']}/files", token).get("files", [])
        for fobj in files:
            out.append({
                "name": fobj["name"],
                "subtitle": proj.get("name", ""),
                "url": f"https://www.figma.com/design/{fobj['key']}/",
            })

    out.sort(key=lambda e: e["name"].lower())
    os.makedirs(CACHE, exist_ok=True)
    tmp = FILES + ".tmp"
    with open(tmp, "w") as f:
        json.dump(out, f, indent=2)
        f.write("\n")
    os.replace(tmp, FILES)  # atomic: a concurrent reader never sees a half file
    print(f"Wrote {len(out)} files from team {team_id} to {FILES}")


if __name__ == "__main__":
    main()
