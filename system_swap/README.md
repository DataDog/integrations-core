# Agent Check: swap

## Overview

This check monitors the number of bytes a host has swapped in and swapped out.

## Setup
### Installation

The system swap check is included in the [Datadog Agent][1] package, so you don't need to install anything else on your server.

### Configuration

1. Edit the `system_swap.d/conf.yaml` file in the `conf.d/` folder at the root of your [Agent's configuration directory][2]. See the [sample system_swap.d/conf.yaml][3] for all available configuration options:

    ```
    # This check takes no initial configuration
    init_config:

    instances: [{}]
    ```

2. [Restart the Agent][4] to start collecting swap metrics.

### Validation

[Run the Agent's `status` subcommand][5] and look for `system_swap` under the Checks section.

## Data Collected
### Metrics

See [metadata.csv][6] for a list of metrics provided by this check.

### Events
The System Swap check does not include any events at this time.

### Service Checks
The System Swap check does not include any service checks at this time.

## Troubleshooting
Need help? Contact [Datadog Support][7].

[1]: https://app.datadoghq.com/account/settings#agent
[2]: https://docs.datadoghq.com/agent/faq/agent-configuration-files/#agent-configuration-directory
[3]: https://github.com/DataDog/integrations-core/blob/master/system_swap/datadog_checks/system_swap/data/conf.yaml.example
[4]: https://docs.datadoghq.com/agent/faq/agent-commands/#start-stop-restart-the-agent
[5]: https://docs.datadoghq.com/agent/faq/agent-commands/#agent-status-and-information
[6]: https://github.com/DataDog/integrations-core/blob/master/system_swap/metadata.csv
[7]: https://docs.datadoghq.com/help
