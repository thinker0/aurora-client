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

thrift_sources(
  name = '_api',
  sources = [
    'api.thrift',
  ],
  dependencies = [
    '3rdparty/python#thrift',
  ],
)

thrift_sources(
  name = '_test',
  sources = ['*test.thrift'],
  dependencies = [
    '3rdparty/python#thrift',
  ],
)

thrift_sources(
  name = '_storage',
  sources = ['storage.thrift'],
  dependencies = [
    '3rdparty/python#thrift',
    ':_api',
  ],
)

target(
  name = 'gen',
  dependencies = [
    ':_api',
    ':_test',
    ':_storage',
  ],
)

python_distribution(
  name = 'aurora_thrift_dist',
  dependencies = [
    ':gen',
  ],
  provides = python_artifact(
    name = 'aurora-thrift',
    version = '0.0.0',
  ),
)
