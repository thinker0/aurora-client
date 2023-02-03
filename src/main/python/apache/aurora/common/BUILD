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

python_source(
    name = "common",
    dependencies = [
        "3rdparty/python:certifi",
        "3rdparty/python:chardet",
        "3rdparty/python:idna",
        "3rdparty/python:pex",
        "3rdparty/python:pystachio",
        "3rdparty/python:requests",
        "3rdparty/python:subprocess32",
        "3rdparty/python:thrift",
        "3rdparty/python:twitter.common.collections",
        "3rdparty/python:twitter.common.lang",
        "3rdparty/python:twitter.common.log",
        "3rdparty/python:urllib3",
        "api/src/main/thrift/org/apache/aurora/gen",
    ],
    interpreter_constraints = [
        "CPython==2.7.*",
        "CPython>=3.5",
    ],
    provides = setup_py(
        name = "apache.aurora.common",
        description = "Aurora common libraries.",
        license = "Apache License, Version 2.0",
        version = open(os.path.join(".auroraversion")).read().strip().upper(),
    ),
    sources = ["**/*.py"],
)
