# Kong Integration

## Overview

The Agent's Kong check tracks total requests, response codes, client connections, and more.

## Setup
### Installation

The Kong check is packaged with the Agent, so simply [install the Agent](https://app.datadoghq.com/account/settings#agent) on your Kong servers. If you need the newest version of the check, install the `dd-check-kong` package.

### Configuration

Create a `kong.yaml` in the Datadog Agent's `conf.d` directory:

```
init_config:

instances:
# Each instance needs a `kong_status_url`. Tags are optional.
-   kong_status_url: http://example.com:8001/status/
    tags:
    - instance:foo
#-   kong_status_url: http://example2.com:8001/status/
#    tags:
#    - instance:bar
```

Restart the Agent to begin sending Kong metrics to Datadog.

### Validation

Run the Agent's `info` subcommand and look for `kong` under the Checks section:

```
  Checks
  ======
    [...]

    kong
    -------
      - instance #0 [OK]
      - Collected 26 metrics, 0 events & 1 service check

    [...]
```

## Compatibility

The kong check is compatible with all major platforms.

## Data Collected
### Metrics

See [metadata.csv](https://github.com/DataDog/integrations-core/blob/master/kong/metadata.csv) for a list of metrics provided by this check.

### Events
The Kong check does not include any event at this time.

### Service Checks

`kong.can_connect`:

Returns CRITICAL if the Agent cannot connect to Kong to collect metrics, otherwise OK.

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
To get a better idea of how (or why) to monitor Kong with Datadog, check out our [series of blog posts](https://www.datadoghq.com/blog/monitor-kong-datadog/) about it.
