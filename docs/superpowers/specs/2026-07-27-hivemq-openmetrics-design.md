# HiveMQ: Add OpenMetrics collection as an alternative to JMX

- Status: Draft
- Related: [FRAGENT-3671](https://datadoghq.atlassian.net/browse/FRAGENT-3671)
- Author: Ian Bucad (with Claude)
- Date: 2026-07-27

## Summary

Add an OpenMetrics/Prometheus collection path to the HiveMQ integration, selectable
per-instance via `is_jmx: false`, as an alternative to the existing JMXFetch-only
collection. The two collection methods are mutually exclusive per instance, share no
runtime code, and the existing JMX path's behavior and tests are unaffected.

## Motivation

JMX requires exposing a remote JMX port and, in containerized/Kubernetes environments,
extra sidecar or attach machinery that OpenMetrics-style HTTP scraping avoids. HiveMQ
ships a free, official extension
([hivemq/hivemq-prometheus-extension](https://github.com/hivemq/hivemq-prometheus-extension))
that exposes the same underlying metric registry over HTTP, making this a
container/Kubernetes-friendliness improvement rather than a JMX deprecation — JMX
remains the default and fully supported.

## Background: why this is feasible

HiveMQ's Prometheus extension hands the same Dropwizard `MetricRegistry` that backs
JMX (`Services.metricRegistry()`) to `io.prometheus.client.dropwizard.DropwizardExports`
with the default `MetricFilter.ALL` — no metric is excluded. This was confirmed by
reading the extension's source directly:

```java
// PrometheusExtensionMain.java
final var prometheusServer = new PrometheusServer(configuration, Services.metricRegistry());
```
```java
// PrometheusServer.java
.collector(new DropwizardExports(metricRegistry))
```

`DropwizardExports` (from `prometheus/client_java`, `simpleclient_dropwizard`) converts
each Dropwizard metric type as follows — this is the exact, verified mapping, not an
assumption:

| Dropwizard type | JMX attribute(s) collected today | Prometheus/OpenMetrics wire type | Notes |
|---|---|---|---|
| `Gauge` | `Value` | `gauge` | 1:1, same value |
| `Counter` | `Count` | `gauge` (not `counter`!) | Same numeric value, but wire type metadata says `gauge` |
| `Histogram` | `50th/75th/95th/98th/99th/999thPercentile`, `Count`, `Max`, `Mean`, `Min`, `StdDev`, `SnapshotSize` (12 attrs) | `summary`: quantiles `{0.5,0.75,0.95,0.98,0.99,0.999}` + `_count` (7 of 12) | `Max`, `Mean`, `Min`, `StdDev`, `SnapshotSize` are **not exposed** — `DropwizardExports.fromHistogram` doesn't emit them |
| `Meter`/`Timer` | not collected today | counter `_total` / summary | No regression; out of scope |

Name mapping is deterministic: `Collector.sanitizeMetricName()` replaces every
non-alphanumeric character (`.`, `-`) with `_`, e.g.
`com.hivemq.cache.payload-persistence.hit-rate` → `com_hivemq_cache_payload_persistence_hit_rate`.

### Documented gap

The 9 histogram-backed metric groups currently collected via JMX lose their `.max`,
`.mean`, `.min`, `.std_dev`, `.snapshot_size` sub-metrics under OpenMetrics (45 of the
current ~246 `metadata.csv` rows). This is a permanent limitation of the Dropwizard →
Prometheus exporter, not a config gap on our side:

- `extension.managed_executor.scheduled.percent_of_period`
- `messages.incoming.publish.bytes`
- `messages.incoming.total.bytes`
- `messages.outgoing.publish.bytes`
- `messages.outgoing.total.bytes`
- `messages.retained.mean`
- `networking.connections.mean`
- `payload_persistence.cleanup_executor.scheduled.percent_of_period`
- `persistence_scheduled_executor.scheduled.percent_of_period`

All ~64 gauges and ~46 counters carry over unchanged (only wire-level type metadata
differs for counters, not availability). This gap must be stated explicitly in the
`is_jmx` config description and README so it's a known tradeoff, not a silent
regression when a user switches modes.

## Prior art in this repo (and why it doesn't fully apply)

- `amazon_msk` toggles between two `OpenMetricsBaseCheck(V2)` implementations via a
  `use_openmetrics` boolean and a `__new__` override — both its paths are already
  OpenMetrics (scraping a JMX Exporter's Prometheus endpoint), so this doesn't
  demonstrate a real JMXFetch ↔ OpenMetrics switch.
- `sonarqube` and `hazelcast` both combine a real `check.py` with a JMX
  `data/metrics.yaml`, gated by an `is_jmx` instance/init_config flag. This *is* the
  right mechanism (see below) — but their non-JMX path is hand-rolled REST/HTTP, not
  OpenMetrics. Confirmed by reading both check.py files in full: no
  `OpenMetricsBaseCheck` import in either package.
- A repo-wide cross-reference of every integration importing
  `OpenMetricsBaseCheck`/`OpenMetricsBaseCheckV2` (61 hits) against every integration
  with `jmx_metrics:` in its `data/metrics.yaml` (15 hits) found **zero overlap**.
  No integration in `integrations-core` currently combines JMXFetch with OpenMetrics
  for the same data source, and there is no existing shared-metrics-definition or
  codegen mechanism to reuse. This design establishes that pattern for the first time,
  scoped locally to HiveMQ rather than as a new repo-wide convention.

## Architecture

### Toggle: `is_jmx`, corrected for HiveMQ's current spec

The Agent's collector reads `is_jmx` natively (outside this repo, in Go) to decide
whether to run JMXFetch against `data/metrics.yaml` (never invoking Python) or to load
`check.py` instead. HiveMQ's current `assets/configuration/spec.yaml` already imports
both `init_config/jmx` and `instances/jmx`, but as currently configured this doesn't
provide a working per-instance switch:

- `init_config/jmx`'s `is_jmx` is `required: true` — this forces every instance in the
  file into JMX mode unconditionally today.
- `instances/jmx`'s `is_jmx` is `hidden: true` and, per its own description, is
  *"ignored if `is_jmx` is set to true at the init_config level"* — so today it's dead
  configuration.

The fix (matching `hazelcast`'s pattern):

```yaml
- template: init_config
  options:
  - template: init_config/jmx
    overrides:
      is_jmx.required: false
      is_jmx.value.example: false
- template: instances
  options:
  - template: instances/jmx
    overrides:
      port.value.example: 9010
      is_jmx.hidden: false
      is_jmx.value.default: true   # preserve current behavior for configs with no flag set
      is_jmx.value.example: true
  - template: instances/openmetrics
    overrides:
      openmetrics_endpoint.value.example: http://%%host%%:9399/metrics
```

`is_jmx.value.default: true` at the instance level is required, not cosmetic: existing
customer configs never had to set `is_jmx` (it was forced), so on upgrade its absence
must still resolve to "JMX, exactly as before."

### `check.py`

```python
from datadog_checks.base import OpenMetricsBaseCheckV2
from datadog_checks.hivemq.config_models import ConfigMixin
from datadog_checks.hivemq.metrics import METRIC_MAP


class HivemqCheck(OpenMetricsBaseCheckV2, ConfigMixin):
    __NAMESPACE__ = 'hivemq'

    def get_default_config(self):
        return {'metrics': [METRIC_MAP]}
```

When `is_jmx: true`, the Agent never instantiates this class at all — the JMX path is
unaffected by anything in this file.

### `metrics.py`

Following the established convention used by `envoy`/`boundary` (both
`OpenMetricsBaseCheckV2` checks keep their metric map in a dedicated `metrics.py`,
imported into `check.py` and injected via `get_default_config()`):

```python
METRIC_MAP = {
    # Gauges: plain rename, wire type gauge -> gauge
    'com_hivemq_system_system_cpu_load': 'system.system_cpu.load',
    ...
    # Counters: wire type is gauge (DropwizardExports quirk); force counter semantics
    # to match JMX's monotonic_count
    'com_hivemq_messages_incoming_publish_count': {
        'name': 'messages.incoming.publish.count',
        'type': 'counter',
    },
    ...
}
```

The map is generated once from the same Dropwizard metric names already itemized in
`data/metrics.yaml`'s `bean_regex` lists — it is a rename table, not a hand-guessed
list, and is scoped locally to this integration (no repo-wide shared-metrics
convention is introduced).

Histogram/summary metrics need a custom transformer (registered via
`OpenMetricsBaseCheckV2`'s transformer mechanism) to split each summary's
quantile-tagged samples back into the discrete `hivemq.foo.50th_percentile`,
`.75th_percentile`, ..., `.count` metric names already in `metadata.csv`, instead of
accepting the native `hivemq.foo.quantile{quantile:0.5}` tag-based shape. This keeps
existing monitors/dashboards built on the current metric names working under either
collection method, for the subset of stats that both methods actually expose.

### Collision safety

A unit test loads `metadata.csv` and the generated `METRIC_MAP`, asserting:

1. Every `METRIC_MAP` target name already exists in `metadata.csv` (no accidentally
   invented names), and
2. No target name is reused across two `METRIC_MAP` entries with different semantics
   (e.g., a histogram's derived `.count` must never collide with an unrelated
   counter's `.count`).

This is mechanical validation, not review-only, addressing the requirement that no
metric name overlap slip through between the two collection paths.

### Config (`assets/configuration/spec.yaml`)

Beyond the `is_jmx` fix above, add the standard `instances/openmetrics` template
as-is. It already has the right defaults for a custom (non-generic) OpenMetrics check:

- `metrics` is `hidden: true` — it's the generic-`openmetrics`-integration-only field;
  ours is set programmatically via `get_default_config()`, not user-facing.
- `extra_metrics` is visible by default and takes precedence over our built-in map on
  conflict — the escape hatch for anything the built-in map misses or that HiveMQ adds
  in a future version.
- `exclude_metrics`, `rename_labels`, `exclude_labels`/`include_labels` are present and
  visible too.

No overrides are needed for these beyond `openmetrics_endpoint`'s example value.

`config_models/*.py` are regenerated via `ddev -x validate config -s hivemq` and
`ddev -x validate models -s hivemq` per this repo's `AGENTS.md` — they are never
hand-edited.

## Testing

- Existing `tests/test_e2e.py` (pure JMX, `is_jmx: true` implicit) stays unchanged and
  must keep passing — confirmed as a working baseline: `ddev env start --dev hivemq
  py3.13-4.3` + `ddev env test --dev hivemq py3.13-4.3` passes against a real
  `hivemq/hivemq4:4.3.2` container today.
- `tests/docker/docker-compose.yaml` gets the `hivemq-prometheus-extension` installed
  into the HiveMQ container (or a second compose profile), exposing `:9399/metrics`.
- New e2e/integration fixtures cover `is_jmx: false`, asserting the check submits the
  expected renamed metrics and that the documented gap metrics are absent (not
  silently missing due to a bug).
- The `METRIC_MAP` collision-safety unit test described above.

## Out of scope

- Meter/Timer metric collection (not collected via JMX today either).
- Any change to the default (`is_jmx: true`) collection behavior or its metric names.
- A repo-wide JMX↔OpenMetrics shared-metrics-definition convention — this design is
  scoped to HiveMQ only, since no other integration needs it today.

## Open questions for implementation

- Exact custom-transformer implementation for the histogram quantile-splitting
  behavior (mechanism confirmed available in `OpenMetricsBaseCheckV2`; exact code
  shape to be worked out during planning).
- Whether the HiveMQ Prometheus extension needs to be vendored into the e2e Docker
  image or fetched at container-start time.
