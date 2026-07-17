---
type: prompt
name: phase1_metadata
---
# Task — Write `metadata.csv`

You are working on the Datadog integration for **${integration}**. In this task you
produce the integration's **single** `metadata.csv`: the catalog of every metric emitted
across all inspected endpoints, derived from all rename mappings and all endpoint catalogs.

## Context from the endpoint inspection

${inspect_endpoint_memory}

The summary above lists every endpoint and the path to each **metrics catalog** JSONL.

## Inputs to read

1. **Every catalog JSONL** listed above — for each endpoint family's Prometheus `type`,
   `help`, labels, and provenance.
2. **Every rename mapping present in the integration package.** There is `metrics.yaml` for
   one endpoint, or one `metrics/<endpoint_name>.yaml` per endpoint when several were inspected.

Use the integration name and metric prefix derived by your standing identity rule. The
scaffolded directory already exists; list it if you need to confirm the path.

## One metadata file for the union

There is always exactly one `<integration_name>/metadata.csv`, regardless of endpoint count.
Read all mapping files, build their combined effective mapping, and write the metadata in one
pass. Deduplicate shared families and shared emitted Datadog metric names: a metric exposed by
two endpoints still gets one metadata row (or one type-specific row set), not two. If two files
map the same raw family inconsistently, stop and repair the mappings before writing metadata.

## How metrics expand into rows

`metadata.csv` has **one row per emitted metric**. A single mapped family expands into
one or more rows depending on its type. With mapping value `<short>` and prefix
`<prefix>`, the base name is `<prefix>.<short>`, and each row appends a per-type suffix:

| effective `type`   | rows emitted (`metric_name` → `metric_type`)                                          |
|--------------------|---------------------------------------------------------------------------------------|
| `gauge`            | `<prefix>.<short>` → `gauge`                                                          |
| `info`             | `<prefix>.<short>` → `gauge`                                                          |
| `counter`          | `<prefix>.<short>.count` → `count`                                                    |
| `native_dynamic`   | `<prefix>.<short>` → `gauge` ; `<prefix>.<short>.count` → `count` (it is exposed as both) |
| `histogram`        | `<prefix>.<short>.bucket` → `count` ; `<prefix>.<short>.count` → `count` ; `<prefix>.<short>.sum` → `count` |
| `summary`          | `<prefix>.<short>.count` → `count` ; `<prefix>.<short>.sum` → `count` ; `<prefix>.<short>.quantile` → `gauge` |

**Which type drives the rows.** Use the **explicit `type:`** from the relevant mapping YAML
entry when it has the mapping form (`<key>: {name: ..., type: ...}`) — the rename task sets
one for the gauge+counter (`native_dynamic`) case and for families the parser reported as
`unknown`. Only when an entry is a plain string value do you fall back to the family's
catalog `type`. A family that has **no entry in its endpoint mapping** (e.g. an `unknown`-typed
family the rename task deliberately omitted because it could not be confidently typed)
produces **no rows here**. `metadata.csv` must represent exactly the deduplicated union of
all endpoint mappings, no more and no less.

## File format

Write `<integration_name>/metadata.csv`. The **first line is exactly** this header:

```
metric_name,metric_type,interval,unit_name,per_unit_name,description,orientation,integration,short_name,curated_metric,sample_tags
```

Then one row per emitted metric. Column rules:

- **`metric_name`** — as expanded in the table above.
- **`metric_type`** — `gauge`, `count`, or `rate` per the table. These are the only
  valid values; for this rename pipeline you will only use `gauge` and `count`.
- **`interval`** — empty.
- **`unit_name`** — a valid Datadog unit, or empty. Use a unit only when one clearly
  applies; never invent a non-standard word. Common units: `byte`, `second`,
  `millisecond`, `request`, `connection`, `operation`, `query`, `error`, `thread`,
  `packet`, `percent`, `item`, `message`. **Where to place it across a family's rows:**
  - **gauge** → the unit of the measured quantity (e.g. `byte`, `second`).
  - **counter (`.count`)** → the unit of what is *accumulated*, when meaningful (a
    byte counter → `byte`; a CPU-seconds counter → `second`); otherwise empty.
  - **histogram / summary** → put the measured unit **only** on the `.sum` and
    `.quantile` rows (a `_seconds` family → `.sum` is `second`; a `_bytes` family →
    `.sum` is `byte`). Leave the `.bucket` and `.count` rows **empty** — they count
    observations, not the quantity.
- **`per_unit_name`** — empty (only used for genuine "X per Y" rates, which this
  pipeline does not produce).
- **`description`** — a clear, complete sentence describing what the metric measures,
  **ending with a period**. Base it on the catalog `help` (you may reuse it almost
  verbatim); if `help` is empty, write one from the name. For a metric the rename task added
  from an official source (it has no catalog row — the rename summary lists these), base the
  description on that **official** source; use `web_search` and `web_fetch` under the source
  authority rules in your standing instructions. For the several rows of one
  histogram/summary family, give each row a description that fits what that row
  actually measures (the bucket distribution, the observation count, the running sum,
  the quantile). Never leave it empty and never use a generic placeholder like
  "metric" or the metric name alone.
- **`orientation`** — almost always `0`. Do **not** infer a direction from words like
  "failed", "error", "timeout", or "duration". Use `1` (higher is better) or `-1`
  (lower is better) only when the metric has an unambiguous good direction; when in
  doubt, use `0`.
- **`integration`** — `<prefix>` (the snake_case integration name).
- **`short_name`**, **`curated_metric`**, **`sample_tags`** — empty.

CSV correctness:

- Quote any field containing a comma, double-quote, or newline per RFC-4180 (wrap the
  field in double quotes and double any internal double-quote). Descriptions frequently
  need this.
- No pipe (`|`) characters and no non-ASCII characters anywhere.
- **Sort all data rows ascending by `metric_name`.**

## Self-check coverage

Before finishing, confirm: every distinct effective value across every endpoint mapping is
represented by its expected row(s) here (correct prefix and per-type suffixes); shared metrics
are not duplicated; no mapped metric is missing; the header is exact; and the CSV is valid and
sorted.

In your final summary, identify every officially sourced mapping family that is absent from
**all** inspected catalogs. For each one, list the raw family, effective type, source, and every
expanded `metric_name` row you added to `metadata.csv`. Those exact Datadog names form the narrow
fixture-exclusion list used by the test phase; do not include a documented family that appears in
any captured catalog. If there are none, say so explicitly. An independent reviewer verifies
this coverage after you finish, so make it correct now.
