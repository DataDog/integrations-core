# SNMP Testing

## Known issues

### macOS/Windows: "No SNMP response received before timeout for instance localhost"

This is most likely due to a bug with cross-container UDP communication in Docker for macOS and Windows.

A workaround is to pass set your IPv4 host address as the `DD_SNMP_HOST` environment variable, e.g.:

```shell
$ ddev env start -e DD_SNMP_HOST=10.98.76.543 snmp py37
```

The SNMP environment will use this IP instead of the default Docker-provided hostname to connect to the SNMP server container.

This should allow `$ ddev env check ...` and E2E tests to pass locally.
