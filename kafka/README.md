# Agent Check: Kafka Broker

![Kafka Dashboard][1]

## Overview

View Kafka broker metrics collected for a 360-view of the health and performance of your Kafka clusters in real time. With this integration, you can collect metrics and logs from your Kafka deployment to visualize telemetry and alert on the performance of your Kafka stack. 

If you would benefit from visualizing the topology of your streaming data pipelines and identifying the root cause of bottlenecks, learn more about [Data Streams Monitoring][24].

**Note**: 
- This check has a limit of 350 metrics per instance. The number of returned metrics is indicated in the Agent status output. Specify the metrics you are interested in by editing the configuration below. For more detailed instructions on customizing the metrics to collect, see the [JMX Checks documentation][2].
- This integration attached sample configuration works only for Kafka >= 0.8.2.
If you are running a version older than that, see the [Agent v5.2.x released sample files][22].
- To collect Kafka consumer metrics, see the [kafka_consumer check][3].

## Setup

### Installation

The Agent's Kafka check is included in the [Datadog Agent][4] package, so you don't need to install anything else on your Kafka nodes.

The check collects metrics from JMX with [JMXFetch][5]. A JVM is needed on each kafka node so the Agent can run JMXFetch. The same JVM that Kafka uses can be used for this.

**Note**: The Kafka check cannot be used with Managed Streaming for Apache Kafka (Amazon MSK). Use the [Amazon MSK integration][6] instead.

### Configuration

<!-- xxx tabs xxx -->
<!-- xxx tab "Host" xxx -->

#### Host

To configure this check for an Agent running on a host:

##### Metric collection

1. Edit the `kafka.d/conf.yaml` file, in the `conf.d/` folder at the root of your [Agent's configuration directory][7]. Kafka bean names depend on the exact Kafka version you're running. Use the [example configuration file][8] that comes packaged with the Agent as a base since it is the most up-to-date configuration. **Note**: the Agent version in the example may be for a newer version of the Agent than what you have installed.

2. [Restart the Agent][9].

##### Log collection

_Available for Agent versions >6.0_

1. Kafka uses the `log4j` logger by default. To activate logging to a file and customize the format edit the `log4j.properties` file:

   ```text
     # Set root logger level to INFO and its only appender to R
     log4j.rootLogger=INFO, R
     log4j.appender.R.File=/var/log/kafka/server.log
     log4j.appender.R.layout=org.apache.log4j.PatternLayout
     log4j.appender.R.layout.ConversionPattern=%d{yyyy-MM-dd HH:mm:ss} %-5p %c{1}:%L - %m%n
   ```

2. By default, the Datadog integration pipeline supports the following conversion patterns:

   ```text
     %d{yyyy-MM-dd HH:mm:ss} %-5p %c{1}:%L - %m%n
     %d [%t] %-5p %c - %m%n
     %r [%t] %p %c %x - %m%n
     [%d] %p %m (%c)%n
   ```

    Clone and edit the [integration pipeline][10] if you have a different format.

3. Collecting logs is disabled by default in the Datadog Agent, enable it in your `datadog.yaml` file:

   ```yaml
   logs_enabled: true
   ```

4. Add the following configuration block to your `kafka.d/conf.yaml` file. Change the `path` and `service` parameter values based on your environment. See the [sample kafka.d/conf.yaml][8] for all available configuration options.

   ```yaml
   logs:
     - type: file
       path: /var/log/kafka/server.log
       source: kafka
       service: myapp
       #To handle multi line that starts with yyyy-mm-dd use the following pattern
       #log_processing_rules:
       #  - type: multi_line
       #    name: log_start_with_date
       #    pattern: \d{4}\-(0?[1-9]|1[012])\-(0?[1-9]|[12][0-9]|3[01])
   ```

5. [Restart the Agent][9].

<!-- xxz tab xxx -->
<!-- xxx tab "Containerized" xxx -->

#### Containerized

##### Metric collection

For containerized environments, see the [Autodiscovery with JMX][11] guide.

##### Log collection

_Available for Agent versions >6.0_

Collecting logs is disabled by default in the Datadog Agent. To enable it, see [Kubernetes Log Collection][12].

| Parameter      | Value                                              |
| -------------- | -------------------------------------------------- |
| `<LOG_CONFIG>` | `{"source": "kafka", "service": "<SERVICE_NAME>"}` |

<!-- xxz tab xxx -->
<!-- xxz tabs xxx -->

### Validation

[Run the Agent's status subcommand][13] and look for `kafka` under the **JMXFetch** section:

```text
========
JMXFetch
========
  Initialized checks
  ==================
    kafka
      instance_name : kafka-localhost-9999
      message :
      metric_count : 46
      service_check_count : 0
      status : OK
```

## Data Collected

### Metrics

See [metadata.csv][14] for a list of metrics provided by this check.

### Events

The Kafka check does not include any events.

### Service Checks

See [service_checks.json][15] for a list of service checks provided by this integration.

## Troubleshooting

- [Troubleshooting and Deep Dive for Kafka][16]
- [Agent failed to retrieve RMIServer stub][17]

## Further Reading

- [Monitoring Kafka performance metrics][19]
- [Collecting Kafka performance metrics][20]
- [Monitoring Kafka with Datadog][21]
- [Kafka Overview on the Knowledge Center][23]

[1]: https://raw.githubusercontent.com/DataDog/integrations-core/master/kafka/images/kafka_dashboard.png
[2]: https://docs.datadoghq.com/integrations/java/
[3]: https://docs.datadoghq.com/integrations/kafka/?tab=host#kafka-consumer-integration
[4]: https://app.datadoghq.com/account/settings/agent/latest
[5]: https://github.com/DataDog/jmxfetch
[6]: https://docs.datadoghq.com/integrations/amazon_msk/#pagetitle
[7]: https://docs.datadoghq.com/agent/guide/agent-configuration-files/#agent-configuration-directory
[8]: https://github.com/DataDog/integrations-core/blob/master/kafka/datadog_checks/kafka/data/conf.yaml.example
[9]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[10]: https://docs.datadoghq.com/logs/processing/#integration-pipelines
[11]: https://docs.datadoghq.com/agent/guide/autodiscovery-with-jmx/?tab=containerizedagent
[12]: https://docs.datadoghq.com/agent/kubernetes/log/
[13]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[14]: https://github.com/DataDog/integrations-core/blob/master/kafka/metadata.csv
[15]: https://github.com/DataDog/integrations-core/blob/master/kafka/assets/service_checks.json
[16]: https://docs.datadoghq.com/integrations/faq/troubleshooting-and-deep-dive-for-kafka/
[17]: https://docs.datadoghq.com/integrations/guide/agent-failed-to-retrieve-rmiserver-stub/
[19]: https://www.datadoghq.com/blog/monitoring-kafka-performance-metrics
[20]: https://www.datadoghq.com/blog/collecting-kafka-performance-metrics
[21]: https://www.datadoghq.com/blog/monitor-kafka-with-datadog
[22]: https://raw.githubusercontent.com/DataDog/dd-agent/5.2.1/conf.d/kafka.yaml.example
[23]: https://www.datadoghq.com/knowledge-center/apache-kafka/
[24]: https://www.datadoghq.com/product/data-streams-monitoring/
[25]: https://app.datadoghq.com/data-streams
