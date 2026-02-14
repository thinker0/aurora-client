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
  name = '_client',
  sources = ['*.py', '**/*.py'],
  dependencies = [
    '3rdparty/python#certifi',
    '3rdparty/python#chardet',
    '3rdparty/python#idna',
    '3rdparty/python#pex',
    '3rdparty/python#pystachio',
    '3rdparty/python#requests',
    'src/main/python/twitter/common:common_sources',
    'src/main/python/twitter/common/zookeeper',
    '3rdparty/python#thrift',
    '3rdparty/python#urllib3',
    'api/src/main/thrift/org/apache/aurora/gen',
    'src/main/python/apache/aurora/common',
    'src/main/python/apache/aurora/client/cli:auroraversion',
    'src/main/python/apache/aurora/config',
    'src/main/python:process_handle_ps_shim',
    'src/main/python/apache/thermos/common',
    'src/main/python/apache/thermos/config',
  ],
)

pex_binary(
  name='aurora',
  entry_point = 'apache.aurora.client.cli.client:proxy_main',
  dependencies = [
    ':_client'
  ],
)

python_sources(
  name = 'client',
  dependencies = [
    ':_client',
  ],
)
