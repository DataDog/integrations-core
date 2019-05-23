# Agent Check: harbor

## Overview

This check monitors [harbor][1] through the Datadog Agent.

## Setup

### Installation

The harbor check is included in the [Datadog Agent][2] package.
No additional installation is needed on your server.

### Configuration

1. Edit the `harbor.d/conf.yaml` file, in the `conf.d/` folder at the root of your Agent's configuration directory to start collecting your harbor performance data. See the [sample harbor.d/conf.yaml][2] for all available configuration options.

2. [Restart the Agent][3].

### Validation

[Run the Agent's status subcommand][4] and look for `harbor` under the Checks section.

## Data Collected

### Metrics

harbor does not include any metrics.

### Service Checks

harbor does not include any service checks.

### Events

harbor does not include any events.

## Troubleshooting

Need help? Contact [Datadog support][5].

[1]: **LINK_TO_INTEGRATION_SITE**
[2]: https://github.com/DataDog/integrations-core/blob/master/harbor/datadog_checks/harbor/data/conf.yaml.example
[3]: https://docs.datadoghq.com/agent/guide/agent-commands/?tab=agentv6#start-stop-and-restart-the-agent
[4]: https://docs.datadoghq.com/agent/guide/agent-commands/?tab=agentv6#agent-status-and-information
[5]: https://docs.datadoghq.com/help
