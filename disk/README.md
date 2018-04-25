# Disk Check

## Overview

Collect metrics related to disk usage and IO.

## Setup
### Installation

The disk check is packaged with the Agent, so simply [install the Agent](https://app.datadoghq.com/account/settings#agent) anywhere you wish to use it.

### Configuration

The disk check is enabled by default, and the Agent will collect metrics on all local partitions. If you want to configure the check with custom options, create a file `disk.yaml` in the Agent's `conf.d` directory. See the [sample disk.yaml](https://github.com/DataDog/integrations-core/blob/master/disk/conf.yaml.default) for all available configuration options.

### Validation

[Run the Agent's `status` subcommand](https://docs.datadoghq.com/agent/faq/agent-commands/#agent-status-and-information) and look for `disk` under the Checks section.

## Data Collected
### Metrics

See [metadata.csv](https://github.com/DataDog/integrations-core/blob/master/disk/metadata.csv) for a list of metrics provided by this integration.

### Events
The Disk check does not include any event at this time.

### Service Checks
The Disk check does not include any service check at this time.

## Troubleshooting
Need help? Contact [Datadog Support](http://docs.datadoghq.com/help/).

## Further Reading
Learn more about infrastructure monitoring and all our integrations on [our blog](https://www.datadoghq.com/blog/)
