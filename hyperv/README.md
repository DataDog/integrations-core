# Agent Check: Hyper-V

## Overview

This check monitors [Hyper-V][1] through the Datadog Agent.

## Setup
### Installation

The Hyper-V check is included in the [Datadog Agent][3] package. No additional installation is needed on your server.

### Configuration

1. Edit the `hyperv.d/conf.yaml` file, in the `conf.d/` folder at the root of your Agent's configuration directory to collect your Hyper-V performance data. See the [sample hyperv.d/conf.yaml][4] for all available configuration options.

2. [Restart the Agent][5].

### Validation

[Run the Agent's status subcommand][6] and look for `hyperv` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][7] for a list of metrics provided by this integration.

### Service Checks

Hyper-V does not include any service checks.

### Events

Hyper-V does not include any events.

## Troubleshooting

Need help? Contact [Datadog support][8].

## Further Reading

Additional helpful documentation, links, and articles:

* [Monitor Microsoft Hyper-V with Datadog][9]

[1]: https://docs.microsoft.com/en-us/windows-server/virtualization/hyper-v/hyper-v-on-windows-server
[3]: https://docs.datadoghq.com/agent/basic_agent_usage/windows
[4]: https://github.com/DataDog/integrations-core/blob/master/hyperv/datadog_checks/hyperv/data/conf.yaml.example
[5]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[6]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[7]: https://github.com/DataDog/integrations-core/blob/master/hyperv/metadata.csv
[8]: https://docs.datadoghq.com/help
[9]: https://www.datadoghq.com/blog/monitor-microsoft-hyperv-with-datadog
