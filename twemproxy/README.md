# Twemproxy Integration

## Overview

Track overall and per-pool stats on each of your Twemproxy servers. This Agent check collects metrics for client and server connections and errors, request and response rates, bytes in and out of the proxy, and more.

## Setup

### Installation

The Agent's Twemproxy check is included in the [Datadog Agent][2] package, so you don't need to install anything else on your Twemproxy servers.

### Configuration

#### Host

Follow the instructions below to configure this check for an Agent running on a host. For containerized environments, see the [Containerized](#containerized) section.

1. Edit the `twemproxy.d/conf.yaml` file in the `conf.d/` folder at the root of your [Agent's configuration directory][3]. See the [sample twemproxy.d/conf.yaml][4] for all available configuration options:

   ```yaml
   init_config:

   instances:
     - host: localhost
       port: 22222
   ```

2. [Restart the Agent][5] to begin sending Twemproxy metrics to Datadog.

#### Containerized

For containerized environments, see the [Autodiscovery Integration Templates][1] for guidance on applying the parameters below.

| Parameter            | Value                                  |
| -------------------- | -------------------------------------- |
| `<INTEGRATION_NAME>` | `twemproxy`                            |
| `<INIT_CONFIG>`      | blank or `{}`                          |
| `<INSTANCE_CONFIG>`  | `{"host": "%%host%%", "port":"22222"}` |

### Validation

[Run the Agent's `status` subcommand][6] and look for `twemproxy` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][7] for a list of metrics provided by this check.

### Events

The Twemproxy check does not include any events.

### Service Checks

`twemproxy.can_connect`:

Returns CRITICAL if the Agent cannot connect to the Twemproxy stats endpoint to collect metrics, otherwise OK.

## Troubleshooting

Need help? Contact [Datadog support][8].

[1]: https://docs.datadoghq.com/agent/kubernetes/integrations/
[2]: https://app.datadoghq.com/account/settings#agent
[3]: https://docs.datadoghq.com/agent/guide/agent-configuration-files/#agent-configuration-directory
[4]: https://github.com/DataDog/integrations-core/blob/master/twemproxy/datadog_checks/twemproxy/data/conf.yaml.example
[5]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[6]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[7]: https://github.com/DataDog/integrations-core/blob/master/twemproxy/metadata.csv
[8]: https://docs.datadoghq.com/help/
