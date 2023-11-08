# Agent Check: CockroachDB

## Overview

The CockroachDB check monitors the overall health and performance of a [CockroachDB][1] cluster.

## Setup

### Installation

The CockroachDB check is included in the [Datadog Agent][2] package, so you do not
need to install anything else on your server.

Starting with version 1.9.0, this OpenMetrics-based integration has a latest mode (enabled by setting `openmetrics_endpoint` to point to the target endpoint) and a legacy mode (enabled by setting `prometheus_url` instead). To get all the most up-to-date features, Datadog recommends enabling the latest mode. Note that the latest mode requires Python 3. For more information, see [Latest and Legacy Versioning For OpenMetrics-based Integrations][14].

For hosts unable to use Python 3, or to use legacy mode, see the following [configuration][13].

### Configuration

<!-- xxx tabs xxx -->
<!-- xxx tab "Host" xxx -->

#### Host

To configure this check for an Agent running on a host:

##### Metric collection

1. Edit the `cockroachdb.d/conf.yaml` file, in the `conf.d/` folder at the root of your [Agent's configuration directory][3] to start collecting your CockroachDB performance data. For a multi-node cluster, configure a separate check instance for each node. See the [sample cockroachdb.d/conf.yaml][4] for all available configuration options.

   ```yaml
   init_config:

   instances:
       ## @param openmetrics_endpoint - string - required
       ## The URL exposing metrics in the OpenMetrics format.
       #
     - openmetrics_endpoint: http://localhost:8080/_status/vars
   ```

2. [Restart the Agent][5].

##### Log collection

_Available for Agent version 6.0 or later_

1. Collecting logs is disabled by default in the Datadog Agent. Enable it in `datadog.yaml`:

   ```yaml
   logs_enabled: true
   ```

2. Add this configuration block to your `cockroachdb.d/conf.yaml` file to start collecting your CockroachDB logs:

   ```yaml
   logs:
    - type: file
      path: /var/lib/cockroach/logs/cockroach.log
      source: cockroachdb
      service: cockroachdb
      log_processing_rules:
      - type: multi_line
        name: new_log_start_with_status_and_date
        pattern: [A-Z]\d{6}\s\d+\:\d+\:\d+\.\d+
   ```

    Change the `path` and `service` parameter values and configure them for your environment. See the [sample cockroachdb.d/conf.yaml][4] for all available configuration options.

3. [Restart the Agent][5].

<!-- xxz tab xxx -->
<!-- xxx tab "Containerized" xxx -->

#### Containerized

For containerized environments, see the [Autodiscovery Integration Templates][6] for guidance on applying the parameters below.

| Parameter            | Value                                                    |
| -------------------- | -------------------------------------------------------- |
| `<INTEGRATION_NAME>` | `cockroachdb`                                            |
| `<INIT_CONFIG>`      | blank or `{}`                                            |
| `<INSTANCE_CONFIG>`  | `{"openmetrics_endpoint":"http://%%host%%:8080/_status/vars"}` |

##### Log collection

Collecting logs is disabled by default in the Datadog Agent. To enable it, see the [Docker Log Collection][7].

Then, set [log integrations][7] as Docker labels:

```yaml
LABEL "com.datadoghq.ad.logs"='[{"source": "cockroachdb", "service": "<SERVICE_NAME>"}]'
```

<!-- xxz tab xxx -->
<!-- xxz tabs xxx -->

### Validation

[Run the Agent's `status` subcommand][8] and look for `cockroachdb` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][9] for a list of metrics provided by this integration.

### Service Checks

The CockroachDB check does not include any service checks.

### Events

The CockroachDB check does not include any events.

## Troubleshooting

Need help? Contact [Datadog support][10].

## Further Reading

Additional helpful documentation, links, and articles:

- [Monitor CockroachDB performance metrics with Datadog][11]

[1]: https://www.cockroachlabs.com/product/cockroachdb
[2]: https://app.datadoghq.com/account/settings/agent/latest
[3]: https://docs.datadoghq.com/agent/guide/agent-configuration-files/
[4]: https://github.com/DataDog/integrations-core/blob/master/cockroachdb/datadog_checks/cockroachdb/data/conf.yaml.example
[5]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[6]: https://docs.datadoghq.com/agent/kubernetes/integrations/
[7]: https://docs.datadoghq.com/agent/docker/log/?tab=containerinstallation#log-integrations
[8]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[9]: https://github.com/DataDog/integrations-core/blob/master/cockroachdb/metadata.csv
[10]: https://docs.datadoghq.com/help/
[11]: https://www.datadoghq.com/blog/monitor-cockroachdb-performance-metrics-with-datadog
[12]: https://docs.datadoghq.com/integrations/openmetrics/
[13]: https://github.com/DataDog/integrations-core/blob/7.33.x/cockroachdb/datadog_checks/cockroachdb/data/conf.yaml.example
[14]: https://docs.datadoghq.com/integrations/guide/versions-for-openmetrics-based-integrations