# OpenMetrics V2

-----

OpenMetricsV2 is an updated implementation for collecting metrics via the CNCF-backed OpenMetrics format. 


## Issues with OpenMetricsV1
- Metric types
- Counter change
- Abnormal class signature
- Performance
- Configurations

## New Changes
- Py3 only
- Native metric types
- Configurations
- Others: Subclasses, additional endpoints, custom metric types, transformers

## Interface

All functionality is exposed by the `OpenMetricsBaseCheckV2`, `LabelAggregator`, 
`OpenMetricsScraper`, `MetricTransformer` class.

::: datadog_checks.base.checks.openmetrics.v2.base.OpenMetricsBaseCheckV2
    rendering:
      heading_level: 4
    selection:
      members:
        - __init__
        - check
        - configure_scrapers

::: datadog_checks.base.checks.openmetrics.v2.labels.LabelAggregator
    rendering:
      heading_level: 4
    selection:
      members:
        - __init__
        - __call__
        - collect
        - populate

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


::: datadog_checks.base.checks.openmetrics.v2.transform.MetricTransformer
    rendering:
      heading_level: 4
    selection:
      members:
        - __init__
        - get
        - compile_transformer
        - skip_native_metric


## Options
Talk about config options for this