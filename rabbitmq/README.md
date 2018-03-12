# RabbitMQ Check
{{< img src="integrations/rabbitmq/rabbitmqdashboard.png" alt="RabbitMQ Dashboard" responsive="true" popup="true">}}
## Overview

The RabbitMQ check lets you:

* Track queue-based stats: queue size, consumer count, unacknowledged messages, redelivered messages, etc
* Track node-based stats: waiting processes, used sockets, used file descriptors, etc
* Monitor vhosts for aliveness and number of connections

And more.
## Setup
### Installation

The RabbitMQ check is packaged with the Agent, so simply [install the Agent](https://app.datadoghq.com/account/settings#agent) on your RabbitMQ servers.

If you need the newest version of the RabbitMQ check, install the `dd-check-rabbitmq` package; this package's check overrides the one packaged with the Agent. See the [integrations-core repository README.md for more details](https://docs.datadoghq.com/agent/faq/install-core-extra/).

### Configuration
#### Prepare RabbitMQ

You must enable the RabbitMQ management plugin. See [RabbitMQ's documentation](https://www.rabbitmq.com/management.html) to enable it.

#### Connect the Agent

Create a file `rabbitmq.yaml` in the Agent's `conf.d` directory. See the [sample rabbitmq.yaml](https://github.com/DataDog/integrations-core/blob/master/rabbitmq/conf.yaml.example) for all available configuration options:

```
init_config:

instances:
  - rabbitmq_api_url: http://localhost:15672/api/
#   rabbitmq_user: <RABBIT_USER> # if your rabbitmq API requires auth; default is guest
#   rabbitmq_pass: <RABBIT_PASS> # default is guest
#   tag_families: true           # default is false
#   vhosts:
#     - <THE_ONE_VHOST_YOU_CARE_ABOUT>
```

If you don't set `vhosts`, the Agent sends the following for EVERY vhost:

1. the `rabbitmq.aliveness` service check
1. the `rabbitmq.connections` metric

If you do set `vhosts`, the Agent sends this check and metric only for the vhosts you list.

There are options for `queues` and `nodes` that work similarly—the Agent checks all queues and nodes by default, but you can provide lists or regexes to limit this. See the [example check configuration](https://github.com/DataDog/integrations-core/blob/master/rabbitmq/conf.yaml.example) for details on these configuration options (and all others).

Configuration Options

* `rabbitmq_api_url` - **required** - Points to the api url of the [RabbitMQ Managment Plugin](http://www.rabbitmq.com/management.html)
* `rabbitmq_user` - **optional** - Defaults to 'guest'
* `rabbitmq_pass` - **optional** - Defaults to 'guest'
* `tag_families` - **optional** - Defaults to false - Tag queue "families" based off of regex matching
* `nodes` or `nodes_regexes` - **optional** - Use the `nodes` or `nodes_regexes` parameters to specify the nodes you'd like to collect metrics on (up to 100 nodes). If you have less than 100 nodes, you don't have to set this parameter, the metrics will be collected on all the nodes by default. See the link to the example YAML below for more.
* `queues` or `queues_regexes` - **optional** - Use the `queues` or `queues_regexes` parameters to specify the queues you'd like to collect metrics on (up to 200 queues). If you have less than 200 queues, you don't have to set this parameter, the metrics will be collected on all the queues by. default. If you have set up vhosts, set the queue names as `vhost_name/queue_name`. If you have `tag_families` enabled, the first captured group in the regex will be used as the queue_family tag.  See the link to the example YAML below for more.
* `vhosts` - **optional** - By default a list of all vhosts is fetched and each one will be checked using the aliveness API. If you prefer only certain vhosts to be monitored, list the vhosts you care about.

[Restart the Agent](https://docs.datadoghq.com/agent/faq/agent-commands/#start-stop-restart-the-agent) to begin sending RabbitMQ metrics, events, and service checks to Datadog.

### Validation

[Run the Agent's `status` subcommand](https://docs.datadoghq.com/agent/faq/agent-commands/#agent-status-and-information) and look for `rabbitmq` under the Checks section:

```
  Checks
  ======
    [...]

    rabbitmq
    -------
      - instance #0 [OK]
      - Collected 26 metrics, 0 events & 2 service checks

    [...]
```

## Compatibility

The rabbitmq check is compatible with all major platforms.

## Data Collected
### Metrics

See [metadata.csv](https://github.com/DataDog/integrations-core/blob/master/rabbitmq/metadata.csv) for a list of metrics provided by this check.

The Agent tags `rabbitmq.queue.*` metrics by queue name, and `rabbitmq.node.*` metrics by node name.

### Events

For performance reasons, the RabbitMQ check self-limits the number of queues and nodes it will collect metrics for. If and when the check nears this limit, it emits a warning-level event to your event stream.

See the [example check configuration](https://github.com/DataDog/integrations-core/blob/master/rabbitmq/conf.yaml.example) for details about these limits.

### Service Checks

**rabbitmq.aliveness**:

The Agent submits this service check for all vhosts (if `vhosts` is not configured) OR a subset of vhosts (those configured in `vhosts`), tagging each service check `vhost:<vhost_name>`. Returns CRITICAL if the aliveness check failed, otherwise OK.

**rabbitmq.status**:

Returns CRITICAL if the Agent cannot connect to rabbitmq to collect metrics, otherwise OK.

## Troubleshooting

* [Tagging RabbitMQ queues by tag family](https://docs.datadoghq.com/integrations/faq/tagging-rabbitmq-queues-by-tag-family)

## Further Reading
### Datadog Blog
Learn more about infrastructure monitoring and all our integrations on [our blog](https://www.datadoghq.com/blog/)

### Knowledge Base
* By default, `queue` metrics are tagged by queue and `node` metrics are tagged by node. If you have a Datadog account you can see the integration installation instructions [here](https://app.datadoghq.com/account/settings#integrations/rabbitmq)
