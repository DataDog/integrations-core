# Agent Check: StatsD

## Overview

This check monitors the availability and uptime of non-Datadog StatsD servers. It also tracks the number of metrics, by metric type, received by StatsD.

This check does **NOT** forward application metrics from StatsD servers to Datadog. It collects metrics about StatsD itself.

## Setup
### Installation

The StatsD check is packaged with the Agent, so simply [install the Agent](https://app.datadoghq.com/account/settings#agent) on any servers that run StatsD.

If you need the newest version of the StatsD check, install the `dd-check-statsd` package; this package's check overrides the one packaged with the Agent. See the [integrations-core repository README.md for more details](https://docs.datadoghq.com/agent/faq/install-core-extra/).

### Configuration

Create a file `statsd.yaml` in the Agent's `conf.d` directory. See the [sample statsd.yaml](https://github.com/DataDog/integrations-core/blob/master/statsd/conf.yaml.example) for all available configuration options:

```
init_config:

instances:
  - host: localhost
    port: 8126 # or wherever your statsd listens
```

[Restart the Agent](https://docs.datadoghq.com/agent/faq/agent-commands/#start-stop-restart-the-agent) to start sending StatsD metrics and service checks to Datadog.

### Validation

[Run the Agent's `status` subcommand](https://docs.datadoghq.com/agent/faq/agent-commands/#agent-status-and-information) and look for `statsd` under the Checks section:

```
  Checks
  ======
    [...]

    statsd
    -------
      - instance #0 [OK]
      - Collected 3 metrics, 0 events & 2 service checks

    [...]
```

## Compatibility

The statsd check is compatible with all major platforms.

## Data Collected
### Metrics
See [metadata.csv](https://github.com/DataDog/integrations-core/blob/master/statsd/metadata.csv) for a list of metrics provided by this integration.

### Events
The StatsD check does not include any event at this time.

### Service Checks

**statsd.is_up**:

Returns CRITICAL if the StatsD server does not respond to the Agent's health status request, otherwise OK.

**statsd.can_connect**:

Returns CRITICAL if the Agent cannot collect metrics about StatsD, otherwise OK.

## Troubleshooting
Need help? Contact [Datadog Support](http://docs.datadoghq.com/help/).

## Further Reading
If you don't know what StatsD is and how does it work, check out [our blog post about it](https://www.datadoghq.com/blog/statsd/)

To get a better idea of how (or why) to visualize StatsD metrics with Counts Graphing with Datadog, check out our [series of blog posts](https://www.datadoghq.com/blog/visualize-statsd-metrics-counts-graphing/) about it.
