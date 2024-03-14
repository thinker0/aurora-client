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

rm -rf ./scratch/
mkdir -p ./scratch/src
cd ./scratch

tar --strip-components 1 -xf ../build.tar.gz

#JAVA_VERSION=1.8
#JAVA_HOME="$(/usr/libexec/java_home -v ${JAVA_VERSION}+ 2> /dev/null)" || true
#export PATH=${JAVA_HOME}/bin:${PATH}
#${JAVA_HOME}/bin/java -version
java -version
# Replace hyphens in version ID.
export AURORA_VERSION=$(echo $AURORA_VERSION | tr '-' '_')
export LC_ALL=en_US.UTF-8
export LANG=en_US.UTF-8

# Downloads Gradle executable.
wget https://services.gradle.org/distributions/gradle-${GRADLE_VERSION}-bin.zip
unzip gradle-${GRADLE_VERSION}-bin.zip

export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:/usr/local/lib
# Builds the Aurora scheduler.
./gradle-${GRADLE_VERSION}/bin/gradle installDist --stacktrace

# Builds Aurora client PEX binaries.
./pants binary src/main/python/apache/aurora/kerberos:kaurora
mv dist/kaurora.pex dist/aurora.pex
./pants binary src/main/python/apache/aurora/kerberos:kaurora_admin
mv dist/kaurora_admin.pex dist/aurora_admin.pex
cp dist/aurora.pex ~/bin/aurora
cp dist/aurora_admin.pex ~/bin/aurora_admin
# Builds Aurora Thermos and GC executor PEX binaries.
./pants binary src/main/python/apache/aurora/executor:thermos_executor
./pants binary src/main/python/apache/aurora/tools:thermos
./pants binary src/main/python/apache/aurora/tools:thermos_observer
./pants binary src/main/python/apache/thermos/runner:thermos_runner

# Packages the Thermos runner within the Thermos executor.
#build-support/embed_runner_in_executor.py
