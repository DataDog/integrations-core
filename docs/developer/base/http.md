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

## Options

Some options can be set globally in `init_config` (with `instances` taking precedence).
For complete documentation of every option, see the associated configuration templates for the
[instances][config-spec-template-instances-http] and [init_config][config-spec-template-init-config-http] sections.

## Interface

The interface lives in `datadog_checks.base.utils.http_protocol` as the `HTTPClient` and `HTTPResponse` protocols.
`RequestsWrapper` implements them on top of requests today. Read those protocols to find out what a check may rely on:
a member reachable on the concrete client but absent from them is an implementation detail, and a future backend is
free not to provide it.

Beyond the verb methods, the client exposes these capabilities so a check never has to reach into the backend:

| Member | Purpose |
| --- | --- |
| `get_header(name, default=None)` | Read a configured request header. Lookup is case-insensitive, and the value returned is the one that reaches the wire. |
| `set_header(name, value)` | Set a request header for later requests, collapsing any other spelling of the same name. |
| `disable_auth()` | Suppress config-derived and environment or `.netrc` auth, leaving proxy and CA resolution intact. |
| `get_cookie(name, default=None)` | Read a cookie held on the persistent session, or the default when it is absent or ambiguous. |
| `should_bypass_proxy(url)` | Whether the URL bypasses the configured proxy under the client's `no_proxy` rules. |
| `close()` | Close open connections. Idempotent, and the client stays usable afterwards. |
| `trust_env` | Whether environment configuration (proxies, auth, CA bundles) is trusted. |

Responses add `get_peer_cert(binary_form=False)` for the peer TLS certificate, which returns `None` for a plain HTTP
request or once the connection has been released.

## Building a client outside a check

`self.http` covers the common case. When a check needs a second client, built from a config other than its own
instance, call the factory rather than constructing a backend object:

```python
scraper_client = self.create_http_client(scraper_config)
```

`AgentCheck.create_http_client` is also the single override point for the backing implementation, and
`datadog_checks.base.utils.http.create_http_client` is the module-level equivalent for code that has no check at hand.

## Testing

The `datadog_checks_dev` pytest plugin ships a `mock_http` fixture that patches `AgentCheck.http` and
`AgentCheck.create_http_client` with a sealed double built from the `HTTPClient` protocol. Because it is sealed,
reading a member the protocol does not declare raises `AttributeError`, so a test cannot come to depend on a detail of
the backend. Use `mock_openmetrics_http` or `mock_prometheus_http` for checks built on those scrapers.

`datadog_checks.dev.http.MockHTTPResponse` is the matching response double. It enforces the `HTTPResponse` protocol the
same way and reproduces the character-set rules a real response applies, so a body with no `Content-Type` decodes the
way the production backend decodes it.

## Future

- Support for configuring cookies! Since they can be set globally, per-domain, and even per-path, the configuration may be complex
  if not thought out adequately. We'll discuss options for what that might look like. Only our `spark` and `cisco_aci` checks
  currently set cookies, and that is based on code logic, not configuration.
