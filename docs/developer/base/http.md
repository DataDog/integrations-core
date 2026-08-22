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

## Errors

A failed request raises one of the backend-agnostic types in `datadog_checks.base.utils.http_exceptions`, never an
exception class belonging to the underlying HTTP library. Catch these instead:

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

A check reporting connectivity therefore looks like this:

```python
from datadog_checks.base.utils.http_exceptions import HTTPClientError

try:
    response = self.http.get(url)
    response.raise_for_status()
except HTTPClientError as e:
    self.service_check('can_connect', AgentCheck.CRITICAL, message=str(e))
else:
    self.service_check('can_connect', AgentCheck.OK)
```

Body decoding is the one exception to that rule. Calling `response.json()` on a body that is not valid JSON raises the
standard library's `json.JSONDecodeError`, a subclass of `ValueError` that is not part of the tree above, so handle it
separately from the types listed here.

## Future

- Support for configuring cookies! Since they can be set globally, per-domain, and even per-path, the configuration may be complex
  if not thought out adequately. We'll discuss options for what that might look like. Only our `spark` and `cisco_aci` checks
  currently set cookies, and that is based on code logic, not configuration.
