# Agent Check: Cassandra Nodetool

![Cassandra default dashboard][111]

## Overview

This check collects metrics for your Cassandra cluster that are not available through [jmx integration][112].
It uses the `nodetool` utility to collect them.

## Setup
### Installation

The Cassandra Nodetool check is included in the [Datadog Agent][114] package, so you don't need to install anything else on your Cassandra nodes.

### Configuration

Edit the file `cassandra_nodetool.d/conf.yaml` in the `conf.d/` folder at the root of your [Agent's configuration directory][115].
See the [sample cassandra_nodetool.d/conf.yaml][116] for all available configuration options:

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

  # Whether or not to use the --ssl parameter for nodetool to initiate a connection over SSL to the JMX server.
  # Optional boolean. If included must be true or false.
  # ssl: false

  # a list of additional tags to be sent with the metrics
  # tags: []
```

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

* [How to monitor Cassandra performance metrics][120]
* [How to collect Cassandra metrics][121]
* [Monitoring Cassandra with Datadog][122]

[111]: https://raw.githubusercontent.com/DataDog/integrations-core/master/cassandra_nodetool/images/cassandra_dashboard.png
[112]: https://github.com/DataDog/integrations-core/tree/master/cassandra
[114]: https://app.datadoghq.com/account/settings#agent
[115]: https://docs.datadoghq.com/agent/guide/agent-configuration-files/#agent-configuration-directory
[116]: https://github.com/DataDog/integrations-core/blob/master/cassandra_nodetool/datadog_checks/cassandra_nodetool/data/conf.yaml.example
[117]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[118]: https://github.com/DataDog/integrations-core/blob/master/cassandra_nodetool/metadata.csv
[119]: https://docs.datadoghq.com/help
[120]: https://www.datadoghq.com/blog/how-to-monitor-cassandra-performance-metrics
[121]: https://www.datadoghq.com/blog/how-to-collect-cassandra-metrics
[122]: https://www.datadoghq.com/blog/monitoring-cassandra-with-datadog
