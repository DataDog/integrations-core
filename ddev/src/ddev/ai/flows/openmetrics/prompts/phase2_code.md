---
type: prompt
name: phase2_code
---
# Task — Write the check and the configuration spec

You are building the Datadog integration for **${integration}**. The endpoint metric mapping
file(s) and the single integration-wide `metadata.csv` already exist. In this task you write `check.py` and
`assets/configuration/spec.yaml`, then regenerate the derived config files.

Use `web_search` and `web_fetch` under the standing source-authority policy only when repository
inputs do not establish a config option, product default, or label behavior.

## Product requirements (mandatory)

The team defined product requirements for this integration. They are **mandatory** and take
precedence over the implementation rules below wherever they conflict. Apply every one of them
in this task — and only the changes they call for. Common shapes and how to honor them:

- **Drop a metric** — remove it from every endpoint mapping where it occurs and from
  `metadata.csv` so the union stays in sync.
- **Rename or re-prefix a metric or label** — apply it consistently across all endpoint mappings,
  `metadata.csv`, and any check code.
- **Force a config default or option** (a label rename, an exclude, a namespace, …) — set it in
  `check.py` (via `get_default_config`) and/or `spec.yaml`, whichever is appropriate.

If the block below states there are no requirements (e.g. "nothing to require"), proceed with
the standard build and do **not** invent any.

Requirements, verbatim:

```
${prd}
```

## Mapping and metadata handoff

${rename_metrics_memory}

Use the handoff for the integration's directory name, the **metric prefix**, every endpoint
mapping path, and anything flagged. If you need to confirm a path, list the working tree.

## Endpoint inspection

${inspect_endpoint_memory}

Use this inspection summary for endpoint URLs and label catalogs. When several endpoints are
listed, the first endpoint in inspection order is the representative endpoint for the generated
configuration example.

## Steps

1. **`check.py`** — replace the scaffold placeholder at
   `<integration_name>/datadog_checks/<integration_name>/check.py` with an OpenMetrics V2
   check. Import `OpenMetricsBaseCheckV2` from `datadog_checks.base`, subclass it, set
   `__NAMESPACE__` to the metric prefix from the handoff (exactly, no trailing dot), and set
   `DEFAULT_METRIC_LIMIT = 0`. Override `get_config_with_defaults()`, call `super()` to preserve
   file-based metric mappings and other defaults, and force `enable_health_service_check` to
   `False` in the returned config so the deprecated OpenMetrics health service check cannot be
   enabled or emitted. Remove all placeholder scaffold methods, examples, and unused imports.

   Then wire the mappings according to their count:

   - **One mapping (`metrics.yaml`):** add no metric-loading code; let convention load it.
   - **Multiple mappings (`metrics/<endpoint_name>.yaml`):** import `Path` from `pathlib` and
     `MetricsMapping` from
     `datadog_checks.base.checks.openmetrics.v2.metrics_mapping`. Declare an ordered
     `METRICS_MAP` tuple with one unconditional
     `MetricsMapping(Path("metrics/<endpoint_name>.yaml"))` entry per endpoint file. Do not
     manually read, concatenate, or merge the YAML dictionaries: the base class loads all
     tuple entries and appends their dictionaries to the effective `metrics` list consumed by
     the scraper. Use a predicate only when an actual config option conditionally enables a
     mapping; endpoint files required for every instance are unconditional.

   The required `get_config_with_defaults()` override must call
   `super().get_config_with_defaults(config)` so the file mappings are preserved. Keep all
   other code minimal unless the mapping-and-metadata handoff, the combined metric set, or an
   endpoint's labels justify more. Add `get_default_config()` for declarative scraper options
   such as `rename_labels`, `share_labels`, `raw_metric_prefix`, or `exclude_labels`. Add a
   custom scraper only for per-sample transformations configuration cannot express, and a
   custom `check()` only for a separate probe the base scrape cannot perform.

   **Do not forget label hygiene** — it is the usual reason to add `get_default_config`, and
   it is easy to skip. Re-check the `label_keys` in every inspection catalog and, via
   `rename_labels` / `exclude_labels`: rename reserved Datadog tag keys (`host`, `device`,
   `source`, `service`, `env`, `version`, `team`) so they do not collide; give generic labels
   (`name`, `type`, `id`, `state`, `status`, `role`, `component`) product-specific names; and
   exclude genuinely unbounded or non-grouping labels (`request_id`, `trace_id`, a unique
   numeric `id`). This is situational — many integrations need none of it — but when a label
   the catalog exposes calls for it, applying it is mandatory.

2. **`spec.yaml`** — replace `assets/configuration/spec.yaml` with a metrics-only spec using
   both mandatory shared templates: `init_config/openmetrics` nested under `init_config`, and
   `instances/openmetrics` nested under `instances`. Use this structure:

   ```yaml
   name: <DisplayName>
   files:
   - name: <integration_name>.yaml
     options:
     - template: init_config
       options:
       - template: init_config/openmetrics
     - template: instances
       options:
       - template: instances/openmetrics
         overrides:
           openmetrics_endpoint.value.example: <example endpoint>
   ```

   Set `<DisplayName>` to `${integration}`. Build the endpoint example from the representative
   inspected URL by replacing only its host with `%%host%%` and preserving its scheme, port,
   path, and query string.

   Do not add a `logs` block. Read or grep the shared templates before adding an option so you
   do not redeclare behavior they already supply.

   For **every** option you add to the spec yourself (a requirement-forced option, or one
   this integration needs beyond the templates), two rules are **mandatory**:
   - Set `fleet_configurable: true` on the option.
   - Declare a `default:` under `value:` whenever the option has a sensible default, alongside
     the `example:` (e.g. a boolean that defaults to `true` carries both `example: true` and
     `default: true`).

3. **Regenerate** `config_models/` and `data/conf.yaml.example` by running both configuration
   validators in sync mode. Resolve validation failures in `spec.yaml` and repeat until both
   validators pass.

4. **Format and lint** — run the integration's formatter/lint pass (`ddev test` in
   format-and-fix mode) and address anything it flags in the files you wrote.

## Finish

Summarize the check you wrote (namespace; whether you added anything beyond the minimum and
why), the spec, and the outcome of regeneration and formatting. For each product requirement,
state what you changed and where (e.g. "dropped `krakend.foo` from its endpoint mapping and metadata.csv")
— or note that no requirements were provided. A reviewer will verify your work.
