# Agent Check: swap

## Overview

This check monitors the number of bytes a host has swapped in and swapped out.

## Setup
### Installation

The system swap check is packaged with the Agent, so simply [install the Agent](https://app.datadoghq.com/account/settings#agent) on any host.

### Configuration

Create a blank Agent check configuration file called `system_swap.yaml` in the Agent's `conf.d` directory:

```
# This check takes no initial configuration
init_config:

instances: [{}]
```

Restart the Agent to start collecting swap metrics.

### Validation

Run the Agent's `info` subcommand and look for `system_swap` under the Checks section:

```
  Checks
  ======
    [...]

    system_swap
    -------
      - instance #0 [OK]
      - Collected 2 metrics, 0 events & 0 service checks

    [...]
```

## Compatibility

The system_swap check is compatible with all major platforms.

## Data Collected
### Metrics

See [metadata.csv](https://github.com/DataDog/integrations-core/blob/master/system_swap/metadata.csv) for a list of metrics provided by this check.

### Events
The System Swap check does not include any event at this time.

### Service Checks
The System Swap check does not include any service check at this time.

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
Learn more about infrastructure monitoring and all our integrations on [our blog](https://www.datadoghq.com/blog/)