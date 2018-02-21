# Agent Check: Kafka

## Overview

Connect Kafka to Datadog in order to:

* Visualize the performance of your cluster in real time
* Correlate the performance of Kafka with the rest of your applications

This check has a limit of 350 metrics per instance. The number of returned metrics is indicated in the info page. You can specify the metrics you are interested in by editing the configuration below. To learn how to customize the metrics to collect visit the [JMX Checks documentation](https://docs.datadoghq.com/integrations/java/) for more detailed instructions.

To collect Kafka consumer metrics, see the [kafka_consumer check](https://docs.datadoghq.com/integrations/kafka/).

## Setup
### Installation

The Agent's Kafka check is packaged with the Agent, so simply [install the Agent](https://app.datadoghq.com/account/settings#agent) on your Kafka nodes.

If you need the newest version of the Kafka check, install the `dd-check-kafka` package; this package's check overrides the one packaged with the Agent. See the [integrations-core repository README.md for more details](https://github.com/DataDog/integrations-core#installing-the-integrations).

The check collects metrics via JMX, so you'll need a JVM on each kafka node so the Agent can fork [jmxfetch](https://github.com/DataDog/jmxfetch). You can use the same JVM that Kafka uses.

### Configuration

**The following instructions are for the Datadog agent >= 5.0. For agents before that, refer to the [older documentation](https://github.com/DataDog/dd-agent/wiki/Deprecated-instructions-to-install-python-dependencies-for-the-Datadog-Agent).**

Configure a `kafka.yaml` in the Datadog Agent's `conf.d` directory. Kafka bean names depend on the exact Kafka version you're running. You should always use the example that comes packaged with the Agent as a base since that will be the most up-to-date configuration. Use [this sample conf file](https://github.com/DataDog/integrations-core/blob/master/kafka/conf.yaml.example) as an example, but note that the version there may be for a newer version of the Agent than what you've got installed.

After you've configured `kafka.yaml`, [restart the Agent](https://docs.datadoghq.com/agent/faq/start-stop-restart-the-datadog-agent) to begin sending Kafka metrics to Datadog.

### Validation

[Run the Agent's `status` subcommand](https://docs.datadoghq.com/agent/faq/agent-status-and-information/) and look for `kafka` under the Checks section:

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

## Data Collected
### Metrics
See [metadata.csv](https://github.com/DataDog/integrations-core/blob/master/kafka/metadata.csv) for a list of metrics provided by this check.

### Events
The Kafka check does not include any event at this time.

### Service Checks
The Kafka check does not include any service check at this time.



## Troubleshooting

* [Troubleshooting and Deep Dive for Kafka](https://docs.datadoghq.com/integrations/faq/troubleshooting-and-deep-dive-for-kafka)
* [Agent failed to retrieve RMIServer stub](https://docs.datadoghq.com/integrations/faq/agent-failed-to-retrieve-rmierver-stub)
* [Producer and Consumer metrics don't appear in my Datadog application](https://docs.datadoghq.com/integrations/faq/producer-and-consumer-metrics-don-t-appear-in-my-datadog-application)

## Further Reading

* [Monitoring Kafka performance metrics](https://www.datadoghq.com/blog/monitoring-kafka-performance-metrics/)
* [Collecting Kafka performance metrics](https://www.datadoghq.com/blog/collecting-kafka-performance-metrics/)
* [Monitoring Kafka with Datadog](https://www.datadoghq.com/blog/monitor-kafka-with-datadog/)
