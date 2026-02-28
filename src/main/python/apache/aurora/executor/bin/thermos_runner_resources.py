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

from __future__ import print_function

import os
import sys
import zipfile

from twitter.common import log

CWD = os.environ.get('MESOS_SANDBOX', '.')


# TODO(wickman) Consider just having the OSS version require pip installed
# thermos_runner binaries on every machine and instead of embedding the pex
# as a resource, shell out to one on the PATH.
def dump_runner_pex():
  pex_name = 'thermos_runner.pex'
  runner_pex = os.path.join(os.path.abspath(CWD), pex_name)
  resource_path = 'apache/aurora/executor/resources/' + pex_name

  # Read directly from the running PEX zip to avoid using the unzipped cache,
  # which contains a 0-byte placeholder at build time.
  pex_file = os.environ.get('PEX', sys.argv[0])
  log.info('dump_runner_pex: pex_file=%s resource_path=%s' % (pex_file, resource_path))

  extracted = False
  if zipfile.is_zipfile(pex_file):
    try:
      with zipfile.ZipFile(pex_file, 'r') as zf:
        try:
          info = zf.getinfo(resource_path)
          log.info('dump_runner_pex: found in zip, file_size=%d' % info.file_size)
          if info.file_size > 0:
            with zf.open(resource_path) as src, open(runner_pex, 'wb') as dst:
              dst.write(src.read())
            extracted = True
          else:
            log.warning('dump_runner_pex: resource in zip is 0 bytes, falling back to pkg_resources')
        except KeyError:
          log.warning('dump_runner_pex: resource not found in zip: %s' % resource_path)
    except Exception as e:
      log.warning('dump_runner_pex: zipfile read failed: %s' % e)
  else:
    log.warning('dump_runner_pex: pex_file is not a zip: %s' % pex_file)

  if not extracted:
    import pkg_resources
    import apache.aurora.executor.resources
    import shutil
    log.info('dump_runner_pex: falling back to pkg_resources')
    with open(runner_pex, 'wb') as fp:
      shutil.copyfileobj(
          pkg_resources.resource_stream(apache.aurora.executor.resources.__name__, pex_name),
          fp)

  size = os.path.getsize(runner_pex)
  log.info('dump_runner_pex: wrote %d bytes to %s' % (size, runner_pex))
  if size == 0:
    raise RuntimeError(
        'thermos_runner.pex was extracted as 0 bytes. '
        'Ensure embed_runner_in_executor.py was run after building thermos_executor.')

  return runner_pex
