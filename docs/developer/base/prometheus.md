# Prometheus

-----

[Prometheus](https://prometheus.io) is an open-source monitoring system for timeseries metric data. Many Datadog 
integrations collect metrics based on Prometheus exported data sets.

Prometheus-based integrations use the OpenMetrics exposition format to collect metrics.

## Interface

All functionality is exposed by the `OpenMetricsBaseCheck` and `OpenMetricsScraperMixin` classes.

::: datadog_checks.base.checks.openmetrics.OpenMetricsBaseCheck
    rendering:
      heading_level: 4

::: datadog_checks.base.checks.openmetrics.mixins.OpenMetricsScraperMixin
    rendering:
      heading_level: 4
    selection:
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
[instances][config-spec-template-instances-openmetrics] and [init_config][config-spec-template-init-config-openmetrics] sections.

All [HTTP options](http.md#options) are also supported.


::: datadog_checks.base.checks.openmetrics.base_check.StandardFields
    rendering:
      show_root_heading: false
      show_root_toc_entry: false

## Prometheus to Datadog metric types

The Openmetrics Base Check supports various configurations for submitting Prometheus metrics to Datadog.
We currently support Prometheus `gauge`, `counter`, `histogram`, and `summary` metric types.

### Gauge
A gauge metric represents a single numerical value that can arbitrarily go up or down.

Prometheus gauge metrics are submitted as Datadog gauge metrics

### Counter

A [Prometheus counter](https://prometheus.io/docs/concepts/metric_types/#counter) is cumulative metric that represents 
a single monotonically increasing counter whose value can only increase or be reset to zero on restart.

Config Option|Value|Datadog Metric Submitted
-------------|-----|------------------------
`send_monotonic_counter`|`true` (default)| [`monotonic_count`](https://github.com/DataDog/integrations-core/blob/master/datadog_checks_base/datadog_checks/base/checks/openmetrics/mixins.py#L667-L668)
&nbsp;|`false`|[`gauge`](https://github.com/DataDog/integrations-core/blob/master/datadog_checks_base/datadog_checks/base/checks/openmetrics/mixins.py#L671-L672)

### Histogram

A [Prometheus histogram](https://prometheus.io/docs/concepts/metric_types/#histogram) samples observations and counts 
them in configurable buckets along with a sum of all observed values.

Histogram metrics ending in:

- `_sum` represent the total sum of all observed values. Generally [sums](https://prometheus.io/docs/practices/histograms/#count-and-sum-of-observations)
 are like counters but it's also possible for a negative observation which would not behave like a typical always increasing counter.
- `_count` represent the count of events that have been observed.
- `_bucket` represent the cumulative counters for the observation buckets. Note that buckets are only submitted if `send_histogram_buckets` is enabled.


Subtype|Config Option|Value|Datadog Metric Submitted
-------|-------------|-----|------------------------
&nbsp;|`send_distribution_buckets`|`true`|The entire histogram can be submitted as a single [distribution metric][datadog-distribution-metrics]. If the option is enabled, none of the subtype metrics will be submitted.
`_sum`|`send_distribution_sums_as_monotonic`|`false` (default)|[`gauge`](https://github.com/DataDog/integrations-core/blob/master/datadog_checks_base/datadog_checks/base/checks/openmetrics/mixins.py#L826-L835)
&nbsp;| &nbsp;|`true`|`monotonic_gauge`
`_count`|`send_distribution_counts_as_monotonic`|`false` (default)|[`gauge`](https://github.com/DataDog/integrations-core/blob/master/datadog_checks_base/datadog_checks/base/checks/openmetrics/mixins.py#L753-L763)
&nbsp;|&nbsp;|`true`|`monotonic_count`
`_bucket`|`non_cumulative_buckets`|`false` (default)|`gauge`
&nbsp;|&nbsp;|`true`|`monotonic_count` under `.count` metric name if `send_distribution_counts_as_monotonic` is enabled. Otherwise, `gauge`.


### Summary
Prometheus [summary metrics](https://prometheus.io/docs/concepts/metric_types/#summary) are similar to histograms but allow configurable quantiles.

Summary metrics ending in:

- `_sum` represent the total sum of all observed values. Generally [sums](https://prometheus.io/docs/practices/histograms/#count-and-sum-of-observations)
 are like counters but it's also possible for a negative observation which would not behave like a typical always increasing counter.
- `_count` represent the count of events that have been observed.
-  metrics with labels like `{quantile="<φ>"}` represent the streaming quantiles of observed events.

Subtype|Config Option|Value|Datadog Metric Submitted
-------|-------------|-----|------------------------
`_sum`|`send_distribution_sums_as_monotonic`|`false` (default)|[`gauge`](https://github.com/DataDog/integrations-core/blob/master/datadog_checks_base/datadog_checks/base/checks/openmetrics/mixins.py#L826-L835)
&nbsp;| &nbsp;|`true`|`monotonic_gauge`
`_count`|`send_distribution_counts_as_monotonic`|`false` (default)|[`gauge`](https://github.com/DataDog/integrations-core/blob/master/datadog_checks_base/datadog_checks/base/checks/openmetrics/mixins.py#L753-L763)
&nbsp;|&nbsp;|`true`|`monotonic_count`
`_quantile`|&nbsp;|&nbsp;|`gauge`