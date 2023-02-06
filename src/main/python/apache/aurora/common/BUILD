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
  name = '_common',
  sources = ['*.py'],
  interpreter_constraints = ['CPython==2.7.*', 'CPython>=3.5'],
)

python_distribution(
    name = "common",
    dependencies = [
        "//:3rdparty#certifi",
        "//:3rdparty#chardet",
        "//:3rdparty#idna",
        "//:3rdparty#pex",
        "//:3rdparty#pystachio",
        "//:3rdparty#requests",
        "//:3rdparty#subprocess32",
        "//:3rdparty#thrift",
        "//:3rdparty#twitter.common.collections",
        "//:3rdparty#twitter.common.lang",
        "//:3rdparty#twitter.common.log",
        "//:3rdparty#urllib3",
        "api/src/main/thrift/org/apache/aurora/gen",
        'src/main/python/apache/aurora/common',
    ],
    interpreter_constraints = ['CPython==2.7.*', 'CPython>=3.5'],
    provides = python_artifact(
        name = "apache.aurora.common",
        description = "Aurora common libraries.",
        license = "Apache License, Version 2.0",
        version = open(".auroraversion").read().strip().upper(),
    ),
)
