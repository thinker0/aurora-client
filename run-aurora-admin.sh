#!/usr/bin/env bash
export PATH="/opt/homebrew/bin:$PATH"
# Avoid using global caches that may contain incompatible wheels.
export PANTS_CACHE_DIR="${PWD}/.cache/pants"
export PANTS_PEX_PATH="${PWD}/.cache/pants/pex"
export PEX_ROOT="${PWD}/.cache/pex"
export PANTS_NAMED_CACHES_DIR="${PWD}/.cache/pants/named_caches"

# Use only local wheels to keep resolution deterministic.
export PIP_NO_INDEX="1"
export PIP_FIND_LINKS="file://${PWD}/3rdparty/python/wheels"

./pants package //src/main/python/apache/aurora/kerberos:kaurora_admin \
    && python3 build-support/flatten_dist_pex.py \
    && arch -x86_64 /usr/bin/python3 \
      dist/src.main.python.apache.aurora.kerberos/kaurora_admin.pex "$@"
