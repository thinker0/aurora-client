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

"""HTTP interface to the Thermos TaskObserver

This modules provides an HTTP server which exposes information about Thermos tasks running on a
system. To do this, it relies heavily on the Thermos TaskObserver.

"""
import socket
import hashlib
import bottle

from bottle import HTTPResponse
from expiringdict import ExpiringDict

from twitter.common import log
from twitter.common.http import HttpServer, Plugin, request
from redis3.client import Redis

from .file_browser import TaskObserverFileBrowser
from .json import TaskObserverJSONBindings
from .static_assets import StaticAssets
from .templating import HttpTemplate

# Cache for user authentication information
# TODO make this configurable
cache = ExpiringDict(max_len=100, max_age_seconds=1800)


class BasicAuth(Plugin):
  """A CherryPy plugin that provides HTTP Basic Authentication."""
  name = 'basic_auth'
  _key_prefix = '/aurora/thermos/user/'

  def __init__(self, options=None, realm='Thermos Observer'):
    self._options = options
    self._realm = realm
    self._app = None
    self._authRedis = None

  def setup(self, app):
    log.debug('Setting up BasicAuthPlugin')
    ''' Make sure that other installed plugins don't affect the same
        keyword argument.'''
    self._app = app
    for other in app.plugins:
      if not isinstance(other, BasicAuth): continue
      if other.keyword == self.keyword:
        raise RuntimeError("Found another BasicAuth plugin with " \
                          "conflicting settings (non-unique keyword).")
    redis_url = self._options.redis_cluster
    self._authRedis = Redis.from_url(redis_url)
    log.debug('Starting redis client: %s' % redis_url)
    self._key_prefix = self._options.redis_key_prefix

  def get_user(self, user=None):
    if user is None:
      return None
    if user in cache:
      log.debug('cache hit: %s' % user)
      return cache.get(user, None)
    val = self._authRedis.get(self._key_prefix + '%s' % user)
    if val:
      log.debug('cache miss: %s' % user)
      cache[user] = val
      return val
    return None

  def apply(self, callback, context):
    user, password = request.auth or (None, None)
    userhash = hashlib.sha256('%s:%s' % (user, password)).hexdigest()
    if (user is not None and password is not None
        and self.get_user(user) == 'sha256:%s' % userhash):
      log.debug('Success Authorization user=%s' % user)
      return callback

    def wrap(*args, **kwargs):
      user, password = request.auth or (None, None)
      userhash = hashlib.sha256('%s:%s' % (user, password)).hexdigest()
      if (user is not None and password is not None
          and self.get_user(user) == 'sha256:%s' % userhash):
        log.debug('Success Authorization user=%s' % user)
        return callback(*args, **kwargs)
      else:
        response = HTTPResponse(status=401)
        response.set_header('WWW-Authenticate', 'Basic realm="%s"' % self._realm)
        response.status = 401
        return response
    return wrap

  def close(self):
    log.debug('Closing BasicAuthPlugin')
    self._authRedis.close()


class AuthenticateEverything(object):
  plugins = []

  def __init__(self, options):
    self._options = options
    if options.enable_authentication is not None \
        and options.enable_authentication.lower()=='basic':
      basicAuth = BasicAuth(self._options)
      log.debug('Installing AuthenticateEverything')
      bottle.install(basicAuth)
      self.plugins.append(basicAuth)
      log.debug('Installing AuthenticateEverything.plugins: %d' % len(self.plugins))


class BottleObserver(HttpServer, StaticAssets, TaskObserverFileBrowser, TaskObserverJSONBindings,
                     AuthenticateEverything):
  """
    A bottle wrapper around a Thermos TaskObserver.
  """

  def __init__(self, observer, options):
    self._observer = observer
    self._options = options
    StaticAssets.__init__(self)
    TaskObserverFileBrowser.__init__(self)
    TaskObserverJSONBindings.__init__(self)
    HttpServer.__init__(self)
    AuthenticateEverything.__init__(self, options)

  @HttpServer.route("/")
  @HttpServer.view(HttpTemplate.load('index'))
  def handle_index(self):
    return dict(hostname=socket.gethostname())

  @HttpServer.route("/main")
  @HttpServer.route("/main/:type")
  @HttpServer.route("/main/:type/:offset")
  @HttpServer.route("/main/:type/:offset/:num")
  @HttpServer.mako_view(HttpTemplate.load('main'))
  def handle_main(self, type=None, offset=None, num=None):
    if type not in (None, 'all', 'finished', 'active'):
      HttpServer.abort(404, 'Invalid task type: %s' % type)
    if offset is not None:
      try:
        offset = int(offset)
      except ValueError:
        HttpServer.abort(404, 'Invalid offset: %s' % offset)
    if num is not None:
      try:
        num = int(num)
      except ValueError:
        HttpServer.abort(404, 'Invalid count: %s' % num)
    return self._observer.main(type, offset, num)

  @HttpServer.route("/task/:task_id")
  @HttpServer.mako_view(HttpTemplate.load('task'))
  def handle_task(self, task_id):
    task = self.get_task(task_id)
    processes = self._observer.processes([task_id])
    if not processes.get(task_id, None):
      HttpServer.abort(404, 'Unknown task_id: %s' % task_id)
    processes = processes[task_id]
    state = self._observer.state(task_id)

    return dict(
      task_id=task_id,
      task=task,
      statuses=self._observer.task_statuses(task_id),
      user=task['user'],
      ports=task['ports'],
      processes=processes,
      chroot=state.get('sandbox', ''),
      launch_time=state.get('launch_time', 0),
      hostname=state.get('hostname', 'localhost'),
    )

  def get_task(self, task_id):
    task = self._observer._task(task_id)
    if not task:
      HttpServer.abort(404, "Failed to find task %s.  Try again shortly." % task_id)
    return task

  @HttpServer.route("/rawtask/:task_id")
  @HttpServer.mako_view(HttpTemplate.load('rawtask'))
  def handle_rawtask(self, task_id):
    task = self.get_task(task_id)
    state = self._observer.state(task_id)
    return dict(
      hostname=state.get('hostname', 'localhost'),
      task_id=task_id,
      task_struct=task['task_struct']
    )

  @HttpServer.route("/process/:task_id/:process_id")
  @HttpServer.mako_view(HttpTemplate.load('process'))
  def handle_process(self, task_id, process_id):
    all_processes = {}
    current_run = self._observer.process(task_id, process_id)
    if not current_run:
      HttpServer.abort(404, 'Invalid task/process combination: %s/%s' % (task_id, process_id))
    process = self._observer.process_from_name(task_id, process_id)
    if process is None:
      msg = 'Could not recover process: %s/%s' % (task_id, process_id)
      log.error(msg)
      HttpServer.abort(404, msg)

    current_run_number = current_run['process_run']
    all_processes[current_run_number] = current_run
    for run in range(current_run_number):
      all_processes[run] = self._observer.process(task_id, process_id, run)

    template = {
      'task_id': task_id,
      'process': {
         'name': process_id,
         'status': all_processes[current_run_number]["state"],
         'cmdline': process.cmdline().get()
      },
    }
    template['process'].update(**all_processes[current_run_number].get('used', {}))
    template['runs'] = all_processes
    log.debug('Rendering template is: %s', template)
    return template
