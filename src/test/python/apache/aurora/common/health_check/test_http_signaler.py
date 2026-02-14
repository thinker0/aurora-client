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

import unittest
from socket import timeout as SocketTimeout
from unittest import mock
from twitter.common.lang import Compatibility

from apache.aurora.common.health_check.http_signaler import HttpSignaler

if Compatibility.PY3:
  import urllib.request as urllib_request
  from urllib.error import HTTPError
else:
  import urllib2 as urllib_request
  from urllib2 import HTTPError


class OpenedURL(object):
  def __init__(self, content, code=200):
    self.content = content
    self.code = code

  def read(self):
    return self.content

  def close(self):
    pass

  def getcode(self):
    return self.code


class TestHttpSignaler(unittest.TestCase):
  PORT = 12345

  def test_all_calls_ok(self):
    with mock.patch.object(urllib_request, 'urlopen') as urlopen:
      urlopen.side_effect = [OpenedURL(''), OpenedURL('')]

      signaler = HttpSignaler(self.PORT)
      assert signaler('/quitquitquit', use_post_method=True) == (True, None)
      assert signaler('/abortabortabort', use_post_method=True) == (True, None)

      urlopen.assert_has_calls([
        mock.call('http://localhost:%s/quitquitquit' % self.PORT, b'', timeout=1.0),
        mock.call('http://localhost:%s/abortabortabort' % self.PORT, b'', timeout=1.0),
      ])

  def test_health_checks(self):
    with mock.patch.object(urllib_request, 'urlopen') as urlopen:
      urlopen.side_effect = [
        OpenedURL('ok'),
        OpenedURL('not ok'),
        OpenedURL('not ok', code=200),
        OpenedURL('ok', code=400),
        HTTPError('', 501, '', None, None),
        OpenedURL('ok', code=200),
        OpenedURL('ok'),
      ]

      signaler = HttpSignaler(self.PORT)
      assert signaler('/health', expected_response='ok') == (True, None)
      assert signaler('/health', expected_response='ok') == (
          False, 'Response differs from expected response (expected "ok", got "not ok")')
      assert signaler('/health', expected_response_code=200) == (True, None)
      assert signaler('/health', expected_response_code=200) == (
          False, 'Response code differs from expected response (expected 200, got 400)')
      assert signaler('/health', expected_response_code=200) == (
          False, 'Response code differs from expected response (expected 200, got 501)')
      assert signaler('/health', expected_response='ok', expected_response_code=200) == (True, None)
      assert signaler('/random/endpoint', expected_response='ok') == (True, None)

      urlopen.assert_has_calls([
        mock.call('http://localhost:%s/health' % self.PORT, None, timeout=1.0),
        mock.call('http://localhost:%s/health' % self.PORT, None, timeout=1.0),
        mock.call('http://localhost:%s/health' % self.PORT, None, timeout=1.0),
        mock.call('http://localhost:%s/health' % self.PORT, None, timeout=1.0),
        mock.call('http://localhost:%s/health' % self.PORT, None, timeout=1.0),
        mock.call('http://localhost:%s/health' % self.PORT, None, timeout=1.0),
        mock.call('http://localhost:%s/random/endpoint' % self.PORT, None, timeout=1.0),
      ])

  def test_exception(self):
    with mock.patch.object(urllib_request, 'urlopen') as urlopen:
      urlopen.side_effect = SocketTimeout('Timed out')

      assert not HttpSignaler(self.PORT)('/health', expected_response='ok')[0]
      urlopen.assert_called_once_with(
          'http://localhost:%s/health' % self.PORT, None, timeout=1.0)
