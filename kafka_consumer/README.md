# kafka_consumer Integration

# Overview

This Agent check only collects metrics for Kafka broker offset, consumer offset, and consumer lag. If you want to collect many more Kafka metrics, see the kafka check.

# Installation

The Agent's Kafka consumer check is packaged with the Agent, so simply [install the Agent](https://app.datadoghq.com/account/settings#agent) on your Kafka nodes. If you need the newest version of the check, install the `dd-check-kafka-consumer` package.

# Configuration

Create a `kafka.yaml` in the Datadog Agent's `conf.d` directory:

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
