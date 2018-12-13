# Cassandra Integration

![Cassandra default dashboard][1]

## Overview

Get metrics from Cassandra service in real time to:

* Visualize and monitor Cassandra states
* Be notified about Cassandra failovers and events.

## Setup
### Installation

The Cassandra check is included in the [Datadog Agent][2] package, so you don't need to install anything else on your Cassandra nodes.

We recommend the use of Oracle's JDK for this integration.

This check has a limit of 350 metrics per instance. The number of returned metrics is indicated in the info page. You can specify the metrics you are interested in by editing the configuration below. To learn how to customize the metrics to collect visit the [JMX Checks documentation][3] for more detailed instructions. If you need to monitor more metrics, please send us an email at support@datadoghq.com

### Configuration

Edit the `cassandra.d/conf.yaml` file, in the `conf.d/` folder at the root of your [Agent's configuration directory][4] to start collecting your Cassandra [metrics](#metric-collection) and [logs](#log-collection).
See the [sample cassandra.d/conf.yaml][5] for all available configuration options.

#### Metric Collection

The default configuration of your `cassandra.d/conf.yaml` file activate the collection of your [Cassandra metrics](#metrics).
See the [sample  cassandra.d/conf.yaml][5] for all available configuration options.

#### Log Collection

**Available for Agent >6.0**

* Collecting logs is disabled by default in the Datadog Agent, enable it in your `datadog.yaml` file:

  ```yaml
  logs_enabled: true
  ```

* Add this configuration block to your `cassandra.d/conf.yaml` file to start collecting your Cassandra logs:

  ```yaml
  logs:
    - type: file
      path: /var/log/cassandra/*.log
      source: cassandra
      sourcecategory: database
      service: myapplication
  ```

  Change the `path` and `service` parameter values and configure them for your environment.
  See the [sample  cassandra.d/conf.yaml][5] for all available configuration options.

* [Restart the Agent][6].

### Validation

[Run the Agent's `status` subcommand][7] and look for `cassandra` under the Checks section.

## Data Collected
### Metrics
See [metadata.csv][8] for a list of metrics provided by this integration.

### Events
The Cassandra check does not include any events at this time.

### Service Checks
**cassandra.can_connect**

Returns `CRITICAL` if the Agent is unable to connect to and collect metrics from the monitored Cassandra instance. Returns `OK` otherwise.

## Troubleshooting
Need help? Contact [Datadog Support][9].

## Further Reading

* [How to monitor Cassandra performance metrics][10]
* [How to collect Cassandra metrics][11]
* [Monitoring Cassandra with Datadog][12]


[1]: https://raw.githubusercontent.com/DataDog/integrations-core/master/cassandra/images/cassandra_dashboard.png
[2]: https://app.datadoghq.com/account/settings#agent
[3]: https://docs.datadoghq.com/integrations/java
[4]: https://docs.datadoghq.com/agent/faq/agent-configuration-files/#agent-configuration-directory
[5]: https://github.com/DataDog/integrations-core/blob/master/cassandra/datadog_checks/cassandra/data/conf.yaml.example
[6]: https://docs.datadoghq.com/agent/faq/agent-commands/#start-stop-restart-the-agent
[7]: https://docs.datadoghq.com/agent/faq/agent-commands/#agent-status-and-information
[8]: https://github.com/DataDog/integrations-core/blob/master/cassandra/metadata.csv
[9]: https://docs.datadoghq.com/help
[10]: https://www.datadoghq.com/blog/how-to-monitor-cassandra-performance-metrics
[11]: https://www.datadoghq.com/blog/how-to-collect-cassandra-metrics
[12]: https://www.datadoghq.com/blog/monitoring-cassandra-with-datadog
