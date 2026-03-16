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
import threading
import bottle
import requests as _requests

from bottle import HTTPResponse
from expiringdict import ExpiringDict

from twitter.common import log
from twitter.common.http import HttpServer, Plugin, request
from rediscluster import RedisCluster

from .file_browser import TaskObserverFileBrowser
from .json import TaskObserverJSONBindings
from .static_assets import StaticAssets
from .templating import HttpTemplate

# Cache for Basic Auth credentials (30-minute TTL)
cache = ExpiringDict(max_len=100, max_age_seconds=1800)

# Cache for OIDC token validation results (5-minute TTL — tokens are short-lived)
_oidc_cache = ExpiringDict(max_len=500, max_age_seconds=300)
_oidc_cache_lock = threading.Lock()


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
    self._authRedis = RedisCluster.from_url(redis_url, readonly_mode=True)
    log.debug('Starting redis client: %s' % redis_url)
    self._key_prefix = self._options.redis_key_prefix

  def get_user(self, user=None):
    if user is None:
      return None
    if cache.__contains__(user):
      # log.debug('cache hit: %s' % user)
      val= cache.get(user, None)
      return val
    try:
      val = self._authRedis.get(self._key_prefix + '%s' % user)
      if user is not None and val is not None:
        if isinstance(val, bytes):
          val = val.decode('utf-8')
        log.debug('redis get: %s=%s' % (user, val))
        return val
    except Exception as e:
      log.error('redis get: %s' % e)
    return None

  def set_cache(self, user, user_hash):
    if user is not None and user_hash is not None:
      cache[user] = 'sha256:%s' % user_hash
      log.debug('cache set: %s=sha256:%s' % (user, user_hash))

  def apply(self, callback, context):
    def wrap(*args, **kwargs):
      user, password = request.auth or (None, None)
      if user is not None and password is not None:
        user_hash = hashlib.sha256(('%s:%s' % (user, password)).encode('utf-8')).hexdigest()
        if self.get_user(user) == 'sha256:%s' % user_hash:
          log.debug('Success Authorization user=%s' % user)
          self.set_cache(user, user_hash)
          return callback(*args, **kwargs)
      log.debug('Authentication failed')
      raise HTTPResponse(status=401, headers={'WWW-Authenticate': 'Basic realm="%s"' % self._realm})
    return wrap

  def close(self):
    log.debug('Closing BasicAuthPlugin')
    self._authRedis.close()


class OidcBearerAuth(Plugin):
  """Bottle plugin that validates OIDC Bearer tokens via the userinfo endpoint."""
  name = 'oidc_bearer_auth'

  def __init__(self, options, realm='Thermos Observer'):
    self._issuer = getattr(options, 'oidc_issuer', None)
    self._realm = realm
    self._userinfo_url = None

  def setup(self, app):
    if not self._issuer:
      log.error('OidcBearerAuth: --oidc-issuer is required for oidc auth mode')
      return
    config_url = self._issuer.rstrip('/') + '/.well-known/openid-configuration'
    try:
      resp = _requests.get(config_url, timeout=5)
      if resp.status_code != 200:
        log.error('OidcBearerAuth: OIDC discovery returned HTTP %s', resp.status_code)
        return
      self._userinfo_url = resp.json().get('userinfo_endpoint')
      if not self._userinfo_url:
        log.error('OidcBearerAuth: OIDC discovery document missing userinfo_endpoint')
      else:
        log.debug('OidcBearerAuth: userinfo endpoint: %s', self._userinfo_url)
    except Exception as e:
      log.error('OidcBearerAuth: failed to fetch OIDC discovery document: %s', e)

  def _validate_token(self, token):
    with _oidc_cache_lock:
      cached = _oidc_cache.get(token)
    if cached is not None:
      return cached
    if not self._userinfo_url:
      return False
    try:
      resp = _requests.get(
          self._userinfo_url,
          headers={'Authorization': 'Bearer ' + token},
          timeout=5,
      )
      ok = resp.status_code == 200
      with _oidc_cache_lock:
        _oidc_cache[token] = ok
      if ok:
        try:
          sub = resp.json().get('sub', '?')
        except (ValueError, KeyError):
          sub = '?'
        log.debug('OidcBearerAuth: token valid, sub=%s', sub)
      else:
        log.debug('OidcBearerAuth: token rejected, status=%s', resp.status_code)
      return ok
    except Exception as e:
      log.warning('OidcBearerAuth: token validation error: %s', e)
      return False

  def apply(self, callback, context):
    def wrap(*args, **kwargs):
      auth_header = request.headers.get('Authorization', '')
      if auth_header.startswith('Bearer ') and self._validate_token(auth_header[7:]):
        return callback(*args, **kwargs)
      raise HTTPResponse(
          status=401,
          headers={'WWW-Authenticate': 'Bearer realm="%s"' % self._realm},
      )
    return wrap

  def close(self):
    pass


class CombinedAuth(Plugin):
  """Bottle plugin that accepts either an OIDC Bearer token or HTTP Basic credentials."""
  name = 'combined_auth'

  def __init__(self, options, realm='Thermos Observer'):
    self._oidc = OidcBearerAuth(options, realm)
    self._basic = BasicAuth(options, realm)
    self._realm = realm

  def setup(self, app):
    self._oidc.setup(app)
    self._basic.setup(app)

  def apply(self, callback, context):
    def wrap(*args, **kwargs):
      # 1) OIDC Bearer token — tried first
      auth_header = request.headers.get('Authorization', '')
      if auth_header.startswith('Bearer '):
        if self._oidc._validate_token(auth_header[7:]):
          log.debug('CombinedAuth: OIDC Bearer accepted')
          return callback(*args, **kwargs)

      # 2) HTTP Basic credentials
      user, password = request.auth or (None, None)
      if user and password:
        user_hash = hashlib.sha256(
            ('%s:%s' % (user, password)).encode('utf-8')
        ).hexdigest()
        if self._basic.get_user(user) == 'sha256:%s' % user_hash:
          log.debug('CombinedAuth: Basic accepted, user=%s', user)
          self._basic.set_cache(user, user_hash)
          return callback(*args, **kwargs)

      # 3) Neither succeeded
      raise HTTPResponse(
          status=401,
          headers={'WWW-Authenticate': 'Basic realm="%s"' % self._realm},
      )
    return wrap

  def close(self):
    self._oidc.close()
    self._basic.close()


class AuthenticateEverything(object):

  def __init__(self, options):
    self.plugins = []
    self._options = options
    mode = (getattr(options, 'enable_authentication', None) or '').lower()
    plugin = None
    if mode == 'basic':
      plugin = BasicAuth(self._options)
    elif mode == 'oidc':
      plugin = OidcBearerAuth(self._options)
    elif mode == 'oidc+basic':
      plugin = CombinedAuth(self._options)
    if plugin is not None:
      log.debug('Installing auth plugin: %s', plugin.name)
      bottle.install(plugin)
      self.plugins.append(plugin)
      log.debug('AuthenticateEverything: %d plugin(s) active', len(self.plugins))

  def close(self):
    for plugin in self.plugins:
      try:
        plugin.close()
      except Exception as e:
        log.warning('Error closing auth plugin %s: %s', plugin.name, e)


class BottleObserver(HttpServer, StaticAssets, TaskObserverFileBrowser, TaskObserverJSONBindings,
                     AuthenticateEverything):
  """
    A bottle wrapper around a Thermos TaskObserver.
  """

  def __init__(self, observer, options):
    self._observer = observer
    self._options = options
    self._scheduler_web_url = options.scheduler_web_url
    StaticAssets.__init__(self)
    TaskObserverFileBrowser.__init__(self, options)
    TaskObserverJSONBindings.__init__(self)
    HttpServer.__init__(self)
    AuthenticateEverything.__init__(self, options)

  @HttpServer.route("/")
  @HttpServer.view(HttpTemplate.load('index'))
  def handle_index(self):
    return dict(
      hostname=socket.gethostname(),
      scheduler_web_url=self._scheduler_web_url,
    )

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
      scheduler_web_url=self._scheduler_web_url,
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
      task_struct=task['task_struct'],
      scheduler_web_url=self._scheduler_web_url,
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
      'scheduler_web_url': self._scheduler_web_url,
    }
    template['process'].update(**all_processes[current_run_number].get('used', {}))
    template['runs'] = all_processes
    log.debug('Rendering template is: %s', template)
    return template
