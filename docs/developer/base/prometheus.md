# Prometheus

-----

[Prometheus](https://prometheus.io) is an open-source monitoring system for timeseries metric data. Many Datadog 
integrations collect metrics based on Prometheus exported data sets.

As of [Agent `6.5.0`](https://www.datadoghq.com/blog/monitor-prometheus-metrics/), Prometheus-based integrations use 
the OpenMetric exposition format to monitor metrics.

## Openmetrics Base Check

### Interface

All functionality is exposed by the `OpenMetricsBaseCheck` and `OpenMetricsScraperMixin` classes.

::: datadog_checks.base.checks.openmetrics.OpenMetricsBaseCheck
    rendering:
      heading_level: 4

::: datadog_checks.base.checks.openmetrics.OpenMetricsScraperMixin
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

### Options

Some options can be set globally in `init_config` (with `instances` taking precedence).
For complete documentation of every option, see the associated configuration templates for the
[instances][config-spec-template-instances-openmetrics] and [init_config][config-spec-template-init-config-openmetrics] sections.

Default options from the `HTTP` wrapper and `AgentCheck` are also supported.


::: datadog_checks.base.checks.openmetrics.base_check.StandardFields
    rendering:
      show_root_heading: false
      show_root_toc_entry: false

## Prometheus to Datadog metric types
