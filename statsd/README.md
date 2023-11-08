# Agent Check: StatsD

## Overview

This check monitors the availability and uptime of non-Datadog StatsD servers. It also tracks the number of metrics, by metric type, received by StatsD.

This check does **NOT** forward application metrics from StatsD servers to Datadog. It collects metrics about StatsD itself.

## Setup

### Installation

The StatsD check is included in the [Datadog Agent][1] package, so you don't need to install anything else on any servers that run StatsD.

### Configuration

<!-- xxx tabs xxx -->
<!-- xxx tab "Host" xxx -->

#### Host

To configure this check for an Agent running on a host:

1. Edit the `statsd.d/conf.yaml` in the `conf.d/` folder at the root of your [Agent's configuration directory][2]. See the [sample statsd.d/conf.yaml][3] for all available configuration options:

   ```yaml
   init_config:

   instances:
     - host: localhost
       port: 8126 # or wherever your statsd listens
   ```

2. [Restart the Agent][4] to start sending StatsD metrics and service checks to Datadog.

<!-- xxz tab xxx -->
<!-- xxx tab "Containerized" xxx -->

#### Containerized

For containerized environments, see the [Autodiscovery Integration Templates][5] for guidance on applying the parameters below.

| Parameter            | Value                                 |
| -------------------- | ------------------------------------- |
| `<INTEGRATION_NAME>` | `statsd`                              |
| `<INIT_CONFIG>`      | blank or `{}`                         |
| `<INSTANCE_CONFIG>`  | `{"host": "%%host%%", "port":"8126"}` |

<!-- xxz tab xxx -->
<!-- xxz tabs xxx -->

#### Log collection

1. Collecting logs is disabled by default in the Datadog Agent, you need to enable it in `datadog.yaml`:

   ```yaml
   logs_enabled: true
   ```

2. Add this configuration block to your `statsd.d/conf.yaml` file to start collecting your Supervisord Logs:

   ```yaml
   logs:
     - type: file
       path: /path/to/my/directory/file.log
       source: statsd
   ```

   Change the `path` parameter value and configure it for your environment. 
   See the [sample statsd.d/conf.yaml][3] for all available configuration options.

3. [Restart the Agent][4].

### Validation

Run the [Agent's status subcommand][6] and look for `statsd` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][7] for a list of metrics provided by this integration.

### Events

The StatsD check does not include any events.

### Service Checks

See [service_checks.json][8] for a list of service checks provided by this integration.

## Troubleshooting

Need help? Contact [Datadog support][9].

## Further Reading

Additional helpful documentation, links, and articles:

- [StatsD, what it is and how it can help you][10]
- [Visualize StatsD metrics with Counts Graphing][11]


[1]: https://app.datadoghq.com/account/settings/agent/latest
[2]: https://docs.datadoghq.com/agent/guide/agent-configuration-files/#agent-configuration-directory
[3]: https://github.com/DataDog/integrations-core/blob/master/statsd/datadog_checks/statsd/data/conf.yaml.example
[4]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[5]: https://docs.datadoghq.com/agent/kubernetes/integrations/
[6]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[7]: https://github.com/DataDog/integrations-core/blob/master/statsd/metadata.csv
[8]: https://github.com/DataDog/integrations-core/blob/master/statsd/assets/service_checks.json
[9]: https://docs.datadoghq.com/help/
[10]: https://www.datadoghq.com/blog/statsd
[11]: https://www.datadoghq.com/blog/visualize-statsd-metrics-counts-graphing
