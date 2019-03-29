# Agent Check: Hyper-V

## Overview

This check monitors [Hyper-V][1] through the Datadog Agent.

## Setup

### Installation

The Hyper-V check is included in the [Datadog Agent][2] package. No additional installation is needed on your server.

### Configuration

1. Edit the `hyperv.d/conf.yaml` file, in the `conf.d/` folder at the root of your Agent's configuration directory to collect your Hyper-V performance data. See the [sample hyperv.d/conf.yaml][3] for all available configuration options.

2. [Restart the Agent][4].

### Validation

[Run the Agent's status subcommand][5] and look for `hyperv` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][6] for a list of metrics provided by this integration.

### Service Checks

Hyper-V does not include any service checks.

### Events

Hyper-V does not include any events.

## Troubleshooting

Need help? Contact [Datadog support][7].

[1]: https://docs.microsoft.com/en-us/windows-server/virtualization/hyper-v/hyper-v-on-windows-server
[2]: https://docs.datadoghq.com/agent/basic_agent_usage/windows
[3]: https://github.com/DataDog/integrations-core/blob/master/hyperv/datadog_checks/hyperv/data/conf.yaml.example
[4]: https://docs.datadoghq.com/agent/guide/agent-commands/?tab=agentv6#start-stop-and-restart-the-agent
[5]: https://docs.datadoghq.com/agent/guide/agent-commands/?tab=agentv6#agent-status-and-information
[6]: https://github.com/DataDog/integrations-core/blob/master/hyperv/metadata.csv
[7]: https://docs.datadoghq.com/help
