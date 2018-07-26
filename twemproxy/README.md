# Twemproxy Integration

## Overview

Track overall and per-pool stats on each of your twemproxy servers. This Agent check collects metrics for client and server connections and errors, request and response rates, bytes in and out of the proxy, and more.

## Setup
### Installation

The Agent's Twemproxy check is included in the [Datadog Agent][1] package, so you don't need to install anything else on your Twemproxy servers.

### Configuration

1. Edit the `twemproxy.d/conf.yaml` file in the `conf.d/` folder at the root of your [Agent's configuration directory][7]. See the [sample twemproxy.d/conf.yaml][2] for all available configuration options:

    ```
    init_config:

    instances:
        - host: localhost
          port: 2222 # change if your twemproxy doesn't use the default stats monitoring port
    ```

2. [Restart the Agent][3] to begin sending twemproxy metrics to Datadog.

### Validation

[Run the Agent's `status` subcommand][4] and look for `twemproxy` under the Checks section.

## Data Collected
### Metrics

See [metadata.csv][5] for a list of metrics provided by this check.

### Events
The Twemproxy check does not include any events at this time.

### Service Checks

`twemproxy.can_connect`:

Returns CRITICAL if the Agent cannot connect to the Twemproxy stats endpoint to collect metrics, otherwise OK.

## Troubleshooting
Need help? Contact [Datadog Support][6].

[1]: https://app.datadoghq.com/account/settings#agent
[2]: https://github.com/DataDog/integrations-core/blob/master/twemproxy/datadog_checks/twemproxy/data/conf.yaml.example
[3]: https://docs.datadoghq.com/agent/faq/agent-commands/#start-stop-restart-the-agent
[4]: https://docs.datadoghq.com/agent/faq/agent-commands/#agent-status-and-information
[5]: https://github.com/DataDog/integrations-core/blob/master/twemproxy/metadata.csv
[6]: https://docs.datadoghq.com/help/
[7]: https://docs.datadoghq.com/agent/faq/agent-configuration-files/#agent-configuration-directory
