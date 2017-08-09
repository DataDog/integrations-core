# Agent Check: Kafka Consumer

# Overview

This Agent check only collects metrics for message offsets. If you want to collect metrics about the Kafka brokers themselves, see the kafka check.

This check fetches the highwater offsets from the Kafka brokers, consumer offsets for old-style consumers that store their offsets in zookeeper, and the calculated consumer lag (which is the difference between those two metrics).

This check does NOT support Kafka versions > 0.8—it can't collect consumer offsets for new-style consumer groups which store their offsets in Kafka. If run such a version of Kafka, track [this issue on GitHub](https://github.com/DataDog/integrations-core/issues/457).

# Installation

The Agent's Kafka consumer check is packaged with the Agent, so simply [install the Agent](https://app.datadoghq.com/account/settings#agent) on your Kafka nodes. If you need the newest version of the check, install the `dd-check-kafka-consumer` package.

# Configuration

Create a `kafka_consumer.yaml` in the Datadog Agent's `conf.d` directory:

```
init_config:
#  Customize the ZooKeeper connection timeout here
#  zk_timeout: 5
#  Customize the Kafka connection timeout here
#  kafka_timeout: 5

instances:
  # - kafka_connect_str: localhost:9092
  #   zk_connect_str: localhost:2181
  #   zk_prefix: /0.8
  #   consumer_groups:
  #     my_consumer:
  #       my_topic: [0, 1, 4, 12]
```

# Validation

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

# Compatibility

The kafka_consumer check is compatible with all major platforms

# Metrics

See [metadata.csv](https://github.com/DataDog/integrations-core/blob/master/kafka_consumer/metadata.csv) for a list of metrics provided by this check.
