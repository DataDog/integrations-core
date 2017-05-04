# Disk Check

# Overview

Collect metrics related to disk usage and IO.

# Installation

The disk check is packaged with the Agent, so simply [install the Agent](https://app.datadoghq.com/account/settings#agent) anywhere you wish to use it.

# Configuration

The disk check is enabled by default, and the Agent will collect metrics on all local partitions. If you want to configure the check with custom options, create a file `disk.yaml` in the Agent's `conf.d` directory. See the [sample disk.yaml](https://github.com/DataDog/integrations-core/blob/master/disk/conf.yaml.default) for all available configuration options.

# Validation

Run the Agent's `info` subcommand and look for `disk` under the Checks section:

```
  Checks
  ======
    [...]

    disk
    -------
      - instance #0 [OK]
      - Collected 40 metrics, 0 events & 0 service checks

    [...]
```

# Troubleshooting

# Metrics

See [metadata.csv](https://github.com/DataDog/integrations-core/blob/master/disk/metadata.csv) for a list of metrics provided by this check.
