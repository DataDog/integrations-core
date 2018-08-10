# HDFS DataNode Integration

![HDFS Dashboard][1011]

## Overview

Track disk utilization and failed volumes on each of your HDFS DataNodes. This Agent check collects metrics for these, as well as block- and cache-related metrics.

Use this check (hdfs_datanode) and its counterpart check (hdfs_namenode), not the older two-in-one check (hdfs); that check is deprecated.

## Setup
### Installation

The HDFS DataNode check is included in the [Datadog Agent][101] package, so you don't need to install anything else on your DataNodes.

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

Edit the `hdfs_datanode.d/conf.yaml` file, in the `conf.d/` folder at the root of your [Agent's configuration directory][1012]. See the [sample hdfs_datanode.d/conf.yaml][102] for all available configuration options:

```
init_config:

instances:
  - hdfs_datanode_jmx_uri: http://localhost:50075
```

[Restart the Agent][103] to begin sending DataNode metrics to Datadog.

### Validation

[Run the Agent's `status` subcommand][104] and look for `hdfs_datanode` under the Checks section.

## Data Collected
### Metrics
See [metadata.csv][105] for a list of metrics provided by this integration.

### Events
The HDFS-datanode check does not include any events at this time.

### Service Checks

`hdfs.datanode.jmx.can_connect`:

Returns `Critical` if the Agent cannot connect to the DataNode's JMX interface for any reason (e.g. wrong port provided, timeout, un-parseable JSON response).

## Troubleshooting
Need help? Contact [Datadog Support][106].

## Further Reading

* [Hadoop architectural overview][107]
* [How to monitor Hadoop metrics][108]
* [How to collect Hadoop metrics][109]
* [How to monitor Hadoop with Datadog][1010]


[101]: https://app.datadoghq.com/account/settings#agent
[102]: https://github.com/DataDog/integrations-core/blob/master/hdfs_datanode/datadog_checks/hdfs_datanode/data/conf.yaml.example
[103]: https://docs.datadoghq.com/agent/faq/agent-commands/#start-stop-restart-the-agent
[104]: https://docs.datadoghq.com/agent/faq/agent-commands/#agent-status-and-information
[105]: https://github.com/DataDog/integrations-core/blob/master/hdfs_datanode/metadata.csv
[106]: https://docs.datadoghq.com/help/
[107]: https://www.datadoghq.com/blog/hadoop-architecture-overview/
[108]: https://www.datadoghq.com/blog/monitor-hadoop-metrics/
[109]: https://www.datadoghq.com/blog/collecting-hadoop-metrics/
[1010]: https://www.datadoghq.com/blog/monitor-hadoop-metrics-datadog/
[1011]: https://raw.githubusercontent.com/DataDog/integrations-core/master/hdfs_datanode/images/hadoop_dashboard.png
[1012]: https://docs.datadoghq.com/agent/faq/agent-configuration-files/#agent-configuration-directory
