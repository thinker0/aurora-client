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

"""Tests for OidcBearerAuth, CombinedAuth, and AuthenticateEverything in http_observer.py."""

import hashlib
import importlib.util
import os
import sys
import types
import unittest
from unittest.mock import MagicMock


# ---------------------------------------------------------------------------
# Stub heavy dependencies before loading http_observer.py
# ---------------------------------------------------------------------------

def _stub(name, **attrs):
    mod = types.ModuleType(name)
    for k, v in attrs.items():
        setattr(mod, k, v)
    sys.modules[name] = mod
    return mod


# --- bottle stubs ---
class _FakeHTTPResponse(Exception):
    def __init__(self, status=200, headers=None):
        self.status = status
        self.headers = headers or {}


class _FakePlugin:
    name = 'plugin'
    keyword = 'auth'


class _FakeRequest:
    def __init__(self):
        self.auth = None
        self.headers = {}


_fake_request = _FakeRequest()
_bottle_mod = _stub('bottle',
    Plugin=_FakePlugin,
    HTTPResponse=_FakeHTTPResponse,
    request=_fake_request,
)
_bottle_mod.install = MagicMock()

# --- expiringdict stub ---
class _FakeExpiringDict(dict):
    def __init__(self, max_len=100, max_age_seconds=300):
        super().__init__()

_stub('expiringdict', ExpiringDict=_FakeExpiringDict)

# --- rediscluster stub ---
_stub('rediscluster', RedisCluster=MagicMock())

# --- twitter.common stubs ---
_tc = _stub('twitter')
_tc_common = _stub('twitter.common', log=MagicMock())
_tc.common = _tc_common

# --- Plain base-class stubs (must come before twitter.common.http stub) ---
class _HttpPlugin:
    """Minimal Plugin base used by BasicAuth / OidcBearerAuth / CombinedAuth."""
    name = 'base_plugin'
    keyword = 'base_auth'


class _StubHttpServer:
    """Minimal HttpServer stub — decorators are pass-throughs."""
    @staticmethod
    def route(path):
        def d(fn): return fn
        return d

    @staticmethod
    def mako_view(tpl):
        def d(fn): return fn
        return d

    @staticmethod
    def view(tpl):
        def d(fn): return fn
        return d

    @staticmethod
    def abort(code, msg=''):
        raise Exception('abort %s: %s' % (code, msg))


class _StubFileBrowser:
    def __init__(self, *a, **kw): pass


class _StubJsonBindings:
    def __init__(self, *a, **kw): pass


class _StubStaticAssets:
    def __init__(self, *a, **kw): pass


# --- twitter.common.http stub ---
_stub('twitter.common.http',
    HttpServer=_StubHttpServer,
    Plugin=_HttpPlugin,
    request=_fake_request,
)

# --- requests stub (imported as _requests in http_observer.py) ---
_requests_stub = _stub('requests')

# --- thermos observer sub-module stubs ---
_stub('apache')
_stub('apache.thermos')
_stub('apache.thermos.observer')
_stub('apache.thermos.observer.http')
_stub('apache.thermos.observer.http.file_browser', TaskObserverFileBrowser=_StubFileBrowser)
_stub('apache.thermos.observer.http.json', TaskObserverJSONBindings=_StubJsonBindings)
_stub('apache.thermos.observer.http.static_assets', StaticAssets=_StubStaticAssets)
_stub('apache.thermos.observer.http.templating', HttpTemplate=MagicMock())

# ---------------------------------------------------------------------------
# Load http_observer.py directly (bypass package __init__)
# ---------------------------------------------------------------------------

_TEST_DIR = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.normpath(os.path.join(_TEST_DIR, *(['..'] * 7)))
_HTTP_OBS_PATH = os.path.join(
    _REPO_ROOT, 'src', 'main', 'python', 'apache', 'thermos', 'observer', 'http', 'http_observer.py'
)

spec = importlib.util.spec_from_file_location(
    'apache.thermos.observer.http.http_observer',
    _HTTP_OBS_PATH,
)
_mod = importlib.util.module_from_spec(spec)
_mod.__package__ = 'apache.thermos.observer.http'
sys.modules['apache.thermos.observer.http.http_observer'] = _mod
spec.loader.exec_module(_mod)

OidcBearerAuth = _mod.OidcBearerAuth
CombinedAuth = _mod.CombinedAuth
BasicAuth = _mod.BasicAuth
AuthenticateEverything = _mod.AuthenticateEverything
cache = _mod.cache  # Basic Auth credential cache


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _options(**kwargs):
    ns = MagicMock()
    for k, v in kwargs.items():
        setattr(ns, k, v)
    return ns


def _discovery_resp(status=200, userinfo_endpoint='https://auth.example.com/userinfo'):
    resp = MagicMock()
    resp.status_code = status
    resp.json.return_value = (
        {'userinfo_endpoint': userinfo_endpoint} if userinfo_endpoint else {}
    )
    return resp


def _userinfo_resp(status=200, sub='user@example.com', email='user@example.com'):
    resp = MagicMock()
    resp.status_code = status
    resp.json.return_value = {'sub': sub, 'email': email}
    return resp


def _user_hash(user, password):
    return 'sha256:%s' % hashlib.sha256(
        ('%s:%s' % (user, password)).encode('utf-8')
    ).hexdigest()


# ---------------------------------------------------------------------------
# OidcBearerAuth — setup
# ---------------------------------------------------------------------------

class TestOidcBearerAuthSetup(unittest.TestCase):

    def setUp(self):
        _mod._oidc_cache.clear()
        _requests_stub.get = MagicMock()

    def test_setup_success(self):
        opts = _options(oidc_issuer='https://auth.example.com')
        plugin = OidcBearerAuth(opts)
        _requests_stub.get.return_value = _discovery_resp(200)
        plugin.setup(MagicMock())
        self.assertEqual(plugin._userinfo_url, 'https://auth.example.com/userinfo')

    def test_setup_missing_issuer_skips_request(self):
        opts = _options(oidc_issuer=None)
        plugin = OidcBearerAuth(opts)
        plugin.setup(MagicMock())
        self.assertIsNone(plugin._userinfo_url)
        _requests_stub.get.assert_not_called()

    def test_setup_discovery_non_200_leaves_url_none(self):
        opts = _options(oidc_issuer='https://auth.example.com')
        plugin = OidcBearerAuth(opts)
        _requests_stub.get.return_value = _discovery_resp(500, None)
        plugin.setup(MagicMock())
        self.assertIsNone(plugin._userinfo_url)

    def test_setup_discovery_missing_userinfo_endpoint(self):
        opts = _options(oidc_issuer='https://auth.example.com')
        plugin = OidcBearerAuth(opts)
        _requests_stub.get.return_value = _discovery_resp(200, None)
        plugin.setup(MagicMock())
        self.assertIsNone(plugin._userinfo_url)

    def test_setup_network_exception_leaves_url_none(self):
        opts = _options(oidc_issuer='https://auth.example.com')
        plugin = OidcBearerAuth(opts)
        _requests_stub.get.side_effect = Exception('network error')
        plugin.setup(MagicMock())
        self.assertIsNone(plugin._userinfo_url)

    def test_setup_userinfo_url_skips_discovery(self):
        """--oidc-userinfo-url set → discovery request never made."""
        opts = _options(
            oidc_issuer=None,
            oidc_userinfo_url='https://oauth2proxy.example.com/oauth2/userinfo',
        )
        plugin = OidcBearerAuth(opts)
        plugin.setup(MagicMock())
        self.assertEqual(plugin._userinfo_url, 'https://oauth2proxy.example.com/oauth2/userinfo')
        _requests_stub.get.assert_not_called()

    def test_setup_userinfo_url_takes_precedence_over_issuer(self):
        """When both are set, --oidc-userinfo-url wins; no discovery request."""
        opts = _options(
            oidc_issuer='https://auth.example.com',
            oidc_userinfo_url='https://oauth2proxy.example.com/oauth2/userinfo',
        )
        plugin = OidcBearerAuth(opts)
        plugin.setup(MagicMock())
        self.assertEqual(plugin._userinfo_url, 'https://oauth2proxy.example.com/oauth2/userinfo')
        _requests_stub.get.assert_not_called()

    def test_setup_empty_userinfo_url_falls_back_to_discovery(self):
        """Empty string for --oidc-userinfo-url is treated as unset; discovery runs."""
        opts = _options(oidc_issuer='https://auth.example.com', oidc_userinfo_url='')
        plugin = OidcBearerAuth(opts)
        _requests_stub.get.return_value = _discovery_resp(200)
        plugin.setup(MagicMock())
        self.assertEqual(plugin._userinfo_url, 'https://auth.example.com/userinfo')
        _requests_stub.get.assert_called_once()

    def test_setup_rejects_non_https_userinfo_url(self):
        opts = _options(
            oidc_userinfo_url='http://oauth2proxy.example.com/oauth2/userinfo',
        )
        plugin = OidcBearerAuth(opts)
        plugin.setup(MagicMock())
        self.assertIsNone(plugin._userinfo_url)
        _requests_stub.get.assert_not_called()

    def test_setup_allows_localhost_http_userinfo_url(self):
        opts = _options(oidc_userinfo_url='http://localhost:4180/oauth2/userinfo')
        plugin = OidcBearerAuth(opts)
        plugin.setup(MagicMock())
        self.assertEqual(plugin._userinfo_url, 'http://localhost:4180/oauth2/userinfo')
        _requests_stub.get.assert_not_called()

    def test_setup_rejects_non_https_issuer(self):
        opts = _options(oidc_issuer='http://auth.example.com')
        plugin = OidcBearerAuth(opts)
        plugin.setup(MagicMock())
        self.assertIsNone(plugin._userinfo_url)
        _requests_stub.get.assert_not_called()

    def test_setup_allows_localhost_http_issuer(self):
        opts = _options(oidc_issuer='http://127.0.0.1:8081')
        plugin = OidcBearerAuth(opts)
        _requests_stub.get.return_value = _discovery_resp(200, 'http://127.0.0.1:8081/userinfo')
        plugin.setup(MagicMock())
        self.assertEqual(plugin._userinfo_url, 'http://127.0.0.1:8081/userinfo')

    def test_setup_rejects_non_https_discovered_userinfo(self):
        opts = _options(oidc_issuer='https://auth.example.com')
        plugin = OidcBearerAuth(opts)
        _requests_stub.get.return_value = _discovery_resp(200, 'http://auth.example.com/userinfo')
        plugin.setup(MagicMock())
        self.assertIsNone(plugin._userinfo_url)


# ---------------------------------------------------------------------------
# OidcBearerAuth — _validate_token
# ---------------------------------------------------------------------------

class TestOidcBearerAuthValidateToken(unittest.TestCase):

    def setUp(self):
        _mod._oidc_cache.clear()
        _requests_stub.get = MagicMock()
        opts = _options(oidc_issuer='https://auth.example.com')
        self.plugin = OidcBearerAuth(opts)
        self.plugin._userinfo_url = 'https://auth.example.com/userinfo'

    def test_cache_hit_true_skips_request(self):
        _mod._oidc_cache['tok'] = {'sub': 'cached@example.com'}
        result = self.plugin._validate_token('tok')
        self.assertEqual(result.get('sub'), 'cached@example.com')
        _requests_stub.get.assert_not_called()

    def test_cache_hit_false_skips_request(self):
        _mod._oidc_cache['bad'] = False
        self.assertIsNone(self.plugin._validate_token('bad'))
        _requests_stub.get.assert_not_called()

    def test_valid_token_returns_userinfo_and_caches(self):
        _requests_stub.get.return_value = _userinfo_resp(200)
        result = self.plugin._validate_token('valid')
        self.assertEqual(result.get('email'), 'user@example.com')
        self.assertEqual(_mod._oidc_cache.get('valid').get('sub'), 'user@example.com')

    def test_invalid_token_returns_none_and_caches_false(self):
        _requests_stub.get.return_value = _userinfo_resp(401)
        self.assertIsNone(self.plugin._validate_token('expired'))
        self.assertFalse(_mod._oidc_cache.get('expired'))

    def test_no_userinfo_url_returns_false(self):
        self.plugin._userinfo_url = None
        self.assertIsNone(self.plugin._validate_token('tok'))
        _requests_stub.get.assert_not_called()

    def test_request_exception_returns_false(self):
        _requests_stub.get.side_effect = Exception('timeout')
        self.assertIsNone(self.plugin._validate_token('tok'))

    def test_json_parse_error_returns_none(self):
        resp = MagicMock()
        resp.status_code = 200
        resp.json.side_effect = ValueError('bad json')
        _requests_stub.get.return_value = resp
        self.assertIsNone(self.plugin._validate_token('tok2'))


# ---------------------------------------------------------------------------
# OidcBearerAuth — apply (per-request middleware)
# ---------------------------------------------------------------------------

class TestOidcBearerAuthApply(unittest.TestCase):

    def setUp(self):
        _mod._oidc_cache.clear()
        _requests_stub.get = MagicMock()
        opts = _options(oidc_issuer='https://auth.example.com')
        self.plugin = OidcBearerAuth(opts)
        self.plugin._userinfo_url = 'https://auth.example.com/userinfo'
        self.callback = MagicMock(return_value='ok')

    def _wrap(self, auth_header=None, trusted_user='user@example.com', trusted_header='X-Forwarded-User'):
        headers = {}
        if auth_header:
            headers['Authorization'] = auth_header
        if trusted_user:
            headers[trusted_header] = trusted_user
        _mod.request.headers = headers
        return self.plugin.apply(self.callback, MagicMock())

    def test_valid_bearer_calls_callback(self):
        _mod._oidc_cache['good'] = {'sub': 'user@example.com'}
        result = self._wrap('Bearer good')()
        self.assertEqual(result, 'ok')

    def test_invalid_bearer_raises_401(self):
        _mod._oidc_cache['bad'] = False
        with self.assertRaises(_FakeHTTPResponse) as ctx:
            self._wrap('Bearer bad')()
        self.assertEqual(ctx.exception.status, 401)

    def test_no_auth_header_raises_401(self):
        with self.assertRaises(_FakeHTTPResponse) as ctx:
            self._wrap(None)()
        self.assertEqual(ctx.exception.status, 401)

    def test_basic_scheme_not_accepted_raises_401(self):
        with self.assertRaises(_FakeHTTPResponse) as ctx:
            self._wrap('Basic dXNlcjpwYXNz')()
        self.assertEqual(ctx.exception.status, 401)

    def test_missing_trusted_header_raises_401(self):
        _mod._oidc_cache['good'] = {'sub': 'user@example.com'}
        with self.assertRaises(_FakeHTTPResponse) as ctx:
            self._wrap('Bearer good', trusted_user=None)()
        self.assertEqual(ctx.exception.status, 401)

    def test_trusted_header_mismatch_raises_401(self):
        _mod._oidc_cache['good'] = {'sub': 'user@example.com', 'email': 'user@example.com'}
        with self.assertRaises(_FakeHTTPResponse) as ctx:
            self._wrap('Bearer good', trusted_user='other@example.com')()
        self.assertEqual(ctx.exception.status, 401)

    def test_accepts_x_auth_request_user_header(self):
        _mod._oidc_cache['good'] = {'sub': 'user@example.com'}
        result = self._wrap('Bearer good', trusted_user='user@example.com', trusted_header='X-Auth-Request-User')()
        self.assertEqual(result, 'ok')


# ---------------------------------------------------------------------------
# CombinedAuth
# ---------------------------------------------------------------------------

class TestCombinedAuth(unittest.TestCase):

    def setUp(self):
        _mod._oidc_cache.clear()
        _requests_stub.get = MagicMock()
        self.callback = MagicMock(return_value='ok')
        opts = _options(
            oidc_issuer='https://auth.example.com',
            redis_cluster='redis://localhost:6379',
            redis_key_prefix='/aurora/thermos/user/',
        )
        self.plugin = CombinedAuth(opts)
        self.plugin._oidc._userinfo_url = 'https://auth.example.com/userinfo'

    def _wrap(self, bearer=None, basic_user=None, basic_pass=None, trusted_user='user@example.com'):
        headers = {'Authorization': 'Bearer ' + bearer} if bearer else {}
        if trusted_user:
            headers['X-Forwarded-User'] = trusted_user
        _mod.request.headers = headers
        _mod.request.auth = (basic_user, basic_pass) if basic_user else None
        return self.plugin.apply(self.callback, MagicMock())

    def test_oidc_bearer_accepted(self):
        _mod._oidc_cache['tok'] = {'sub': 'user@example.com'}
        result = self._wrap(bearer='tok')()
        self.assertEqual(result, 'ok')

    def test_basic_accepted_when_no_bearer(self):
        self.plugin._basic.get_user = MagicMock(return_value=_user_hash('alice', 'secret'))
        result = self._wrap(basic_user='alice', basic_pass='secret')()
        self.assertEqual(result, 'ok')

    def test_basic_accepted_when_oidc_fails(self):
        _mod._oidc_cache['bad'] = False
        self.plugin._basic.get_user = MagicMock(return_value=_user_hash('alice', 'secret'))
        result = self._wrap(bearer='bad', basic_user='alice', basic_pass='secret')()
        self.assertEqual(result, 'ok')

    def test_basic_fallback_when_trusted_header_mismatch(self):
        _mod._oidc_cache['tok'] = {'sub': 'user@example.com'}
        self.plugin._basic.get_user = MagicMock(return_value=_user_hash('alice', 'secret'))
        result = self._wrap(
            bearer='tok',
            trusted_user='other@example.com',
            basic_user='alice',
            basic_pass='secret',
        )()
        self.assertEqual(result, 'ok')

    def test_wrong_basic_password_raises_401(self):
        self.plugin._basic.get_user = MagicMock(return_value=_user_hash('alice', 'correct'))
        with self.assertRaises(_FakeHTTPResponse) as ctx:
            self._wrap(basic_user='alice', basic_pass='wrong')()
        self.assertEqual(ctx.exception.status, 401)

    def test_no_credentials_raises_401(self):
        with self.assertRaises(_FakeHTTPResponse) as ctx:
            self._wrap()()
        self.assertEqual(ctx.exception.status, 401)


# ---------------------------------------------------------------------------
# AuthenticateEverything
# ---------------------------------------------------------------------------

class TestAuthenticateEverything(unittest.TestCase):

    def setUp(self):
        _bottle_mod.install = MagicMock()

    def _make(self, mode):
        opts = _options(
            enable_authentication=mode,
            oidc_issuer='https://auth.example.com',
            redis_cluster='redis://localhost:6379',
            redis_key_prefix='/aurora/thermos/user/',
        )
        return AuthenticateEverything(opts)

    def test_basic_mode(self):
        ae = self._make('basic')
        self.assertEqual(len(ae.plugins), 1)
        self.assertIsInstance(ae.plugins[0], BasicAuth)
        _bottle_mod.install.assert_called_once()

    def test_oidc_mode(self):
        ae = self._make('oidc')
        self.assertEqual(len(ae.plugins), 1)
        self.assertIsInstance(ae.plugins[0], OidcBearerAuth)

    def test_oidc_plus_basic_mode(self):
        ae = self._make('oidc+basic')
        self.assertEqual(len(ae.plugins), 1)
        self.assertIsInstance(ae.plugins[0], CombinedAuth)

    def test_none_mode_no_plugin(self):
        ae = self._make(None)
        self.assertEqual(len(ae.plugins), 0)
        _bottle_mod.install.assert_not_called()

    def test_unknown_mode_no_plugin(self):
        ae = self._make('kerberos')
        self.assertEqual(len(ae.plugins), 0)

    def test_mode_is_case_insensitive(self):
        ae = self._make('OIDC+BASIC')
        self.assertIsInstance(ae.plugins[0], CombinedAuth)

    def test_plugins_is_instance_not_class_variable(self):
        ae1 = self._make('basic')
        ae2 = self._make('oidc')
        self.assertIsNot(ae1.plugins, ae2.plugins)
        self.assertIsInstance(ae1.plugins[0], BasicAuth)
        self.assertIsInstance(ae2.plugins[0], OidcBearerAuth)


# ---------------------------------------------------------------------------
# BasicAuth.apply — cache always populated (regression for early-return bug)
# ---------------------------------------------------------------------------

class TestBasicAuthApply(unittest.TestCase):

    def setUp(self):
        opts = _options(
            redis_cluster='redis://localhost:6379',
            redis_key_prefix='/aurora/thermos/user/',
        )
        self.plugin = BasicAuth(opts)
        self.plugin._authRedis = MagicMock()
        self.callback = MagicMock(return_value='ok')

    def test_valid_credentials_calls_callback_and_sets_cache(self):
        user, password = 'alice', 'secret'
        stored_hash = _user_hash(user, password)
        self.plugin._authRedis.get = MagicMock(return_value=stored_hash)
        _mod.request.auth = (user, password)
        wrap = self.plugin.apply(self.callback, MagicMock())
        result = wrap()
        self.assertEqual(result, 'ok')
        # cache must be populated after successful auth
        self.assertEqual(cache.get(user), stored_hash)

    def test_wrong_password_raises_401(self):
        stored_hash = _user_hash('alice', 'correct')
        self.plugin._authRedis.get = MagicMock(return_value=stored_hash)
        _mod.request.auth = ('alice', 'wrong')
        wrap = self.plugin.apply(self.callback, MagicMock())
        with self.assertRaises(_FakeHTTPResponse) as ctx:
            wrap()
        self.assertEqual(ctx.exception.status, 401)

    def test_no_credentials_raises_401(self):
        _mod.request.auth = None
        wrap = self.plugin.apply(self.callback, MagicMock())
        with self.assertRaises(_FakeHTTPResponse) as ctx:
            wrap()
        self.assertEqual(ctx.exception.status, 401)


# ---------------------------------------------------------------------------
# AuthenticateEverything.close — plugin cleanup
# ---------------------------------------------------------------------------

class TestAuthenticateEverythingClose(unittest.TestCase):

    def setUp(self):
        _bottle_mod.install = MagicMock()

    def test_close_calls_plugin_close(self):
        opts = _options(
            enable_authentication='oidc',
            oidc_issuer='https://auth.example.com',
            redis_cluster='redis://localhost:6379',
            redis_key_prefix='/aurora/thermos/user/',
        )
        ae = AuthenticateEverything(opts)
        ae.plugins[0].close = MagicMock()
        ae.close()
        ae.plugins[0].close.assert_called_once()

    def test_close_tolerates_plugin_error(self):
        opts = _options(
            enable_authentication='oidc',
            oidc_issuer='https://auth.example.com',
            redis_cluster='redis://localhost:6379',
            redis_key_prefix='/aurora/thermos/user/',
        )
        ae = AuthenticateEverything(opts)
        ae.plugins[0].close = MagicMock(side_effect=Exception('redis gone'))
        ae.close()  # must not raise

    def test_close_no_plugins_is_safe(self):
        opts = _options(enable_authentication=None)
        ae = AuthenticateEverything(opts)
        ae.close()  # must not raise


if __name__ == '__main__':
    unittest.main()
