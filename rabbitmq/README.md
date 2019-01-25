# RabbitMQ Check

![RabbitMQ Dashboard][1]

## Overview

The RabbitMQ check lets you:

* Track queue-based stats: queue size, consumer count, unacknowledged messages, redelivered messages, etc
* Track node-based stats: waiting processes, used sockets, used file descriptors, etc
* Monitor vhosts for aliveness and number of connections

And more.
## Setup
### Installation

The RabbitMQ check is included in the [Datadog Agent][2] package, so you don't need to install anything else on your RabbitMQ servers.

### Configuration

Edit the `rabbitmq.d/conf.yaml` file, in the `conf.d/` folder at the root of your [Agent's configuration directory][3] to start collecting your RabbitMQ [metrics](#metric-collection) and [logs](#log-collection). See the [sample rabbitmq.yaml][4] for all available configuration options.

#### Prepare RabbitMQ

Enable the RabbitMQ management plugin. See [RabbitMQ's documentation][5] to enable it.

Agent user then needs at least the `monitoring` tag and those required permissions:

* **conf** - `^aliveness-test$`  
* **write** - `^amq\.default$`  
* **read** - `.*`  

Create an Agent user for your default vhost with the following commands:

```
rabbitmqctl add_user datadog <SECRET>
rabbitmqctl set_permissions  -p / datadog "^aliveness-test$" "^amq\.default$" ".*"
rabbitmqctl set_user_tags datadog monitoring
```

Here, `/` refers to the default host. Set this to your specified virtual host name. See the [RabbitMQ documentation][6] for more information.

#### Metric Collection

* Add this configuration block to your `rabbitmq.d/conf.yaml` file to start gathering your [RabbitMQ metrics](#metrics):

```
init_config:

instances:
  - rabbitmq_api_url: http://localhost:15672/api/
  #  rabbitmq_user: <RABBIT_USER> # if your rabbitmq API requires auth; default is guest
  #  rabbitmq_pass: <RABBIT_PASS> # default is guest
  #  tag_families: true           # default is false
  #  vhosts:
  #    - <THE_ONE_VHOST_YOU_CARE_ABOUT>
```

If you don't set `vhosts`, the Agent sends the following for EVERY vhost:

1. the `rabbitmq.aliveness` service check
2. the `rabbitmq.connections` metric

If you do set `vhosts`, the Agent sends this check and metric only for the vhosts you list.

There are options for `queues` and `nodes` that work similarly. The Agent checks all queues and nodes by default, but you can provide lists or regexes to limit this. See the [example check configuration][4] for details on these configuration options (and all others).

Configuration Options:

* `rabbitmq_api_url` - **required** - Points to the api url of the [RabbitMQ Managment Plugin][7]
* `rabbitmq_user` - **optional** - Defaults to 'guest'
* `rabbitmq_pass` - **optional** - Defaults to 'guest'
* `tag_families` - **optional** - Defaults to false - Tag queue "families" based off of regex matching
* `nodes` or `nodes_regexes` - **optional** - Use the `nodes` or `nodes_regexes` parameters to specify the nodes you'd like to collect metrics on (up to 100 nodes). If you have less than 100 nodes, you don't have to set this parameter, the metrics will be collected on all the nodes by default. See the link to the example YAML below for more.
* `queues` or `queues_regexes` - **optional** - Use the `queues` or `queues_regexes` parameters to specify the queues you'd like to collect metrics on (up to 200 queues). If you have less than 200 queues, you don't have to set this parameter, the metrics will be collected on all the queues by. default. If you have set up vhosts, set the queue names as `vhost_name/queue_name`. If you have `tag_families` enabled, the first captured group in the regex will be used as the queue_family tag.  See the link to the example YAML below for more.
* `vhosts` - **optional** - By default a list of all vhosts is fetched and each one will be checked using the aliveness API. If you prefer only certain vhosts to be monitored, list the vhosts you care about.

See the [sample rabbitmq.d/conf.yaml][4] for all available configuration options.

[Restart the Agent][8] to begin sending RabbitMQ metrics, events, and service checks to Datadog.

#### Log Collection

**Available for Agent >6.0**

1. To modify the default log file location either set the `RABBITMQ_LOGS` environment variable or add the following in your rabbitmq configuration file (`/etc/rabbitmq/rabbitmq.conf`):

    ```
    log.dir = /var/log/rabbit
    log.file = rabbit.log
    ```

2. Collecting logs is disabled by default in the Datadog Agent, enable it in your `datadog.yaml` file:

    ```
    logs_enabled: true
    ```

3. Add this configuration block to your `rabbitmq.d/conf.yaml` file to start collecting your RabbitMQ logs:

    ```
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

    See the [sample rabbitmq.yaml][4] for all available configuration options.

4. [Restart the Agent][8].

### Validation

[Run the Agent's `status` subcommand][9] and look for `rabbitmq` under the Checks section.

## Data Collected
### Metrics

See [metadata.csv][10] for a list of metrics provided by this integration.


The Agent tags `rabbitmq.queue.*` metrics by queue name, and `rabbitmq.node.*` metrics by node name.

### Events

For performance reasons, the RabbitMQ check self-limits the number of queues and nodes it will collect metrics for. If and when the check nears this limit, it emits a warning-level event to your event stream.

See the [example check configuration][4] for details about these limits.

### Service Checks

**rabbitmq.aliveness**:

The Agent submits this service check for all vhosts (if `vhosts` is not configured) OR a subset of vhosts (those configured in `vhosts`), tagging each service check `vhost:<vhost_name>`. Returns CRITICAL if the aliveness check failed, otherwise OK.

**rabbitmq.status**:

Returns CRITICAL if the Agent cannot connect to rabbitmq to collect metrics, otherwise OK.

## Troubleshooting

* [Tagging RabbitMQ queues by tag family][11]

## Further Reading
### Datadog Blog
* [Key metrics for RabbitMQ monitoring][12]
* [Collecting metrics with RabbitMQ monitoring tools][13]
* [Monitoring RabbitMQ performance with Datadog][14]

### Knowledge Base
* By default, `queue` metrics are tagged by queue and `node` metrics are tagged by node. If you have a Datadog account you can see the integration installation instructions [here][15]


[1]: https://raw.githubusercontent.com/DataDog/integrations-core/master/rabbitmq/images/rabbitmq_dashboard.png
[2]: https://app.datadoghq.com/account/settings#agent
[3]: https://docs.datadoghq.com/agent/faq/agent-configuration-files/#agent-configuration-directory
[4]: https://github.com/DataDog/integrations-core/blob/master/rabbitmq/datadog_checks/rabbitmq/data/conf.yaml.example
[5]: https://www.rabbitmq.com/management.html
[6]: https://www.rabbitmq.com/rabbitmqctl.8.html#set_permissions
[7]: https://www.rabbitmq.com/management.html
[8]: https://docs.datadoghq.com/agent/faq/agent-commands/#start-stop-restart-the-agent
[9]: https://docs.datadoghq.com/agent/faq/agent-commands/#agent-status-and-information
[10]: https://github.com/DataDog/integrations-core/blob/master/rabbitmq/metadata.csv
[11]: https://docs.datadoghq.com/integrations/faq/tagging-rabbitmq-queues-by-tag-family
[12]: https://www.datadoghq.com/blog/rabbitmq-monitoring
[13]: https://www.datadoghq.com/blog/rabbitmq-monitoring-tools
[14]: https://www.datadoghq.com/blog/monitoring-rabbitmq-performance-with-datadog
[15]: https://app.datadoghq.com/account/settings#integrations/rabbitmq
