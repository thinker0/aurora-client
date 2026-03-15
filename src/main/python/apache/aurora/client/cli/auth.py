
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

from apache.aurora.client.cli import Noun, Verb
from apache.aurora.client.cli.context import AuroraCommandContext
from apache.aurora.client.cli.options import CommandOption
from apache.aurora.common.clusters import CLUSTERS


SESSION_DIR = os.path.expanduser('~/.aurora')

_DISCOVERY_TIMEOUT = 10
_TOKEN_TIMEOUT = 15
_BROWSER_TIMEOUT = 300


def _session_file(cluster_name):
    return os.path.join(SESSION_DIR, f'session.{cluster_name}')


def save_session(cluster_name, data):
    os.makedirs(SESSION_DIR, mode=0o700, exist_ok=True)
    path = _session_file(cluster_name)
    with open(path, 'w') as f:
        json.dump(data, f)
    os.chmod(path, 0o600)


def load_session(cluster_name):
    path = _session_file(cluster_name)
    if not os.path.exists(path):
        return None
    with open(path) as f:
        return json.load(f)


def _oidc_discovery(discovery_url):
    with urllib.request.urlopen(discovery_url, timeout=_DISCOVERY_TIMEOUT) as resp:
        return json.loads(resp.read())


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


def _refresh_tokens(token_endpoint, client_id, refresh_token):
    data = urllib.parse.urlencode({
        'grant_type': 'refresh_token',
        'client_id': client_id,
        'refresh_token': refresh_token,
    }).encode()
    req = urllib.request.Request(token_endpoint, data=data, method='POST')
    req.add_header('Content-Type', 'application/x-www-form-urlencoded')
    with urllib.request.urlopen(req, timeout=_TOKEN_TIMEOUT) as resp:
        return json.loads(resp.read())


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

    if not refresh_token or not token_endpoint:
        return None

    try:
        new_tokens = _refresh_tokens(token_endpoint, client_id, refresh_token)
        if 'refresh_token' not in new_tokens:
            new_tokens['refresh_token'] = refresh_token
        _persist_tokens(cluster_name, new_tokens,
                        token_endpoint=token_endpoint, client_id=client_id)
        return load_session(cluster_name)
    except Exception as e:
        print(f'Warning: Token refresh failed: {e}', file=sys.stderr)
        return None


def _exchange_code(token_endpoint, client_id, code, redirect_uri, code_verifier):
    data = urllib.parse.urlencode({
        'grant_type': 'authorization_code',
        'client_id': client_id,
        'code': code,
        'redirect_uri': redirect_uri,
        'code_verifier': code_verifier,
    }).encode()
    req = urllib.request.Request(token_endpoint, data=data, method='POST')
    req.add_header('Content-Type', 'application/x-www-form-urlencoded')
    with urllib.request.urlopen(req, timeout=_TOKEN_TIMEOUT) as resp:
        return json.loads(resp.read())


def _poll_device_token(token_endpoint, client_id, device_code, interval, expires_in):
    params = {
        'grant_type': 'urn:ietf:params:oauth:grant-type:device_code',
        'client_id': client_id,
        'device_code': device_code,
    }
    deadline = time.time() + expires_in
    wait = interval
    while time.time() < deadline:
        time.sleep(wait)
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
                continue
            elif error == 'slow_down':
                wait = min(wait + 5, 60)
            elif error == 'expired_token':
                raise RuntimeError('Device code expired. Please try again.')
            else:
                raise RuntimeError(f'{error}: {body.get("error_description", "")}')
    raise RuntimeError('Device authorization timed out.')


# ---------------------------------------------------------------------------
# Method 1 — Browser (Authorization Code + PKCE)
# ---------------------------------------------------------------------------

def _browser_auth(discovery, client_id, cluster_name):
    authorization_endpoint = discovery['authorization_endpoint']
    token_endpoint = discovery['token_endpoint']

    verifier, challenge = _pkce_pair()
    auth_code = [None]
    auth_error = [None]
    stop_event = threading.Event()

    class _CallbackHandler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            params = parse_qs(urlparse(self.path).query)
            if 'code' in params:
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

    # Bind to port 0 atomically to avoid TOCTOU race between _free_port() and server start
    server = socketserver.TCPServer(('127.0.0.1', 0), _CallbackHandler, bind_and_activate=False)
    server.allow_reuse_address = True
    server.server_bind()
    server.server_activate()
    port = server.socket.getsockname()[1]

    redirect_uri = f'http://localhost:{port}/callback'
    auth_url = '{}?{}'.format(
        authorization_endpoint,
        urllib.parse.urlencode({
            'response_type': 'code',
            'client_id': client_id,
            'redirect_uri': redirect_uri,
            'scope': 'openid email profile offline_access',
            'code_challenge': challenge,
            'code_challenge_method': 'S256',
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
        print(f'Authentication failed: {auth_error[0]}')
        return 1

    try:
        tokens = _exchange_code(token_endpoint, client_id, auth_code[0], redirect_uri, verifier)
    except Exception as e:
        print(f'Token exchange failed: {e}')
        return 1

    _persist_tokens(cluster_name, tokens, token_endpoint=token_endpoint, client_id=client_id)
    return 0


# ---------------------------------------------------------------------------
# Method 2 — Device Authorization Flow (headless / server)
# ---------------------------------------------------------------------------

def _device_auth(discovery, client_id, cluster_name):
    device_endpoint = discovery.get('device_authorization_endpoint')
    if not device_endpoint:
        print('Error: OIDC provider does not support Device Authorization Flow.')
        print('Please run this command on a machine with a browser.')
        return 1

    token_endpoint = discovery['token_endpoint']

    req = urllib.request.Request(
        device_endpoint,
        data=urllib.parse.urlencode({
            'client_id': client_id,
            'scope': 'openid email profile offline_access',
        }).encode(),
        method='POST',
    )
    req.add_header('Content-Type', 'application/x-www-form-urlencoded')
    with urllib.request.urlopen(req, timeout=_TOKEN_TIMEOUT) as resp:
        dr = json.loads(resp.read())

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
        tokens = _poll_device_token(token_endpoint, client_id, device_code, interval, expires_in)
    except RuntimeError as e:
        print(f'Authentication failed: {e}')
        return 1

    _persist_tokens(cluster_name, tokens, token_endpoint=token_endpoint, client_id=client_id)
    return 0


def _persist_tokens(cluster_name, tokens, token_endpoint=None, client_id=None):
    if 'access_token' not in tokens:
        raise ValueError('Token response missing access_token')
    tokens['cluster'] = cluster_name
    tokens['expires_at'] = int(time.time()) + tokens.get('expires_in', 3600)
    if token_endpoint:
        tokens['token_endpoint'] = token_endpoint
    if client_id:
        tokens['client_id'] = client_id
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

        if not oidc_issuer:
            context.print_err(
                f'Cluster "{cluster_name}" has no oidc_issuer.\n'
                'Add "oidc_issuer" (and optionally "oidc_client_id") to clusters.json.'
            )
            return 1

        discovery_url = oidc_issuer.rstrip('/') + '/.well-known/openid-configuration'

        try:
            discovery = _oidc_discovery(discovery_url)
        except Exception as e:
            context.print_err(f'Failed to fetch OIDC discovery document: {e}')
            return 1

        use_device = context.options.device or not _is_browser_available()

        if use_device:
            return _device_auth(discovery, client_id, cluster_name)
        else:
            return _browser_auth(discovery, client_id, cluster_name)


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
