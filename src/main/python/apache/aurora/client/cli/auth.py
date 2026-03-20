
import base64
import hashlib
import http.server
import json
import os
import secrets
import socketserver
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import webbrowser
from urllib.parse import urlparse, parse_qs

from twitter.common import log

from apache.aurora.client.cli import Noun, Verb
from apache.aurora.client.cli.context import AuroraCommandContext
from apache.aurora.client.cli.options import CommandOption
from apache.aurora.common.clusters import CLUSTERS


SESSION_DIR = os.path.expanduser('~/.aurora')

_DISCOVERY_TIMEOUT = 10
_TOKEN_TIMEOUT = 15
_BROWSER_TIMEOUT = 300
_DEFAULT_OIDC_SCOPE = 'openid email profile'


def _session_file(cluster_name):
    return os.path.join(SESSION_DIR, f'session.{cluster_name}')


def _normalize_oidc_scope(scope_value):
    if not scope_value:
        return _DEFAULT_OIDC_SCOPE
    if isinstance(scope_value, (list, tuple)):
        return ' '.join(str(s).strip() for s in scope_value if str(s).strip())
    return str(scope_value).strip()


def save_session(cluster_name, data):
    os.makedirs(SESSION_DIR, mode=0o700, exist_ok=True)
    path = _session_file(cluster_name)
    fd = os.open(path, os.O_CREAT | os.O_WRONLY | os.O_TRUNC, 0o600)
    with os.fdopen(fd, 'w') as f:
        json.dump(data, f)


def load_session(cluster_name):
    path = _session_file(cluster_name)
    if not os.path.exists(path):
        return None
    with open(path) as f:
        return json.load(f)


def _validate_https_url(url, label='URL'):
    parsed = urlparse(url)
    if parsed.scheme != 'https':
        raise ValueError(
            f'{label} must use HTTPS (got {parsed.scheme!r}): {url}'
        )


def _oidc_discovery(discovery_url):
    _validate_https_url(discovery_url, 'OIDC discovery URL')
    log.debug('OIDC discovery GET %s', discovery_url)
    with urllib.request.urlopen(discovery_url, timeout=_DISCOVERY_TIMEOUT) as resp:
        result = json.loads(resp.read())
    log.debug('OIDC discovery OK, keys: %s', list(result.keys()))
    return result


def _pkce_pair():
    verifier = secrets.token_urlsafe(64)
    digest = hashlib.sha256(verifier.encode()).digest()
    challenge = base64.urlsafe_b64encode(digest).rstrip(b'=').decode()
    return verifier, challenge


def _is_browser_available():
    if not sys.stdout.isatty():
        return False
    if sys.platform in ('darwin', 'win32', 'cygwin'):
        return True
    return bool(os.environ.get('DISPLAY') or os.environ.get('WAYLAND_DISPLAY'))


def _refresh_tokens(token_endpoint, client_id, refresh_token, client_secret=None):
    payload = {
        'grant_type': 'refresh_token',
        'client_id': client_id,
        'refresh_token': refresh_token,
    }
    if client_secret:
        payload['client_secret'] = client_secret
    data = urllib.parse.urlencode(payload).encode()
    req = urllib.request.Request(token_endpoint, data=data, method='POST')
    req.add_header('Content-Type', 'application/x-www-form-urlencoded')
    log.debug('Token refresh POST %s', token_endpoint)
    with urllib.request.urlopen(req, timeout=_TOKEN_TIMEOUT) as resp:
        result = json.loads(resp.read())
    log.debug('Token refresh response keys: %s', list(result.keys()))
    return result


def get_valid_session(cluster_name):
    """Return a valid session for cluster_name, refreshing the token if expired.

    Returns the session dict or None if no valid session is available.
    """
    session = load_session(cluster_name)
    if not session:
        return None

    expires_at = session.get('expires_at', 0)
    if time.time() < expires_at - 60:
        return session

    refresh_token = session.get('refresh_token')
    token_endpoint = session.get('token_endpoint')
    client_id = session.get('client_id', 'aurora-cli')
    client_secret = None
    try:
        cluster = CLUSTERS[cluster_name]
        client_secret = getattr(cluster, 'oidc_client_secret', None)
    except Exception:
        client_secret = session.get('client_secret')

    if not refresh_token or not token_endpoint:
        return None

    try:
        new_tokens = _refresh_tokens(token_endpoint, client_id, refresh_token, client_secret)
        if 'refresh_token' not in new_tokens:
            new_tokens['refresh_token'] = refresh_token
        _persist_tokens(cluster_name, new_tokens,
                        token_endpoint=token_endpoint, client_id=client_id,
                        client_secret=client_secret)
        return load_session(cluster_name)
    except urllib.error.HTTPError as e:
        if e.code in (401, 403):
            log.warning(
                'Token refresh unauthorized (HTTP %s). '
                'Please re-authenticate with: aurora auth login', e.code)
        else:
            log.warning('Token refresh failed with HTTP %s', e.code)
        return None
    except Exception as e:
        log.warning('Token refresh failed: %s', e)
        return None


def _exchange_code(token_endpoint, client_id, code, redirect_uri, code_verifier, client_secret=None):
    payload = {
        'grant_type': 'authorization_code',
        'client_id': client_id,
        'code': code,
        'redirect_uri': redirect_uri,
        'code_verifier': code_verifier,
    }
    if client_secret:
        payload['client_secret'] = client_secret
    data = urllib.parse.urlencode(payload).encode()
    req = urllib.request.Request(token_endpoint, data=data, method='POST')
    req.add_header('Content-Type', 'application/x-www-form-urlencoded')
    log.debug('Token exchange POST %s', token_endpoint)
    with urllib.request.urlopen(req, timeout=_TOKEN_TIMEOUT) as resp:
        result = json.loads(resp.read())
    log.debug('Token exchange OK')
    return result


def _poll_device_token(token_endpoint, client_id, device_code, interval, expires_in, client_secret=None):
    params = {
        'grant_type': 'urn:ietf:params:oauth:grant-type:device_code',
        'client_id': client_id,
        'device_code': device_code,
    }
    if client_secret:
        params['client_secret'] = client_secret
    deadline = time.time() + expires_in
    wait = interval
    while time.time() < deadline:
        time.sleep(wait)
        log.debug('Device poll POST %s', token_endpoint)
        req = urllib.request.Request(
            token_endpoint,
            data=urllib.parse.urlencode(params).encode(),
            method='POST',
        )
        req.add_header('Content-Type', 'application/x-www-form-urlencoded')
        try:
            with urllib.request.urlopen(req, timeout=_TOKEN_TIMEOUT) as resp:
                return json.loads(resp.read())
        except urllib.error.HTTPError as e:
            try:
                body = json.loads(e.read().decode('utf-8'))
            except (json.JSONDecodeError, UnicodeDecodeError):
                raise RuntimeError(f'Token endpoint returned HTTP {e.code}')
            error = body.get('error', '')
            if error == 'authorization_pending':
                log.debug('Device poll: authorization_pending')
                continue
            elif error == 'slow_down':
                wait = min(wait + 5, 60)
                log.debug('Device poll: slow_down, new interval=%s', wait)
            elif error == 'expired_token':
                raise RuntimeError('Device code expired. Please try again.')
            else:
                raise RuntimeError(f'{error}: {body.get("error_description", "")}')
    raise RuntimeError('Device authorization timed out.')


# ---------------------------------------------------------------------------
# Method 1 — Browser (Authorization Code + PKCE)
# ---------------------------------------------------------------------------

def _browser_auth(discovery, client_id, cluster_name, client_secret=None, scope=None, redirect_port=0):
    authorization_endpoint = discovery['authorization_endpoint']
    token_endpoint = discovery['token_endpoint']
    _validate_https_url(authorization_endpoint, 'authorization_endpoint')
    _validate_https_url(token_endpoint, 'token_endpoint')

    verifier, challenge = _pkce_pair()
    state = secrets.token_urlsafe(32)
    auth_code = [None]
    auth_error = [None]
    state_error = [None]
    stop_event = threading.Event()

    class _CallbackHandler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            params = parse_qs(urlparse(self.path).query)
            returned_state = params.get('state', [None])[0]
            if returned_state != state:
                state_error[0] = 'invalid_state'
                body = (
                    b'<html><body><h2>Authentication failed: invalid state</h2>'
                    b'</body></html>'
                )
                self.send_response(400)
            elif 'code' in params:
                auth_code[0] = params['code'][0]
                body = (
                    b'<html><body><h2>Authentication successful!</h2>'
                    b'<p>You may close this window and return to the terminal.</p>'
                    b'</body></html>'
                )
                self.send_response(200)
            else:
                auth_error[0] = params.get('error', ['unknown'])[0]
                body = f'<html><body><h2>Authentication failed: {auth_error[0]}</h2></body></html>'.encode()
                self.send_response(400)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            stop_event.set()

        def log_message(self, fmt, *args):
            pass

    # Use configured port when provided so operators can pre-register a fixed redirect_uri.
    # Port 0 lets the OS pick a free port (random — most providers will reject it).
    bind_port = int(redirect_port) if redirect_port else 0
    server = socketserver.TCPServer(('127.0.0.1', bind_port), _CallbackHandler, bind_and_activate=False)
    server.allow_reuse_address = True
    try:
        server.server_bind()
        server.server_activate()
    except OSError as e:
        server.server_close()
        if bind_port:
            print(
                f'Failed to bind to port {bind_port}: {e}\n'
                f'Ensure no other process is using port {bind_port}, '
                f'or remove "oidc_redirect_port" from the cluster config to use a random port.'
            )
        else:
            print(f'Failed to start local callback server: {e}')
        return 1
    port = server.socket.getsockname()[1]

    redirect_uri = f'http://localhost:{port}/callback'
    auth_url = '{}?{}'.format(
        authorization_endpoint,
        urllib.parse.urlencode({
            'response_type': 'code',
            'client_id': client_id,
            'redirect_uri': redirect_uri,
            'scope': scope or _DEFAULT_OIDC_SCOPE,
            'code_challenge': challenge,
            'code_challenge_method': 'S256',
            'state': state,
        }),
    )

    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()

    print(f'Opening browser for login on cluster "{cluster_name}"...')
    webbrowser.open(auth_url)
    print('Waiting for authentication (timeout 5 minutes)...')

    timed_out = not stop_event.wait(timeout=_BROWSER_TIMEOUT)
    server.shutdown()

    if timed_out:
        print('Authentication timed out.')
        return 1

    if not auth_code[0]:
        error = state_error[0] or auth_error[0]
        print(f'Authentication failed: {error}')
        return 1

    try:
        tokens = _exchange_code(
            token_endpoint,
            client_id,
            auth_code[0],
            redirect_uri,
            verifier,
            client_secret=client_secret,
        )
    except Exception as e:
        print(f'Token exchange failed: {e}')
        return 1

    _persist_tokens(
        cluster_name,
        tokens,
        token_endpoint=token_endpoint,
        client_id=client_id,
        client_secret=client_secret,
    )
    return 0


# ---------------------------------------------------------------------------
# Method 2 — Browser via Scheduler OAuth2 flow (uses scheduler's registered redirect_uri)
# ---------------------------------------------------------------------------

def _scheduler_browser_auth(scheduler_base_url, cluster_name, redirect_port=0):
    """Browser login via the scheduler's /oauth2/cli-authorize endpoint.

    The scheduler performs the Authorization Code flow using its own registered
    redirect_uri (e.g. https://aurora.example.com/oauth2/callback), then redirects
    the resulting ``aurora_token`` cookie value back to a local callback server.
    This avoids registering a localhost redirect_uri with the OIDC provider.
    """
    bind_port = int(redirect_port) if redirect_port else 0

    aurora_token = [None]
    stop_event = threading.Event()

    class _CliCallbackHandler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            params = parse_qs(urlparse(self.path).query)
            token = params.get('aurora_token', [None])[0]
            if token:
                aurora_token[0] = token
                body = (
                    b'<html><body><h2>Authenticated!</h2>'
                    b'<p>You may close this window and return to the terminal.</p>'
                    b'</body></html>'
                )
                self.send_response(200)
            else:
                body = b'<html><body><h2>Authentication failed.</h2></body></html>'
                self.send_response(400)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            stop_event.set()

        def log_message(self, fmt, *args):
            pass

    server = socketserver.TCPServer(
        ('127.0.0.1', bind_port), _CliCallbackHandler, bind_and_activate=False)
    server.allow_reuse_address = True
    try:
        server.server_bind()
        server.server_activate()
    except OSError as e:
        server.server_close()
        print(f'Failed to bind local callback port: {e}')
        return 1
    port = server.socket.getsockname()[1]

    cli_auth_url = (
        scheduler_base_url.rstrip('/') + f'/oauth2/cli-authorize?local_port={port}'
    )
    log.debug('Scheduler CLI authorize URL: %s', cli_auth_url)

    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()

    print(f'Opening browser for login on cluster "{cluster_name}"...')
    webbrowser.open(cli_auth_url)
    print('Waiting for authentication (timeout 5 minutes)...')

    timed_out = not stop_event.wait(timeout=_BROWSER_TIMEOUT)
    server.shutdown()

    if timed_out:
        print('Authentication timed out.')
        return 1

    if not aurora_token[0]:
        print('Authentication failed: no token received from scheduler.')
        return 1

    session_data = {
        'aurora_token': aurora_token[0],
        'token_type': 'aurora_cookie',
        'cluster': cluster_name,
        'expires_at': int(time.time()) + 28800,
    }
    save_session(cluster_name, session_data)
    print(f'Authenticated. Session saved to {_session_file(cluster_name)}')
    return 0


# ---------------------------------------------------------------------------
# Method 3 — Device Authorization Flow (headless / server)
# ---------------------------------------------------------------------------

def _device_auth(discovery, client_id, cluster_name, client_secret=None, scope=None):
    device_endpoint = discovery.get('device_authorization_endpoint')
    if not device_endpoint:
        print('Error: OIDC provider does not support Device Authorization Flow.')
        print('Please run this command on a machine with a browser.')
        return 1

    token_endpoint = discovery['token_endpoint']
    _validate_https_url(device_endpoint, 'device_authorization_endpoint')
    _validate_https_url(token_endpoint, 'token_endpoint')

    req = urllib.request.Request(
        device_endpoint,
        data=urllib.parse.urlencode({
            'client_id': client_id,
            'scope': scope or _DEFAULT_OIDC_SCOPE,
            **({'client_secret': client_secret} if client_secret else {}),
        }).encode(),
        method='POST',
    )
    req.add_header('Content-Type', 'application/x-www-form-urlencoded')
    try:
        with urllib.request.urlopen(req, timeout=_TOKEN_TIMEOUT) as resp:
            dr = json.loads(resp.read())
    except urllib.error.HTTPError as e:
        body = ''
        try:
            body = e.read().decode('utf-8', errors='replace')
        except Exception:
            body = ''

        details = f'HTTP {e.code}'
        if body:
            try:
                parsed = json.loads(body)
                error = parsed.get('error')
                description = parsed.get('error_description')
                if error and description:
                    details = f'HTTP {e.code}, {error}: {description}'
                elif error:
                    details = f'HTTP {e.code}, {error}'
                else:
                    details = f'HTTP {e.code}, {body}'
            except ValueError:
                details = f'HTTP {e.code}, {body}'

        print('Device authorization request failed.')
        print(f'Endpoint: {device_endpoint}')
        print(f'Client ID: {client_id}')
        print(f'Reason: {details}')
        return 1

    user_code = dr['user_code']
    verification_uri = dr.get('verification_uri_complete') or dr['verification_uri']
    device_code = dr['device_code']
    interval = dr.get('interval', 5)
    expires_in = dr.get('expires_in', 300)

    print()
    print('=' * 62)
    print('  Device Authorization  —  cluster: ' + cluster_name)
    print('=' * 62)
    if dr.get('verification_uri_complete'):
        print(f'  Open this URL in any browser:')
        print(f'  {verification_uri}')
    else:
        print(f'  1. Open:        {verification_uri}')
        print(f'  2. Enter code:  {user_code}')
    print(f'  (expires in {expires_in}s)')
    print('=' * 62)
    print()

    try:
        tokens = _poll_device_token(
            token_endpoint,
            client_id,
            device_code,
            interval,
            expires_in,
            client_secret=client_secret,
        )
    except RuntimeError as e:
        print(f'Authentication failed: {e}')
        return 1

    _persist_tokens(
        cluster_name,
        tokens,
        token_endpoint=token_endpoint,
        client_id=client_id,
        client_secret=client_secret,
    )
    return 0


def _persist_tokens(cluster_name, tokens, token_endpoint=None, client_id=None, client_secret=None):
    if 'access_token' not in tokens:
        raise ValueError('Token response missing access_token')
    tokens['cluster'] = cluster_name
    tokens['expires_at'] = int(time.time()) + tokens.get('expires_in', 3600)
    if token_endpoint:
        tokens['token_endpoint'] = token_endpoint
    if client_id:
        tokens['client_id'] = client_id
    if client_secret:
        tokens['client_secret'] = client_secret
    save_session(cluster_name, tokens)
    print(f'Authenticated. Session saved to {_session_file(cluster_name)}')


# ---------------------------------------------------------------------------
# CLI Nouns / Verbs
# ---------------------------------------------------------------------------

class LoginVerb(Verb):
    @property
    def name(self):
        return 'login'

    @property
    def help(self):
        return (
            'Authenticate with a cluster via OIDC.\n'
            'On Mac/desktop the browser flow (Authorization Code + PKCE) is used.\n'
            'On headless servers the Device Authorization Flow is used automatically.'
        )

    def get_options(self):
        return [
            CommandOption('cluster', type=str, help='Cluster name (from clusters.json)'),
            CommandOption(
                '--device', action='store_true', default=False,
                help='Force Device Authorization Flow regardless of environment',
            ),
        ]

    def execute(self, context):
        cluster_name = context.options.cluster
        if cluster_name not in CLUSTERS:
            context.print_err(f'Unknown cluster: {cluster_name}')
            return 1

        cluster = CLUSTERS[cluster_name]
        oidc_issuer = getattr(cluster, 'oidc_issuer', None)
        client_id = getattr(cluster, 'oidc_client_id', 'aurora-cli')
        client_secret = getattr(cluster, 'oidc_client_secret', None)
        scope = _normalize_oidc_scope(getattr(cluster, 'oidc_scope', None))
        redirect_port = getattr(cluster, 'oidc_redirect_port', 0) or 0
        scheduler_base_url = getattr(cluster, 'scheduler_base_url', None)

        if not oidc_issuer and not scheduler_base_url:
            context.print_err(
                f'Cluster "{cluster_name}" has no oidc_issuer or scheduler_base_url.\n'
                'Add "oidc_issuer" or "scheduler_base_url" to clusters.json.'
            )
            return 1

        use_device = context.options.device or not _is_browser_available()

        if use_device:
            if not oidc_issuer:
                context.print_err(
                    f'Cluster "{cluster_name}" has no oidc_issuer. '
                    'Device flow requires oidc_issuer in clusters.json.'
                )
                return 1
            discovery_url = oidc_issuer.rstrip('/') + '/.well-known/openid-configuration'
            try:
                discovery = _oidc_discovery(discovery_url)
            except Exception as e:
                context.print_err(f'Failed to fetch OIDC discovery document: {e}')
                return 1
            return _device_auth(
                discovery, client_id, cluster_name, client_secret=client_secret, scope=scope)

        # Browser flow: prefer scheduler-based flow (no localhost redirect_uri registration needed).
        if scheduler_base_url:
            return _scheduler_browser_auth(
                scheduler_base_url, cluster_name, redirect_port=redirect_port)

        # Fallback: direct OIDC PKCE browser flow (requires redirect_uri pre-registered).
        if not oidc_issuer:
            context.print_err(
                f'Cluster "{cluster_name}" has no oidc_issuer or scheduler_base_url.\n'
                'Add "scheduler_base_url" or "oidc_issuer" to clusters.json.'
            )
            return 1
        discovery_url = oidc_issuer.rstrip('/') + '/.well-known/openid-configuration'
        try:
            discovery = _oidc_discovery(discovery_url)
        except Exception as e:
            context.print_err(f'Failed to fetch OIDC discovery document: {e}')
            return 1
        return _browser_auth(
            discovery, client_id, cluster_name,
            client_secret=client_secret, scope=scope, redirect_port=redirect_port)


class Auth(Noun):
    @classmethod
    def create_context(cls):
        return AuroraCommandContext()

    @property
    def name(self):
        return 'auth'

    @property
    def help(self):
        return 'Authentication commands (OIDC login, session management)'

    def __init__(self):
        super(Auth, self).__init__()
        self.register_verb(LoginVerb())
