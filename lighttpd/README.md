# Lighttpd Check

![Lighttpd Dashboard][1]

## Overview

The Agent's lighttpd check tracks uptime, bytes served, requests per second, response codes, and more.

## Setup

### Installation

The Lighttpd check is included in the [Datadog Agent][2] package, so you don't need to install anything else on your Lighttpd servers.

In addition, install `mod_status` on your Lighttpd servers.

### Configuration

#### Host

Follow the instructions below to configure this check for an Agent running on a host. For containerized environments, see the [Containerized](#containerized) section.

1. Edit the `lighttpd.d/conf.yaml` file, in the `conf.d/` folder at the root of your [Agent's configuration directory][3]. See the [sample lighttpd.d/conf.yaml][4] for all available configuration options:

   ```yaml
   init_config:

   instances:
     ## @param lighttpd_status_url - string - required
     ## Status url of your Lighttpd server.
     #
     - lighttpd_status_url: http://localhost/server-status?auto
   ```

2. [Restart the Agent][5].

#### Containerized

For containerized environments, see the [Autodiscovery Integration Templates][6] for guidance on applying the parameters below.

| Parameter            | Value                                                           |
| -------------------- | --------------------------------------------------------------- |
| `<INTEGRATION_NAME>` | `lighttpd`                                                      |
| `<INIT_CONFIG>`      | blank or `{}`                                                   |
| `<INSTANCE_CONFIG>`  | `{"lighttpd_status_url": "http://%%host%%/server-status?auto"}` |

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
[2]: https://app.datadoghq.com/account/settings#agent
[3]: https://docs.datadoghq.com/agent/guide/agent-configuration-files/#agent-configuration-directory
[4]: https://github.com/DataDog/integrations-core/blob/master/lighttpd/datadog_checks/lighttpd/data/conf.yaml.example
[5]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[6]: https://docs.datadoghq.com/agent/autodiscovery/integrations
[7]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[8]: https://github.com/DataDog/integrations-core/blob/master/lighttpd/metadata.csv
[9]: https://docs.datadoghq.com/help
[10]: https://www.datadoghq.com/blog/monitor-lighttpd-web-server-metrics
