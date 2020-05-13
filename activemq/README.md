# ActiveMQ Integration

## Overview

The ActiveMQ check collects metrics for brokers and queues, producers and consumers, and more.

**Note**: If you are running a ActiveMQ version older than 5.8.0, see the [Agent 5.10.x released sample files][1].

## Setup

### Installation

The Agent's ActiveMQ check is included in the [Datadog Agent][2] package, so you don't need to install anything else on your ActiveMQ nodes.

The check collects metrics via JMX, so you need a JVM on each node so the Agent can fork [jmxfetch][3]. We recommend using an Oracle-provided JVM.

### Configuration

#### Host

Follow the instructions below to configure this check for an Agent running on a host. For containerized environments, see the [Containerized](#containerized) section.

1. **Make sure that [JMX Remote is enabled][4] on your ActiveMQ server.**
2. Configure the agent to connect to ActiveMQ. Edit `activemq.d/conf.yaml`, in the `conf.d/` folder at the root of your [Agent's configuration directory][5]. See the [sample activemq.d/conf.yaml][6] for all available configuration options.

   ```yaml
   instances:
     - host: localhost
       port: 1616
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

3. [Restart the agent][7]

##### Log collection

_Available for Agent versions >6.0_

1. Collecting logs is disabled by default in the Datadog Agent, enable it in your `datadog.yaml` file:

   ```yaml
   logs_enabled: true
   ```

2. Add this configuration block to your `activemq.d/conf.yaml` file to start collecting your Riak logs:

   ```yaml
   logs:
     - type: file
       path: "<ACTIVEMQ_BASEDIR>/data/activemq.log"
       source: activemq
       service: "<SERVICE_NAME>"
     - type: file
       path: "<ACTIVEMQ_BASEDIR>/data/audit.log"
       source: activemq
       service: "<SERVICE_NAME>"
   ```

3. [Restart the Agent][7].

#### Containerized

For containerized environments, see the [Autodiscovery Integration Templates][13] for guidance on applying the parameters below.

##### Metric collection

| Parameter            | Value                                |
| -------------------- | ------------------------------------ |
| `<INTEGRATION_NAME>` | `activemq`                           |
| `<INIT_CONFIG>`      | blank or `{}`                        |
| `<INSTANCE_CONFIG>`  | `{"host": "%%host%%","port":"1099"}` |

##### Log collection

_Available for Agent versions >6.0_

Collecting logs is disabled by default in the Datadog Agent. To enable it, see [Kubernetes log collection documentation][14].

| Parameter      | Value                                                  |
| -------------- | ------------------------------------------------------ |
| `<LOG_CONFIG>` | `{"source": "activemq", "service": "<YOUR_APP_NAME>"}` |

### Validation

[Run the Agent's status subcommand][8] and look for `activemq` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][9] for a list of metrics provided by this integration.

### Events

The ActiveMQ check does not include any events.

### Service Checks

**activemq.can_connect**:<br>
Returns `CRITICAL` if the Agent is unable to connect to and collect metrics from the monitored ActiveMQ instance, otherwise returns `OK`.

## Troubleshooting

Need help? Contact [Datadog support][10].

## Further Reading

Additional helpful documentation, links, and articles:

- [ActiveMQ architecture and key metrics][11]
- [Monitor ActiveMQ metrics and performance][12]

[1]: https://raw.githubusercontent.com/DataDog/dd-agent/5.10.1/conf.d/activemq.yaml.example
[2]: https://app.datadoghq.com/account/settings#agent
[3]: https://github.com/DataDog/jmxfetch
[4]: https://activemq.apache.org/jmx.html
[5]: https://docs.datadoghq.com/agent/guide/agent-configuration-files/#agent-configuration-directory
[6]: https://github.com/DataDog/integrations-core/blob/master/activemq/datadog_checks/activemq/data/conf.yaml.example
[7]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[8]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[9]: https://github.com/DataDog/integrations-core/blob/master/activemq/metadata.csv
[10]: https://docs.datadoghq.com/help/
[11]: https://www.datadoghq.com/blog/activemq-architecture-and-metrics
[12]: https://www.datadoghq.com/blog/monitor-activemq-metrics-performance
[13]: https://docs.datadoghq.com/agent/kubernetes/integrations/
[14]: https://docs.datadoghq.com/agent/kubernetes/log/?tab=containerinstallation#setup
