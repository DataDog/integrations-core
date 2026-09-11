# ClickHouse integration agent notes

This supplements the repository's root `AGENTS.md` — read that first for general
conventions (naming, testing, changelogs, PRs); it still applies here. This file
adds ClickHouse-specific orientation. Read it before touching `advanced_queries/`
or `scripts/generate_metrics.py`.

## Bulk match queries live in JSON, not Python

Three of the four advanced queries (`SystemEvents`, `SystemMetrics`,
`SystemAsynchronousMetrics`) are *bulk match queries*: one SQL that returns
`(value, metric_name)` rows and dispatches to per-name metric definitions
through a large lookup table (over 1,000 entries for `SystemEvents`). Those
lookup tables ship as compact JSON files under
`datadog_checks/clickhouse/data/system_*.json` and are reassembled into the
`QueryManager` shape at load time.

Before changing anything in this area, read:

- `datadog_checks/clickhouse/advanced_queries/__init__.py`: the loader
  (`load_match_query`, `_expand_match_items`, `warm_cache`, `__getattr__`) and
  the JSON-schema docstring at the top of the file.
- `scripts/generate_metrics.py`: the script that parses ClickHouse's C++
  source files to work out which of the shipped metrics each supported version
  exposes.

The fourth query, `SystemErrors`, is a plain Python literal in the same
`__init__.py`. Its shape (one metric plus tag columns, no per-row lookup)
doesn't fit the bulk-match pattern, so the JSON compression has nothing to
compress for it. Don't move it into JSON; the dual format was deliberately
removed during the JSON migration.

## The JSON files are the source of truth for shipped metrics

The three `data/system_*.json` files define exactly which metrics the
integration ships, and nothing regenerates them. Adding a metric is a
deliberate act: edit the JSON file and add the matching rows to
`metadata.csv` by hand (a `monotonic_gauge` needs both a `.count` and a
`.total` row).

`scripts/generate_metrics.py` only refreshes the *test expectations* in
`tests/advanced_metrics.py`. For every version in `VERSIONS`, it reads
ClickHouse's C++ sources, keeps the metrics that are already shipped, and
writes out the base and optional lists (metrics common to every version, plus
the ones unique to each). Metrics that exist in ClickHouse but are not in the
JSON files are counted and reported at the end of the run, never added. To add
support for a new version, extend the version matrix in `hatch.toml` and run:

```shell
cd clickhouse && VERSIONS=24.8,25.3,25.8,26.3 hatch run metrics:generate
```

`tests/advanced_metrics.py` is generated, so don't hand-edit it. An expected
metric that doesn't come from the system tables (for example one emitted by the
legacy query set) belongs in `EXTRA_OPTIONAL_METRICS` in the script, otherwise
the next run drops it.
