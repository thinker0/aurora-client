#!/usr/bin/env python
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
"""Package thermos_runner within thermos_executor."""

import contextlib
import os
import shutil
import tempfile
import zipfile
from pathlib import Path

EXECUTOR_PEX = 'dist/thermos_executor.pex'
RUNNER_PEX = 'dist/thermos_runner.pex'
RESOURCE_INIT = 'apache/aurora/executor/resources/__init__.py'
RESOURCE_RUNNER = 'apache/aurora/executor/resources/thermos_runner.pex'

executor_path = Path(EXECUTOR_PEX)
runner_path = Path(RUNNER_PEX)

if not runner_path.is_file() or runner_path.stat().st_size == 0:
    raise SystemExit(f'{RUNNER_PEX} is missing or empty')

if not executor_path.is_file():
    raise SystemExit(f'{EXECUTOR_PEX} is missing')

tmp_fd, tmp_path = tempfile.mkstemp(
    dir=str(executor_path.parent),
    prefix=f'{executor_path.name}.',
    suffix='.tmp',
)
os.close(tmp_fd)

tmp_zip_fd, tmp_zip_path = tempfile.mkstemp(
    dir=str(executor_path.parent),
    prefix=f'{executor_path.name}.',
    suffix='.zip',
)
os.close(tmp_zip_fd)


def read_pex_prefix(path):
    with path.open('rb') as handle:
        data = handle.read()
    marker = data.find(b'PK\x03\x04')
    if marker == -1:
        raise SystemExit(f'{EXECUTOR_PEX} does not contain a ZIP header')
    return data[:marker]


try:
    prefix = read_pex_prefix(executor_path)
    with contextlib.closing(zipfile.ZipFile(executor_path, 'r')) as src:
        with contextlib.closing(zipfile.ZipFile(tmp_zip_path, 'w')) as dst:
            existing = set(src.namelist())
            for info in src.infolist():
                if info.filename == RESOURCE_RUNNER:
                    continue
                dst.writestr(info, src.read(info.filename))
            if RESOURCE_INIT not in existing:
                dst.writestr(RESOURCE_INIT, '')
            dst.write(RUNNER_PEX, RESOURCE_RUNNER)
    with open(tmp_path, 'wb') as final_handle:
        final_handle.write(prefix)
        with open(tmp_zip_path, 'rb') as zip_handle:
            shutil.copyfileobj(zip_handle, final_handle)
    shutil.copystat(executor_path, tmp_path)
    os.replace(tmp_path, executor_path)
finally:
    if os.path.exists(tmp_path):
        os.unlink(tmp_path)
    if os.path.exists(tmp_zip_path):
        os.unlink(tmp_zip_path)
