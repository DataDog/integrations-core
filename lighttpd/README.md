# Lighttpd Check

## Overview

The Agent's lighttpd check tracks uptime, bytes served, requests per second, response codes, and more.

## Setup
### Installation

The lighttpd check is packaged with the Agent, so simply [install the Agent](https://app.datadoghq.com/account/settings#agent) on your lighttpd servers. If you need the newest version of the check, install the `dd-check-lighttpd` package.

You'll also need to install `mod_status` on your Lighttpd servers.

### Configuration

Create a file `lighttpd.yaml` in the Agent's `conf.d` directory:

```
init_config:

instances:
# Each instance needs a lighttpd_status_url. Tags are optional.
  - lighttpd_status_url: http://example.com/server-status?auto
#   tags:
#     - instance:foo
```

Restart the Agent to begin sending lighttpd metrics to Datadog.

### Validation

Run the Agent's `info` subcommand and look for `lighttpd` under the Checks section:

```
  Checks
  ======
    [...]

    lighttpd
    -------
      - instance #0 [OK]
      - Collected 30 metrics, 0 events & 1 service check

    [...]
```

## Compatibility

The lighttpd check is compatible with all major platforms.

## Data Collected
### Metrics

See [metadata.csv](https://github.com/DataDog/integrations-core/blob/master/lighttpd/metadata.csv) for a list of metrics provided by this integration.

### Events
The Lighttpd check does not include any event at this time.

### Service Checks

`- lighttpd.can_connect`:

Returns CRITICAL if the Agent cannot connect to lighttpd to collect metrics, otherwise OK.

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
To get a better idea of how (or why) to monitor Lighttpd web server metrics with Datadog, check out our [series of blog posts](https://www.datadoghq.com/blog/monitor-lighttpd-web-server-metrics/) about it.
