# Btrfs Integration

![BTRFS metric][1]

## Overview

Get metrics from Btrfs in real time to:

- Visualize and monitor Btrfs states.

## Setup

### Installation

The Btrfs check is included in the [Datadog Agent][2] package, so you don't need to install anything else on your servers that use at least one Btrfs filesystem.

### Configuration

1. Edit the `btrfs.d/conf.yaml` file in the `conf.d/` folder at the root of your [Agent's configuration directory][3]. See the [sample btrfs.d/conf.yaml][4] for all available configuration options.

2. [Restart the Agent][5].

### Validation

[Run the Agent's status subcommand][6] and look for `btrfs` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][7] for a list of metrics provided by this integration.

### Events

The Btrfs check does not include any events.

### Service Checks

The Btrfs check does not include any service checks.

## Troubleshooting

Need help? Contact [Datadog support][8].

[1]: https://raw.githubusercontent.com/DataDog/integrations-core/master/btrfs/images/btrfs_metric.png
[2]: https://app.datadoghq.com/account/settings/agent/latest
[3]: https://docs.datadoghq.com/agent/guide/agent-configuration-files/#agent-configuration-directory
[4]: https://github.com/DataDog/integrations-core/blob/master/btrfs/datadog_checks/btrfs/data/conf.yaml.example
[5]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[6]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[7]: https://github.com/DataDog/integrations-core/blob/master/btrfs/metadata.csv
[8]: https://docs.datadoghq.com/help/
