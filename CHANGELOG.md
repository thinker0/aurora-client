# Changelog

All notable changes to this project will be documented in this file.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

---

## [Unreleased] — 2026-03-16

### Security
- **Command injection fix** (`admin/admin_util.py`): validate hostnames with `_HOSTNAME_RE`
  regex before passing to `subprocess.Popen`; invalid hostnames cause `die()` with a clear error.
- **SSH injection fix** (`client/api/command_runner.py`): validate `hostname` and `role`
  with `_SSH_SAFE` regex before constructing the SSH command; invalid values are skipped with
  an error log instead of being passed to the shell.

### Fixed
- Narrowed 4× bare `except Exception:` in `executor/aurora_executor.py` to specific types
  (`AttributeError`, `RuntimeError`, `ValueError`, `TypeError`) to prevent masking
  programming errors.
- Narrowed `except Exception:` in `common/kazoo_compat.py` to `except ImportError:`
  (correct scope for optional `kazoo.recipe` import).
- `client/hooks/hooked_api.py`: include exception type and message in hook error log for
  faster debugging.

### Added
- **Thermos OIDC Bearer auth** (`thermos/observer/http/http_observer.py`):
  - `OidcBearerAuth` plugin: validates `Authorization: Bearer <token>` via OIDC `/userinfo`
    endpoint with a 5-minute `ExpiringDict` cache.
  - `CombinedAuth` plugin: tries OIDC Bearer first, falls back to HTTP Basic Auth.
  - `AuthenticateEverything` now supports three modes:
    `'basic'` (existing), `'oidc'`, `'oidc+basic'`.
- **Auth debug logging**: `log.debug()` calls added to all OIDC HTTP requests in
  `client/cli/auth.py` and `common/auth/auth_module.py` — visible with `--verbose`.

---

## [0.24.0-dev] — 2026-03-15

### Added
- **OIDC authentication** (`client/cli/auth.py`):
  - Browser flow: Authorization Code + PKCE via local callback server (macOS/desktop).
  - Device Authorization Flow: headless / server environments (`--device` flag).
  - Automatic token refresh on expiry using stored `refresh_token`.
  - Sessions stored securely in `~/.aurora/session.<cluster>` (mode 0600).
- **OIDC-aware auth modules** (`common/auth/auth_module.py`):
  - `OidcDeviceAuth`: Bearer token auth with auto-refresh via OIDC token endpoint.
  - `SessionTokenAuth`: reads Bearer token from `~/.aurora/token.<cluster>`.
  - `ProxySessionAuth`: injects OAuth2-Proxy cookies from `~/.aurora/session.<cluster>`.
- **Cluster-specific sessions**: all auth modules support per-cluster session files.
- Migrated all `print(..., file=sys.stderr)` diagnostic calls to `twitter.common.log`
  in `auth_module.py`; interactive device-flow output kept as `print()`.

### Fixed
- `auth.py` security hardening:
  - HTTPS-only validation for all OIDC endpoint URLs.
  - TOCTOU race condition in session file loading replaced with `try/except FileNotFoundError`.
  - Removed `MD5` → replaced with `SHA-256` throughout.
  - Bearer token loaded without blocking the main thread.
  - `abstractproperty` replaced with `@property @abstractmethod`.
- `refresh_token` auto-renewal: silently re-uses previous `refresh_token` when new one
  is not returned; `slow_down` polling interval capped at 60 s.
- Removed `gen` stub import from `conftest.py` that caused `pants test ::` failures.

---

## [0.23.x] — 2026-03-08 to 2026-03-14

### Added
- `lastSeenMs` field added to `HostAttributes`; support for removing host attributes.
- Thrift `_wrapper_codegen.py` synced with upstream Aurora changes.

### Fixed
- **Thermos Observer**: removed duplicate `Date` header; fixed incorrect `HTTPResponse`
  usage causing 500 errors.
- **ZooKeeper / Kazoo**:
  - `ServerSet` join failure fixed — ZooKeeper value encoded as `bytes` for Python 3.
  - `KazooClient` patched at all instantiation paths for Python 3 compatibility.
  - Native `zookeeper` module (`zkpython`) patched for Python 3 string/bytes semantics.
  - Early `kazoo` patching in `thermos_executor` to avoid ctypes errors.
- **Python 3 I/O**: `RecordIO` and Shell Health Check I/O compatibility fixed.
- RPM build: disabled jar repacking and post-install scripts to reduce build time.

### Build
- JDK upgraded 11 → 17; Gradle upgraded to 8.9.

---

## [0.23.3] — 2026-03-01 to 2026-03-03

### Fixed
- `sla_host_drain`: `duration`/`timeout` cast to `int` to fix `struct.error`.
- `urllib3` downgraded 2.2.3 → 1.26.20 for CentOS 7 compatibility.
- Security vulnerabilities in Python dependencies resolved.
- CPython wheel build scripts fixed for Apple Silicon (arm64).
- Rocky 8 / Rocky 9 build environment variables aligned.
- `lock.txt` hash mismatches resolved; `--sync-lock` flag added to `build_wheels.py`.
- `/wheels` mounted read-only in all builder containers to prevent hash corruption.
- Java preference updated to Java 11 over Java 1.8 in startup scripts.

### Build
- PEX artifact names standardized; build robustness improved.
- Legacy GitHub Actions workflow removed.

---

## [0.23.0] — 2026-02-14 to 2026-02-21

### Added
- Self-extracting installer (`build-installer.sh`) that embeds `aurora.pex` +
  `aurora_admin.pex` into a single shell script.
- Builder images for CentOS 7 and Rocky 8/9 with CPython wheel build pipelines.
- Custom BUILD helpers (`globs`, `rglobs`, `zglobs`) for Pants v2 compatibility.
- Vendored `twitter.common` components; Kazoo compatibility shim
  (`common/kazoo_compat.py`) for `aurora_admin` with `kazoo==2.10.0`.
- Python 2/3 compatibility shims (`StringIO`, `cStringIO`, `urlparse`, etc.).

### Changed
- **Migrated build system**: Pants v1 → Pants v2.17.1 (`pants.ini` → `pants.toml`).
- Python standardized on CPython 3.9.
- `pants` wrapper now sets `PANTS_PYTHON_REPOS_FIND_LINKS` dynamically from CWD,
  removing hardcoded paths.
- `python-bootstrap.search_path` made flexible for macOS / Homebrew / Apple Silicon.
- Local-only helper scripts removed from version control (added to `.gitignore`).

### Fixed
- Thrift structs made hashable for Python 3 via `_to_hashable` + `_thrift_struct_hash`.

---

[Unreleased]: https://github.com/your-org/aurora-client/compare/v0.23.3...HEAD
[0.24.0-dev]: https://github.com/your-org/aurora-client/compare/v0.23.3...HEAD
[0.23.3]: https://github.com/your-org/aurora-client/compare/v0.23.0...v0.23.3
[0.23.0]: https://github.com/your-org/aurora-client/releases/tag/v0.23.0
