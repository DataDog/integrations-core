# Agent Check: Aerospike

## Overview

Get metrics from Aerospike Database in real time to:

* Visualize and monitor Aerospike states
* Be notified about Aerospike failovers and events.

Note: Authentication and TLS are not supported.

## Setup

### Installation

The Aerospike check is included in the [Datadog Agent][2] package.
No additional installation is needed on your server.

### Configuration

1. Edit the `aerospike.d/conf.yaml` file, in the `conf.d/` folder at the root of your Agent's configuration directory to start collecting your aerospike performance data. See the [sample aerospike.d/conf.yaml][2] for all available configuration options.

2. [Restart the Agent][3].

### Validation

[Run the Agent's status subcommand][4] and look for `aerospike` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][5] for a list of metrics provided by this integration.

### Service Checks

Aerospike does not include any service checks.

### Events

Aerospike does not include any events.

## Troubleshooting

Need help? Contact [Datadog support][6].

[1]: https://www.aerospike.com/products/aerospike-database-platform
[2]: https://github.com/DataDog/integrations-core/blob/master/aerospike/datadog_checks/aerospike/data/conf.yaml.example
[3]: https://docs.datadoghq.com/agent/faq/agent-commands/#start-stop-restart-the-agent
[4]: https://docs.datadoghq.com/agent/faq/agent-commands/#agent-status-and-information
[5]: https://github.com/DataDog/integrations-core/blob/master/aerospike/metadata.csv
[6]: https://docs.datadoghq.com/help
