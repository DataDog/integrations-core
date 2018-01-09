# exchange_check Integration

## Overview

Get metrics from Microsoft Exchange Server

* Visualize and monitor Exchange server performance

## Setup
### Installation

Install the `dd-check-exchange_server` package manually or with your favorite configuration manager

### Configuration

Edit the `exchange_server.yaml` file to collect Exchange Server performance data. See the [sample exchange_server.yaml](https://github.com/DataDog/integrations-core/blob/master/exchange_server/conf.yaml.example) for all available configuration options.

### Validation

[Run the Agent's `info` subcommand](https://help.datadoghq.com/hc/en-us/articles/203764635-Agent-Status-and-Information) and look for `exchange_server` under the Checks section:

    Checks
    ======

        exchange_server
        -----------
          - instance #0 [OK]
          - Collected 39 metrics, 0 events & 7 service checks

## Compatibility

The exchange_server check is compatible with Windows.

## Data Collected
### Metrics
See [metadata.csv](https://github.com/DataDog/integrations-core/blob/master/exchange_server/metadata.csv) for a list of metrics provided by this integration.

### Events
The exchange server check does not include any events at this time.

### Service Checks
The exchange server check does not include any service check at this time.