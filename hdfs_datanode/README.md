# HDFS DataNode Integration

## Overview

Track disk utilization and failed volumes on each of your HDFS DataNodes. This Agent check collects metrics for these, as well as block- and cache-related metrics.

Use this check (hdfs_datanode) and its counterpart check (hdfs_namenode), not the older two-in-one check (hdfs); that check is deprecated.

## Setup
### Installation

The HDFS DataNode check is packaged with the Agent, so simply [install the Agent][1] on your DataNodes.

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

Create a file `hdfs_datanode.yaml` in the Agent's `conf.d` directory. See the [sample hdfs_datanode.yaml][2] for all available configuration options:

```
init_config:

instances:
  - hdfs_datanode_jmx_uri: http://localhost:50075
```

[Restart the Agent][3] to begin sending DataNode metrics to Datadog.

### Validation

[Run the Agent's `status` subcommand][4] and look for `hdfs_datanode` under the Checks section:

```
  Checks
  ======
    [...]

    hdfs_datanode
    -------
      - instance #0 [OK]
      - Collected 26 metrics, 0 events & 1 service check

    [...]
```

## Compatibility

The hdfs_datanode check is compatible with all major platforms.

## Data Collected
### Metrics
See [metadata.csv][5] for a list of metrics provided by this integration.

### Events
The HDFS-datanode check does not include any event at this time.

### Service Checks

`hdfs.datanode.jmx.can_connect`:

Returns `Critical` if the Agent cannot connect to the DataNode's JMX interface for any reason (e.g. wrong port provided, timeout, un-parseable JSON response).

## Troubleshooting
Need help? Contact [Datadog Support][6].

## Further Reading

* [Hadoop architectural overview][7]
* [How to monitor Hadoop metrics][8]
* [How to collect Hadoop metrics][9]
* [How to monitor Hadoop with Datadog][10]


[1]: https://app.datadoghq.com/account/settings#agent
[2]: https://github.com/DataDog/integrations-core/blob/master/hdfs_datanode/conf.yaml.example
[3]: https://docs.datadoghq.com/agent/faq/agent-commands/#start-stop-restart-the-agent
[4]: https://docs.datadoghq.com/agent/faq/agent-commands/#agent-status-and-information
[5]: https://github.com/DataDog/integrations-core/blob/master/hdfs_datanode/metadata.csv
[6]: http://docs.datadoghq.com/help/
[7]: https://www.datadoghq.com/blog/hadoop-architecture-overview/
[8]: https://www.datadoghq.com/blog/monitor-hadoop-metrics/
[9]: https://www.datadoghq.com/blog/collecting-hadoop-metrics/
[10]: https://www.datadoghq.com/blog/monitor-hadoop-metrics-datadog/
