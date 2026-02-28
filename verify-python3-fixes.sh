#!/bin/bash
# Regression test for Aurora Python 3 Compatibility fixes

set -e

REPO_ROOT=$(git rev-parse --show-toplevel)
cd "$REPO_ROOT"

echo "--- Checking Protobuf Version ---"
# Verify that protobuf version is 3.5.1 and not 2.6.1
./pants package src/main/python/apache/aurora/executor:thermos_executor > /dev/null 2>&1
PROTOBUF_VERSION=$(PEX_INTERPRETER=1 arch -x86_64 /usr/bin/python3 dist/src.main.python.apache.aurora.executor/thermos_executor.pex -c "import google.protobuf; print(google.protobuf.__version__)")
echo "Found Protobuf: $PROTOBUF_VERSION"
if [[ "$PROTOBUF_VERSION" != "3.5.1" ]]; then
  echo "FAIL: Expected Protobuf 3.5.1, found $PROTOBUF_VERSION"
  exit 1
fi

echo "--- Checking Pesos Vendor Import ---"
PEX_INTERPRETER=1 arch -x86_64 /usr/bin/python3 dist/src.main.python.apache.aurora.executor/thermos_executor.pex -c "from pesos.vendor.mesos import mesos_pb2; print('Pesos import OK')"

echo "--- Checking Thermos Monitoring Import ---"
PEX_INTERPRETER=1 arch -x86_64 /usr/bin/python3 dist/src.main.python.apache.aurora.executor/thermos_executor.pex -c "import apache.thermos.monitoring.detector; print('Thermos Monitoring import OK')"

echo "--- Checking Thermos Runner Resource Extraction ---"
# Rebuild everything and embed runner
./pants package src/main/python/apache/thermos/runner:thermos_runner > /dev/null 2>&1
echo "Rebuilding executor..."
./pants package src/main/python/apache/aurora/executor:thermos_executor > /dev/null 2>&1
cp dist/src.main.python.apache.aurora.executor/thermos_executor.pex dist/thermos_executor.pex
cp dist/src.main.python.apache.thermos.runner/thermos_runner.pex dist/thermos_runner.pex
python3 build-support/embed_runner_in_executor.py

# Simulate sandbox extraction
SANDBOX=$(mktemp -d)
export MESOS_SANDBOX="$SANDBOX"
cd "$SANDBOX"

# Use an isolated PEX_ROOT so the zip-injected executor is always re-extracted fresh
FRESH_PEX_ROOT=$(mktemp -d)
export PEX_ROOT="$FRESH_PEX_ROOT"

PEX_INTERPRETER=1 arch -x86_64 /usr/bin/python3 "$REPO_ROOT/dist/thermos_executor.pex" -c "from apache.aurora.executor.bin.thermos_executor_main import dump_runner_pex; path = dump_runner_pex(); print('Extracted runner to:', path)"

if [[ ! -f "thermos_runner.pex" ]]; then
  echo "FAIL: thermos_runner.pex was not extracted to sandbox"
  exit 1
fi

# Verify header of extracted pex to ensure no text-mode corruption
if [[ "$(head -c 2 thermos_runner.pex)" != "#!" ]]; then
  echo "FAIL: thermos_runner.pex header is corrupted (likely text-mode extraction)"
  exit 1
fi

echo "--- Checking Binary File Handling Logic (Static Audit) ---"
# Check if we still have any 'w' or 'a' for binary streams
grep "open(.*, 'w')" "$REPO_ROOT/src/main/python/apache/thermos/core/process.py" && { echo "FAIL: process.py still uses text write mode"; exit 1; } || true
grep "open(.*, 'a')" "$REPO_ROOT/src/main/python/apache/thermos/core/helper.py" && { echo "FAIL: helper.py still uses text append mode"; exit 1; } || true
grep "open(.*, 'rb')" "$REPO_ROOT/src/main/python/apache/thermos/common/ckpt.py" > /dev/null || { echo "FAIL: ckpt.py missing binary read mode"; exit 1; }

echo "--- ALL TESTS PASSED ---"
rm -rf "$SANDBOX"
