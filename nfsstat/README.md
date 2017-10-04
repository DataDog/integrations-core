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

If you have any questions about Datadog or a use case our [Docs](https://docs.datadoghq.com/) didn’t mention, we’d love to help! Here’s how you can reach out to us:

### Visit the Knowledge Base

Learn more about what you can do in Datadog on the [Support Knowledge Base](https://datadog.zendesk.com/agent/).

### Web Support

Messages in the [event stream](https://app.datadoghq.com/event/stream) containing **@support-datadog** will reach our Support Team. This is a convenient channel for referencing graph snapshots or a particular event. In addition, we have a livechat service available during the day (EST) from any page within the app.

### By Email

You can also contact our Support Team via email at [support@datadoghq.com](mailto:support@datadoghq.com).

### Over Slack

Reach out to our team and other Datadog users on [Slack](http://chat.datadoghq.com/).

## Further Reading
### Datadog Blog
Learn more about infrastructure monitoring and all our integrations on [our blog](https://www.datadoghq.com/blog/)

### Knowledge Base
* [Built a network monitor on an http check](https://help.datadoghq.com/hc/en-us/articles/115003314726-Built-a-network-monitor-on-an-http-check-)
