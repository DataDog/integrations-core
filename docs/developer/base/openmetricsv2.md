# OpenMetrics V2

-----

OpenMetricsV2 is an updated implementation for collecting metrics via the CNCF-backed OpenMetrics format. This new version is the default version for all new OpenMetric-checks, and it is compatible with Python 3 only.
There were flaws with the original implementation of the OpenMetrics check, including performance issues, abnormal class signature, and inability to define multiple endpoints.

## Improvements over OpenMetricsV1
### Native Metric Type Support
Originally, OpenMetrics only supported the gauge metric type, so all Prometheus metric types would default to gauge. The other Prometheus types were eventually correctly sent as monotonic counts via config options.
OpenMetricsV2 improves this by natively handling OpenMetrics' different metric types (gauge, counter, histogram, etc.).

#### Gauge

Gauge metric samples will continue to be submitted as gauges.

Code equivalent:

```python
self.gauge(metric.name, ...)
```

#### Counter

The `_total` suffix for samples will now be submitted as monotonic counts with a `.count` suffix.

Code equivalent:

```python
if sample.name.endswith('_total'):
    self.monotonic_count(f'{metric.name}.count', ...)
```

#### Histogram

The `_sum` and `_count` suffixes for samples will now be submitted as monotonic counts.

Code equivalent:

```python
if sample.name.endswith('_sum'):
    self.monotonic_count(f'{metric.name}.sum', ...)
elif sample.name.endswith('_count'):
    self.monotonic_count(f'{metric.name}.count', ...)
```

The `_bucket` suffix for samples will now be submitted as monotonic counts with a `.bucket` suffix.

Code equivalent:

```python
if sample.name.endswith('_bucket'):
    self.monotonic_count(f'{metric.name}.bucket', ...)
```

No longer being aggregated under the `.count` suffix eliminates the need to submit a
[dummy tag](https://github.com/DataDog/integrations-core/pull/3777) for the actual `.count` metric.
This aligns with the alternative solution that was proposed
[here](https://github.com/DataDog/architecture/blob/f5813a5b6451a4dbaa1846925a83a977890aaed1/rfcs/openmetrics/histograms-support.md#recommended-solution).

#### Summary

The `_sum` and `_count` suffixes for samples will now be submitted as monotonic counts.

Code equivalent:

```python
if sample.name.endswith('_sum'):
    self.monotonic_count(f'{metric.name}.sum', ...)
elif sample.name.endswith('_count'):
    self.monotonic_count(f'{metric.name}.count', ...)
```

Quantiles will continue to be submitted as gauges with a `.quantile` suffix.

Code equivalent:

```python
if sample.name == metric.name:
    self.gauge(f'{metric.name}.quantile', ...)
```

### Allow Additional Endpoints
OpenMetricsV2 now supports metric collection for multiple endpoints during runtime. This can be done using `scraper_configs`:

```python
class FooCheck(OpenMetricsBaseCheck):
    def __init__(self, name, init_config, instances):
        super(FooCheck, self).__init__(name, init_config, instances)

        self.check_initializations.appendleft(self._parse_config)

    def _parse_config(self):
        extra_config = {'...': ...}
        self.scraper_configs.append(extra_config)
    ...
```
If endpoints need to be determined each check run, `refresh_scrapers()` can be overridden, and this method is always called before each check run:
```python
class FooCheck(OpenMetricsBaseCheck):
    def refresh_scrapers(self):
        self.scraper_configs = [{...}, {...}]

        # This must be called if `self.scraper_configs` has been modified
        self.configure_scrapers()
    ...
```

### Configuration Changes
#### Wildcards
Pattern matching functionality is now exposed as regular expressions rather than glob patterns.


#### Updated metric definition
OpenMetricsV2 now supports three ways to define what metrics to collect:

1. Simple match
```yaml
metrics:
- foo
```
2. Name re-map
```yaml
metrics:
- foo
- bar_baz: bar.baz
```
3. Type override
```yaml
metrics:
- foo
- bar_baz: bar.baz
- baz_foo:
    type: gauge
    # Optional
    name: baz.foo
```

### Support for Custom Metric Types

#### Counter gauge

This submits metrics as both a `monotonic_count` suffixed by `.count` and a `gauge` suffixed by `.total`.

Example:

```yaml
metrics:
- kube_pod_container_status_restarts:
    type: counter_gauge
```

#### Metadata

This allows for the submission of instance metadata like the product version. The required modifier
`label` indicates which label contains the desired information.

Example:

```yaml
metrics:
- kubernetes_build_info:
    type: metadata
    label: gitVersion
    name: version
```

For more information, see: https://datadoghq.dev/integrations-core/base/metadata/

#### Service check

This submits metrics as service checks.

Example:

```yaml
metrics:
- cluster_state:
    type: service_check
    status_map:
      0: OK
      1: ERROR
```

#### Temporal percent

This calculates values as a percentage of time since the last check run.

Valid values are:

- `second`
- `millisecond`
- `microsecond`
- `nanosecond`

You may also define the unit as an integer number of parts compared to seconds e.g. `millisecond` is
equivalent to `1000`.

Example:

```yaml
metrics:
- process_cpu_seconds:
    type: temporal_percent
    scale: second
```

#### Time elapsed

This sends the number of seconds elapsed from a time in the past as a `gauge`.

Example:

```yaml
metrics:
- last_backup_time:
    type: time_elapsed
```

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



## Options
For complete documentation on every option, see the associated templates for the 
[instance](https://github.com/DataDog/integrations-core/blob/master/datadog_checks_dev/datadog_checks/dev/tooling/templates/configuration/instances/openmetrics.yaml) 
and [init_config](https://github.com/DataDog/integrations-core/blob/master/datadog_checks_dev/datadog_checks/dev/tooling/templates/configuration/init_config/openmetrics.yaml)
 sections. 