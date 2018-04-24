# Agent Check: swap

## Overview

This check monitors the number of bytes a host has swapped in and swapped out.

## Setup
### Installation

The system swap check is packaged with the Agent, so simply [install the Agent][1] on any host.

### Configuration

Create a blank Agent check configuration file called `system_swap.yaml` in the Agent's `conf.d` directory. See the [sample system_swap.yaml][2] for all available configuration options:

```
# This check takes no initial configuration
init_config:

instances: [{}]
```

[Restart the Agent][3] to start collecting swap metrics.

### Validation

[Run the Agent's `status` subcommand][4] and look for `system_swap` under the Checks section:

```
  Checks
  ======
    [...]

    system_swap
    -------
      - instance #0 [OK]
      - Collected 2 metrics, 0 events & 0 service checks

    [...]
```

## Compatibility

The system_swap check is compatible with all major platforms.

## Data Collected
### Metrics

See [metadata.csv][5] for a list of metrics provided by this check.

### Events
The System Swap check does not include any event at this time.

### Service Checks
The System Swap check does not include any service check at this time.

## Troubleshooting
Need help? Contact [Datadog Support][6].

## Further Reading
Learn more about infrastructure monitoring and all our integrations on [our blog][7]


[1]: https://app.datadoghq.com/account/settings#agent
[2]: https://github.com/DataDog/integrations-core/blob/master/system_swap/conf.yaml.example
[3]: https://docs.datadoghq.com/agent/faq/agent-commands/#start-stop-restart-the-agent
[4]: https://docs.datadoghq.com/agent/faq/agent-commands/#agent-status-and-information
[5]: https://github.com/DataDog/integrations-core/blob/master/system_swap/metadata.csv
[6]: http://docs.datadoghq.com/help/
[7]: https://www.datadoghq.com/blog/
