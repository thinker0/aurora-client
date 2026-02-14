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
export TAR_OPTIONS="--no-same-owner"

make srpm
/usr/bin/sed -i '1s|/usr/bin/python|/usr/bin/python2|' /usr/libexec/urlgrabber-ext-down
/usr/bin/python2 /usr/bin/yum-builddep -y ../../../dist/rpmbuild/SRPMS/*
/usr/bin/python2 /usr/bin/yum remove -y git

# Build wheels inside the container and repack the source tarball
# so rpmbuild uses the updated wheelhouse.
bash /build_wheels.sh
cp -R --no-preserve=ownership /wheels/. /scratch/src/3rdparty/python/wheels/

custom_source="/dist/rpmbuild/SOURCES/apache-aurora-${AURORA_VERSION}.tar.gz"
tar --warning=no-unknown-keyword -C /scratch/src \
  -czf "${custom_source}" \
  --transform "s,^,apache-aurora-${AURORA_VERSION}/," .

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
  -ba aurora.spec

yum -y install createrepo
cd ../../../dist/rpmbuild/RPMS/x86_64
createrepo .
