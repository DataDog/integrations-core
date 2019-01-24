# Squid Integration

## Overview

This integration lets you monitor your Squid metrics from the Cache Manager directly in Datadog.

## Setup

### Installation

The Agent's Squid check is included in the [Datadog Agent][1] package, so you don't need to install anything else on your Squid server.

### Configuration

1. Edit the `squid.d/conf.yaml`, in the `conf.d/` folder at the root of your [Agent's configuration directory][2].
    See the [sample squid.d/conf.yaml][3] for all available configuration options:

```
    init_config:

    instances:
        # A list of squid instances identified by their name

        - name: my_squid
        #   host: localhost  # The hostname or ip address of the squid server. Default to 'localhost'
        #   port: 3128  # The port where the squid server is listening. Default to 3128
        #   tags: ['custom:tag']  # A list of tags that you wish to send with your squid metrics
```

2. [Restart the Agent][4] to start sending metrics and service checks to Datadog.

### Validation

[Run the Agent's info subcommand][5] and look for `squid` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][6]

### Events

The Squid check does not include any events at this time

### Service Checks

**squid.can_connect**:
Returns CRITICAL if the Agent cannot connect to Squid to collect metrics, otherwise OK.

## Troubleshooting

If you have any questions about Datadog or a use case our [Docs][7] didn't mention, we'd love to help! Here's how you can reach out to us:

### Visit the Knowledge Base

Learn more about what you can do in Datadog on the [Support Knowledge Base][8].

### Web Support

Messages in the [event stream][9] containing **@support-datadog** will reach our Support Team. This is a convenient channel for referencing graph snapshots or a particular event. In addition, we have a livechat service available during the day (EST) from any page within the app.

### By Email

You can also contact our Support Team via email at [support@datadoghq.com][10].

### Over Slack

Reach out to our team and other Datadog users on [Slack][11].


[1]: https://app.datadoghq.com/account/settings#agent
[2]: https://docs.datadoghq.com/agent/faq/agent-configuration-files/#agent-configuration-directory
[3]: https://github.com/DataDog/integrations-core/blob/master/squid/datadog_checks/squid/data/conf.yaml.example
[4]: https://docs.datadoghq.com/agent/faq/agent-commands/#start-stop-restart-the-agent
[5]: https://docs.datadoghq.com/agent/faq/agent-commands/#agent-status-and-information
[6]: https://github.com/DataDog/integrations-core/blob/master/squid/metadata.csv
[7]: https://docs.datadoghq.com
[8]: https://datadog.zendesk.com/agent
[9]: https://app.datadoghq.com/event/stream
[10]: mailto:support@datadoghq.com
[11]: https://chat.datadoghq.com
