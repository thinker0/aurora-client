#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DIST_DIR="$ROOT_DIR/dist"

if [[ $# -ne 2 ]]; then
  echo "Usage: $0 <version> <platform>" >&2
  echo "Example: $0 0.23.3-SNAPSHOT darwin" >&2
  exit 1
fi

VERSION="$1"
PLATFORM="$2"

OUT_NAME="aurora-client-${VERSION}-${PLATFORM}.sh"
OUT_PATH="$ROOT_DIR/$OUT_NAME"

AURORA_PEX="$DIST_DIR/aurora.pex"
AURORA_ADMIN_PEX="$DIST_DIR/aurora_admin.pex"

if [[ ! -f "$AURORA_PEX" ]]; then
  echo "ERROR: Missing $AURORA_PEX" >&2
  exit 1
fi

if [[ ! -f "$AURORA_ADMIN_PEX" ]]; then
  echo "ERROR: Missing $AURORA_ADMIN_PEX" >&2
  exit 1
fi

cat <<'SCRIPT' > "$OUT_PATH"
#!/usr/bin/env bash
set -euo pipefail

BIN_DIR="$HOME/bin"
TARGET_AURORA="$BIN_DIR/aurora"
TARGET_AURORA_ADMIN="$BIN_DIR/aurora_admin"

WORKDIR="$(mktemp -d)"
cleanup() { rm -rf "$WORKDIR"; }
trap cleanup EXIT

ARCHIVE_LINE="$(awk '/^__ARCHIVE_BELOW__$/ {print NR + 1; exit 0;}' "$0")"
if [[ -z "$ARCHIVE_LINE" ]]; then
  echo "ERROR: embedded archive not found" >&2
  exit 1
fi

tail -n +"$ARCHIVE_LINE" "$0" | tar -xz -C "$WORKDIR"

if [[ ! -f "$WORKDIR/aurora.pex" ]]; then
  echo "ERROR: embedded aurora.pex missing" >&2
  exit 1
fi

if [[ ! -f "$WORKDIR/aurora_admin.pex" ]]; then
  echo "ERROR: embedded aurora_admin.pex missing" >&2
  exit 1
fi

mkdir -p "$BIN_DIR"

cp -f "$WORKDIR/aurora.pex" "$TARGET_AURORA"
cp -f "$WORKDIR/aurora_admin.pex" "$TARGET_AURORA_ADMIN"
chmod +x "$TARGET_AURORA" "$TARGET_AURORA_ADMIN"

echo "Installed:"
echo "  $TARGET_AURORA"
echo "  $TARGET_AURORA_ADMIN"
exit 0

__ARCHIVE_BELOW__
SCRIPT

tar -czf - -C "$DIST_DIR" aurora.pex aurora_admin.pex >> "$OUT_PATH"
chmod +x "$OUT_PATH"

echo "Created installer: $OUT_PATH"
