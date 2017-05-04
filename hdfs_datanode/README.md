# HDFS DataNode Integration

# Overview

Track disk utilization and failed volumes on each of your HDFS DataNodes. This Agent check collects metrics for these, as well as block- and cache-related metrics.

Use this check (hdfs_datanode) and its counterpart check (hdfs_namenode), not the older two-in-one check (hdfs); that check is deprecated.

# Installation

The HDFS DataNode check is packaged with the Agent, so simply [install the Agent](https://app.datadoghq.com/account/settings#agent) on your DataNodes.

# Configuration

## Prepare the DataNode

The Agent collects metrics from the DataNode's JMX remote interface. The interface is disabled by default, so enable it by setting the following option in `hadoop-env.sh` (usually found in $HADOOP_HOME/conf):

```
export HADOOP_DATANODE_OPTS="-Dcom.sun.management.jmxremote
  -Dcom.sun.management.jmxremote.authenticate=false
  -Dcom.sun.management.jmxremote.ssl=false
  -Dcom.sun.management.jmxremote.port=50075 $HADOOP_DATANODE_OPTS"
```

Restart the DataNode process to enable the JMX interface.

## Connect the Agent

Create a file `hdfs_datanode.yaml` in the Agent's `conf.d` directory:

```
init_config:

instances:
  - hdfs_datanode_jmx_uri: http://localhost:50075
```

Restart the Agent to begin sending DataNode metrics to Datadog.

# Validation

Run the Agent's `info` subcommand and look for `hdfs_datanode` under the Checks section:

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

# Troubleshooting

# Compatibility

The hdfs_datanode check is compatible with all major platforms.

# Metrics

See [metadata.csv](https://github.com/DataDog/integrations-core/blob/master/hdfs_datanode/metadata.csv) for a list of metrics provided by this integration.

# Events

# Service Checks

`hdfs.datanode.jmx.can_connect`:

Returns `Critical` if the Agent cannot connect to the DataNode's JMX interface for any reason (e.g. wrong port provided, timeout, un-parseable JSON response).

# Further Reading

To get a better idea of how (or why) to integrate your HDFS DataNodes with Datadog, check out our [series of blog posts](https://www.datadoghq.com/blog/hadoop-architecture-overview/) about monitoring Hadoop. In particular, [Part 2](https://www.datadoghq.com/blog/monitor-hadoop-metrics/) provides a useful walkthrough of key metrics.
