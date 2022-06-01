# Agent Check: Kafka

![Kafka Dashboard][1]

## Overview

Connect Kafka to Datadog to:

- Visualize the performance of your cluster in real time.
- Correlate the performance of Kafka with the rest of your applications.

This check has a limit of 350 metrics per instance. The number of returned metrics is indicated on the info page. Specify the metrics you are interested in by editing the configuration below. To learn how to customize the metrics to collect see the [JMX Checks documentation][2] for more detailed instructions.

To collect Kafka consumer metrics, see the [kafka_consumer check][3].

**Note**: This integration attached sample configuration works only for Kafka >= 0.8.2.
If you are running a version older than that, see the [Agent v5.2.x released sample files][22].

## Setup

### Installation

The Agent's Kafka check is included in the [Datadog Agent][4] package, so you don't need to install anything else on your Kafka nodes.

The check collects metrics with JMX, so you need a JVM on each kafka node so the Agent can fork [jmxfetch][5]. You can use the same JVM that Kafka uses.

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

[1]: https://raw.githubusercontent.com/DataDog/integrations-core/master/kafka/images/kafka_dashboard.png
[2]: https://docs.datadoghq.com/integrations/java/
[3]: https://docs.datadoghq.com/integrations/kafka/?tab=host#kafka-consumer-integration
[4]: https://app.datadoghq.com/account/settings#agent
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
