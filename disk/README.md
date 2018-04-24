# Disk Check

## Overview

Collect metrics related to disk usage and IO.

## Setup
### Installation

The disk check is packaged with the Agent, so simply [install the Agent][1] anywhere you wish to use it.

### Configuration

The disk check is enabled by default, and the Agent will collect metrics on all local partitions. If you want to configure the check with custom options, create a file `disk.yaml` in the Agent's `conf.d` directory. See the [sample disk.yaml][2] for all available configuration options.

### Validation

[Run the Agent's `status` subcommand][3] and look for `disk` under the Checks section:

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

## Data Collected
### Metrics

See [metadata.csv][4] for a list of metrics provided by this integration.

### Events
The Disk check does not include any event at this time.

### Service Checks
The Disk check does not include any service check at this time.

## Troubleshooting
Need help? Contact [Datadog Support][5].

## Further Reading
Learn more about infrastructure monitoring and all our integrations on [our blog][6]


[1]: https://app.datadoghq.com/account/settings#agent
[2]: https://github.com/DataDog/integrations-core/blob/master/disk/conf.yaml.default
[3]: https://docs.datadoghq.com/agent/faq/agent-commands/#agent-status-and-information
[4]: https://github.com/DataDog/integrations-core/blob/master/disk/metadata.csv
[5]: http://docs.datadoghq.com/help/
[6]: https://www.datadoghq.com/blog/
