# Agent Check: {integration_name}

## Overview

This check monitors [{integration_name}][1] through the Datadog Agent.

## Setup

Follow the instructions below to install and configure this check for an Agent running on a host. For containerized environments, see the [Autodiscovery Integration Templates][2] for guidance on applying these instructions.

### Installation

{install_info}

### Configuration

1. Edit the `{check_name}.d/conf.yaml` file, in the `conf.d/` folder at the root of your Agent's configuration directory to start collecting your {check_name} performance data. See the [sample {check_name}.d/conf.yaml][3] for all available configuration options.

2. [Restart the Agent][4].

### Validation

[Run the Agent's status subcommand][5] and look for `{check_name}` under the Checks section.

## Data Collected

### Metrics

{integration_name} does not include any metrics.

### Service Checks

{integration_name} does not include any service checks.

### Events

{integration_name} does not include any events.

## Troubleshooting

Need help? Contact [Datadog support][6].

[1]: **LINK_TO_INTEGRATION_SITE**
[2]: https://docs.datadoghq.com/agent/autodiscovery/integrations
[3]: https://github.com/DataDog/integrations-core/blob/master/{check_name}/datadog_checks/{check_name}/data/conf.yaml.example
[4]: https://docs.datadoghq.com/agent/guide/agent-commands/?tab=agentv6#start-stop-and-restart-the-agent
[5]: https://docs.datadoghq.com/agent/guide/agent-commands/?tab=agentv6#agent-status-and-information
[6]: https://docs.datadoghq.com/help
