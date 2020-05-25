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

### Counter

### Histogram

### Summary