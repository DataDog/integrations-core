# Agent Check: Cassandra Nodetool

![Cassandra default dashboard][111]

## Overview

This check collects metrics for your Cassandra cluster that are not available through [jmx integration][112]. It uses the `nodetool` utility to collect them.

## Setup

### Installation

The Cassandra Nodetool check is included in the [Datadog Agent][113] package, so you don't need to install anything else on your Cassandra nodes.

### Configuration

Follow the instructions below to configure this check for an Agent running on a host. For containerized environments, see the [Containerized](#containerized) section.

#### Host

1. Edit the file `cassandra_nodetool.d/conf.yaml` in the `conf.d/` folder at the root of your [Agent's configuration directory][114]. See the [sample cassandra_nodetool.d/conf.yaml][115] for all available configuration options:

    ```yaml
      init_config:

      instances:

          ## @param keyspaces - list of string - required
          ## The list of keyspaces to monitor.
          ## An empty list results in no metrics being sent.
          #
        - keyspaces:
            - <KEYSPACE_1>
            - <KEYSPACE_2>
    ```

2. [Restart the Agent][116]

#### Containerized

For containerized environments, see the [Autodiscovery Integration Templates][117] for guidance on applying the parameters below.

##### Metric collection

| Parameter            | Value                                                               |
|----------------------|---------------------------------------------------------------------|
| `<INTEGRATION_NAME>` | `cassandra_nodetool`                                                |
| `<INIT_CONFIG>`      | blank or `{}`                                                       |
| `<INSTANCE_CONFIG>`  | `{"keyspaces": ["<KEYSPACE_1>","<KEYSPACE_2>], "host":"%%hosts%%"}` |

### Validation

[Run the Agent's `status` subcommand][118] and look for `cassandra_nodetool` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][119] for a list of metrics provided by this integration.

### Events

The Cassandra_nodetool check does not include any events.

### Service Checks

**cassandra.nodetool.node_up**:
The agent sends this service check for each node of the monitored cluster. Returns CRITICAL if the node is down, otherwise OK.

## Troubleshooting

Need help? Contact [Datadog support][1110].

## Further Reading

* [How to monitor Cassandra performance metrics][1111]
* [How to collect Cassandra metrics][1112]
* [Monitoring Cassandra with Datadog][1113]

[111]: https://raw.githubusercontent.com/DataDog/integrations-core/master/cassandra_nodetool/images/cassandra_dashboard.png
[112]: https://github.com/DataDog/integrations-core/tree/master/cassandra
[113]: https://app.datadoghq.com/account/settings#agent
[114]: https://docs.datadoghq.com/agent/guide/agent-configuration-files/#agent-configuration-directory
[115]: https://github.com/DataDog/integrations-core/blob/master/cassandra_nodetool/datadog_checks/cassandra_nodetool/data/conf.yaml.example
[116]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[117]: https://docs.datadoghq.com/agent/autodiscovery/integrations
[118]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[119]: https://github.com/DataDog/integrations-core/blob/master/cassandra_nodetool/metadata.csv
[1110]: https://docs.datadoghq.com/help
[1111]: https://www.datadoghq.com/blog/how-to-monitor-cassandra-performance-metrics
[1112]: https://www.datadoghq.com/blog/how-to-collect-cassandra-metrics
[1113]: https://www.datadoghq.com/blog/monitoring-cassandra-with-datadog
