# Agent Check: Cassandra Nodetool

## Overview

This check collects metrics for your Cassandra cluster that are not available through [jmx integration](https://github.com/DataDog/integrations-core/tree/master/cassandra).
It uses the `nodetool` utility to collect them.

## Setup
### Installation

The cassandra nodetool check is packaged with the Agent, so simply [install the Agent](https://app.datadoghq.com/account/settings#agent) on your cassandra nodes.
If you need the newest version of the check, install the `dd-check-cassandra_nodetool` package.

### Configuration

Create a file `cassandra_nodetool.yaml` in the Agent's `conf.d` directory:
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

When you run `datadog-agent info` you should see something like the following:

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
See [metadata.csv](https://github.com/DataDog/integrations-core/blob/master/cassandra_nodetool/metadata.csv) for a list of metrics provided by this integration.

### Events
The Cassandra_nodetool check does not include any event at this time.

### Service Checks

**cassandra.nodetool.node_up**:
The agent sends this service check for each node of the monitored cluster. Returns CRITICAL if the node is down, otherwise OK.

## Troubleshooting

If you have any questions about Datadog or a use case our [Docs](https://docs.datadoghq.com/) didn’t mention, we’d love to help! Here’s how you can reach out to us:

### Visit the Knowledge Base

Learn more about what you can do in Datadog on the [Support Knowledge Base](https://datadog.zendesk.com/agent/).

### Web Support

Messages in the [event stream](https://app.datadoghq.com/event/stream) containing **@support-datadog** will reach our Support Team. This is a convenient channel for referencing graph snapshots or a particular event. In addition, we have a livechat service available during the day (EST) from any page within the app.

### By Email

You can also contact our Support Team via email at [support@datadoghq.com](mailto:support@datadoghq.com).

### Over Slack

Reach out to our team and other Datadog users on [Slack](http://chat.datadoghq.com/).

## Further Reading
To get a better idea of how (or why) to integrate your Cassandra cluster with Datadog, check out our [series of blog posts](https://www.datadoghq.com/blog/how-to-monitor-cassandra-performance-metrics) about it.
