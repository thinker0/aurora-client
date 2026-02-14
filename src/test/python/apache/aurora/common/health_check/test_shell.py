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

from unittest import mock
import subprocess

from apache.aurora.common.health_check.shell import ShellHealthCheck

STDOUT = subprocess.STDOUT


class TestHealthChecker(unittest.TestCase):

  @mock.patch('subprocess.check_output', autospec=True)
  def test_health_check_ok(self, mock_popen):
    shell = ShellHealthCheck(raw_cmd='cmd', wrapped_cmd='wrapped-cmd', timeout_secs=30)
    success, msg = shell()
    self.assertTrue(success)
    self.assertIsNone(msg)
    mock_popen.assert_called_once_with(
      'wrapped-cmd', timeout=30, preexec_fn=mock.ANY, stderr=STDOUT)

  @mock.patch('subprocess.check_output', autospec=True)
  def test_health_check_failed(self, mock_popen):
    cmd = 'failed'
    wrapped_cmd = 'wrapped-failed'
    # Fail due to command returning a non-0 exit status.
    mock_popen.side_effect = subprocess.CalledProcessError(1, wrapped_cmd, output='No file.')

    shell = ShellHealthCheck(raw_cmd=cmd, wrapped_cmd=wrapped_cmd, timeout_secs=30)
    success, msg = shell()
    mock_popen.assert_called_once_with(wrapped_cmd, timeout=30, preexec_fn=mock.ANY, stderr=STDOUT)

    self.assertFalse(success)
    self.assertEqual(msg, "Command 'failed' returned non-zero exit status 1 with output 'No file.'")

  @mock.patch('subprocess.check_output', autospec=True)
  def test_health_check_timeout(self, mock_popen):
    # Fail due to command returning a non-0 exit status.
    mock_popen.side_effect = subprocess.TimeoutExpired('failed', timeout=30)

    shell = ShellHealthCheck(raw_cmd='cmd', wrapped_cmd='wrapped-cmd', timeout_secs=30)
    success, msg = shell()
    mock_popen.assert_called_once_with(
      'wrapped-cmd', timeout=30, preexec_fn=mock.ANY, stderr=STDOUT)

    self.assertFalse(success)
    self.assertEqual(msg, 'Health check timed out.')

  @mock.patch('subprocess.check_output', autospec=True)
  def test_health_check_os_error(self, mock_popen):
    # Fail due to command not existing.
    mock_popen.side_effect = OSError(1, 'failed')

    shell = ShellHealthCheck(raw_cmd='cmd', wrapped_cmd='wrapped-cmd', timeout_secs=30)
    success, msg = shell()
    mock_popen.assert_called_once_with(
      'wrapped-cmd', timeout=30, preexec_fn=mock.ANY, stderr=STDOUT)
    self.assertFalse(success)
    self.assertEqual(msg, 'OSError: failed')

  @mock.patch('subprocess.check_output', autospec=True)
  def test_health_check_value_error(self, mock_popen):
    # Invalid commmand passed in raises ValueError.
    mock_popen.side_effect = ValueError('Could not read command.')
    timeout = 10
    shell = ShellHealthCheck(raw_cmd='cmd', wrapped_cmd='wrapped-cmd', timeout_secs=timeout)
    success, msg = shell()
    mock_popen.assert_called_once_with(
      'wrapped-cmd', timeout=timeout, preexec_fn=mock.ANY, stderr=STDOUT)
    self.assertFalse(success)
    self.assertEqual(msg, 'Invalid commmand.')
