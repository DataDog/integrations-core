# Kafka Consumer Integration

![Kafka Dashboard][1]

## Overview

This Agent check only collects metrics for message offsets. If you want to collect JMX metrics from the Kafka brokers or Java-based consumers/producers, see the kafka check.

This check fetches the highwater offsets from the Kafka brokers, consumer offsets that are stored in Kafka or zookeeper (for old-style consumers), and the calculated consumer lag (which is the difference between the broker offset and the consumer offset).

**Note:** This integration ensures that consumer offsets are checked before broker offsets because worst case is that consumer lag is a little overstated. Doing it in reverse can understate consumer lag to the point of having negative values, which is a dire scenario usually indicating messages are being skipped.

## Setup

### Installation

The Agent's Kafka consumer check is included in the [Datadog Agent][2] package. No additional installation is needed on your Kafka nodes.

### Configuration

<!-- xxx tabs xxx -->
<!-- xxx tab "Host" xxx -->

#### Host

To configure this check for an Agent running on a host:

##### Metric collection

1. Edit the `kafka_consumer.d/conf.yaml` file, in the `conf.d/` folder at the root of your [Agent's configuration directory][3]. See the [sample kafka_consumer.d/conf.yaml][4] for all available configuration options.

2. [Restart the Agent][5].

##### Log collection

<!-- partial
{{< site-region region="us3" >}}
**Log collection is not supported for the Datadog {{< region-param key="dd_site_name" >}} site**.
{{< /site-region >}}
partial -->

This check does not collect additional logs. To collect logs from Kafka brokers, see [log collection instructions for Kafka][6].

<!-- xxz tab xxx -->
<!-- xxx tab "Containerized" xxx -->

#### Containerized

For containerized environments, see the [Autodiscovery with JMX][7] guide.

<!-- xxz tab xxx -->
<!-- xxz tabs xxx -->

### Validation

[Run the Agent's status subcommand][8] and look for `kafka_consumer` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][9] for a list of metrics provided by this check.

### Events

**consumer_lag**:<br>
The Datadog Agent emits an event when the value of the `consumer_lag` metric goes below 0, tagging it with `topic`, `partition` and `consumer_group`.

### Service Checks

The Kafka-consumer check does not include any service checks.

## Troubleshooting

- [Troubleshooting and Deep Dive for Kafka][10]
- [Agent failed to retrieve RMIServer stub][11]

## Further Reading

- [Monitoring Kafka performance metrics][13]
- [Collecting Kafka performance metrics][14]
- [Monitoring Kafka with Datadog][15]

[1]: https://raw.githubusercontent.com/DataDog/integrations-core/master/kafka_consumer/images/kafka_dashboard.png
[2]: https://app.datadoghq.com/account/settings#agent
[3]: https://docs.datadoghq.com/agent/guide/agent-configuration-files/#agent-configuration-directory
[4]: https://github.com/DataDog/integrations-core/blob/master/kafka_consumer/datadog_checks/kafka_consumer/data/conf.yaml.example
[5]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[6]: https://docs.datadoghq.com/integrations/kafka/#log-collection
[7]: https://docs.datadoghq.com/agent/guide/autodiscovery-with-jmx/?tab=containerizedagent
[8]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[9]: https://github.com/DataDog/integrations-core/blob/master/kafka_consumer/metadata.csv
[10]: https://docs.datadoghq.com/integrations/faq/troubleshooting-and-deep-dive-for-kafka/
[11]: https://docs.datadoghq.com/integrations/faq/agent-failed-to-retrieve-rmierver-stub/
[13]: https://www.datadoghq.com/blog/monitoring-kafka-performance-metrics
[14]: https://www.datadoghq.com/blog/collecting-kafka-performance-metrics
[15]: https://www.datadoghq.com/blog/monitor-kafka-with-datadog
