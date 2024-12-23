# Agent Check: Milvus

## Overview

This check monitors [Milvus][1] through the Datadog Agent. It provides insights into your Milvus deployment's performance by collecting information about the latency and number of executions of individual operations. This integration also allows for monitoring the size and ressource allocation of your deployment.

## Setup

### Installation

The Milvus check is included in the [Datadog Agent][2] package.
No additional installation is needed on your server.

### Configuration

#### Host

Follow the instructions below to configure this check for an Agent running on a host. For containerized environments, see the [Containerized](#containerized) section.

<!-- xxx tabs xxx -->
<!-- xxx tab "Host" xxx -->

1. Edit the `milvus.d/conf.yaml` file, in the `conf.d/` folder at the root of your Agent's configuration directory to start collecting your Milvus performance data. See the [sample milvus.d/conf.yaml][4] for all available configuration options.

2. [Restart the Agent][5].

<!-- xxz tab xxx -->
<!-- xxx tab "Containerized" xxx -->

#### Containerized

For containerized environments, see the [Autodiscovery Integration Templates][3] for guidance on applying these instructions.

<!-- xxz tab xxx -->
<!-- xxz tabs xxx -->

### Validation

[Run the Agent's status subcommand][6] and look for `milvus` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][7] for a list of metrics provided by this integration.

### Events

The Milvus integration does not include any events.

### Service Checks

The Milvus integration does not include any service checks.

## Troubleshooting

Need help? Contact [Datadog support][9].


[1]: https://milvus.io/
[2]: https://app.datadoghq.com/account/settings/agent/latest
[3]: https://docs.datadoghq.com/agent/kubernetes/integrations/
[4]: https://github.com/DataDog/integrations-core/blob/master/milvus/datadog_checks/milvus/data/conf.yaml.example
[5]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[6]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[7]: https://github.com/DataDog/integrations-core/blob/master/milvus/metadata.csv
[8]: https://github.com/DataDog/integrations-core/blob/master/milvus/assets/service_checks.json
[9]: https://docs.datadoghq.com/help/
