# Agent Check: Cassandra Nodetool

![Cassandra default dashboard][1]

## Overview

This check collects metrics for your Cassandra cluster that are not available through [jmx integration][2].
It uses the `nodetool` utility to collect them.

## Setup
### Installation

The Cassandra Nodetool check is included in the [Datadog Agent][3] package, so you don't need to install anything else on your Cassandra nodes.

### Configuration

Edit the file `cassandra_nodetool.d/conf.yaml` in the `conf.d/` folder at the root of your [Agent's configuration directory][4].
See the [sample cassandra_nodetool.d/conf.yaml][5] for all available configuration options:

```yaml
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

  # a list of additional tags to be sent with the metrics
  # tags: []
```

### Validation

[Run the Agent's `status` subcommand][6] and look for `cassandra_nodetool` under the Checks section.

## Data Collected
### Metrics
See [metadata.csv][7] for a list of metrics provided by this integration.

### Events
The Cassandra_nodetool check does not include any events at this time.

### Service Checks

**cassandra.nodetool.node_up**:
The agent sends this service check for each node of the monitored cluster. Returns CRITICAL if the node is down, otherwise OK.

## Troubleshooting
Need help? Contact [Datadog Support][8].

## Further Reading

* [How to monitor Cassandra performance metrics][9]
* [How to collect Cassandra metrics][10]
* [Monitoring Cassandra with Datadog][11]


[1]: https://raw.githubusercontent.com/DataDog/integrations-core/master/cassandra_nodetool/images/cassandra_dashboard.png
[2]: https://github.com/DataDog/integrations-core/tree/master/cassandra
[3]: https://app.datadoghq.com/account/settings#agent
[4]: https://docs.datadoghq.com/agent/faq/agent-configuration-files/#agent-configuration-directory
[5]: https://github.com/DataDog/integrations-core/blob/master/cassandra_nodetool/datadog_checks/cassandra_nodetool/data/conf.yaml.example
[6]: https://docs.datadoghq.com/agent/faq/agent-commands/#agent-status-and-information
[7]: https://github.com/DataDog/integrations-core/blob/master/cassandra_nodetool/metadata.csv
[8]: https://docs.datadoghq.com/help
[9]: https://www.datadoghq.com/blog/how-to-monitor-cassandra-performance-metrics
[10]: https://www.datadoghq.com/blog/how-to-collect-cassandra-metrics
[11]: https://www.datadoghq.com/blog/monitoring-cassandra-with-datadog
