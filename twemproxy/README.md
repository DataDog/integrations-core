# Twemproxy Integration

## Overview

Track overall and per-pool stats on each of your twemproxy servers. This Agent check collects metrics for client and server connections and errors, request and response rates, bytes in and out of the proxy, and more.

## Setup
### Installation

The Agent's twemproxy check is packaged with the Agent, so simply [install the Agent](https://app.datadoghq.com/account/settings#agent) on each of your Twemproxy servers.

### Configuration

Create a file `twemproxy.yaml` in the Agent's `conf.d` directory:

```
init_config:

instances:
    - host: localhost
      port: 2222 # change if your twemproxy doesn't use the default stats monitoring port
```

Restart the Agent to begin sending twemproxy metrics to Datadog.

### Validation

Run the Agent's `info` subcommand and look for `twemproxy` under the Checks section:

```
  Checks
  ======
    [...]

    twemproxy
    -------
      - instance #0 [OK]
      - Collected 20 metrics, 0 events & 1 service check

    [...]
```

## Compatibility

The twemproxy check is compatible with all major platforms.

## Data Collected
### Metrics

See [metadata.csv](https://github.com/DataDog/integrations-core/blob/master/twemproxy/metadata.csv) for a list of metrics provided by this check.

### Events
The Twemproxy check does not include any event at this time.

### Service Checks

`twemproxy.can_connect`:

Returns CRITICAL if the Agent cannot connect to the Twemproxy stats endpoint to collect metrics, otherwise OK.

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
### Blog Article
Learn more about infrastructure monitoring and all our integrations on [our blog](https://www.datadoghq.com/blog/)