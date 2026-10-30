# alfred-figma

Alfred workflow (macOS) that searches Figma files and opens them in the desktop app.
This repo holds the **source**; the packaged workflow is distributed via GitHub releases.

## Distribution / releasing

The built `*.alfredworkflow` is **gitignored — never commit it**. It's published as a
GitHub release asset instead.

```bash
git push                                    # publish source changes first
./package.sh                                # builds Figma Search.alfredworkflow (gitignored)
gh release create vX.Y "Figma Search.alfredworkflow" \
  --title "Figma Search vX.Y" --notes "..."
```

The README's Download link points at `/releases/latest`, so it always resolves to the
newest release.

## Scrub before every commit and release

The repo and its releases are **public**. Before each commit, and again before each
`gh release create`, confirm no personal data is included:

- No real `figma_token` (`figd_…`), team id, file keys, file/folder names, or local
  paths (`/Users/…`) in the diff. Placeholders (`figd_...`, `1234567890`) are fine.
- `info.plist`'s `userconfigurationconfig` defaults stay empty; top-level `variables` stays
  empty. (Alfred's installed copy holds real values in `prefs.plist` — never copy that or
  the installed `info.plist` back into the repo.)
- `.env`, `.cache/`, `files.json`, and `*.alfredworkflow` are never staged.
- After `./package.sh`, unzip the bundle to a temp dir and check it contains only
  `info.plist figma_search.py handle.sh sync_files.py results.png icon.png`, then grep it:

```bash
git diff --cached | grep -nE 'figd_[A-Za-z0-9]{6,}|/Users/|[0-9]{9,}'
grep -rnE 'figd_[A-Za-z0-9]{6,}|/Users/' <unzipped-bundle-dir>
```

## Runtime data

`files.json` and `.sync.lock` are written to `$alfred_workflow_cache` (Alfred sets this),
falling back to `./.cache/` when scripts run directly from the repo — **never** inside the
workflow bundle dir. `files.json` is a regenerable cache of the Figma API.

## Config vars

`figma_token` / `figma_team_id` are defined once, in `info.plist`'s
`userconfigurationconfig` (Configuration Builder), both `required`. Do not duplicate them
into the top-level `variables` dict (that triggers Alfred's editor warning).
