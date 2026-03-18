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
from urllib.parse import urlparse
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
_TRUSTED_USER_HEADERS = ('X-Forwarded-User', 'X-Auth-Request-User')


def _is_allowed_oidc_url(url):
  try:
    parsed = urlparse(url)
    if parsed.scheme == 'https':
      return True
    if parsed.scheme == 'http' and parsed.hostname in ('localhost', '127.0.0.1', '::1'):
      return True
    return False
  except Exception:
    return False


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
    log.debug('BasicAuth: setting up plugin, realm=%s', self._realm)
    self._app = app
    for other in app.plugins:
      if not isinstance(other, BasicAuth): continue
      if other.keyword == self.keyword:
        raise RuntimeError("Found another BasicAuth plugin with " \
                          "conflicting settings (non-unique keyword).")
    redis_url = self._options.redis_cluster
    self._key_prefix = getattr(self._options, 'redis_key_prefix', '/aurora/thermos/user/')
    log.debug('BasicAuth: connecting to Redis %s (key_prefix=%s)', redis_url, self._key_prefix)
    self._authRedis = RedisCluster.from_url(redis_url, readonly_mode=True)
    log.debug('BasicAuth: Redis client ready')

  def get_user(self, user=None):
    if user is None:
      return None
    if cache.__contains__(user):
      val = cache.get(user, None)
      log.debug('BasicAuth: cache hit for user=%s', user)
      return val
    log.debug('BasicAuth: cache miss for user=%s, querying Redis key=%s', user, self._key_prefix + user)
    try:
      val = self._authRedis.get(self._key_prefix + '%s' % user)
      if val is not None:
        if isinstance(val, bytes):
          val = val.decode('utf-8')
        log.debug('BasicAuth: Redis returned hash for user=%s (len=%d)', user, len(val))
        return val
      log.debug('BasicAuth: Redis returned None for user=%s (key not found)', user)
    except Exception as e:
      log.error('BasicAuth: Redis error for user=%s: %s', user, e)
    return None

  def set_cache(self, user, user_hash):
    if user is not None and user_hash is not None:
      cache[user] = 'sha256:%s' % user_hash
      log.debug('BasicAuth: cached credentials for user=%s', user)

  def apply(self, callback, context):
    def wrap(*args, **kwargs):
      user, password = request.auth or (None, None)
      log.debug('BasicAuth: request user=%s has_password=%s path=%s',
                user, password is not None, getattr(request, 'path', '?'))
      if user is not None and password is not None:
        user_hash = hashlib.sha256(('%s:%s' % (user, password)).encode('utf-8')).hexdigest()
        stored = self.get_user(user)
        if stored == 'sha256:%s' % user_hash:
          log.debug('BasicAuth: accepted user=%s', user)
          self.set_cache(user, user_hash)
          return callback(*args, **kwargs)
        log.debug('BasicAuth: password mismatch for user=%s', user)
      else:
        log.debug('BasicAuth: missing credentials (user=%s)', user)
      raise HTTPResponse(status=401, headers={'WWW-Authenticate': 'Basic realm="%s"' % self._realm})
    return wrap

  def close(self):
    log.debug('BasicAuth: closing Redis connection')
    self._authRedis.close()


class OidcBearerAuth(Plugin):
  """Bottle plugin that validates OIDC Bearer tokens via the userinfo endpoint."""
  name = 'oidc_bearer_auth'

  def __init__(self, options, realm='Thermos Observer'):
    self._issuer = getattr(options, 'oidc_issuer', None)
    self._realm = realm
    flag = getattr(options, 'oidc_allow_trusted_header_without_bearer', False)
    if isinstance(flag, bool):
      self._allow_trusted_header_without_bearer = flag
    elif isinstance(flag, str):
      self._allow_trusted_header_without_bearer = flag.strip().lower() in ('1', 'true', 'yes', 'on')
    else:
      self._allow_trusted_header_without_bearer = False
    # Direct userinfo URL takes precedence over OIDC discovery (supports oauth2-proxy)
    _raw_url = getattr(options, 'oidc_userinfo_url', None)
    self._userinfo_url = _raw_url if isinstance(_raw_url, str) and _raw_url else None

  def setup(self, app):
    if self._userinfo_url:
      if not _is_allowed_oidc_url(self._userinfo_url):
        log.error('OidcBearerAuth: --oidc-userinfo-url must use HTTPS (localhost may use HTTP): %s',
                  self._userinfo_url)
        self._userinfo_url = None
        return
      log.debug('OidcBearerAuth: using pre-configured userinfo URL: %s', self._userinfo_url)
      return
    if not self._issuer:
      log.error('OidcBearerAuth: --oidc-issuer or --oidc-userinfo-url is required')
      return
    if not _is_allowed_oidc_url(self._issuer):
      log.error('OidcBearerAuth: --oidc-issuer must use HTTPS (localhost may use HTTP): %s',
                self._issuer)
      return
    config_url = self._issuer.rstrip('/') + '/.well-known/openid-configuration'
    log.debug('OidcBearerAuth: fetching OIDC discovery document: %s', config_url)
    try:
      resp = _requests.get(config_url, timeout=5)
      log.debug('OidcBearerAuth: discovery response HTTP %s', resp.status_code)
      if resp.status_code != 200:
        log.error('OidcBearerAuth: OIDC discovery returned HTTP %s from %s',
                  resp.status_code, config_url)
        return
      self._userinfo_url = resp.json().get('userinfo_endpoint')
      if not self._userinfo_url:
        log.error('OidcBearerAuth: OIDC discovery document missing userinfo_endpoint (url=%s)',
                  config_url)
      elif not _is_allowed_oidc_url(self._userinfo_url):
        log.error('OidcBearerAuth: userinfo_endpoint must use HTTPS (localhost may use HTTP), got %s',
                  self._userinfo_url)
        self._userinfo_url = None
      else:
        log.debug('OidcBearerAuth: discovered userinfo endpoint: %s', self._userinfo_url)
    except Exception as e:
      log.error('OidcBearerAuth: failed to fetch OIDC discovery document %s: %s', config_url, e)

  def _validate_token(self, token):
    token_prefix = token[:8] + '...' if len(token) > 8 else '(short)'
    with _oidc_cache_lock:
      cached = _oidc_cache.get(token)
    if cached is not None:
      log.debug('OidcBearerAuth: cache hit token=%s', token_prefix)
      if cached is False:
        return None
      return cached
    if not self._userinfo_url:
      log.debug('OidcBearerAuth: no userinfo URL configured, rejecting token=%s', token_prefix)
      return None
    log.debug('OidcBearerAuth: validating token=%s via %s', token_prefix, self._userinfo_url)
    try:
      resp = _requests.get(
          self._userinfo_url,
          headers={'Authorization': 'Bearer ' + token},
          timeout=5,
      )
      log.debug('OidcBearerAuth: userinfo response HTTP %s for token=%s', resp.status_code, token_prefix)
      if resp.status_code != 200:
        with _oidc_cache_lock:
          _oidc_cache[token] = False
        log.debug('OidcBearerAuth: token rejected (HTTP %s) token=%s', resp.status_code, token_prefix)
        return None
      try:
        userinfo = resp.json()
      except (ValueError, KeyError, TypeError):
        log.debug('OidcBearerAuth: invalid userinfo JSON, token=%s', token_prefix)
        with _oidc_cache_lock:
          _oidc_cache[token] = False
        return None
      if not isinstance(userinfo, dict):
        log.debug('OidcBearerAuth: userinfo payload is not an object, token=%s', token_prefix)
        with _oidc_cache_lock:
          _oidc_cache[token] = False
        return None
      with _oidc_cache_lock:
        _oidc_cache[token] = userinfo
      log.debug(
          'OidcBearerAuth: token accepted, sub=%s email=%s token=%s',
          userinfo.get('sub', '?'),
          userinfo.get('email', '?'),
          token_prefix,
      )
      return userinfo
    except Exception as e:
      log.warning('OidcBearerAuth: token validation error token=%s: %s', token_prefix, e)
      return None

  @staticmethod
  def _normalize_user(value):
    if not isinstance(value, str):
      return None
    normalized = value.strip().lower()
    return normalized if normalized else None

  def _trusted_user(self):
    for header in _TRUSTED_USER_HEADERS:
      user = self._normalize_user(request.headers.get(header))
      if user:
        return user
    return None

  def _userinfo_candidates(self, userinfo):
    candidates = set()
    for key in ('email', 'preferred_username', 'username', 'upn', 'sub'):
      normalized = self._normalize_user(userinfo.get(key))
      if normalized:
        candidates.add(normalized)
    return candidates

  def authenticate_trusted_header_only(self, path):
    trusted_user = self._trusted_user()
    if not trusted_user:
      log.debug('OidcBearerAuth: trusted-header-only auth failed (missing trusted user), path=%s', path)
      return False
    log.debug('OidcBearerAuth: trusted-header-only auth accepted user=%s path=%s', trusted_user, path)
    return True

  def authenticate_bearer(self, auth_header, path):
    if not auth_header or not auth_header.startswith('Bearer '):
      log.debug('OidcBearerAuth: missing/invalid Authorization scheme, path=%s', path)
      return False
    trusted_user = self._trusted_user()
    if not trusted_user:
      log.debug('OidcBearerAuth: missing trusted user header, path=%s', path)
      return False
    userinfo = self._validate_token(auth_header[7:])
    if userinfo is None:
      log.debug('OidcBearerAuth: token invalid, path=%s', path)
      return False
    candidates = self._userinfo_candidates(userinfo)
    if trusted_user not in candidates:
      log.debug(
          'OidcBearerAuth: trusted user mismatch, trusted=%s claims=%s path=%s',
          trusted_user,
          sorted(candidates),
          path,
      )
      return False
    log.debug('OidcBearerAuth: request authorised user=%s path=%s', trusted_user, path)
    return True

  def apply(self, callback, context):
    def wrap(*args, **kwargs):
      auth_header = request.headers.get('Authorization', '')
      path = getattr(request, 'path', '?')
      if not auth_header:
        if self._allow_trusted_header_without_bearer and self.authenticate_trusted_header_only(path):
          return callback(*args, **kwargs)
        log.debug('OidcBearerAuth: no Authorization header, path=%s', path)
        raise HTTPResponse(
            status=401,
            headers={'WWW-Authenticate': 'Bearer realm="%s"' % self._realm},
        )
      if not auth_header.startswith('Bearer '):
        log.debug('OidcBearerAuth: unsupported scheme "%s", path=%s',
                  auth_header.split(' ')[0], path)
        raise HTTPResponse(
            status=401,
            headers={'WWW-Authenticate': 'Bearer realm="%s"' % self._realm},
        )
      if self.authenticate_bearer(auth_header, path):
        return callback(*args, **kwargs)
      log.debug('OidcBearerAuth: bearer auth failed, path=%s', path)
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
      path = getattr(request, 'path', '?')
      auth_header = request.headers.get('Authorization', '')

      # 1) OIDC Bearer token — tried first
      if auth_header.startswith('Bearer '):
        log.debug('CombinedAuth: trying OIDC Bearer, path=%s', path)
        if self._oidc.authenticate_bearer(auth_header, path):
          log.debug('CombinedAuth: OIDC Bearer accepted, path=%s', path)
          return callback(*args, **kwargs)
        log.debug('CombinedAuth: OIDC Bearer failed, falling back to Basic, path=%s', path)
      else:
        if (
            self._oidc._allow_trusted_header_without_bearer
            and self._oidc.authenticate_trusted_header_only(path)
        ):
          log.debug('CombinedAuth: trusted-header-only auth accepted, path=%s', path)
          return callback(*args, **kwargs)
        log.debug('CombinedAuth: no Bearer header, trying Basic only, path=%s', path)

      # 2) HTTP Basic credentials
      user, password = request.auth or (None, None)
      log.debug('CombinedAuth: Basic attempt user=%s has_password=%s, path=%s',
                user, password is not None, path)
      if user and password:
        user_hash = hashlib.sha256(
            ('%s:%s' % (user, password)).encode('utf-8')
        ).hexdigest()
        stored = self._basic.get_user(user)
        if stored == 'sha256:%s' % user_hash:
          log.debug('CombinedAuth: Basic accepted, user=%s, path=%s', user, path)
          self._basic.set_cache(user, user_hash)
          return callback(*args, **kwargs)
        log.debug('CombinedAuth: Basic failed for user=%s, path=%s', user, path)
      else:
        log.debug('CombinedAuth: no Basic credentials, path=%s', path)

      # 3) Neither succeeded
      log.debug('CombinedAuth: all auth methods failed, returning 401, path=%s', path)
      raise HTTPResponse(
          status=401,
          headers={'WWW-Authenticate': 'Bearer realm="%s", Basic realm="%s"'
                   % (self._realm, self._realm)},
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
    log.debug('AuthenticateEverything: mode=%r', mode or '(none)')
    plugin = None
    if mode == 'basic':
      log.debug('AuthenticateEverything: enabling HTTP Basic Auth (Redis-backed)')
      plugin = BasicAuth(self._options)
    elif mode == 'oidc':
      log.debug('AuthenticateEverything: enabling OIDC Bearer Auth (issuer=%s, userinfo_url=%s)',
                getattr(options, 'oidc_issuer', None),
                getattr(options, 'oidc_userinfo_url', None))
      plugin = OidcBearerAuth(self._options)
    elif mode == 'oidc+basic':
      log.debug('AuthenticateEverything: enabling Combined Auth (OIDC+Basic)')
      plugin = CombinedAuth(self._options)
    else:
      log.debug('AuthenticateEverything: authentication disabled')
    if plugin is not None:
      log.debug('AuthenticateEverything: installing plugin=%s', plugin.name)
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
