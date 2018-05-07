# Nfsstat Integration

## Overview

The NFS integration collects metrics about mount points on the NFS client as it uses the `nfsiostat` tool that displays NFS client per-mount [statistics][1].

## Setup
### Installation

The NFSstat check is packaged with the Agent, so simply [install the Agent][2] on your servers.

### Configuration

Edit the `nfsstat.d/conf.yaml` file, in the `conf.d/` folder at the root of your Agent's directory, to point to your nfsiostat binary script, or use the one included with the binary installer. See the [sample nfsstat.d/conf.yaml][3] for all available configuration options.

### Validation

[Run the Agent's `status` subcommand][4] and look for `nfsstat` under the Checks section.

## Data Collected
### Metrics
See [metadata.csv][5] for a list of metrics provided by this check.

### Events
The Nfststat check does not include any event at this time.

### Service Checks
The Nfsstat check does not include any service check at this time.

## Troubleshooting
Need help? Contact [Datadog Support][6].

## Further Reading
### Datadog Blog
Learn more about infrastructure monitoring and all our integrations on [our blog][7]

### Knowledge Base
* [Built a network monitor on an http check][8]


[1]: http://man7.org/linux/man-pages/man8/nfsiostat.8.html
[2]: https://app.datadoghq.com/account/settings#agent
[3]: https://github.com/DataDog/integrations-core/blob/master/nfsstat/conf.yaml.example
[4]: https://docs.datadoghq.com/agent/faq/agent-commands/#agent-status-and-information
[5]: https://github.com/DataDog/integrations-core/blob/master/nfsstat/metadata.csv
[6]: http://docs.datadoghq.com/help/
[7]: https://www.datadoghq.com/blog/
[8]: https://docs.datadoghq.com/monitors/monitor_types/network
