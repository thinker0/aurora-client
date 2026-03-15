
import http.server
import os
import socketserver
import threading
import webbrowser
from urllib.parse import urlparse, parse_qs

from apache.aurora.client.cli import Noun, Verb, Context
from apache.aurora.client.cli.options import CommandOption

class LoginVerb(Verb):
  @property
  def name(self):
    return 'login'

  @property
  def help(self):
    return 'Authenticate with the cluster via OAuth2-Proxy or OIDC'

  def get_options(self):
    return [
      CommandOption('cluster', type=str, help='Cluster to authenticate with')
    ]

  def execute(self, context):
    cluster_name = context.options.cluster
    cluster = context.get_cluster(cluster_name)
    scheduler_uri = cluster.scheduler_uri
    mechanism = getattr(cluster, 'auth_mechanism', 'PROXY_SESSION')

    if mechanism == 'OIDC_DEVICE':
      from apache.aurora.common.auth.auth_module import OidcDeviceAuth
      auth = OidcDeviceAuth(token_file=os.path.expanduser(f'~/.aurora/token.{cluster_name}'))
      if hasattr(cluster, 'oidc_issuer'): auth._issuer = cluster.oidc_issuer
      if hasattr(cluster, 'oidc_client_id'): auth._client_id = cluster.oidc_client_id
      
      
      token_file = os.path.expanduser(f'~/.aurora/token.{cluster_name}')
      if auth.authenticate_via_device_flow():
        if os.path.exists(auth._token_file):
          os.chmod(auth._token_file, 0o600)
        print(f'Successfully authenticated with OIDC for {cluster_name}')

        return 0
      return 1

    captured_cookie = None
    stop_event = threading.Event()

    class RedirectHandler(http.server.BaseHTTPRequestHandler):
      def do_GET(self):
        nonlocal captured_cookie
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(b'<html><body><h1>Authentication Successful</h1><p>You can close this window now.</p></body></html>')
        cookie_header = self.headers.get('Cookie')
        if cookie_header:
          captured_cookie = cookie_header
        stop_event.set()
      def log_message(self, format, *args): pass

    port = 12345
    try:
      server = socketserver.TCPServer(('127.0.0.1', port), RedirectHandler)
    except OSError:
      port = 12346
      server = socketserver.TCPServer(('127.0.0.1', port), RedirectHandler)

    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()

    login_url = f'{scheduler_uri}/oauth2/start?rd=http://localhost:{port}/'
    print(f'Opening browser for login: {login_url}')
    webbrowser.open(login_url)

    print('Waiting for authentication results (timeout 5m)...')
    if stop_event.wait(timeout=300):
      
      session_file = os.path.expanduser(f'~/.aurora/session.{cluster_name}')
      with open(session_file, 'w') as f:
        f.write(captured_cookie)
      os.chmod(session_file, 0o600) # Secure file permissions
      print(f'Successfully authenticated and saved session to {session_file}')

      server.shutdown()
      return 0
    else:
      print('Failed to capture authentication cookie (timeout).')
      server.shutdown()
      return 1

class Auth(Noun):
  @property
  def name(self):
    return 'auth'

  @property
  def help(self):
    return 'Authentication related commands'

  def __init__(self):
    super(Auth, self).__init__()
    self.register_verb(LoginVerb())
