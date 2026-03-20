
import os
import unittest
from unittest.mock import mock_open, patch, MagicMock
from apache.aurora.common.auth.auth_module import (
  OidcDeviceAuth,
  OidcDeviceAuthModule,
  ProxySessionAuth,
  SessionTokenAuth,
  _refresh_session_data,
)

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

  def test_oidc_device_auth_module_uses_cluster_session_file(self):
    with patch('os.path.exists', return_value=False):
      auth = OidcDeviceAuthModule().auth(cluster_name='prod')
    self.assertEqual(auth._token_file, os.path.expanduser('~/.aurora/session.prod'))

  def test_session_token_auth_falls_back_to_session_json(self):
    def _exists(path):
      return path.endswith('/session.prod')

    with patch('os.path.exists', side_effect=_exists):
      m = mock_open(read_data='{"access_token":"session-token"}')
      with patch('builtins.open', m):
        auth = SessionTokenAuth(cluster_name='prod')
        request = MagicMock()
        request.headers = {}
        auth(request)
        self.assertEqual(request.headers['Authorization'], 'Bearer session-token')

  @patch('apache.aurora.common.auth.auth_module.requests.post')
  def test_session_token_auth_refreshes_expired_session_json(self, mock_post):
    def _exists(path):
      return path.endswith('/session.prod')

    refreshed = MagicMock()
    refreshed.json.return_value = {'access_token': 'new-token', 'expires_in': 3600}
    mock_post.return_value = refreshed
    session_json = (
      '{"access_token":"old-token","expires_at":1,'
      '"refresh_token":"refresh-token","token_endpoint":"https://auth.example.com/token",'
      '"client_id":"aurora-cli"}'
    )
    with patch('os.path.exists', side_effect=_exists):
      m = mock_open(read_data=session_json)
      with patch('builtins.open', m):
        auth = SessionTokenAuth(cluster_name='prod')
        request = MagicMock()
        request.headers = {}
        auth(request)
        self.assertEqual(request.headers['Authorization'], 'Bearer new-token')

  @patch('apache.aurora.common.auth.auth_module.requests.post')
  def test_refresh_session_data_includes_client_secret(self, mock_post):
    mock_post.return_value = MagicMock(
      json=MagicMock(return_value={'access_token': 'new', 'expires_in': 3600})
    )
    session = {
      'access_token': 'old',
      'expires_at': 1,
      'refresh_token': 'ref',
      'token_endpoint': 'https://auth.example.com/token',
      'client_id': 'aurora-cli',
      'client_secret': 'supersecret',
    }
    result = _refresh_session_data(session)
    self.assertIsNotNone(result)
    _, kwargs = mock_post.call_args
    self.assertEqual(kwargs['data']['client_secret'], 'supersecret')

  @patch('apache.aurora.common.auth.auth_module.requests.post')
  def test_refresh_session_data_omits_client_secret_when_absent(self, mock_post):
    mock_post.return_value = MagicMock(
      json=MagicMock(return_value={'access_token': 'new', 'expires_in': 3600})
    )
    session = {
      'access_token': 'old',
      'expires_at': 1,
      'refresh_token': 'ref',
      'token_endpoint': 'https://auth.example.com/token',
      'client_id': 'aurora-cli',
    }
    result = _refresh_session_data(session)
    self.assertIsNotNone(result)
    _, kwargs = mock_post.call_args
    self.assertNotIn('client_secret', kwargs['data'])

  @patch('apache.aurora.common.auth.auth_module.requests.post')
  def test_oidc_device_auth_refresh_includes_client_secret(self, mock_post):
    mock_post.return_value = MagicMock(
      json=MagicMock(return_value={'access_token': 'new', 'expires_in': 3600})
    )
    with patch('os.path.exists', return_value=False):
      auth = OidcDeviceAuth(cluster_name='prod')
    session = {
      'access_token': 'old',
      'refresh_token': 'ref',
      'token_endpoint': 'https://auth.example.com/token',
      'client_id': 'aurora-cli',
      'client_secret': 'topsecret',
    }
    result = auth._refresh_token(session)
    self.assertIsNotNone(result)
    _, kwargs = mock_post.call_args
    self.assertEqual(kwargs['data']['client_secret'], 'topsecret')

  def test_session_token_auth_no_token_passes_request_unchanged(self):
    with patch('os.path.exists', return_value=False):
      auth = SessionTokenAuth(cluster_name='no-token-cluster')
    request = MagicMock()
    request.headers = {}
    auth(request)
    self.assertNotIn('Authorization', request.headers)
