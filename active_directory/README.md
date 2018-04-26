# active_directory Integration

## Overview

Get metrics from Microsoft Active Directory

* Visualize and monitor Active Directory performance

## Setup
### Installation

Install the `dd-check-active_directory` package manually or with your favorite configuration manager

### Configuration

Edit the `active_directory.yaml` file to collect Active Directory performance data. See the [sample active_directory.yaml][1] for all available configuration options.

### Validation

[Run the Agent's `info` subcommand][2] and look for `active_directory` under the Checks section.

## Data Collected
### Metrics
See [metadata.csv][3] for a list of metrics provided by this integration.

### Events
The active directory check does not include any event at this time.

### Service Checks
The active directory check does not include any service check at this time.


[1]: https://github.com/DataDog/integrations-core/blob/master/active_directory/conf.yaml.example
[2]: https://help.datadoghq.com/hc/en-us/articles/203764635-Agent-Status-and-Information
[3]: https://github.com/DataDog/integrations-core/blob/master/active_directory/metadata.csv
