# Lighttpd Check

![Lighttpd Dashboard][1]

## Overview

The Agent's lighttpd check tracks uptime, bytes served, requests per second, response codes, and more.

## Setup

Follow the instructions below to install and configure this check for an Agent running on a host. For containerized environments, see the [Autodiscovery Integration Templates][2] for guidance on applying these instructions.

### Installation

The lighttpd check is included in the [Datadog Agent][3] package, so you don't need to install anything else on your lighttpd servers.

In addition, install `mod_status` on your Lighttpd servers.

### Configuration

1. Edit the  `lighttpd.d/conf.yaml` file, in the `conf.d/` folder at the root of your [Agent's configuration directory][4].
	See the [sample lighttpd.d/conf.yaml][5] for all available configuration options:

    ```yaml
	init_config:

	instances:
	    # Each instance needs a lighttpd_status_url. Tags are optional.
      	- lighttpd_status_url: http://example.com/server-status?auto
	    #   tags:
	    #     - instance:foo
    ```

2. [Restart the Agent][6] to begin sending lighttpd metrics to Datadog.

### Validation

[Run the Agent's `status` subcommand][7] and look for `lighttpd` under the Checks section.

## Data Collected
### Metrics

See [metadata.csv][8] for a list of metrics provided by this integration.

### Events
The Lighttpd check does not include any events.

### Service Checks

`- lighttpd.can_connect`:

Returns CRITICAL if the Agent cannot connect to lighttpd to collect metrics, otherwise OK.

## Troubleshooting

Need help? Contact [Datadog support][9].

## Further Reading
To get a better idea of how (or why) to monitor Lighttpd web server metrics with Datadog, check out our [series of blog posts][10] about it.


[1]: https://raw.githubusercontent.com/DataDog/integrations-core/master/lighttpd/images/lighttpddashboard.png
[2]: https://docs.datadoghq.com/agent/autodiscovery/integrations
[3]: https://app.datadoghq.com/account/settings#agent
[4]: https://docs.datadoghq.com/agent/guide/agent-configuration-files/#agent-configuration-directory
[5]: https://github.com/DataDog/integrations-core/blob/master/lighttpd/datadog_checks/lighttpd/data/conf.yaml.example
[6]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[7]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[8]: https://github.com/DataDog/integrations-core/blob/master/lighttpd/metadata.csv
[9]: https://docs.datadoghq.com/help
[10]: https://www.datadoghq.com/blog/monitor-lighttpd-web-server-metrics
