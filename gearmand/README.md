# Gearman Integration

## Overview

Collect Gearman metrics to:

* Visualize Gearman performance.
* Know how many tasks are queued or running.
* Correlate Gearman performance with the rest of your applications.

## Setup
### Installation

The Gearman check is packaged with the Agent, so simply [install the Agent](https://app.datadoghq.com/account/settings#agent) on your Gearman job servers.

### Configuration

Create a file `gearmand.yaml` in the Agent's `conf.d` directory:

```
init_config:

instances:
  - server: localhost
    port: 4730
```

Restart the Agent to begin sending Gearman metrics to Datadog.

### Validation

Run the Agent's `info` subcommand and look for `gearmand` under the Checks section:

```
  Checks
  ======
    [...]

    gearmand
    -------
      - instance #0 [OK]
      - Collected 26 metrics, 0 events & 1 service check

    [...]
```

## Compatibility

The gearmand check is compatible with all major platforms.

## Data Collected
### Metrics

See [metadata.csv](https://github.com/DataDog/integrations-core/blob/master/gearmand/metadata.csv) for a list of metrics provided by this integration.

### Events
The Gearmand check does not include any event at this time.

### Service Checks

`gearman.can_connect`:

Returns `Critical` if the Agent cannot connect to Gearman to collect metrics.

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