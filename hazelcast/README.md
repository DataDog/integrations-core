# Agent Check: Hazelcast

## Overview

This check monitors [Hazelcast][1].

## Setup

### Installation

The Hazelcast check is included in the [Datadog Agent][2] package.
No additional installation is needed on your server.

### Configuration

#### Host

Follow the instructions below to configure this check for an Agent running on a host. For containerized environments, see the [Containerized](#containerized) section.

##### Metric collection

1. Edit the `hazelcast.d/conf.yaml` file, in the `conf.d/` folder at the root of your
   Agent's configuration directory to start collecting your Hazelcast performance data.
   See the [sample hazelcast.d/conf.yaml][3] for all available configuration options.

   This check has a limit of 350 metrics per instance. The number of returned metrics is indicated in the info page.
   You can specify the metrics you are interested in by editing the configuration below.
   To learn how to customize the metrics to collect, visit the [JMX Checks documentation][4] for more detailed instructions.
   If you need to monitor more metrics, contact [Datadog support][5].

2. [Restart the Agent][6].

##### Log collection

1. Hazelcast supports many different [logging adapters][7]. Here is an example of a `log4j2.properties` file:

   ```text
   rootLogger=file
   rootLogger.level=info
   property.filepath=/path/to/log/files
   property.filename=hazelcast

   appender.file.type=RollingFile
   appender.file.name=RollingFile
   appender.file.fileName=${filepath}/${filename}.log
   appender.file.filePattern=${filepath}/${filename}-%d{yyyy-MM-dd}-%i.log.gz
   appender.file.layout.type=PatternLayout
   appender.file.layout.pattern = %d{yyyy-MM-dd HH:mm:ss} [%thread] %level{length=10} %c{1}:%L - %m%n
   appender.file.policies.type=Policies
   appender.file.policies.time.type=TimeBasedTriggeringPolicy
   appender.file.policies.time.interval=1
   appender.file.policies.time.modulate=true
   appender.file.policies.size.type=SizeBasedTriggeringPolicy
   appender.file.policies.size.size=50MB
   appender.file.strategy.type=DefaultRolloverStrategy
   appender.file.strategy.max=100

   rootLogger.appenderRefs=file
   rootLogger.appenderRef.file.ref=RollingFile

   #Hazelcast specific logs.

   #log4j.logger.com.hazelcast=debug

   #log4j.logger.com.hazelcast.cluster=debug
   #log4j.logger.com.hazelcast.partition=debug
   #log4j.logger.com.hazelcast.partition.InternalPartitionService=debug
   #log4j.logger.com.hazelcast.nio=debug
   #log4j.logger.com.hazelcast.hibernate=debug
   ```

2. By default, Datadog's integration pipeline supports the following conversion [pattern][8]:

   ```text
   %d{yyyy-MM-dd HH:mm:ss} [%thread] %level{length=10} %c{1}:%L - %m%n
   ```

    Clone and edit the [integration pipeline][9] if you have a different format.

3. Collecting logs is disabled by default in the Datadog Agent. Enable it in your `datadog.yaml` file:

   ```yaml
   logs_enabled: true
   ```

4. Add the following configuration block to your `hazelcast.d/conf.yaml` file. Change the `path` and `service` parameter values based on your environment. See the [sample hazelcast.d/conf.yaml][3] for all available configuration options.

   ```yaml
   logs:
     - type: file
       path: /var/log/hazelcast.log
       source: hazelcast
       service: <SERVICE>
       log_processing_rules:
         - type: multi_line
           name: log_start_with_date
           pattern: \d{4}\.\d{2}\.\d{2}
   ```

5. [Restart the Agent][6].

#### Containerized

##### Metric collection

For containerized environments, see the [Autodiscovery with JMX][10] guide.

##### Log collection

Collecting logs is disabled by default in the Datadog Agent. To enable it, see [Docker log collection][11].

| Parameter      | Value                                              |
| -------------- | -------------------------------------------------- |
| `<LOG_CONFIG>` | `{"source": "hazelcast", "service": "<SERVICE_NAME>"}` |

### Validation

[Run the Agent's status subcommand][12] and look for `hazelcast` under the **JMXFetch** section:

```text
========
JMXFetch
========
  Initialized checks
  ==================
    hazelcast
      instance_name : hazelcast-localhost-9999
      message :
      metric_count : 46
      service_check_count : 0
      status : OK
```

## Data Collected

### Metrics

See [metadata.csv][13] for a list of metrics provided by this check.

### Service Checks

**hazelcast.can_connect**:<br>
Returns `CRITICAL` if the Agent is unable to connect to and collect metrics from the monitored Hazelcast instance, otherwise returns `OK`.

**hazelcast.mc_cluster_state**:<br>
Represents the state of the Hazelcast Management Center as indicated by its health check.

### Events

Hazelcast does not include any events.

## Troubleshooting

Need help? Contact [Datadog support][5].

[1]: https://hazelcast.org
[2]: https://docs.datadoghq.com/agent/
[3]: https://github.com/DataDog/integrations-core/blob/master/hazelcast/datadog_checks/hazelcast/data/conf.yaml.example
[4]: https://docs.datadoghq.com/integrations/java
[5]: https://docs.datadoghq.com/help
[6]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[7]: https://docs.hazelcast.org/docs/latest/manual/html-single/index.html#logging-configuration
[8]: https://logging.apache.org/log4j/2.x/manual/layouts.html#Patterns
[9]: https://docs.datadoghq.com/logs/processing/#integration-pipelines
[10]: https://docs.datadoghq.com/agent/guide/autodiscovery-with-jmx/?tab=containerizedagent
[11]: https://docs.datadoghq.com/agent/docker/log/
[12]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[13]: https://github.com/DataDog/integrations-core/blob/master/hazelcast/metadata.csv
