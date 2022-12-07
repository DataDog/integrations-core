# Agent Check: Datadog Cluster Agent

## Overview

This check monitors the [Datadog Cluster Agent][1] through the Datadog Agent.

## Setup

Follow the instructions below to install and configure this check for an Agent running on a host. For containerized environments, see the [Autodiscovery Integration Templates][2] for guidance on applying these instructions.

### Installation

The Datadog-Cluster-Agent check is included in the [Datadog Agent][2] package.
No additional installation is needed on your server.

### Configuration

1. Edit the `datadog_cluster_agent.d/conf.yaml` file, in the `conf.d/` folder at the root of your Agent's configuration directory to start collecting your datadog_cluster_agent performance data. See the [sample datadog_cluster_agent.d/conf.yaml][3] for all available configuration options.

2. [Restart the Agent][4].

### Validation

[Run the Agent's status subcommand][5] and look for `datadog_cluster_agent` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][6] for a list of metrics provided by this check.

### Events

The Datadog-Cluster-Agent integration does not include any events.

### Service Checks

See [service_checks.json][7] for a list of service checks provided by this integration.

## Troubleshooting

Need help? Contact [Datadog support][8].


[1]: https://docs.datadoghq.com/agent/cluster_agent/
[2]: https://docs.datadoghq.com/agent/kubernetes/integrations/
[3]: https://github.com/DataDog/integrations-core/blob/master/datadog_cluster_agent/datadog_checks/datadog_cluster_agent/data/conf.yaml.example
[4]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[5]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[6]: https://github.com/DataDog/integrations-core/blob/master/datadog_cluster_agent/metadata.csv
[7]: https://github.com/DataDog/integrations-core/blob/master/datadog_cluster_agent/assets/service_checks.json
[8]: https://docs.datadoghq.com/help/
