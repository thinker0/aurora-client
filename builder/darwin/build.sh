#!/bin/bash
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

set -ex

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"
BUILD_TAR="${ROOT_DIR}/build.tar.gz"
SCRATCH_DIR="${ROOT_DIR}/scratch"

if [[ ! -f "${BUILD_TAR}" ]]; then
  echo "Missing build tarball: ${BUILD_TAR}"
  exit 1
fi

rm -rf "${SCRATCH_DIR}"
mkdir -p "${SCRATCH_DIR}"
tar -xf "${BUILD_TAR}" -C "${SCRATCH_DIR}"

WORK_DIR="${SCRATCH_DIR}/apache-aurora-${AURORA_VERSION}"
if [[ ! -d "${WORK_DIR}" ]]; then
  echo "Expected extracted directory not found: ${WORK_DIR}"
  exit 1
fi

cd "${WORK_DIR}"
sed -i '' "s/version = '16.19.1'/version = '20.18.1'/g" build.gradle
sed -i '' "s/version = '16.19.1'/version = '20.18.1'/g" build.gradle
sed -i '' "s/version = '20.11.0'/version = '20.18.1'/g" build.gradle

# Explicitly set JAVA_HOME to Java 11 for Gradle compatibility
export JAVA_HOME="/Users/thinker0/Library/Java/JavaVirtualMachines/azul-11.0.25/Contents/Home"
export PATH=${JAVA_HOME}/bin:${PATH}
echo "Using Java Home: $JAVA_HOME"
"$JAVA_HOME"/bin/java -version
java -version
export AURORA_VERSION=$(echo $AURORA_VERSION | tr '-' '_')
export LC_ALL=en_US.UTF-8
export LANG=en_US.UTF-8

# Downloads Gradle executable.
wget https://services.gradle.org/distributions/gradle-${GRADLE_VERSION}-bin.zip
unzip gradle-${GRADLE_VERSION}-bin.zip

export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:/usr/local/lib
# Builds the Aurora scheduler.
./gradle-${GRADLE_VERSION}/bin/gradle installDist --stacktrace

export PANTS_WORKDIR="${PANTS_WORKDIR:-.pants.d}"
export PANTS_BOOTSTRAPDIR="${PANTS_BOOTSTRAPDIR:-.pants.d/bootstrap}"
export PANTS_LOCAL_STORE_DIR="${PANTS_LOCAL_STORE_DIR:-.pants.d/lmdb_store}"
export PANTS_PYTHON_BOOTSTRAP_SEARCH_PATH="/opt/homebrew/opt/python@3.9/bin/python3.9"

PANTS_REPO_FLAGS=(
  "--python-repos-find-links=[\"file://${WORK_DIR}/3rdparty/python/wheels\"]"
  "--python-repos-indexes=[]"
)

# Builds Aurora client PEX binaries.
./pants package src/main/python/apache/aurora/kerberos:kaurora "${PANTS_REPO_FLAGS[@]}"
if [[ -f dist/kaurora.pex ]]; then
  mv dist/kaurora.pex dist/aurora.pex
elif [[ -f dist/src.main.python.apache.aurora.kerberos/kaurora.pex ]]; then
  mv dist/src.main.python.apache.aurora.kerberos/kaurora.pex dist/aurora.pex
else
  echo "kaurora.pex not found in dist/"
  exit 1
fi
./pants package src/main/python/apache/aurora/kerberos:kaurora_admin "${PANTS_REPO_FLAGS[@]}"
if [[ -f dist/kaurora_admin.pex ]]; then
  mv dist/kaurora_admin.pex dist/aurora_admin.pex
elif [[ -f dist/src.main.python.apache.aurora.kerberos/kaurora_admin.pex ]]; then
  mv dist/src.main.python.apache.aurora.kerberos/kaurora_admin.pex dist/aurora_admin.pex
else
  echo "kaurora_admin.pex not found in dist/"
  exit 1
fi
artifact_dir="${artifact_dir:-${ROOT_DIR}/artifacts/aurora-darwin}"
mkdir -p "${artifact_dir}"
cp dist/aurora.pex ~/bin/aurora
cp dist/aurora_admin.pex ~/bin/aurora_admin
# Builds Aurora Thermos and GC executor PEX binaries.
./pants package src/main/python/apache/aurora/executor:thermos_executor "${PANTS_REPO_FLAGS[@]}"
./pants package src/main/python/apache/aurora/tools:thermos "${PANTS_REPO_FLAGS[@]}"
./pants package src/main/python/apache/aurora/tools:thermos_observer "${PANTS_REPO_FLAGS[@]}"
./pants package src/main/python/apache/thermos/runner:thermos_runner "${PANTS_REPO_FLAGS[@]}"
if [[ -f dist/thermos_runner.pex ]]; then
  true
elif [[ -f dist/src.main.python.apache.thermos.runner/thermos_runner.pex ]]; then
  mv dist/src.main.python.apache.thermos.runner/thermos_runner.pex dist/thermos_runner.pex
else
  echo "thermos_runner.pex not found in dist/"
  exit 1
fi

# Packages the Thermos runner within the Thermos executor.
build-support/embed_runner_in_executor.py

# Copy all pex artifacts after executor embedding.
cp dist/*.pex "${artifact_dir}/"
