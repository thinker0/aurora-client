#!/bin/bash
# Builds CentOS 7 RPM and verifies thermos_runner.pex is correctly embedded
# in the thermos_executor binary.

set -ex

REPO_ROOT=$(git rev-parse --show-toplevel)
cd "$REPO_ROOT"

AURORA_VERSION=$(cat .auroraversion | tr -d '[:space:]')
BUILDER="$1"
RELEASE_TAR="apache-aurora-${AURORA_VERSION}.tar.gz"
ARTIFACT_DIR="artifacts/aurora-${BUILDER}"
CPIO_BIN=$(command -v cpio || true)

if [[ -z "$CPIO_BIN" ]]; then
  echo "FAIL: cpio not found in PATH"
  exit 1
fi

if [[ "$CPIO_BIN" != /* ]]; then
  CPIO_BIN=$(python3 - "$CPIO_BIN" <<'EOF'
import os
import sys

print(os.path.realpath(sys.argv[1]))
EOF
)
fi

echo "=== Building CentOS 7 RPM (version: ${AURORA_VERSION}) ==="
echo ./build-artifact.sh "${BUILDER}" "${RELEASE_TAR}" "${AURORA_VERSION}"

echo ""
echo "=== Verifying thermos_runner.pex is embedded in RPM ==="

# Find the built RPM
RPM_FILE=$(find "${ARTIFACT_DIR}/rpmbuild/RPMS" -name "aurora-executor-*.rpm" | head -1)
if [[ -z "$RPM_FILE" ]]; then
  echo "FAIL: No aurora-executor RPM file found in ${ARTIFACT_DIR}/rpmbuild/RPMS"
  exit 1
fi
RPM_FILE_ABS=$(python3 - "$RPM_FILE" <<'EOF'
import os
import sys

print(os.path.realpath(sys.argv[1]))
EOF
)
echo "RPM: ${RPM_FILE_ABS}"

# Extract thermos_executor from the RPM
TMPDIR=$(mktemp -d)
pushd "$TMPDIR" > /dev/null
rpm2cpio "$RPM_FILE_ABS" | "$CPIO_BIN" -idm --quiet ./usr/bin/thermos_executor 2>/dev/null
EXECUTOR="$TMPDIR/usr/bin/thermos_executor"

if [[ ! -f "$EXECUTOR" ]]; then
  echo "FAIL: thermos_executor not found in RPM"
  rm -rf "$TMPDIR"
  exit 1
fi

EXECUTOR_SIZE=$(wc -c < "$EXECUTOR")
echo "thermos_executor size: ${EXECUTOR_SIZE} bytes"

# Check embedded thermos_runner.pex inside the PEX zip
python3 - "$EXECUTOR" <<'EOF'
import sys, zipfile

pex_file = sys.argv[1]
resource_path = 'apache/aurora/executor/resources/thermos_runner.pex'

if not zipfile.is_zipfile(pex_file):
    print(f"FAIL: {pex_file} is not a zip/pex file")
    sys.exit(1)

with zipfile.ZipFile(pex_file, 'r') as zf:
    try:
        info = zf.getinfo(resource_path)
        size = info.file_size
        print(f"Embedded thermos_runner.pex size: {size:,} bytes")
        if size == 0:
            print("FAIL: thermos_runner.pex is 0 bytes — embed_runner_in_executor.py was not run!")
            sys.exit(1)
        else:
            print("OK: thermos_runner.pex is properly embedded")
    except KeyError:
        print(f"FAIL: {resource_path} not found in PEX zip — embed step was not run!")
        sys.exit(1)
EOF

popd > /dev/null
rm -rf "$TMPDIR"

echo ""
echo "=== ALL CHECKS PASSED ==="
