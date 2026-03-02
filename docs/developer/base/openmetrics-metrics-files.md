# Metrics Files

-----

Instead of hardcoding metric name mappings in Python or requiring per-instance user configuration, integrations can ship mappings as YAML files alongside the check module. The base class discovers and loads these files automatically and merges them into the scraper configuration before each scrape.

For the user-level `metrics` configuration option, the
[generic OpenMetrics check documentation](https://docs.datadoghq.com/integrations/guide/prometheus-host-collection/)
covers the supported formats. The generic check exposes a default configuration that does not apply to all
OpenMetrics-based integrations; each integration surfaces its own set of options. See the individual
integration's documentation for the full reference (for example, the
[KrakenD integration](https://docs.datadoghq.com/integrations/krakend/)).

## Metrics File Format

A metrics file is a YAML document containing a flat mapping of Prometheus metric names to Datadog metric names. The same formats supported by the `metrics` instance option are valid here.

**Simple rename:**

```yaml
go_goroutines: go.goroutines
go_threads: go.threads
```

**Rename with type override:**

```yaml
some_counter:
  name: my.counter
  type: counter
```

**Regex rename:**

```yaml
"(?P<name>.+)_total$": \g<name>
```

All keys in a single file are merged into the `metrics` list of the scraper configuration.

## Convention-Based Discovery

When `METRICS_MAP` is not set on the check class, the base class searches for a metrics file next to the check module automatically. The lookup order is:

1. `metrics.yaml`
2. `metrics.yml`

The first match is loaded; if both exist, `.yaml` takes precedence. No code is required. Drop the file in the right place and the base class handles the rest.

## Explicit Declaration with `METRICS_MAP`

For integrations that ship multiple files or need to load files conditionally, declare `METRICS_MAP` as a class variable. The presence of `METRICS_MAP` (even if empty) suppresses convention-based discovery entirely.

```python
from pathlib import Path

from datadog_checks.base import OpenMetricsBaseCheckV2
from datadog_checks.base.checks.openmetrics.v2.metrics_mapping import ConfigOptionTruthy, MetricsMapping


class MyCheck(OpenMetricsBaseCheckV2):
    METRICS_MAP = [
        MetricsMapping(Path("metrics/default.yaml")),
        MetricsMapping(Path("metrics/go.yaml"), predicate=ConfigOptionTruthy("go_metrics")),
        MetricsMapping(Path("metrics/process.yaml"), predicate=ConfigOptionTruthy("process_metrics")),
    ]
```

Paths in `METRICS_MAP` are relative to the package directory (the directory containing the check module). Files listed without a predicate are always loaded.

## Conditional Loading with Predicates

Any `MetricsMapping` can carry a predicate. When the predicate returns `False` for the current instance configuration, the file is skipped. A single check class can cover deployments that expose different metric sets based on their configuration.

```python
MetricsMapping(Path("metrics/go.yaml"), predicate=ConfigOptionTruthy("go_metrics"))
```

The file `metrics/go.yaml` is loaded only when the instance option `go_metrics` is truthy. When the option is absent, it defaults to `True`, so metrics are included unless explicitly disabled.

Predicates are evaluated once per check instance, against the configuration at the time of the first scrape. For the full list of built-in predicates, see the [API Reference](#api-reference) below.

### Custom Predicates

Any class with a `should_load(self, config: Mapping) -> bool` method satisfies the `MetricsPredicate` protocol and can be used directly. No inheritance or registration is required:

```python
class MyPredicate:
    def should_load(self, config: Mapping) -> bool:
        return config.get("mode") in ("advanced", "full")


class MyCheck(OpenMetricsBaseCheckV2):
    METRICS_MAP = [
        MetricsMapping(Path("metrics/default.yaml")),
        MetricsMapping(Path("metrics/extra.yaml"), predicate=MyPredicate()),
    ]
```

## Customizing Defaults with `get_default_config`

`get_default_config()` is the hook for providing instance-level scraper defaults. File-based metrics are merged on top of whatever this method returns, so you can combine file metrics with other defaults such as `rename_labels`:

```python
class MyCheck(OpenMetricsBaseCheckV2):
    def get_default_config(self) -> dict:
        return {
            "rename_labels": {"exported_job": "job"},
        }
```

The returned dict may be mutated by the framework before it is wrapped in a `ChainMap`. Return a fresh dict on every call. Returning a shared class-level or instance-level object can cause state leakage between check executions.

## API Reference

::: datadog_checks.base.checks.openmetrics.v2.metrics_mapping.MetricsMapping
    options:
      heading_level: 3
      members: false

::: datadog_checks.base.checks.openmetrics.v2.metrics_mapping.MetricsPredicate
    options:
      heading_level: 3
      members: false

::: datadog_checks.base.checks.openmetrics.v2.metrics_mapping.ConfigOptionTruthy
    options:
      heading_level: 3
      members: false

::: datadog_checks.base.checks.openmetrics.v2.metrics_mapping.ConfigOptionEquals
    options:
      heading_level: 3
      members: false

::: datadog_checks.base.checks.openmetrics.v2.metrics_mapping.AllOf
    options:
      heading_level: 3
      members: false

::: datadog_checks.base.checks.openmetrics.v2.metrics_mapping.AnyOf
    options:
      heading_level: 3
      members: false
