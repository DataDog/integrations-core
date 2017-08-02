# Agent Check: swap

## Overview

This check monitors the number of bytes a host has swapped in and swapped out.

## Installation

The system swap check is packaged with the Agent, so simply [install the Agent](https://app.datadoghq.com/account/settings#agent) on any host.

## Configuration

Create a blank Agent check configuration file called `system_swap.yaml` in the Agent's `conf.d` directory:

```
# This check takes no initial configuration
init_config:

instances: [{}]
```

Restart the Agent to start collecting swap metrics.

## Validation

Run the Agent's `info` subcommand and look for `system_swap` under the Checks section:

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

## Metrics

See [metadata.csv](https://github.com/DataDog/integrations-core/blob/master/system_swap/metadata.csv) for a list of metrics provided by this check.
