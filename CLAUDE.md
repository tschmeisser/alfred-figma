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

## Runtime data

`files.json` and `.sync.lock` are written to `$alfred_workflow_cache` (Alfred sets this),
falling back to `./.cache/` when scripts run directly from the repo — **never** inside the
workflow bundle dir. `files.json` is a regenerable cache of the Figma API.

## Config vars

`figma_token` / `figma_team_id` are defined once, in `info.plist`'s
`userconfigurationconfig` (Configuration Builder), both `required`. Do not duplicate them
into the top-level `variables` dict (that triggers Alfred's editor warning).
