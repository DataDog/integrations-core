# Nfsstat Integration

## Overview

nfsiostat is a tool that gets metrics from NFS mounts. This check grabs these metrics.

## Setup
### Installation

Install the `dd-check-nfsstat` package manually or with your favorite configuration manager

### Configuration

Edit the `nfsstat.yaml` file to point to your nfsiostat binary script, or use the one included with the binary installer.

### Validation

When you run `datadog-agent info` you should see something like the following:

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
* [Built a network monitor on an http check](https://help.datadoghq.com/hc/en-us/articles/115003314726-Built-a-network-monitor-on-an-http-check-)
