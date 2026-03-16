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
# Browser flow (macOS / desktop)
aurora auth login <cluster>

# Device Authorization Flow (headless / server)
aurora auth login --device <cluster>
```

Sessions are stored in `~/.aurora/session.<cluster>`.
Tokens are automatically refreshed on expiry.

**`clusters.json` example:**

```json
{
  "mycluster": {
    "name": "mycluster",
    "zk": "zk-host:2181",
    "scheduler_zk_path": "/aurora/scheduler",
    "auth_mechanism": "OIDC_DEVICE",
    "oidc_issuer": "https://auth.example.com",
    "oidc_client_id": "aurora-cli"
  }
}
```

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

### Session Token

`SESSION_TOKEN` supports both legacy token files and OIDC session files:

- Legacy plain token: `~/.aurora/token.<cluster>` (or `~/.aurora/token`)
- OIDC session JSON: `~/.aurora/session.<cluster>`

When a session JSON is present and expired, the client automatically refreshes it using
`refresh_token` and `token_endpoint`.

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
aurora auth login <cluster>          → stores OIDC access_token
    ↓
SessionTokenAuth                     → Authorization: Bearer <token>
    ↓
ThermosProxyServlet                  → forwards Authorization header (Jetty default)
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
