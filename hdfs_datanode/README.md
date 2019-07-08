# HDFS DataNode Integration

![HDFS Dashboard][1]

## Overview

Track disk utilization and failed volumes on each of your HDFS DataNodes. This Agent check collects metrics for these, as well as block- and cache-related metrics.

Use this check (hdfs_datanode) and its counterpart check (hdfs_namenode), not the older two-in-one check (hdfs); that check is deprecated.

## Setup

Find below instructions to install and configure the check when running the Agent on a host. See the [Autodiscovery Integration Templates documentation][2] to learn how to apply those instructions to a containerized environment.

### Installation

The HDFS DataNode check is included in the [Datadog Agent][3] package, so you don't need to install anything else on your DataNodes.

### Configuration
#### Prepare the DataNode

The Agent collects metrics from the DataNode's JMX remote interface. The interface is disabled by default, so enable it by setting the following option in `hadoop-env.sh` (usually found in $HADOOP_HOME/conf):

```
export HADOOP_DATANODE_OPTS="-Dcom.sun.management.jmxremote
  -Dcom.sun.management.jmxremote.authenticate=false
  -Dcom.sun.management.jmxremote.ssl=false
  -Dcom.sun.management.jmxremote.port=50075 $HADOOP_DATANODE_OPTS"
```

Restart the DataNode process to enable the JMX interface.

#### Connect the Agent

Edit the `hdfs_datanode.d/conf.yaml` file, in the `conf.d/` folder at the root of your [Agent's configuration directory][4]. See the [sample hdfs_datanode.d/conf.yaml][5] for all available configuration options:

```
init_config:

instances:
  - hdfs_datanode_jmx_uri: http://localhost:50075
```

[Restart the Agent][6] to begin sending DataNode metrics to Datadog.

### Validation

[Run the Agent's `status` subcommand][7] and look for `hdfs_datanode` under the Checks section.

## Data Collected
### Metrics
See [metadata.csv][8] for a list of metrics provided by this integration.

### Events
The HDFS-datanode check does not include any events.

### Service Checks

`hdfs.datanode.jmx.can_connect`:

Returns `Critical` if the Agent cannot connect to the DataNode's JMX interface for any reason (e.g. wrong port provided, timeout, un-parseable JSON response).

## Troubleshooting
Need help? Contact [Datadog support][9].

## Further Reading

* [Hadoop architectural overview][10]
* [How to monitor Hadoop metrics][11]
* [How to collect Hadoop metrics][12]
* [How to monitor Hadoop with Datadog][13]


[1]: https://raw.githubusercontent.com/DataDog/integrations-core/master/hdfs_datanode/images/hadoop_dashboard.png
[2]: https://docs.datadoghq.com/agent/autodiscovery/integrations
[3]: https://app.datadoghq.com/account/settings#agent
[4]: https://docs.datadoghq.com/agent/guide/agent-configuration-files/?tab=agentv6#agent-configuration-directory
[5]: https://github.com/DataDog/integrations-core/blob/master/hdfs_datanode/datadog_checks/hdfs_datanode/data/conf.yaml.example
[6]: https://docs.datadoghq.com/agent/guide/agent-commands/?tab=agentv6#start-stop-and-restart-the-agent
[7]: https://docs.datadoghq.com/agent/guide/agent-commands/?tab=agentv6#agent-status-and-information
[8]: https://github.com/DataDog/integrations-core/blob/master/hdfs_datanode/metadata.csv
[9]: https://docs.datadoghq.com/help
[10]: https://www.datadoghq.com/blog/hadoop-architecture-overview
[11]: https://www.datadoghq.com/blog/monitor-hadoop-metrics
[12]: https://www.datadoghq.com/blog/collecting-hadoop-metrics
[13]: https://www.datadoghq.com/blog/monitor-hadoop-metrics-datadog
