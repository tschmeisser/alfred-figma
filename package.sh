#!/bin/bash
# Build the public Figma Search.alfredworkflow.
# Contains NO token, NO team id, and NO file list — the importer fills the
# token + team id in Alfred's config sheet, then resyncs to populate the list.
set -e
cd "$(dirname "$0")"

OUT="Figma Search.alfredworkflow"
BUILD="$(mktemp -d)"
trap 'rm -rf "$BUILD"' EXIT

cp info.plist figma_search.py handle.sh sync_files.py results.png icon.png "$BUILD/"   # never .env

rm -f "$OUT"
( cd "$BUILD" && zip -q "$OLDPWD/$OUT" info.plist figma_search.py handle.sh sync_files.py results.png icon.png )
echo "Built: $OUT"
