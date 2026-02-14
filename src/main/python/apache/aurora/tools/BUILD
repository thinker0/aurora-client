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

THERMOS_SOURCE = 'thermos.py'
OBSERVER_SOURCE = 'thermos_observer.py'

python_sources(
  name = '_tools',
  sources = [
    '*.py',
    '**/*.py',
    f'!{THERMOS_SOURCE}',
    f'!{OBSERVER_SOURCE}',
  ],
  dependencies = [
    '3rdparty/python#CherryPy',
    '3rdparty/python#MarkupSafe',
    'src/main/python/twitter/common:common_sources',
    'src/main/python:process_handle_ps_shim',
    'src/main/python/apache/aurora/executor',
    'src/main/python/apache/thermos/cli',
    'src/main/python/apache/thermos/common',
    'src/main/python/apache/thermos/monitoring',
    'src/main/python/apache/thermos/observer',
  ],
)

python_sources(
  name = '_thermos',
  sources = [THERMOS_SOURCE],
  dependencies = [
    ':_tools',
  ],
)

pex_binary(
  name = 'thermos',
  entry_point = 'apache.aurora.tools.thermos',
  dependencies = [':_thermos'],
)

python_sources(
  name = '_thermos_observer',
  sources = [OBSERVER_SOURCE],
  dependencies = [
    ':_tools',
  ],
)

pex_binary(
  name = 'thermos_observer',
  entry_point = 'apache.aurora.tools.thermos_observer',
  dependencies = [':_thermos_observer'],
)

python_sources(
  name = 'tools',
  dependencies = [
    ':_thermos',
    ':_thermos_observer',
    ':_tools',
  ],
)
