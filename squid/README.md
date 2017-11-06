# Squid Integration

## Overview

This integration lets you monitor your Squid metrics from the Cache Manager directly in Datadog.

## Setup

### Installation

The Agent's Squid integration is packaged with the Agent, so simply [install the agent](https://app.datadoghq.com/account/settings#agent) on your Squid server. If you need the newest version of the check, install the `dd-check-squid` package.

## Configuration

Create a file `squid.yaml` in the Agent's `conf.d` directory. See the [sample squid.yaml](https://github.com/DataDog/integrations-core/blob/master/squid/squid.yaml.example) for all available configuration options:

```yaml
init_config:

instances:
  # A list of squid instances identified by their name

  - name: my_squid
  #   host: localhost  # The hostname or ip address of the squid server. Default to 'localhost'
  #   port: 3128  # The port where the squid server is listening. Default to 3128
  #   tags: ['custom:tag']  # A list of tags that you wish to send with your squid metrics
```

Restart the Agent to start sending metrics and service checks to Datadog.

## Validation

[Run the Agent's info subcommand](https://help.datadoghq.com/hc/en-us/articles/203764635-Agent-Status-and-Information) and look for `squid` under the Checks section:

```
    Checks
    ======
        [...]

        squid
        -----
          - instance #0 [OK]
          - Collected 40 metrics, 0 events & 1 service checks

        [...]
```

## Compatibility

The squid check is compatible with all major platforms.

## Data Collected

### Metrics

See [metadata.csv](https://github.com/DataDog/integrations-core/blob/master/squid/metadata.csv)

### Events

The Squid check does not include any events at this time

### Service Checks

**squid.can_connect**:
Returns CRITICAL if the Agent cannot connect to Squid to collect metrics, otherwise OK.

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
