# Redis Integration: GCP IAM Authentication — Design Spec

**Date:** 2026-04-06
**Jira:** [FRAGENT-3519](https://datadoghq.atlassian.net/browse/FRAGENT-3519)
**Related:** FRAGENT-3397, FRAGENT-3522, FRAGENT-3524, FRAGENT-3525, FRAGENT-3544

## Problem

The Datadog Redis/Valkey integration only supports static username/password authentication. Multiple customers (Anthropic, and others) running Redis or Valkey on **GCP Memorystore** require IAM-based authentication, which uses short-lived OAuth2 tokens rather than static passwords. Without this, they cannot monitor their clusters at all.

A parallel request exists for AWS ElastiCache IAM (FRAGENT-3477), making multi-cloud extensibility a design requirement.

## Goals

- Support GCP IAM authentication for the `redisdb` integration (covers both Redis and Valkey on GCP Memorystore)
- Design the implementation to make AWS ElastiCache IAM straightforward to add later without reworking existing code
- Do not break existing password-based authentication

## Non-Goals

- AWS ElastiCache IAM support (follow-up work)
- Azure AD authentication
- Enforcing TLS (user responsibility; we warn but do not block)

## Design

### Architecture

Three units of change:

1. **`gcp.py`** (new) — `GCPIAMTokenProvider`: owns token generation, caching, and expiry
2. **`redisdb.py`** (modified) — `__init__` instantiates the provider; `_get_conn` injects credentials and handles eviction
3. **`spec.yaml`** (modified) — adds the `gcp` configuration block

### Configuration Schema

New top-level `gcp` instance option, consistent with the `aws` pattern used in the mysql/postgres integrations:

```yaml
# redisdb.d/conf.yaml

host: my-redis.memorystore.googleapis.com
port: 6380
ssl: true
gcp:
  managed_authentication:
    enabled: true
    service_account: datadog@my-project.iam.gserviceaccount.com  # optional
```

- `enabled` (bool, required): activates IAM auth mode
- `service_account` (string, optional): service account email to impersonate for token generation. If omitted, Application Default Credentials (ADC) are used — covers GKE Workload Identity, `GOOGLE_APPLICATION_CREDENTIALS`, and other ADC-compatible environments. The service account is **not** used as the Redis AUTH username (see below).
- `username` and `password` must **not** be set alongside `gcp.managed_authentication.enabled: true` — the integration raises `ConfigurationError` if either is present

### AUTH Username

GCP Memorystore (Redis Cluster and Valkey) requires **`"default"` as the Redis AUTH username** for IAM auth. The service account email is only used to generate the IAM access token — it is never passed to Redis as the username. Confirmed against Google's official docs for both Memorystore Cluster and Memorystore for Valkey:

> *"'default' is the only supported username."*
> — [Manage IAM auth, Memorystore Cluster](https://cloud.google.com/memorystore/docs/cluster/manage-iam-auth)
> — [Manage IAM auth, Memorystore for Valkey](https://cloud.google.com/memorystore/docs/valkey/manage-iam-auth)

`GCPIAMTokenProvider.username` therefore always returns `"default"`.

### `GCPIAMTokenProvider`

```python
# redisdb/datadog_checks/redisdb/gcp.py

GCP_SCOPE = "https://www.googleapis.com/auth/cloud-platform"
TOKEN_TTL = 55 * 60  # 55 minutes; GCP tokens expire at 60

class GCPIAMTokenProvider:
    def __init__(self, service_account: str | None = None): ...
    @property
    def username(self) -> str: ...   # always returns "default" for Memorystore
    def get_token(self) -> str: ...  # returns cached or refreshed OAuth2 access token
    def is_token_expired(self) -> bool: ...
    def invalidate(self) -> None: ...  # forces refresh on next get_token() call
```

**Credential setup:**
- Always starts with `google.auth.default(scopes=[GCP_SCOPE])` to get ADC
- If `service_account` is provided, wraps ADC in `google.auth.impersonated_credentials.Credentials` targeting the given SA — used only for token generation
- Any principal with `roles/redis.dbConnectionUser` and a valid access token is sufficient; no SA email is required on the credentials object itself
- If ADC resolution fails entirely (no credentials found on the host), catch `google.auth.exceptions.DefaultCredentialsError` and re-raise as `ConfigurationError` with a user-facing message. This ensures check init fails with clear text rather than a raw stack trace.

**Token lifecycle:**
- `get_token()` calls `credentials.refresh(Request())` if `is_token_expired()` is true, then returns `credentials.token`
- `is_token_expired()` checks `time.monotonic()` against the fetch timestamp; TTL is 55 minutes
- Token refresh failures (network error, permission denied) propagate as exceptions, which surface as `redis.can_connect: CRITICAL` in the check

**Dependency:**
- `google-auth>=2.0.0` added as an optional extra: `pip install datadog-checks-redisdb[gcp]`
- Import is guarded with a `try/except ImportError`; missing dependency raises `ConfigurationError` with install instructions at check init time, not at import time

### Connection Logic Changes (`redisdb.py`)

**`__init__` additions:**
```python
gcp_config = self.instance.get('gcp', {})
managed_auth = gcp_config.get('managed_authentication', {})
if is_affirmative(managed_auth.get('enabled', False)):
    # Validate no conflicting static credentials
    if self.instance.get('username') or self.instance.get('password'):
        raise ConfigurationError(
            "Cannot set 'username' or 'password' alongside gcp.managed_authentication"
        )
    if not self.instance.get('ssl'):
        self.log.warning(
            "GCP IAM auth is enabled but 'ssl' is not set. "
            "Tokens will be transmitted in plaintext."
        )
    service_account = managed_auth.get('service_account')
    self._gcp_token_provider = GCPIAMTokenProvider(service_account)
else:
    self._gcp_token_provider = None
```

**`_get_conn` additions:**
```python
def _get_conn(self, instance_config):
    no_cache = is_affirmative(instance_config.get('disable_connection_cache', False))
    key = self._generate_instance_key(instance_config)

    # Evict stale IAM connection before cache check
    if self._gcp_token_provider and self._gcp_token_provider.is_token_expired():
        conn = self.connections.pop(key, None)
        if conn:
            conn.connection_pool.disconnect()

    if no_cache or key not in self.connections:
        # ... existing param building ...
        if self._gcp_token_provider:
            connection_params['username'] = self._gcp_token_provider.username  # "default"
            connection_params['password'] = self._gcp_token_provider.get_token()
        self.connections[key] = redis.Redis(**connection_params)

    return self.connections[key]
```

**Auth error retry:**
In `_check_db`, catch `redis.AuthenticationError` once: force-evict the connection, invalidate the provider's token, and retry. If the retry also fails, propagate as normal.

The existing `_check_db` code is safe to run twice — it emits metrics but has no write-side effects — so a full retry is appropriate. Duplicate metric points within a single check run are deduplicated by the Agent.

```python
def _check_db(self):
    try:
        self._run_check_db()
    except redis.AuthenticationError:
        if self._gcp_token_provider:
            self._force_iam_reconnect()
            self._run_check_db()  # let second failure propagate
        else:
            raise

def _force_iam_reconnect(self):
    key = self._generate_instance_key(self.instance)
    conn = self.connections.pop(key, None)
    if conn:
        conn.connection_pool.disconnect()
    self._gcp_token_provider.invalidate()
```

### Files Changed

| File | Change |
|---|---|
| `redisdb/datadog_checks/redisdb/gcp.py` | New |
| `redisdb/datadog_checks/redisdb/redisdb.py` | Modify `__init__`, `_get_conn`, `_check_db` |
| `redisdb/assets/configuration/spec.yaml` | Add `gcp` block |
| `redisdb/datadog_checks/redisdb/config_models/instance.py` | Regenerated via `ddev validate config/models` |
| `redisdb/pyproject.toml` | Add optional `[gcp]` extra |

### Dependencies

```toml
[project.optional-dependencies]
gcp = ["google-auth>=2.0.0"]
```

`google-auth` is already present elsewhere in the DD agent ecosystem. No heavier GCP SDK needed.

## Edge Cases & Error Handling

| Scenario | Behavior |
|---|---|
| `google-auth` not installed | `ConfigurationError` at check init with install instructions |
| ADC resolution fails (no credentials on host) | `google.auth.exceptions.DefaultCredentialsError` propagates as `ConfigurationError` |
| `username`/`password` set alongside IAM enabled | `ConfigurationError` at init |
| `ssl` not set with IAM enabled | `WARNING` log; check continues |
| Token refresh fails (network/permission) | Exception propagates; service check reports `CRITICAL` |
| Token rejected by Redis mid-TTL | Caught as `AuthenticationError`; retry once with forced fresh token |
| `ERR_IAM_EXHAUSTED` (GCP quota throttle) | Falls through as `ResponseError`; logged, service check `CRITICAL`; no special handling in v1 |
| `disable_connection_cache: true` + IAM enabled | Works correctly; token still cached for 55 min, new connection created each run. Note: avoid pairing with very short check intervals as GCP throttles new IAM connections per second. |

## Testing

**Unit tests** (mock `google.auth`):
- Token caching: returns same token within TTL; `credentials.refresh` not called again
- Token refresh: calls `credentials.refresh` after TTL expires
- `invalidate()` causes immediate refresh on next `get_token()` call
- `username` always returns `"default"`
- `ConfigurationError` when `google-auth` not installed
- `ConfigurationError` when both static password and IAM enabled
- `_get_conn` evicts and disconnects connection pool on token expiry
- `_get_conn` injects `"default"` as username and IAM token as password
- `_check_db` retry on `AuthenticationError` with forced token refresh
- SSL warning logged when `ssl` not set

**Integration/E2E:**
No Docker fixture needed. Unit tests with mocked credentials provide sufficient coverage. Manual validation against a live Memorystore instance (Anthropic's environment) recommended before release.

## Future Work

AWS ElastiCache IAM auth (FRAGENT-3477) follows the same pattern:
- Add `aws.managed_authentication` config block (consistent with mysql/postgres)
- Add `AWSIAMTokenProvider` in a new `aws.py` using `boto3`'s ElastiCache token generation
- No changes to `_get_conn` logic needed — provider interface is identical
