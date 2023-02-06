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
  name = '_monitoring',
  sources = ['**/*.py'],
  interpreter_constraints = ['CPython==2.7.*', 'CPython>=3.5'],
  dependencies = [
    '//:3rdparty#jmespath',
    '//:3rdparty#psutil',
    '//:3rdparty#twitter.common.collections',
    '//:3rdparty#twitter.common.concurrent',
    '//:3rdparty#twitter.common.dirutil',
    '//:3rdparty#twitter.common.exceptions',
    '//:3rdparty#twitter.common.lang',
    '//:3rdparty#twitter.common.log',
    '//:3rdparty#twitter.common.quantity',
    '//:3rdparty#twitter.common.recordio',
    'api/src/main/thrift/org/apache/thermos',
    'src/main/python/apache/thermos/common',
  ],
)

python_distribution(
  name = 'monitoring',
  dependencies = [
    ':_monitoring',
  ],
  provides = python_artifact(
    name = 'apache.thermos.monitoring',
    version = open('.auroraversion').read().strip().upper(),
    description = 'Thermos monitoring library.',
    wheel_config_settings={"--global-option": ["--python-tag", "py37.py38.py39"]},
  )
)
