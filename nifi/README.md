# Agent Check: NiFi

## Overview

This check monitors [Apache NiFi][1] through the Datadog Agent.

Apache NiFi is a data integration and automation platform for moving data between systems. This integration collects JVM health, flow throughput, queue backpressure, processor status, and bulletin events from the NiFi REST API, providing visibility into data pipeline health without requiring NiFi-side configuration.

## Setup

Follow the instructions below to install and configure this check for an Agent running on a host. For containerized environments, see the [Autodiscovery Integration Templates][3] for guidance on applying these instructions.

### Installation

The NiFi check is included in the [Datadog Agent][2] package.
No additional installation is needed on your server.

### Configuration

1. Edit the `nifi.d/conf.yaml` file, in the `conf.d/` folder at the root of your Agent's configuration directory to start collecting your NiFi performance data. See the [sample nifi.d/conf.yaml][4] for all available configuration options.

2. At minimum, configure the `api_url`, `username`, and `password`:

   ```yaml
   instances:
     - api_url: https://localhost:8443/nifi-api
       username: <NIFI_USERNAME>
       password: <NIFI_PASSWORD>
       tls_verify: true
   ```

3. [Restart the Agent][5].

### Validation

[Run the Agent's status subcommand][6] and look for `nifi` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][7] for a list of metrics provided by this integration.

Per-connection and per-processor metrics are opt-in to control cardinality. Enable them with `collect_connection_metrics: true` and `collect_processor_metrics: true`. Use `max_connections` and `max_processors` to cap the number of entities monitored.

### Events

NiFi bulletins (errors and warnings from processors and system components) are forwarded as Datadog events when `collect_bulletins` is enabled (default: true). Filter by severity with `bulletin_min_level` (default: WARNING).

### Service Checks

The NiFi integration does not include any service checks. Connectivity is reported via the `nifi.can_connect` gauge (1 = OK, 0 = unreachable).

See [service_checks.json][8] for a list of service checks provided by this integration.

## Troubleshooting

Need help? Contact [Datadog support][9].


[1]: https://nifi.apache.org/
[2]: https://app.datadoghq.com/account/settings/agent/latest
[3]: https://docs.datadoghq.com/containers/kubernetes/integrations/
[4]: https://github.com/DataDog/integrations-core/blob/master/nifi/datadog_checks/nifi/data/conf.yaml.example
[5]: https://docs.datadoghq.com/agent/configuration/agent-commands/#start-stop-and-restart-the-agent
[6]: https://docs.datadoghq.com/agent/configuration/agent-commands/#agent-status-and-information
[7]: https://github.com/DataDog/integrations-core/blob/master/nifi/metadata.csv
[8]: https://github.com/DataDog/integrations-core/blob/master/nifi/assets/service_checks.json
[9]: https://docs.datadoghq.com/help/
