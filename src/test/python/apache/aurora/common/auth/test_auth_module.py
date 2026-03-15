
import os
import unittest
from unittest.mock import mock_open, patch, MagicMock
from apache.aurora.common.auth.auth_module import ProxySessionAuth, SessionTokenAuth, OidcDeviceAuth

class TestAuthModules(unittest.TestCase):
  @patch('os.path.exists')
  def test_proxy_session_auth_with_cluster(self, mock_exists):
    mock_exists.return_value = True
    m = mock_open(read_data='_oauth2_proxy=v1abc')
    with patch('builtins.open', m):
      auth = ProxySessionAuth(cluster_name='lad-beta')
      request = MagicMock()
      request.headers = {}
      auth(request)
      
      self.assertEqual(request.headers['Cookie'], '_oauth2_proxy=v1abc')
      # Verify correct file path was used
      expected_path = os.path.expanduser('~/.aurora/session.lad-beta')
      m.assert_called_with(expected_path, 'r')

  @patch('os.path.exists')
  def test_session_token_auth_with_cluster(self, mock_exists):
    mock_exists.return_value = True
    m = mock_open(read_data='secret-token-123')
    with patch('builtins.open', m):
      auth = SessionTokenAuth(cluster_name='prod-cluster')
      request = MagicMock()
      request.headers = {}
      auth(request)
      
      self.assertEqual(request.headers['Authorization'], 'Bearer secret-token-123')
      expected_path = os.path.expanduser('~/.aurora/token.prod-cluster')
      m.assert_called_with(expected_path, 'r')

  @patch('os.path.exists')
  def test_oidc_device_auth_load_token(self, mock_exists):
    mock_exists.return_value = True
    m = mock_open(read_data='{"access_token": "jwt-token-xyz"}')
    with patch('builtins.open', m):
      auth = OidcDeviceAuth(token_file='/tmp/token.json')
      self.assertEqual(auth._access_token, 'jwt-token-xyz')
