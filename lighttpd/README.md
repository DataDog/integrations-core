# Lighttpd Check
{{< img src="integrations/lighttpd/lighttpddashboard.png" alt="Lighttpd Dashboard" responsive="true" popup="true">}}
## Overview

The Agent's lighttpd check tracks uptime, bytes served, requests per second, response codes, and more.

## Setup
### Installation

The lighttpd check is packaged with the Agent, so simply [install the Agent](https://app.datadoghq.com/account/settings#agent) on your lighttpd servers.

You'll also need to install `mod_status` on your Lighttpd servers.

### Configuration

Create a file `lighttpd.yaml` in the Agent's `conf.d` directory. See the [sample lighttpd.yaml](https://github.com/DataDog/integrations-core/blob/master/lighttpd/conf.yaml.example) for all available configuration options:

```
init_config:

instances:
# Each instance needs a lighttpd_status_url. Tags are optional.
  - lighttpd_status_url: http://example.com/server-status?auto
#   tags:
#     - instance:foo
```

[Restart the Agent](https://docs.datadoghq.com/agent/faq/agent-commands/#start-stop-restart-the-agent) to begin sending lighttpd metrics to Datadog.

### Validation

[Run the Agent's `status` subcommand](https://docs.datadoghq.com/agent/faq/agent-commands/#agent-status-and-information) and look for `lighttpd` under the Checks section.

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

Need help? Contact [Datadog Support](http://docs.datadoghq.com/help/).

## Further Reading
To get a better idea of how (or why) to monitor Lighttpd web server metrics with Datadog, check out our [series of blog posts](https://www.datadoghq.com/blog/monitor-lighttpd-web-server-metrics/) about it.
