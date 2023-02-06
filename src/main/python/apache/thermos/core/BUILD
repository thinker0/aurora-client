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
  name = '_core',
  sources = ['**/*.py'],
  interpreter_constraints = ['CPython==2.7.*', 'CPython>=3.5'],
  dependencies = [
    '//:3rdparty#psutil',
    '//:3rdparty#twitter.common.dirutil',
    '//:3rdparty#twitter.common.lang',
    '//:3rdparty#twitter.common.log',
    '//:3rdparty#twitter.common.quantity',
    '//:3rdparty#twitter.common.recordio',
    'api/src/main/thrift/org/apache/aurora/gen',
    'api/src/main/thrift/org/apache/thermos',
    'src/main/python/apache/thermos/common',
    'src/main/python/apache/thermos/config',
  ],
)

python_distribution(
  name = 'core',
  dependencies = [
    ':_core',
  ],
  provides = python_artifact(
    name = 'apache.thermos.core',
    version = open('.auroraversion').read().strip().upper(),
    description = 'The Thermos core state machine.',
  )
)
