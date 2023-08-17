# OpenMetrics

-----

OpenMetrics is used for collecting metrics using the CNCF-backed OpenMetrics format. This version is the default version for all new OpenMetric-checks, and it is compatible with Python 3 only.

## Interface

::: datadog_checks.base.checks.openmetrics.v2.base.OpenMetricsBaseCheckV2
    options:
      heading_level: 3
      members:
        - __init__
        - check
        - configure_scrapers
        - create_scraper

## Scrapers

::: datadog_checks.base.checks.openmetrics.v2.scraper.OpenMetricsScraper
    options:
      heading_level: 3
      members:
        - __init__
        - scrape
        - consume_metrics
        - parse_metrics
        - generate_sample_data
        - stream_connection_lines
        - filter_connection_lines
        - get_connection
        - send_requests
        - set_dynamic_tags
        - submit_health_check

## Transformers
::: datadog_checks.base.checks.openmetrics.v2.transform.Transformers
    options:
      heading_level: 3

## Options

For complete documentation on every option, see the associated templates for the
[instance][config-spec-template-instances-openmetrics] and [init_config][config-spec-template-init-config-openmetrics]
 sections.

## Legacy

This OpenMetrics implementation is the updated version of the original Prometheus/OpenMetrics implementation.
The [docs for the deprecated implementation](../legacy/prometheus.md) are still available as a reference.
