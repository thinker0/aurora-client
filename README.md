# Aurora Client

Python 3 client for the [Apache Aurora](https://aurora.apache.org/) scheduler.
Migrated from Python 2, fully compatible with CPython 3.9+ on Linux (CentOS 7, Rocky 8/9) and macOS.

## Features

- Full Aurora CLI (`aurora`) and admin CLI (`aurora_admin`)
- OIDC authentication (Authorization Code + PKCE, Device Authorization Flow)
- HTTP Basic Auth via Redis-backed credential store
- Session token and OAuth2-Proxy session support
- Thermos HTTP Observer with pluggable auth (OIDC / Basic / combined)
- ZooKeeper compatibility via Kazoo 2.10 shim

---

## Quick Start

### Prerequisites

- Python 3.9+
- [Pants v2.17](https://www.pantsbuild.org/)
- Local wheel files (see [Local Setup](#local-setup))

### Local Setup (`~/.pants.rc`)

Pants uses local wheel files instead of PyPI. Create `~/.pants.rc`:

```ini
[python-repos]
find_links = ["file:///path/to/your/wheels"]
path_mappings = ["AURORA_WHEELS_DIR|/path/to/your/wheels"]
```

The wheels directory must contain the `.whl` files listed in `3rdparty/python/requirements.txt`.
On macOS the `3rdparty/python/wheels` symlink points to the right location.

Alternatively, use the wrapper which sets `find_links` dynamically:

```bash
./run-pants-local-wheels.sh test ::
```

---

## Building

### Aurora CLI

```bash
pants package src/main/python/apache/aurora/kerberos:kaurora
```

### Admin CLI

```bash
pants package src/main/python/apache/aurora/kerberos:kaurora_admin
```

### Thermos Observer

```bash
pants package src/main/python/apache/aurora/tools:thermos_observer
```

### Self-Extracting Installer (macOS)

```bash
./build-installer.sh
```

Produces `aurora-client-<version>-darwin.sh` that installs `aurora` and `aurora_admin` into `~/bin`.

### Python Source Distributions

```bash
./build-support/release/make-python-sdists
```

---

## Running Tests

```bash
pants test ::
```

To force local wheels:

```bash
./run-pants-local-wheels.sh test ::
```

---

## Authentication

Aurora Client supports multiple authentication mechanisms, configured per-cluster in `clusters.json`.

### OIDC Login (recommended)

```bash
# Browser flow (macOS / desktop) — Authorization Code + PKCE
aurora auth login <cluster>

# Device Authorization Flow (headless / server)
aurora auth login --device <cluster>
```

Sessions are stored in `~/.aurora/session.<cluster>` (mode 0600).
Tokens are automatically refreshed on expiry using the stored `refresh_token`.

---

### `clusters.json` OIDC Configuration Reference

| Key | Required | Default | Description |
|-----|----------|---------|-------------|
| `auth_mechanism` | No | `SESSION_TOKEN` | Auth module used by the CLI for scheduler API calls. See [Auth Mechanisms](#auth-mechanisms). |
| `oidc_issuer` | Yes (OIDC) | — | OIDC provider base URL. Used to fetch `/.well-known/openid-configuration`. Trailing slash is stripped automatically. |
| `oidc_client_id` | No | `aurora-cli` | OAuth2 client ID registered in the OIDC provider. |
| `oidc_client_secret` | No | — | OAuth2 client secret for **confidential clients**. Forwarded in token exchange, refresh, and device flow requests. |
| `oidc_scope` | No | `openid email profile` | Space-separated scope string, or a JSON array. |
| `oidc_redirect_port` | No | `0` (random) | Fixed TCP port for the browser-flow local callback server. Must match the `redirect_uri` registered in the OIDC client (e.g. `http://localhost:8850/callback`). Use `0` to let the OS assign a free port — **most OIDC providers will reject a random port** because the redirect URI is not pre-registered. |
| `scheduler_base_url` | No | — | Base URL of the Aurora Scheduler HTTP endpoint (e.g. `https://aurora.example.com`). When set, the CLI uses the scheduler as an OIDC proxy for browser and device flows. `oidc_client_secret` is **not** required on the client — it is kept server-side. |

#### Minimal public client (no secret)

```json
{
  "lad-beta": {
    "name": "lad-beta",
    "zk": "zk01.example.com:2181",
    "scheduler_zk_path": "/aurora/scheduler",
    "auth_mechanism": "SESSION_TOKEN",
    "oidc_issuer": "https://auth.example.com",
    "oidc_client_id": "aurora-cli"
  }
}
```

Login:
```bash
aurora auth login lad-beta          # browser flow (macOS)
aurora auth login lad-beta --device # device flow (server / headless)
```

#### Confidential client (with secret)

Required when the OIDC provider is configured as a **confidential client** (client secret
is needed for token exchange and refresh).

```json
{
  "lad-beta": {
    "name": "lad-beta",
    "zk": "zk01.example.com:2181",
    "scheduler_zk_path": "/aurora/scheduler",
    "auth_mechanism": "SESSION_TOKEN",
    "oidc_issuer": "https://auth.example.com",
    "oidc_client_id": "aurora-cli",
    "oidc_client_secret": "YOUR_CLIENT_SECRET"
  }
}
```

#### Browser flow with fixed redirect port

Most OIDC providers require the `redirect_uri` to be **exactly pre-registered**. Without
a fixed port, a random port is used on every invocation and the provider will reject the
callback with `redirect_uri_mismatch`.

Steps:
1. Register `http://localhost:8850/callback` in your OIDC client settings.
2. Add `oidc_redirect_port` to the cluster config:

```json
{
  "lad-beta": {
    "name": "lad-beta",
    "zk": "zk01.example.com:2181",
    "scheduler_zk_path": "/aurora/scheduler",
    "auth_mechanism": "SESSION_TOKEN",
    "oidc_issuer": "https://auth.example.com",
    "oidc_client_id": "aurora-cli",
    "oidc_redirect_port": 8850
  }
}
```

Then use the browser flow:
```bash
aurora auth login lad-beta
# → opens http://localhost:8850/callback (registered URI)
```

#### Custom scope

```json
{
  "lad-beta": {
    "oidc_scope": "openid email groups"
  }
}
```

Or as a JSON array:
```json
{
  "lad-beta": {
    "oidc_scope": ["openid", "email", "groups"]
  }
}
```

---

### Scheduler Proxy Auth Flow

When `scheduler_base_url` is set in `clusters.json`, the Aurora Scheduler acts as an OIDC
proxy on behalf of the CLI. The `oidc_client_secret` stays server-side and is never required
in the client config.

#### Browser flow (scheduler proxy)

The CLI opens `<scheduler_base_url>/oauth2/cli-authorize?local_port=PORT` in the browser.
The scheduler performs the OIDC Authorization Code Flow and redirects the resulting
`aurora_token` cookie to the localhost callback. The session file stores
`{aurora_token, token_type: "aurora_cookie"}`.

#### Device flow (scheduler proxy)

The CLI POSTs to `/oauth2/device-authorize` (scheduler returns a `proxy_device_code`),
then polls `/oauth2/device-token` until the user approves. The scheduler proxies the full
OIDC device flow and returns the `aurora_token`. No `oidc_client_secret` needed on the client.

#### Minimal scheduler-proxy config

```json
{
  "lad-prod": {
    "name": "lad-prod",
    "zk": "zk01.example.com:2181",
    "scheduler_zk_path": "/aurora/scheduler",
    "auth_mechanism": "SESSION_TOKEN",
    "scheduler_base_url": "https://aurora.example.com",
    "oidc_issuer": "https://sso.example.com",
    "oidc_client_id": "aurora-cli"
  }
}
```

> `oidc_issuer` and `oidc_client_id` are still listed here for documentation purposes and
> for the direct-OIDC fallback path (when `scheduler_base_url` is absent). They are not
> sent to the scheduler in the proxy flow.

---

### Auth Mechanisms

The `auth_mechanism` key controls how `aurora` injects credentials into Thrift API calls.
Default is `SESSION_TOKEN` — no configuration needed after `aurora auth login`.

| Value | Description |
|-------|-------------|
| `SESSION_TOKEN` | **(Default)** Reads `~/.aurora/session.<cluster>` and injects credentials into Thrift API calls. When `token_type` is `"bearer"` (direct OIDC flow), sends `Authorization: Bearer <access_token>` and auto-refreshes on expiry. When `token_type` is `"aurora_cookie"` (scheduler proxy flow), sends `Cookie: aurora_token=<jwt>` instead. Falls back to `~/.aurora/token.<cluster>` (legacy plain token). No-ops silently if no token file exists (backward-compatible with unauthenticated clusters). |
| `OIDC_DEVICE` | Same Bearer injection as `SESSION_TOKEN`, plus an embedded device-flow fallback via `AURORA_OIDC_ISSUER` / `AURORA_OIDC_CLIENT_ID` environment variables. |
| `BASIC` | HTTP Basic Auth via `~/.netrc` or explicit username/password. |
| `PROXY_SESSION` | Injects OAuth2-Proxy session cookie from `~/.aurora/session.<cluster>`. |
| `UNAUTHENTICATED` | No auth headers — for clusters without authentication. |

### HTTP Basic Auth

Credentials are stored in Redis as `sha256:<hash(user:password)>` under the key prefix
`/aurora/thermos/user/<username>`.

```json
{
  "mycluster": {
    "auth_mechanism": "BASIC"
  }
}
```

### Session Token (legacy)

`SESSION_TOKEN` (now the default) supports both legacy token files and OIDC session files:

- OIDC session JSON (written by `aurora auth login`): `~/.aurora/session.<cluster>`
- Legacy plain token: `~/.aurora/token.<cluster>` (or `~/.aurora/token`)

When a session JSON is present and expired, the client automatically refreshes it using
`refresh_token` and `token_endpoint` stored in the session file.

```json
{
  "auth_mechanism": "SESSION_TOKEN"
}
```

### OAuth2-Proxy Session (cookie-based)

Place the proxy session cookie in `~/.aurora/session.<cluster>`:

```json
{
  "auth_mechanism": "PROXY_SESSION"
}
```

---

## Thermos Observer Authentication

The Thermos HTTP Observer (`http_observer.py`) supports three authentication modes
via the `--enable-authentication` option:

| Mode | Description |
|------|-------------|
| `basic` | HTTP Basic Auth only (Redis-backed SHA-256, backward compatible) |
| `oidc` | OIDC Bearer token only (validates via `/userinfo` endpoint) |
| `oidc+basic` | OIDC Bearer preferred; falls back to Basic Auth |

### Standard OIDC provider (Keycloak, Okta, etc.)

OIDC discovery (`/.well-known/openid-configuration`) is used to locate the
`userinfo_endpoint` automatically:

```
--enable-authentication=oidc+basic
--oidc-issuer=https://auth.example.com
--redis-cluster=redis://redis-host:7000
--redis-key-prefix=/aurora/thermos/user/
```

### oauth2-proxy

oauth2-proxy does not expose a discovery document. Use `--oidc-userinfo-url`
to point directly at its `/oauth2/userinfo` endpoint, bypassing discovery:

```
--enable-authentication=oidc+basic
--oidc-userinfo-url=https://oauth2proxy.example.com/oauth2/userinfo
--redis-cluster=redis://redis-host:7000
--redis-key-prefix=/aurora/thermos/user/
```

> When `--oidc-userinfo-url` is set, `--oidc-issuer` is not required and
> `GET /.well-known/openid-configuration` is never called.
> For local development, `http://localhost` and loopback URLs are allowed.
> In remote environments, use HTTPS endpoints.

### Auth flow

```
aurora auth login <cluster>
  ├─ browser flow (no scheduler_base_url)  → Authorization Code + PKCE → ~/.aurora/session.<cluster>
  ├─ browser flow (scheduler_base_url set) → GET /oauth2/cli-authorize → aurora_token cookie → ~/.aurora/session.<cluster>
  ├─ --device flag (no scheduler_base_url) → Direct OIDC Device Flow → ~/.aurora/session.<cluster>
  └─ --device flag (scheduler_base_url set)→ POST /oauth2/device-authorize → aurora_token → ~/.aurora/session.<cluster>
         ↓
aurora job list / create / ...
  └─ SESSION_TOKEN (default auth_mechanism)
       ├─ token_type=bearer       → Authorization: Bearer <access_token>  (auto-refresh on expiry)
       └─ token_type=aurora_cookie→ Cookie: aurora_token=<jwt>
         ↓
ThermosProxyServlet (Jetty)          → forwards Authorization header
         ↓
OidcBearerAuth / CombinedAuth        → GET /userinfo → 200 OK → allow
                                                      → non-200 → 401
```

Token validation results are cached for 5 minutes to avoid repeated calls to the OIDC provider.

### Debug logging

Run the observer with `--verbose` (or `-v`) to set the log level to DEBUG and enable
detailed output for all authentication steps: Redis key lookups, cache hit/miss,
token validation requests, HTTP response codes, and per-request auth decisions.

```
thermos_observer --verbose --enable-authentication=oidc+basic ...
```

---

## Kazoo Compatibility

The admin client uses `kazoo==2.10.0` while the legacy `twitter.common.zookeeper`
expects older recipe APIs. A compatibility shim is applied at startup:

- Shim: `src/main/python/apache/aurora/common/kazoo_compat.py`
- Applied in: `src/main/python/apache/aurora/admin/aurora_admin.py`
- Forked package: `src/main/python/twitter/common/zookeeper`

To build the forked ZooKeeper wheel:

```bash
pants package src/main/python/twitter/common/zookeeper:zookeeper_dist
```

---

## Platform Support

| Platform | CPython | Build script |
|----------|---------|--------------|
| macOS (arm64 / x86_64) | 3.9 | `build-artifact.sh` |
| CentOS 7 | 3.8 | `build-centos7-cpython38-wheels.sh` |
| Rocky Linux 8 | 3.9 | `build-rocky8-cpython-wheels.sh` |
| Rocky Linux 9 | 3.9 | `build-rocky9-cpython-wheels.sh` |

---

## License

Apache License 2.0 — see [LICENSE](LICENSE).
