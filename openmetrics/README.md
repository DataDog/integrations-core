# OpenMetrics Integration

## Overview

Extract custom metrics from any OpenMetrics or Prometheus endpoints.

<div class="alert alert-warning">All the metrics retrieved by this integration are considered <a href="https://docs.datadoghq.com/developers/metrics/custom_metrics">custom metrics</a>.</div>

The integration is compatible with both the [Prometheus exposition format][12] as well as with the [OpenMetrics specification][13].

## Setup

Follow the instructions below to install and configure this check for an Agent running on a host. For containerized environments, see the [Autodiscovery Integration Templates][1] for guidance on applying these instructions.

This integration has a latest mode (enabled by setting `openmetrics_endpoint` to point to the target endpoint) and a legacy mode (enabled by setting `prometheus_url` instead). To get all the most up-to-date features, Datadog recommends enabling the latest mode. For more information, see [Latest and Legacy Versioning For OpenMetrics-based Integrations][15].

### Installation

The OpenMetrics check is packaged with the [Datadog Agent v6.6.0 or later][2].

### Configuration

Edit the `conf.d/openmetrics.d/conf.yaml` file at the root of your [Agent's configuration directory][3]. See the [sample openmetrics.d/conf.yaml][4] for all available configuration options. This is the latest OpenMetrics check example as of Datadog Agent version 7.32.0. If you previously implemented this integration, see the [legacy example][5].

For each instance, the following parameters are required:

| Parameter        | Description                                                                                                                                                                                                                                                              |
| ---------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `openmetrics_endpoint` | The URL where your application metrics are exposed in Prometheus or OpenMetrics format (must be unique).                                                                                                                         |
| `namespace`      | The namespace to prepend to all metrics.                                                                                                                                                                                                                                 |
| `metrics`        | A list of metrics to retrieve as custom metrics. Add each metric to the list as `metric_name` or `metric_name: renamed` to rename it. The metrics are interpreted as regular expressions. Use `".*"` as a wildcard (`metric.*`) to fetch all matching metrics. **Note**: Regular expressions can potentially send a lot of custom metrics. |

Starting in Datadog Agent v7.32.0, in adherence to the [OpenMetrics specification standard][11], counter names ending in `_total` must be specified without the `_total` suffix. For example, to collect `promhttp_metric_handler_requests_total`, specify the metric name `promhttp_metric_handler_requests`. This submits to Datadog the metric name appended with `.count`, `promhttp_metric_handler_requests.count`.

This check has a limit of 2000 metrics per instance. The number of returned metrics is indicated when running the Datadog Agent [status command][6]. You can specify the metrics you are interested in by editing the configuration. To learn how to customize the metrics to collect, see [Prometheus and OpenMetrics Metrics Collection][7].

If you need to monitor more metrics, contact [Datadog support][8].

### Validation

[Run the Agent's status subcommand][6] and look for `openmetrics` under the Checks section.

## Data Collected

### Metrics

All metrics collected by the OpenMetrics check are forwarded to Datadog as custom metrics.

### Events

The OpenMetrics check does not include any events.

### Service Checks

The OpenMetrics check does not include any service checks.

## Troubleshooting

### High custom metrics billing

OpenMetrics configurations with generic wildcard values for the `metrics` option have significant impact on custom metrics billing.

Datadog recommends using specific metric names or partial metric name matches for more precise collection.

### Missing untyped metrics

By default, the integration skips metrics that come without a type on a Prometheus exposition. If you want to collect untyped metrics, you must explicitly specify their type in the `metrics` mapping, for example:

```yaml
  metrics:
    - "<NAME_OF_METRIC_WITHOUT_TYPE>":
        "type": "gauge"
```

Remember that metric names can be specified as regular expressions, making it possible to specify the type for a set of metrics without listing all of them individually.

### Errors parsing the OpenMetrics payload with Agent 7.46

The version of this integration shipped with version 7.46 of the Agent gives preference by default to the OpenMetrics format when requesting metrics from the metrics endpoint. It does so by setting the `Accept` header to `application/openmetrics-text;version=1.0.0,application/openmetrics-text;version=0.0.1;q=0.75,text/plain;version=0.0.4;q=0.5,*/*;q=0.1`. This was done in combination with dynamically determining which scraper to use based on the `Content-Type` it receives from the server, to reduce the need for manual setup.

Previous versions defaulted to `text/plain`, which normally results in the server returning metrics in the Prometheus exposition format. This means that updating to this version of the integration may result in switching from the Prometheus format to the OpenMetrics format.

Although the behavior should remain the same in most circumstances, some applications return metrics in a format that is not fully OpenMetrics-compliant, despite setting the `Content-Type` to signal the use of the OpenMetrics standard format. This may cause our integration to report errors while parsing the metrics payload.

If you see parsing errors when scraping the OpenMetrics endpoint with this new version, you can force the use of the less strict Prometheus format by manually setting the `Accept` header that the integration sends to `text/plain` using the `headers` option in the [configuration file][14]. For instance: 

```yaml
## All options defined here are available to all instances.
#
init_config:
  ...
instances:
  - openmetrics_endpoint: <OPENMETRICS_ENDPOINT>
    ...
    headers:
      Accept: text/plain
```

Need help? Contact [Datadog support][8].

## Further Reading

- [Configuring a OpenMetrics Check][9]
- [Writing a custom OpenMetrics Check][10]

[1]: https://docs.datadoghq.com/agent/kubernetes/integrations/
[2]: https://docs.datadoghq.com/getting_started/integrations/prometheus/?tab=docker#configuration
[3]: https://docs.datadoghq.com/agent/guide/agent-configuration-files/#agent-configuration-directory
[4]: https://github.com/DataDog/integrations-core/blob/master/openmetrics/datadog_checks/openmetrics/data/conf.yaml.example
[5]: https://github.com/DataDog/integrations-core/blob/7.30.x/openmetrics/datadog_checks/openmetrics/data/conf.yaml.example
[6]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[7]: https://docs.datadoghq.com/getting_started/integrations/prometheus/
[8]: https://docs.datadoghq.com/help/
[9]: https://docs.datadoghq.com/agent/openmetrics/
[10]: https://docs.datadoghq.com/developers/openmetrics/
[11]: https://github.com/OpenObservability/OpenMetrics/blob/main/specification/OpenMetrics.md#suffixes
[12]: https://prometheus.io/docs/instrumenting/exposition_formats/#text-based-format
[13]: https://github.com/OpenObservability/OpenMetrics/blob/main/specification/OpenMetrics.md#suffixes
[14]: https://github.com/DataDog/integrations-core/blob/7.46.x/openmetrics/datadog_checks/openmetrics/data/conf.yaml.example#L537-L546
[15]: https://docs.datadoghq.com/integrations/guide/versions-for-openmetrics-based-integrations
