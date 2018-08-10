# Activemq Integration

## Overview

The ActiveMQ check lets you collect metrics for brokers and queues, producers and consumers, and more.

**Note**: If you are running a ActiveMQ version older than 5.8.0, refer to [Agent 5.10.x released sample files][110].

## Setup
### Installation

The Agent's ActiveMQ check is included in the [Datadog Agent][101] package, so you don't need to install anything else on your ActiveMQ nodes.

The check collects metrics via JMX, so you need a JVM on each node so the Agent can fork [jmxfetch][102]. We recommend using an Oracle-provided JVM.

### Configuration

1. **Make sure that [JMX Remote is enabled][103] on your ActiveMQ server.**
2. Configure the agent to connect to ActiveMQ. Edit `activemq.d/conf.yaml` file, in the `conf.d/` folder at the root of your [Agent's configuration directory][111]. See the [sample activemq.d/conf.yaml][104] for all available configuration options.

      ```yaml
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

3. [Restart the agent][109]

### Validation

[Run the Agent's `status` subcommand][105] and look for `activemq` under the Checks section.

## Data Collected
### Metrics
The ActiveMQ check does not include any metrics at this time.

### Events
The ActiveMQ check does not include any events at this time.

### Service Checks
**activemq.can_connect**:

Returns `CRITICAL` if the Agent is unable to connect to and collect metrics from the monitored ActiveMQ instance. Returns `OK` otherwise.

## Troubleshooting
Need help? Contact [Datadog Support][107].

## Further Reading

* [Monitor ActiveMQ metrics and performance][108]


[101]: https://app.datadoghq.com/account/settings#agent
[102]: https://github.com/DataDog/jmxfetch
[103]: https://activemq.apache.org/jmx.html
[104]: https://github.com/DataDog/integrations-core/blob/master/activemq/datadog_checks/activemq/data/conf.yaml.example
[105]: https://docs.datadoghq.com/agent/faq/agent-commands/#agent-status-and-information
[107]: https://docs.datadoghq.com/help/
[108]: https://www.datadoghq.com/blog/monitor-activemq-metrics-performance/
[109]: https://docs.datadoghq.com/agent/faq/agent-commands/#start-stop-restart-the-agent
[110]: https://raw.githubusercontent.com/DataDog/dd-agent/5.10.1/conf.d/activemq.yaml.example
[111]: https://docs.datadoghq.com/agent/faq/agent-configuration-files/#agent-configuration-directory
