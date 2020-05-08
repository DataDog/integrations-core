# Disk Check

## Overview

Collect metrics related to disk usage and IO.

## Setup

### Installation

The disk check is included in the [Datadog Agent][1] package, so you don't need to install anything else on your server.

### Configuration

The disk check is enabled by default, and the Agent collects metrics on all local partitions.
If you want to configure the check with custom options, Edit the `disk.d/conf.yaml` file, in the `conf.d/` folder at the root of your [Agent's configuration directory][2]. See the [sample disk.d/conf.yaml][3] for all available configuration options.

### Validation

[Run the Agent's `status` subcommand][4] and look for `disk` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][5] for a list of metrics provided by this integration.

### Events

The Disk check does not include any events.

### Service Checks

**`disk.read_write`**:
Returns `CRITICAL` if filesystem is in read-only mode.

## Troubleshooting

Need help? Contact [Datadog support][6].

[1]: https://app.datadoghq.com/account/settings#agent
[2]: https://docs.datadoghq.com/agent/guide/agent-configuration-files/#agent-configuration-directory
[3]: https://github.com/DataDog/integrations-core/blob/master/disk/datadog_checks/disk/data/conf.yaml.example
[4]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[5]: https://github.com/DataDog/integrations-core/blob/master/disk/metadata.csv
[6]: https://docs.datadoghq.com/help/
