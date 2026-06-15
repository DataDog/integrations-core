# Postgres DBM Query Metrics — Source Code Deep-Dive

Raw research input for implementing **Db2 query metrics** (DBM "query metrics" feature) by mirroring the Postgres collector. This documents EXACTLY how the Postgres integration collects per-statement metrics from `pg_stat_statements`, computes deltas across runs, obfuscates/normalizes, computes `query_signature`, shapes the payload, the config knobs, and how it is scheduled via `DBMAsyncJob`.

All citations are absolute paths into `/home/bits/dd/integrations-core`. Two collector implementations coexist:
- **v1 (legacy)** — `postgres/datadog_checks/postgres/statements.py` (full pgss load every run)
- **v2 (incremental, default-on path when `incremental_query_metrics` is enabled)** — `postgres/datadog_checks/postgres/statements_v2.py` + `delta_detector.py` + `obfuscation_lookup.py`

The shared delta-computation engine lives in `datadog_checks_base/datadog_checks/base/utils/db/statement_metrics.py` (used by v1; v2 has its own `DeltaDetector` with the same algorithm).

---

## 1. Source of truth: `pg_stat_statements`

Postgres query metrics come from the **`pg_stat_statements`** extension view (a cumulative, monotonically-increasing per-(userid, dbid, queryid) counter table). Db2 equivalent: `SYSIBMADM.MON_GET_PKG_CACHE_STMT` table function (or `MON_GET_PKG_CACHE_STMT_DETAILS`), keyed by `EXECUTABLE_ID` — see §10.

### v1 base query — `statements.py:35-62`
```sql
SELECT {cols}
  FROM {pg_stat_statements_view} as pg_stat_statements
  LEFT JOIN pg_roles
         ON pg_stat_statements.userid = pg_roles.oid
  LEFT JOIN pg_database
         ON pg_stat_statements.dbid = pg_database.oid
  WHERE query != '<insufficient privilege>'
  AND query NOT LIKE '/* DDIGNORE */%%'
  {queryid_filter}
  {filters}
  {extra_clauses}
```
- `pg_roles` join resolves `userid` -> `rolname`; `pg_database` join resolves `dbid` -> `datname`.
- `<insufficient privilege>` rows (text the dd user can't read) are filtered out.
- `/* DDIGNORE */`-prefixed queries (the agent's own queries) are filtered out.
- `{filters}` = db scoping (see §7 dbstrict / ignore_databases).
- Column-introspection variant uses `extra_clauses="LIMIT 0"` to read just `cursor.description` column names without pulling data (`statements.py:211-232`).

### v2 lightweight query — `statements_v2.py:45-54`
```sql
SELECT {cols}
  FROM pg_stat_statements(false) AS pg_stat_statements
  LEFT JOIN pg_roles
         ON pg_stat_statements.userid = pg_roles.oid
  LEFT JOIN pg_database
         ON pg_stat_statements.dbid = pg_database.oid
  WHERE queryid IS NOT NULL
  {filters}
```
- **`pg_stat_statements(false)`** — the function form with `showtext=false` returns counters WITHOUT the SQL text, avoiding pulling query text from disk every cycle. This is the central v2 optimization. (v1 count query also uses `pg_stat_statements(false)` — `statements.py:66`.)
- v2 never selects `query` here; it only later fetches text for rows whose counters changed (see §5).

### v2 query-text fetch (miss path only) — `statements_v2.py:56-61`
```sql
SELECT s.queryid, s.dbid, s.userid, s.query
  FROM pg_stat_statements AS s
  INNER JOIN unnest(%s::bigint[], %s::oid[], %s::oid[]) AS v(queryid, dbid, userid)
         ON s.queryid = v.queryid AND s.dbid = v.dbid AND s.userid = v.userid
```
Fetches text only for the `(queryid, dbid, userid)` keys that changed and are not in the obfuscation cache.

### pgss housekeeping queries — `statements.py:66-68`
```sql
SELECT COUNT(*) FROM pg_stat_statements(false)            -- PG >= 9.4
SELECT COUNT(*) FROM pg_stat_statements                   -- PG < 9.4 (PG_STAT_STATEMENTS_COUNT_QUERY_LT_9_4)
SELECT dealloc FROM pg_stat_statements_info               -- PG >= 14 (PG_STAT_STATEMENTS_DEALLOC)
```

---

## 2. Columns: required / metric / tag / optional

Defined in `statements.py:72-130`.

**Required columns** (`PG_STAT_STATEMENTS_REQUIRED_COLUMNS`, `statements.py:72`) — collection aborts with a warning + `dd.postgres.statement_metrics.error` count if any are missing:
```
calls, query, rows
```
(v2 required is different — `statements_v2.py:65`: `queryid, userid, dbid, calls`.)

**Metric columns** (`PG_STAT_STATEMENTS_METRICS_COLUMNS`, `statements.py:87-116`) — these are the monotonically-increasing counters that get diffed:
```
calls, rows,
total_time, total_exec_time,
shared_blks_hit, shared_blks_read, shared_blks_dirtied, shared_blks_written,
local_blks_hit, local_blks_read, local_blks_dirtied, local_blks_written,
temp_blks_read, temp_blks_written,
wal_records, wal_fpi, wal_bytes,
total_plan_time, min_plan_time, max_plan_time, mean_plan_time, stddev_plan_time
```
plus timing columns (conditional on `track_io_timing=on`, see §6):
```
shared_blk_read_time, shared_blk_write_time         (PG >= 17, PG_STAT_STATEMENTS_TIMING_COLUMNS)
blk_read_time, blk_write_time                       (PG < 17,  PG_STAT_STATEMENTS_TIMING_COLUMNS_LT_17)
```
> NOTE: `min_plan_time/max_plan_time/mean_plan_time/stddev_plan_time` are gauges, not counters — but they are included in the diff set. The merge logic sums them across duplicates; the delta logic subtracts them. The backend reinterprets these per metric (the agent integration just ships raw diffs). For Db2, treat distribution-style stat columns carefully — see §3 caveat.

**Tag columns** (`PG_STAT_STATEMENTS_TAG_COLUMNS`, `statements.py:118-124`) — carried through but NOT diffed:
```
datname, rolname, query
```

**Optional columns** (`PG_STAT_STATEMENTS_OPTIONAL_COLUMNS`, `statements.py:126`):
```
queryid
```

`PG_STAT_ALL_DESIRED_COLUMNS = metrics | tags | optional` (`statements.py:128-130`).

**Column availability is queried, not assumed** (`statements.py:211-232`): the column list is read from `cursor.description` of a `LIMIT 0` query and cached in `self._stat_column_cache`. The actual selected columns are `sorted(available_columns & desired_columns)` (`statements.py:361`). This is required because the extension can lag behind the server version. **For Db2, mirror this: introspect the available `MON_GET_PKG_CACHE_STMT` columns rather than hard-coding by version**, since Db2 12.1 columns differ from older fixpacks.

---

## 3. Delta / rate computation across runs

The cumulative counters are converted to per-interval deltas by subtracting the previous run's snapshot. **The integration ships interval-total counts (the diff), not rates** — rate-per-second derivation happens server-side. Both v1 (`StatementMetrics.compute_derivative_rows`) and v2 (`DeltaDetector.compute`) implement the SAME algorithm.

### v1 engine: `StatementMetrics.compute_derivative_rows`
`datadog_checks_base/datadog_checks/base/utils/db/statement_metrics.py:25-123`

Called from `statements.py:511`:
```python
rows = self._state.compute_derivative_rows(
    rows, metric_columns, key=_row_key, execution_indicators=['calls']
)
```
where `metric_columns = available_columns & PG_STAT_STATEMENTS_METRICS_COLUMNS` (`statements.py:508-509`).

**Row key** (`statements.py:137-142`):
```python
def _row_key(row):
    return row['query_signature'], row['datname'], row['rolname']
```
Identity is the obfuscated-query signature + database + role — NOT the raw `queryid`. This means distinct `queryid`s that normalize to the same obfuscated text are merged.

**Algorithm (statement_metrics.py):**
1. `_merge_duplicate_rows` (`:126-150`) — sum metric columns across all current rows sharing the same key (multiple pgss rows normalizing to one signature). Tracks `dropped_metrics` (metrics absent from a row) and logs a warning.
2. For each merged row, look up `prev = self._previous_statements.get(row_key)` (`:69`). If no previous snapshot for this key, **skip** (first time seen → no delta emitted; becomes baseline) (`:70-71`).
3. `metric_columns = metrics & row.keys() & prev.keys()` computed once from first pair (`:73-76`).
4. **Stats-reset / no-change guard** (`:81-91`): compute `diff = row[k] - prev[k]` for each metric col.
   - If ANY `diff < 0` → `has_negative=True`, **skip the entire row** (treats negative as a stats reset; discards the whole row, not just one column — see class docstring `:34-36`).
   - If no `diff != 0` anywhere → `has_change=False`, **skip** (nothing changed).
5. **Execution-indicator guard** (`:93-100`): with `execution_indicators=['calls']`, the row is skipped unless at least one indicator column increased (`row[k] - prev[k] > 0`). This filters the case where a normalized query was evicted from pgss then re-inserted with the same `calls` (typically 1) and a slightly different duration — that re-inserted entry must become a new baseline, not emit a spurious delta. (docstring `:42-49`).
6. Emit `{k: row[k] - prev[k] if k in metric_columns else row[k] for k in row}` (`:102`) — metric cols become diffs, tag/text cols pass through unchanged.
7. **Cache update** (`:104-122`): drop stale keys no longer present; update existing entries in place; allocate new dicts only for first-seen keys. **`compute_derivative_rows` resets/updates the cache, so it must be called exactly once per check run** (docstring `:37`).

### v2 engine: `DeltaDetector.compute`
`postgres/datadog_checks/postgres/delta_detector.py:34-122`

Constructed with `metric_columns=PG_STAT_STATEMENTS_METRICS_COLUMNS`, `execution_indicators=frozenset({'calls'})` (`statements_v2.py:113-116`).

Key difference from v1: **the delta is keyed by `PgssKey = (queryid, dbid, userid)`** (`delta_detector.py:11, 38`), NOT by signature. Same negative/no-change/indicator guards (`delta_detector.py:62-78`). Returns a `DeltaResult` (`delta_detector.py:14-20`):
- `derivative_rows: list[dict]` — diffed rows for changed keys (still carry `queryid/dbid/userid`).
- `changed_pgss_keys: set[PgssKey]` — keys that produced a delta (need obfuscation resolution).
- `vanished_pgss_keys: set[PgssKey]` — keys present last run, absent now (evict from obfuscation cache).

After delta, v2 obfuscates only changed keys, then **re-merges by signature** in `_merge_by_query_signature` (`statements_v2.py:396-409`) using key `(query_signature, datname, rolname)` — so the final output rows match v1's grouping.

**Implication for Db2:** keep a `_previous` snapshot keyed by Db2's stable statement identity (e.g. `EXECUTABLE_ID` + db/schema), diff the cumulative columns, drop negative-diff rows wholesale (handles cache flush / `MON_GET` cache eviction = stats reset), require the execution-indicator (`NUM_EXECUTIONS` / `NUM_EXEC_WITH_METRICS`) to increase, and re-merge by `query_signature`.

---

## 4. Obfuscation / normalization

### v1: `_normalize_queries` — `statements.py:522-546`
For each raw row:
1. `statement = obfuscate_sql_with_metadata(row['query'], self._obfuscate_options)` (`:528`). On failure: log (warning if `log_unobfuscated_queries`, else debug) and **drop the row** (`:529-534`).
2. `obfuscated_query = statement['query']`; set `normalized_row['query'] = obfuscated_query` (`:536-537`).
3. `normalized_row['query_signature'] = compute_sql_signature(obfuscated_query)` (`:538`) — see §5.
4. Extract metadata (`:540-543`): `dd_tables = metadata.get('tables')`, `dd_commands = metadata.get('commands')`, `dd_comments = metadata.get('comments')`.

### v2: `ObfuscationLookup` — `obfuscation_lookup.py`
Two-tier LRU cache to avoid both the PG text fetch AND the FFI obfuscation call on cache hits:
- Tier 1: `_key_to_sig: OrderedDict[PgssKey, str]` — `(queryid,dbid,userid)` → signature.
- Tier 2: `_sig_to_result: OrderedDict[str, ObfuscationResult]` — signature → obfuscation result (multiple pgss keys sharing a signature share one result).
- `lookup(keys)` (`:66-92`) returns `(hits, misses)`, LRU-touching on hit.
- `populate(raw_texts)` (`:94-121`) obfuscates miss-path raw text, stores both tiers, trims to `maxsize`, discards raw text.
- `evict(keys)` (`:123-128`) drops tier-1 entries for vanished pgss keys.
- `_obfuscate_single` (`:130-148`) calls the same `obfuscate_sql_with_metadata` and `compute_sql_signature` and builds `ObfuscationResult(obfuscated_query, query_signature, tables, commands, comments)` (`:18-25`).
- Cache `maxsize` is synced each run to `pg_stat_statements.max` (default `DEFAULT_PGSS_MAX = 5000`) — `statements_v2.py:244-248, 63`.

### `obfuscate_sql_with_metadata` — `datadog_checks_base/datadog_checks/base/utils/db/utils.py:249-286`
- Calls `datadog_agent.obfuscate_sql(query, options)` — an FFI call into the agent's Go obfuscator. Returns a JSON string when metadata is requested (agent >= 7.34); otherwise plain obfuscated text.
- Parses `{'query': ..., 'metadata': {...}}`. Pops `tables_csv`, splits on `,` into a `tables` list (`:283-285`).
- `replace_null_character` arg strips `\x00` before obfuscating — **relevant for Db2/SQL Server** which allow embedded nulls in text (`:264-266`); Postgres doesn't set it but Db2 likely should.

### Obfuscator options — `statements.py:177-183` / `statements_v2.py:118-123`
```python
obfuscate_options = self._config.obfuscator_options.model_dump()
obfuscate_options['table_names']          = config.obfuscator_options.collect_tables
obfuscate_options['dollar_quoted_func']   = config.obfuscator_options.keep_dollar_quoted_func
obfuscate_options['return_json_metadata'] = config.obfuscator_options.collect_metadata
obfuscate_options['dbms'] = 'postgresql'   # <-- for Db2 use the Db2 dbms identifier
self._obfuscate_options = to_native_string(json.dumps(obfuscate_options))
```
`dbms` selects the dialect-specific obfuscator in the agent Go code. **For Db2 the correct dbms string must be passed** (Db2 uses SQL similar to others; confirm the agent supports a `db2` dialect or use a generic SQL one — open question for the implementation plan).

---

## 5. `query_signature`

`compute_sql_signature` — `datadog_checks_base/datadog_checks/base/utils/db/sql.py:18-26`:
```python
def compute_sql_signature(normalized_query):
    if not normalized_query:
        return None
    return format(mmh3.hash64(ensure_bytes(normalized_query), signed=False)[0], 'x')
```
- **MurmurHash3 64-bit (mmh3), unsigned, first of the two 64-bit halves, formatted as lowercase hex.**
- Input is the AGENT-OBFUSCATED query text (post-`obfuscate_sql`), so it matches the APM resource hash the backend computes (comment `sql.py:24-25` — do not change without coordinating with backend).
- **For Db2: use the identical hash function on the obfuscated statement text** so DBM <-> APM correlation works. Reuse `compute_sql_signature` from base — do not reimplement.

Related (samples/plans, not metrics, but in same module):
- `compute_exec_plan_signature` (`sql.py:48-56`) — hashes sorted-key JSON plan.
- `normalize_query_tag` (`sql.py:29-45`) — substitutes ASCII commas with U+066B for tag display (used for sample tags).

---

## 6. `track_io_timing` gating

Timing columns are only requested when the server has `track_io_timing=on`:
- v1: `statements.py:328-330` — `if self._check.pg_settings.get("track_io_timing") != "on": desired_columns -= TIMING_COLUMNS; desired_columns -= TIMING_COLUMNS_LT_17`.
- v2: `statements_v2.py:278-279` — same.

Db2 analog: certain `MON_GET_PKG_CACHE_STMT` timing columns require the `MON_REQ_METRICS`/`MON_ACT_METRICS` / `mon_obj_metrics` collection levels to be enabled (`DFTMON_*` dbm cfg or `WLM`/`MONITOR` switches). Gate timing-derived metrics on those being enabled.

---

## 7. Database scoping filters (dbstrict / ignore_databases)

`statements.py:362-371` (v1) and `statements_v2.py:283-292` (v2):
```python
if self._config.dbstrict:
    filters = "AND pg_database.datname = %s"
    params = (self._config.dbname,)
elif self._config.ignore_databases:
    filters = " AND " + " AND ".join("pg_database.datname NOT ILIKE %s" for _ in ...)
    params += tuple(self._config.ignore_databases)
```
`dbstrict` restricts to the configured db; otherwise `ignore_databases` excludes named DBs (case-insensitive). pgss is host-wide (all DBs), so the collector filters in SQL.

---

## 8. Payload shapes sent to the backend

Two distinct event-platform streams are produced per run from the collected rows.

### 8a. Query-metrics payload → `dbm-metrics`
Submitted via `self._check.database_monitoring_query_metrics(payload)` (`statements.py:266`, `statements_v2.py:441`), which calls `aggregator.submit_event_platform_event(self, self.check_id, raw_event, "dbm-metrics")` — `datadog_checks_base/datadog_checks/base/checks/base.py:779-784`.

**Wrapper** (`statements.py:252-261` / `statements_v2.py:428-437`):
```python
payload_wrapper = {
    'host': self._check.reported_hostname,
    'timestamp': time.time() * 1000,            # ms
    'min_collection_interval': self._metrics_collection_interval,
    'tags': self._tags_no_db,                   # tags WITHOUT the per-db "db:" tag
    'cloud_metadata': self._check.cloud_metadata,
    'postgres_version': payload_pg_version(self._check.version),
    'ddagentversion': datadog_agent.get_version(),
    'service': self._config.service,
}
```
Then `_get_query_metrics_payloads` (`statements.py:271-297` / `statements_v2.py:500-524`) attaches the rows under the key **`postgres_rows`** and serializes:
```python
payload["postgres_rows"] = current   # list of derivative+normalized row dicts
serialized = json.dumps(payload, default=default_json_event_encoding)
```
**Each `postgres_rows` element** = a derivative row dict containing:
- metric diffs: `calls, rows, total_time/total_exec_time, *_blks_*, *_blk_*_time, wal_*, *_plan_time`, etc. (whichever metric columns were available)
- tag/text fields: `datname`, `rolname`, `query` (obfuscated text), `query_signature`
- metadata: `dd_tables`, `dd_commands`, `dd_comments`
- (v1 also `queryid` if present; v2 strips `dbid`/`userid` via `_assemble_rows` `statements_v2.py:385-386`)

**Batch splitting** (`statements.py:274-297`): rows are recursively bisected so each serialized payload stays under `batch_max_content_size` (default 20 MB, matching `database_monitoring.metrics.batch_max_content_size` in datadog.yaml — `statements.py:164-171`). A single row larger than the limit is dropped with a warning.

> The `*_rows` wrapper key and `*_version` key are dialect-named (`postgres_rows`, `postgres_version`). **For Db2 these become e.g. `db2_rows` and `db2_version`** — the backend ingestion has per-dbms parsers. The metric NAMES inside the rows (`calls`, `rows`, timing, etc.) are also Postgres-specific column names; the backend maps each known column to a Datadog metric. The Db2 implementation must agree with the backend on the row schema/column names (coordinate with the DBM backend team).

### 8b. Full-query-text (FQT) event → `dbm-samples`
`_rows_to_fqt_events` (`statements.py:548-581` / `statements_v2.py:526-559`), submitted via `self._check.database_monitoring_query_sample(json.dumps(event, ...))` (`statements.py:250`, `statements_v2.py:426`) → `submit_event_platform_event(..., "dbm-samples")` (`base.py:772-777`).

Emitted **once per `(query_signature, datname, rolname)` per TTL window** — rate-limited by `self._full_statement_text_cache` (a `TTLCache`, §9). Event shape:
```python
{
  "timestamp": time.time() * 1000,
  "host": self._check.reported_hostname,
  "database_instance": self._check.database_identifier,
  "ddagentversion": datadog_agent.get_version(),
  "ddsource": "postgres",                       # dbms identifier
  "ddtags": ",".join(row_tags),                 # tags_no_db + ["db:<datname>", "rolname:<rolname>"]
  "dbm_type": "fqt",                            # <-- full query text marker
  "service": self._config.service,
  "db": {
    "instance": row['datname'],
    "query_signature": row['query_signature'],
    "statement": row['query'],                  # obfuscated text
    "metadata": {"tables": ..., "commands": ..., "comments": ...},
  },
  "postgres": {"datname": ..., "rolname": ...}, # dialect-specific block
}
```
**For Db2:** `ddsource: "db2"` (or the registered source), and a `db2` block instead of `postgres`.

### JSON encoding helper
`default_json_event_encoding` (`utils.py:237-246`) handles Decimal→float, date/datetime→isoformat, IPv4Address→str, bytes→utf-8. Required because pgss returns `Decimal`/`numeric` values. Db2's `ibm_db` driver returns `Decimal` for many numeric columns — reuse this encoder.

---

## 9. Caches & TTLs

**Full-statement-text rate-limit cache** (`statements.py:184-188` / `statements_v2.py:131-134`):
```python
self._full_statement_text_cache = TTLCache(
    maxsize=config.query_metrics.full_statement_text_cache_max_size,           # default 10000
    ttl=60 * 60 / config.query_metrics.full_statement_text_samples_per_hour_per_query,  # default => 3600s
)
```
Keyed by `(query_signature, datname, rolname)`; presence means "already emitted an FQT this window" → skip (`statements.py:550-553`). Default = 1 FQT per query per hour.

**v2 obfuscation LRU** — `maxsize = pg_stat_statements.max` (default `DEFAULT_PGSS_MAX=5000`), synced each run (`statements_v2.py:63, 244-248`).

---

## 10. Scheduling: `DBMAsyncJob`

Both collectors subclass `DBMAsyncJob` (`datadog_checks_base/datadog_checks/base/utils/db/utils.py:289-499`).

### Construction — `statements.py:148-159` / `statements_v2.py:93-104`
```python
collection_interval = float(config.query_metrics.collection_interval)
super().__init__(
    check,
    run_sync=config.query_metrics.run_sync,
    enabled=config.query_metrics.enabled,
    expected_db_exceptions=(psycopg.errors.DatabaseError,),
    min_collection_interval=config.min_collection_interval,
    dbms="postgres",
    rate_limit=1 / float(collection_interval),     # executions per second
    job_name="query-metrics",
)
```
- `rate_limit = 1/collection_interval` → enforced by `ConstantRateLimiter` (`utils.py:106-145`), which sleeps in `max_sleep_chunk_s` chunks to maintain the period, breaking early on cancel.
- `expected_db_exceptions` are logged as warnings (not crashes) and counted as `dd.postgres.async_job.error` (`utils.py:439-451`).

### Wiring into the check
- Instantiated in `_initialize_statement_metrics`, registered via `check_initializations.append(self._initialize_statement_metrics)` — `postgres.py:185, 644-666`.
- **v1 vs v2 selection** (`postgres.py:644-666`): uses `PostgresStatementMetricsV2` when `config.query_metrics.incremental_query_metrics and version >= V10 and not custom_pgss_view`; else `PostgresStatementMetrics`. (`incremental_query_metrics` default is shown as `true` in spec — `spec.yaml:788-798`.)
- Added to the jobs list for cancellation: `postgres.py:537` (`jobs.extend([self.statement_metrics, self.statement_samples, self.metadata_samples])`).
- **Kicked off each check run** in `check()` (`postgres.py:1272-1278`):
```python
if not self._config.only_custom_queries:
    self._collect_stats(tags)
    if not self._cancelled and self._config.dbm:
        self.statement_metrics.run_job_loop(tags)   # <-- per-run trigger
        self.statement_samples.run_job_loop(tags)
        self.metadata_samples.run_job_loop(tags)
```

### `run_job_loop` lifecycle — `utils.py:354-471`
- If `not enabled` → return (`:359-361`).
- Resolves db host once (`:362-363`); stores `tags`, builds `_job_tags = tags + ["job:query-metrics"]`; sets `_last_check_run = now` (`:364-368`).
- If `run_sync` (or env `DBM_THREADED_JOB_RUN_SYNC`) → run inline rate-limited (`:369-371`).
- Else submit `_job_loop` to a shared `ThreadPoolExecutor(100000)` (`:293, 372-373`) **only if not already running**. If already running and the expected interval was exceeded, emit a `MISSED_COLLECTION` health event + `dd.postgres.async_job.missed_collection` count (`:374-408`).
- `_job_loop` (`:410-471`) loops calling `_run_job_rate_limited()` until: cancel event set (count `dd.postgres.async_job.cancel`), OR check inactivity `now - _last_check_run > min_collection_interval * 2` (count `dd.postgres.async_job.inactive_stop`) (`:418-423`). The main-check `run_job_loop` call each interval refreshes `_last_check_run`, keeping the background loop alive.
- `_run_job_rate_limited` (`:482-492`): records `_last_run_start`, runs `_run_job_traced` → `run_job()`, then sleeps to enforce the rate limit.

### `run_job` → collection pipeline
**v1** (`statements.py:234-238`): strips `dd.internal*` tags into `self.tags`, strips `db:*` into `self._tags_no_db`, then `collect_per_statement_metrics()`:
1. `_collect_metrics_rows` (`:497-520`): emit pgss housekeeping metrics; `_load_pg_stat_statements`; `_normalize_queries`; `_state.compute_derivative_rows(...)`; emit `dd.postgres.queries.query_rows_raw` gauge.
2. For each FQT event → `database_monitoring_query_sample` (`:249-250`).
3. Build wrapper, `_get_query_metrics_payloads`, send each via `database_monitoring_query_metrics` (`:263-266`).
- All wrapped in try/except logging `'Unable to collect statement metrics due to an error'` (`:267-269`).

**v2** (`statements_v2.py:413-496`): `_collect_metrics_rows`:
1. `_emit_pg_stat_statements_metrics` + `_emit_pg_stat_statements_dealloc` + `_emit_pg_stat_statements_max_warning` + `_sync_cache_sizes`.
2. `_load_lightweight_snapshot` (counters only).
3. `delta = self._delta_detector.compute(snapshot_rows)`.
4. `obfuscations = self._resolve_obfuscations(delta.changed_pgss_keys, delta.vanished_pgss_keys)` — evict vanished, lookup hits, fetch+obfuscate misses.
5. `rows = self._assemble_rows(delta.derivative_rows, obfuscations)` → merge by signature.
6. Same FQT + payload emission as v1.

---

## 11. Config knobs (the `query_metrics` block)

Model `QueryMetrics` (`postgres/datadog_checks/postgres/config_models/instance.py:285-297`); spec/defaults in `postgres/assets/configuration/spec.yaml:742-816`:

| Option | Type | Default | Notes / spec line |
|---|---|---|---|
| `enabled` | bool | `true` | requires `dbm: true`; passed to `DBMAsyncJob(enabled=...)`. spec:747 |
| `collection_interval` | number (s) | `10` | drives `rate_limit = 1/interval`; must be identical across all instances. spec:754 |
| `pg_stat_statements_max_warning_threshold` | number | `10000` | warns if `pg_stat_statements.max` exceeds it. spec:763 |
| `full_statement_text_cache_max_size` | number | `10000` | FQT cache `maxsize`. spec:772 |
| `full_statement_text_samples_per_hour_per_query` | number | `1` | FQT TTL = `3600 / value`. spec:780 |
| `incremental_query_metrics` | bool | `true` (display_default) | selects v2 collector (PG>=10, no custom pgss view). spec:788 |
| `run_sync` | bool | `false` | run inline (testing). spec:799 |
| `batch_max_content_size` | int | `20_000_000` | stub; real value from `datadog.yaml` `database_monitoring.metrics.batch_max_content_size`. spec:808 |

Related instance-level knobs used by the collector:
- `dbm` (bool) — master gate (`postgres.py:1275`).
- `min_collection_interval` (default 15) — feeds inactivity stop = `2 * min_collection_interval` (`utils.py:418`).
- `dbstrict`, `ignore_databases`, `dbname`, `pg_stat_statements_view` — scoping (§7), and the custom-view check that forces v1 (`postgres.py:645,652`).
- `obfuscator_options.{collect_tables, keep_dollar_quoted_func, collect_metadata, ...}` — obfuscation (§4).
- `log_unobfuscated_queries` — whether obfuscation failures log the raw query.
- `service`, `reported_hostname`, `cloud_metadata`, `database_identifier` — payload identity.

---

## 12. Internal telemetry metrics emitted by the collector

(All raw / `dd.internal`-excluded; useful to mirror for Db2 observability.)
- `dd.postgres.statement_metrics.error` (count, with `error:*` tag) — `statements.py:313, 427`; v2 `statements_v2.py:266, 602`.
- `pg_stat_statements.max` (gauge), `pg_stat_statements.count` (count) — `statements.py:482-493`.
- `pg_stat_statements.dealloc` (monotonic_count, PG>=14) — `statements.py:463`.
- `dd.postgres.queries.query_rows_raw` (gauge) — `statements.py:512`; v2 `statements_v2.py:488`.
- v2 only: `dd.postgres.statement_metrics.lookup.hits/misses` (`statements_v2.py:342-355`), `dd.postgres.statement_metrics.delta.derivative_rows` / `.delta.changed_queryids` (`statements_v2.py:460-473`).
- Async-job framework counts: `dd.postgres.async_job.{cancel,inactive_stop,error,missed_collection}` (`utils.py:404,416,421,438,447,455`).

---

## 13. Db2 12.1 mapping guidance (target = 12.1.4 live container)

The Db2 integration currently has NO statement-monitoring queries (`ibm_db2/datadog_checks/ibm_db2/queries.py` contains none; verified by grep). To replicate this feature for Db2 12.1:

**Source table function** — `TABLE(MON_GET_PKG_CACHE_STMT(NULL, NULL, NULL, -1))` (in `SYSIBMADM`/system catalog). It returns cumulative per-cached-statement counters analogous to `pg_stat_statements`. Stable identity column: **`EXECUTABLE_ID`** (VARBINARY) — the analog of `(queryid,dbid,userid)`. The SQL text is **`STMT_TEXT`** (analog of `query`).

Candidate metric (cumulative counter) columns on `MON_GET_PKG_CACHE_STMT` (Db2 12.1; introspect actual columns at runtime per §2):
- Execution-indicator: `NUM_EXECUTIONS` (analog of `calls`; also `NUM_EXEC_WITH_METRICS`).
- Rows: `ROWS_READ`, `ROWS_RETURNED`, `ROWS_MODIFIED`, `ROWS_INSERTED/UPDATED/DELETED`.
- Timing: `TOTAL_ACT_TIME`, `TOTAL_CPU_TIME`, `STMT_EXEC_TIME`, `TOTAL_ACT_WAIT_TIME`, `LOCK_WAIT_TIME`, `TOTAL_SECTION_SORT_TIME`.
- IO/buffer: `POOL_DATA_L_READS`, `POOL_DATA_P_READS`, `POOL_INDEX_L_READS`, `POOL_INDEX_P_READS`, `DIRECT_READS`, `DIRECT_WRITES`, `POOL_*_WRITES`.
- Sort/lock: `TOTAL_SORTS`, `SORT_OVERFLOWS`, `LOCK_WAITS`, `LOCK_TIMEOUTS`, `DEADLOCKS`.
> Confirm exact column names against the live 12.1.4 catalog (`SELECT * FROM TABLE(MON_GET_PKG_CACHE_STMT(NULL,NULL,NULL,-1)) FETCH FIRST 1 ROWS ONLY`) — do not hard-code; introspect like §2.

**Reusable base helpers (import, do NOT reimplement):**
- `datadog_checks.base.utils.db.statement_metrics.StatementMetrics.compute_derivative_rows` — delta engine (§3).
- `datadog_checks.base.utils.db.sql.compute_sql_signature` — signature (§5).
- `datadog_checks.base.utils.db.utils.obfuscate_sql_with_metadata` (call with `replace_null_character=True` for Db2 — §4) and `default_json_event_encoding` (§8b), `DBMAsyncJob` (§10).

**Db2-specific deltas from the Postgres design:**
- Key by `EXECUTABLE_ID` (+ database/member) for the snapshot diff; key the final merge by `(query_signature, db, ...)`.
- Use `NUM_EXECUTIONS` as the `execution_indicators` value.
- Cache flush / `STMT_TEXT` truncation: Db2 may truncate STMT_TEXT to a configured size; the obfuscated signature is still computed over whatever text is returned — note the truncation caveat.
- Payload wrapper key → `db2_rows`; FQT `ddsource: "db2"`, dialect block `"db2": {...}`; obfuscator `dbms` must be the Db2 dialect identifier (open question — confirm agent obfuscator supports Db2; otherwise a generic SQL mode).
- Timing columns gating analog (§6): require Db2 monitoring metrics collection (`mon_req_metrics`/`mon_act_metrics`/`mon_obj_metrics` ≥ BASE, or `MON_*` WLM switches) before emitting timing-derived metrics.

---

## 14. Key file index (absolute paths)

- `/home/bits/dd/integrations-core/postgres/datadog_checks/postgres/statements.py` — v1 collector.
- `/home/bits/dd/integrations-core/postgres/datadog_checks/postgres/statements_v2.py` — v2 incremental collector.
- `/home/bits/dd/integrations-core/postgres/datadog_checks/postgres/delta_detector.py` — v2 delta engine.
- `/home/bits/dd/integrations-core/postgres/datadog_checks/postgres/obfuscation_lookup.py` — v2 two-tier obfuscation cache.
- `/home/bits/dd/integrations-core/datadog_checks_base/datadog_checks/base/utils/db/statement_metrics.py` — shared delta engine (v1).
- `/home/bits/dd/integrations-core/datadog_checks_base/datadog_checks/base/utils/db/sql.py` — `compute_sql_signature`.
- `/home/bits/dd/integrations-core/datadog_checks_base/datadog_checks/base/utils/db/utils.py` — `DBMAsyncJob`, `obfuscate_sql_with_metadata`, `ConstantRateLimiter`, `default_json_event_encoding`, `TagManager`.
- `/home/bits/dd/integrations-core/datadog_checks_base/datadog_checks/base/checks/base.py:772-799` — `database_monitoring_query_metrics` / `database_monitoring_query_sample` submission.
- `/home/bits/dd/integrations-core/postgres/datadog_checks/postgres/postgres.py:185,537,644-666,1272-1278` — wiring & scheduling.
- `/home/bits/dd/integrations-core/postgres/datadog_checks/postgres/config_models/instance.py:285-297` — `QueryMetrics` model.
- `/home/bits/dd/integrations-core/postgres/assets/configuration/spec.yaml:742-816` — `query_metrics` spec & defaults.
