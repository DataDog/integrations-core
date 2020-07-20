# HDFS DataNode Integration

![HDFS Dashboard][1]

## Overview

Track disk utilization and failed volumes on each of your HDFS DataNodes. This Agent check collects metrics for these, as well as block- and cache-related metrics.

Use this check (hdfs_datanode) and its counterpart check (hdfs_namenode), not the older two-in-one check (hdfs); that check is deprecated.

## Setup

Follow the instructions below to install and configure this check for an Agent running on a host. For containerized environments, see the [Autodiscovery Integration Templates][2] for guidance on applying these instructions.

### Installation

The HDFS DataNode check is included in the [Datadog Agent][3] package, so you don't need to install anything else on your DataNodes.

### Configuration

#### Prepare the DataNode

1. The Agent collects metrics from the DataNode's JMX remote interface. The interface is disabled by default, enable it by setting the following option in `hadoop-env.sh` (usually found in $HADOOP_HOME/conf):

   ```conf
   export HADOOP_DATANODE_OPTS="-Dcom.sun.management.jmxremote
     -Dcom.sun.management.jmxremote.authenticate=false
     -Dcom.sun.management.jmxremote.ssl=false
     -Dcom.sun.management.jmxremote.port=50075 $HADOOP_DATANODE_OPTS"
   ```

2. Restart the DataNode process to enable the JMX interface.

#### Connect the Agent

##### Host

Follow the instructions below to configure this check for an Agent running on a host. For containerized environments, see the [Containerized](#containerized) section.

1. Edit the `hdfs_datanode.d/conf.yaml` file, in the `conf.d/` folder at the root of your [Agent's configuration directory][4]. See the [sample hdfs_datanode.d/conf.yaml][5] for all available configuration options:

   ```yaml
   init_config:

   instances:
     ## @param hdfs_datanode_jmx_uri - string - required
     ## The HDFS DataNode check retrieves metrics from the HDFS DataNode's JMX
     ## interface via HTTP(S) (not a JMX remote connection). This check must be installed on a HDFS DataNode. The HDFS
     ## DataNode JMX URI is composed of the DataNode's hostname and port.
     ##
     ## The hostname and port can be found in the hdfs-site.xml conf file under
     ## the property dfs.datanode.http.address
     ## https://hadoop.apache.org/docs/r2.7.1/hadoop-project-dist/hadoop-hdfs/hdfs-default.xml
     #
     - hdfs_datanode_jmx_uri: http://localhost:50075
   ```

2. [Restart the Agent][6].

#### Containerized

For containerized environments, see the [Autodiscovery Integration Templates][2] for guidance on applying the parameters below.

| Parameter            | Value                                                |
| -------------------- | ---------------------------------------------------- |
| `<INTEGRATION_NAME>` | `hdfs_datanode`                                      |
| `<INIT_CONFIG>`      | blank or `{}`                                        |
| `<INSTANCE_CONFIG>`  | `{"hdfs_datanode_jmx_uri": "http://%%host%%:50075"}` |

#### Log collection

**Available for Agent >6.0**

1. Collecting logs is disabled by default in the Datadog Agent. Enable it in the `datadog.yaml` file with:

    ```yaml
      logs_enabled: true
    ```

2. Add this configuration block to your `hdfs_datanode.d/conf.yaml` file to start collecting your DataNode logs:

    ```yaml
      logs:
        - type: file
          path: /var/log/hadoop-hdfs/*.log
          source: hdfs_datanode
          service: <SERVICE_NAME>
    ```

    Change the `path` and `service` parameter values and configure them for your environment.

3. [Restart the Agent][6].

### Validation

[Run the Agent's status subcommand][7] and look for `hdfs_datanode` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][8] for a list of metrics provided by this integration.

### Events

The HDFS-datanode check does not include any events.

### Service Checks

**hdfs.datanode.jmx.can_connect**:<br>
Returns `Critical` if the Agent cannot connect to the DataNode's JMX interface for any reason (e.g. wrong port provided, timeout, un-parseable JSON response).

## Troubleshooting

Need help? Contact [Datadog support][9].

## Further Reading

- [Hadoop architectural overview][10]
- [How to monitor Hadoop metrics][11]
- [How to collect Hadoop metrics][12]
- [How to monitor Hadoop with Datadog][13]

[1]: https://raw.githubusercontent.com/DataDog/integrations-core/master/hdfs_datanode/images/hadoop_dashboard.png
[2]: https://docs.datadoghq.com/agent/kubernetes/integrations/
[3]: https://app.datadoghq.com/account/settings#agent
[4]: https://docs.datadoghq.com/agent/guide/agent-configuration-files/#agent-configuration-directory
[5]: https://github.com/DataDog/integrations-core/blob/master/hdfs_datanode/datadog_checks/hdfs_datanode/data/conf.yaml.example
[6]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[7]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[8]: https://github.com/DataDog/integrations-core/blob/master/hdfs_datanode/metadata.csv
[9]: https://docs.datadoghq.com/help/
[10]: https://www.datadoghq.com/blog/hadoop-architecture-overview
[11]: https://www.datadoghq.com/blog/monitor-hadoop-metrics
[12]: https://www.datadoghq.com/blog/collecting-hadoop-metrics
[13]: https://www.datadoghq.com/blog/monitor-hadoop-metrics-datadog
