# Overview

Get metrics from ActiveMQ in real time to

* Visualize your web ActiveMQ server performance
* Correlate the performance of ActiveMQ with the rest of your applications

# Installation

The ActiveMQ check is included in the Datadog Agent package, so simply install the Agent on your ActiveMQ servers.

Metrics will be captured using a JMX connection. We recommend the use of Oracle’s JDK for this integration.

# Configuration

Enable JMX Remote on your ActiveMQ server.

Create a file `activemq.yaml` in the Datadog Agent's `conf.d` directory:

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

Restart the Datadog Agent to begin sending ActiveMQ metrics to Datadog.

# Validation

Run the Agent's `info` subcommand and look for `activemq` under the Checks section:

```
  Checks
  ======
    [...]

    activemq
    -------
      - instance #0 [OK]
      - Collected 26 metrics, 0 events & 1 service check

    [...]
```

# Troubleshooting

# Compatibility

The ActiveMQ check is compatible with Linux and macOS.

# Metrics

See [metadata.csv](https://github.com/DataDog/integrations-core/blob/master/activemq/metadata.csv) for a list of metrics provided by this integration.

# Events

# Service Checks

