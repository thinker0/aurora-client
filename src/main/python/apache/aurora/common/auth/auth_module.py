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
from abc import abstractmethod
from base64 import b64encode
try:
  from netrc import netrc
except ImportError:
  netrc = None
from requests.compat import urlparse

from requests.auth import AuthBase
from requests.utils import to_native_string
from twitter.common import log
from twitter.common.lang import Interface


class AuthModule(Interface):
  @property
  @abstractmethod
  def mechanism(self):
    """Return the mechanism provided by this AuthModule.
    ":rtype: string
    """

  @abstractmethod
  def auth(self, cluster_name=None):
    """Authentication handler for the HTTP transport layer.
    :rtype: requests.auth.AuthBase.
    """

  @property
  @abstractmethod
  def failed_auth_message(self):
    """Default help message to log on failed auth attempt.
    :rtype: string
    """


class InsecureAuthModule(AuthModule):
  @property
  def mechanism(self):
    return 'UNAUTHENTICATED'

  def auth(self, cluster_name=None):
    return None

  @property
  def failed_auth_message(self):
    return ''


class BasicAuth(AuthBase):
  """Attaches HTTP Basic Authentication to the given Request object."""
  def __init__(self, username=None, password=None, netrc_file=None):
    self._username = username
    self._password = password
    self._netrc = None
    if netrc is not None and not (username and password):
      try:
        if netrc_file is None:
          self._netrc = netrc()
        else:
          self._netrc = netrc(netrc_file)
      except (IOError, TypeError, ValueError):
        # Skip if netrc file is not found or has invalid format
        pass

  def _basic_auth_str(self, username, password):
    """Returns a Basic Auth string."""

    if isinstance(username, str):
      username = username.encode('latin1')

    if isinstance(password, str):
      password = password.encode('latin1')

    authstr = 'Basic ' + to_native_string(
      b64encode(b':'.join((username, password))).strip()
    )
    return authstr

  def __call__(self, request):
    if self._username and self._password:
      request.headers['Authorization'] = self._basic_auth_str(self._username, self._password)
    elif self._netrc:
      host = urlparse(request.url).hostname
      authenticators = self._netrc.authenticators(host)
      if authenticators:
        login, account, password = authenticators
        request.headers['Authorization'] = self._basic_auth_str(login, password)
    return request


class BasicAuthModule(AuthModule):
  def __init__(self, username=None, password=None, netrc_file=None):
    self._username = username
    self._password = password
    self._netrc_file = netrc_file

  @property
  def mechanism(self):
    return 'BASIC'

  def auth(self, cluster_name=None):
    return BasicAuth(
        username=self._username,
        password=self._password,
        netrc_file=self._netrc_file)

  @property
  def failed_auth_message(self):
    return ('Communication with Aurora scheduler requires HTTP Basic Authentication. '
            'Does your %s file contain valid credentials for the scheduler host?'
            % (self._netrc_file or '~/.netrc'))

import os



class SessionTokenAuth(AuthBase):
  def __init__(self, token_file=None, cluster_name=None):
    self._cluster = cluster_name
    if token_file:
      self._token_file = token_file
    elif self._cluster:
      self._token_file = os.path.expanduser(f'~/.aurora/token.{self._cluster}')
    else:
      self._token_file = os.path.expanduser('~/.aurora/token')

    
    self._token = None
    try:
      if os.path.exists(self._token_file):
        with open(self._token_file, 'r') as f:
          self._token = f.read().strip()
    except (OSError, UnicodeDecodeError) as e:
      log.warning('Failed to load session token from %s: %s', self._token_file, e)

  def __call__(self, request):
    if self._token:
      request.headers['Authorization'] = 'Bearer %s' % self._token
    return request



class SessionTokenAuthModule(AuthModule):
  def __init__(self, token_file=None):
    self._token_file = token_file

  @property
  def mechanism(self):
    return 'SESSION_TOKEN'

  def auth(self, cluster_name=None):
    return SessionTokenAuth(token_file=self._token_file, cluster_name=cluster_name)

  @property
  def failed_auth_message(self):
    return 'Communication requires a valid session token. Please check ~/.aurora/token'

import json
import time
import requests

class OidcDeviceAuth(AuthBase):
  def __init__(self, token_file=None):
    self._token_file = token_file or os.path.expanduser('~/.aurora/oidc_token.json')
    self._issuer = os.environ.get('AURORA_OIDC_ISSUER')
    self._client_id = os.environ.get('AURORA_OIDC_CLIENT_ID')
    self._access_token = None
    self._load_token()

  def _load_token(self):
    if os.path.exists(self._token_file):
      try:
        with open(self._token_file, 'r') as f:
          data = json.load(f)
        if 'access_token' not in data:
          log.warning('OIDC token file missing access_token: %s', self._token_file)
          return
        expires_at = data.get('expires_at', 0)
        if time.time() >= expires_at - 60 and data.get('refresh_token'):
          data = self._refresh_token(data) or data
        if 'access_token' in data:
          self._access_token = data['access_token']
      except (OSError, UnicodeDecodeError, json.JSONDecodeError) as e:
        log.warning('Failed to load OIDC token from %s: %s', self._token_file, e)

  def _save_token(self, data):
    try:
      os.makedirs(os.path.dirname(self._token_file), mode=0o700, exist_ok=True)
      fd = os.open(self._token_file, os.O_CREAT | os.O_WRONLY | os.O_TRUNC, 0o600)
      with os.fdopen(fd, 'w') as f:
        json.dump(data, f)
    except OSError as e:
      log.warning('Failed to save OIDC token: %s', e)

  def _refresh_token(self, session_data):
    token_endpoint = session_data.get('token_endpoint')
    client_id = session_data.get('client_id') or self._client_id
    refresh_token = session_data.get('refresh_token')
    if not token_endpoint or not client_id or not refresh_token:
      return None
    try:
      resp = requests.post(
        token_endpoint,
        data={
          'grant_type': 'refresh_token',
          'client_id': client_id,
          'refresh_token': refresh_token,
        },
        timeout=10,
      )
      new_data = resp.json()
      if 'access_token' not in new_data:
        log.warning('Token refresh response missing access_token')
        return None
      if 'refresh_token' not in new_data:
        new_data['refresh_token'] = refresh_token
      new_data.setdefault('token_endpoint', token_endpoint)
      new_data.setdefault('client_id', client_id)
      new_data['expires_at'] = int(time.time()) + new_data.get('expires_in', 3600)
      self._save_token(new_data)
      return new_data
    except requests.RequestException as e:
      log.warning('Token refresh failed: %s', e)
      return None

  def _get_openid_config(self):
    if not self._issuer:
      return None
    try:
      resp = requests.get(
        self._issuer.rstrip('/') + '/.well-known/openid-configuration', timeout=5)
      return resp.json()
    except requests.RequestException as e:
      log.warning('Failed to fetch OIDC discovery document: %s', e)
      return None

  def authenticate_via_device_flow(self):
    if not self._issuer or not self._client_id:
      log.error('AURORA_OIDC_ISSUER and AURORA_OIDC_CLIENT_ID environment variables must be set for OIDC Device Flow.')
      return False

    config = self._get_openid_config()
    if not config or 'device_authorization_endpoint' not in config:
      log.error('OIDC Provider does not support Device Authorization Flow.')
      return False

    # 1. Request device code
    try:
      resp = requests.post(
        config['device_authorization_endpoint'],
        data={'client_id': self._client_id, 'scope': 'openid profile email'},
        timeout=5
      ).json()
    except requests.RequestException as e:
      log.error('Failed to initiate device flow: %s', e)
      return False

    print("\n=======================================================")
    print("To authenticate with Aurora, please visit:")
    print("\n  %s\n" % resp.get('verification_uri_complete', resp.get('verification_uri')))
    print("And enter the code: %s" % resp.get('user_code'))
    print("=======================================================\n")
    print("Waiting for authorization...", end='', flush=True)

    # 2. Poll for token
    token_endpoint = config['token_endpoint']
    interval = resp.get('interval', 5)
    device_code = resp['device_code']
    expires_in = resp.get('expires_in', 300)
    deadline = time.time() + expires_in

    while time.time() < deadline:
      time.sleep(interval)
      print(".", end='', flush=True)
      try:
        token_resp = requests.post(
          token_endpoint,
          data={
            'grant_type': 'urn:ietf:params:oauth:grant-type:device_code',
            'client_id': self._client_id,
            'device_code': device_code
          },
          timeout=10
        )
        data = token_resp.json()

        if token_resp.status_code == 200:
          self._access_token = data['access_token']
          data.setdefault('token_endpoint', token_endpoint)
          data.setdefault('client_id', self._client_id)
          data['expires_at'] = int(time.time()) + data.get('expires_in', 3600)
          self._save_token(data)
          print("\nAuthentication successful!")
          return True
        error = data.get('error', '')
        if error == 'authorization_pending':
          continue
        elif error == 'slow_down':
          interval = min(interval + 5, 60)
        else:
          print("\nAuthentication failed: %s" % data.get('error_description', error))
          return False
      except Exception as e:
        log.warning('Polling error: %s', e)

    print("\nDevice authorization timed out.")
    return False

  def __call__(self, request):
    if self._access_token:
      request.headers['Authorization'] = 'Bearer %s' % self._access_token
    else:
      log.warning('No OIDC token available. Run "aurora auth login <cluster>" to authenticate.')
    return request

class OidcDeviceAuthModule(AuthModule):
  def __init__(self, token_file=None):
    self._token_file = token_file

  @property
  def mechanism(self):
    return 'OIDC_DEVICE'

  def auth(self, cluster_name=None):
    return OidcDeviceAuth(token_file=self._token_file)

  @property
  def failed_auth_message(self):
    return ('Authentication failed. If using OIDC, ensure AURORA_OIDC_ISSUER and '
            'AURORA_OIDC_CLIENT_ID are set, or your token is valid.')



class ProxySessionAuth(AuthBase):
  def __init__(self, session_file=None, cluster_name=None):
    self._cluster = cluster_name
    if session_file:
      self._session_file = session_file
    elif self._cluster:
      self._session_file = os.path.expanduser(f'~/.aurora/session.{self._cluster}')
    else:
      self._session_file = os.path.expanduser('~/.aurora/session')
    
    self._cookies = {}
    self._load_session()


  def _load_session(self):
    if os.path.exists(self._session_file):
      try:
        with open(self._session_file, 'r') as f:
          line = f.read().strip()
          if '=' in line:
            for cookie in line.split(';'):
              if '=' in cookie:
                name, value = cookie.strip().split('=', 1)
                self._cookies[name] = value
          else:
            self._cookies['_oauth2_proxy'] = line
      except (OSError, UnicodeDecodeError) as e:
        log.warning('Failed to load proxy session from %s: %s', self._session_file, e)

  def __call__(self, request):
    if self._cookies:
      cookie_header = '; '.join([f'{k}={v}' for k, v in self._cookies.items()])
      request.headers['Cookie'] = cookie_header
    return request




class ProxySessionAuthModule(AuthModule):
  def __init__(self, session_file=None):
    self._session_file = session_file

  @property
  def mechanism(self):
    return 'PROXY_SESSION'

  def auth(self, cluster_name=None):
    return ProxySessionAuth(session_file=self._session_file, cluster_name=cluster_name)


  @property
  def failed_auth_message(self):
    return 'Authentication failed. Please login via "aurora auth login"'
