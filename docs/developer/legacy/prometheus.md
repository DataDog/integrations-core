# Prometheus/OpenMetrics V1

-----

[Prometheus](https://prometheus.io) is an open source monitoring system for timeseries metric data. Many Datadog
integrations collect metrics based on Prometheus exported data sets.

Prometheus-based integrations use the OpenMetrics exposition format to collect metrics.

## Interface

All functionality is exposed by the `OpenMetricsBaseCheck` and `OpenMetricsScraperMixin` classes.

::: datadog_checks.base.checks.openmetrics.base_check.OpenMetricsBaseCheck
    options:
      heading_level: 4
      members:
        - __init__
        - check
        - get_scraper_config

::: datadog_checks.base.checks.openmetrics.mixins.OpenMetricsScraperMixin
    options:
      heading_level: 4
      members:
        - parse_metric_family
        - scrape_metrics
        - process
        - poll
        - submit_openmetric
        - process_metric
        - create_scraper_configuration

## Options

Some options can be set globally in `init_config` (with `instances` taking precedence).
For complete documentation of every option, see the associated configuration templates for the
[instances][config-spec-template-instances-openmetrics-legacy] and [init_config][config-spec-template-init-config-openmetrics-legacy] sections.

### Config changes between versions
There are config option changes between OpenMetrics V1 and V2, so check if any updated OpenMetrics instances use deprecated options and update accordingly.


| OpenMetrics V1              | OpenMetrics V2                       |
|-----------------------------|--------------------------------------|
| `ignore_metrics`            | `exclude_metrics`                    |
| `prometheus_metrics_prefix` | `raw_metric_prefix`                  |
| `health_service_check`      | `enable_health_service_check`        |
| `labels_mapper`             | `rename_labels`                      |
| `label_joins`               | `share_labels`*                      |
| `send_histograms_buckets`   | `collect_histogram_buckets`          |
| `send_distribution_buckets` | `histogram_buckets_as_distributions` |

**Note**: The `type_overrides` option is incorporated in the `metrics` option. This `metrics` option defines the list of which metrics to collect from the `openmetrics_endpoint`, and it can be used to remap the names and types of exposed metrics as well as use regular expression to match exposed metrics.

`share_labels` are used to join labels with a 1:1 mapping and can take other parameters for sharing. More information can be found in the [conf.yaml.exmaple][conf-yaml-example-share-labels].


All [HTTP options](../base/http.md#options) are also supported.


::: datadog_checks.base.checks.openmetrics.base_check.StandardFields
    options:
      show_root_heading: false
      show_root_toc_entry: false

## Prometheus to Datadog metric types

The Openmetrics Base Check supports various configurations for submitting Prometheus metrics to Datadog.
We currently support Prometheus `gauge`, `counter`, `histogram`, and `summary` metric types.

### Gauge
A gauge metric represents a single numerical value that can arbitrarily go up or down.

Prometheus gauge metrics are submitted as Datadog gauge metrics.

### Counter

A [Prometheus counter](https://prometheus.io/docs/concepts/metric_types/#counter) is a cumulative metric that represents
a single monotonically increasing counter whose value can only increase or be reset to zero on restart.

| Config Option | Value | Datadog Metric Submitted |
| ------------- | ----- | ------------------------ |
| `send_monotonic_counter` | `true` (default)| `monotonic_count` |
| &nbsp; | `false` | `gauge` |

### Histogram

A [Prometheus histogram](https://prometheus.io/docs/concepts/metric_types/#histogram) samples observations and counts
them in configurable buckets along with a sum of all observed values.

Histogram metrics ending in:

- `_sum` represent the total sum of all observed values. Generally [sums](https://prometheus.io/docs/practices/histograms/#count-and-sum-of-observations)
 are like counters but it's also possible for a negative observation which would not behave like a typical always increasing counter.
- `_count` represent the total number of events that have been observed.
- `_bucket` represent the cumulative counters for the observation buckets. Note that buckets are only submitted if `send_histograms_buckets` is enabled.


| Subtype | Config Option | Value | Datadog Metric Submitted |
| ------- | ------------- | ----- | ------------------------ |
| &nbsp; | `send_distribution_buckets` | `true` | The entire histogram can be submitted as a single [distribution metric][datadog-distribution-metrics]. If the option is enabled, none of the subtype metrics will be submitted.
| `_sum` | `send_distribution_sums_as_monotonic` | `false` (default) | `gauge` |
| &nbsp; | &nbsp; | `true` | `monotonic_count` |
| `_count` | `send_distribution_counts_as_monotonic` | `false` (default) | `gauge` |
| &nbsp; | &nbsp; | `true` | `monotonic_count` |
| `_bucket` | `non_cumulative_buckets` | `false` (default) | `gauge` |
| &nbsp; | &nbsp; | `true` | `monotonic_count` under `.count` metric name if `send_distribution_counts_as_monotonic` is enabled. Otherwise, `gauge`. |


### Summary
Prometheus [summary metrics](https://prometheus.io/docs/concepts/metric_types/#summary) are similar to histograms but allow configurable quantiles.

Summary metrics ending in:

- `_sum` represent the total sum of all observed values. Generally [sums](https://prometheus.io/docs/practices/histograms/#count-and-sum-of-observations)
 are like counters but it's also possible for a negative observation which would not behave like a typical always increasing counter.
- `_count` represent the total number of events that have been observed.
-  metrics with labels like `{quantile="<φ>"}` represent the streaming quantiles of observed events.

| Subtype | Config Option | Value | Datadog Metric Submitted |
| ------- | ------------- | ----- | ------------------------ |
| `_sum` | `send_distribution_sums_as_monotonic` | `false` (default) |`gauge` |
| &nbsp; | &nbsp; | `true` | `monotonic_count` |
| `_count` | `send_distribution_counts_as_monotonic` | `false` (default) | `gauge` |
| &nbsp; | &nbsp; | `true` | `monotonic_count` |
| `_quantile` | &nbsp; | &nbsp; | `gauge` |
