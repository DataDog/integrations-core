# Nfsstat Integration

## Overview

The NFS integration collects metrics about mount points on the NFS client as it uses the `nfsiostat` tool that displays NFS client per-mount [statistics][1].

## Setup

Find below instructions to install and configure the check when running the Agent on a host. See the [Autodiscovery Integration Templates documentation][2] to learn how to apply those instructions to a containerized environment.

### Installation

The NFSstat check is included in the [Datadog Agent][3] package, so you don't need to install anything else on your servers.

### Configuration

Edit the `nfsstat.d/conf.yaml` file, in the `conf.d/` folder at the root of your [Agent's configuration directory][4], to point to your nfsiostat binary script, or use the one included with the binary installer. See the [sample nfsstat.d/conf.yaml][5] for all available configuration options.

### Validation

[Run the Agent's `status` subcommand][6] and look for `nfsstat` under the Checks section.

## Data Collected
### Metrics
See [metadata.csv][7] for a list of metrics provided by this check.

### Events
The Nfststat check does not include any events.

### Service Checks
The Nfsstat check does not include any service checks.

## Troubleshooting
Need help? Contact [Datadog support][8].

## Further Reading

* [Built a network monitor on an http check][9]


[1]: http://man7.org/linux/man-pages/man8/nfsiostat.8.html
[2]: https://docs.datadoghq.com/agent/autodiscovery/integrations
[3]: https://app.datadoghq.com/account/settings#agent
[4]: https://docs.datadoghq.com/agent/guide/agent-configuration-files/?tab=agentv6#agent-configuration-directory
[5]: https://github.com/DataDog/integrations-core/blob/master/nfsstat/datadog_checks/nfsstat/data/conf.yaml.example
[6]: https://docs.datadoghq.com/agent/guide/agent-commands/?tab=agentv6#agent-status-and-information
[7]: https://github.com/DataDog/integrations-core/blob/master/nfsstat/metadata.csv
[8]: https://docs.datadoghq.com/help
[9]: https://docs.datadoghq.com/monitors/monitor_types/network
