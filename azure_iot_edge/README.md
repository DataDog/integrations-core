# Agent Check: Azure IoT Edge

## Overview

This check monitors [Azure IoT Edge][1] through the Datadog Agent.

## Setup

Follow the instructions below to install and configure this check for an Agent running on a host. For containerized environments, see the [Autodiscovery Integration Templates][2] for guidance on applying these instructions.

### Installation

The Azure IoT Edge check is included in the [Datadog Agent][2] package.
No additional installation is needed on your server.

### Configuration

1. Edit the `azure_iot_edge.d/conf.yaml` file, in the `conf.d/` folder at the root of your Agent's configuration directory to start collecting your azure_iot_edge performance data. See the [sample azure_iot_edge.d/conf.yaml][3] for all available configuration options.

2. [Restart the Agent][4].

### Validation

[Run the Agent's status subcommand][5] and look for `azure_iot_edge` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][6] for a list of metrics provided by this check.

### Service Checks

Azure IoT Edge does not include any service checks.

### Events

Azure IoT Edge does not include any events.

## Troubleshooting

Need help? Contact [Datadog support][7].

[1]: **LINK_TO_INTEGRATION_SITE**
[2]: https://docs.datadoghq.com/agent/kubernetes/integrations/
[3]: https://github.com/DataDog/integrations-core/blob/master/azure_iot_edge/datadog_checks/azure_iot_edge/data/conf.yaml.example
[4]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[5]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[6]: https://github.com/DataDog/integrations-core/blob/master/azure_iot_edge/metadata.csv
[7]: https://docs.datadoghq.com/help/
