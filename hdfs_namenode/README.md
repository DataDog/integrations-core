# HDFS NameNode Integration

## Overview

Monitor your primary _and_ standby HDFS NameNodes to know when your cluster falls into a precarious state: when you're down to one NameNode remaining, or when it's time to add more capacity to the cluster. This Agent check collects metrics for remaining capacity, corrupt/missing blocks, dead DataNodes, filesystem load, under-replicated blocks, total volume failures (across all DataNodes), and many more.

Use this check (hdfs_namenode) and its counterpart check (hdfs_datanode), not the older two-in-one check (hdfs); that check is deprecated.

## Setup
### Installation

The HDFS NameNode check is packaged with the Agent, so simply [install the Agent](https://app.datadoghq.com/account/settings#agent) on your NameNodes.

### Configuration
#### Prepare the NameNode

The Agent collects metrics from the NameNode's JMX remote interface. The interface is disabled by default, so enable it by setting the following option in `hadoop-env.sh` (usually found in $HADOOP_HOME/conf):

```
export HADOOP_NAMENODE_OPTS="-Dcom.sun.management.jmxremote
  -Dcom.sun.management.jmxremote.authenticate=false
  -Dcom.sun.management.jmxremote.ssl=false
  -Dcom.sun.management.jmxremote.port=50070 $HADOOP_NAMENODE_OPTS"
```

Restart the NameNode process to enable the JMX interface.

#### Connect the Agent

Create a file `hdfs_namenode.yaml` in the Agent's `conf.d` directory. See the [sample hdfs_namenode.yaml](https://github.com/DataDog/integrations-core/blob/master/hdfs_namenode/conf.yaml.example) for all available configuration options:

```
init_config:

instances:
  - hdfs_namenode_jmx_uri: http://localhost:50070
```

[Restart the Agent](https://docs.datadoghq.com/agent/faq/agent-commands/#start-stop-restart-the-agent) to begin sending NameNode metrics to Datadog.

### Validation

[Run the Agent's `status` subcommand](https://docs.datadoghq.com/agent/faq/agent-commands/#agent-status-and-information) and look for `hdfs_namenode` under the Checks section.

## Compatibility

The hdfs_namenode check is compatible with all major platforms.

## Data Collected
### Metrics

See [metadata.csv](https://github.com/DataDog/integrations-core/blob/master/hdfs_namenode/metadata.csv) for a list of metrics provided by this integration.

### Events
The HDFS-namenode check does not include any event at this time.

### Service Checks

`hdfs.namenode.jmx.can_connect`:

Returns `Critical` if the Agent cannot connect to the NameNode's JMX interface for any reason (e.g. wrong port provided, timeout, un-parseable JSON response).

## Troubleshooting
Need help? Contact [Datadog Support](http://docs.datadoghq.com/help/).

## Further Reading

* [Hadoop architectural overview](https://www.datadoghq.com/blog/hadoop-architecture-overview/)
* [How to monitor Hadoop metrics](https://www.datadoghq.com/blog/monitor-hadoop-metrics/)
* [How to collect Hadoop metrics](https://www.datadoghq.com/blog/collecting-hadoop-metrics/)
* [How to monitor Hadoop with Datadog](https://www.datadoghq.com/blog/monitor-hadoop-metrics-datadog/)
