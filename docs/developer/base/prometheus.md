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
        - parse_metric_family
        - scrape_metrics
        - process
        - process_metric
        - poll
        - submit_openmetric

### Options

## Prometheus to Datadog metric types
