# Agent Check: Datadog Agent

## Overview

This check monitors the [Datadog Agent][1] itself by scraping the internal telemetry it exposes in the OpenMetrics format. Use it to track the health and throughput of the Agent's core components, such as the forwarder, DogStatsD, the aggregator, the check scheduler, and the Logs Agent.

This integration replaces the deprecated [Agent Metrics][2] integration, which collects similar data through the `go_expvar` check. Compared to expvar, the telemetry endpoint provides typed metrics, more granular tags, and a larger set of available metrics.

**Note:** The Agent's internal telemetry may change between minor Agent versions. Such changes may not be mentioned in the Agent's changelog.

## Setup

### Installation

The Datadog Agent check is included in the [Datadog Agent][3] package. No additional installation is needed.

Some of the metrics collected by default were added to the Agent's telemetry in Agent v7.86.0, so earlier Agent versions report only part of the default set.

### Configuration

The Agent always serves its telemetry at `/telemetry` on the port set by `expvar_port` in [`datadog.yaml`][4], which defaults to `5000`. Setting `telemetry.enabled: true` is not required for this check; it only enables additional telemetry.

1. Edit the `datadog_agent.d/conf.yaml` file in the `conf.d/` folder at the root of your [Agent's configuration directory][4]. See the [sample datadog_agent.d/conf.yaml][5] for all available configuration options. For example:

   ```yaml
   init_config:

   instances:
     - openmetrics_endpoint: http://localhost:5000/telemetry
   ```

   To collect telemetry beyond the default set, list the metrics to add with the `extra_metrics` option. You can view all available metrics by querying the `/telemetry` endpoint directly.

2. [Restart the Agent][6].

### Validation

[Run the Agent's status subcommand][7] and look for `datadog_agent` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][8] for a list of metrics provided by this integration.

### Events

The Datadog Agent integration does not include any events.

### Service Checks

See [service_checks.json][9] for a list of service checks provided by this integration.

## Troubleshooting

Need help? Contact [Datadog support][10].

[1]: https://docs.datadoghq.com/agent/
[2]: https://docs.datadoghq.com/integrations/agent_metrics/
[3]: https://app.datadoghq.com/account/settings/agent/latest
[4]: https://docs.datadoghq.com/agent/configuration/agent-configuration-files/
[5]: https://github.com/DataDog/integrations-core/blob/master/datadog_agent/datadog_checks/datadog_agent/data/conf.yaml.example
[6]: https://docs.datadoghq.com/agent/configuration/agent-commands/#start-stop-and-restart-the-agent
[7]: https://docs.datadoghq.com/agent/configuration/agent-commands/#agent-status-and-information
[8]: https://github.com/DataDog/integrations-core/blob/master/datadog_agent/metadata.csv
[9]: https://github.com/DataDog/integrations-core/blob/master/datadog_agent/assets/service_checks.json
[10]: https://docs.datadoghq.com/help/
