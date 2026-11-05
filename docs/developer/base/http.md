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

Opted-in checks use only the members listed under [Reference](#reference).

### Client defaults

Each client starts from defaults built from the check's configuration. To read or change a default header after the
client exists, for example to send a session token on every later request, use `get_header()` and `set_header()`. Both
match header names case-insensitively:

```python
self.http.set_header('X-Vault-Token', token)
```

The `options` attribute holds every default, such as `headers`, `timeout` and `verify`. It stays public while checks
migrate to this interface, but its keys and value shapes follow `requests`, for example a `(connect, read)` tuple for
`timeout`. Once the persistent session exists, setting a key to `None`, or replacing `headers` or `proxies` with a
mapping that omits keys, does not remove the values the session started with. Prefer `set_header()`, `disable_auth()`
and per-request options to editing `options`.

The `tls_config` attribute holds the resolved `tls_*` settings, for code that builds its own SSL context.

### Proxies

Each client resolves its proxies once, from the first of these settings that is set:

1. `proxy` in the instance.
2. `proxy` in `init_config`.
3. The Agent's `proxy` setting, unless `use_agent_proxy` is false in `init_config`.

Hosts in the `no_proxy` entry of that setting bypass the proxy, and `should_bypass_proxy(url)` reports whether a URL
matches them. Setting `skip_proxy` in the instance or `init_config` disables every proxy, including environment
variables. When no proxy is configured and `trust_env` is true, the client uses environment variables such as
`HTTP_PROXY` and `NO_PROXY`. Environment variables do not change a configured proxy, and `should_bypass_proxy()` ignores
them.

A per-request `proxies` mapping replaces the client's proxies for that request. Omit the option to keep the client's
settings: `proxies=None` also uses the configured proxies, but skips `no_proxy` and `skip_proxy`.

### Additional clients

The client behind `self.http` is created on first use and then reused. To build another one, for example for an
endpoint with its own credentials, call `create_http_client()`:

```python
self.api_client = self.create_http_client({**self.instance, 'timeout': 30})
```

Each argument replaces the check's own value rather than merging with it, and an omitted or `None` argument falls back
to that value:

- The first positional argument, `instance`, is used instead of the check's instance. Copy `self.instance` into it, as
  above, to keep the check's other settings.
- The keyword-only `init_config` is used instead of the check's `init_config`.
- The keyword-only `remapper` is used instead of `HTTP_CONFIG_REMAPPER`.

Each call builds a new client that follows the check's `AGNOSTIC_HTTP_CLIENT` setting. Do not instantiate
`RequestsWrapper` or a `requests.Session` directly.

### Connections and sessions

With `persist_connections` enabled, or with `persist=True` on a request, requests share one session that keeps its
connections open and stores the cookies the server sets, which `get_cookie()` reads. Every other request uses a new
session, so the cookies it receives are not kept.

Calling `close()` closes open connections and discards the persistent session and its cookies. The client stays
usable, and the next request starts a new session.

The `trust_env` attribute, true by default, controls whether requests read environment proxy variables and `.netrc`
credentials.

A response requested with `stream=True` holds its connection until the body is fully read or the response is closed,
so use it as a context manager:

```python
with self.http.get(url, stream=True) as response:
    for line in response.iter_lines():
        ...
```

### Testing with `fake_http`

Use the `fake_http` and `fake_http_response` fixtures to test a check. The check runs its real client, configured from
its instance and `init_config`, and the fixture answers on the wire with the registered `FakeHTTPResponse`.
Registrations matching the same request are served in order, and the last one then repeats.

The `fake_http_response` fixture builds a `FakeHTTPResponse`, registers it and returns it:

```python
def test_check(dd_run_check, fake_http_response, instance):
    fake_http_response('http://localhost:8080/metrics', 'up 1\n')
    fake_http_response('http://localhost:8080/api', method='POST', json_data={'status': 'ok'})
    fake_http_response('http://localhost:8080/health', status_code=503)
    ...
```

Its signature is `fake_http_response(url, content=b'', *, method='GET', json_data=..., status_code=200,
encoding='utf-8', match_options=None, **overrides)`. Passing `json_data` sends it serialized as the body. Other keyword
arguments, such as `headers` or `reason`, are passed to `FakeHTTPResponse`.

To raise an exception instead, or to register a response built by hand, call
`fake_http.register_response(method, url, response, match_options=None)`:

```python
from datadog_checks.base.utils.http_exceptions import HTTPClientConnectTimeoutError

fake_http.register_response('GET', url, HTTPClientConnectTimeoutError('timed out'))
```

An exception is raised as registered. Unlike the errors the real client raises, it does not also subclass a `requests`
exception, so a leftover `except requests...` clause in the check does not catch it.

A registration matches a call when:

- Its method and URL equal the call's exactly, as the check passed them. Parameters sent through `params` are not part
  of that URL: register the URL without them and match them with `match_options`. A URL that the check passes with a
  query string must be registered with the same query string.
- Each entry of `match_options` equals the option the check passed to the call, for example
  `match_options={'params': {'page': '2'}}`. An option the check did not pass never matches, client defaults such as the
  configured timeout are not considered, and options left out of `match_options` are ignored.

The fixture records two views of each request:

- The `fake_http.requests` list holds a `RecordedRequest(method, url, options)` for each call, with the method
  upper-cased and the options exactly as the check passed them.
- The `fake_http.sent` list holds a `SentRequest(method, url, headers)` for each request that reached the wire, with
  the final URL including query parameters, and the headers after the client applied its defaults and authentication.

Use `fake_http.assert_requests(expected)` to check the full list of calls, in order, and
`fake_http.assert_has_request(expected)` to check for one call. Both compare whole `RecordedRequest` values, so list
every option the check passed:

```python
from datadog_checks.base.stubs.http import RecordedRequest

fake_http.assert_has_request(RecordedRequest('GET', url, {'params': {'page': '2'}}))
```

Recorded options hold only what the check passed to each call. To check settings the client resolved from the
configuration, such as its timeout or TLS verification, assert on the check's client, or on the headers in
`fake_http.sent`:

```python
check = MyCheck('my_check', {}, [instance])
assert check.http.options['timeout'] == (5.0, 5.0)
assert check.http.tls_config['tls_verify'] is False
```

The fixture fails the test instead of serving a response it cannot represent:

- A request with no matching registration, or one sent by a client that did not opt in, such as one built with
  `RequestsWrapper(...)` or with the module-level `create_http_client()` without `agnostic=True`.
- A request sent outside a check client, a followed redirect, or a wire request that differs from the call that sent
  it, such as an auth token fetch. Pass `allow_redirects=False` to receive a registered redirect. The call fails even
  if the client catches the error and retries, as it does when renewing an auth token.
- A `FakeHTTPResponse` that sets `elapsed`, `stream_error`, `history`, `peer_cert`, `json_error` or `url`, more than one
  entry in `content_chunks`, or `lines` that do not split back unchanged.
- A `FakeHTTPResponse` whose `text`, `lines`, `content_chunks` or `json_result` disagree with the body it sends, which
  is its `content` if set. The wire carries one body, so the client derives every view from it.

Request-guard errors also fail fixture cleanup, even if the check catches the original error and continues. Deliberately
registered exceptions and error responses are valid test outcomes, not guard errors. Call
`fake_http.assert_all_responses_consumed()` to check separately that every registration was used.

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
module `datadog_checks.base.utils.http_exceptions`. Catch these instead of the underlying HTTP library's exceptions.
Catching a type also catches every type below it in the tree:

| Exception | Parent | Raised when |
| --- | --- | --- |
| `HTTPClientError` | `Exception` | Root of the tree. Catch this to handle any HTTP failure. |
| `HTTPClientRequestError` | `HTTPClientError` | The request never produced a usable response. |
| `HTTPClientConnectionError` | `HTTPClientRequestError` | The connection could not be established or was lost. |
| `HTTPClientSSLError` | `HTTPClientConnectionError` | The TLS handshake or certificate verification failed. |
| `HTTPClientInvalidURLError` | `HTTPClientRequestError` | The URL was rejected before a connection was attempted. |
| `HTTPClientTimeoutError` | `HTTPClientRequestError` | The request exceeded its configured timeout. |
| `HTTPClientConnectTimeoutError` | `HTTPClientTimeoutError` | The timeout elapsed while establishing the connection. |
| `HTTPClientReadTimeoutError` | `HTTPClientTimeoutError` | The timeout elapsed while waiting for response data. |
| `HTTPClientStatusError` | `HTTPClientError` | An error status was raised through `raise_for_status()`. |

Timeouts are not connection errors: `except HTTPClientConnectionError` does not catch a connect timeout.

Each error the client raises also subclasses the `requests` exception it replaces, and through it `OSError`, so
existing handlers that catch `requests` exceptions keep matching. Don't rely on that in an opted-in check: catch the
types above instead. The `fake_http` fixture raises them without the `requests` base classes, so a `requests` handler
never runs in tests.

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

Decoding the body is the only failure outside this tree. Calling `response.json()` on a body that is not valid JSON
raises the standard library's `json.JSONDecodeError`, a subclass of `ValueError`. In `requests` this error is also a
`RequestException`, but `except HTTPClientError` does not catch it, so handle it separately.

### Error details

Every error has two attributes:

- The `response` attribute holds the response, if one was received, such as for an `HTTPClientStatusError` raised by
  `raise_for_status()`. It is `None` for connection, TLS, timeout and invalid-URL errors.
- The `request` attribute holds the method, URL and headers of the request that failed, or `None` if the request was
  rejected before it was built, such as for an invalid URL. Its headers are not redacted and can include credentials,
  such as an `Authorization` header, so don't log them.

The message, `str(error)`, comes from the backend and may change with it. Don't parse it or assert on its exact text.

### Raising errors from a check

A check may raise these types itself, for example when a response with a successful status is still unusable:

```python
from datadog_checks.base.utils.http_exceptions import HTTPClientStatusError

if response.status_code != 201:
    raise HTTPClientStatusError(f'Expected 201, got {response.status_code}', response=response)
```

The constructor takes the message, and optional `response` and `request` keyword arguments. An error raised this way
does not subclass any `requests` exception.

Don't subclass these types. Code that handles HTTP failures by catching a type from the tree, such as
`except HTTPClientError`, would also catch the subclass, so the check's own failure would be reported as an HTTP
failure. Derive check-specific errors from `Exception` instead.

### Porting from `requests`

Replace each `requests` exception with its counterpart:

| `requests` exception | Catch instead |
| --- | --- |
| `RequestException` | `HTTPClientError`, and `json.JSONDecodeError` if the block calls `response.json()` |
| `ConnectionError`, `ProxyError` | `HTTPClientConnectionError`, and `HTTPClientTimeoutError` to keep catching connect timeouts |
| `SSLError` | `HTTPClientSSLError` |
| `Timeout` | `HTTPClientTimeoutError` |
| `ConnectTimeout` | `HTTPClientConnectTimeoutError` |
| `ReadTimeout` | `HTTPClientReadTimeoutError` |
| `HTTPError` | `HTTPClientStatusError` |
| `InvalidURL`, `MissingSchema`, `InvalidSchema`, `URLRequired` | `HTTPClientInvalidURLError` |
| `JSONDecodeError` | `json.JSONDecodeError` |
| Any other, such as `TooManyRedirects` or `ChunkedEncodingError` | `HTTPClientRequestError` |

In `requests`, a connect timeout is both a `Timeout` and a `ConnectionError`. Here it is only a timeout, so replacing
`except requests.ConnectionError` with `except HTTPClientConnectionError` alone changes which branch handles a connect
timeout, and which service check status it reports:

```python
# Before
except requests.exceptions.ConnectionError:
    self.service_check('can_connect', AgentCheck.CRITICAL)

# After
except (HTTPClientConnectionError, HTTPClientTimeoutError):
    self.service_check('can_connect', AgentCheck.CRITICAL)
```

Also check the order of `except` clauses. A handler for `Timeout` placed after one for `ConnectionError` used to miss
connect timeouts, and now catches them.

## Reference

Opted-in checks may use the members documented below. To annotate clients and responses, import `HTTPClient` and
`HTTPResponse` from `datadog_checks.base.utils.http_protocol`. Some members, such as `HTTPClient.options`, use
`requests` value shapes.

::: datadog_checks.base.utils.http_protocol.HTTPClient
    options:
      heading_level: 3

::: datadog_checks.base.utils.http_protocol.HTTPRequestOptions
    options:
      heading_level: 3

::: datadog_checks.base.utils.http_protocol.HTTPResponse
    options:
      heading_level: 3

::: datadog_checks.base.utils.http_protocol.HTTPHeaders
    options:
      heading_level: 3
      members: false

## Future

- Support for configuring cookies! Since they can be set globally, per-domain, and even per-path, the configuration may be complex
  if not thought out adequately. We'll discuss options for what that might look like. Only our `spark` and `cisco_aci` checks
  currently set cookies, and that is based on code logic, not configuration.
