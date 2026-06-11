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

# Re-run measurements without recreating the schema:
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

## Expected outcome

The limited run (max\_tables=300, max\_columns=50) processes 300 tables × 50 columns =
15 000 column dicts. The unlimited run processes 1000 tables × 1000 columns = 1 000 000
column dicts, all held in memory at once before the single `json.dumps` flush. The
unlimited peak RSS is expected to be several times to an order of magnitude larger.
