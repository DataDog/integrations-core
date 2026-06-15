# 05 — DBM Query Metrics: the Db2 Statement-Metrics Collector

**Audience:** an engineer or AI agent who already understands Datadog DBM "query metrics" for
Postgres (`pg_stat_statements`) or MySQL (`events_statements_summary_by_digest`), but has little
Db2 background. This doc designs the Db2 analog end-to-end so you can implement it without re-deriving
the framework.

**What "query metrics" is, in one sentence:** every collection interval, read a cumulative
per-statement counter table from the database, diff it against the previous read to get
per-interval deltas, obfuscate + sign the statement text, and ship one `dbm-metrics` event whose
rows the backend turns into the per-query throughput/latency/rows time series you see in the DBM
"Query Metrics" page.

**Where this fits in the plan:**
- [`03-reference-architecture.md`](03-reference-architecture.md) §1.3–§1.5 + §3.2 — the shared
  `DBMAsyncJob` / `StatementMetrics` / payload-contract pieces this collector assembles. Read it
  first if you have not.
- [`06-dbm-query-samples-activity.md`](06-dbm-query-samples-activity.md) — the samples/FQT/plan collector; this doc
  emits the **FQT** event but defers **plan** events to 06 / [`07-dbm-execution-plans.md`](07-dbm-execution-plans.md).
- [`09-implementation-architecture.md`](09-implementation-architecture.md) — the concrete module
  layout, check wiring (`run_job_loop`/`cancel`), and per-job `ibm_db` connection isolation that
  this collector plugs into.
- [`11-testing-and-validation.md`](11-testing-and-validation.md) — how to test the delta engine,
  obfuscation, and payload shape against the live 12.1.4 container.
- [`12-risks-open-questions.md`](12-risks-open-questions.md) — the obfuscator-dialect and
  `ibm_db` CLOB/cursor open questions surfaced here.

> **Authoritative source for everything Db2-specific below:**
> [`_research/db2-live-pkgcache.md`](_research/db2-live-pkgcache.md) — empirical probe of
> `MON_GET_PKG_CACHE_STMT` on our live Db2 **12.1.4** container (2026-06-15), plus
> [`_research/_raw/02-monget-key-columns.txt`](_research/_raw/02-monget-key-columns.txt) (the column
> oracle). Claims I could not verify against that probe are tagged **(verify)**.

---

## 1. Source of truth: `MON_GET_PKG_CACHE_STMT`

### 1.1 The analogy

| | Postgres | MySQL | **Db2** |
|---|---|---|---|
| Source | `pg_stat_statements` view | `events_statements_summary_by_digest` | `TABLE(MON_GET_PKG_CACHE_STMT(NULL,NULL,NULL,-1))` |
| Stable row id | `(queryid, dbid, userid)` | `(schema_name, digest)` | **`EXECUTABLE_ID`** (`VARCHAR(32) FOR BIT DATA`) |
| Statement text | `query` | `digest_text` | **`STMT_TEXT`** (`CLOB`, ≤ 2 MB) |
| Execution count | `calls` | `count_star` | **`NUM_EXEC_WITH_METRICS`** (not `NUM_EXECUTIONS` — see §1.4) |
| Counter semantics | monotonic, reset on stats reset | monotonic, reset on table truncate | monotonic since db activation, reset on **cache eviction / db reactivation** |

`MON_GET_PKG_CACHE_STMT` returns cumulative-since-database-activation counters for every section
currently in the **package cache** — both dynamic and static SQL. It is the closest Db2 thing to
`pg_stat_statements`. The package cache is finite and entries are **evicted** under memory pressure,
which is the central caveat (see §8.1).

### 1.2 The exact SELECT

Db2 has **327 columns** in 12.1.4 (older fixpacks have fewer). **Do not hard-code the column list by
fixpack** — introspect at runtime (§3.2) and intersect with the desired set, exactly as Postgres does
with `cursor.description` of a `LIMIT 0` probe. The query below is the *full-desired* form; the
implementation builds the column list dynamically and only ever selects `available & desired`.

```sql
SELECT
    -- identity / tag columns (passed through, NOT diffed)
    HEX(EXECUTABLE_ID)        AS executable_id,   -- 64-char uppercase hex; stable diff key (§3.1)
    SECTION_TYPE,                                 -- 'D' dynamic / 'S' static
    MEMBER,
    -- execution indicators (diffed; drive the "executed?" gate)
    NUM_EXEC_WITH_METRICS,                        -- average divisor + execution indicator (§1.4)
    NUM_EXECUTIONS,                               -- carried for reference / fallback only
    -- timing counters (diffed; gate on mon_act_metrics >= BASE, §7)
    TOTAL_CPU_TIME,                               -- *** microseconds ***
    STMT_EXEC_TIME,                               -- milliseconds
    COORD_STMT_EXEC_TIME,                         -- milliseconds
    TOTAL_ACT_TIME,                               -- milliseconds
    TOTAL_ACT_WAIT_TIME,                          -- milliseconds
    LOCK_WAIT_TIME,                               -- milliseconds
    TOTAL_SECTION_SORT_TIME,                      -- milliseconds
    -- row counters (diffed)
    ROWS_READ, ROWS_RETURNED, ROWS_MODIFIED,
    ROWS_INSERTED, ROWS_UPDATED, ROWS_DELETED,
    -- I/O & sort counters (diffed)
    POOL_DATA_L_READS, POOL_DATA_P_READS,
    POOL_INDEX_L_READS, POOL_INDEX_P_READS,
    DIRECT_READS, DIRECT_WRITES,
    TOTAL_SORTS, SORT_OVERFLOWS,
    LOCK_WAITS, LOCK_TIMEOUTS, DEADLOCKS,
    -- statement text (CLOB; bounded fetch, see §2)
    SUBSTR(STMT_TEXT, 1, 16384) AS stmt_text,
    LENGTH(STMT_TEXT)           AS stmt_text_length   -- for truncation detection (§2)
FROM TABLE(MON_GET_PKG_CACHE_STMT(NULL, NULL, NULL, -1)) AS t
WHERE NUM_EXEC_WITH_METRICS > 0
```

Argument meaning for `MON_GET_PKG_CACHE_STMT(section_type, executable_id, member, ...)`:
- arg1 `section_type`: `NULL` = dynamic **and** static; `'D'` = dynamic only.
- arg2 `executable_id`: `NULL` = all cached sections; or pass one `x'...'` to fetch a single section
  cheaply (the two-step pattern, §2 / §8.2).
- arg3 `member`: `NULL` = current member.
- arg4 `-1` = current member (`-2` = aggregate all members). `-1` is correct for the single-member
  local container; multi-member/pureScale deployments should consider `-2` **(verify)**.

> **Column-introspection probe** (mirror of Postgres `LIMIT 0`):
> `SELECT * FROM TABLE(MON_GET_PKG_CACHE_STMT(NULL,NULL,NULL,-1)) FETCH FIRST 0 ROWS ONLY` — read
> `cursor.description`, cache the available names, and select `sorted(available & desired)`.

### 1.3 Columns → metrics mapping

These are the candidate metric (delta) columns. The backend maps each known column to a Datadog
metric; the integration ships **raw interval deltas**, not rates (rate-per-second is derived
server-side). Coordinate the exact row-key names with the DBM backend team
([`12-risks-open-questions.md`](12-risks-open-questions.md)).

| `MON_GET_PKG_CACHE_STMT` column | Unit | Role | Postgres analog |
|---|---|---|---|
| `NUM_EXEC_WITH_METRICS` | count | **execution indicator** + average divisor | `calls` |
| `NUM_EXECUTIONS` | count | reference / fallback only | (≈ `calls`) |
| `TOTAL_CPU_TIME` | **microseconds** | CPU time | (no direct pg analog) |
| `STMT_EXEC_TIME` | milliseconds | statement exec (elapsed) time | `total_exec_time` |
| `COORD_STMT_EXEC_TIME` | milliseconds | coordinator exec time | — |
| `TOTAL_ACT_TIME` / `TOTAL_ACT_WAIT_TIME` | milliseconds | activity time / wait time | — |
| `LOCK_WAIT_TIME` | milliseconds | lock wait | — |
| `TOTAL_SECTION_SORT_TIME` | milliseconds | sort time | — |
| `ROWS_READ` | count | rows read (scan cost signal) | (≈ `shared_blks_read` family) |
| `ROWS_RETURNED` | count | rows returned | `rows` |
| `ROWS_MODIFIED` / `ROWS_INSERTED` / `ROWS_UPDATED` / `ROWS_DELETED` | count | DML rows | `rows` |
| `POOL_DATA_L_READS` / `POOL_DATA_P_READS` | count | logical / physical data reads | `shared_blks_hit` / `shared_blks_read` |
| `POOL_INDEX_L_READS` / `POOL_INDEX_P_READS` | count | logical / physical index reads | — |
| `DIRECT_READS` / `DIRECT_WRITES` | count | direct (LOB/large) I/O | — |
| `TOTAL_SORTS` / `SORT_OVERFLOWS` | count | sort count / spills | — |
| `LOCK_WAITS` / `LOCK_TIMEOUTS` / `DEADLOCKS` | count | concurrency events | — |

> **Unit hazard (critical):** `TOTAL_CPU_TIME` is in **microseconds**; every `*_TIME` activity
> column (`STMT_EXEC_TIME`, `TOTAL_ACT_TIME`, `LOCK_WAIT_TIME`, …) is in **milliseconds**. This was
> verified live (a statement with `total_cpu_time=3679` us and `stmt_exec_time=4` ms — CPU is a
> subset of elapsed). **Do not** copy MySQL's picosecond math. Decide one canonical wire unit and
> convert `TOTAL_CPU_TIME` µs→ms (or document the µs) before mixing — keep the conversion in one
> place and write a unit test ([`11-testing-and-validation.md`](11-testing-and-validation.md)).

`ROWS_READ` ≫ `ROWS_RETURNED` is the classic inefficiency signal this feature surfaces — the live
probe showed `select * ... where sku='item1'` reading 10 000 rows to return 1 (a full scan with no
usable index on the literal path).

### 1.4 Why `NUM_EXEC_WITH_METRICS`, not `NUM_EXECUTIONS`

`NUM_EXECUTIONS` counts **every** execution of the cached section. `NUM_EXEC_WITH_METRICS` counts
only executions for which Db2 actually accumulated the metric counters (gated by the `mon_*_metrics`
collection levels, §7). Per IBM guidance, **averages must divide by `NUM_EXEC_WITH_METRICS`** and the
**execution indicator must be `NUM_EXEC_WITH_METRICS`** — otherwise you would divide a metric sum
(populated only on metric-collecting executions) by a larger execution count and under-report
per-exec averages, or emit a delta for executions that contributed no metric movement.

On our live container they happened to be equal for the orders statements (e.g. `324 / 324`), but
the implementation must not rely on that. Always:
- use `NUM_EXEC_WITH_METRICS` as `execution_indicators` (§3.3), and
- guard division by zero when computing any per-exec average for display
  ([`11-testing-and-validation.md`](11-testing-and-validation.md) should cover the 0 case).

---

## 2. `STMT_TEXT` handling — CLOB, not normalized, comment-prefixed

`STMT_TEXT` is a **`CLOB`** declared up to **2 MB** (2 097 152 bytes). Observed real lengths on the
live DB: 12–5195 chars. Three properties drive the design:

1. **It is NOT server-normalized.** The package cache stores the statement *as prepared*:
   - parameterized prepares keep `?` markers verbatim (`UPDATE inventory_items SET quantity = ? WHERE sku = ?`),
   - literal-inlined statements keep their literals (`... where sku = 'item1'`), and **each distinct
     literal value becomes its own cache entry with its own `EXECUTABLE_ID`**.

   This is the opposite of MySQL's `digest_text` (already templated). A literal-heavy app explodes
   the cache into one entry per value, so **the agent MUST obfuscate client-side** and re-aggregate
   by `query_signature` (§3) — Db2 will not collapse literals for you.

2. **It carries the Datadog APM SQL-comment prefix.** The orders app prepends
   `/*dddbs='...',dde='...',ddps='...',ddprs='...'*/`. These leading comments differ across otherwise
   identical statements (e.g. `dde='local'` present vs absent), which would split both the raw
   `EXECUTABLE_ID` identity *and* the signature if left in. The obfuscator strips/handles comments,
   so computing the signature over the **obfuscated** text (not the raw text) collapses them
   correctly. (Comments are also extracted into `dd_comments` metadata, §3.4.)

3. **It can be truncated by the bounded fetch.** Db2 does not append a `...` marker like MySQL. Fetch
   a bounded prefix (`SUBSTR(STMT_TEXT, 1, N)`, e.g. 16 KB) and **also select `LENGTH(STMT_TEXT)`**;
   set a truncation flag when `LENGTH > N`. Mirror MySQL's `get_truncation_state` enum
   (`truncated` / `not_truncated`) so the FQT event can carry `query_truncated`
   (the value is consumed by [`06-dbm-query-samples-activity.md`](06-dbm-query-samples-activity.md)).

### Obfuscation + signature

Reuse the base helpers — **do not reimplement**:

```python
from datadog_checks.base.utils.db.utils import obfuscate_sql_with_metadata
from datadog_checks.base.utils.db.sql import compute_sql_signature

def _normalize(self, raw_text):
    # replace_null_character=True: Db2 CLOB/VARCHAR may contain embedded \x00 (mirror SQL Server)
    statement = obfuscate_sql_with_metadata(
        raw_text, self._obfuscate_options, replace_null_character=True
    )
    obfuscated = statement['query']
    return {
        'query': obfuscated,                                  # obfuscated text replaces raw
        'query_signature': compute_sql_signature(obfuscated), # mmh3 64-bit hex; matches APM resource hash
        'dd_tables':   statement['metadata'].get('tables'),
        'dd_commands': statement['metadata'].get('commands'),
        'dd_comments': statement['metadata'].get('comments'),
    }
```

- `compute_sql_signature` is `mmh3.hash64(bytes, signed=False)[0]` as lowercase hex. **It must match
  the APM resource hash** — reuse it verbatim so DBM ↔ APM correlation works. The input is the
  *obfuscated* text, so the `/*dd...*/` comment and any literal/`?` differences are already gone.
- Obfuscator options carry `'dbms': 'db2'` **(verify the Agent `pkg/obfuscate` supports a `db2`
  dialect; if not, fall back to a generic SQL value)** — open question tracked in
  [`12-risks-open-questions.md`](12-risks-open-questions.md). Build them once at construction:

  ```python
  opts = self._config.obfuscator_options.model_dump()
  opts['dbms'] = 'db2'                                  # (verify)
  opts['return_json_metadata'] = self._config.obfuscator_options.collect_metadata
  opts['table_names']          = self._config.obfuscator_options.collect_tables
  self._obfuscate_options = to_native_string(json.dumps(opts))
  ```
- Rows that fail obfuscation are **dropped** (log WARNING when `log_unobfuscated_queries`, else DEBUG)
  — same as Postgres/MySQL.

---

## 3. Delta computation across runs

The cumulative counters become per-interval deltas via the shared base engine
`StatementMetrics.compute_derivative_rows`
(`datadog_checks_base/datadog_checks/base/utils/db/statement_metrics.py:25`). Reuse it — it already
handles row-merging, stats-reset detection, no-change suppression, and the execution-indicator gate.
Verified signature:

```python
compute_derivative_rows(rows, metrics, key, execution_indicators=None) -> List[dict]
```

### 3.1 Row identity = `HEX(EXECUTABLE_ID)`

`EXECUTABLE_ID` is a 32-byte `FOR BIT DATA` value; render it with `HEX()` to a 64-char uppercase hex
string. The live probe **verified it is stable across successive snapshots** of the same cache entry
(two reads moments apart returned the identical `...037276` hex while the counters advanced 0→1 /
0→2675). So it is a safe diff key. Treat the binary as **opaque** — the trailing bytes happen to
encode a timestamp, but do not parse or depend on that.

Key tuple for the **snapshot diff**:

```python
def _row_key(row):
    # stable across runs for a given cache entry; member + db make it unambiguous on
    # multi-member / multi-db monitoring users.
    return (row['executable_id'], row['member'], self._db_name)
```

> **Why not key the diff on `query_signature` directly (as Postgres does)?** Because a re-prepare or
> cache churn creates a **new** `EXECUTABLE_ID` for the *same* text (verified live: the same UPDATE
> appeared under two different ids). Diffing two cumulative counters that belong to different cache
> generations would be wrong. So the diff is keyed on the stable raw identity (`EXECUTABLE_ID`), and
> the **final merge** is keyed on `query_signature` (§3.4) to fold churned ids and literal variants
> back together.

### 3.2 Runtime column introspection (sets `metrics`)

```python
desired_metric_cols = {
    'num_exec_with_metrics', 'num_executions',
    'total_cpu_time', 'stmt_exec_time', 'coord_stmt_exec_time',
    'total_act_time', 'total_act_wait_time', 'lock_wait_time', 'total_section_sort_time',
    'rows_read', 'rows_returned', 'rows_modified',
    'rows_inserted', 'rows_updated', 'rows_deleted',
    'pool_data_l_reads', 'pool_data_p_reads', 'pool_index_l_reads', 'pool_index_p_reads',
    'direct_reads', 'direct_writes', 'total_sorts', 'sort_overflows',
    'lock_waits', 'lock_timeouts', 'deadlocks',
}
available = self._get_available_columns(cursor)         # from FETCH FIRST 0 ROWS probe (§1.2)
metric_columns = sorted(available & desired_metric_cols)
```

### 3.3 Calling the engine (once per run)

```python
rows = self._state.compute_derivative_rows(
    rows,
    metric_columns,
    key=_row_key,
    execution_indicators=['num_exec_with_metrics'],   # NOT num_executions (§1.4)
)
```

What the engine does for you (verified in source):
- **Merge duplicates** sharing the same `_row_key` (sums metric columns).
- For each key, look up the previous snapshot. **First time seen → skip** (becomes the baseline; no
  delta emitted). This is why the very first run produces no metrics.
- **Stats-reset guard:** if *any* metric diff is negative, **drop the whole row** (a negative diff
  means the package-cache entry was evicted then re-cached / the db reactivated → counter reset).
- **No-change guard:** if nothing changed, skip.
- **Execution-indicator guard:** emit only if `num_exec_with_metrics` increased — filters the
  evict-then-reinsert phantom where counts look identical but the entry is actually new.
- Emits `{col: cur - prev}` for metric cols, passes tag/text cols through unchanged.
- **Mutates its cache in place**, so call it **exactly once per run**.

### 3.4 Re-merge by `query_signature`

Because churned `EXECUTABLE_ID`s and literal variants are distinct snapshot rows, fold them after the
diff so the shipped metric is per-logical-query. Mirror MySQL's `_add_associated_rows` / Postgres v2's
`_merge_by_query_signature`: sum the (already-diffed) metric columns of rows sharing
`(query_signature, db_name)`; keep one representative `query` text. The result rows are what go into
`db2_rows`.

> The order is: **obfuscate → diff (keyed on EXECUTABLE_ID) → re-merge (keyed on signature)**. (An
> alternative is to merge raw cumulative rows by signature *before* diffing — but cumulative sums
> across churned ids are not monotonic across runs, so diff-then-merge is the safe order.)

---

## 4. The `dbm-metrics` payload

Per the payload contract ([`code-dbm-payload-contract.md`](_research/code-dbm-payload-contract.md) §3;
[`03-reference-architecture.md`](03-reference-architecture.md) §3.2), one event per collection run.
Submit with `self._check.database_monitoring_query_metrics(json.dumps(payload, default=default_json_event_encoding))`.

```python
payload = {
    'host':                    self._check.reported_hostname,
    'timestamp':               time.time() * 1000,                 # epoch MILLISECONDS
    'min_collection_interval': self._metrics_collection_interval,  # seconds
    'tags':                    self._tags_no_db,                   # dd.internal* AND db: stripped
    'cloud_metadata':          self._check.cloud_metadata,         # {aws,azure,gcp}; keys must exist
    'db2_version':             self._check.dbms_version,           # e.g. "12.1.4"
    'ddagentversion':          datadog_agent.get_version(),
    'service':                 self._config.service,
    'db2_rows':                rows,                               # <-- per-statement delta rows
}
```

Vendor-specific conventions (confirm exact names with the DBM backend —
[`12-risks-open-questions.md`](12-risks-open-questions.md)):
- **Vendor row key = `db2_rows`** (mirrors `postgres_rows` / `mysql_rows`). The backend keys off the
  track + the `<dbms>_rows` field.
- **Version key = `db2_version`**; **`dbms` / `ddsource` source string = `"db2"`** everywhere it
  appears (FQT, activity, metadata).
- `timestamp` is **milliseconds**; `min_collection_interval` is **seconds**.
- `tags` is `_tags_no_db` (strip `dd.internal.*` and `db:` — the backend re-adds `db:` per row).
- `default_json_event_encoding` coerces `Decimal→float` etc. — required because `ibm_db` returns
  `Decimal` for many numeric columns. Reuse it.

Each element of `db2_rows` carries: the metric **diffs** (`num_exec_with_metrics`, `total_cpu_time`,
`stmt_exec_time`, `rows_read`, …), plus `query` (obfuscated text), `query_signature`, `dd_tables`,
`dd_commands`, `dd_comments`. The raw `stmt_text` / `executable_id` need not be shipped in the metric
row (the FQT event carries the text).

**Batch splitting:** recursively bisect `db2_rows` so each serialized payload stays under
`batch_max_content_size` (default 20 MB, matching the Agent forwarder's
`database_monitoring.metrics.batch_max_content_size`); drop a single oversized row with a warning.

**FQT (full query text) event** — emitted from this same job (not the samples job), rate-limited to
N/hour/query by a `TTLCache` keyed on `(query_signature, db_name)`. Shape and `query_truncated`
handling are owned by [`06-dbm-query-samples-activity.md`](06-dbm-query-samples-activity.md) §FQT; the metrics job just
calls `self._check.database_monitoring_query_sample(...)` with `dbm_type:"fqt"`, `ddsource:"db2"`.

---

## 5. Scheduling (`DBMAsyncJob`) + config knobs

### 5.1 The job

`Db2StatementMetrics` subclasses `DBMAsyncJob`
(`datadog_checks_base/datadog_checks/base/utils/db/utils.py:289`), exactly like
`SqlserverStatementMetrics` / `PostgresStatementMetrics`. It holds its **own dedicated `ibm_db`
connection** (never share the main check's cursor across the background thread — see
[`03-reference-architecture.md`](03-reference-architecture.md) §5.3 and §8.3 below).

```python
class Db2StatementMetrics(DBMAsyncJob):
    def __init__(self, check, config, connection_args):
        self._metrics_collection_interval = float(config.query_metrics.collection_interval)  # default 10
        super().__init__(
            check,
            run_sync=config.query_metrics.run_sync,
            enabled=config.query_metrics.enabled,            # requires top-level dbm: true
            expected_db_exceptions=(ibm_db.Error,),          # (verify exact ibm_db exception class)
            min_collection_interval=config.min_collection_interval,
            dbms="db2",                                       # drives dd.db2.async_job.* metric names
            rate_limit=1 / self._metrics_collection_interval, # executions per second
            job_name="query-metrics",
            shutdown_callback=self._close_db_conn,
        )
        self._state = StatementMetrics()                      # holds the _previous snapshot cache
        self._full_statement_text_cache = TTLCache(
            maxsize=config.query_metrics.full_statement_text_cache_max_size,                 # 10000
            ttl=60 * 60 / config.query_metrics.full_statement_text_samples_per_hour_per_query,  # 1/hr
        )

    def run_job(self):
        # strip dd.internal* into self.tags; strip db: into self._tags_no_db
        self._collect_statement_metrics()
```

- The check creates the job in `__init__`, calls `self._statement_metrics.run_job_loop(dbm_tags)`
  each check run **only when `dbm` is enabled**, and `.cancel()` on shutdown — wiring is in
  [`09-implementation-architecture.md`](09-implementation-architecture.md).
- `rate_limit = 1/collection_interval` paces the background loop via `ConstantRateLimiter`. The loop
  self-terminates if the main check stops calling `run_job_loop` for `min_collection_interval * 2`s.
- `expected_db_exceptions` are logged as warnings (counted `dd.db2.async_job.error`), not crashes.

### 5.2 Config (`query_metrics` block) — mirror Postgres/MySQL defaults

| Option | Default | Notes |
|---|---|---|
| `query_metrics.enabled` | `true` | requires top-level `dbm: true` |
| `query_metrics.collection_interval` | `10` (s) | drives `rate_limit`; keep identical across instances |
| `query_metrics.run_sync` | `false` | run inline (tests / low intervals) |
| `query_metrics.full_statement_text_cache_max_size` | `10000` | FQT dedup cache size |
| `query_metrics.full_statement_text_samples_per_hour_per_query` | `1` | FQT TTL = `3600 / value` |
| `query_metrics.batch_max_content_size` | `20_000_000` | real value from `datadog.yaml` |
| (Db2-specific, optional) `query_metrics.max_statements` | e.g. `10000` **(verify)** | cap rows / `FETCH FIRST N` for large caches |
| `obfuscator_options.{collect_tables,collect_metadata,collect_commands,...}` | — | §2 |
| top-level `dbm` | `false` | master switch; also sets `metadata.dbm=true` in the `database_instance` event |
| top-level `min_collection_interval` | `15` | inactivity-stop = `2 ×` |

There is intentionally **no `incremental_query_metrics` / v2 path** for Db2 in this design — start
with the v1 `StatementMetrics` engine (Postgres v2 exists only to avoid pulling `pg_stat_statements`
text every run; the Db2 two-step text fetch, §8.2, achieves the same without a second engine).

---

## 6. Required privileges

The monitoring user needs `EXECUTE` on the table function (the live probe observed the grant
`GRANT EXECUTE ON FUNCTION SYSPROC.MON_GET_PKG_CACHE_STMT TO USER datadog` sitting in the cache):

```sql
GRANT EXECUTE ON FUNCTION SYSPROC.MON_GET_PKG_CACHE_STMT TO USER datadog;
```

Notes:
- `db2inst1` could call it with no extra grant (instance owner); a dedicated `datadog` monitoring
  user needs the explicit grant above.
- `MON_GET_PKG_CACHE_STMT_DETAILS` (the XML-detail sibling) was **not callable** as `db2inst1` in the
  probe (`SQL0440N No authorized routine ... compatible arguments`) and is **not required** — the
  flat `MON_GET_PKG_CACHE_STMT` columns cover exec count / CPU / exec time / rows. Treat
  `_DETAILS` grants/signature as a separate, optional investigation **(verify)**.
- Timing columns additionally require the `mon_*_metrics` collection levels (§7) — a *configuration*
  prerequisite, not a privilege.
- Cross-reference the consolidated privilege matrix in
  [`03-reference-architecture.md`](03-reference-architecture.md) / the prereqs section once it lands;
  this doc states only the query-metrics-specific grant.

---

## 7. Timing-column gating (the `track_io_timing` analog)

Postgres drops timing columns unless `track_io_timing=on`. The Db2 analog: the `*_TIME` activity
columns are only populated when **`mon_act_metrics >= BASE`** (and request/object metrics for their
respective columns). The live container had the defaults — `mon_act_metrics=BASE`,
`mon_req_metrics=BASE`, `mon_obj_metrics=EXTENDED` — so timing was populated. But a customer can set
these to `NONE`.

**Introspect the levels at startup and gate timing-derived metrics** (read once, cache):

```sql
SELECT NAME, VALUE FROM SYSIBMADM.DBCFG
WHERE NAME IN ('mon_act_metrics', 'mon_req_metrics', 'mon_obj_metrics');
```

If `mon_act_metrics = NONE`, drop the timing columns (`*_TIME`) from `desired_metric_cols` for that
instance and (optionally) record a `DatabaseConfigurationError`-style warning so the user knows why
timing metrics are absent — mirror MySQL's `record_warning` preflight pattern. Counters that are not
timing-gated (`ROWS_*`, `NUM_EXEC_*`, `POOL_*_READS`, `LOCK_WAITS`, `DEADLOCKS`) remain valid.

---

## 8. Caveats

### 8.1 Package-cache eviction = counter reset

The package cache is finite. Under memory pressure (or on db deactivation/reactivation) entries are
evicted; a re-cached statement starts its counters back at 0 and gets a **new `EXECUTABLE_ID`**. Two
consequences, both already handled by the design:
- The diff sees a **negative** delta for the vanished id's successor → `compute_derivative_rows`
  drops that row wholesale (stats-reset guard, §3.3). No spurious spike is emitted.
- Churn fragments one logical query across several `EXECUTABLE_ID`s → the **signature re-merge**
  (§3.4) folds them. The first interval after a churn under-counts (the new id is a fresh baseline);
  this is the same first-seen behavior Postgres/MySQL have and is acceptable.

Eviction also means **literal-heavy workloads can thrash the cache** (one entry per literal). The
obfuscation+signature merge limits the *metric* fan-out, but the *source* read still scans many cache
rows — hence the optional `max_statements` cap and the two-step text fetch below.

### 8.2 `ibm_db` CLOB / statement-handle / no-cursor considerations

This is the Db2-specific driver risk; track in [`12-risks-open-questions.md`](12-risks-open-questions.md):
- **CLOB materialization.** `STMT_TEXT` is a CLOB. Over `ibm_db`/CLI some configurations return a LOB
  **locator** rather than the materialized string. The `SUBSTR(STMT_TEXT, 1, N)` cast in the SELECT
  (§1.2) returns a bounded `VARCHAR`, sidestepping locator handling and bounding memory — prefer it
  over selecting the bare CLOB. **(verify** the exact `ibm_db` fetch behavior for CLOB columns on the
  target driver version.**)**
- **Two-step fetch for large caches (cost control).** Pulling `STMT_TEXT` for every cached section
  every interval is expensive on a big/churning cache. Optionally fetch identity + counters in the
  broad call, diff, then fetch text only for the changed top-N ids via
  `TABLE(MON_GET_PKG_CACHE_STMT(NULL, x'<EXECUTABLE_ID>', NULL, -1))`. This is the Db2 equivalent of
  Postgres v2's `pg_stat_statements(false)` + miss-path text fetch, achieved without a second delta
  engine.
- **No-cursor / statement-handle reuse.** `ibm_db` exposes statement handles
  (`ibm_db.exec_immediate` / `ibm_db.prepare` + `ibm_db.execute`) rather than DB-API cursors. The
  background job must use its **own connection/handle** (never the main check's), and should
  `ibm_db.free_result` / free the handle between runs to avoid leaking handles across the long-lived
  async-job loop. Wrap fetches so a dropped idle connection is reconnected (the job runs every ~10s,
  so idle-drop is less likely than for the 600s metadata job, but still guard it). **(verify** the
  precise handle-lifecycle API against the `ibm_db` version pinned in the integration.**)**
- **`db2inst1` no-password / `dd-auth` gotcha.** Local-dev connects as `db2inst1` with no password;
  production uses a dedicated `datadog` user with the §6 grant. (Recorded in project memory:
  dd-auth/set-a ops gotcha for local Db2.)

### 8.3 Connection isolation

Each DBM async job owns a dedicated `ibm_db` connection so the background thread never races the main
check's synchronous metric collection. Closed via `shutdown_callback=self._close_db_conn`. This is the
single most important Db2 adaptation called out in
[`03-reference-architecture.md`](03-reference-architecture.md) §5.3.

---

## 9. End-to-end pipeline (the `run_job` body)

```python
def _collect_statement_metrics(self):
    rows = self._load_pkg_cache_stmt_rows()          # §1.2 SELECT (introspected cols), one snapshot
    rows = [{**r, **self._normalize(r['stmt_text'])} # §2: obfuscate + signature + dd_* metadata
            for r in rows if self._normalize(r['stmt_text'])]   # drop unobfuscatable
    rows = self._state.compute_derivative_rows(      # §3.3: diff, keyed on EXECUTABLE_ID
        rows, self._metric_columns,
        key=_row_key, execution_indicators=['num_exec_with_metrics'])
    rows = self._merge_by_signature(rows)            # §3.4: fold churned ids + literal variants

    for event in self._rows_to_fqt_events(rows):     # §4: FQT, rate-limited (TTLCache)
        self._check.database_monitoring_query_sample(json.dumps(event, default=default_json_event_encoding))

    payload = self._build_payload(rows)              # §4: db2_rows wrapper
    for chunk in self._chunk(payload):               # batch-size split
        self._check.database_monitoring_query_metrics(
            json.dumps(chunk, default=default_json_event_encoding))
```

This is the Db2 mirror of Postgres `collect_per_statement_metrics` / MySQL
`_collect_per_statement_metrics`, with the four Db2-specific substitutions: the
`MON_GET_PKG_CACHE_STMT` source, `EXECUTABLE_ID` diff key, `num_exec_with_metrics` indicator, and the
`db2_*` / `ddsource:"db2"` payload naming.

---

## 10. Implementation checklist

- [ ] `Db2StatementMetrics(DBMAsyncJob)`, `dbms="db2"`, `job_name="query-metrics"`, own `ibm_db` conn (§5, §8.3).
- [ ] Runtime column introspection (`FETCH FIRST 0 ROWS`), `metrics = sorted(available & desired)` (§1.2, §3.2).
- [ ] `execution_indicators=['num_exec_with_metrics']` — **not** `num_executions` (§1.4).
- [ ] Convert `TOTAL_CPU_TIME` µs→ms (or document); never mix µs/ms (§1.3) + unit test.
- [ ] Obfuscate with `replace_null_character=True`, `dbms:'db2'` (verify); strip `/*dd...*/`; `compute_sql_signature` (§2).
- [ ] Diff key `(HEX(EXECUTABLE_ID), member, db)`; re-merge by `query_signature` (§3.1, §3.4).
- [ ] Payload: `db2_rows`, `db2_version`, ms timestamp, `_tags_no_db`, batch-split (§4).
- [ ] FQT event with `query_truncated` from `LENGTH(STMT_TEXT)` (§2; shape in 06).
- [ ] Gate timing columns on `mon_act_metrics >= BASE` (§7).
- [ ] Grant `EXECUTE ON FUNCTION SYSPROC.MON_GET_PKG_CACHE_STMT` (§6).
- [ ] Two-step text fetch + CLOB-as-VARCHAR + handle lifecycle for large/churning caches (§8.2).

---

## 11. Citations

- **Authoritative Db2 source behavior:** [`_research/db2-live-pkgcache.md`](_research/db2-live-pkgcache.md)
  (§1 TL;DR, §2 probe SQL, §3 real output, §4 stable-id verification, §5 normalization, §6 columns,
  §7 truncation, §8 units, §9 collection guidance) and
  [`_research/_raw/02-monget-key-columns.txt`](_research/_raw/02-monget-key-columns.txt).
- **Framework / payload contract:**
  [`_research/code-postgres-dbm-statements.md`](_research/code-postgres-dbm-statements.md),
  [`_research/code-mysql-dbm.md`](_research/code-mysql-dbm.md),
  [`_research/code-base-framework.md`](_research/code-base-framework.md),
  [`_research/code-dbm-payload-contract.md`](_research/code-dbm-payload-contract.md).
- **Base helpers (reuse, do not reimplement):**
  `datadog_checks_base/datadog_checks/base/utils/db/statement_metrics.py:25` (`compute_derivative_rows`),
  `datadog_checks_base/datadog_checks/base/utils/db/sql.py:18` (`compute_sql_signature`),
  `datadog_checks_base/datadog_checks/base/utils/db/utils.py:249` (`obfuscate_sql_with_metadata`),
  `:289` (`DBMAsyncJob`), `:237` (`default_json_event_encoding`),
  `datadog_checks_base/datadog_checks/base/checks/base.py:772` (DBM submitters).
- **Sibling docs:** [`03-reference-architecture.md`](03-reference-architecture.md),
  [`06-dbm-query-samples-activity.md`](06-dbm-query-samples-activity.md),
  [`07-dbm-execution-plans.md`](07-dbm-execution-plans.md),
  [`09-implementation-architecture.md`](09-implementation-architecture.md),
  [`11-testing-and-validation.md`](11-testing-and-validation.md),
  [`12-risks-open-questions.md`](12-risks-open-questions.md).
</content>
</invoke>
