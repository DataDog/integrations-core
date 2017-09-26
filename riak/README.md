# Riak Check

## Overview

This check lets you track node, vnode and ring performance metrics from RiakKV or RiakTS.

## Setup
### Installation

The Riak check is packaged with the Agent, so simply [install the Agent](https://app.datadoghq.com/account/settings#agent) on your Riak servers. If you need the newest version of the check, install the `dd-check-riak` package.

### Configuration

Create a file `riak.yaml` in the Agent's `conf.d` directory:

```
init_config:

instances:
  - url: http://127.0.0.1:8098/stats # or whatever your stats endpoint is
```

[Restart the Agent](https://help.datadoghq.com/hc/en-us/articles/203764515-Start-Stop-Restart-the-Datadog-Agent) to start sending Riak metrics to Datadog.

### Validation

Run the Agent's `info` subcommand and look for `riak` under the Checks section:

```
  Checks
  ======
    [...]

    riak
    -------
      - instance #0 [OK]
      - Collected 26 metrics, 0 events & 1 service check

    [...]
```

## Compatibility

The riak check is compatible with all major platforms.

## Data Collected
### Metrics

See [metadata.csv](https://github.com/DataDog/integrations-core/blob/master/riak/metadata.csv) for a list of metrics provided by this check.

### Events
The Riak check does not include any event at this time.

### Service Checks

**riak.can_connect**:

Returns CRITICAL if the Agent cannot connect to the Riak stats endpoint to collect metrics, otherwise OK.

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