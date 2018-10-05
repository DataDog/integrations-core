# Btrfs Integration

![BTRFS metric][8]

## Overview

Get metrics from Btrfs service in real time to:

* Visualize and monitor Btrfs states
* Be notified about Btrfs failovers and events.

## Setup
### Installation

The Btrfs check is included in the [Datadog Agent][1] package, so you don't need to install anything else on your servers that use at least one Btrfs filesystem.

### Configuration

1. Configure the Agent according to your needs, edit the `btrfs.d/conf.yaml` file in the `conf.d/` folder at the root of your [Agent's configuration directory][9].
    See the [sample btrfs.d/conf.yaml][2] for all available configuration options.

2. [Restart the Agent][3]

### Validation

[Run the Agent's `status` subcommand][4] and look for `btrfs` under the Checks section.

## Data Collected
### Metrics
See [metadata.csv][5] for a list of metrics provided by this integration.

### Events
The Btrfs check does not include any events at this time.

### Service Checks
The Btrfs check does not include any service checks at this time.

## Troubleshooting
Need help? Contact [Datadog Support][6].

[1]: https://app.datadoghq.com/account/settings#agent
[2]: https://github.com/DataDog/integrations-core/blob/master/btrfs/datadog_checks/btrfs/data/conf.yaml.example
[3]: https://docs.datadoghq.com/agent/faq/agent-commands/#start-stop-restart-the-agent
[4]: https://docs.datadoghq.com/agent/faq/agent-commands/#agent-status-and-information
[5]: https://github.com/DataDog/integrations-core/blob/master/btrfs/metadata.csv
[6]: https://docs.datadoghq.com/help/
[8]: https://raw.githubusercontent.com/DataDog/integrations-core/master/btrfs/images/btrfs_metric.png
[9]: https://docs.datadoghq.com/agent/faq/agent-configuration-files/#agent-configuration-directory
