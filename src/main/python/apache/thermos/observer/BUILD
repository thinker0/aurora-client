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
  name = '_observer',
  sources = ['**/*.py'],
  interpreter_constraints = ['CPython==2.7.*', 'CPython>=3.5'],
  dependencies = [
    '//:3rdparty#bottle',
    '//:3rdparty#mako',
    '//:3rdparty#pex',
    '//:3rdparty#pystachio',
    '//:3rdparty#twitter.common.exceptions',
    '//:3rdparty#twitter.common.http',
    '//:3rdparty#twitter.common.lang',
    '//:3rdparty#twitter.common.log',
    '//:3rdparty#twitter.common.metrics',
    '//:3rdparty#twitter.common.quantity',
    'api/src/main/thrift/org/apache/thermos',

    # covering libraries
    'src/main/python/apache/thermos/common',
    'src/main/python/apache/thermos/config',
    'src/main/python/apache/thermos/monitoring',

    ':ui',
  ],
)

python_distribution(
  name = 'observer',
  dependencies = [
    ':_observer',
  ],
  provides = python_artifact(
    name = 'apache.thermos.observer',
    version = open('.auroraversion').read().strip().upper(),
    description = 'The Thermos observer web interface libraries.',
  ),
)
