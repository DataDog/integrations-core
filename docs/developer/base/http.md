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

To mock HTTP in tests without depending on `requests` or `httpx`, use the helpers in `datadog_checks.base.utils.http_mock`:

- **`HTTPResponseMock`**: Builds a response (status_code, content, headers, json_data) that satisfies the same interface as the real response.
- **`RequestWrapperMock`**: Implements the HTTP client interface. Pass callables for `get`, `post`, etc. to control responses. As a context manager with a check instance, it patches `check.http` for the duration:

```python
from datadog_checks.base.utils.http_mock import HTTPResponseMock, RequestWrapperMock

def test_check(dd_run_check, check, instance):
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
