# RiakCS Check

## Overview

Capture RiakCS metrics in Datadog to:

* Visualize key RiakCS metrics.
* Correlate RiakCS performance with the rest of your applications.

## Setup
### Installation

The RiakCS check is packaged with the Agent, so simply [install the Agent](https://app.datadoghq.com/account/settings#agent) on your RiakCS nodes. If you need the newest version of the check, install the `dd-check-riakcs` package.

### Configuration

Create a file `riakcs.yaml` in the Agent's `conf.d` directory:

```
init_config:

instances:
  - host: localhost 
    port: 8080 
    access_id: <YOUR_ACCESS_KEY>
    access_secret: <YOUR_ACCESS_SECRET>
#   is_secure: true # set to false if your endpoint doesn't use SSL
#   s3_root: s3.amazonaws.com # 
```

[Restart the Agent](https://help.datadoghq.com/hc/en-us/articles/203764515-Start-Stop-Restart-the-Datadog-Agent) to start sending RiakCS metrics to Datadog.

### Validation

Run the Agent's `info` subcommand and look for `riakcs` under the Checks section:

```
  Checks
  ======
    [...]

    riakcs
    -------
      - instance #0 [OK]
      - Collected 26 metrics, 0 events & 1 service check

    [...]
```

## Compatibility

The riakcs check is compatible with all major platforms.

## Data Collected
### Metrics

See [metadata.csv](https://github.com/DataDog/integrations-core/blob/master/riakcs/metadata.csv) for a list of metrics provided by this check.

### Events
The RiackCS check does not include any event at this time.

### Service Checks

**riakcs.can_connect**:

Returns CRITICAL if the Agent cannot connect to the RiakCS endpoint to collect metrics, otherwise OK.

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
To get a better idea of how (or why) to monitor Riak CS performance and availability with Datadog, check out our [series of blog posts](https://www.datadoghq.com/blog/monitor-riak-cs-performance-and-availability/) about it.
