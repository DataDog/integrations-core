# HTTP

-----

Whenever you need to make HTTP requests, the base class provides a convenience member that ensures consistent behavior
across all integrations. Its request methods and response objects follow the shape of the popular
[requests][requests-github] library, but the member is defined by its own interface rather than by that library.
Anything this page does not document is an implementation detail and may change.

The wrapper automatically parses and uses configuration from the `instance`, `init_config`, and Agent config. Also, this
is only done once during initialization and cached to reduce the overhead of every call.

For example, to make a GET request you would use:

```python
response = self.http.get(url)
```

and the wrapper will pass the right things to the underlying HTTP library. All methods accept optional keyword arguments
like `stream`, etc.

Any method-level option will override configuration. So for example if `tls_verify` was set to false and you do
`self.http.get(url, verify=True)`, then SSL certificates will be verified on that particular request. You can
use the keyword argument `persist` to override `persist_connections`.

There is also support for non-standard or legacy configurations with the `HTTP_CONFIG_REMAPPER` class attribute. For example:

```python
class MyCheck(AgentCheck):
    HTTP_CONFIG_REMAPPER = {
        'disable_ssl_validation': {
            'name': 'tls_verify',
            'default': False,
            'invert': True,
        },
        ...
    }
    ...
```

Support for Unix socket is provided via [requests-unixsocket][requests-unixsocket-pypi] and allows making UDS requests on the `unix://` scheme (not supported on Windows until Python adds support for `AF_UNIX`, see [ticket][python-bpo-af-unix-win]):

```python
url = 'unix:///var/run/docker.sock'
response = self.http.get(url)
```

## Backend-neutral mode

Set the `AGNOSTIC_HTTP_CLIENT` class attribute to opt a check into the interface this page describes:

```python
class MyCheck(AgentCheck):
    AGNOSTIC_HTTP_CLIENT = True
```

With it set, every client the check creates through `self.http` or `create_http_client()`, including the clients its
OpenMetrics and Prometheus scrapers build, returns responses that expose only the documented members and raises the
errors listed under [Errors](#errors). The `fake_http` test fixture requires it. Without it, clients return `requests`
responses and raise `requests` exceptions unchanged.

### Migrating an existing check

Move a check onto this mode in one pull request dedicated to it, covering production code, tests and test-environment
helpers together. The check is migrated when all of the following hold:

- `AGNOSTIC_HTTP_CLIENT = True` is set on every check class the integration instantiates, including legacy
  implementations and the classes a `__new__` factory returns. Don't set it on a shared base class instead.
- Extra clients are built with `create_http_client()`, never with `RequestsWrapper` or a `requests.Session`.
- Production code catches the types listed under [Errors](#errors). Keep separately handled cases separate: a timeout
  handled apart from a connection error maps to `HTTPClientTimeoutError` and `HTTPClientConnectionError`, and `except
  HTTPError` maps to `HTTPClientStatusError`. Catch `json.JSONDecodeError` from the standard library, not from
  `simplejson` or `requests`, for bodies that are not valid JSON.
- Nothing under `datadog_checks/` or `tests/` imports `requests`, `urllib3`, `requests_mock`, `responses` or a
  `requests_*` package, or uses `RequestsWrapper`, `ResponseWrapper`, `MockResponse`, `mock_http_response`,
  `requests.*` patch targets, `.session`, `._session` or `.raw`.
- Unit tests register responses per URL with the `fake_http_response` fixture, or register exceptions with
  `fake_http.register_response()`, and call `fake_http.assert_all_responses_consumed()`. Register one response per
  request, so a test that runs the check twice registers each response twice.
- Tests for configuration, such as authentication or timeouts, create the check without the `fake_http` fixture and
  assert on `check.http.options`, because the fake does not parse configuration.
- Environment helpers, such as `conftest.py` conditions and data loaders, use the standard library (`urllib.request`).
- `requests` and `requests-mock` are removed from `hatch.toml` and `pyproject.toml`, and `datadog-checks-base` is
  pinned to a release that includes this mode.

### Testing TLS configuration

Each `FakeHTTPClient` starts with the real client's canonical TLS defaults. Pass `tls_config=...` to override specific
fields; overrides, including `False` and `None`, take precedence. Each client gets its own copy of the overrides, so changing
one client's TLS settings doesn't affect other clients or the caller's mapping.

Calling `fake_http.create_client()` creates a fresh client with defaults, not a copy of the parent's TLS settings.
The fixture does not parse integration configuration or legacy aliases. Tests needing non-default TLS settings must
configure each check-owned fake explicitly; changing the parent fixture's `tls_config` does not configure those clients.

## Options

Some options can be set globally in `init_config` (with `instances` taking precedence).
For complete documentation of every option, see the associated configuration templates for the
[instances][config-spec-template-instances-http] and [init_config][config-spec-template-init-config-http] sections.

## Disabling authentication

Call `self.http.disable_auth()` to suppress the client's configured `auth` (such as Basic credentials) and automatic `.netrc`
credentials on subsequent requests, including redirects:

```python
self.http.disable_auth()
response = self.http.get(url)
```

This applies to existing and newly created sessions, including requests with `auth=None`, without disabling other
environment settings, such as proxies. It does not suppress `auth_token` handling or an `Authorization` entry in `headers`.
Explicit per-request authentication still overrides client configuration.

## Errors

With `AGNOSTIC_HTTP_CLIENT` set, a failed request raises one of the backend-neutral types from the
module `datadog_checks.base.utils.http_exceptions`, never an exception class belonging to the underlying HTTP
library. Catch these instead:

| Exception | Raised when |
| --- | --- |
| `HTTPClientError` | Root of the tree. Catch this to handle any HTTP failure. |
| `HTTPClientRequestError` | The request never produced a usable response. |
| `HTTPClientConnectionError` | The connection could not be established or was lost. |
| `HTTPClientSSLError` | The TLS handshake or certificate verification failed. |
| `HTTPClientInvalidURLError` | The URL was rejected before a connection was attempted. |
| `HTTPClientTimeoutError` | The request exceeded its configured timeout. |
| `HTTPClientConnectTimeoutError` | The timeout elapsed while establishing the connection. |
| `HTTPClientReadTimeoutError` | The timeout elapsed while waiting for response data. |
| `HTTPClientStatusError` | An error status was raised through `raise_for_status()`. |

For example, a check that skips optional data when its endpoint is unavailable looks like this:

```python
from datadog_checks.base.utils.http_exceptions import HTTPClientError

try:
    response = self.http.get(url)
    response.raise_for_status()
except HTTPClientError as e:
    self.log.debug('Could not retrieve version metadata: %s', e)
    return
```

Decoding the body is the only failure outside this tree. Calling `response.json()` on a body that is not valid JSON raises the
standard library's `json.JSONDecodeError`, a subclass of `ValueError` that is not part of the tree above, so handle it
separately from the types listed here.

## Future

- Support for configuring cookies! Since they can be set globally, per-domain, and even per-path, the configuration may be complex
  if not thought out adequately. We'll discuss options for what that might look like. Only our `spark` and `cisco_aci` checks
  currently set cookies, and that is based on code logic, not configuration.
