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
from abc import abstractmethod, abstractproperty
from base64 import b64encode
from netrc import netrc
from requests.compat import urlparse

from requests.auth import AuthBase
from requests.utils import to_native_string
from twitter.common.lang import Interface


class AuthModule(Interface):
  @abstractproperty
  def mechanism(self):
    """Return the mechanism provided by this AuthModule.
    ":rtype: string
    """

  @abstractmethod
  def auth(self):
    """Authentication handler for the HTTP transport layer.
    :rtype: requests.auth.AuthBase.
    """

  @abstractproperty
  def failed_auth_message(self):
    """Default help message to log on failed auth attempt.
    :rtype: string
    """


class InsecureAuthModule(AuthModule):
  @property
  def mechanism(self):
    return 'UNAUTHENTICATED'

  def auth(self):
    return None

  @property
  def failed_auth_message(self):
    return ''


class BasicAuth(AuthBase):
  """Attaches HTTP Basic Authentication to the given Request object."""
  def __init__(self, netrc_file=None):
    if netrc_file is None:
      self._netrc = netrc()
    else:
      self._netrc = netrc(netrc_file)

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
    host = urlparse(request.url).hostname
    login, account, password = self._netrc.authenticators(host)
    request.headers['Authorization'] = self._basic_auth_str(account, password)
    return request


class BasicAuthModule(AuthModule):
  def __init__(self, netrc_file=None):
    self._netrc_file = netrc_file

  @property
  def mechanism(self):
    return 'BASIC'

  def auth(self):
    return BasicAuth(netrc_file=self._netrc_file)

  @property
  def failed_auth_message(self):
    return 'Communication with Aurora scheduler is %s.' % self.netrc_file
