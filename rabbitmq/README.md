# RabbitMQ Check

![RabbitMQ Dashboard][1]

## Overview

This check monitors [RabbitMQ][2] through the Datadog Agent. It allows you to:

- Track queue-based stats: queue size, consumer count, unacknowledged messages, redelivered messages, etc.
- Track node-based stats: waiting processes, used sockets, used file descriptors, etc.
- Monitor vhosts for aliveness and number of connections

And more.

## Setup

### Installation

The RabbitMQ check is included in the [Datadog Agent][3] package. No additional installation is needed on your server.

### Configuration

RabbitMQ exposes metrics in two ways: the [RabbitMQ Management Plugin][4] and the [Rabbitmq Prometheus Plugin][19]. The Datadog integration supports both versions. Please follow the configuration instruction in this file that pertain to the version you intend to use. The metrics accessible via the Prometheus plugin version of the integration are marked with [OpenMetricsV2] in their `metadata.csv` descriptions. The Datadog integration also comes with an out-of-the-box dashboard and monitors for each version, as labelled by the Dashboard and Monitor titles.

#### Prepare RabbitMQ

##### [RabbitMQ Prometheus Plugin][19].

*Starting with RabbitMQ v3.8, the [RabbitMQ Prometheus Plugin][19] is enabled by default and the integration communicates with it over HTTP API using OpenMetricsV2.*

*The Prometheus plugin version of RabbitMQ requires Python 3 support by the Datadog agent, and so can only be supported by Agent V6 onwards. Please ensure your agent is updated before configuring the Prometheus plugin version of the integration.*

Configure the `prometheus_plugin` section in your instance configuration. When using the `prometheus_plugin` option, settings related to the Management Plugin are ignored.

 ```yaml
 instances:
   - prometheus_plugin:
       url: http://<HOST>:15692
 ```

 This enables scraping of the [`/metrics` endpoint][20] on one RabbitMQ node. We can also collect data from the [`/metrics/detailed` endpoint][22].


##### [RabbitMQ Management Plugin][4].

Enable the plugin. The Agent user then needs at least the `monitoring` tag and these required permissions:

| Permission | Command            |
| ---------- | ------------------ |
| **conf**   | `^aliveness-test$` |
| **write**  | `^amq\.default$`   |
| **read**   | `.*`               |

Create an Agent user for your default vhost with the following commands:

```text
rabbitmqctl add_user datadog <SECRET>
rabbitmqctl set_permissions  -p / datadog "^aliveness-test$" "^amq\.default$" ".*"
rabbitmqctl set_user_tags datadog monitoring
```

Here, `/` refers to the default host. Set this to your specified virtual host name. See the [RabbitMQ documentation][5] for more information.

<!-- xxx tabs xxx -->
<!-- xxx tab "Host" xxx -->

#### Host

To configure this check for an Agent running on a host:

##### Metric collection

1. Edit the `rabbitmq.d/conf.yaml` file, in the `conf.d/` folder at the root of your [Agent's configuration directory][6] to start collecting your RabbitMQ metrics. See the [sample rabbitmq.d/conf.yaml][7] for all available configuration options.

    **Note**: The Agent checks all queues, vhosts, and nodes by default, but you can provide lists or regexes to limit this. See the [rabbitmq.d/conf.yaml][7] for examples.

2. [Restart the Agent][8].

##### Log collection

_Available for Agent versions >6.0_

1. To modify the default log file location either set the `RABBITMQ_LOGS` environment variable or add the following to your RabbitMQ configuration file (`/etc/rabbitmq/rabbitmq.conf`):

   ```conf
     log.dir = /var/log/rabbit
     log.file = rabbit.log
   ```

2. Collecting logs is disabled by default in the Datadog Agent, enable it in your `datadog.yaml` file:

   ```yaml
   logs_enabled: true
   ```

3. Edit the `logs` section of your `rabbitmq.d/conf.yaml` file to start collecting your RabbitMQ logs:

   ```yaml
   logs:
     - type: file
       path: /var/log/rabbit/*.log
       source: rabbitmq
       service: myservice
       log_processing_rules:
         - type: multi_line
           name: logs_starts_with_equal_sign
           pattern: "="
   ```

4. [Restart the Agent][8].

<!-- xxz tab xxx -->
<!-- xxx tab "Containerized" xxx -->

#### Containerized

You can take advantage of Datadog's [Docker container Autodiscovery][21], see the `auto_conf.yaml` example configuration for Rabbitmq-specific settings.

For container environments such as Kubernetes, see the [Autodiscovery Integration Templates][9] for guidance on applying the parameters below.

##### Metric collection

| Parameter            | Value                                        |
| -------------------- | -------------------------------------------- |
| `<INTEGRATION_NAME>` | `rabbitmq`                                   |
| `<INIT_CONFIG>`      | blank or `{}`                                |
| `<INSTANCE_CONFIG>`  | `{"prometheus_plugin": {"url": "%%host%%:15692"}}` |

##### Log collection

_Available for Agent versions >6.0_

Collecting logs is disabled by default in the Datadog Agent. To enable it, see [Kubernetes Log Collection][10].

| Parameter      | Value                                                                                                                                               |
| -------------- | --------------------------------------------------------------------------------------------------------------------------------------------------- |
| `<LOG_CONFIG>` | `{"source": "rabbitmq", "service": "rabbitmq", "log_processing_rules": [{"type":"multi_line","name":"logs_starts_with_equal_sign", "pattern": "="}]}` |

<!-- xxz tab xxx -->
<!-- xxz tabs xxx -->

### Validation

[Run the Agent's status subcommand][11] and look for `rabbitmq` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][12] for a list of metrics provided by this integration.

### Events

### Service Checks

See [service_checks.json][14] for a list of service checks provided by this integration.

## Troubleshooting

Need help? Contact [Datadog support][13].

## Further Reading

Additional helpful documentation, links, and articles:

- [Key metrics for RabbitMQ monitoring][15]
- [Collecting metrics with RabbitMQ monitoring tools][16]
- [Monitoring RabbitMQ performance with Datadog][17]

### Prometheus Plugin Migration Guide

The following table maps metrics coming from the Management plugin to their Prometheus plugin equivalents.

| Management Plugin metric                                                    | Prometheus Plugin Equivalent                                                                                                                | Endpoint            |
|----------------------------------------------------------------|-------------------------------------------------------------------------------------------------------------------------------|---------------------|
| rabbitmq.connections                                           | rabbitmq\_connections                                                                                                         |                     |
| rabbitmq.node.disk\_alarm                                      | rabbitmq\_alarms\_free\_disk\_space\_watermark                                                                                | /metrics            |
| rabbitmq.node.disk\_free                                       | rabbitmq\_disk\_space\_available\_bytes                                                                                       |                     |
| rabbitmq.node.fd\_used                                         | rabbitmq\_process\_open\_fds                                                                                                  |                     |
| rabbitmq.node.mem\_alarm                                       | rabbitmq\_alarms\_memory\_used\_watermark                                                                                     | /metrics            |
| rabbitmq.node.mem\_limit                                       | rabbitmq\_resident\_memory\_limit\_bytes                                                                                      |                     |
| rabbitmq.node.mem\_used                                        | rabbitmq\_process\_resident\_memory\_bytes                                                                                    |                     |
| rabbitmq.node.sockets\_used                                    | erlang\_vm\_port\_count                                                                                                       |                     |
| rabbitmq.overview.messages.confirm.count                       | rabbitmq\_global\_messages\_confirmed\_total                                                                                  |                     |
| rabbitmq.overview.messages.deliver\_get.count                  | rabbitmq\_global\_messages\_delivered\_get\_auto\_ack\_total + rabbitmq\_global\_messages\_delivered\_get\_manual\_ack\_total |                     |
| rabbitmq.overview.messages.publish.count                       | rabbitmq\_queue\_messages\_published\_total                                                                                   | /metrics            |
| rabbitmq.overview.messages.redeliver.count                     | rabbitmq\_global\_messages\_redelivered\_total                                                                                |                     |
| rabbitmq.overview.messages.return\_unroutable.count            | rabbitmq\_global\_messages\_unroutable\_returned\_total                                                                       |                     |
| rabbitmq.overview.object\_totals.channels                      | rabbitmq\_channels                                                                                                            |                     |
| rabbitmq.overview.object\_totals.connections                   | rabbitmq\_connections                                                                                                         |                     |
| rabbitmq.overview.object\_totals.consumers                     | rabbitmq\_global\_consumers                                                                                                   |                     |
| rabbitmq.overview.object\_totals.queues                        | rabbitmq\_queues                                                                                                              |                     |
| rabbitmq.overview.queue\_totals.messages.count                 | rabbitmq\_queue\_messages                                                                                                     | /metrics            |
| rabbitmq.overview.queue\_totals.messages\_ready.count          | rabbitmq\_queue\_messages\_ready                                                                                              | /metrics            |
| rabbitmq.overview.queue\_totals.messages\_unacknowledged.count | rabbitmq\_queue\_messages\_unacked                                                                                            | /metrics            |
| rabbitmq.queue.consumers                                       | rabbitmq\_queue\_consumers                                                                                                    | /metrics            |
| rabbitmq.queue.head\_message\_timestamp                        | rabbitmq\_queue\_head\_message\_timestamp                                                                                     | /metrics/per-object |
| rabbitmq.queue.memory                                          | rabbitmq\_queue\_process\_memory\_bytes                                                                                       | /metrics/per-object |
| rabbitmq.queue.message\_bytes                                  | rabbitmq\_queue\_messages\_ready\_bytes                                                                                       | /metrics/per-object |
| rabbitmq.queue.messages                                        | rabbitmq\_queue\_messages                                                                                                     | /metrics/per-object |
| rabbitmq.queue.messages.publish.count                          | rabbitmq\_queue\_messages\_published\_total                                                                                   | /metrics            |
| rabbitmq.queue.messages.redeliver.count                        | rabbitmq\_global\_messages\_redelivered\_total                                                                                |                     |
| rabbitmq.queue.messages\_ready                                 | rabbitmq\_queue\_messages\_ready                                                                                              |                     |
| rabbitmq.queue.messages\_unacknowledged                        | rabbitmq\_queue\_messages\_unacked                                                                                            |                     |

The following Management plugin metrics to our knowledge have no equivalent in the Prometheus plugin.

- rabbitmq.connections.state
- rabbitmq.exchange.messages.ack.count
- rabbitmq.exchange.messages.ack.rate
- rabbitmq.exchange.messages.confirm.count
- rabbitmq.exchange.messages.confirm.rate
- rabbitmq.exchange.messages.deliver\_get.count
- rabbitmq.exchange.messages.deliver\_get.rate
- rabbitmq.exchange.messages.publish.count
- rabbitmq.exchange.messages.publish.rate
- rabbitmq.exchange.messages.publish\_in.count
- rabbitmq.exchange.messages.publish\_in.rate
- rabbitmq.exchange.messages.publish\_out.count
- rabbitmq.exchange.messages.publish\_out.rate
- rabbitmq.exchange.messages.redeliver.count
- rabbitmq.exchange.messages.redeliver.rate
- rabbitmq.exchange.messages.return\_unroutable.count
- rabbitmq.exchange.messages.return\_unroutable.rate
- rabbitmq.node.partitions
- rabbitmq.node.run\_queue
- rabbitmq.node.running
- rabbitmq.overview.messages.ack.count
- rabbitmq.overview.messages.ack.rate
- rabbitmq.overview.messages.confirm.rate
- rabbitmq.overview.messages.deliver\_get.rate
- rabbitmq.overview.messages.publish.rate
- rabbitmq.overview.messages.publish\_in.count
- rabbitmq.overview.messages.publish\_in.rate
- rabbitmq.overview.messages.publish\_out.count
- rabbitmq.overview.messages.publish\_out.rate
- rabbitmq.overview.messages.redeliver.rate
- rabbitmq.overview.messages.return\_unroutable.rate
- rabbitmq.overview.queue\_totals.messages.rate
- rabbitmq.overview.queue\_totals.messages\_ready.rate
- rabbitmq.overview.queue\_totals.messages\_unacknowledged.rate
- rabbitmq.queue.active\_consumers
- rabbitmq.queue.bindings.count
- rabbitmq.queue.messages.ack.count
- rabbitmq.queue.messages.ack.rate
- rabbitmq.queue.messages.deliver.count
- rabbitmq.queue.messages.deliver.rate
- rabbitmq.queue.messages.deliver\_get.count
- rabbitmq.queue.messages.deliver\_get.rate
- rabbitmq.queue.messages.publish.rate
- rabbitmq.queue.messages.rate
- rabbitmq.queue.messages.redeliver.rate
- rabbitmq.queue.messages\_ready.rate
- rabbitmq.queue.messages\_unacknowledged.rate

### FAQ

- [Tagging RabbitMQ queues by tag family][18]

[1]: https://raw.githubusercontent.com/DataDog/integrations-core/master/rabbitmq/images/rabbitmq_dashboard.png
[2]: https://www.rabbitmq.com
[3]: https://app.datadoghq.com/account/settings#agent
[4]: https://www.rabbitmq.com/management.html
[5]: https://www.rabbitmq.com/rabbitmqctl.8.html#set_permissions
[6]: https://docs.datadoghq.com/agent/guide/agent-configuration-files/#agent-configuration-directory
[7]: https://github.com/DataDog/integrations-core/blob/master/rabbitmq/datadog_checks/rabbitmq/data/conf.yaml.example
[8]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[9]: https://docs.datadoghq.com/agent/kubernetes/integrations/
[10]: https://docs.datadoghq.com/agent/kubernetes/log/
[11]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[12]: https://github.com/DataDog/integrations-core/blob/master/rabbitmq/metadata.csv
[13]: https://docs.datadoghq.com/help/
[14]: https://github.com/DataDog/integrations-core/blob/master/rabbitmq/assets/service_checks.json
[15]: https://www.datadoghq.com/blog/rabbitmq-monitoring
[16]: https://www.datadoghq.com/blog/rabbitmq-monitoring-tools
[17]: https://www.datadoghq.com/blog/monitoring-rabbitmq-performance-with-datadog
[18]: https://docs.datadoghq.com/integrations/faq/tagging-rabbitmq-queues-by-tag-family/
[19]: https://www.rabbitmq.com/prometheus.html
[20]: https://www.rabbitmq.com/prometheus.html#default-endpoint
[21]: https://docs.datadoghq.com/containers/docker/integrations/?tab=dockeradv2
[22]: https://www.rabbitmq.com/prometheus.html#detailed-endpoint
[23]: https://docs.datadoghq.com/integrations/rabbitmq/?tab=host#metrics
