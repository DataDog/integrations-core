# Agent Check: Kafka

## Overview

Connect Kafka to Datadog in order to:

* Visualize the performance of your cluster in real time
* Correlate the performance of Kafka with the rest of your applications

This check has a limit of 350 metrics per instance. The number of returned metrics is indicated in the info page. You can specify the metrics you are interested in by editing the configuration below. To learn how to customize the metrics to collect visit the [JMX Checks documentation](/integrations/java) for more detailed instructions.

To collect Kafka consumer metrics, see the kafka_consumer check.

## Installation

The Agent's Kafka check is packaged with the Agent, so simply [install the Agent](https://app.datadoghq.com/account/settings#agent) on your Kafka nodes.

The check collects metrics via JMX, so you'll need a JVM on each kafka node so the Agent can fork [jmxfetch](https://github.com/DataDog/jmxfetch). You can use the same JVM that Kafka uses.

## Configuration

**The following instructions are for the Datadog agent >= 5.0. For agents before that, refer to the [older documentation](https://github.com/DataDog/dd-agent/wiki/Deprecated-instructions-to-install-python-dependencies-for-the-Datadog-Agent).**

Configure a `kafka.yaml` in the Datadog Agent's `conf.d` directory. Kafka bean names depend on the exact Kafka version you're running. You should always use the example that comes packaged with the Agent as a base since that will be the most up-to-date configuration. Use [this sample conf file](https://github.com/DataDog/integrations-core/blob/master/kafka/conf.yaml.example) as an example, but note that the version there may be for a newer version of the Agent than what you've got installed.

After you've configured `kafka.yaml`, restart the Agent to begin sending Kafka metrics to Datadog.

## Validation

Run the Agent's `info` subcommand and look for `kafka` under the Checks section:

```
  Checks
  ======
    [...]

    kafka-localhost-9999
    -------
      - instance #0 [OK]
      - Collected 8 metrics, 0 events & 0 service checks

    [...]
```

## Compatibility

The kafka check is compatible with all major platforms.

## Metrics

See [metadata.csv](https://github.com/DataDog/integrations-core/blob/master/kafka/metadata.csv) for a list of metrics provided by this check.

## Further Reading

To get a better idea of how (or why) to monitor Kafka performance metrics with Datadog, check out our [series of blog posts](https://www.datadoghq.com/blog/monitoring-kafka-performance-metrics/) about it.
