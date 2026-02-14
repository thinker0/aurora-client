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

set -eux

print_available_builders() {
  find builder -name Dockerfile | sed "s/\/Dockerfile$//"
}

realpath() {
  echo "$(cd "$(dirname "$1")"; pwd)/$(basename "$1")"
}

run_build() {
  BUILDER_DIR=$1
  RELEASE_TAR=$2
  AURORA_VERSION=$3
  BUILD_PACKAGE=build.tar.gz
  local package_name="apache-aurora-${AURORA_VERSION}"
  IMAGE_NAME="aurora-$(basename $BUILDER_DIR)"
  echo "Using docker image $IMAGE_NAME"
  echo docker build --pull --platform=linux/amd64 -t "$IMAGE_NAME" "builder/rpm/$BUILDER_DIR"
  docker build --pull --platform=linux/amd64 -t "$IMAGE_NAME" "builder/rpm/$BUILDER_DIR"
  rm -f ${BUILD_PACKAGE} target/${BUILD_PACKAGE}
  artifact_dir="artifacts/$IMAGE_NAME"
  rm -rf "$artifact_dir"
  mkdir -p "$artifact_dir" target
  pushd ../aurora && {
    git archive --format=tar.gz \
        --prefix=apache-aurora-$AURORA_VERSION/ \
        HEAD > ../aurora-client/target/apache-aurora-$AURORA_VERSION.tar.gz
    popd
  } && {
    rm -rf target/$package_name
    pushd target/ && tar xvfz apache-aurora-$AURORA_VERSION.tar.gz && popd
  }
  rsync -a 3rdparty api src pants pants.toml build-support builder specs \
      --exclude '*.venv' \
      "target/${package_name}/"
  PACKAGE_NAME="${package_name}" python3 - <<'PY'
from pathlib import Path
import os
import shutil

path = Path("target") / os.environ["PACKAGE_NAME"] / "build.gradle"
if path.exists():
    text = path.read_text()
    text = text.replace(
        "def python27Executable = ['python2.7', 'python'].find { python ->",
        "def python27Executable = ['python3', 'python2.7', 'python'].find { python ->",
    )
    text = text.replace(
        "sys.version_info >= (2,7) and sys.version_info < (3,)",
        "sys.version_info >= (3,0)",
    )
    text = text.replace("Build requires Python 2.7.", "Build requires Python 3.")

    # Update NodeJS version for UI build (cheerio@1.2.0 requires >=20.18.1).
    text = text.replace("version = '20.11.0'", "version = '20.18.1'")
    path.write_text(text)

codegen_path = Path("target") / os.environ["PACKAGE_NAME"] / "src/main/python/apache/aurora/tools/java/thrift_wrapper_codegen.py"
if codegen_path.exists():
    codegen = codegen_path.read_text()
    old_parse_fields = "return map(parse_field, re.finditer(FIELD_RE, field_str))"
    new_parse_fields = "return list(map(parse_field, re.finditer(FIELD_RE, field_str)))"
    if old_parse_fields in codegen:
        codegen = codegen.replace(old_parse_fields, new_parse_fields)
        codegen_path.write_text(codegen)

# Patch pants.toml for container paths and keep no-index behavior.
pants_toml = Path("target") / os.environ["PACKAGE_NAME"] / "pants.toml"
if pants_toml.exists():
    text = pants_toml.read_text()
    # Keep indexes empty to avoid remote resolution.
    text = text.replace('indexes = ["https://pypi.org/simple"]', 'indexes = []')
    # Point wheelhouse to the container build path.
    text = text.replace(
        "file:///Users/thinker0/opensource/aurora-client/3rdparty/python/wheels",
        f"file:///dist/rpmbuild/BUILD/{os.environ['PACKAGE_NAME']}/3rdparty/python/wheels",
    )
    pants_toml.write_text(text)

# Replace absolute symlinked wheels dir with a real copy so rpmbuild/pants can read it.
wheels_path = Path("target") / os.environ["PACKAGE_NAME"] / "3rdparty/python/wheels"
if wheels_path.is_symlink():
    resolved = wheels_path.resolve()
    wheels_path.unlink()
    if resolved.is_dir():
        shutil.copytree(resolved, wheels_path, symlinks=False)
    else:
        raise RuntimeError(f"Expected wheels directory at {resolved}")

# Replace absolute symlinked thrift binary with a real copy so pants can read it.
thrift_path = Path("target") / os.environ["PACKAGE_NAME"] / "build-support/thrift/thrift"
if thrift_path.is_symlink():
    resolved = thrift_path.resolve()
    thrift_path.unlink()
    if resolved.is_file():
        shutil.copy2(resolved, thrift_path)
    else:
        raise RuntimeError(f"Expected thrift binary at {resolved}")
PY
  pushd target && {
    rsync -a ${package_name}/.auroraversion \
        ${package_name}/src/main/python/apache/aurora/client/cli/
    tar cfz "$RELEASE_TAR" ${package_name}/
    tar cfz ../${BUILD_PACKAGE} "$RELEASE_TAR" \
        ${package_name}
    popd
  }
  docker run \
    -e AURORA_VERSION=$AURORA_VERSION \
    -e GRADLE_VERSION=6.9.4 \
    -e GIT_DISCOVERY_ACROSS_FILESYSTEM=1 \
    --net=host \
    --platform=linux/amd64 \
    -v "$(pwd)/$artifact_dir:/dist:rw" \
    -v "$(pwd)/specs:/specs:ro" \
    -v "$(realpath ${BUILD_PACKAGE}):/src.tar.gz:ro" \
    -t "$IMAGE_NAME" /build.sh
  container=$(docker ps -l -q)
  docker cp $container:/dist "$artifact_dir"
  docker rm "$container"

  echo "Produced artifacts in $artifact_dir:"
  ls -R "$artifact_dir"
}

run_build_platform() {
  BUILDER_DIR=$1
  RELEASE_TAR=$2
  AURORA_VERSION=$3
  BUILD_PACKAGE=build.tar.gz
  local package_name="apache-aurora-${AURORA_VERSION}"
  IMAGE_NAME="aurora-$(basename $BUILDER_DIR)"
  echo "Using docker image $IMAGE_NAME"
  rm -f ${BUILD_PACKAGE}
  artifact_dir="artifacts/$IMAGE_NAME"
  rm -rf "$artifact_dir"
  mkdir -p "$artifact_dir" target
  pushd ../aurora && {
    git archive --format=tar.gz \
        --prefix=apache-aurora-$AURORA_VERSION/ \
        HEAD > ../aurora-client/target/apache-aurora-$AURORA_VERSION.tar.gz
    popd
  } && {
    rm -rf target/$package_name
    pushd target/ && tar xvfz apache-aurora-$AURORA_VERSION.tar.gz && popd
  }
  rsync -a 3rdparty api src pants pants.toml build-support builder specs \
      --exclude '*.venv' \
      "target/${package_name}/"
  PACKAGE_NAME="${package_name}" python3 - <<'PY'
from pathlib import Path
import os
import shutil

path = Path("target") / os.environ["PACKAGE_NAME"] / "build.gradle"
if path.exists():
    text = path.read_text()
    text = text.replace(
        "def python27Executable = ['python2.7', 'python'].find { python ->",
        "def python27Executable = ['python3', 'python2.7', 'python'].find { python ->",
    )
    text = text.replace(
        "sys.version_info >= (2,7) and sys.version_info < (3,)",
        "sys.version_info >= (3,0)",
    )
    text = text.replace("Build requires Python 2.7.", "Build requires Python 3.")

    # Update NodeJS version for UI build (cheerio@1.2.0 requires >=20.18.1).
    text = text.replace("version = '20.11.0'", "version = '20.18.1'")
    path.write_text(text)

codegen_path = Path("target") / os.environ["PACKAGE_NAME"] / "src/main/python/apache/aurora/tools/java/thrift_wrapper_codegen.py"
if codegen_path.exists():
    codegen = codegen_path.read_text()
    old_parse_fields = "return map(parse_field, re.finditer(FIELD_RE, field_str))"
    new_parse_fields = "return list(map(parse_field, re.finditer(FIELD_RE, field_str)))"
    if old_parse_fields in codegen:
        codegen = codegen.replace(old_parse_fields, new_parse_fields)
        codegen_path.write_text(codegen)

# Patch pants.toml for container paths and keep no-index behavior.
pants_toml = Path("target") / os.environ["PACKAGE_NAME"] / "pants.toml"
if pants_toml.exists():
    text = pants_toml.read_text()
    # Keep indexes empty to avoid remote resolution.
    text = text.replace('indexes = ["https://pypi.org/simple"]', 'indexes = []')
    # Point wheelhouse to the local build path.
    wheels_file = (Path("target") / os.environ["PACKAGE_NAME"] / "3rdparty/python/wheels").resolve().as_posix()
    text = text.replace(
        "file:///Users/thinker0/opensource/aurora-client/3rdparty/python/wheels",
        f"file://{wheels_file}",
    )
    pants_toml.write_text(text)

# Replace absolute symlinked wheels dir with a real copy so rpmbuild/pants can read it.
wheels_path = Path("target") / os.environ["PACKAGE_NAME"] / "3rdparty/python/wheels"
if wheels_path.is_symlink():
    resolved = wheels_path.resolve()
    wheels_path.unlink()
    if resolved.is_dir():
        shutil.copytree(resolved, wheels_path, symlinks=False)
    else:
        raise RuntimeError(f"Expected wheels directory at {resolved}")

# Replace absolute symlinked thrift binary with a real copy so pants can read it.
thrift_path = Path("target") / os.environ["PACKAGE_NAME"] / "build-support/thrift/thrift"
if thrift_path.is_symlink():
    resolved = thrift_path.resolve()
    thrift_path.unlink()
    if resolved.is_file():
        shutil.copy2(resolved, thrift_path)
    else:
        raise RuntimeError(f"Expected thrift binary at {resolved}")
PY
  pushd target && {
    rsync -a ${package_name}/.auroraversion \
        ${package_name}/src/main/python/apache/aurora/client/cli/
    tar cfz "$RELEASE_TAR" ${package_name}/
    tar cfz ../${BUILD_PACKAGE} "$RELEASE_TAR" \
        ${package_name}
    popd
  }
  export AURORA_VERSION=$AURORA_VERSION
  export GRADLE_VERSION=6.9.4
  ./builder/$BUILDER_DIR/build.sh
  echo "Produced artifacts in $artifact_dir:"
  ls -R "$artifact_dir"
}

case $# in
  2)
    for builder in $(print_available_builders); do
      echo $builder
      run_build $builder $1 $2
    done
    ;;

  3)
    if [ -d "builder/rpm/$1" ]; then
      run_build "$@"
    else
      run_build_platform "$@"
    fi
    ;;

  *)
    echo 'usage:'
    echo 'to build all artifacts:'
    echo "  $0 RELEASE_TAR AURORA_VERSION"
    echo
    echo 'or to build a specific artifact:'
    echo "  $0 BUILDER RELEASE_TAR AURORA_VERSION"
    echo
    echo 'Where BUILDER is a builder directory in:'
    print_available_builders
    exit 1
    ;;
esac
