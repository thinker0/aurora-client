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
  name = 'kerberos_auth',
  sources = ['*.py', '**/*.py'],
  dependencies = [
    '3rdparty/python#requests-kerberos',
    'src/main/python/apache/aurora/common',
  ],
)

python_sources(
  name = '_kerberos',
  sources = ['*.py', '**/*.py'],
  dependencies = [
    ':kerberos_auth',
    'src/main/python/apache/aurora/admin:_admin',
    'src/main/python/apache/aurora/client',
  ],
)

pex_binary(
  name = 'kaurora',
  entry_point = 'apache.aurora.client.cli.client:proxy_main',
  dependencies = [
    ':_kerberos',
    'src/main/python/apache/aurora/client:_client',
  ],
)

pex_binary(
  name = 'kaurora_admin',
  entry_point = 'apache.aurora.admin.aurora_admin:proxy_main',
  dependencies = [
    ':_kerberos',
    'src/main/python/apache/aurora/admin:_admin',
  ],
  layout = 'zipapp',
)

python_sources(
  name = 'kerberos',
  dependencies = [
    ':_kerberos',
  ],
)
