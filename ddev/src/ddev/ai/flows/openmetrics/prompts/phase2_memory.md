---
type: memory_prompt
name: phase2_memory
---
Summarize this phase for the **next phase, which writes the test suite**. The test author
does not see your work directly — this summary is their specification of what to test, so
be precise about **intent**, not just about what the code now contains. The goal is that
the tests validate the *intended* behavior of the check, rather than rubber-stamping
whatever the current implementation happens to do.

Keep it tight and factual. Include:

- The integration name and directory, and the **metric prefix** / `__NAMESPACE__`
  (exactly, no trailing dot).
- Every endpoint mapping file and how `check.py` links it. State whether convention loads the
  single `metrics.yaml` or a `METRICS_MAP` tuple loads multiple endpoint YAMLs.
- Every endpoint URL and copied fixture path the tests must mock, and whether the Docker
  environment exposes all endpoints in one service topology.
- Repeat the fixture-exclusion list from the rename/metadata handoff exactly: the expanded
  Datadog names for officially sourced metrics absent from every captured fixture. Do not add
  observed metrics to this list.
- Whether the check is the minimal OpenMetrics check, or whether you added behavior beyond
  the minimum. For **each** addition — a `get_default_config` option (`rename_labels`,
  `share_labels`, `exclude_labels`, `raw_metric_prefix`, …), a custom scraper, or a custom
  `check()` — state:
  - **what** it does (the concrete transformation or probe), and
  - **why** — the endpoint-specific intent behind it: the behavior a *correct* check must
    exhibit, which is what the test author should assert against.
  - a concrete, checkable expectation wherever you can, for example: "the label `version`
    is renamed to `<prefix>_version`, so emitted metrics carry a `<prefix>_version:<value>`
    tag", or "the label `request_id` is dropped, so no emitted metric carries a
    `request_id` tag".
- The spec: confirm it is metrics-only and that `config_models/` and `conf.yaml.example`
  were regenerated from it; note the example `openmetrics_endpoint`.
- **Product requirements applied:** for each team requirement you honored, what you changed and
  where (e.g. "dropped `krakend.foo` from its endpoint mapping and metadata.csv", "renamed label
  `ver`→`version`"), so the test author can pin that the requirement holds. If no requirements
  document was provided, say so.
- The outcome of the format/lint pass, and anything still flagged or worth a human's
  attention.
