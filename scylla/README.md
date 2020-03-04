# Agent Check: Scylla

## Overview

This Datadog-[Scylla][1] integration collects a majority of the exposed metrics by default, with the ability to customize additional groups based on specific user needs.

Scylla is an open-source NoSQL data store that can act as "a drop-in Apache Cassandra alternative." It has rearchitected the Cassandra model tuned for modern hardware, reducing the size of required clusters while improving theoretical throughput and performance.

## Setup

Follow the instructions below to install and configure this check for an Agent running on a host.

### Installation

The Scylla check is included in the [Datadog Agent][2] package. No additional installation is needed on your server.

### Configuration

1. Edit the `scylla.d/conf.yaml` file, in the `conf.d/` folder at the root of your Agent's configuration directory to start collecting your scylla performance data. See the [sample scylla.d/conf.yaml][3] for all available configuration options.

2. [Restart the Agent][4].

### Validation

[Run the Agent's status subcommand][5] and look for `scylla` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][6] for a list of metrics provided by this check.

### Service Checks

`scylla.prometheus.health`: Returns `CRITICAL` if the Agent cannot reach the metrics endpoints, `OK` otherwise.

### Events

The Scylla check does not include any events.

## Troubleshooting

Need help? Contact [Datadog support][7].

[1]: https://scylladb.com
[2]: https://docs.datadoghq.com/agent
[3]: https://github.com/DataDog/integrations-core/blob/master/scylla/datadog_checks/scylla/data/conf.yaml.example
[4]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[5]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[6]: https://github.com/DataDog/integrations-core/blob/master/scylla/metadata.csv
[7]: https://docs.datadoghq.com/help
