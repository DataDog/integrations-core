# Cassandra Integration

![Cassandra default dashboard][1]

## Overview

Get metrics from Cassandra service in real time to:

* Visualize and monitor Cassandra states
* Be notified about Cassandra failovers and events.

## Setup

Follow the instructions below to install and configure this check for an Agent running on a host. For containerized environments, see the [Autodiscovery Integration Templates][2] for guidance on applying these instructions.

### Installation

The Cassandra check is included in the [Datadog Agent][3] package, so you don't need to install anything else on your Cassandra nodes.

We recommend the use of Oracle's JDK for this integration.

This check has a limit of 350 metrics per instance. The number of returned metrics is indicated in the info page. You can specify the metrics you are interested in by editing the configuration below. To learn how to customize the metrics to collect visit the [JMX Checks documentation][4] for more detailed instructions. If you need to monitor more metrics, contact [Datadog support][5].

### Configuration

Edit the `cassandra.d/conf.yaml` file, in the `conf.d/` folder at the root of your [Agent's configuration directory][6] to start collecting your Cassandra [metrics](#metric-collection) and [logs](#log-collection).
See the [sample cassandra.d/conf.yaml][7] for all available configuration options.

#### Metric Collection

The default configuration of your `cassandra.d/conf.yaml` file activate the collection of your [Cassandra metrics](#metrics).
See the [sample  cassandra.d/conf.yaml][7] for all available configuration options.

#### Log Collection

**Available for Agent >6.0**

1. Collecting logs is disabled by default in the Datadog Agent, enable it in your `datadog.yaml` file:

    ```yaml
      logs_enabled: true
    ```

2. Add this configuration block to your `cassandra.d/conf.yaml` file to start collecting your Cassandra logs:

    ```yaml
      logs:
        - type: file
          path: /var/log/cassandra/*.log
          source: cassandra
          sourcecategory: database
          service: myapplication
    ```

    Change the `path` and `service` parameter values and configure them for your environment.
    See the [sample  cassandra.d/conf.yaml][7] for all available configuration options.

    To make sure that stacktraces are properly aggregated as one single log, a [multiline processing rule][8] can be added.

3. [Restart the Agent][9].

### Validation

[Run the Agent's status subcommand][10] and look for `cassandra` under the Checks section.

## Data Collected
### Metrics
See [metadata.csv][11] for a list of metrics provided by this integration.

### Events
The Cassandra check does not include any events.

### Service Checks
**cassandra.can_connect**:<br>
Returns `CRITICAL` if the Agent is unable to connect to and collect metrics from the monitored Cassandra instance, otherwise returns `OK`.

## Troubleshooting
Need help? Contact [Datadog support][5].

## Further Reading

* [How to monitor Cassandra performance metrics][12]
* [How to collect Cassandra metrics][13]
* [Monitoring Cassandra with Datadog][14]

[1]: https://raw.githubusercontent.com/DataDog/integrations-core/master/cassandra/images/cassandra_dashboard.png
[2]: https://docs.datadoghq.com/agent/autodiscovery/integrations
[3]: https://app.datadoghq.com/account/settings#agent
[4]: https://docs.datadoghq.com/integrations/java
[5]: https://docs.datadoghq.com/help
[6]: https://docs.datadoghq.com/agent/guide/agent-configuration-files/#agent-configuration-directory
[7]: https://github.com/DataDog/integrations-core/blob/master/cassandra/datadog_checks/cassandra/data/conf.yaml.example
[8]: https://docs.datadoghq.com/logs/log_collection/?tab=tailexistingfiles#multi-line-aggregation
[9]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[10]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[11]: https://github.com/DataDog/integrations-core/blob/master/cassandra/metadata.csv
[12]: https://www.datadoghq.com/blog/how-to-monitor-cassandra-performance-metrics
[13]: https://www.datadoghq.com/blog/how-to-collect-cassandra-metrics
[14]: https://www.datadoghq.com/blog/monitoring-cassandra-with-datadog
