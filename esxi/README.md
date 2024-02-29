# Agent Check: ESXi

## Overview

This check monitors [ESXi][1] hosts and the virtual machines running on them through the Datadog Agent.

## Setup

Follow the instructions below to install and configure this check for an Agent running on a host. For containerized environments, see the [Autodiscovery Integration Templates][3] for guidance on applying these instructions.

### Installation

The ESXi check is included in the [Datadog Agent][2] package.
No additional installation is needed on your server.

### Configuration

1. Edit the `esxi.d/conf.yaml` file, in the `conf.d/` folder at the root of your Agent's configuration directory to start collecting your esxi performance data. See the [sample esxi.d/conf.yaml][4] for all available configuration options.

2. [Restart the Agent][5].

### Validation

[Run the Agent's status subcommand][6] and look for `esxi` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][7] for a list of metrics provided by this integration.

### Events

The ESXi integration does not include any events.

### Service Checks

The ESXi integration does not include any service checks.

## Troubleshooting

Need help? Contact [Datadog support][9].


[1]: https://www.vmware.com/products/esxi-and-esx.html
[2]: https://app.datadoghq.com/account/settings/agent/latest
[3]: https://docs.datadoghq.com/agent/kubernetes/integrations/
[4]: https://github.com/DataDog/integrations-core/blob/master/esxi/datadog_checks/esxi/data/conf.yaml.example
[5]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[6]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[7]: https://github.com/DataDog/integrations-core/blob/master/esxi/metadata.csv
[8]: https://github.com/DataDog/integrations-core/blob/master/esxi/assets/service_checks.json
[9]: https://docs.datadoghq.com/help/
