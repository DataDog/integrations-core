# exchange_check Integration

## Overview

Get metrics from Microsoft Exchange Server

* Visualize and monitor Exchange server performance

## Setup
### Installation

The Exchange check is packaged with the Agent, so simply [install the Agent][1] on your servers.

### Configuration

Edit the `exchange_server.yaml` file to collect Exchange Server performance data. See the [sample exchange_server.yaml][2] for all available configuration options.

### Validation

[Run the Agent's `status` subcommand][3] and look for `exchange_server` under the Checks section:

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
See [metadata.csv][4] for a list of metrics provided by this integration.

### Events
The exchange server check does not include any events at this time.

### Service Checks
The exchange server check does not include any service check at this time.


[1]: https://app.datadoghq.com/account/settings#agent
[2]: https://github.com/DataDog/integrations-core/blob/master/exchange_server/conf.yaml.example
[3]: https://docs.datadoghq.com/agent/faq/agent-commands/#agent-status-and-information
[4]: https://github.com/DataDog/integrations-core/blob/master/exchange_server/metadata.csv
