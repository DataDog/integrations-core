# Cloud Spanner DBM — Product Requirements & Design

## Goal

Add DBM (Database Monitoring) support for Google Cloud Spanner, starting with query metrics.

The existing `gcp.spanner.*` metrics come from the Datadog GCP integration in **dogweb** via the
Cloud Monitoring API — a server-side poll with no access to per-query internals. DBM requires an
agent-side check that connects directly to Spanner and queries `SPANNER_SYS.*` system tables.

---

## Architecture Decisions

### Python in integrations-core (not Go in datadog-agent)

Newer DBM checks (Oracle) are Go corechecks in `datadog-agent/pkg/collector/corechecks/`.
Postgres/MySQL/SQLServer DBM are older Python checks in `integrations-core`. We chose Python for
the prototype for iteration speed. Can be ported to Go later.

### New check, not extending the GCP integration

`gcp.spanner.*` metrics come from dogweb (server-side). DBM needs an agent-side direct Spanner
connection — different runtime, different codebase. The two coexist, the same pattern as
Cloud SQL + postgres check: the GCP integration handles Cloud Monitoring surface metrics, this
check handles DBM. The check carries `cloud_metadata.gcp` (`project_id`, `instance_id`) on every
DBM event so the UI can correlate the two data sources.

### One database per check instance (for now)

Config has `project_id`, `instance_id`, `database` (singular). Multi-database fan-out can be
added later. Matches the simplest Spanner access pattern.

### No emulator for integration tests

The Spanner emulator does **not** support `SPANNER_SYS.*` tables — those only exist on real
Spanner instances. Unit tests mock the client fully. Integration tests require a real GCP Spanner
instance. The emulator is only useful for connectivity/schema testing.

---

## Data Sources

All `SPANNER_SYS` tables are per-database; queried by connecting to each database individually.
Each category has `_TOP_MINUTE`, `_TOP_10MINUTE`, and `_TOP_HOUR` variants.

| Table | Granularity | Status | GCP coverage gap |
|---|---|---|---|
| `QUERY_STATS_TOP_MINUTE` | 1-min window, top 100 by CPU | ✅ implemented | `gcp.spanner.query_stat.total.*` are aggregate-only; no per-query breakdown |
| `TXN_STATS_TOP_MINUTE` | 1-min window, top 100 by CPU | Not yet implemented | No GCP equivalent — abort rates and retry storms are invisible without this |
| `LOCK_STATS_TOP_MINUTE` | 1-min window, top 100 by lock wait | Not yet implemented | `gcp.spanner.lock_stat.total.lock_wait_time` is aggregate; no row-range hotspot |
| `READ_STATS_TOP_MINUTE` | 1-min window, top 100 by CPU | Not yet implemented | `gcp.spanner.read_stat.total.*` are aggregate; no per-read-shape breakdown |

Execution plans come from the Spanner API `ANALYZE` mode (set `query_mode=PLAN` on an
`ExecuteSql` RPC) — there is no SQL-level `EXPLAIN` statement.

### Transaction stats (`TXN_STATS_TOP_*`)

Rows are grouped by transaction tag or fingerprint of operations performed. Key columns:

| Column | Notes |
|---|---|
| `TRANSACTION_TAG` | Tag applied by the application (`SET TRANSACTION_TAG = 'name'`) |
| `FPRINT` | Hash of the tag (or operation set if untagged) |
| `ATTEMPT_COUNT` | Total attempts including aborts before commit |
| `COMMIT_ATTEMPT_COUNT` | Actual commit RPCs issued |
| `COMMIT_ABORT_COUNT` | Aborted commit attempts (contention, deadlock) |
| `COMMIT_RETRY_COUNT` | Retry attempts — high ratio relative to attempts indicates a retry storm |
| `COMMIT_FAILED_PRECONDITION_COUNT` | Constraint violations (UNIQUE, row not found, etc.) |
| `AVG_PARTICIPANTS` | Average Paxos shard count in commit — 1 = single-shard (cheap); >1 = cross-shard 2PC |
| `AVG_TOTAL_LATENCY_SECONDS` | Time from first operation to commit/abort |
| `AVG_COMMIT_LATENCY_SECONDS` | Pure commit RPC time (for multi-region overhead analysis) |
| `AVG_BYTES` | Average bytes written per transaction |
| `SERIALIZABLE_PESSIMISTIC_TXN_COUNT` | Count of pessimistic/serializable transactions |
| `SERIALIZABLE_OPTIMISTIC_TXN_COUNT` | Count of optimistic/serializable transactions |
| `REPEATABLE_READ_OPTIMISTIC_TXN_COUNT` | Count of optimistic/repeatable-read transactions |

`AVG_PARTICIPANTS` and the abort/retry counts have no postgres analog and are the primary signals
for diagnosing expensive or contention-heavy Spanner transactions.

### Lock stats (`LOCK_STATS_TOP_*`)

Rows are grouped by the row range where lock conflicts occurred. Only populated for pessimistic
(read-write) transactions; optimistic transactions have no lock stats. Key columns:

| Column | Notes |
|---|---|
| `ROW_RANGE_START_KEY` | The row key(s) at the start of the conflicted range |
| `LOCK_WAIT_SECONDS` | Cumulative lock wait time for this row range in the interval |
| `SAMPLE_LOCK_REQUESTS` | Array of up to 20 samples, each with `lock_mode`, `column` (`table.col`), and `transaction_tag` of the blocker/waiter |

`ROW_RANGE_START_KEY` is the critical field — it pinpoints which rows/tables are hotspots,
something the GCP aggregate metric cannot provide.

### Read stats (`READ_STATS_TOP_*`)

Rows are grouped by the set of columns read (fingerprinted). Key columns:

| Column | Notes |
|---|---|
| `READ_COLUMNS` | Array of columns read, in alphabetical order (`table.column`) |
| `READ_TYPE` | `READ` or `PARTITIONED_READ` |
| `REQUEST_TAG` | Application-provided tag (same mechanism as query stats) |
| `FPRINT` | Hash of request tag or read columns |
| `EXECUTION_COUNT` | Number of read executions |
| `AVG_ROWS`, `AVG_BYTES` | Data volume per read |
| `AVG_CPU_SECONDS` | Server-side CPU (excludes prefetch) |
| `AVG_LOCKING_DELAY_SECONDS` | Time spent waiting for locks during reads (pessimistic txns) |
| `AVG_CLIENT_WAIT_SECONDS` | Time waiting for the client to consume results (backpressure) |
| `AVG_LEADER_REFRESH_DELAY_SECONDS` | Paxos leader confirmation overhead |
| `AVG_DISK_IO_COST` | HDD disk load cost — useful for tiered storage monitoring |

`AVG_LOCKING_DELAY_SECONDS` on reads cross-correlates with `LOCK_STATS` data to understand
whether read traffic is being stalled by write contention.

---

## Distributed Architecture Impact on Metrics & Tagging

Spanner-specific differences from postgres DBM that shape the design:

**No `host` tag.** Spanner is serverless; there are no machines to tag. The resource identifier
is `project_id:instance_id`. `reported_hostname` is set to `"{project_id}:{instance_id}"`.

**`QUERY_TYPE` is a first-class dimension.** Rows in `QUERY_STATS_TOP_MINUTE` carry either
`GLOBAL` (routed to a single split) or `PARTITIONED_QUERY` (fanned out across all splits for
full-table scans / partitioned DML). High CPU on a `PARTITIONED_QUERY` is expected; the same
numbers on a `GLOBAL` query are a red flag. Must be a tag/field, not just a payload detail.

**`REQUEST_TAG` is the only service-attribution mechanism.** Spanner has no user/role concept
analogous to `pg_stat_activity.rolname`. Applications tag queries with
`@{REQUEST_TAG='svc/operation'}` and this surfaces in `SPANNER_SYS`. Without tags, only the
query text fingerprint is available for attribution.

**`AVG_PARTICIPANTS` in `TXN_STATS` is the distributed-cost signal.** It records the average
number of Paxos participant shards involved in a transaction's 2PC commit. A value of 1 means
single-shard (no 2PC overhead); higher values indicate cross-shard coordination. Nothing like
this exists in postgres. It is the primary signal for diagnosing expensive transactions.

**Multi-region latency interpretation.** For instances with multi-region configs (`nam4`, `eur3`,
etc.) the difference between `AVG_COMMIT_LATENCY_SECONDS` and `AVG_TOTAL_LATENCY_SECONDS` reveals
cross-region Paxos overhead. The `instance_config` tag (regional vs multi-regional) is needed to
make latency values interpretable.

### Tagging scheme

```
project_id:my-project
instance_id:my-instance
database:my-db
instance_config:us-central1     # or nam4, eur3, nam-eur-asia1, etc.

# per-row on query metrics:
query_type:GLOBAL | PARTITIONED_QUERY
request_tag:svc/operation       # if set by the application

# no equivalent for: host, user/role, wait_event (no session model)
```

---

## Query Metrics Payload

Sent via `check.database_monitoring_query_metrics(json_string)`.
Appears as `"dbm-metrics"` event platform events in tests.

**Top-level fields:**
```json
{
  "host": "project:instance",
  "database_instance": "project:instance",
  "spanner_version": "spanner",
  "cloud_metadata": {"gcp": {"project_id": "...", "instance_id": "..."}},
  "tags": ["env:prod"],
  "ddagentversion": "...",
  "service": "...",
  "timestamp": 1234567890000,
  "min_collection_interval": 10.0,
  "spanner_rows": [...]
}
```

`spanner_version: "spanner"` is the sentinel field the `dbm-metrics-processor` uses to identify
the payload as Spanner (mirrors `postgres_version`, `mysql_version`, etc. in other integrations).

**Per-row fields** (from `QUERY_STATS_TOP_MINUTE`):

| Field | Source column | Notes |
|---|---|---|
| `database` | config | database name |
| `query_signature` | computed | `compute_sql_signature(obfuscated_text)` |
| `text` | `TEXT` | obfuscated via `obfuscate_sql_with_metadata` |
| `text_truncated` | `TEXT_TRUNCATED` | bool |
| `text_fingerprint` | `TEXT_FINGERPRINT` | INT64 hash from Spanner |
| `query_type` | `QUERY_TYPE` | `GLOBAL` or `PARTITIONED_QUERY` |
| `request_tag` | `REQUEST_TAG` | empty string if unset |
| `interval_end` | `INTERVAL_END` | ISO 8601 string |
| `execution_count` | `EXECUTION_COUNT` | int |
| `avg_latency_seconds` | `AVG_LATENCY_SECONDS` | float |
| `avg_rows` | `AVG_ROWS` | float |
| `avg_bytes` | `AVG_BYTES` | float |
| `avg_rows_scanned` | `AVG_ROWS_SCANNED` | float |
| `avg_cpu_seconds` | `AVG_CPU_SECONDS` | float |
| `all_failed_execution_count` | `ALL_FAILED_EXECUTION_COUNT` | int |
| `all_failed_avg_latency_seconds` | `ALL_FAILED_AVG_LATENCY_SECONDS` | float |
| `cancelled_or_disconnected_execution_count` | `CANCELLED_OR_DISCONNECTED_EXECUTION_COUNT` | int |
| `timed_out_execution_count` | `TIMED_OUT_EXECUTION_COUNT` | int |

---

## Configuration

```yaml
instances:
  - project_id: my-gcp-project        # required
    instance_id: my-spanner-instance  # required
    database: my-database             # required
    dbm: true
    credentials_path: /path/to/sa.json  # optional; uses ADC if absent
    service: my-service                 # optional
    tags:
      - env:prod
    query_metrics:
      enabled: true
      collection_interval: 10.0
```

Authentication: service account JSON file via `credentials_path`, or Application Default
Credentials (ADC) if omitted. For GCP-hosted agents, ADC is the recommended path.

---

## Current State

**Location:** `integrations-core/cloud_spanner/`

```
cloud_spanner/
  datadog_checks/cloud_spanner/
    check.py          — SpannerCheck(AgentCheck); lazy client init; reported_hostname; cloud_metadata
    config.py         — SpannerConfig, QueryMetricsConfig (plain classes; no generated config_models yet)
    queries.py        — QUERY_STATS_TOP_MINUTE SQL constant + QUERY_STATS_COLUMNS tuple
    query_metrics.py  — SpannerQueryMetrics: fetch → parse → obfuscate → emit
    __about__.py, __init__.py
  tests/
    conftest.py       — aggregator/dd_run_check fixtures; MOCK_QUERY_STATS_ROWS; mock client builder
    test_query_metrics.py — 26 unit tests (all passing)
    pytest.ini
  pyproject.toml, hatch.toml, manifest.json
```

**Run unit tests:**
```bash
PYTHONPATH=cloud_spanner python3 -m pytest cloud_spanner/tests/ -v
# prereqs: pip install mmh3 cachetools lazy_loader
# + pip install -e integrations-core/datadog_checks_base/
```

**26/26 unit tests pass.**

---

## Not Yet Implemented

### Transaction metrics (`TXN_STATS_TOP_MINUTE`)

Highest priority addition. No GCP equivalent exists — abort rates, retry storms, and distributed
commit cost (`AVG_PARTICIPANTS`) are completely invisible without this table. Key signals:

- `COMMIT_RETRY_COUNT / COMMIT_ATTEMPT_COUNT` → retry storm ratio
- `COMMIT_ABORT_COUNT` → contention rate
- `AVG_PARTICIPANTS` → distributed transaction cost (unique to Spanner)
- `COMMIT_FAILED_PRECONDITION_COUNT` → constraint violation rate
- Isolation breakdown (pessimistic vs optimistic vs repeatable-read counts)

Will require a new `transaction_metrics.py` module and a corresponding `txn_rows` field in the
payload, parallel to `spanner_rows` for query metrics.

### Lock contention metrics (`LOCK_STATS_TOP_MINUTE`)

GCP exposes `gcp.spanner.lock_stat.total.lock_wait_time` as an aggregate, but provides no
per-row-range attribution. `LOCK_STATS` surfaces which specific rows/tables are hotspots via
`ROW_RANGE_START_KEY`. Useful for diagnosing pessimistic transaction contention.

Note: the `SAMPLE_LOCK_REQUESTS` column is an array of structs — will require special handling
in `_parse_row` to serialize to JSON (similar to how `LATENCY_DISTRIBUTION` histograms work).

### Read metrics (`READ_STATS_TOP_MINUTE`)

Per-column-set read breakdown. `AVG_LOCKING_DELAY_SECONDS` on reads cross-correlates with lock
stats to understand whether read traffic is being stalled by write contention. `AVG_DISK_IO_COST`
is the primary signal for tiered storage (HDD vs SSD) efficiency.

`READ_COLUMNS` is an array of strings (`table.column`) — serialize as a joined string or JSON
array for the payload.

### Other

- Execution plan collection via Spanner API `ANALYZE` mode (`query_mode=PLAN` on `ExecuteSql` RPC)
- Schema/metadata collection from `INFORMATION_SCHEMA`
- Multi-database fan-out per check instance
- Generated `config_models/` from `spec.yaml` (currently plain Python classes)
- `instance_config` tag (requires Spanner Admin API call; needed to make multi-region latency interpretable)
- GCP autodiscovery listener (no equivalent of the Aurora/RDS listener in the agent yet)
