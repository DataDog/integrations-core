# Gearman Integration

## Overview

Collect Gearman metrics to:

* Visualize Gearman performance.
* Know how many tasks are queued or running.
* Correlate Gearman performance with the rest of your applications.

## Setup
### Installation

The Gearman check is included in the [Datadog Agent][1] package, so you don't need to install anything else on your Gearman job servers.

### Configuration


1. Edit the `gearmand.d/conf.yaml` file, in the `conf.d/` folder at the root of your [Agent's configuration directory][2] to start collecting your Gearman performance data.
    See the [sample gearmand.d/conf.yaml][3] for all available configuration options.
    ```yaml
    init_config:

    instances:
        - server: localhost
          port: 4730
    ```

2. [Restart the Agent][4]

### Validation

[Run the Agent's `status` subcommand][5] and look for `gearmand` under the Checks section.

## Data Collected
### Metrics

See [metadata.csv][6] for a list of metrics provided by this integration.

### Events
The Gearmand check does not include any events.

### Service Checks

`gearman.can_connect`:

Returns `Critical` if the Agent cannot connect to Gearman to collect metrics.

## Troubleshooting
Need help? Contact [Datadog support][7].

[1]: https://app.datadoghq.com/account/settings#agent
[2]: https://docs.datadoghq.com/agent/guide/agent-configuration-files/?tab=agentv6#agent-configuration-directory
[3]: https://github.com/DataDog/integrations-core/blob/master/gearmand/datadog_checks/gearmand/data/conf.yaml.example
[4]: https://docs.datadoghq.com/agent/guide/agent-commands/?tab=agentv6#start-stop-and-restart-the-agent
[5]: https://docs.datadoghq.com/agent/guide/agent-commands/?tab=agentv6#agent-status-and-information
[6]: https://github.com/DataDog/integrations-core/blob/master/gearmand/metadata.csv
[7]: https://docs.datadoghq.com/help
