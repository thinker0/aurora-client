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
  sources = ['**/*.py', '!thermos.py', '!thermos_observer.py'],
  interpreter_constraints = ['CPython==2.7.*', 'CPython>=3.5'],
  dependencies = [
    '//:3rdparty#CherryPy',
    '//:3rdparty#twitter.common.app',
    '//:3rdparty#twitter.common.exceptions',
    '//:3rdparty#twitter.common.log',
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

python_source(
  name = 'thermos',
  # TODO(ksweeney): Investigate making this use entry_point instead.
  source = THERMOS_SOURCE,
  dependencies = [
    ':_tools',
  ]
)

python_sources(
  name = '_thermos_observer',
  sources = [OBSERVER_SOURCE],
  dependencies = [
    ':_tools',
  ],
)

python_distribution(
  name = 'thermos_observer',
  # TODO(ksweeney): Investigate making this use entry_point instead.
  dependencies = [
    ':_tools',
    ':_thermos_observer',
  ],
  provides = python_artifact(
    name = 'apache.aurora.tools',
    version = open('.auroraversion').read().strip().upper(),
  ),
)

python_distribution(
  name = 'tools',
  dependencies = [
    ':_thermos',
    ':_thermos_observer',
    ':_tools',
  ],
  provides = python_artifact(
    name = 'apache.aurora.tools',
    version = open('.auroraversion').read().strip().upper(),
  ),
  #.with_binaries({
  #  'thermos': ':thermos',
  #  'thermos_observer': ':thermos_observer',
  #}),
)
