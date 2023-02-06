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


python_sources(
  name = '_executor',
  sources = ['**/*.py'],
  interpreter_constraints = ['CPython==2.7.*', 'CPython>=3.5'],
  dependencies = [
    '//:3rdparty#mesos.interface',
    '//:3rdparty#pex',
    # To prevent an alpha version of protobuf from being pulled down by pants we
    # specify protobuf here. See AURORA-1128 for more details.
    '//:3rdparty#protobuf',
    '//:3rdparty#psutil',
    '//:3rdparty#pystachio',
    '//:3rdparty#twitter.common.app',
    '//:3rdparty#twitter.common.concurrent',
    '//:3rdparty#twitter.common.dirutil',
    '//:3rdparty#twitter.common.exceptions',
    '//:3rdparty#twitter.common.lang',
    '//:3rdparty#twitter.common.log',
    '//:3rdparty#twitter.common.metrics',
    '//:3rdparty#twitter.common.quantity',
    '//:3rdparty#twitter.common.string',
    '//:3rdparty#twitter.common.zookeeper',
    'api/src/main/thrift/org/apache/aurora/gen',
    'src/main/python/apache/aurora/common',
    'src/main/python/apache/aurora/config',
    'src/main/python/apache/thermos/common',
    'src/main/python/apache/thermos/config',
    'src/main/python/apache/thermos/core',
    'src/main/python/apache/thermos/monitoring',
  ],
)

pex_binary(
  name = 'thermos_executor',
  entry_point = 'apache.aurora.executor.bin.thermos_executor_main:proxy_main',
  dependencies = [
    ':_executor',
    # TODO(ksweeney): This violates the rule that every library export the same deps as its
    # contained binaries.
    '//:3rdparty#mesos.executor',
  ],
  # The binary can only build when the native Mesos dependency has been prefetched. This tag
  # allows us to skip this target on development machines if necessary.
  tags=['mesos-native']
)

python_distribution(
  name = 'executor',
  dependencies = [
    ':_executor',
    ':thermos_executor',
  ],
  provides = python_artifact(
    name = 'apache.aurora.executor',
    version = open('.auroraversion').read().strip().upper(),
  ),
)
