# Agent Check: Kafka Consumer

![Kafka Dashboard][11]

## Overview

This Agent check only collects metrics for message offsets. If you want to collect JMX metrics from the Kafka brokers or Java-based consumers/producers, see the kafka check.

This check fetches the highwater offsets from the Kafka brokers, consumer offsets that are stored in kafka or zookeeper (for old-style consumers), and the calculated consumer lag (which is the difference between the broker offset and the consumer offset).

## Setup
### Installation

The Agent's Kafka consumer check is included in the [Datadog Agent][12] package, so you don't need to install anything else on your Kafka nodes.

### Configuration

Create a `kafka_consumer.yaml` file using [this sample configuration file][13] as an example. Then [restart the Datadog Agent][14] to start sending metrics to Datadog.

### Validation

[Run the Agent's `status` subcommand][15] and look for `kafka_consumer` under the Checks section.

## Data Collected
### Metrics
See [metadata.csv][16] for a list of metrics provided by this check.

### Events

`consumer_lag`:

The Datadog Agent emits an event when the value of the `consumer_lag` metric goes below 0, tagging it with `topic`,
`partition` and `consumer_group`.

### Service Checks
The Kafka-consumer check does not include any service checks.

## Troubleshooting

* [Troubleshooting and Deep Dive for Kafka][17]
* [Agent failed to retrieve RMIServer stub][18]
* [Producer and Consumer metrics don't appear in my Datadog application][19]

## Further Reading

* [Monitoring Kafka performance metrics][110]
* [Collecting Kafka performance metrics][111]
* [Monitoring Kafka with Datadog][112]


[11]: https://raw.githubusercontent.com/DataDog/integrations-core/master/kafka_consumer/images/kafka_dashboard.png
[12]: https://app.datadoghq.com/account/settings#agent
[13]: https://github.com/DataDog/integrations-core/blob/master/kafka_consumer/datadog_checks/kafka_consumer/data/conf.yaml.example
[14]: https://docs.datadoghq.com/agent/guide/agent-commands/?tab=agentv6#start-stop-and-restart-the-agent
[15]: https://docs.datadoghq.com/agent/guide/agent-commands/?tab=agentv6#agent-status-and-information
[16]: https://github.com/DataDog/integrations-core/blob/master/kafka_consumer/metadata.csv
[17]: https://docs.datadoghq.com/integrations/faq/troubleshooting-and-deep-dive-for-kafka
[18]: https://docs.datadoghq.com/integrations/faq/agent-failed-to-retrieve-rmierver-stub
[19]: https://docs.datadoghq.com/integrations/faq/producer-and-consumer-metrics-don-t-appear-in-my-datadog-application
[110]: https://www.datadoghq.com/blog/monitoring-kafka-performance-metrics
[111]: https://www.datadoghq.com/blog/collecting-kafka-performance-metrics
[112]: https://www.datadoghq.com/blog/monitor-kafka-with-datadog
