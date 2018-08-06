# Nfsstat Integration

## Overview

The NFS integration collects metrics about mount points on the NFS client as it uses the `nfsiostat` tool that displays NFS client per-mount [statistics][1].

## Setup
### Installation

The NFSstat check is included in the [Datadog Agent][2] package, so you don't need to install anything else on your servers.

### Configuration

Edit the `nfsstat.d/conf.yaml` file, in the `conf.d/` folder at the root of your [Agent's configuration directory][9], to point to your nfsiostat binary script, or use the one included with the binary installer. See the [sample nfsstat.d/conf.yaml][3] for all available configuration options.

### Validation

[Run the Agent's `status` subcommand][4] and look for `nfsstat` under the Checks section.

## Data Collected
### Metrics
See [metadata.csv][5] for a list of metrics provided by this check.

### Events
The Nfststat check does not include any events at this time.

### Service Checks
The Nfsstat check does not include any service checks at this time.

## Troubleshooting
Need help? Contact [Datadog Support][6].

## Further Reading

* [Built a network monitor on an http check][8]


[1]: http://man7.org/linux/man-pages/man8/nfsiostat.8.html
[2]: https://app.datadoghq.com/account/settings#agent
[3]: https://github.com/DataDog/integrations-core/blob/master/nfsstat/datadog_checks/nfsstat/data/conf.yaml.example
[4]: https://docs.datadoghq.com/agent/faq/agent-commands/#agent-status-and-information
[5]: https://github.com/DataDog/integrations-core/blob/master/nfsstat/metadata.csv
[6]: https://docs.datadoghq.com/help/
[8]: https://docs.datadoghq.com/monitors/monitor_types/network
[9]: https://docs.datadoghq.com/agent/faq/agent-configuration-files/#agent-configuration-directory
