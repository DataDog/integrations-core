# Agent Check: mapr

## Overview

This check monitors [mapr][1] through the Datadog Agent.

## Setup

Follow the instructions below to install and configure this check for an Agent running on a host. For containerized environments, see the [Autodiscovery Integration Templates][2] for guidance on applying these instructions.

### Installation

The mapr check is included in the [Datadog Agent][2] package.
No additional installation is needed on your server.

### Configuration

1. Edit the `mapr.d/conf.yaml` file, in the `conf.d/` folder at the root of your Agent's configuration directory to start collecting your mapr performance data. See the [sample mapr.d/conf.yaml][3] for all available configuration options.

2. [Restart the Agent][4].

### Validation

[Run the Agent's status subcommand][5] and look for `mapr` under the Checks section.

## Data Collected

### Metrics

mapr does not include any metrics.

### Service Checks

mapr does not include any service checks.

### Events

mapr does not include any events.

## Troubleshooting

Need help? Contact [Datadog support][6].

[1]: **LINK_TO_INTEGRATION_SITE**
[2]: https://docs.datadoghq.com/agent/autodiscovery/integrations
[3]: https://github.com/DataDog/integrations-core/blob/master/mapr/datadog_checks/mapr/data/conf.yaml.example
[4]: https://docs.datadoghq.com/agent/guide/agent-commands/?tab=agentv6#start-stop-and-restart-the-agent
[5]: https://docs.datadoghq.com/agent/guide/agent-commands/?tab=agentv6#agent-status-and-information
[6]: https://docs.datadoghq.com/help
