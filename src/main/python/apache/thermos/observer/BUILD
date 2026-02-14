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


resources(
  name = 'ui',
  sources = ['**/assets/*', '**/*.tpl'],
)

python_sources(
  name = 'observer',
  sources = ['*.py', '**/*.py'],
  dependencies = [
    '3rdparty/python#CherryPy',
    '3rdparty/python#expiringdict',
    '3rdparty/python#redis-py-cluster',
    '3rdparty/python#bottle',
    '3rdparty/python#mako',
    '3rdparty/python#pex',
    '3rdparty/python#pystachio',
    'src/main/python/twitter/common:common_sources',
    'api/src/main/thrift/org/apache/thermos',

    # covering libraries
    'src/main/python/apache/thermos/common',
    'src/main/python/apache/thermos/config',
    'src/main/python/apache/thermos/monitoring',

    ':ui',
  ],
)
