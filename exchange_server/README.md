# exchange_check Integration

## Overview

Get metrics from Microsoft Exchange Server

* Visualize and monitor Exchange server performance

## Setup
### Installation

The Exchange check is included in the [Datadog Agent][1] package, so you don't need to install anything else on your servers.

### Configuration

1. Edit the `exchange_server.d/conf.yaml` file, in the `conf.d/` folder at the root of your Agent's directory to start collecting your Exchange Server performance data.  
    See the [sample exchange_server.d/conf.yaml][2] for all available configuration options.

2. [Restart the Agent][5]

### Validation

[Run the Agent's `status` subcommand][3] and look for `exchange_server` under the Checks section.

## Data Collected
### Metrics
See [metadata.csv][4] for a list of metrics provided by this integration.

### Events
The Exchange server check does not include any events at this time.

### Service Checks
The Exchange server check does not include any service checks at this time.


[1]: https://app.datadoghq.com/account/settings#agent
[2]: https://github.com/DataDog/integrations-core/blob/master/exchange_server/datadog_checks/exchange_server/data/conf.yaml.example
[3]: https://docs.datadoghq.com/agent/faq/agent-commands/#agent-status-and-information
[4]: https://github.com/DataDog/integrations-core/blob/master/exchange_server/metadata.csv
[5]: https://docs.datadoghq.com/agent/faq/agent-commands/#start-stop-restart-the-agent


