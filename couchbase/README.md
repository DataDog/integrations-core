# Couchbase Integration

![Couchbase Bytes Read][1]

## Overview

Identify busy buckets, track cache miss ratios, and more. This Agent check collects metrics like:

- Hard disk and memory used by data
- Current connections
- Total objects
- Operations per second
- Disk write queue size

And many more.

**Minimum Agent version:** 6.0.0

## Setup

### Installation

The Couchbase check is included in the [Datadog Agent][2] package, so you don't need to install anything else on your Couchbase nodes.

### Configuration

<!-- xxx tabs xxx -->
<!-- xxx tab "Host" xxx -->

#### Host

To configure this check for an Agent running on a host:

##### Metric collection

1. Edit the `couchbase.d/conf.yaml` file in the `conf.d/` folder at the root of your [Agent's configuration directory][3] to start collecting your Couchbase data. See the [sample couchbase.d/conf.yaml][4] for all available configuration options.

   The Couchbase integration supports two collection methods:

   **Prometheus-based collection (Couchbase 7.0+)**

   For Couchbase 7.0 and later, configure the `prometheus_url` to use the Prometheus exporter:

   ```yaml
   init_config:

   instances:
     ## @param prometheus_url - string - optional
     ## The Prometheus/OpenMetrics endpoint URL for the Prometheus-based check.
     #
     - prometheus_url: http://localhost:8091/metrics
   ```

   **Legacy REST API collection**

   For older versions or to use the legacy REST API:

   ```yaml
   init_config:

   instances:
     ## @param server - string - optional
     ## The server's url.
     #
     - server: http://localhost:8091
   ```

2. [Restart the Agent][5].

#### Log collection

_Available for Agent versions >6.0_

1. Collecting logs is disabled by default in the Datadog Agent, you need to enable it in `datadog.yaml`:

   ```yaml
   logs_enabled: true
   ```

2. Add this configuration block to your `couchbase.d/conf.yaml` file to start collecting your Couchbase Logs:

   ```yaml
   logs:
     - type: file
       path: /opt/couchbase/var/lib/couchbase/logs/couchdb.log
       source: couchdb
   ```

    Change the `path` and `service` parameter values and configure them for your environment. See the [sample couchbase.d/conf.yaml][4] for all available configuration options.

3. [Restart the Agent][5].

<!-- xxz tab xxx -->
<!-- xxx tab "Containerized" xxx -->

#### Containerized

For containerized environments, see the [Autodiscovery Integration Templates][6] for guidance on applying the parameters below.

##### Metric collection

For Prometheus-based collection (Couchbase 7.0+):

| Parameter            | Value                                            |
| -------------------- | ------------------------------------------------ |
| `<INTEGRATION_NAME>` | `couchbase`                                      |
| `<INIT_CONFIG>`      | blank or `{}`                                    |
| `<INSTANCE_CONFIG>`  | `{"prometheus_url": "http://%%host%%:8091/metrics"}` |

For legacy REST API collection:

| Parameter            | Value                                |
| -------------------- | ------------------------------------ |
| `<INTEGRATION_NAME>` | `couchbase`                          |
| `<INIT_CONFIG>`      | blank or `{}`                        |
| `<INSTANCE_CONFIG>`  | `{"server": "http://%%host%%:8091"}` |

<!-- xxz tab xxx -->
<!-- xxz tabs xxx -->

### Validation

[Run the Agent's `status` subcommand][7] and look for `couchbase` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][8] for a list of metrics provided by this integration.

### Events

The Couchbase check emits an event to Datadog each time the cluster is rebalanced.

### Service Checks

See [service_checks.json][9] for a list of service checks provided by this integration.

## Troubleshooting

Need help? Contact [Datadog support][10].

## Further Reading

- [Monitor key Couchbase metrics][11].

[1]: https://raw.githubusercontent.com/DataDog/integrations-core/master/couchbase/images/couchbase_graph.png
[2]: /account/settings/agent/latest
[3]: https://docs.datadoghq.com/agent/guide/agent-configuration-files/#agent-configuration-directory
[4]: https://github.com/DataDog/integrations-core/blob/master/couchbase/datadog_checks/couchbase/data/conf.yaml.example
[5]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[6]: https://docs.datadoghq.com/agent/kubernetes/integrations/
[7]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[8]: https://github.com/DataDog/integrations-core/blob/master/couchbase/metadata.csv
[9]: https://github.com/DataDog/integrations-core/blob/master/couchbase/assets/service_checks.json
[10]: https://docs.datadoghq.com/help/
[11]: https://www.datadoghq.com/blog/monitoring-couchbase-performance-datadog
