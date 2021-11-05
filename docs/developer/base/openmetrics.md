# OpenMetrics

-----

OpenMetrics is used for collecting metrics using the CNCF-backed OpenMetrics format. This version is the default version for all new OpenMetric-checks, and it is compatible with Python 3 only.

## Interface

::: datadog_checks.base.checks.openmetrics.v2.base.OpenMetricsBaseCheckV2
    rendering:
      heading_level: 3
    selection:
      members:
        - __init__
        - check
        - configure_scrapers

## Scrapers

::: datadog_checks.base.checks.openmetrics.v2.scraper.OpenMetricsScraper
    rendering:
      heading_level: 3
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

## Transformers
::: datadog_checks.base.checks.openmetrics.v2.transform.Transformers
    rendering:
      heading_level: 3

## Options

For complete documentation on every option, see the associated templates for the 
[instance][config-spec-template-instances-openmetrics] and [init_config][config-spec-template-init-config-openmetrics]
 sections. 

## Legacy

This OpenMetrics implementation is the updated version of the original Prometheus/OpenMetrics implementation. 
The [docs for the deprecated implementation](../legacy/prometheus.md) are still available as a reference.

### Config changes between OpenMetrics V1 and V2
There were config option changes between OpenMetrics V1 and V2, so please check if any updated OpenMetrics instances use deprecated options and update accordingly.

Note that the `type_overrides` option is incorporated in the `metrics` option now.

| OpenMetricsV1               | OpenMetricsV2                        |
|-----------------------------|--------------------------------------|
| `ignore_metrics`            | `exclude_metrics`                    |
| `prometheus_metrics_prefix` | `raw_metric_prefix`                  |
| `health_service_check`      | `enable_health_service_check`        |
| `labels_mapper`             | `labels_rename`                      |
| `label_joins`               | `share_labels`                       |
| `send_histograms_buckets`   | `collect_histogram_buckets`          |
| `send_distribution_buckets` | `histogram_buckets_as_distributions` |

