# Nfsstat Integration

## Overview

The NFS integration collects metrics about mount points on the NFS client as it uses the `nfsiostat` tool that displays NFS client per-mount [statistics](http://man7.org/linux/man-pages/man8/nfsiostat.8.html).

## Setup
### Installation

The NFSstat check is packaged with the Agent, so simply [install the Agent](https://app.datadoghq.com/account/settings#agent) on your servers.

### Configuration

Edit the `nfsstat.yaml` file to point to your nfsiostat binary script, or use the one included with the binary installer. See the [sample nfsstat.yaml](https://github.com/DataDog/integrations-core/blob/master/nfsstat/conf.yaml.example) for all available configuration options.

### Validation

[Run the Agent's `status` subcommand](https://docs.datadoghq.com/agent/faq/agent-commands/#agent-status-and-information) and look for `nfsstat` under the Checks section:

    Checks
    ======

        nfsstat
        -----------
          - instance #0 [OK]
          - Collected 39 metrics, 0 events & 7 service checks

## Compatibility

The nfsstat check is compatible with linux

## Data Collected
### Metrics
See [metadata.csv](https://github.com/DataDog/integrations-core/blob/master/nfsstat/metadata.csv) for a list of metrics provided by this check.

### Events
The nfststat check does not include any event at this time.

### Service Checks
The nfsstat check does not include any service check at this time.

## Troubleshooting
Need help? Contact [Datadog Support](http://docs.datadoghq.com/help/).

## Further Reading
### Datadog Blog
Learn more about infrastructure monitoring and all our integrations on [our blog](https://www.datadoghq.com/blog/)

### Knowledge Base
* [Built a network monitor on an http check](https://docs.datadoghq.com/monitors/monitor_types/network)
