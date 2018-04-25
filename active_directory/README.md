# active_directory Integration

## Overview

Get metrics from Microsoft Active Directory

* Visualize and monitor Active Directory performance

## Setup
### Installation

Install the `dd-check-active_directory` package manually or with your favorite configuration manager

### Configuration

Edit the `active_directory.yaml` file to collect Active Directory performance data. See the [sample active_directory.yaml](https://github.com/DataDog/integrations-core/blob/master/active_directory/conf.yaml.example) for all available configuration options.

### Validation

[Run the Agent's `info` subcommand](https://help.datadoghq.com/hc/en-us/articles/203764635-Agent-Status-and-Information) and look for `active_directory` under the Checks section.

## Compatibility

The ative_directory check is compatible with Windows.

## Data Collected
### Metrics
See [metadata.csv](https://github.com/DataDog/integrations-core/blob/master/active_directory/metadata.csv) for a list of metrics provided by this integration.

### Events
The active directory check does not include any event at this time.

### Service Checks
The active directory check does not include any service check at this time.
