#!/usr/bin/env python3
"""Regenerate files.json from your Figma account via the REST API.

The Figma API has no "search my files" endpoint, so this walks
teams -> projects -> files and caches the result locally. Run it whenever
you want to refresh the list; Alfred then searches the cache instantly.

Usage:
    python3 sync_files.py                 # uses work token + team from .env
    python3 sync_files.py --personal      # uses personal token + team from .env
    python3 sync_files.py TEAM_ID         # override the team id explicitly

Reads .env in this folder, expecting:
    figma_work_token=figd_...
    figma_work_team_id=1234567890
    figma_personal_token=...
    figma_personal_team_id=...

Find a team id in the Figma URL while viewing a team in the browser:
    figma.com/files/team/<TEAM_ID>/...
"""
import json
import os
import sys
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
FILES = os.path.join(HERE, "files.json")
LOCK = os.path.join(HERE, ".sync.lock")


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
    args = [a for a in sys.argv[1:] if a != "--personal"]
    scope = "personal" if "--personal" in sys.argv else "work"
    env = load_env()

    token = resolve(f"figma_{scope}_token", env)
    if not token:
        sys.exit(f"No {scope} token. Set it in the workflow config (figma_{scope}_token) or .env")

    team_id = args[0] if args else resolve(f"figma_{scope}_team_id", env)
    if not team_id:
        sys.exit(
            f"No team id. Set figma_{scope}_team_id in .env, or pass it:\n"
            f"    python3 sync_files.py TEAM_ID\n"
            f"Find it in figma.com/files/team/<TEAM_ID>/..."
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
    tmp = FILES + ".tmp"
    with open(tmp, "w") as f:
        json.dump(out, f, indent=2)
        f.write("\n")
    os.replace(tmp, FILES)  # atomic: a concurrent reader never sees a half file
    print(f"Wrote {len(out)} files from team {team_id} to {FILES}")


if __name__ == "__main__":
    main()
