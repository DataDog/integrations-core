# Activemq Integration

## Overview

The ActiveMQ check lets you collect metrics for brokers and queues, producers and consumers, and more.

## Setup
### Installation

The Agent's ActiveMQ check is packaged with the Agent, so simply [install the Agent](https://app.datadoghq.com/account/settings#agent) on your ActiveMQ nodes.  

If you need the newest version of the ActiveMQ check, install the `dd-check-activemq` package; this package's check overrides the one packaged with the Agent. See the [integrations-core repository README.md for more details](https://github.com/DataDog/integrations-core#installing-the-integrations).

The check collects metrics via JMX, so you'll need a JVM on each node so the Agent can fork [jmxfetch](https://github.com/DataDog/jmxfetch). We recommend using an Oracle-provided JVM.

### Configuration

1. **Make sure that [JMX Remote is enabled](http://activemq.apache.org/jmx.html) on your ActiveMQ server.**
2. Configure the agent to connect to ActiveMQ. Edit `${confd_help('`conf.d/activemq.yaml`')}`. See the [sample activemq.yaml](https://github.com/DataDog/integrations-core/blob/master/activemq/conf.yaml.example) for all available configuration options.

```
instances:
  - host: localhost
    port: 7199
    user: username
    password: password
    name: activemq_instance
# List of metrics to be collected by the integration
# You should not have to modify this.
init_config:
  conf:
    - include:
      Type: Queue
      attribute:
        AverageEnqueueTime:
          alias: activemq.queue.avg_enqueue_time
          metric_type: gauge
        ConsumerCount:
          alias: activemq.queue.consumer_count
          metric_type: gauge
        ProducerCount:
          alias: activemq.queue.producer_count
          metric_type: gauge
        MaxEnqueueTime:
          alias: activemq.queue.max_enqueue_time
          metric_type: gauge
        MinEnqueueTime:
          alias: activemq.queue.min_enqueue_time
          metric_type: gauge
        MemoryPercentUsage:
          alias: activemq.queue.memory_pct
          metric_type: gauge
        QueueSize:
          alias: activemq.queue.size
          metric_type: gauge
        DequeueCount:
          alias: activemq.queue.dequeue_count
          metric_type: counter
        DispatchCount:
          alias: activemq.queue.dispatch_count
          metric_type: counter
        EnqueueCount:
          alias: activemq.queue.enqueue_count
          metric_type: counter
        ExpiredCount:
          alias: activemq.queue.expired_count
          type: counter
        InFlightCount:
          alias: activemq.queue.in_flight_count
          metric_type: counter

    - include:
      Type: Broker
      attribute:
        StorePercentUsage:
          alias: activemq.broker.store_pct
          metric_type: gauge
        TempPercentUsage:
          alias: activemq.broker.temp_pct
          metric_type: gauge
        MemoryPercentUsage:
          alias: activemq.broker.memory_pct
          metric_type: gauge
```

3. Restart the agent

```bash
sudo /etc/init.d/datadog-agent restart


if [ $(sudo supervisorctl status | egrep "datadog-agent.*RUNNING" | wc -l) == 3 ]; \
then echo -e "\e[0;32mAgent is running\e[0m"; \
else echo -e "\e[031mAgent is not running\e[0m"; fi
```

{{< insert-example-links check="none" >}}

### Validation

[Run the Agent's `info` subcommand](https://docs.datadoghq.com/agent/faq/agent-status-and-information/) and look for `activemq` under the Checks section:

```
  Checks
  ======
    [...]

    activemq
    -------
      - instance #0 [OK]
      - Collected 8 metrics, 0 events & 0 service checks

    [...]
```

## Compatibility

The ActiveMQ check only runs on Linux or Mac (OS X or macOS).

## Data Collected
### Metrics
See [metadata.csv](https://github.com/DataDog/integrations-core/blob/master/activemq/metadata.csv) for a list of metrics provided by this integration.

### Events
The Activemq check does not include any event at this time.

### Service Checks
The Activemq check does not include any service check at this time.

## Troubleshooting
Need help? Contact [Datadog Support](http://docs.datadoghq.com/help/).

## Further Reading

* [Monitor ActiveMQ metrics and performance](https://www.datadoghq.com/blog/monitor-activemq-metrics-performance/)
