# Agent Check: Hive

## Overview

This check monitors two parts of [Hive][1]: Hive Metastore and HiveServer2.

## Setup

### Installation

The Hive check is included in the [Datadog Agent][2] package.
No additional installation is needed on your server.

### Configuration

1. Edit the Hive configuration file in [`HIVE_HOME/conf/hive-site.xml`][3] to enable the Hive Metastore and HiveServer2 metrics by adding these properties:
    ```
    <property>
      <name>hive.metastore.metrics.enabled</name>
      <value>true</value>
    </property>
    <property>
      <name>hive.server2.metrics.enabled</name>
      <value>true</value>
    </property>
    ```
2. Enable a JMX remote connection for the HiveServer2 and/or for the Hive Metastore. For example, set the `HADOOP_CLIENT_OPTS` environment variable:
    ```
    export HADOOP_CLIENT_OPTS="$HADOOP_CLIENT_OPTS -Dcom.sun.management.jmxremote \
    -Dcom.sun.management.jmxremote.authenticate=false -Dcom.sun.management.jmxremote.ssl=false \
    -Dcom.sun.management.jmxremote.port=8808"
    ```
    Then restart the HiveServer2 or the Hive Metastore. Hive Metastore and HiveServer2 cannot share the same JMX connection.

3. Edit the `hive.d/conf.yaml` file, in the `conf.d/` folder at the root of your
   Agent's configuration directory to start collecting your hive performance data.
   See the [sample hive.d/conf.yaml][10] for all available configuration options.

   This check has a limit of 350 metrics per instance. The number of returned metrics is indicated in the info page.
   You can specify the metrics you are interested in by editing the configuration below.
   To learn how to customize the metrics to collect, visit the [JMX Checks documentation][4] for more detailed instructions.
   If you need to monitor more metrics, contact [Datadog support][8].

4. [Restart the Agent][5].

### Validation

[Run the Agent's status subcommand][6] and look for `Hive` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][7] for a list of metrics provided by this integration.

### Service Checks

 **hive.can_connect**:  
Returns `CRITICAL` if the Agent is unable to connect to and collect metrics from the monitored HiveServer2/Hive Metastore instance, otherwise returns `OK`.

### Events

The Hive check does not include any events.

## Troubleshooting

Need help? Contact [Datadog support][8].


[1]: https://cwiki.apache.org/confluence/display/Hive/Home
[2]: https://docs.datadoghq.com/agent
[3]: https://cwiki.apache.org/confluence/display/Hive/Configuration+Properties#ConfigurationProperties-Metrics
[4]: https://docs.datadoghq.com/integrations/java
[5]: https://docs.datadoghq.com/agent/guide/agent-commands/?tab=agentv6#start-stop-and-restart-the-agent
[6]: https://docs.datadoghq.com/agent/guide/agent-commands/?tab=agentv6#agent-status-and-information
[7]: https://github.com/DataDog/integrations-core/blob/master/hive/metadata.csv
[8]: https://docs.datadoghq.com/help
[9]: https://github.com/DataDog/integrations-core/blob/master/hive/assets/service_checks.json
[10]: https://github.com/DataDog/integrations-core/blob/master/hive/datadog_checks/hive/data/conf.yaml.example
