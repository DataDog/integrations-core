# Cassandra Integration
{{< img src="integrations/cassandra/cassandra.png" alt="Cassandra default dashboard" responsive="true" popup="true">}}
## Overview

Get metrics from cassandra service in real time to:

* Visualize and monitor cassandra states
* Be notified about cassandra failovers and events.

## Setup
### Installation

The Cassandra check is packaged with the Agent, so simply [install the Agent](https://app.datadoghq.com/account/settings#agent) on your Cassandra nodes.

If you need the newest version of the Cassandra check, install the `dd-check-cassandra` package; this package's check overrides the one packaged with the Agent. See the [integrations-core repository README.md for more details](https://github.com/DataDog/integrations-core#installing-the-integrations).

We recommend the use of Oracle's JDK for this integration.

This check has a limit of 350 metrics per instance. The number of returned metrics is indicated in the info page. You can specify the metrics you are interested in by editing the configuration below. To learn how to customize the metrics to collect visit the [JMX Checks documentation](https://docs.datadoghq.com/integrations/java/) for more detailed instructions. If you need to monitor more metrics, please send us an email at support@datadoghq.com

### Configuration

1. Configure the Agent to connect to Cassandra, just edit `conf.d/cassandra.yaml`. See the [sample  cassandra.yaml](https://github.com/DataDog/integrations-core/blob/master/cassandra/conf.yaml.example) for all available configuration options.
2. [Restart the Agent](https://docs.datadoghq.com/agent/faq/start-stop-restart-the-datadog-agent)

### Validation

[Run the Agent's `status` subcommand](https://docs.datadoghq.com/agent/faq/agent-status-and-information/) and look for `cassandra` under the Checks section:

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
Need help? Contact [Datadog Support](http://docs.datadoghq.com/help/).

## Further Reading

* [How to monitor Cassandra performance metrics](https://www.datadoghq.com/blog/how-to-monitor-cassandra-performance-metrics/)
* [How to collect Cassandra metrics](https://www.datadoghq.com/blog/how-to-collect-cassandra-metrics/)
* [Monitoring Cassandra with Datadog](https://www.datadoghq.com/blog/monitoring-cassandra-with-datadog/)
