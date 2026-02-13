# HTTP

-----

Whenever you need to make HTTP requests, the base class provides a convenience member that has the same interface as the
popular [requests][requests-github] library and ensures consistent behavior across all integrations.

The wrapper automatically parses and uses configuration from the `instance`, `init_config`, and Agent config. Also, this
is only done once during initialization and cached to reduce the overhead of every call.

By default, the HTTP client is backed by the `requests` library. You can opt in to an `httpx`-backed client by setting
the option **`use_httpx`** to `true` in `init_config` or in the instance configuration (instance takes precedence).
When `use_httpx` is true, `self.http` returns a wrapper that uses the same API but is implemented with `httpx`. The
default is `false` (requests-based wrapper).

For example, to make a GET request you would use:

```python
response = self.http.get(url)
```

and the wrapper will pass the right things to `requests`. All methods accept optional keyword arguments like `stream`, etc.

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

## Testing

To mock HTTP in tests without depending on `requests` or `httpx`, use the helpers in `datadog_checks.dev.http` (or the `mock_response`, `mock_http_response`, `http_response_mock`, and `request_wrapper_mock` pytest fixtures from the dev plugin).

**Mock HTTP design (implementation-independent):**

1. **Check mode** – When testing a check that has `get_http_handler` (e.g. OpenMetrics, Prometheus), use the `mock_http_response` fixture with the check class as first argument. It patches that class’s `get_http_handler` with a `RequestWrapperMock` and a response queue:

   ```python
   mock_http_response(OpenMetricsBaseCheckV2, file_path=fixture_path)
   dd_run_check(check(instance))
   ```

2. **General mode** – When the test does not have a check (e.g. wrapper-level or helper code), call `mock_http_response(...)` with only response spec (no check class). It returns `(client, enqueue)` where `client` is a `RequestWrapperMock` and `enqueue(...)` adds responses; inject `client` where the HTTP wrapper is created or used.

   ```python
   client, enqueue = mock_http_response(content=b'first')
   enqueue(content=b'second')
   with patch('mymodule.get_http_handler', return_value=client):
       ...
   ```

3. **Direct helpers** – For ad-hoc tests, use `HTTPResponseMock` and `RequestWrapperMock` from `datadog_checks.dev.http`:

   ```python
   from datadog_checks.dev.http import HTTPResponseMock, RequestWrapperMock

   with RequestWrapperMock(check, get=lambda url, **kwargs: HTTPResponseMock(200, content=b'...')):
       dd_run_check(check(instance))
   ```

This keeps tests implementation-independent so they pass whether the check uses the requests-based or httpx-based wrapper.

## Options

Some options can be set globally in `init_config` (with `instances` taking precedence).
For complete documentation of every option, see the associated configuration templates for the
[instances][config-spec-template-instances-http] and [init_config][config-spec-template-init-config-http] sections.

## Future

- Support for configuring cookies! Since they can be set globally, per-domain, and even per-path, the configuration may be complex
  if not thought out adequately. We'll discuss options for what that might look like. Only our `spark` and `cisco_aci` checks
  currently set cookies, and that is based on code logic, not configuration.
