# Btrfs Integration

## Overview

Get metrics from btrfs service in real time to:

* Visualize and monitor btrfs states
* Be notified about btrfs failovers and events.

## Installation

The Btrfs check is packaged with the Agent, so simply [install the Agent](https://app.datadoghq.com/account/settings#agent) on every server that uses at least one Btrfs filesystem.

## Configuration

## Validation

Run the Agent's `info` subcommand and look for `btrfs` under the Checks section:

```
  Checks
  ======
    [...]

    btrfs
    -------
      - instance #0 [OK]
      - Collected 26 metrics, 0 events & 1 service check

    [...]
```

## Troubleshooting

## Compatibility

The btrfs check is compatible with all major platforms.

## Metrics

## Events

## Service Checks
