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
  name = '_admin',
  sources = ['*.py', '**/*.py'],
  dependencies = [
    'src/main/python/twitter/common:common_sources',
    '3rdparty/python#thrift',
    'api/src/main/thrift/org/apache/aurora/gen',
    'src/main/python/apache/aurora/client',
    'src/main/python/apache/aurora/common',
    'src/main/python/apache/aurora/config',
  ],
  resolve = 'python-default',
)

pex_binary(
  name = 'aurora_admin',
  entry_point = 'apache.aurora.admin.aurora_admin:proxy_main',
  dependencies = [
    'src/main/python:admin_src',
    'api/src/main/thrift/org/apache/aurora/gen:gen',
    ':_admin',
  ],
  include_sources = True,
  layout = 'zipapp',
  resolve = 'python-admin',
)
