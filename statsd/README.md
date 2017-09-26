# Agent Check: StatsD

## Overview

This check monitors the availability and uptime of non-Datadog StatsD servers. It also tracks the number of metrics, by metric type, received by StatsD.

This check does **NOT** forward application metrics from StatsD servers to Datadog. It collects metrics about StatsD itself.

## Setup
### Installation

The StatsD check is packaged with the Agent, so simply [install the Agent](https://app.datadoghq.com/account/settings#agent) on any servers that run StatsD. If you need the newest version of the check, install the `dd-check-statsd` package.

### Configuration

Create a file `statsd.yaml` in the Agent's `conf.d` directory:

```
init_config:

instances:
  - host: localhost
    port: 8126 # or wherever your statsd listens
```

Restart the Agent to start sending StatsD metrics and service checks to Datadog.

### Validation

Run the Agent's `info` subcommand and look for `statsd` under the Checks section:

```
  Checks
  ======
    [...]

    statsd
    -------
      - instance #0 [OK]
      - Collected 3 metrics, 0 events & 2 service checks

    [...]
```

## Compatibility

The statsd check is compatible with all major platforms.

## Data Collected
### Metrics
See [metadata.csv](https://github.com/DataDog/integrations-core/blob/master/statsd/metadata.csv) for a list of metrics provided by this integration.

### Events
The StatsD check does not include any event at this time.

### Service Checks

**statsd.is_up**:

Returns CRITICAL if the StatsD server does not respond to the Agent's health status request, otherwise OK.

**statsd.can_connect**:

Returns CRITICAL if the Agent cannot collect metrics about StatsD, otherwise OK.

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
If you don't know what StatsD is and how does it work, check out [our blog post about it](https://www.datadoghq.com/blog/statsd/)

To get a better idea of how (or why) to visualize StatsD metrics with Counts Graphing with Datadog, check out our [series of blog posts](https://www.datadoghq.com/blog/visualize-statsd-metrics-counts-graphing/) about it.
