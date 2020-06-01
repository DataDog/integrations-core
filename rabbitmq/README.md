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

#### Prepare RabbitMQ

Enable the RabbitMQ management plugin. See [RabbitMQ's documentation][4] to enable it. The Agent user then needs at least the `monitoring` tag and these required permissions:

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

#### Host

Follow the instructions below to configure this check for an Agent running on a host. For containerized environments, see the [Containerized](#containerized) section.

##### Metric collection

1. Edit the `rabbitmq.d/conf.yaml` file, in the `conf.d/` folder at the root of your [Agent's configuration directory][6] to start collecting your RabbitMQ metrics. See the [sample rabbitmq.d/conf.yaml][7] for all available configuration options.

   ```yaml
   init_config:

   instances:
     ## @param rabbit_api_url - string - required
     ## For every instance a 'rabbitmq_api_url' must be provided, pointing to the api
     ## url of the RabbitMQ Managment Plugin (http://www.rabbitmq.com/management.html).
     #
     - rabbitmq_api_url: http://localhost:15672/api/
   ```

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

3. Add this configuration block to your `rabbitmq.d/conf.yaml` file to start collecting your RabbitMQ logs:

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

#### Containerized

For containerized environments, see the [Autodiscovery Integration Templates][9] for guidance on applying the parameters below.

##### Metric collection

| Parameter            | Value                                        |
| -------------------- | -------------------------------------------- |
| `<INTEGRATION_NAME>` | `rabbitmq`                                   |
| `<INIT_CONFIG>`      | blank or `{}`                                |
| `<INSTANCE_CONFIG>`  | `{"rabbitmq_api_url":"%%host%%:15672/api/","username": <USERNAME>, "password": <PASSWORD>}` |

##### Log collection

_Available for Agent versions >6.0_

Collecting logs is disabled by default in the Datadog Agent. To enable it, see [Kubernetes log collection documentation][10].

| Parameter      | Value                                                                                                                                               |
| -------------- | --------------------------------------------------------------------------------------------------------------------------------------------------- |
| `<LOG_CONFIG>` | `{"source": "rabbitmq", "service": "rabbitmq", "log_processing_rules": {"type":"multi_line","name":"logs_starts_with_equal_sign", "pattern": "="}}` |

### Validation

[Run the Agent's status subcommand][11] and look for `rabbitmq` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][12] for a list of metrics provided by this integration.

The Agent tags `rabbitmq.queue.*` metrics by queue name and `rabbitmq.node.*` metrics by node name.

### Events

For performance reasons, the RabbitMQ check limits the number of exchanges, queues, and nodes it collects metrics for. If the check nears this limit, it emits a warning-level event to your event stream.

If you require an increase in the number of exchanges, queues, or nodes, contact [Datadog support][13].

### Service Checks

**rabbitmq.aliveness**:<br>
The Agent submits this service check for all vhosts (if `vhosts` is not configured) OR a subset of vhosts (those configured in `vhosts`). Each service check is tagged with `vhost:<vhost_name>`. Returns `CRITICAL` if the aliveness check failed, otherwise returns `OK`.

**rabbitmq.status**:<br>
Returns `CRITICAL` if the Agent cannot connect to RabbitMQ to collect metrics, otherwise returns `OK`.

## Troubleshooting

Need help? Contact [Datadog support][13].

## Further Reading

Additional helpful documentation, links, and articles:

### Datadog Blog

- [Key metrics for RabbitMQ monitoring][14]
- [Collecting metrics with RabbitMQ monitoring tools][15]
- [Monitoring RabbitMQ performance with Datadog][16]

### FAQ

- [Tagging RabbitMQ queues by tag family][17]

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
[14]: https://www.datadoghq.com/blog/rabbitmq-monitoring
[15]: https://www.datadoghq.com/blog/rabbitmq-monitoring-tools
[16]: https://www.datadoghq.com/blog/monitoring-rabbitmq-performance-with-datadog
[17]: https://docs.datadoghq.com/integrations/faq/tagging-rabbitmq-queues-by-tag-family/
