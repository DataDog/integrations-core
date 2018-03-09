# Agent Check: Envoy
## Overview

This check collects distributed system observability metrics from [Envoy](https://www.envoyproxy.io).

## Setup
### Installation

The Envoy check is packaged with the Agent, so simply [install the Agent](https://app.datadoghq.com/account/settings#agent) on your server.

If you need the newest version of the Envoy check, install the `dd-check-envoy` package; this package's check overrides the one packaged with the Agent. See the [integrations-core repository README.md for more details](https://docs.datadoghq.com/agent/faq/install-core-extra/).

### Configuration

Be sure the Datadog Agent can access Envoy's [admin endpoint](https://www.envoyproxy.io/docs/envoy/latest/operations/admin). Here's an example Envoy admin configuration: 

```yaml
admin:
  access_log_path: "/dev/null"
  address:
    socket_address:
      address: 0.0.0.0
      port_value: 8001
```

Create a file `envoy.yaml` in the Datadog Agent's `conf.d` directory. See the [sample envoy.yaml](https://github.com/DataDog/integrations-core/blob/master/envoy/conf.yaml.example) for all available configuration options:

### Validation

[Run the Agent's `status` subcommand](https://docs.datadoghq.com/agent/faq/agent-commands/#agent-status-and-information) and look for `envoy` under the Checks section:

```
  Checks
  ======
    [...]

    envoy
    -----
      - instance #0 [OK]
      - Collected 244 metrics, 0 events & 1 service check

    [...]
```

## Compatibility

The Envoy check is compatible with all platforms.

## Data Collected
### Metrics

See [metadata.csv](https://github.com/DataDog/integrations-core/blob/master/envoy/metadata.csv) for a list of metrics provided by this check.
See [metrics.py](https://github.com/DataDog/integrations-core/blob/master/envoy/datadog_checks/envoy/metrics.py) for a list of tags sent by each metric.

### Events

The Envoy check does not include any events at this time.

### Service Checks

`envoy.can_connect`:

Returns CRITICAL if the Agent cannot connect to Envoy to collect metrics, otherwise OK.

## Troubleshooting

Need help? Contact [Datadog Support](http://docs.datadoghq.com/help/).

## Further Reading
Learn more about infrastructure monitoring and all our integrations on [our blog](https://www.datadoghq.com/blog/)
