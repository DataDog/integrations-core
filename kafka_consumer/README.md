# Agent Check: Kafka Consumer

## Overview

This Agent check only collects metrics for message offsets. If you want to collect JMX metrics from the Kafka brokers or Java-based consumers/producers, see the kafka check.

This check fetches the highwater offsets from the Kafka brokers, consumer offsets that are stored in kafka or zookeeper (for old-style consumers), and the calculated consumer lag (which is the difference between the broker offset and the consumer offset).

## Setup
### Installation

The Agent's Kafka consumer check is packaged with the Agent, so simply [install the Agent][1] on your Kafka nodes.

### Configuration

Create a `kafka_consumer.yaml` file using [this sample conf file][2] as an example. Then restart the Datadog Agent to start sending metrics to Datadog.

### Validation

[Run the Agent's `status` subcommand][3] and look for `kafka_consumer` under the Checks section.

## Data Collected
### Metrics
See [metadata.csv][4] for a list of metrics provided by this check.

### Events

`consumer_lag`:

The Datadog Agent emits an event when the value of the `consumer_lag` metric goes below 0, tagging it with `topic`,
`partition` and `consumer_group`.

### Service Checks
The Kafka-consumer check does not include any service check at this time.

## Troubleshooting
### Specifying a non existent partition in your kafka_Consumer.yaml file
If you get this error in your info.log:
```
instance - #0 [Error]: ''
```

Specify the specific partition of your environment for your topic in your kafka_Consumer.yaml file:
```
#my_topic [0, 1, 4, 12]
```

## Further Reading

## Further Reading

* [Monitoring Kafka performance metrics][5]
* [Collecting Kafka performance metrics][6]
* [Monitoring Kafka with Datadog][7]


[1]: https://app.datadoghq.com/account/settings#agent
[2]: https://github.com/DataDog/integrations-core/blob/master/kafka_consumer/conf.yaml.example
[3]: https://docs.datadoghq.com/agent/faq/agent-commands/#agent-status-and-information
[4]: https://github.com/DataDog/integrations-core/blob/master/kafka_consumer/metadata.csv
[5]: https://www.datadoghq.com/blog/monitoring-kafka-performance-metrics/
[6]: https://www.datadoghq.com/blog/collecting-kafka-performance-metrics/
[7]: https://www.datadoghq.com/blog/monitor-kafka-with-datadog/
