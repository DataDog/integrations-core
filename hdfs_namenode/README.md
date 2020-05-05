# HDFS NameNode Integration

![HDFS Dashboard][111]

## Overview

Monitor your primary _and_ standby HDFS NameNodes to know when your cluster falls into a precarious state: when you're down to one NameNode remaining, or when it's time to add more capacity to the cluster. This Agent check collects metrics for remaining capacity, corrupt/missing blocks, dead DataNodes, filesystem load, under-replicated blocks, total volume failures (across all DataNodes), and many more.

Use this check (hdfs_namenode) and its counterpart check (hdfs_datanode), not the older two-in-one check (hdfs); that check is deprecated.

## Setup

Follow the instructions below to install and configure this check for an Agent running on a host. For containerized environments, see the [Autodiscovery Integration Templates][112] for guidance on applying these instructions.

### Installation

The HDFS NameNode check is included in the [Datadog Agent][113] package, so you don't need to install anything else on your NameNodes.

### Configuration

#### Prepare the NameNode

1. The Agent collects metrics from the NameNode's JMX remote interface. The interface is disabled by default, so enable it by setting the following option in `hadoop-env.sh` (usually found in \$HADOOP_HOME/conf):

    ```conf
    export HADOOP_NAMENODE_OPTS="-Dcom.sun.management.jmxremote
      -Dcom.sun.management.jmxremote.authenticate=false
      -Dcom.sun.management.jmxremote.ssl=false
      -Dcom.sun.management.jmxremote.port=50070 $HADOOP_NAMENODE_OPTS"
    ```

2. Restart the NameNode process to enable the JMX interface.

#### Connect the Agent

##### Host

Follow the instructions below to configure this check for an Agent running on a host. For containerized environments, see the [Containerized](#containerized) section.

1. Edit the `hdfs_namenode.d/conf.yaml` file, in the `conf.d/` folder at the root of your [Agent's configuration directory][114]. See the [sample hdfs_namenode.d/conf.yaml][115] for all available configuration options:

   ```yaml
   init_config:

   instances:
     ## @param hdfs_namenode_jmx_uri - string - required
     ## The HDFS NameNode check retrieves metrics from the HDFS NameNode's JMX
     ## interface via HTTP(S) (not a JMX remote connection). This check must be installed on
     ## a HDFS NameNode. The HDFS NameNode JMX URI is composed of the NameNode's hostname and port.
     ##
     ## The hostname and port can be found in the hdfs-site.xml conf file under
     ## the property dfs.namenode.http-address
     ## https://hadoop.apache.org/docs/r2.7.1/hadoop-project-dist/hadoop-hdfs/hdfs-default.xml
     #
     - hdfs_namenode_jmx_uri: http://localhost:50070
   ```

2. [Restart the Agent][116].

#### Containerized

For containerized environments, see the [Autodiscovery Integration Templates][112] for guidance on applying the parameters below.

| Parameter            | Value                                                 |
| -------------------- | ----------------------------------------------------- |
| `<INTEGRATION_NAME>` | `hdfs_namenode`                                       |
| `<INIT_CONFIG>`      | blank or `{}`                                         |
| `<INSTANCE_CONFIG>`  | `{"hdfs_namenode_jmx_uri": "https://%%host%%:50070"}` |

#### Log collection

**Available for Agent >6.0**

1. Collecting logs is disabled by default in the Datadog Agent. Enable it in the `datadog.yaml` file with:

    ```yaml
      logs_enabled: true
    ```

2. Add this configuration block to your `hdfs_namenode.d/conf.yaml` file to start collecting your NameNode logs:

    ```yaml
      logs:
        - type: file
          path: /var/log/hadoop-hdfs/*.log
          source: hdfs_namenode
          service: <SERVICE_NAME>
    ```

    Change the `path` and `service` parameter values and configure them for your environment.

3. [Restart the Agent][6].

### Validation

[Run the Agent's status subcommand][117] and look for `hdfs_namenode` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][118] for a list of metrics provided by this integration.

### Events

The HDFS-namenode check does not include any events.

### Service Checks

**hdfs.namenode.jmx.can_connect**:<br>
Returns `Critical` if the Agent cannot connect to the NameNode's JMX interface for any reason (e.g. wrong port provided, timeout, un-parseable JSON response).

## Troubleshooting

Need help? Contact [Datadog support][119].

## Further Reading

- [Hadoop architectural overview][1110]
- [How to monitor Hadoop metrics][1111]
- [How to collect Hadoop metrics][1112]
- [How to monitor Hadoop with Datadog][1113]

[111]: https://raw.githubusercontent.com/DataDog/integrations-core/master/hdfs_datanode/images/hadoop_dashboard.png
[112]: https://docs.datadoghq.com/agent/kubernetes/integrations/
[113]: https://app.datadoghq.com/account/settings#agent
[114]: https://docs.datadoghq.com/agent/guide/agent-configuration-files/#agent-configuration-directory
[115]: https://github.com/DataDog/integrations-core/blob/master/hdfs_namenode/datadog_checks/hdfs_namenode/data/conf.yaml.example
[116]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[117]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[118]: https://github.com/DataDog/integrations-core/blob/master/hdfs_namenode/metadata.csv
[119]: https://docs.datadoghq.com/help/
[1110]: https://www.datadoghq.com/blog/hadoop-architecture-overview
[1111]: https://www.datadoghq.com/blog/monitor-hadoop-metrics
[1112]: https://www.datadoghq.com/blog/collecting-hadoop-metrics
[1113]: https://www.datadoghq.com/blog/monitor-hadoop-metrics-datadog
