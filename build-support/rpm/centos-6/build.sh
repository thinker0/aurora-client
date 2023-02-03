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

tar --strip-components 1 -C src -xf /src.tar.gz

cp -R /specs/rpm .
cd rpm
# python mesos centos 6
cat << __EOF > ./SOURCES/aurora-pants.ini
[GLOBAL]
print_exception_stacktrace: True

[python-repos]
repos: ['third_party/', 'https://svn.apache.org/repos/asf/aurora/3rdparty/centos/6/python/']
__EOF

# Replace hyphens in version ID.
export AURORA_VERSION=$(echo $AURORA_VERSION | tr '-' '_')
export LC_ALL=en_US.UTF-8
export LANG=en_US.UTF-8

make srpm
yum-builddep -y ../../../dist/rpmbuild/SRPMS/*
make rpm

yum -y install createrepo
cd ../../../dist/rpmbuild/RPMS/x86_64
createrepo .
