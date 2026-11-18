# Agent Check: InterSystems IRIS

## Overview

This check monitors [InterSystems IRIS][1] through the Datadog Agent.

InterSystems IRIS is a data platform combining a multi-model database, an interoperability engine, and an analytics layer. This integration collects metrics from the `/api/monitor/metrics` OpenMetrics endpoint built into IRIS, so no additional instrumentation is required.

The collected metrics cover distributed cache (ECP) and mirroring topology, interoperability productions and queues, write daemon and journaling throughput, cache and database efficiency, SQL activity, processes and work queues, and host-level CPU, disk, and license consumption.

## Setup

Follow the instructions below to install and configure this check for an Agent running on a host. For containerized environments, see the [Autodiscovery integration templates][3] for guidance on applying these instructions.

### Installation

The InterSystems IRIS check is included in the [Datadog Agent][2] package.
No additional installation is needed on your server.

### Configuration

1. Edit the `intersystems_iris.d/conf.yaml` file, in the `conf.d/` folder at the root of your Agent's configuration directory to start collecting your InterSystems IRIS performance data. See the [sample intersystems_iris.d/conf.yaml][4] for all available configuration options.

2. [Restart the Agent][5].

### Validation

[Run the Agent's status subcommand][6] and look for `intersystems_iris` under the Checks section.

## Data collected

### Metrics

See [metadata.csv][7] for a list of metrics provided by this integration.

### Events

The InterSystems IRIS integration does not include any events.

### Service checks

See [service_checks.json][8] for a list of service checks provided by this integration.

## Troubleshooting

Need help? Contact [Datadog support][9].


[1]: https://www.intersystems.com/products/intersystems-iris/
[2]: https://app.datadoghq.com/account/settings/agent/latest
[3]: https://docs.datadoghq.com/containers/kubernetes/integrations/
[4]: https://github.com/DataDog/integrations-core/blob/master/intersystems_iris/datadog_checks/intersystems_iris/data/conf.yaml.example
[5]: https://docs.datadoghq.com/agent/configuration/agent-commands/#start-stop-and-restart-the-agent
[6]: https://docs.datadoghq.com/agent/configuration/agent-commands/#agent-status-and-information
[7]: https://github.com/DataDog/integrations-core/blob/master/intersystems_iris/metadata.csv
[8]: https://github.com/DataDog/integrations-core/blob/master/intersystems_iris/assets/service_checks.json
[9]: https://docs.datadoghq.com/help/
