# Btrfs Integration
{{< img src="integrations/btrfs/btrfs_metric.png" alt="btrfs metric" responsive="true" popup="true">}}
## Overview

Get metrics from Btrfs service in real time to:

* Visualize and monitor Btrfs states
* Be notified about Btrfs failovers and events.

## Setup
### Installation

The Btrfs check is included in the [Datadog Agent][4] package, so you don't need to install anything else on your servers that use at least one Btrfs filesystem.

### Configuration

1. Configure the Agent according to your needs, edit the `btrfs.d/conf.yaml` file in the `conf.d/` folder at the root of your Agent's configuration directory.
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

## Further Reading

Learn more about infrastructure monitoring and all our integrations on [our blog][7]


[1]: https://app.datadoghq.com/account/settings#agent
[2]: https://github.com/DataDog/integrations-core/blob/master/btrfs/datadog_checks/btrfs/data/conf.yaml.example
[3]: https://docs.datadoghq.com/agent/faq/agent-commands/#start-stop-restart-the-agent
[4]: https://docs.datadoghq.com/agent/faq/agent-commands/#agent-status-and-information
[5]: https://github.com/DataDog/integrations-core/blob/master/btrfs/metadata.csv
[6]: http://docs.datadoghq.com/help/
[7]: https://www.datadoghq.com/blog/
