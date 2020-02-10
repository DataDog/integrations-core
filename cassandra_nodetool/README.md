# Agent Check: Cassandra Nodetool

![Cassandra default dashboard][111]

## Overview

This check collects metrics for your Cassandra cluster that are not available through [jmx integration][112]. It uses the `nodetool` utility to collect them.

## Setup

### Installation

The Cassandra Nodetool check is included in the [Datadog Agent][113] package, so you don't need to install anything else on your Cassandra nodes.

### Configuration

1. Edit the file `cassandra_nodetool.d/conf.yaml` in the `conf.d/` folder at the root of your [Agent's configuration directory][114]. See the [sample cassandra_nodetool.d/conf.yaml][115] for all available configuration options:

   ```yaml
   init_config:

   instances:
     ## @param keyspaces - list of string - required
     ## The list of keyspaces to monitor.
     ## An empty list results in no metrics being sent.
     #
     - keyspaces:
         - "<KEYSPACE_1>"
         - "<KEYSPACE_2>"
   ```

2. [Restart the Agent][116].

### Validation

[Run the Agent's `status` subcommand][117] and look for `cassandra_nodetool` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][118] for a list of metrics provided by this integration.

### Events

The Cassandra_nodetool check does not include any events.

### Service Checks

**cassandra.nodetool.node_up**:
The agent sends this service check for each node of the monitored cluster. Returns CRITICAL if the node is down, otherwise OK.

## Troubleshooting

Need help? Contact [Datadog support][119].

## Further Reading

- [How to monitor Cassandra performance metrics][1110]
- [How to collect Cassandra metrics][1111]
- [Monitoring Cassandra with Datadog][1112]

[111]: https://raw.githubusercontent.com/DataDog/integrations-core/master/cassandra_nodetool/images/cassandra_dashboard.png
[112]: https://github.com/DataDog/integrations-core/tree/master/cassandra
[113]: https://app.datadoghq.com/account/settings#agent
[114]: https://docs.datadoghq.com/agent/guide/agent-configuration-files/#agent-configuration-directory
[115]: https://github.com/DataDog/integrations-core/blob/master/cassandra_nodetool/datadog_checks/cassandra_nodetool/data/conf.yaml.example
[116]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[117]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[118]: https://github.com/DataDog/integrations-core/blob/master/cassandra_nodetool/metadata.csv
[119]: https://docs.datadoghq.com/help
[1110]: https://www.datadoghq.com/blog/how-to-monitor-cassandra-performance-metrics
[1111]: https://www.datadoghq.com/blog/how-to-collect-cassandra-metrics
[1112]: https://www.datadoghq.com/blog/monitoring-cassandra-with-datadog
