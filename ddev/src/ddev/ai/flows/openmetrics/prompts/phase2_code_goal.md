---
type: goal
name: phase2_code_goal
---
Verify that the **check** and the **configuration spec** for **${integration}** are
correct and idiomatic for an OpenMetrics V2 integration. Read the files yourself to
confirm; do not trust the summary alone.

The integration directory is `${integration}` in snake_case. The intended **metric
prefix** is stated in the worker summary.

## Product requirements (mandatory)

The team defined product requirements for this integration; they were given to the check author
and are **mandatory**. Read them below and verify the built integration honors **every one** of
them — for example, a metric the requirements say to drop must be absent from **both**
every affected endpoint mapping and `metadata.csv`; a forced config option must be present in `check.py`/`spec.yaml`.

If the block below states there are no requirements (e.g. "nothing to require"), there is
nothing extra to enforce here — do not invent requirements.

Fail (`valid: false`) if any stated requirement is unmet, naming the specific requirement and the
file/line where it is violated.

Requirements, verbatim:

```
${prd}
```

## `check.py`

Read `<integration_name>/datadog_checks/<integration_name>/check.py`. It must:

1. Subclass `OpenMetricsBaseCheckV2`.
2. Set `__NAMESPACE__` to exactly the metric prefix (no trailing dot).
3. Set `DEFAULT_METRIC_LIMIT = 0`.
4. Override `get_config_with_defaults()`, call `super()` so file mappings are retained, and force
   `enable_health_service_check: false` in the effective config so the deprecated OpenMetrics
   health service check cannot be enabled or emitted.
5. Load the mapping files correctly for their count:
   - one endpoint uses conventional `metrics.yaml` with no `METRICS_MAP` or hand-built loader;
   - multiple endpoints declare every `metrics/<endpoint_name>.yaml` exactly once in an
     ordered `METRICS_MAP` tuple of unconditional `MetricsMapping(Path(...))` entries.
     There must be no manual YAML parsing or dictionary concatenation. If
     `get_config_with_defaults()` is overridden, it must call `super()` so the mappings load.
6. Carry **no** leftover scaffold boilerplate (placeholder `__init__`/`check` bodies,
   commented database/HTTP examples, unused imports).

A minimal check is the expected and correct outcome for one endpoint. For multiple endpoints,
the declarative `METRICS_MAP` tuple and imports are required and are not unnecessary complexity. Anything beyond that
(`get_default_config`, a custom scraper, a custom `check`) is acceptable **only** if the
summary gives a concrete endpoint-specific reason; flag unjustified additions.

**Label hygiene.** Inspect every endpoint's labels (all catalog `label_keys`). If any label is a
reserved Datadog tag key (`host`, `device`, `source`, `service`, `env`, `version`, `team`), is
an overly generic name (`name`, `type`, `id`, `state`, `status`, `role`, `component`), or is
genuinely unbounded / non-grouping (`request_id`, `trace_id`, a unique numeric `id`), the check
must handle it via `rename_labels` / `exclude_labels` in `get_default_config`. Fail if such a
label is left unhandled — a reserved key passed through unrenamed is always a fail. Labels that
need none of this are fine; do not demand cleanup that isn't warranted.

## `spec.yaml`

Read `assets/configuration/spec.yaml`. It must:

1. Be metrics-only — **no `logs` block**.
2. Build `init_config` from the `init_config/openmetrics` template and `instances` from
   the `instances/openmetrics` template, rather than hand-listing options those
   templates already provide.
3. Override the `openmetrics_endpoint` example to a sensible endpoint for this
   technology.
4. For **every** option the spec adds beyond the templates: it sets `fleet_configurable: true`,
   and it declares a `default:` under `value:` whenever the option has a sensible default. Fail
   if an added option is missing `fleet_configurable: true` or omits a default it should have.

Then confirm the generated files exist and are consistent with the spec:
`<integration_name>/datadog_checks/<integration_name>/config_models/` and
`<integration_name>/datadog_checks/<integration_name>/data/conf.yaml.example` — they
must be present and reflect an OpenMetrics instance (not a leftover default-template
config).

Also confirm the effective mapping composition: the number of `MetricsMapping` declarations
equals the number of endpoint mapping files and the union of their emitted names matches the
single `metadata.csv` without missing or duplicated metadata rows.

Pass (`valid: true`) only if the check and spec meet every point above, every product
requirement is honored, the generated config is present and consistent, and all endpoint
mappings are linked. Otherwise fail with the specific file, line, and problem.
