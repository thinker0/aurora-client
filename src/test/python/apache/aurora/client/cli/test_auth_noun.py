
import importlib.util
import json
import os
import sys
import types
import tempfile
import time
import unittest
import urllib.error
from io import BytesIO
from unittest.mock import MagicMock, patch

# ---------------------------------------------------------------------------
# Stub out heavy Aurora/thrift deps before loading auth.py directly
# ---------------------------------------------------------------------------

def _stub(name, **attrs):
    mod = types.ModuleType(name)
    for k, v in attrs.items():
        setattr(mod, k, v)
    sys.modules[name] = mod
    return mod

class _Verb:
    @property
    def name(self): return ''
    def get_options(self): return []
    def execute(self, context): return 0

class _Noun:
    def __init__(self):
        self._verbs = {}
    @property
    def name(self): return ''
    def register_verb(self, verb): self._verbs[verb.name] = verb
    @property
    def verbs(self): return self._verbs

_apache_stub   = _stub('apache')
_aurora_stub   = _stub('apache.aurora')
_client_stub   = _stub('apache.aurora.client')
_cli_stub      = _stub('apache.aurora.client.cli', Noun=_Noun, Verb=_Verb)
_common_stub   = _stub('apache.aurora.common')
_stub('apache.aurora.client.cli.context', AuroraCommandContext=MagicMock)
_stub('apache.aurora.client.cli.options', CommandOption=MagicMock)
_stub('apache.aurora.common.clusters', CLUSTERS={})

# Wire attribute chain so patch() can traverse dotted paths
_apache_stub.aurora  = _aurora_stub
_aurora_stub.client  = _client_stub
_aurora_stub.common  = _common_stub
_client_stub.cli     = _cli_stub

# Load auth.py directly from the source file, bypassing the package __init__
_AUTH_PY = os.path.join(
    os.path.dirname(__file__),
    '..', '..', '..', '..', '..', '..', '..', '..', '..', '..', '..', '..', '..', '..',
    'src', 'main', 'python', 'apache', 'aurora', 'client', 'cli', 'auth.py',
)
_AUTH_PY = os.path.normpath(os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    '../../../../../../main/python/apache/aurora/client/cli/auth.py',
))
_spec = importlib.util.spec_from_file_location('apache.aurora.client.cli.auth', _AUTH_PY)
_auth_mod = importlib.util.module_from_spec(_spec)
sys.modules['apache.aurora.client.cli.auth'] = _auth_mod
_spec.loader.exec_module(_auth_mod)

# Wire up parent module attributes so patch() can traverse the dotted path
_cli_stub.auth = _auth_mod
_client_stub.cli = _cli_stub

from apache.aurora.client.cli.auth import (  # noqa: E402
    Auth,
    LoginVerb,
    _is_browser_available,
    _pkce_pair,
    _persist_tokens,
    _poll_device_token,
    _refresh_tokens,
    get_valid_session,
    load_session,
    save_session,
)


class TestIsBrowserAvailable(unittest.TestCase):
    def test_no_tty_returns_false(self):
        with patch('sys.stdout') as mock_stdout:
            mock_stdout.isatty.return_value = False
            self.assertFalse(_is_browser_available())

    def test_darwin_returns_true(self):
        with patch('sys.stdout') as mock_stdout:
            mock_stdout.isatty.return_value = True
            with patch.object(sys, 'platform', 'darwin'):
                self.assertTrue(_is_browser_available())

    def test_win32_returns_true(self):
        with patch('sys.stdout') as mock_stdout:
            mock_stdout.isatty.return_value = True
            with patch.object(sys, 'platform', 'win32'):
                self.assertTrue(_is_browser_available())

    def test_cygwin_returns_true(self):
        with patch('sys.stdout') as mock_stdout:
            mock_stdout.isatty.return_value = True
            with patch.object(sys, 'platform', 'cygwin'):
                self.assertTrue(_is_browser_available())

    def test_linux_with_display_returns_true(self):
        with patch('sys.stdout') as mock_stdout:
            mock_stdout.isatty.return_value = True
            with patch.object(sys, 'platform', 'linux'):
                with patch.dict(os.environ, {'DISPLAY': ':0'}, clear=True):
                    self.assertTrue(_is_browser_available())

    def test_linux_with_wayland_returns_true(self):
        with patch('sys.stdout') as mock_stdout:
            mock_stdout.isatty.return_value = True
            with patch.object(sys, 'platform', 'linux'):
                with patch.dict(os.environ, {'WAYLAND_DISPLAY': 'wayland-0'}, clear=True):
                    self.assertTrue(_is_browser_available())

    def test_linux_headless_returns_false(self):
        with patch('sys.stdout') as mock_stdout:
            mock_stdout.isatty.return_value = True
            with patch.object(sys, 'platform', 'linux'):
                env = {k: v for k, v in os.environ.items()
                       if k not in ('DISPLAY', 'WAYLAND_DISPLAY')}
                with patch.dict(os.environ, env, clear=True):
                    self.assertFalse(_is_browser_available())


class TestPkcePair(unittest.TestCase):
    def test_returns_verifier_and_challenge(self):
        verifier, challenge = _pkce_pair()
        self.assertIsInstance(verifier, str)
        self.assertIsInstance(challenge, str)
        self.assertTrue(len(verifier) > 40)

    def test_challenge_has_no_padding(self):
        _, challenge = _pkce_pair()
        self.assertNotIn('+', challenge)
        self.assertNotIn('/', challenge)
        self.assertNotIn('=', challenge)

    def test_unique_pairs(self):
        v1, _ = _pkce_pair()
        v2, _ = _pkce_pair()
        self.assertNotEqual(v1, v2)


class TestSessionPersistence(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def test_save_and_load_roundtrip(self):
        with patch('apache.aurora.client.cli.auth.SESSION_DIR', self.tmpdir):
            save_session('mycluster', {'access_token': 'abc'})
            result = load_session('mycluster')
        self.assertEqual(result['access_token'], 'abc')

    def test_load_nonexistent_returns_none(self):
        with patch('apache.aurora.client.cli.auth.SESSION_DIR', self.tmpdir):
            self.assertIsNone(load_session('nonexistent'))

    def test_session_file_permissions(self):
        with patch('apache.aurora.client.cli.auth.SESSION_DIR', self.tmpdir):
            save_session('mycluster', {'token': 'x'})
            path = os.path.join(self.tmpdir, 'session.mycluster')
            self.assertEqual(oct(os.stat(path).st_mode)[-3:], '600')


class TestPersistTokens(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def test_adds_expires_at_and_cluster(self):
        with patch('apache.aurora.client.cli.auth.SESSION_DIR', self.tmpdir):
            with patch('apache.aurora.client.cli.auth.time.time', return_value=1000):
                _persist_tokens('mycluster', {'access_token': 'tok', 'expires_in': 3600})
            result = load_session('mycluster')
        self.assertEqual(result['expires_at'], 4600)
        self.assertEqual(result['cluster'], 'mycluster')

    def test_stores_token_endpoint_and_client_id(self):
        with patch('apache.aurora.client.cli.auth.SESSION_DIR', self.tmpdir):
            _persist_tokens(
                'mycluster',
                {'access_token': 'tok'},
                token_endpoint='https://auth.example.com/token',
                client_id='aurora-cli',
            )
            result = load_session('mycluster')
        self.assertEqual(result['token_endpoint'], 'https://auth.example.com/token')
        self.assertEqual(result['client_id'], 'aurora-cli')

    def test_missing_access_token_raises(self):
        with patch('apache.aurora.client.cli.auth.SESSION_DIR', self.tmpdir):
            with self.assertRaises(ValueError):
                _persist_tokens('mycluster', {'token_type': 'Bearer'})


class TestPollDeviceToken(unittest.TestCase):
    def _http_error(self, body_dict):
        body = json.dumps(body_dict).encode()
        return urllib.error.HTTPError(
            url='http://x', code=400, msg='Bad',
            hdrs=None, fp=BytesIO(body),
        )

    def _mock_response(self, data):
        m = MagicMock()
        m.__enter__ = lambda s: s
        m.__exit__ = MagicMock(return_value=False)
        m.read = MagicMock(return_value=json.dumps(data).encode())
        return m

    @patch('apache.aurora.client.cli.auth.time.sleep')
    @patch('apache.aurora.client.cli.auth.time.time')
    @patch('urllib.request.urlopen')
    def test_returns_tokens_on_success(self, mock_urlopen, mock_time, _sleep):
        mock_time.side_effect = [0, 1]
        mock_urlopen.return_value = self._mock_response({'access_token': 'tok'})
        result = _poll_device_token('http://token', 'client', 'devcode', 5, 300)
        self.assertEqual(result['access_token'], 'tok')

    @patch('apache.aurora.client.cli.auth.time.sleep')
    @patch('apache.aurora.client.cli.auth.time.time')
    @patch('urllib.request.urlopen')
    def test_retries_on_authorization_pending(self, mock_urlopen, mock_time, _sleep):
        mock_time.side_effect = [0, 1, 2]
        calls = [0]

        def side_effect(*a, **kw):
            calls[0] += 1
            if calls[0] == 1:
                raise self._http_error({'error': 'authorization_pending'})
            return self._mock_response({'access_token': 'tok'})

        mock_urlopen.side_effect = side_effect
        result = _poll_device_token('http://token', 'client', 'devcode', 5, 300)
        self.assertEqual(result['access_token'], 'tok')

    @patch('apache.aurora.client.cli.auth.time.sleep')
    @patch('apache.aurora.client.cli.auth.time.time')
    @patch('urllib.request.urlopen')
    def test_raises_on_expired_token(self, mock_urlopen, mock_time, _sleep):
        mock_time.side_effect = [0, 1]
        mock_urlopen.side_effect = self._http_error({'error': 'expired_token'})
        with self.assertRaises(RuntimeError) as ctx:
            _poll_device_token('http://token', 'client', 'devcode', 5, 300)
        self.assertIn('expired', str(ctx.exception).lower())

    @patch('apache.aurora.client.cli.auth.time.sleep')
    @patch('apache.aurora.client.cli.auth.time.time')
    def test_raises_on_timeout(self, mock_time, _sleep):
        mock_time.side_effect = [0, 9999]
        with self.assertRaises(RuntimeError) as ctx:
            _poll_device_token('http://token', 'client', 'devcode', 5, 300)
        self.assertIn('timed out', str(ctx.exception).lower())

    @patch('apache.aurora.client.cli.auth.time.sleep')
    @patch('apache.aurora.client.cli.auth.time.time')
    @patch('urllib.request.urlopen')
    def test_slow_down_caps_at_60(self, mock_urlopen, mock_time, mock_sleep):
        mock_time.side_effect = [0, 1, 2, 3]
        waits = []

        def side_effect(*a, **kw):
            # first two calls: slow_down; third: success
            if len(waits) < 2:
                raise self._http_error({'error': 'slow_down'})
            return self._mock_response({'access_token': 'tok'})

        mock_urlopen.side_effect = side_effect
        mock_sleep.side_effect = lambda w: waits.append(w)
        _poll_device_token('http://token', 'client', 'devcode', 55, 300)
        # After two slow_down bumps: 55+5=60, then min(60+5,60)=60
        self.assertTrue(all(w <= 60 for w in waits))

    @patch('apache.aurora.client.cli.auth.time.sleep')
    @patch('apache.aurora.client.cli.auth.time.time')
    @patch('urllib.request.urlopen')
    def test_raises_on_non_json_http_error(self, mock_urlopen, mock_time, _sleep):
        mock_time.side_effect = [0, 1]
        err = urllib.error.HTTPError(
            url='http://x', code=500, msg='Internal Server Error',
            hdrs=None, fp=BytesIO(b'<html>Server Error</html>'),
        )
        mock_urlopen.side_effect = err
        with self.assertRaises(RuntimeError) as ctx:
            _poll_device_token('http://token', 'client', 'devcode', 5, 300)
        self.assertIn('500', str(ctx.exception))


class TestLoginVerbExecute(unittest.TestCase):
    def _ctx(self, cluster_name='mycluster', device=False):
        ctx = MagicMock()
        ctx.options.cluster = cluster_name
        ctx.options.device = device
        return ctx

    def _cluster(self, issuer='https://auth.example.com'):
        c = MagicMock(spec=['oidc_issuer', 'oidc_client_id'])
        c.oidc_issuer = issuer
        c.oidc_client_id = 'aurora-cli'
        return c

    def test_unknown_cluster_returns_error(self):
        verb = LoginVerb()
        with patch('apache.aurora.client.cli.auth.CLUSTERS', {}):
            self.assertEqual(verb.execute(self._ctx('unknown')), 1)

    def test_missing_oidc_issuer_returns_error(self):
        verb = LoginVerb()
        cluster = MagicMock(spec=[])
        with patch('apache.aurora.client.cli.auth.CLUSTERS', {'mycluster': cluster}):
            self.assertEqual(verb.execute(self._ctx()), 1)

    def test_discovery_failure_returns_error(self):
        verb = LoginVerb()
        with patch('apache.aurora.client.cli.auth.CLUSTERS', {'mycluster': self._cluster()}):
            with patch('apache.aurora.client.cli.auth._oidc_discovery',
                       side_effect=Exception('network')):
                self.assertEqual(verb.execute(self._ctx()), 1)

    @patch('apache.aurora.client.cli.auth._device_auth', return_value=0)
    @patch('apache.aurora.client.cli.auth._oidc_discovery', return_value={})
    def test_device_flag_forces_device_flow(self, _disc, mock_device):
        verb = LoginVerb()
        with patch('apache.aurora.client.cli.auth.CLUSTERS', {'mycluster': self._cluster()}):
            self.assertEqual(verb.execute(self._ctx(device=True)), 0)
        mock_device.assert_called_once()

    @patch('apache.aurora.client.cli.auth._device_auth', return_value=0)
    @patch('apache.aurora.client.cli.auth._is_browser_available', return_value=False)
    @patch('apache.aurora.client.cli.auth._oidc_discovery', return_value={})
    def test_headless_uses_device_flow(self, _disc, _avail, mock_device):
        verb = LoginVerb()
        with patch('apache.aurora.client.cli.auth.CLUSTERS', {'mycluster': self._cluster()}):
            self.assertEqual(verb.execute(self._ctx()), 0)
        mock_device.assert_called_once()

    @patch('apache.aurora.client.cli.auth._browser_auth', return_value=0)
    @patch('apache.aurora.client.cli.auth._is_browser_available', return_value=True)
    @patch('apache.aurora.client.cli.auth._oidc_discovery', return_value={})
    def test_desktop_uses_browser_flow(self, _disc, _avail, mock_browser):
        verb = LoginVerb()
        with patch('apache.aurora.client.cli.auth.CLUSTERS', {'mycluster': self._cluster()}):
            self.assertEqual(verb.execute(self._ctx()), 0)
        mock_browser.assert_called_once()

    @patch('apache.aurora.client.cli.auth._device_auth', return_value=0)
    @patch('apache.aurora.client.cli.auth._is_browser_available', return_value=False)
    @patch('apache.aurora.client.cli.auth._oidc_discovery', return_value={})
    def test_discovery_url_strips_trailing_slash(self, mock_disc, _avail, _device):
        verb = LoginVerb()
        cluster = self._cluster(issuer='https://auth.example.com/')
        with patch('apache.aurora.client.cli.auth.CLUSTERS', {'mycluster': cluster}):
            verb.execute(self._ctx())
        mock_disc.assert_called_once_with(
            'https://auth.example.com/.well-known/openid-configuration'
        )


class TestGetValidSession(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def _save(self, data):
        with patch('apache.aurora.client.cli.auth.SESSION_DIR', self.tmpdir):
            save_session('c', data)

    def test_returns_none_when_no_session(self):
        with patch('apache.aurora.client.cli.auth.SESSION_DIR', self.tmpdir):
            self.assertIsNone(get_valid_session('c'))

    def test_returns_session_when_not_expired(self):
        self._save({'access_token': 'tok', 'expires_at': time.time() + 3600})
        with patch('apache.aurora.client.cli.auth.SESSION_DIR', self.tmpdir):
            result = get_valid_session('c')
        self.assertEqual(result['access_token'], 'tok')

    def test_returns_none_when_expired_no_refresh_token(self):
        self._save({'access_token': 'old', 'expires_at': 1})
        with patch('apache.aurora.client.cli.auth.SESSION_DIR', self.tmpdir):
            self.assertIsNone(get_valid_session('c'))

    @patch('apache.aurora.client.cli.auth._refresh_tokens')
    def test_refreshes_when_expired(self, mock_refresh):
        self._save({
            'access_token': 'old',
            'expires_at': 1,
            'refresh_token': 'reftok',
            'token_endpoint': 'https://auth.example.com/token',
            'client_id': 'aurora-cli',
        })
        mock_refresh.return_value = {
            'access_token': 'new',
            'expires_in': 3600,
            'refresh_token': 'reftok',
        }
        with patch('apache.aurora.client.cli.auth.SESSION_DIR', self.tmpdir):
            result = get_valid_session('c')
        self.assertEqual(result['access_token'], 'new')
        mock_refresh.assert_called_once_with(
            'https://auth.example.com/token', 'aurora-cli', 'reftok'
        )

    @patch('apache.aurora.client.cli.auth._refresh_tokens', side_effect=Exception('network'))
    def test_returns_none_on_refresh_failure(self, _mock):
        self._save({
            'access_token': 'old',
            'expires_at': 1,
            'refresh_token': 'reftok',
            'token_endpoint': 'https://auth.example.com/token',
            'client_id': 'aurora-cli',
        })
        with patch('apache.aurora.client.cli.auth.SESSION_DIR', self.tmpdir):
            self.assertIsNone(get_valid_session('c'))

    @patch('apache.aurora.client.cli.auth._refresh_tokens')
    def test_preserves_refresh_token_if_not_in_response(self, mock_refresh):
        self._save({
            'access_token': 'old',
            'expires_at': 1,
            'refresh_token': 'original_ref',
            'token_endpoint': 'https://auth.example.com/token',
            'client_id': 'aurora-cli',
        })
        mock_refresh.return_value = {'access_token': 'new', 'expires_in': 3600}
        with patch('apache.aurora.client.cli.auth.SESSION_DIR', self.tmpdir):
            result = get_valid_session('c')
        self.assertEqual(result['refresh_token'], 'original_ref')


class TestAuthNoun(unittest.TestCase):
    def test_noun_name(self):
        self.assertEqual(Auth().name, 'auth')

    def test_has_login_verb(self):
        self.assertIn('login', Auth().verbs)

    def test_login_verb_name(self):
        self.assertEqual(LoginVerb().name, 'login')


if __name__ == '__main__':
    unittest.main()
