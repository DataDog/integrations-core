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

### Testing with `fake_http`

Use the `fake_http` and `fake_http_response` fixtures to test a check. The check runs its real client, configured from
its instance and `init_config`, and the fixture answers on the wire with the registered `FakeHTTPResponse`.
Registrations matching the same request are served in order, and the last one then repeats. `fake_http.requests` holds
each call as the check made it, and `fake_http.sent` holds each request as it reached the wire, with the headers and
authentication the client applied.

The fixture fails the test instead of serving a response it cannot represent:

- A request sent by a client that did not opt in, such as one built with `RequestsWrapper(...)` or with the
  module-level `create_http_client()` without `agnostic=True`.
- A request sent outside a check client, a followed redirect, or a wire request that differs from the call that sent
  it, such as an auth token fetch. Pass `allow_redirects=False` to receive a registered redirect. The call fails even
  if the client catches the error and retries, as it does when renewing an auth token.
- A `FakeHTTPResponse` that sets `elapsed`, `stream_error`, `history`, `peer_cert`, `json_error` or `url`, more than one
  entry in `content_chunks`, or `lines` that do not split back unchanged.
- A `FakeHTTPResponse` whose `text`, `lines`, `content_chunks` or `json_result` disagree with the body it sends, which
  is its `content` if set. The wire carries one body, so the client derives every view from it.

A custom `status_error` is not detected and is replaced by the client's own error for the status code.

### Testing with `FakeHTTPClient`

A `FakeHTTPClient` is an in-memory `HTTPClient` that never runs the real client. Use it only where the `fake_http`
fixture cannot serve the test:

- Code that receives a client: pass the fake directly.
- A suite-local emulator that computes responses per request: subclass the fake and return it from a patched version
  of `AgentCheck.create_http_client`.
- Responses the fixture rejects, such as `elapsed` or `history`, and cookies seeded on the client with `cookies=...`.

Unlike the fixture, a `FakeHTTPClient` ignores the instance configuration, serves each registration once, and is not
safe for concurrent requests.

Each `FakeHTTPClient` starts with the real client's canonical TLS defaults. Pass `tls_config=...` to override specific
fields; overrides, including `False` and `None`, take precedence. Each client gets its own copy of the overrides, so changing
one client's TLS settings doesn't affect other clients or the caller's mapping.

### Migrating an existing check

Move a check onto this mode in one pull request dedicated to it, covering production code, tests and test-environment
helpers together. The check is migrated when all of the following hold.

Production code:

- Every check class the integration instantiates sets `AGNOSTIC_HTTP_CLIENT = True`, including legacy implementations
  and the classes a `__new__` factory returns. Don't set it on a shared base class instead.
- Extra clients come from `self.create_http_client(...)`, never from `RequestsWrapper(...)` or a `requests.Session`.
- Errors are caught as the types listed under [Errors](#errors), keeping separately handled cases separate. A timeout
  handled apart from a connection error maps to `HTTPClientTimeoutError` and `HTTPClientConnectionError`, and an error
  status caught as `HTTPError` maps to `HTTPClientStatusError`. A body that is not valid JSON raises the standard
  library's `json.JSONDecodeError`, a `ValueError`, rather than the `simplejson` or `requests` one.

Tests:

- Unit tests register responses per URL with the `fake_http_response` fixture, or register exceptions with the
  fixture's `fake_http.register_response()`, and call `fake_http.assert_all_responses_consumed()`. The last matching
  registration repeats, so a test that runs the check twice registers a response once unless the second run needs a
  different one.
- Assert the outcome as well, such as service checks or metrics. A check that catches `Exception` around its request
  also catches the error the fixture raises for an unmatched request.
- Configuration tests run through the fixture and assert `fake_http.sent`, which holds each request with the headers and
  authentication the client applied: instance headers, Basic credentials, and no `Authorization` header after a call
  to `disable_auth()`. Settings that never reach the wire, such as `timeout`, may be asserted on `check.http.options`.
- A helper that receives a client gets one from `fake_http.create_client()`, not the fixture object itself.
- JSON errors are tested by registering a body that is not JSON, such as `content=b'not json'`, not with `json_error`.
- Redirects are tested by registering the 3xx response and calling with `allow_redirects=False`. A followed redirect
  fails the test.
- Tests use `FakeHTTPClient` only for the cases listed under
  [Testing with `FakeHTTPClient`](#testing-with-fakehttpclient).

Everything else:

- Nothing under `datadog_checks/`, `tests/` (including `conftest.py` and Docker helpers) or the package's scripts
  imports `requests`, `urllib3`, `requests_mock`, `responses` or a `requests_*` package. None of them uses the
  classes `RequestsWrapper`, `ResponseWrapper` or `MockResponse`, the `mock_http_response` fixture, `requests.*` patch
  targets, or the client's `.session`, `._session` or `.raw` members.
- Environment helpers, such as readiness conditions and data loaders, use the standard library. The CouchDB helper
  in `couch/tests/api.py` is a template: it sends Basic credentials preemptively, because the `urllib` auth handler
  waits for a 401 challenge, and turns the `URLError` wrapping a connect timeout back into `TimeoutError`.
- The package's `hatch.toml` and `pyproject.toml` no longer list `requests` or `requests-mock`, and the package
  requires a `datadog-checks-base` release that includes this mode.

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
