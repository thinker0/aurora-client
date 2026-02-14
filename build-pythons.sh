#!/usr/bin/env bash
set -ex

export PANTS_WORKDIR="${PANTS_WORKDIR:-.pants.d}"
export PANTS_BOOTSTRAPDIR="${PANTS_BOOTSTRAPDIR:-.pants.d/bootstrap}"
export PANTS_LOCAL_STORE_DIR="${PANTS_LOCAL_STORE_DIR:-.pants.d/lmdb_store}"

# Builds Aurora client PEX binaries.
./run-pants-local-wheels.sh package src/main/python/apache/aurora/kerberos:kaurora "$@"
if [[ -f dist/src.main.python.apache.aurora.kerberos/kaurora.pex ]]; then
  mv -f dist/src.main.python.apache.aurora.kerberos/kaurora.pex dist/aurora.pex
fi
./run-pants-local-wheels.sh package src/main/python/apache/aurora/kerberos:kaurora_admin "$@"
if [[ -f dist/src.main.python.apache.aurora.kerberos/kaurora_admin.pex ]]; then
  mv -f dist/src.main.python.apache.aurora.kerberos/kaurora_admin.pex dist/aurora_admin.pex
fi

# Builds Aurora Thermos and GC executor PEX binaries.
./run-pants-local-wheels.sh package src/main/python/apache/aurora/executor:thermos_executor "$@"
./run-pants-local-wheels.sh package src/main/python/apache/aurora/tools:thermos "$@"
./run-pants-local-wheels.sh package src/main/python/apache/aurora/tools:thermos_observer "$@"
./run-pants-local-wheels.sh package src/main/python/apache/thermos/runner:thermos_runner "$@"

# Packages the Thermos runner within the Thermos executor.
python3 build-support/embed_runner_in_executor.py "$@"
