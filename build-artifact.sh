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
  echo docker build --pull -t "$IMAGE_NAME" "builder/rpm/$BUILDER_DIR"
  docker build --pull -t "$IMAGE_NAME" "builder/rpm/$BUILDER_DIR"
  rm -f ${BUILD_PACKAGE}
  artifact_dir="artifacts/$IMAGE_NAME"
  rm -rf "$artifact_dir"
  mkdir -p "$artifact_dir"
  rsync -a 3rdparty api src pants pants.ini build-support builder specs \
      --exclude '*.venv' \
      ${package_name}/
  rsync -a ${package_name}/.auroraversion \
      ${package_name}/src/main/python/apache/aurora/client/cli/
  tar cfz "$RELEASE_TAR" ${package_name}/
  tar cfz ${BUILD_PACKAGE} "$RELEASE_TAR" \
      ${package_name} \
      --exclude build-support/make-python-sdists.venv \
      --exclude build-support/virtualenv-* \
      build-support builder specs
  docker run -it \
    -e AURORA_VERSION=$AURORA_VERSION \
    -e GRADLE_VERSION=5.6.4 \
    -e GIT_DISCOVERY_ACROSS_FILESYSTEM=1 \
    --net=host \
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
  mkdir -p "$artifact_dir"
  rsync -a 3rdparty api src pants pants.ini build-support builder specs \
      --exclude '*.venv' \
      ${package_name}/
  rsync -a ${package_name}/.auroraversion \
      ${package_name}/src/main/python/apache/aurora/client/cli/
  tar cfz "$RELEASE_TAR" ${package_name}/
  tar cfz ${BUILD_PACKAGE} "$RELEASE_TAR" \
      ${package_name} \
      --exclude build-support/make-python-sdists.venv \
      --exclude 'build-support/virtualenv-*' \
      build-support builder specs
  export AURORA_VERSION=$AURORA_VERSION
  export GRADLE_VERSION=5.6.4
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
      exit 1
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
