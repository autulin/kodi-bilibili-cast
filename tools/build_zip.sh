#!/usr/bin/env bash
# Build an installable Kodi addon zip: dist/service.bili.cast-<version>.zip
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ADDON_DIR="$ROOT/service.bili.cast"
DIST_DIR="$ROOT/dist"

VERSION="$(python3 - "$ADDON_DIR/addon.xml" <<'PY'
import re
import sys

text = open(sys.argv[1], encoding="utf-8").read()
match = re.search(r'<addon[^>]*\bversion="([^"]+)"', text)
print(match.group(1) if match else "0.0.0")
PY
)"

mkdir -p "$DIST_DIR"
ZIP="$DIST_DIR/service.bili.cast-$VERSION.zip"
rm -f "$ZIP"

cd "$ROOT"
find service.bili.cast -name '__pycache__' -type d -prune -exec rm -rf {} +
find service.bili.cast -name '*.pyc' -delete

zip -qr "$ZIP" service.bili.cast \
  -x '*/__pycache__/*' '*.pyc' '*.DS_Store'

echo "built $ZIP"
