# Disk Check

## Overview

Collect metrics related to disk usage and IO.

## Setup

### Installation

The disk check is included in the [Datadog Agent][1] package, so you don't need to install anything else on your server.

### Configuration

The Disk check is enabled by default, and the Agent collects metrics on all local partitions. To configure the check with custom options, edit the `disk.d/conf.yaml` file, in the `conf.d/` folder at the root of your [Agent's configuration directory][2]. See the [sample disk.d/conf.yaml][3] for all available configuration options.

#### Note for Windows hosts
The Agent requires Administrator permissions to collect mount point metrics on hosts running Windows. To collect these metrics without granting Administrator permissions, use the [PDH check][4] to collect mount point metrics from the corresponding perf counters. 

### Validation

[Run the Agent's `status` subcommand][5] and look for `disk` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][6] for a list of metrics provided by this integration.

### Events

The Disk check does not include any events.

### Service Checks

See [service_checks.json][7] for a list of service checks provided by this integration.

## Troubleshooting

Need help? Contact [Datadog support][8].


[1]: https://app.datadoghq.com/account/settings#agent
[2]: https://docs.datadoghq.com/agent/guide/agent-configuration-files/#agent-configuration-directory
[3]: https://github.com/DataDog/integrations-core/blob/master/disk/datadog_checks/disk/data/conf.yaml.default
[4]: https://docs.datadoghq.com/integrations/pdh_check/#pagetitle
[5]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[6]: https://github.com/DataDog/integrations-core/blob/master/disk/metadata.csv
[7]: https://github.com/DataDog/integrations-core/blob/master/disk/assets/service_checks.json
[8]: https://docs.datadoghq.com/help/
