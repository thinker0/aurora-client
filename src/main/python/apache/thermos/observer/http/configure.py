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

import sys
import types

from twitter.common.http import HttpServer
from twitter.common.http import server as http_server
from twitter.common.http.diagnostics import DiagnosticsEndpoints
from twitter.common.metrics import RootMetrics

from .diagnostics import register_build_properties, register_diagnostics
from .http_observer import BottleObserver
from .vars_endpoint import VarsEndpoint


def configure_server(task_observer, options=None):
  if sys.version_info[0] >= 3:
    def _bind_method_py3(self, class_instance, method_name):
      if not hasattr(class_instance, method_name):
        raise ValueError('No method %s.%s exists for bind_method!' % (
          self.source_name(class_instance), method_name))
      method = getattr(class_instance, method_name)
      if isinstance(method, types.MethodType):
        method_self = getattr(method, '__self__', None)
        if method_self is None:
          raise TypeError('Cannot mount methods from an unbound class.')
        self._mounts.add(method_self)
        setattr(self, method_name, method)

    http_server.HttpServer._bind_method = _bind_method_py3

  bottle_wrapper = BottleObserver(task_observer, options=options)
  root_metrics = RootMetrics()
  server = HttpServer()
  server.mount_routes(bottle_wrapper)
  server.mount_routes(DiagnosticsEndpoints())
  server.mount_routes(VarsEndpoint())
  register_build_properties(root_metrics)
  register_diagnostics(root_metrics)
  return server
