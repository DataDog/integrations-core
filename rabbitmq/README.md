# RabbitMQ Check

![RabbitMQ Dashboard][1]

## Overview

This check monitors [RabbitMQ][2] through the Datadog Agent. It allows you to:

- Track queue-based stats: queue size, consumer count, unacknowledged messages, redelivered messages, and more.
- Track node-based stats: waiting processes, used sockets, used file descriptors, and more.
- Monitor vhosts for aliveness and number of connections.

## Setup

### Installation

The RabbitMQ check is included in the [Datadog Agent][3] package. No additional installation is needed on your server.

### Configuration

RabbitMQ exposes metrics in two ways: the [RabbitMQ Management Plugin][4] and the [RabbitMQ Prometheus Plugin][19]. The Datadog integration supports both versions. Follow the configuration instruction in this file that pertain to the version you intend to use. The Datadog integration also comes with an out-of-the-box dashboard and monitors for each version, as labeled by the Dashboard and Monitor titles.

#### Prepare RabbitMQ

##### [RabbitMQ Prometheus Plugin][19].

*Starting with RabbitMQ v3.8, the [RabbitMQ Prometheus Plugin][19] is enabled by default.*

*The Prometheus plugin version of RabbitMQ requires Python 3 support by the Datadog Agent, and so can only be supported by Agent v6 or later. Please ensure your agent is updated before configuring the Prometheus plugin version of the integration.*

Configure the `prometheus_plugin` section in your instance configuration. When using the `prometheus_plugin` option, settings related to the Management Plugin are ignored.

 ```yaml
 instances:
   - prometheus_plugin:
       url: http://<HOST>:15692
 ```

 This enables scraping of the [`/metrics` endpoint][20] on one RabbitMQ node. Datadog can also collect data from the [`/metrics/detailed` endpoint][22].

 ```yaml
 instances:
   - prometheus_plugin:
       url: http://<HOST>:15692
       unaggregated_endpoint: detailed?family=queue_coarse_metrics
 ```
 This enables scraping of the [`/metrics/detailed` endpoint][22] to collect queue coarse metrics.

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

You can take advantage of Datadog's [Docker container Autodiscovery][21], see the `auto_conf.yaml` example configuration for RabbitMQ-specific settings.

For container environments such as Kubernetes, see the [Autodiscovery Integration Templates][9] for guidance on applying the parameters below.

##### Metric collection

| Parameter            | Value                                        |
| -------------------- | -------------------------------------------- |
| `<INTEGRATION_NAME>` | `rabbitmq`                                   |
| `<INIT_CONFIG>`      | blank or `{}`                                |
| `<INSTANCE_CONFIG>`  | `{"prometheus_plugin": {"url": "http://%%host%%:15692"}}` |

##### Log collection

_Available for Agent v6.0 or later_

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

### Migrating to Prometheus Plugin

The Prometheus Plugin exposes a different set of metrics from the Management Plugin.
Here is what to be aware of as you migrate from the Management to the Prometheus Plugin.

- Look up your metrics in [this table][23]. If a metric's description contains an `[OpenMetricsV2]` tag, then it is available in the Prometheus Plugin. Metrics available only in the Management Plugin do not have any tags in their descriptions.
- Any dashboards and monitors using Management Plugin metrics do not function. Switch to the dashboards and monitors marked as *OpenMetrics Version*.
- The default configuration collects aggregated metrics. This means, for example, that there are no metrics tagged by queue. Configure the option `prometheus_plugin.unaggregated_endpoint` to get metrics without aggregation.
- The `rabbitmq.status` service check is replaced by `rabbitmq.openmetrics.health`. The service check `rabbitmq.aliveness` has no equivalent in the Prometheus Plugin.

The Prometheus Plugin changes some tags. The table below describes the changes to the more common tags.

| Management          | Prometheus                               |
|:--------------------|:-----------------------------------------|
| `queue_name`        | `queue`                                  |
| `rabbitmq_vhost`    | `vhost`, `exchange_vhost`, `queue_vhost` |
| `rabbitmq_exchange` | `exchange`                               |

For more information, see [Tagging RabbitMQ queues by tag family][18].

Need help? Contact [Datadog support][13].

## Further Reading

Additional helpful documentation, links, and articles:

- [Key metrics for RabbitMQ monitoring][15]
- [Collecting metrics with RabbitMQ monitoring tools][16]
- [Monitoring RabbitMQ performance with Datadog][17]

[1]: https://raw.githubusercontent.com/DataDog/integrations-core/master/rabbitmq/images/rabbitmq_dashboard.png
[2]: https://www.rabbitmq.com
[3]: https://app.datadoghq.com/account/settings/agent/latest
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
