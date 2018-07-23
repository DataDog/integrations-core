# Agent Check: Kafka Consumer

![Kafka Dashboard][109]

## Overview

This Agent check only collects metrics for message offsets. If you want to collect JMX metrics from the Kafka brokers or Java-based consumers/producers, see the kafka check.

This check fetches the highwater offsets from the Kafka brokers, consumer offsets that are stored in kafka or zookeeper (for old-style consumers), and the calculated consumer lag (which is the difference between the broker offset and the consumer offset).

## Setup
### Installation

The Agent's Kafka consumer check is included in the [Datadog Agent][101] package, so you don't need to install anything else on your Kafka nodes.

### Configuration

Create a `kafka_consumer.yaml` file using [this sample configuration file][102] as an example. Then [restart the Datadog Agent][108] to start sending metrics to Datadog.

### Validation

[Run the Agent's `status` subcommand][103] and look for `kafka_consumer` under the Checks section.

## Data Collected
### Metrics
See [metadata.csv][104] for a list of metrics provided by this check.

### Events

`consumer_lag`:

The Datadog Agent emits an event when the value of the `consumer_lag` metric goes below 0, tagging it with `topic`,
`partition` and `consumer_group`.

### Service Checks
The Kafka-consumer check does not include any service checks at this time.

## Troubleshooting

* [Troubleshooting and Deep Dive for Kafka][24]
* [Agent failed to retrieve RMIServer stub][25]
* [Producer and Consumer metrics don't appear in my Datadog application][26]

## Further Reading

* [Monitoring Kafka performance metrics][105]
* [Collecting Kafka performance metrics][106]
* [Monitoring Kafka with Datadog][107]


[101]: https://app.datadoghq.com/account/settings#agent
[102]: https://github.com/DataDog/integrations-core/blob/master/kafka_consumer/datadog_checks/kafka_consumer/data/conf.yaml.example
[103]: https://docs.datadoghq.com/agent/faq/agent-commands/#agent-status-and-information
[104]: https://github.com/DataDog/integrations-core/blob/master/kafka_consumer/metadata.csv
[105]: https://www.datadoghq.com/blog/monitoring-kafka-performance-metrics/
[106]: https://www.datadoghq.com/blog/collecting-kafka-performance-metrics/
[107]: https://www.datadoghq.com/blog/monitor-kafka-with-datadog/
[108]: https://docs.datadoghq.com/agent/faq/agent-commands/#start-stop-restart-the-agent
[109]: https://raw.githubusercontent.com/DataDog/integrations-core/master/kafka_consumer/images/kafka_dashboard.png
