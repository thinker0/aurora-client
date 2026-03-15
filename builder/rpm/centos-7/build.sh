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

mkdir -p /scratch/src
cd /scratch

tar --warning=no-unknown-keyword --strip-components 1 -C src -xf /src.tar.gz

# Bootstrap thrift compiler if not pre-injected by patch.py.
# Required by pants apache-thrift backend; pants does NOT auto-compile it.
if [ ! -f /scratch/src/build-support/thrift/thrift ]; then
    echo "No pre-built thrift binary found; compiling thrift from source..."
    THRIFT_VERSION="0.22.0"
    THRIFT_URL="https://archive.apache.org/dist/thrift/${THRIFT_VERSION}/thrift-${THRIFT_VERSION}.tar.gz"
    cd /tmp
    wget -q "${THRIFT_URL}" -O thrift-src.tar.gz
    tar xzf thrift-src.tar.gz
    cd "thrift-${THRIFT_VERSION}"
    cmake3 \
        -DBUILD_TESTING=OFF \
        -DBUILD_EXAMPLES=OFF \
        -DBUILD_TUTORIALS=OFF \
        -DBUILD_COMPILER=ON \
        -DWITH_CPP=OFF \
        -DWITH_PYTHON=OFF \
        -DWITH_JAVA=OFF \
        -DWITH_ERLANG=OFF \
        -DWITH_NODEJS=OFF \
        -DCMAKE_BUILD_TYPE=Release \
        .
    make -j"$(nproc)" thrift-compiler
    mkdir -p /scratch/src/build-support/thrift
    install -m 755 compiler/cpp/bin/thrift /scratch/src/build-support/thrift/thrift
    echo "Compiled thrift $(/scratch/src/build-support/thrift/thrift --version)"
    cd /scratch
fi

# Install thrift to /usr/local/bin so pants can find it via <PATH> fallback.
if [ -f /scratch/src/build-support/thrift/thrift ]; then
    install -m 755 /scratch/src/build-support/thrift/thrift /usr/local/bin/thrift
fi

cp -R /specs/rpm .
cd rpm

# Replace hyphens in version ID.
export AURORA_VERSION=$(echo $AURORA_VERSION | tr '-' '_')
MESOS_VERSION=1.11.0
export LC_ALL=en_US.UTF-8
export LANG=en_US.UTF-8
export PYTHON=/usr/bin/python3.8
export PANTS_PYTHON=/usr/bin/python3.8
export PANTS_PYTHON_INTERPRETER_CONSTRAINTS='["CPython==3.8.*"]'
export PANTS_PYTHON_BOOTSTRAP_SEARCH_PATH='["/usr/bin/python3.8"]'
export PANTS_PYTHON_REPOS_FIND_LINKS='["file:///wheels"]'
export PANTS_PYTHON_REPOS_PATH_MAPPINGS='["AURORA_WHEELS_DIR|/wheels"]'
export TAR_OPTIONS="--no-same-owner"

make srpm
yum-builddep -y ../../../dist/rpmbuild/SRPMS/*
yum remove -y git

# Seed with pre-built wheels from the (read-only) host mount, then
# rebuild any CentOS-7/Python-3.8 wheels on top.  We never write back
# to /wheels so the host copy (Rocky-8 wheels) is left untouched.
cp -R --no-preserve=ownership /wheels/. /scratch/src/3rdparty/python/wheels/
(cd /scratch/src \
  && python3.8 build-support/build_wheels.py \
  && python3.8 -m pip wheel --no-deps -w 3rdparty/python/wheels pykerberos==1.2.1)

# Regenerate lockfile with Linux/Python 3.8 wheel hashes so pex hash
# validation passes when rpmbuild invokes pants package.
(cd /scratch/src && ./pants generate-lockfiles --resolve=python-default)

custom_source="/dist/rpmbuild/SOURCES/apache-aurora-${AURORA_VERSION}.tar.gz"
tar --warning=no-unknown-keyword -C /scratch \
  -czf "${custom_source}" \
  --transform "s,^src,apache-aurora-${AURORA_VERSION}," \
  src

rpmbuild \
  --define "_topdir /dist" \
  --define "_builddir %{_topdir}/rpmbuild/BUILD" \
  --define "_buildrootdir %{_topdir}/rpmbuild/BUILDROOT" \
  --define "_rpmdir %{_topdir}/rpmbuild/RPMS" \
  --define "_srcrpmdir %{_topdir}/rpmbuild/SRPMS" \
  --define "_specdir $(pwd)" \
  --define "_sourcedir  %{_topdir}/rpmbuild/SOURCES" \
  --define "AURORA_VERSION ${AURORA_VERSION}" \
  --define "AURORA_INTERNAL_VERSION ${AURORA_VERSION}" \
  --define "MESOS_VERSION ${MESOS_VERSION}" \
  --define "GRADLE_VERSION ${GRADLE_VERSION}" \
  --define "__python3 /usr/bin/python3.8" \
  -ba aurora.spec

yum -y install createrepo
cd ../../../dist/rpmbuild/RPMS/x86_64
createrepo .
