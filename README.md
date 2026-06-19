# Alfred Figma Search

Search your figma files from Alfred and then open in the desktop app or browser.

## Setup

1. Create a token on figma.com → Settings → Security → Personal Access Token.
2. Find your team ID by opening figma.com and looking for the URL segment after “team”.
    - This is different depending on what type of account you have, personal accounts always show it and team account require you to visit a project.
    - Examples:
    - https://www.figma.com/files/team/XXX/project/XXX?fuid=XXX
    - https://www.figma.com/files/XXX/team/XXX?fuid=XXX
3. Double click the .alfredworkflow file and enter your token and team ID.
4. Run "fig" and your files will sync.
5. To edit the workflow yourself and sync files locally, add a .env with two values:
    - figma_token=figd_XXXXXX
    - figma_team_id=XXXXXX

## Using the file search

- Type "fig" then part of a file name to search your Figma files.
- The first time you run the command, it will sync all of your files.
- From the result list, hitting Return opens the selected file in the desktop app and cmd+Return opens it in the browser.
- The fig command also returns a "Resync files from Figma" action that refreshes all of your files (the list is saved locally).
- Change your token and team id with “Configure Workflow and Variables”.

## Files

| File | Role |
|------|------|
| `info.plist`      | Workflow: Script Filter → `handle.sh`; token/team config fields |
| `figma_search.py` | Reads in-workflow `files.json`, emits items + Resync (no token) |
| `handle.sh`       | Opens the URL, or runs resync in place + notifies |
| `sync_files.py`   | Regenerates `files.json` from the Figma API |
| `files.json`      | The file list (lives inside the workflow) |
| `results.png`     | Icon shown on each search result (and the Resync action) |
| `icon.png`        | The workflow's icon in Alfred |
| `package.sh`      | Builds the `.alfredworkflow` bundle |
