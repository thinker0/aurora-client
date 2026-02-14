#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

export PANTS_PYTHON_BOOTSTRAP_SEARCH_PATH="/opt/homebrew/opt/python@3.9/bin/python3.9"

exec "${ROOT_DIR}/pants" "$@" \
  --python-repos-find-links="[\"file://${ROOT_DIR}/3rdparty/python/wheels\"]" \
  --python-repos-indexes="[]"
