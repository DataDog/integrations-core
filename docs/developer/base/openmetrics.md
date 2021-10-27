# OpenMetrics

-----

OpenMetrics is used for collecting metrics via the CNCF-backed OpenMetrics format. This version is the default version for all new OpenMetric-checks, and it is compatible with Python 3 only.
There were flaws with the original implementation of the Prometheus/OpenMetrics check, including performance issues, abnormal class signature, and inability to define multiple endpoints.

## Interface

All functionality is exposed by the `OpenMetricsBaseCheckV2` class.

::: datadog_checks.base.checks.openmetrics.v2.base.OpenMetricsBaseCheckV2
    rendering:
      heading_level: 4
    selection:
      members:
        - __init__
        - check
        - configure_scrapers

## Labels
All functionality is exposed by the `LabelAggregator` class.
::: datadog_checks.base.checks.openmetrics.v2.labels.LabelAggregator
    rendering:
      heading_level: 4
    selection:
      members:
        - __init__
        - __call__
        - collect
        - populate

## Scrapers
All functionality is exposed by the `OpenMetricsScraper` class.
::: datadog_checks.base.checks.openmetrics.v2.scraper.OpenMetricsScraper
    rendering:
      heading_level: 4
    selection:
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
        - submit_telemetry_number_of_total_metric_samples
        - submit_telemetry_number_of_ignored_metric_samples
        - submit_telemetry_number_of_processed_metric_samples
        - submit_telemetry_number_of_ignored_lines
        - submit_telemetry_endpoint_response_size
        - __getattr__

## Transformers
All functionality is exposed by the `MetricTransformer` class.
::: datadog_checks.base.checks.openmetrics.v2.transform.MetricTransformer
    rendering:
      heading_level: 4
    selection:
      members:
        - __init__
        - get
        - compile_transformer
        - skip_native_metric
        - normalize_metric_config

## Options
For complete documentation on every option, see the associated templates for the 
[instance][config-spec-template-instances-openmetrics] and [init_config][config-spec-template-init-config-openmetrics]
 sections. 

## Legacy
This OpenMetrics implementation is the updated version of the original Prometheus/OpenMetrics implementation. 
The docs for the deprecated implementation can be found [here](../legacy/prometheus.md).