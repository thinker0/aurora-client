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

cd /scratch/src
ls -la /scratch/src
yum remove -y git
export PATH=/usr/lib/jvm/java-11/bin:${PATH}

# Downloads Gradle executable.
wget https://services.gradle.org/distributions/gradle-${GRADLE_VERSION}-bin.zip
unzip gradle-${GRADLE_VERSION}-bin.zip

# Builds the Aurora scheduler.
./gradle-${GRADLE_VERSION}/bin/gradle installDist

# Builds Aurora client PEX binaries.
./pants binary src/main/python/apache/aurora/kerberos:kaurora
mv dist/kaurora.pex dist/aurora.pex
./pants binary src/main/python/apache/aurora/kerberos:kaurora_admin
mv dist/kaurora_admin.pex dist/aurora_admin.pex

# Builds Aurora Thermos and GC executor PEX binaries.
./pants binary src/main/python/apache/aurora/executor:thermos_executor
./pants binary src/main/python/apache/aurora/tools:thermos
./pants binary src/main/python/apache/aurora/tools:thermos_observer
./pants binary src/main/python/apache/thermos/runner:thermos_runner

# Packages the Thermos runner within the Thermos executor.
build-support/embed_runner_in_executor.py

# Packages the Aurora scheduler and client PEX binaries.
mkdir -p /dist
mv dist/aurora.pex /dist/aurora
mv dist/aurora_admin.pex /dist/aurora_admin
mv dist/thermos_executor.pex /dist/thermos_executor
mv dist/thermos.pex /dist/thermos
mv dist/thermos_observer.pex /dist/thermos_observer
mv dist/thermos_runner.pex /dist/thermos_runner
chmod -R 555 /dist/*