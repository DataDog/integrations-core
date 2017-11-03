# Btrfs Integration

## Overview

Get metrics from btrfs service in real time to:

* Visualize and monitor btrfs states
* Be notified about btrfs failovers and events.

## Setup
### Installation

The Btrfs check is packaged with the Agent, so simply [install the Agent](https://app.datadoghq.com/account/settings#agent) on every server that uses at least one Btrfs filesystem.

### Configuration

1. Configure the Agent according to your needs, edit `conf.d/btrfs.yaml`. See the [sample btrfs.yaml](https://github.com/DataDog/integrations-core/blob/master/btrfs/conf.yaml.example) for all available configuration options.
2. [Restart the Agent](https://help.datadoghq.com/hc/en-us/articles/203764515-Start-Stop-Restart-the-Datadog-Agent)

### Validation

[Run the Agent's `info` subcommand](https://help.datadoghq.com/hc/en-us/articles/203764635-Agent-Status-and-Information) and look for `btrfs` under the Checks section:

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

## Compatibility

The Btrfs check is compatible with all major platforms.

## Data Collected
### Metrics
See [metadata.csv](https://github.com/DataDog/integrations-core/blob/master/btrfs/metadata.csv) for a list of metrics provided by this integration.

### Events
The Btrfs check does not include any event at this time.

### Service Checks
The Btrfs check does not include any service check at this time.

## Troubleshooting
Need help? Contact [Datadog Support](http://docs.datadoghq.com/help/).

## Further Reading

Learn more about infrastructure monitoring and all our integrations on [our blog](https://www.datadoghq.com/blog/)
