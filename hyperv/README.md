# Agent Check: Hyper-V

## Overview

This check monitors [Hyper-V][1].

## Setup

### Installation

The Hyperv check is included in the [Datadog Agent][2] package, so you do not
need to install anything else on your server.

### Configuration

1. Edit the `hyperv.d/conf.yaml` file, in the `conf.d/` folder at the root of your
   Agent's configuration directory to start collecting your hyperv performance data.
   See the [sample hyperv.d/conf.yaml][2] for all available configuration options.

2. [Restart the Agent][3]

### Validation

[Run the Agent's `status` subcommand][4] and look for `hyperv` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][5] for a list of metrics provided by this integration.

### Service Checks

Hyper-V does not include any service checks.

### Events

Hyper-V does not include any events.

## Troubleshooting

Need help? Contact [Datadog Support][6].

[1]: https://docs.microsoft.com/en-us/windows-server/virtualization/hyper-v/hyper-v-on-windows-server
[2]: https://github.com/DataDog/integrations-core/blob/master/hyperv/datadog_checks/hyperv/data/conf.yaml.example
[3]: https://docs.datadoghq.com/agent/faq/agent-commands/#start-stop-restart-the-agent
[4]: https://docs.datadoghq.com/agent/faq/agent-commands/#agent-status-and-information
[5]: https://github.com/DataDog/integrations-core/blob/master/hyperv/metadata.csv
[6]: https://docs.datadoghq.com/help/
