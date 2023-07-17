# Cassandra Nodetool Integration

![Cassandra default dashboard][1]

## Overview

This check collects metrics for your Cassandra cluster that are not available through [jmx integration][2]. It uses the `nodetool` utility to collect them.

## Setup

### Installation

The Cassandra Nodetool check is included in the [Datadog Agent][3] package, so you don't need to install anything else on your Cassandra nodes.

### Configuration

Follow the instructions below to configure this check for an Agent running on a host. For containerized environments, see the [Containerized](#containerized) section.

<!-- xxx tabs xxx -->
<!-- xxx tab "Host" xxx -->

#### Host

1. Edit the file `cassandra_nodetool.d/conf.yaml` in the `conf.d/` folder at the root of your [Agent's configuration directory][4]. See the [sample cassandra_nodetool.d/conf.yaml][5] for all available configuration options:

   ```yaml
   init_config:

   instances:
     ## @param keyspaces - list of string - required
     ## The list of keyspaces to monitor.
     ## An empty list results in no metrics being sent.
     #
     - keyspaces:
         - "<KEYSPACE_1>"
         - "<KEYSPACE_2>"
   ```

2. [Restart the Agent][6].

#### Log collection

Cassandra Nodetool logs are collected by the Cassandra integration. See the [log collection instructions for Cassandra][7].

<!-- xxz tab xxx -->
<!-- xxx tab "Containerized" xxx -->

#### Containerized

For containerized environments, use the official [Prometheus exporter][15] in the pod, and then use Autodiscovery in the Agent to find the pod and query the endpoint.

<!-- xxz tab xxx -->
<!-- xxz tabs xxx -->

### Validation

[Run the Agent's `status` subcommand][8] and look for `cassandra_nodetool` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][9] for a list of metrics provided by this integration.

### Events

The Cassandra_nodetool check does not include any events.

### Service Checks

See [service_checks.json][10] for a list of service checks provided by this integration.

## Troubleshooting

Need help? Contact [Datadog support][11].

## Further Reading

- [How to monitor Cassandra performance metrics][12]
- [How to collect Cassandra metrics][13]
- [Monitoring Cassandra with Datadog][14]

[1]: https://raw.githubusercontent.com/DataDog/integrations-core/master/cassandra_nodetool/images/cassandra_dashboard.png
[2]: https://github.com/DataDog/integrations-core/tree/master/cassandra
[3]: https://app.datadoghq.com/account/settings/agent/latest
[4]: https://docs.datadoghq.com/agent/guide/agent-configuration-files/#agent-configuration-directory
[5]: https://github.com/DataDog/integrations-core/blob/master/cassandra_nodetool/datadog_checks/cassandra_nodetool/data/conf.yaml.example
[6]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[7]: https://github.com/DataDog/integrations-core/tree/master/cassandra#log-collection
[8]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[9]: https://github.com/DataDog/integrations-core/blob/master/cassandra_nodetool/metadata.csv
[10]: https://github.com/DataDog/integrations-core/blob/master/cassandra_nodetool/assets/service_checks.json
[11]: https://docs.datadoghq.com/help/
[12]: https://www.datadoghq.com/blog/how-to-monitor-cassandra-performance-metrics
[13]: https://www.datadoghq.com/blog/how-to-collect-cassandra-metrics
[14]: https://www.datadoghq.com/blog/monitoring-cassandra-with-datadog
[15]: https://github.com/prometheus/jmx_exporter
