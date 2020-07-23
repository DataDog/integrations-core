# Btrfs Integration

![BTRFS metric][1]

## Overview

Get metrics from Btrfs in real time to:

- Visualize and monitor Btrfs states.
- Be notified about Btrfs failovers and events.

## Setup

### Installation

The Btrfs check is included in the [Datadog Agent][3] package, so you don't need to install anything else on your servers that use at least one Btrfs filesystem.

### Configuration

1. Configure the Agent according to your needs, edit the `btrfs.d/conf.yaml` file in the `conf.d/` folder at the root of your [Agent's configuration directory][4]. See the [sample btrfs.d/conf.yaml][5] for all available configuration options.

2. [Restart the Agent][6]

### Validation

[Run the Agent's `status` subcommand][7] and look for `btrfs` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][8] for a list of metrics provided by this integration.

### Events

The Btrfs check does not include any events.

### Service Checks

The Btrfs check does not include any service checks.

## Troubleshooting

Need help? Contact [Datadog support][9].

[1]: https://raw.githubusercontent.com/DataDog/integrations-core/master/btrfs/images/btrfs_metric.png
[2]: https://docs.datadoghq.com/agent/kubernetes/integrations/
[3]: https://app.datadoghq.com/account/settings#agent
[4]: https://docs.datadoghq.com/agent/guide/agent-configuration-files/#agent-configuration-directory
[5]: https://github.com/DataDog/integrations-core/blob/master/btrfs/datadog_checks/btrfs/data/conf.yaml.example
[6]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[7]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[8]: https://github.com/DataDog/integrations-core/blob/master/btrfs/metadata.csv
[9]: https://docs.datadoghq.com/help/
