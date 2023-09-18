# Agent Check: Temporal

## Overview

This check monitors [Temporal][1] through the Datadog Agent.

## Setup

Follow the instructions below to install and configure this check for an Agent running on a host. For containerized environments, see the [Autodiscovery Integration Templates][3] for guidance on applying these instructions.

### Installation

The Temporal check is included in the [Datadog Agent][2] package.
No additional installation is needed on your server.

### Configuration

1. Configure your Temporal services to expose metrics via a `prometheus` endpoint by following the [official Temporal documentation][10].

2. Edit the `temporal.d/conf.yaml` file located in the `conf.d/` folder at the root of your Agent's configuration directory to start collecting your Temporal performance data. 

To get started, configure the `openmetrics_endpoint` option to match the `listenAddress` and `handlerPath` options from your Temporal server configuration.

Note that when Temporal services in a cluster are deployed independently, every service exposes its own metrics. As a result, you need to configure the `prometheus` endpoint for every service that you want to monitor and define a separate `instance` on the integration's configuration for each of them.

See the [sample temporal.d/conf.yaml][4] for all available configuration options.

#### Log collection

1. Collecting logs is disabled by default in the Datadog Agent. Enable it in your `datadog.yaml` file:

   ```yaml
   logs_enabled: true
   ```

2. Configure your Temporal Cluster to output logs to a file by following the [official documentation][11].

3. Uncomment and edit the logs configuration block in your `temporal.d/conf.yaml` file, and set the `path` to point to the file you configured on your Temporal Cluster:

  ```yaml
  logs:
    - type: file
      path: /var/log/temporal/temporal-server.log
      source: temporal
  ```

4. [Restart the Agent][5].

### Validation

[Run the Agent's status subcommand][6] and look for `temporal` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][7] for a list of metrics provided by this integration.

### Events

The Temporal integration does not include any events.

### Service Checks

See [service_checks.json][8] for a list of service checks provided by this integration.

### Logs

The Temporal integration can collect logs from the Temporal Cluster and forward them to Datadog. 

## Troubleshooting

Need help? Contact [Datadog support][9].

## Further Reading

Additional helpful documentation, links, and articles:

- [Monitor the health of your Temporal Server with Datadog][12]


[1]: https://temporal.io/
[2]: https://app.datadoghq.com/account/settings/agent/latest
[3]: https://docs.datadoghq.com/agent/kubernetes/integrations/
[4]: https://github.com/DataDog/integrations-core/blob/master/temporal/datadog_checks/temporal/data/conf.yaml.example
[5]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[6]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[7]: https://github.com/DataDog/integrations-core/blob/master/temporal/metadata.csv
[8]: https://github.com/DataDog/integrations-core/blob/master/temporal/assets/service_checks.json
[9]: https://docs.datadoghq.com/help/
[10]: https://docs.temporal.io/references/configuration#prometheus
[11]: https://docs.temporal.io/references/configuration#log
[12]: https://www.datadoghq.com/blog/temporal-server-integration/
