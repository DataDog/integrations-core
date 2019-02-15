# Agent Check: Kafka Consumer

![Kafka Dashboard][111]

## Overview

This Agent check only collects metrics for message offsets. If you want to collect JMX metrics from the Kafka brokers or Java-based consumers/producers, see the kafka check.

This check fetches the highwater offsets from the Kafka brokers, consumer offsets that are stored in kafka or zookeeper (for old-style consumers), and the calculated consumer lag (which is the difference between the broker offset and the consumer offset).

## Setup
### Installation

The Agent's Kafka consumer check is included in the [Datadog Agent][112] package, so you don't need to install anything else on your Kafka nodes.

### Configuration

Create a `kafka_consumer.yaml` file using [this sample configuration file][113] as an example. Then [restart the Datadog Agent][114] to start sending metrics to Datadog.

### Validation

[Run the Agent's `status` subcommand][115] and look for `kafka_consumer` under the Checks section.

## Data Collected
### Metrics
See [metadata.csv][116] for a list of metrics provided by this check.

### Events

`consumer_lag`:

The Datadog Agent emits an event when the value of the `consumer_lag` metric goes below 0, tagging it with `topic`,
`partition` and `consumer_group`.

### Service Checks
The Kafka-consumer check does not include any service checks.

## Troubleshooting

* [Troubleshooting and Deep Dive for Kafka][117]
* [Agent failed to retrieve RMIServer stub][118]
* [Producer and Consumer metrics don't appear in my Datadog application][119]

## Further Reading

* [Monitoring Kafka performance metrics][120]
* [Collecting Kafka performance metrics][121]
* [Monitoring Kafka with Datadog][122]


[111]: https://raw.githubusercontent.com/DataDog/integrations-core/master/kafka_consumer/images/kafka_dashboard.png
[112]: https://app.datadoghq.com/account/settings#agent
[113]: https://github.com/DataDog/integrations-core/blob/master/kafka_consumer/datadog_checks/kafka_consumer/data/conf.yaml.example
[114]: https://docs.datadoghq.com/agent/faq/agent-commands/#start-stop-restart-the-agent
[115]: https://docs.datadoghq.com/agent/faq/agent-commands/#agent-status-and-information
[6]: https://github.com/DataDog/integrations-core/blob/master/kafka_consumer/metadata.csv
[117]: https://docs.datadoghq.com/integrations/faq/troubleshooting-and-deep-dive-for-kafka/
[118]: https://docs.datadoghq.com/integrations/faq/agent-failed-to-retrieve-rmierver-stub/
[119]: https://docs.datadoghq.com/integrations/faq/producer-and-consumer-metrics-don-t-appear-in-my-datadog-application/
[120]: https://www.datadoghq.com/blog/monitoring-kafka-performance-metrics
[121]: https://www.datadoghq.com/blog/collecting-kafka-performance-metrics
[122]: https://www.datadoghq.com/blog/monitor-kafka-with-datadog
