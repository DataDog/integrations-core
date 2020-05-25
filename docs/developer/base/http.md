# HTTP

-----

Whenever you need to make HTTP requests, the base class provides a convenience member that has the same interface as the
popular [requests][requests-github] library and ensures consistent behavior across all integrations.

The wrapper automatically parses and uses configuration from the `instance`, `init_config`, and Agent config. Also, this
is only done once during initialization and cached to reduce the overhead of every call.

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

## Options

Some options can be set globally in `init_config` (with `instances` taking precedence).
For complete documentation of every option, see the associated configuration templates for the
[instances][config-spec-template-instances-http] and [init_config][config-spec-template-init-config-http] sections.

::: datadog_checks.base.utils.http.StandardFields
    rendering:
      show_root_heading: false
      show_root_toc_entry: false

## Future

- Support for [UNIX sockets](https://github.com/msabramo/requests-unixsocket)
- Support for configuring cookies! Since they can be set globally, per-domain, and even per-path, the configuration may be complex
  if not thought out adequately. We'll discuss options for what that might look like. Only our `spark` and `cisco_aci` checks
  currently set cookies, and that is based on code logic, not configuration.
