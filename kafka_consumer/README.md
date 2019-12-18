# Agent Check: Kafka Consumer

![Kafka Dashboard][111]

## Overview

This Agent check only collects metrics for message offsets. If you want to collect JMX metrics from the Kafka brokers or Java-based consumers/producers, see the kafka check.

This check fetches the highwater offsets from the Kafka brokers, consumer offsets that are stored in kafka or zookeeper (for old-style consumers), and the calculated consumer lag (which is the difference between the broker offset and the consumer offset).

**Note:** This integration ensures that consumer offsets are checked before broker offsets because worst case is that consumer lag is a little overstated. Doing it the other way around can understate consumer lag to the point of having negative values, which is a dire scenario usually indicating messages are being skipped.

## Setup

Follow the instructions below to install and configure this check for an Agent running on a host. For containerized environments, see the [Autodiscovery Integration Templates][112] for guidance on applying these instructions.

### Installation

The Agent's Kafka consumer check is included in the [Datadog Agent][113] package, so you don't need to install anything else on your Kafka nodes.

### Configuration

Create a `kafka_consumer.yaml` file using [this sample configuration file][114] as an example. Then [restart the Datadog Agent][115] to start sending metrics to Datadog.

### Validation

[Run the Agent's `status` subcommand][116] and look for `kafka_consumer` under the Checks section.

## Data Collected
### Metrics
See [metadata.csv][117] for a list of metrics provided by this check.

### Events

`consumer_lag`:

The Datadog Agent emits an event when the value of the `consumer_lag` metric goes below 0, tagging it with `topic`,
`partition` and `consumer_group`.

### Service Checks
The Kafka-consumer check does not include any service checks.

## Troubleshooting

* [Troubleshooting and Deep Dive for Kafka][118]
* [Agent failed to retrieve RMIServer stub][119]
* [Producer and Consumer metrics don't appear in my Datadog application][120]

## Further Reading

* [Monitoring Kafka performance metrics][121]
* [Collecting Kafka performance metrics][122]
* [Monitoring Kafka with Datadog][123]

[111]: https://raw.githubusercontent.com/DataDog/integrations-core/master/kafka_consumer/images/kafka_dashboard.png
[112]: https://docs.datadoghq.com/agent/autodiscovery/integrations
[113]: https://app.datadoghq.com/account/settings#agent
[114]: https://github.com/DataDog/integrations-core/blob/master/kafka_consumer/datadog_checks/kafka_consumer/data/conf.yaml.example
[115]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[116]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[117]: https://github.com/DataDog/integrations-core/blob/master/kafka_consumer/metadata.csv
[118]: https://docs.datadoghq.com/integrations/faq/troubleshooting-and-deep-dive-for-kafka
[119]: https://docs.datadoghq.com/integrations/faq/agent-failed-to-retrieve-rmierver-stub
[120]: https://docs.datadoghq.com/integrations/faq/producer-and-consumer-metrics-don-t-appear-in-my-datadog-application
[121]: https://www.datadoghq.com/blog/monitoring-kafka-performance-metrics
[122]: https://www.datadoghq.com/blog/collecting-kafka-performance-metrics
[123]: https://www.datadoghq.com/blog/monitor-kafka-with-datadog
