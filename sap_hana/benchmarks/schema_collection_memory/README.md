# Schema Collection Memory Benchmark

Demonstrates the memory impact of the `max_tables` and `max_columns` limits added to
`HanaSchemaCollector`. It stands up a SAP HANA Express container, fills it with a 1000×1000
schema (1000 tables, 1000 columns each), then runs the real `collect_schemas()` code path
twice — once with limits enabled and once effectively unlimited — in isolated subprocesses
and compares peak RSS.

## Prerequisites

- Docker with sufficient memory (≥8 GB recommended for HANA Express).
- A Python environment with the following installed:
  ```
  pip install -e ../../..                  # datadog_checks_base (repo root)
  pip install -e ../..                     # sap_hana integration
  pip install hdbcli==2.21.28
  ```
  The integration's hatch test environment already satisfies this.

## Run

```bash
cd sap_hana/benchmarks/schema_collection_memory

# 1. Start SAP HANA Express (startup takes 5–10 minutes).
PASSWORD=Admin1337 docker compose up -d
docker logs -f saphanabenchmark   # wait for "Startup finished!"

# 2. Populate the database and run both modes.
python benchmark.py

# Re-run measurements without recreating the schema.
python benchmark.py --skip-setup

# 3. Tear down.
docker compose down --volumes
```

Results are written to `results/benchmark_results.txt`.

## Tuning

| Constant | File | Default | Notes |
|---|---|---|---|
| `SAP_HANA_VERSION` | `docker-compose.yaml` env var | `2.00.076.00.20231004.2` | Pin to a known-good image tag. |
| `NUM_TABLES` | `setup_database.py` | 1000 | Lower if setup is too slow. |
| `NUM_COLUMNS` | `setup_database.py` | 1000 | Lower if HANA Express rejects wide tables. |

HANA Express has resource constraints. If `CREATE TABLE` fails with a column-count or
memory error, set `NUM_COLUMNS` to 500 or lower.

## Notes on memory investigation

### `setfetchsize` (no effect on memory)
`cursor.setfetchsize(10_000)` was tried on the hdbcli cursor before `execute()` to reduce
the C-layer result buffer. It had no measurable effect on peak RSS (1042 MiB → 1043 MiB).
The reason: the dominant memory consumer is the Python-side `_queued_rows` list
accumulating all table dicts before the single `json.dumps` flush — not the hdbcli C
layer. The base `SchemaCollector` flushes when `len(_queued_rows) >= payload_chunk_size`
(default 10,000) or on the last database. Since HANA always reports one database and a
1000-table schema is below the 10,000 threshold, everything flushes at once. The
`max_tables` / `max_columns` limits are the effective memory control.

### Column-based flush threshold (1.5x RSS reduction with limits)
The base class `payload_chunk_size` counts tables, which is a poor proxy for memory when
tables are wide. `HanaSchemaCollector` overrides `maybe_flush` to flush after every
`PAYLOAD_COLUMN_CHUNK_SIZE` (50,000) columns instead. For 1000-column tables, this flushes
every 50 tables, keeping `_queued_rows` from growing unboundedly. Result on the 1000×1000
schema (RSS before = without column-flush override; RSS after = with override):

| Mode | RSS before | RSS after | Payloads |
|------|-----------|-----------|---------|
| unlimited (no limits) | 1,038 MiB | 93.7 MiB | 21 |
| limited (300 tables × 50 cols) | 56.4 MiB | 61.5 MiB | 1 |

The limited case is unaffected: 300 × 50 = 15,000 columns never reaches the 50,000
threshold so it still flushes once at the end.

### SQL column limit via `ROW_NUMBER()`
The original query joined `SYS.TABLE_COLUMNS` without a column count cap, so the server
returned all 1000 columns per table regardless of `max_columns`; Python discarded the
excess. Pushing the limit into SQL with a `limited_columns` CTE using `ROW_NUMBER() OVER
(PARTITION BY schema, table ORDER BY position)` means the server only sends the first
`max_columns` columns per table. Result on the 1000×1000 schema (duration before = without
ROW_NUMBER cap; duration after = with cap):

| Mode    | Duration before | Duration after |
|---------|-----------------|----------------|
| limited (max_tables=300, max_columns=50)         | 8.1s | 2.2s |
| unlimited (max_tables=10M, max_columns=10M)      | 48.8s | 50.7s |

Peak RSS was unchanged in both modes — the Python-side column dicts are bounded by
`max_columns` either way, so peak Python heap stays the same. The gain is query
efficiency: 285,000 fewer rows sent from the server (300 tables × 950 discarded
columns) in the limited case.

## Expected outcome

The limited run (max\_tables=300, max\_columns=50) processes 300 tables × 50 columns =
15,000 column dicts. The unlimited run processes 1000 tables × 1000 columns = 1,000,000
column dicts, all held in memory at once before the single `json.dumps` flush. The
unlimited peak RSS is expected to be ~1.5x larger than the limited run.
