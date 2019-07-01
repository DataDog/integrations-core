# Agent Check: Aerospike

## Overview

Get metrics from Aerospike Database in real time to:

* Visualize and monitor Aerospike states
* Be notified about Aerospike failovers and events.

## Setup

### Installation

The Aerospike check is included in the [Datadog Agent][1] package.
No additional installation is needed on your server.

### Configuration

1. Edit the `aerospike.d/conf.yaml` file, in the `conf.d/` folder at the root of your Agent's configuration directory to start collecting your aerospike performance data. See the [sample aerospike.d/conf.yaml][1] for all available configuration options.

2. [Restart the Agent][2].

### Validation

[Run the Agent's status subcommand][3] and look for `aerospike` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][4] for a list of metrics provided by this integration.

### Service Checks

- `aerospike.can_connect`
- `aerospike.cluster_up`

### Events

Aerospike does not include any events.

## Troubleshooting

Need help? Contact [Datadog support][5].

[1]: https://github.com/DataDog/integrations-core/blob/master/aerospike/datadog_checks/aerospike/data/conf.yaml.example
[2]: https://docs.datadoghq.com/agent/guide/agent-commands/?tab=agentv6#start-stop-and-restart-the-agent
[3]: https://docs.datadoghq.com/agent/guide/agent-commands/?tab=agentv6#agent-status-and-information
[4]: https://github.com/DataDog/integrations-core/blob/master/aerospike/metadata.csv
[5]: https://docs.datadoghq.com/help
