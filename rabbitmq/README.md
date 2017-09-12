# RabbitMQ Check

## Overview

The RabbitMQ check lets you:

* Track queue-based stats: queue size, consumer count, unacknowledged messages, redelivered messages, etc
* Track node-based stats: waiting processes, used sockets, used file descriptors, etc
* Monitor vhosts for aliveness and number of connections

And more.
## Setup
### Installation

The RabbitMQ check is packaged with the Agent, so simply [install the Agent](https://app.datadoghq.com/account/settings#agent) on your RabbitMQ servers. If you need the newest version of the check, install the `dd-check-rabbitmq` package.

### Configuration
#### Prepare RabbitMQ

You must enable the RabbitMQ management plugin. See [RabbitMQ's documentation](https://www.rabbitmq.com/management.html) to enable it.

#### Connect the Agent

Create a file `rabbitmq.yaml` in the Agent's `conf.d` directory:

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

Restart the Agent to begin sending RabbitMQ metrics, events, and service checks to Datadog.

### Validation

Run the Agent's `info` subcommand and look for `rabbitmq` under the Checks section:

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

If you have any questions about Datadog or a use case our [Docs](https://docs.datadoghq.com/) didn’t mention, we’d love to help! Here’s how you can reach out to us:

### Visit the Knowledge Base

Learn more about what you can do in Datadog on the [Support Knowledge Base](https://datadog.zendesk.com/agent/).

### Web Support

Messages in the [event stream](https://app.datadoghq.com/event/stream) containing **@support-datadog** will reach our Support Team. This is a convenient channel for referencing graph snapshots or a particular event. In addition, we have a livechat service available during the day (EST) from any page within the app.

### By Email

You can also contact our Support Team via email at [support@datadoghq.com](mailto:support@datadoghq.com).

### Over Slack

Reach out to our team and other Datadog users on [Slack](http://chat.datadoghq.com/).

## Further Reading
### Datadog Blog
Learn more about infrastructure monitoring and all our integrations on [our blog](https://www.datadoghq.com/blog/)

### Knowledge Base
* [Tagging RabbitMQ queues by tag Family](https://help.datadoghq.com/hc/en-us/articles/211590103-Tagging-RabbitMQ-queues-by-tag-family)