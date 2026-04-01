#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SRC="$ROOT/skills/openclaw-kaipanla-bridge"
DEST_ROOT="${CODEX_HOME:-$HOME/.codex}/skills"
DEST="$DEST_ROOT/openclaw-kaipanla-bridge"

if [[ ! -d "$SRC" ]]; then
  echo "source skill not found: $SRC" >&2
  exit 1
fi

mkdir -p "$DEST_ROOT"
rm -rf "$DEST"
cp -R "$SRC" "$DEST"
find "$DEST" -name ".DS_Store" -delete
printf "%s\n" "$ROOT" > "$DEST/repo-root.txt"
if [[ -d "$DEST/scripts" ]]; then
  find "$DEST/scripts" -type f -name "*.sh" -exec chmod +x {} +
fi

echo "$DEST"
