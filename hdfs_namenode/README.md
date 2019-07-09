# HDFS NameNode Integration

![HDFS Dashboard][111]

## Overview

Monitor your primary _and_ standby HDFS NameNodes to know when your cluster falls into a precarious state: when you're down to one NameNode remaining, or when it's time to add more capacity to the cluster. This Agent check collects metrics for remaining capacity, corrupt/missing blocks, dead DataNodes, filesystem load, under-replicated blocks, total volume failures (across all DataNodes), and many more.

Use this check (hdfs_namenode) and its counterpart check (hdfs_datanode), not the older two-in-one check (hdfs); that check is deprecated.

## Setup

Find below instructions to install and configure the check when running the Agent on a host. See the [Autodiscovery Integration Templates documentation][112] to learn how to apply those instructions to a containerized environment.

### Installation

The HDFS NameNode check is included in the [Datadog Agent][113] package, so you don't need to install anything else on your NameNodes.

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

Edit the `hdfs_namenode.d/conf.yaml` file, in the `conf.d/` folder at the root of your [Agent's configuration directory][114]. See the [sample hdfs_namenode.d/conf.yaml][115] for all available configuration options:

```
init_config:

instances:
  - hdfs_namenode_jmx_uri: http://localhost:50070
```

[Restart the Agent][116] to begin sending NameNode metrics to Datadog.

### Validation

[Run the Agent's `status` subcommand][117] and look for `hdfs_namenode` under the Checks section.

## Data Collected
### Metrics

See [metadata.csv][118] for a list of metrics provided by this integration.

### Events
The HDFS-namenode check does not include any events.

### Service Checks

`hdfs.namenode.jmx.can_connect`:

Returns `Critical` if the Agent cannot connect to the NameNode's JMX interface for any reason (e.g. wrong port provided, timeout, un-parseable JSON response).

## Troubleshooting
Need help? Contact [Datadog support][119].

## Further Reading

* [Hadoop architectural overview][120]
* [How to monitor Hadoop metrics][121]
* [How to collect Hadoop metrics][122]
* [How to monitor Hadoop with Datadog][123]


[111]: https://raw.githubusercontent.com/DataDog/integrations-core/master/hdfs_datanode/images/hadoop_dashboard.png
[112]: https://docs.datadoghq.com/agent/autodiscovery/integrations
[113]: https://app.datadoghq.com/account/settings#agent
[114]: https://docs.datadoghq.com/agent/guide/agent-configuration-files/?tab=agentv6#agent-configuration-directory
[115]: https://github.com/DataDog/integrations-core/blob/master/hdfs_namenode/datadog_checks/hdfs_namenode/data/conf.yaml.example
[116]: https://docs.datadoghq.com/agent/guide/agent-commands/?tab=agentv6#start-stop-and-restart-the-agent
[117]: https://docs.datadoghq.com/agent/guide/agent-commands/?tab=agentv6#agent-status-and-information
[118]: https://github.com/DataDog/integrations-core/blob/master/hdfs_namenode/metadata.csv
[119]: https://docs.datadoghq.com/help
[120]: https://www.datadoghq.com/blog/hadoop-architecture-overview
[121]: https://www.datadoghq.com/blog/monitor-hadoop-metrics
[122]: https://www.datadoghq.com/blog/collecting-hadoop-metrics
[123]: https://www.datadoghq.com/blog/monitor-hadoop-metrics-datadog
