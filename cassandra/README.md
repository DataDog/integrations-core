# Cassandra Integration

## Overview

Get metrics from cassandra service in real time to:

* Visualize and monitor cassandra states
* Be notified about cassandra failovers and events.

## Setup
### Installation

The Cassandra check is packaged with the Agent, so simply [install the Agent](https://app.datadoghq.com/account/settings#agent) on your Cassandra nodes.

We recommend the use of Oracle's JDK for this integration. 

This check has a limit of 350 metrics per instance. The number of returned metrics is indicated in the info page. You can specify the metrics you are interested in by editing the configuration below. To learn how to customize the metrics to collect visit the [JMX Checks documentation](https://docs.datadoghq.com/integrations/java/) for more detailed instructions. If you need to monitor more metrics, please send us an email at support@datadoghq.com

### Configuration

1. Configure the Agent to connect to Cassandra, just edit `conf.d/cassandra.yaml`
2. [Restart the Agent](https://help.datadoghq.com/hc/en-us/articles/203764515-Start-Stop-Restart-the-Datadog-Agent)

### Validation

Run the Agent's `info` subcommand and look for `cassandra` under the Checks section:

```
  Checks
  ======
    [...]

    cassandra
    -------
      - instance #0 [OK]
      - Collected 26 metrics, 0 events & 1 service check

    [...]
```

## Compatibility

The cassandra check is compatible with all major platforms.

## Data Collected
### Metrics
See [metadata.csv](https://github.com/DataDog/integrations-core/blob/master/cassandra/metadata.csv) for a list of metrics provided by this integration.

### Events
The Cassandra check does not include any event at this time.

### Service Checks
The Cassandra check does not include any service check at this time.

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
To get a better idea of how (or why) to integrate your Cassandra cluster with Datadog, check out our [series of blog posts](https://www.datadoghq.com/blog/how-to-monitor-cassandra-performance-metrics) about it.
