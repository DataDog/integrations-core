# Agent Check: Kafka Consumer

## Overview

This Agent check only collects metrics for message offsets. If you want to collect metrics about the Kafka brokers themselves, see the kafka check.

This check fetches the highwater offsets from the Kafka brokers, consumer offsets for old-style consumers that store their offsets in zookeeper, and the calculated consumer lag (which is the difference between those two metrics).

This check does NOT support Kafka versions > 0.8—it can't collect consumer offsets for new-style consumer groups which store their offsets in Kafka. If run such a version of Kafka, track [this issue on GitHub](https://github.com/DataDog/integrations-core/issues/457).

## Setup
### Installation

The Agent's Kafka consumer check is packaged with the Agent, so simply [install the Agent](https://app.datadoghq.com/account/settings#agent) on your Kafka nodes. If you need the newest version of the check, install the `dd-check-kafka-consumer` package.

### Configuration

Create a `kafka_consumer.yaml` file using [this sample conf file](https://github.com/DataDog/integrations-core/blob/master/kafka_consumer/conf.yaml.example) as an example. Then restart the Datadog Agent to start sending metrics to Datadog.

### Validation

Run the Agent's `info` subcommand and look for `kafka_consumer` under the Checks section:

```
  Checks
  ======
    [...]

    kafka_consumer
    -------
      - instance #0 [OK]
      - Collected 26 metrics, 0 events & 1 service check

    [...]
```

## Compatibility

The kafka_consumer check is compatible with all major platforms.

## Data Collected
### Metrics
See [metadata.csv](https://github.com/DataDog/integrations-core/blob/master/kafka_consumer/metadata.csv) for a list of metrics provided by this check.

### Events
The Kafka-consumer check does not include any event at this time.

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
To get a better idea of how (or why) to monitor Kafka consumer performance metrics with Datadog, check out our [series of blog posts](https://www.datadoghq.com/blog/monitoring-kafka-performance-metrics/) about it.
