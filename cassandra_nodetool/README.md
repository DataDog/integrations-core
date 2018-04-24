# Agent Check: Cassandra Nodetool

## Overview

This check collects metrics for your Cassandra cluster that are not available through [jmx integration][1].
It uses the `nodetool` utility to collect them.

## Setup
### Installation

The Cassandra nodetool check is packaged with the Agent, so simply [install the Agent][2] on your cassandra nodes.

### Configuration

Create a file `cassandra_nodetool.yaml` in the Agent's `conf.d` directory. See the [sample cassandra_nodetool.yaml][3] for all available configuration options:

```
init_config:
  # command or path to nodetool (e.g. /usr/bin/nodetool or docker exec container nodetool)
  # can be overwritten on an instance
  # nodetool: /usr/bin/nodetool

instances:

  # the list of keyspaces to monitor
  - keyspaces: []

  # host that nodetool will connect to.
  # host: localhost

  # the port JMX is listening to for connections.
  # port: 7199

  # a set of credentials to connect to the host. These are the credentials for the JMX server.
  # For the check to work, this user must have a read/write access so that nodetool can execute the `status` command
  # username:
  # password:

  # a list of additionnal tags to be sent with the metrics
  # tags: []
```

### Validation

[Run the Agent's `status` subcommand][4] and look for `cassandra_nodetool` under the Checks section:

    Checks
    ======

        cassandra_nodetool
        -----------
          - instance #0 [OK]
          - Collected 39 metrics, 0 events & 7 service checks

## Compatibility

The `cassandra_nodetool` check is compatible with all major platforms

## Data Collected
### Metrics
See [metadata.csv][5] for a list of metrics provided by this integration.

### Events
The Cassandra_nodetool check does not include any event at this time.

### Service Checks

**cassandra.nodetool.node_up**:
The agent sends this service check for each node of the monitored cluster. Returns CRITICAL if the node is down, otherwise OK.

## Troubleshooting
Need help? Contact [Datadog Support][6].

## Further Reading

* [How to monitor Cassandra performance metrics][7]
* [How to collect Cassandra metrics][8]
* [Monitoring Cassandra with Datadog][9]


[1]: https://github.com/DataDog/integrations-core/tree/master/cassandra
[2]: https://app.datadoghq.com/account/settings#agent
[3]: https://github.com/DataDog/integrations-core/blob/master/cassandra_nodetool/conf.yaml.example
[4]: https://docs.datadoghq.com/agent/faq/agent-commands/#agent-status-and-information
[5]: https://github.com/DataDog/integrations-core/blob/master/cassandra_nodetool/metadata.csv
[6]: http://docs.datadoghq.com/help/
[7]: https://www.datadoghq.com/blog/how-to-monitor-cassandra-performance-metrics/
[8]: https://www.datadoghq.com/blog/how-to-collect-cassandra-metrics/
[9]: https://www.datadoghq.com/blog/monitoring-cassandra-with-datadog/
