#!/bin/bash
#
# Build CPython wheels on Rocky-9 via Docker and copy into 3rdparty/python/wheels.
#
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARBALL="${1:-$ROOT/apache-aurora-0.23.3.tar.gz}"
WHEEL_OUT="${2:-$ROOT/3rdparty/python/wheels}"

if [[ ! -f "$TARBALL" ]]; then
  echo "Missing tarball: $TARBALL" 1>&2
  exit 1
fi

mkdir -p "$WHEEL_OUT"

docker build -f "$ROOT/builder/rpm/rocky-9/Dockerfile.cpython" -t aurora-rocky9-cpython "$ROOT"
docker run --rm \
  -v "$TARBALL:/src.tar.gz" \
  -v "$WHEEL_OUT:/wheels" \
  aurora-rocky9-cpython \
  /build_wheels.sh
