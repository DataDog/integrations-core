---
type: goal
name: phase1_metadata_goal
---
Verify **metric coverage** of `metadata.csv` for **${integration}**. Check only
coverage — not description quality, units, or orientation.

## Reference (locates the source catalog)

${inspect_endpoint_memory}

## What must be true

`<integration_name>` is `${integration}` lowercased with each run of non-alphanumeric
characters replaced by `_`; the metric prefix is `<integration_name>`. The worker summary
lists the exact file paths; use them.

1. Read every rename mapping: `metrics.yaml` for a single endpoint, or every
   `metrics/<endpoint_name>.yaml` for multiple endpoints. Collect the deduplicated union of
   effective short Datadog names and types.
2. Read `<integration_name>/metadata.csv` and collect the `metric_name` column.
3. Every distinct short value `<v>` from the mapping union must be represented in `metadata.csv` by at
   least one row whose `metric_name` is `<prefix>.<v>` or `<prefix>.<v>.<suffix>`
   (e.g. `.count`, `.sum`, `.bucket`, `.quantile`). No mapped metric may be absent, and a
   metric shared by endpoint files must not create duplicate metadata rows.

Pass (`valid: true`) only if every mapping value is represented. Otherwise fail and
list the specific short names that have no corresponding row in `metadata.csv`.
