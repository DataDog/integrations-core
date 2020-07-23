# Cassandra Integration

![Cassandra default dashboard][1]

## Overview

Get metrics from Cassandra in real time to:

- Visualize and monitor Cassandra states.
- Be notified about Cassandra failovers and events.

## Setup

### Installation

The Cassandra check is included in the [Datadog Agent][2] package, so you don't need to install anything else on your Cassandra nodes. It's recommended to use Oracle's JDK for this integration.

**Note**: This check has a limit of 350 metrics per instance. The number of returned metrics is indicated in the info page. You can specify the metrics you are interested in by editing the configuration below. To learn how to customize the metrics to collect visit the [JMX Checks documentation][3] for more detailed instructions. If you need to monitor more metrics, contact [Datadog support][4].

### Configuration

Follow the instructions below to configure this check for an Agent running on a host. For containerized environments, see the [Containerized](#containerized) section.

#### Host

##### Metric Collection

1. The default configuration of your `cassandra.d/conf.yaml` file activate the collection of your [Cassandra metrics](#metrics). See the [sample cassandra.d/conf.yaml][5] for all available configuration options.

2. [Restart the Agent][6].

##### Log Collection

_Available for Agent versions >6.0_

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
         service: myapplication
         log_processing_rules:
            - type: multi_line
              name: log_start_with_date
              # pattern to match: DEBUG [ScheduledTasks:1] 2019-12-30
              pattern: '[A-Z]+ +\[[^\]]+\] +\d{4}-\d{2}-\d{2}'
   ```

    Change the `path` and `service` parameter values and configure them for your environment. See the [sample cassandra.d/conf.yaml][5] for all available configuration options.

    To make sure that stacktraces are properly aggregated as one single log, a [multiline processing rule][7] can be added.

3. [Restart the Agent][6].

#### Containerized

For containerized environments, see the [Autodiscovery Integration Templates][8] for guidance on applying the parameters below.

##### Metric collection

For containerized environments, see the [Autodiscovery with JMX][9] guide.

##### Log collection

_Available for Agent versions >6.0_

Collecting logs is disabled by default in the Datadog Agent. To enable it, see [Kubernetes log collection documentation][10].

| Parameter      | Value                                                  |
| -------------- | ------------------------------------------------------ |
| `<LOG_CONFIG>` | `{"source": "cassandra", "service": "<SERVICE_NAME>"}` |

### Validation

[Run the Agent's status subcommand][11] and look for `cassandra` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][12] for a list of metrics provided by this integration.

### Events

The Cassandra check does not include any events.

### Service Checks

**cassandra.can_connect**:<br>
Returns `CRITICAL` if the Agent is unable to connect to and collect metrics from the monitored Cassandra instance, otherwise returns `OK`.

## Troubleshooting

Need help? Contact [Datadog support][4].

## Further Reading

- [How to monitor Cassandra performance metrics][13]
- [How to collect Cassandra metrics][14]
- [Monitoring Cassandra with Datadog][15]

[1]: https://raw.githubusercontent.com/DataDog/integrations-core/master/cassandra/images/cassandra_dashboard.png
[2]: https://app.datadoghq.com/account/settings#agent
[3]: https://docs.datadoghq.com/integrations/java/
[4]: https://docs.datadoghq.com/help/
[5]: https://github.com/DataDog/integrations-core/blob/master/cassandra/datadog_checks/cassandra/data/conf.yaml.example
[6]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[7]: https://docs.datadoghq.com/agent/logs/advanced_log_collection/?tab=exclude_at_match#multi-line-aggregation
[8]: https://docs.datadoghq.com/agent/kubernetes/integrations/
[9]: https://docs.datadoghq.com/agent/guide/autodiscovery-with-jmx/?tab=containerizedagent
[10]: https://docs.datadoghq.com/agent/kubernetes/log/
[11]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[12]: https://github.com/DataDog/integrations-core/blob/master/cassandra/metadata.csv
[13]: https://www.datadoghq.com/blog/how-to-monitor-cassandra-performance-metrics
[14]: https://www.datadoghq.com/blog/how-to-collect-cassandra-metrics
[15]: https://www.datadoghq.com/blog/monitoring-cassandra-with-datadog
