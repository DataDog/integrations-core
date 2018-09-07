# Disk Check

## Overview

Collect metrics related to disk usage and IO.

## Setup
### Installation

The disk check is included in the [Datadog Agent][1] package, so you don't need to install anything else on your server.

### Configuration

The disk check is enabled by default, and the Agent collects metrics on all local partitions.
If you want to configure the check with custom options, Edit the `disk.d/conf.yaml` file, in the `conf.d/` folder at the root of your [Agent's configuration directory][6]. See the [sample disk.d/conf.yaml][2] for all available configuration options.

### Validation

[Run the Agent's `status` subcommand][3] and look for `disk` under the Checks section.

## Data Collected
### Metrics

See [metadata.csv][4] for a list of metrics provided by this integration.

### Events
The Disk check does not include any events at this time.

### Service Checks

**`disk.service_check_rw`**:
Returns `CRITICAL` if filesystem is in read-only mode.

## Troubleshooting
Need help? Contact [Datadog Support][5].

[1]: https://app.datadoghq.com/account/settings#agent
[2]: https://github.com/DataDog/integrations-core/blob/master/disk/datadog_checks/disk/data/conf.yaml.default
[3]: https://docs.datadoghq.com/agent/faq/agent-commands/#agent-status-and-information
[4]: https://github.com/DataDog/integrations-core/blob/master/disk/metadata.csv
[5]: https://docs.datadoghq.com/help/
[6]: https://docs.datadoghq.com/agent/faq/agent-configuration-files/#agent-configuration-directory
