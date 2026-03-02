# OpenMetrics

-----

OpenMetrics V2 is the current Prometheus/OpenMetrics scraping framework for Datadog integrations. It is Python 3 only and is the default for all new OpenMetrics-based checks.

The base class handles the full scrape lifecycle: HTTP connection management, metric parsing, label renaming, type overrides, and submission to the Agent. Integration authors subclass `OpenMetricsBaseCheckV2` and configure it through instance options or by overriding a small set of hooks.

For user-level configuration (the `metrics` instance option, label renaming, type overrides), the
[generic OpenMetrics check documentation](https://docs.datadoghq.com/integrations/guide/prometheus-host-collection/)
covers the supported formats. The generic check exposes a default configuration that does not apply to all
OpenMetrics-based integrations; each integration surfaces its own set of options. See the individual
integration's documentation for the full reference (for example, the
[KrakenD integration](https://docs.datadoghq.com/integrations/krakend/)).

For bundling metric name mappings as YAML files alongside the check module, see [Metrics Files](openmetrics-metrics-files.md).

## Interface

::: datadog_checks.base.checks.openmetrics.v2.base.OpenMetricsBaseCheckV2
    options:
      heading_level: 3
      members:
        - __init__
        - check
        - configure_scrapers
        - create_scraper
        - get_default_config

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
