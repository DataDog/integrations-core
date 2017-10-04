# Agent Check: Kafka

## Overview

Connect Kafka to Datadog in order to:

* Visualize the performance of your cluster in real time
* Correlate the performance of Kafka with the rest of your applications

This check has a limit of 350 metrics per instance. The number of returned metrics is indicated in the info page. You can specify the metrics you are interested in by editing the configuration below. To learn how to customize the metrics to collect visit the [JMX Checks documentation](/integrations/java) for more detailed instructions.

To collect Kafka consumer metrics, see the [kafka_consumer check](https://docs.datadoghq.com/integrations/kafka_consumer/).

## Setup
### Installation

The Agent's Kafka check is packaged with the Agent, so simply [install the Agent](https://app.datadoghq.com/account/settings#agent) on your Kafka nodes.

The check collects metrics via JMX, so you'll need a JVM on each kafka node so the Agent can fork [jmxfetch](https://github.com/DataDog/jmxfetch). You can use the same JVM that Kafka uses.

### Configuration

**The following instructions are for the Datadog agent >= 5.0. For agents before that, refer to the [older documentation](https://github.com/DataDog/dd-agent/wiki/Deprecated-instructions-to-install-python-dependencies-for-the-Datadog-Agent).**

Configure a `kafka.yaml` in the Datadog Agent's `conf.d` directory. Kafka bean names depend on the exact Kafka version you're running. You should always use the example that comes packaged with the Agent as a base since that will be the most up-to-date configuration. Use [this sample conf file](https://github.com/DataDog/integrations-core/blob/master/kafka/conf.yaml.example) as an example, but note that the version there may be for a newer version of the Agent than what you've got installed.

After you've configured `kafka.yaml`, restart the Agent to begin sending Kafka metrics to Datadog.

### Validation

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

## Data Collected
### Metrics
See [metadata.csv](https://github.com/DataDog/integrations-core/blob/master/kafka/metadata.csv) for a list of metrics provided by this check.

### Events
The Kafka check does not include any event at this time.

### Service Checks
The Kafka check does not include any service check at this time.



## Troubleshooting
### Agent failed to retrieve RMIServer stub

```
instance #kafka-localhost-<PORT_NUM> [ERROR]: 'Cannot connect to instance localhost:<PORT_NUM>. java.io.IOException: Failed to retrieve RMIServer stub
```

The Datadog Agent is unable to connect to the Kafka instance to retrieve metrics from the exposed mBeans over the RMI protocol.

Include the following JVM arguments when starting the Kafka instance to solve resolve this issue *(required for Producer, Consumer, and Broker as they are all separate Java instances)*

```
-Dcom.sun.management.jmxremote.port=<PORT_NUM> -Dcom.sun.management.jmxremote.rmi.port=<PORT_NUM>
```

### Producer and Consumer metrics don't appear in my Datadog application
By default we only collect broker based metrics. 

If you're running Java based Producers and Consumers, uncomment this section of the yaml file and point the Agent to the proper ports to start pulling in metrics:

```yaml
# - host: remotehost
    # port: 9998 # Producer
    # tags:
    # kafka: producer0
    # env: stage
    # newTag: test
    # - host: remotehost
    # port: 9997 # Consumer
    # tags:
    # kafka: consumer0
    # env: stage
    # newTag: test
```

If you are using custom Producer and Consumer clients that are not written in Java and/or not exposing mBeans, having this enabled would still collect zero metrics. To still submit your metrics from your code use [dogstatsd](https://docs.datadoghq.com/guides/dogstatsd/).

## Further Reading
To get a better idea of how (or why) to monitor Kafka performance metrics with Datadog, check out our [series of blog posts](https://www.datadoghq.com/blog/monitoring-kafka-performance-metrics/) about it.
