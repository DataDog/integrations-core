# MySQL DBM — Source Code Deep-Dive (Query Metrics, Samples, Activity, Metadata/Settings, Schemas)

Raw research input for implementing the full **Db2 DBM feature set** by mirroring the MySQL integration. This documents EXACTLY how the MySQL integration implements each DBM "collector": the source tables/columns, the SQL, delta computation, obfuscation/signatures, payload shapes, scheduling, and every config knob. Target Db2 version is **12.1** (live container 12.1.4) — Db2 analog table functions are noted inline where helpful, but the focus is faithful documentation of the MySQL behavior.

All citations are absolute paths under `/home/bits/dd/integrations-core`.

The four DBM async jobs and their files:
- **Query metrics** — `mysql/datadog_checks/mysql/statements.py` (class `MySQLStatementMetrics`)
- **Statement samples + explain plans** — `mysql/datadog_checks/mysql/statement_samples.py` (class `MySQLStatementSamples`)
- **Activity (active sessions / "the analog of pg_stat_activity")** — `mysql/datadog_checks/mysql/activity.py` (class `MySQLActivity`)
- **Metadata / settings** — `mysql/datadog_checks/mysql/metadata.py` (class `MySQLMetadata`) + schema collection in `mysql/datadog_checks/mysql/databases_data.py` (class `DatabasesData`), SQL in `mysql/datadog_checks/mysql/queries.py`

Shared infra:
- DBMAsyncJob scheduler base: `datadog_checks_base/datadog_checks/base/utils/db/utils.py:289-499`
- Delta engine for metrics: `datadog_checks_base/datadog_checks/base/utils/db/statement_metrics.py` (class `StatementMetrics`)
- Config: `mysql/datadog_checks/mysql/config.py`
- Example config (knobs + defaults): `mysql/datadog_checks/mysql/data/conf.yaml.example`

---

## 0. How the jobs are wired and scheduled

### Instantiation — `mysql/datadog_checks/mysql/mysql.py:156-163`
```python
self._statement_metrics = MySQLStatementMetrics(self, self._config, self._get_connection_args, self._uses_aws_managed_auth)
self._statement_samples  = MySQLStatementSamples(self, self._config, self._get_connection_args, self._uses_aws_managed_auth)
self._mysql_metadata     = MySQLMetadata(self, self._config, self._get_connection_args, self._uses_aws_managed_auth)
self._query_activity     = MySQLActivity(self, self._config, self._get_connection_args, self._uses_aws_managed_auth)
```

### Run on each check run — `mysql.py:425-428` (only when `dbm_enabled`)
```python
self._statement_metrics.run_job_loop(dbm_tags)
self._statement_samples.run_job_loop(dbm_tags)
self._query_activity.run_job_loop(dbm_tags)
self._mysql_metadata.run_job_loop(dbm_tags)
```
### Cancel on check shutdown — `mysql.py:443-447`.

### DBMAsyncJob lifecycle (`db/utils.py:289-499`)
- Each job subclasses `DBMAsyncJob`. `run_job_loop(tags)` is called every main check run; it either (a) runs synchronously if `run_sync` true, or (b) spins up a background thread (`ThreadPoolExecutor(100000)`) that runs `run_job()` in a loop, rate-limited by a `ConstantRateLimiter` set to `rate_limit = 1/collection_interval` (`db/utils.py:354-373, 410-431`).
- `_run_job_rate_limited` runs `run_job()` then sleeps the remainder of the interval (`db/utils.py:482-492`).
- Loop self-terminates if the main check stops calling `run_job_loop` for `min_collection_interval * 2` seconds → emits `dd.mysql.async_job.inactive_stop` (`db/utils.py:418-423`).
- Cancellation emits `dd.mysql.async_job.cancel`; crashes emit `dd.mysql.async_job.error` (`db/utils.py:432-459`).
- Missed-collection health events when elapsed > expected interval (`db/utils.py:375-406`).
- Each job overrides `run_job()` and holds its own dedicated pymysql connection (`self._db`), closed via `shutdown_callback=self._close_db_conn`.

### EventPlatform submission helpers — `datadog_checks_base/datadog_checks/base/checks/base.py:772-798`
| Helper | track type | Used by |
|---|---|---|
| `database_monitoring_query_sample(raw)`   | `dbm-samples`  | FQT events (metrics job) + plan events (samples job) |
| `database_monitoring_query_metrics(raw)`  | `dbm-metrics`  | query metrics payload |
| `database_monitoring_query_activity(raw)` | `dbm-activity` | activity payload |
| `database_monitoring_metadata(raw)`       | `dbm-metadata` | settings + schema payloads |

All payloads are `json.dumps(...)` with `default=default_json_event_encoding` (or a custom encoder in activity).

---

## 1. QUERY METRICS — `statements.py` (`MySQLStatementMetrics`)

### 1.1 Source of truth
**`performance_schema.events_statements_summary_by_digest`** — a cumulative per-`(schema_name, digest)` counter table (monotonically increasing). This is the MySQL analog of `pg_stat_statements`. Db2 analog: `SYSIBMADM.MON_GET_PKG_CACHE_STMT` / `MON_GET_PKG_CACHE_STMT_DETAILS` keyed by `EXECUTABLE_ID`.

Optionally UNION'd with **`performance_schema.prepared_statements_instances`** (prepared statements that never get digested into the summary table).

### 1.2 Base SQL — `statements.py:235-307`
```sql
SELECT `schema_name`, `digest`, `digest_text`,
       `count_star`, `sum_timer_wait`, `sum_lock_time`, `sum_errors`,
       `sum_rows_affected`, `sum_rows_sent`, `sum_rows_examined`,
       `sum_select_scan`, `sum_select_full_join`, `sum_no_index_used`, `sum_no_good_index_used`,
       `sum_sort_rows`, `sum_sort_merge_passes`, `sum_sort_range`, `sum_sort_scan`,
       `sum_created_tmp_tables`, `sum_created_tmp_disk_tables`,
       `sum_select_full_range_join`, `sum_select_range`, `sum_select_range_check`,
       `last_seen`
FROM performance_schema.events_statements_summary_by_digest
{condition}
```
- `{condition}` is one of:
  - default: `WHERE \`digest_text\` NOT LIKE 'EXPLAIN %' OR \`digest_text\` IS NULL`
  - `only_query_recent_statements=true`: `WHERE \`last_seen\` >= %s` (param `self._last_seen`)
- Default path also appends `ORDER BY \`count_star\` DESC LIMIT 10000` (`statements.py:302-307`).
- Prepared-statements UNION (`statements.py:267-301`): same column aliases, summed (`SUM(count_execute) AS count_star`, `SUM(sum_timer_execute) AS sum_timer_wait`, ...), `NOW() AS last_seen`, grouped by `owner_object_schema, sql_text`; filters out EXPLAIN.
- `self._last_seen` initialized `'1970-01-01'`; after each fetch set to `max(row['last_seen'])` (`statements.py:102, 315-318`).

### 1.3 Metric columns (delta candidates) — `METRICS_COLUMNS`, `statements.py:36-57`
These 20 columns get the monotonic→delta treatment:
```
count_star, sum_timer_wait, sum_lock_time, sum_errors, sum_rows_affected,
sum_rows_sent, sum_rows_examined, sum_select_scan, sum_select_full_join,
sum_no_index_used, sum_no_good_index_used, sum_sort_rows, sum_sort_merge_passes,
sum_sort_range, sum_sort_scan, sum_created_tmp_tables, sum_created_tmp_disk_tables,
sum_select_full_range_join, sum_select_range, sum_select_range_check
```
Note: `sum_timer_wait` and `sum_lock_time` are in **picoseconds** in the summary table (sent as-is in the metrics payload; the backend converts).

### 1.4 Pipeline — `_collect_per_statement_metrics`, `statements.py:184-201`
1. `_get_statement_count(tags)` — `SELECT count(*) FROM ...summary_by_digest` → gauge `dd.mysql.statement_metrics.events_statements_summary_by_digest.total_rows` (`statements.py:203-214`).
2. `_query_summary_per_statement()` — runs base SQL above.
3. `_filter_query_rows()` — drop rows where `digest_text` starts with `explain` (`statements.py:320-327`).
4. `_normalize_queries()` — obfuscate + signature (see 1.5).
5. `_add_associated_rows()` — merge rows that share a `query_signature` across different `digest`s (see 1.6).
6. `self._state.compute_derivative_rows(rows, METRICS_COLUMNS, key=_row_key)` — delta computation (see 1.7).

`_row_key = (row['schema_name'], row['query_signature'])` (`statements.py:60-65`).

### 1.5 Obfuscation / normalization — `_normalize_queries`, `statements.py:329-348`
- `obfuscate_sql_with_metadata(row['digest_text'], self._obfuscate_options)` → `statement['query']` (obfuscated) + `statement['metadata']`.
- `query_signature = compute_sql_signature(obfuscated_statement)`.
- Adds `dd_tables = metadata['tables']`, `dd_commands = metadata['commands']`, `dd_comments = metadata['comments']`.
- Rows that fail obfuscation are skipped (logged at WARNING).

### 1.6 Cross-digest aggregation — `_add_associated_rows`, `statements.py:350-365`
Two different `digest`s can normalize to the same `query_signature`. The job caches per-`(schema_name, query_signature)` a dict of `{digest -> row}` in a TTLCache (`_statement_rows`, maxsize `statement_rows_cache_max_size`=10000, ttl `statement_rows_cache_ttl`=3600). Each run updates the cache and re-emits ALL cached rows so deltas are computed across the full set even if a digest was absent in the immediately previous run.

### 1.7 Delta computation — `StatementMetrics.compute_derivative_rows` (`db/statement_metrics.py`)
- Keeps previous run's rows keyed by `_row_key + metric columns`. For each key computes `current - previous` for each column in `METRICS_COLUMNS`.
- **Drops rows where all deltas are zero** (no execution since last run).
- Handles counter resets (negative delta → treated as new baseline, row dropped that run).
- The first run produces no output (no baseline).

### 1.8 Metrics payload (track `dbm-metrics`) — `collect_per_statement_metrics`, `statements.py:164-176`
```python
{
  'host': resolved_hostname,
  'timestamp': time.time()*1000,
  'mysql_version': version.version + '+' + version.build,
  'mysql_flavor': version.flavor,            # 'MySQL' | 'MariaDB' | 'Percona'
  'ddagentversion': datadog_agent.get_version(),
  'min_collection_interval': self._metric_collection_interval,   # default 10
  'tags': tags,                              # dd.internal* stripped
  'cloud_metadata': config.cloud_metadata,
  'service': config.service,
  'mysql_rows': rows,                        # list of per-statement delta rows
}
```
Each row in `mysql_rows` carries: `schema_name`, `digest`, `digest_text` (obfuscated), `query_signature`, `dd_tables`, `dd_commands`, `dd_comments`, plus the 20 delta metric columns and `count_star`.

### 1.9 FQT (full-query-text) events (track `dbm-samples`) — `_rows_to_fqt_events`, `statements.py:367-393`
For each statement seen, at most once per `(schema_name, query_signature)` per the `_full_statement_text_cache` TTLCache (maxsize `full_statement_text_cache_max_size`=10000, ttl `= 3600/full_statement_text_samples_per_hour_per_query`, default 1/hr → ttl 1h):
```python
{
  "timestamp": ms, "host": reported_hostname, "ddagentversion": ...,
  "ddsource": "mysql", "ddtags": "...,schema:<schema_name>", "dbm_type": "fqt",
  "service": config.service,
  "db": {
    "instance": schema_name,
    "query_signature": query_signature,
    "statement": digest_text,                          # obfuscated
    "metadata": {"tables": dd_tables, "commands": dd_commands, "comments": dd_comments}
  },
  "mysql": {"schema": schema_name}
}
```

### 1.10 Preflight: performance_schema must be enabled — `statements.py:140-152`
If `check.global_variables.performance_schema_enabled is False`, records warning `DatabaseConfigurationError.performance_schema_not_enabled` and returns (MySQL silently returns no rows otherwise).

### 1.11 Prepared statements gating — `collect_prepared_statements`, `statements.py:395-408`
`prepared_statements_instances` exists in MySQL ≥5.7.4 / MariaDB ≥10.5.2. Skipped when `only_query_recent_statements=true` (that table has no `last_seen`). Controlled by `query_metrics.collect_prepared_statements` (default true).

### 1.12 Internal/debug metrics emitted by the metrics job
- `dd.mysql.statement_metrics.collect_metrics.elapsed_ms` (gauge) — `statements.py:129`
- `dd.mysql.collect_per_statement_metrics.rows` (gauge) — `statements.py:177`
- `dd.mysql.statement_metrics.query_rows` (gauge) — `statements.py:190`
- `dd.mysql.statement_metrics.events_statements_summary_by_digest.total_rows` (gauge) — `statements.py:209`

### 1.13 Config (under `query_metrics:`) — `config.py:54` (`statement_metrics_config`)
| key | default | code |
|---|---|---|
| `enabled` | `true` | `statements.py:82` |
| `collection_interval` | `10` (s) | `statements.py:75-77` |
| `run_sync` | `false` | `statements.py:81` |
| `only_query_recent_statements` | `false` | `statements.py:224` |
| `collect_prepared_statements` | `true` | `statements.py:405` |
Other instance-level knobs (config.py:47-52): `full_statement_text_cache_max_size`=10000, `full_statement_text_samples_per_hour_per_query`=1, `statement_rows_cache_max_size`=10000, `statement_rows_cache_ttl`=3600.

---

## 2. STATEMENT SAMPLES + EXPLAIN PLANS — `statement_samples.py` (`MySQLStatementSamples`)

### 2.1 Source of truth
**`performance_schema.events_statements_current`** (one in-flight statement per thread), LEFT JOIN `performance_schema.threads` for processlist user/host/db. Db2 analog: `MON_GET_ACTIVITY` / `MON_GET_PKG_CACHE_STMT` + EXPLAIN via `EXPLAIN_*` tables.

### 2.2 Sample-collection SQL — `EVENTS_STATEMENTS_CURRENT_QUERY`, `statement_samples.py:74-116`
```sql
SELECT current_schema, sql_text, digest, digest_text, end_event_id,
       timer_start, @uptime as uptime, unix_timestamp() as now, timer_end,
       timer_wait / 1000 AS timer_wait_ns, lock_time / 1000 AS lock_time_ns,
       rows_affected, rows_sent, rows_examined,
       select_full_join, select_full_range_join, select_range, select_range_check, select_scan,
       sort_merge_passes, sort_range, sort_rows, sort_scan,
       no_index_used, no_good_index_used,
       processlist_user, processlist_host, processlist_db
FROM performance_schema.events_statements_current E
LEFT JOIN performance_schema.threads T ON E.thread_id = T.thread_id
WHERE sql_text IS NOT NULL
  AND event_name like 'statement/%'
  AND digest_text is NOT NULL
  AND digest_text NOT LIKE 'EXPLAIN %'
ORDER BY timer_wait DESC
```
- `timer_wait`/`lock_time` are picoseconds in the table → `/1000` to get **nanoseconds** (`timer_wait_ns`, `lock_time_ns`).
- `@uptime` is set immediately before via `SET @uptime = (SELECT VARIABLE_VALUE FROM {global_status_table} WHERE VARIABLE_NAME='UPTIME')` — `UPTIME_SUBQUERY`, `statement_samples.py:118-126` + `_get_new_events_statements_current` `:350-354`.
- `{global_status_table}` resolved by version: `performance_schema.global_status` (MySQL ≥5.7) else `information_schema.global_status` (MariaDB / <5.7) — `_read_version_info`, `:285-291`.

### 2.3 Run loop — `_collect_statement_samples`, `statement_samples.py:627-676`
1. `_read_version_info()`.
2. `_get_sample_collection_strategy()` (see 2.4) → `(table, collection_interval)`; resets the rate limit to `1/collection_interval`.
3. `_get_new_events_statements_current()` → rows.
4. `_filter_valid_statement_rows()` — drop rows that are falsy / truncated / missing sql_text (`:373-383`).
5. `_collect_plans_for_statements()` → yields plan events.
6. Each event → `database_monitoring_query_sample(json)`.

### 2.4 Collection strategy + preflight — `_get_sample_collection_strategy`, `statement_samples.py:545-622`
- `_get_enabled_performance_schema_consumers()` runs `ENABLED_STATEMENTS_CONSUMERS_QUERY` (`:128-138`): `SELECT name FROM performance_schema.setup_consumers WHERE enabled='YES' AND name LIKE 'events_statements_%' AND name != 'events_statements_cpu'`.
- If <3 consumers enabled, calls `_enable_events_statements_consumers()` → `CALL datadog.enable_events_statements_consumers()` (`:530-543`, name from `events_statements_enable_procedure`), then re-reads.
- If none enabled: records warning `events_statements_consumer_missing`, emits `dd.mysql.query_samples.error{error:no-enabled-events-statements-consumers}`, returns `(None, None)`.
- `_is_time_instrumentation_enabled()` runs `EVENTS_STATEMENTS_TIME_INSTRUMENTATION_QUERY` (`:140-150`): `SELECT COUNT(*) FROM performance_schema.setup_instruments WHERE name LIKE 'statement/%' AND enabled='YES' AND timed='YES'`. If 0 → warning `events_statements_time_instrumentation_not_enabled`, error metric, returns `(None,None)`.
- Strategy cached in `_collection_strategy_cache` (TTLCache, maxsize 1000, ttl 300) under key `"events_statements_strategy"`. The table is always `events_statements_current` (`EVENTS_STATEMENTS_TABLE`, `:44`); default interval map `:49-53` = current:1, history:10, history_long:10.

### 2.5 Plan collection per statement — `_collect_plan_for_statement`, `statement_samples.py:385-491`
- Obfuscate both `sql_text` and `digest_text`:
  - `apm_resource_hash = compute_sql_signature(obfuscated sql_text)`
  - `query_signature   = compute_sql_signature(obfuscated digest_text)`
- Rate-limit explain per `(current_schema, query_signature)` via `_explained_statements_ratelimiter` (RateLimitingTTLCache, maxsize `explained_queries_cache_maxsize`=5000, ttl `= 45*60 / explained_queries_per_hour_per_query`, default 60/hr).
- `_explain_statement(...)` (see 2.6) → raw plan or list of error states.
- Plan obfuscation: `datadog_agent.obfuscate_sql_exec_plan(plan, normalize=True)` → normalized; `obfuscate_sql_exec_plan(plan)` → obfuscated; `plan_signature = compute_exec_plan_signature(normalized_plan)`.
- Rate-limit emission per `((schema, query_signature), plan_signature)` via `_seen_samples_ratelimiter` (RateLimitingTTLCache, maxsize `seen_samples_cache_maxsize`=10000, ttl `= 3600 / samples_per_hour_per_query`, default 15/hr).
- `_has_sampled_since_completion` dedup: if `end_event_id` set (query finished) and the computed end-time is older than the ratelimiter window, skip re-emitting (`:880-892`).

### 2.6 Explain strategies — `_explain_statement`, `statement_samples.py:678-810`
Three strategies (`_explain_strategies`, `:248-252`), preferred order `['PROCEDURE','FQ_PROCEDURE','STATEMENT']` (`:253`):
- **PROCEDURE** — `CALL explain_statement(%s)` (proc name `explain_procedure`, default `explain_statement`); requires `USE \`schema\`` first. `:824-850`.
- **FQ_PROCEDURE** — `CALL datadog.explain_statement(%s)` (`fully_qualified_explain_procedure`, default `datadog.explain_statement`). `:852-878`.
- **STATEMENT** — `EXPLAIN FORMAT=json <statement>`. `:812-822`.
- Optimal strategy = `PROCEDURE` if there's a default schema on the statement, else `FQ_PROCEDURE` (`:736`).
- Only these verbs are explainable: `SUPPORTED_EXPLAIN_STATEMENTS = {select, table, delete, insert, replace, update, with}` (`:42`, `_can_explain` `:894-896`).
- Truncated queries (sql_text ends with `...`) are not explained → error `query_truncated` (`:686-692`).
- `_use_schema` runs `USE \`schema\`` (`:302-327`); permission errors cached.
- Caching: successful strategy cached per-schema in `_collection_strategy_cache`; per-query error states cached in `_explain_error_states_cache` (TTLCache maxsize 5000, ttl `explain_errors_cache_ttl`=7200s) but only when the optimal strategy is already known-good for the schema.

### 2.7 DBExplainErrorCode enum — `statement_samples.py:175-196`
`database_error`, `failed_function`, `invalid_schema`, `no_plans_possible`, `use_schema_error`, `query_truncated`. `ExplainState = (strategy, error_code, error_message)`.

### 2.8 Plan event payload (track `dbm-samples`, `dbm_type='plan'`) — `statement_samples.py:458-491`
```python
{
  "timestamp": ms, "dbm_type": "plan", "host": reported_hostname, "ddagentversion": ...,
  "ddsource": "mysql", "ddtags": tags_str,
  "duration": row['timer_wait_ns'],
  "network": {"client": {"ip": row.get('processlist_host')}},
  "cloud_metadata": ..., "service": ...,
  "db": {
    "instance": current_schema,
    "plan": {"definition": obfuscated_plan, "signature": plan_signature,
             "collection_errors": [{"strategy","code","message"}] or None},
    "query_signature": query_signature,
    "resource_hash": apm_resource_hash,
    "statement": obfuscated_statement,
    "metadata": {"tables","commands","comments"},
    "query_truncated": get_truncation_state(sql_text).value     # 'truncated'|'not_truncated'
  },
  "mysql": {k:v for row excluding EVENTS_STATEMENTS_SAMPLE_EXCLUDE_KEYS}
}
```
`EVENTS_STATEMENTS_SAMPLE_EXCLUDE_KEYS` (`:57-72`): `sql_text, current_schema, digest_text, end_event_id, uptime, now, timer_end, max_timer_wait_ns, timer_start, processlist_host`. So `mysql.{...}` carries the per-row stats (rows_examined, sort_*, select_*, no_index_used, processlist_user/db, timer_wait_ns, lock_time_ns, etc.).

### 2.9 Error/debug metrics emitted by samples job
`dd.mysql.get_new_events_statements.time` (histogram), `.rows` (histogram) `:361-369`; `dd.mysql.run_explain.time` (histogram, tag `strategy:`) `:773-778`; `dd.mysql.collect_statement_samples.time` (histogram) `:647`; `dd.mysql.collect_statement_samples.events_submitted.count` (count) `:653`; `dd.mysql.collect_statement_samples.seen_samples_cache.len` / `.explained_statements_cache.len` / `.collection_strategy_cache.len` (gauges) `:659-676`; `dd.mysql.query_samples.error` (count, many error: tags); `dd.mysql.db.error` (count) `:338`.

### 2.10 Config (under `query_samples:`) — `config.py:53` (`statement_samples_config`)
| key | default | code |
|---|---|---|
| `enabled` | `true` | `:219` |
| `collection_interval` | `1` (s) | `:212-214` |
| `run_sync` | `false` | `:218` |
| `explained_queries_per_hour_per_query` | `60` | `:266` |
| `samples_per_hour_per_query` | `15` | `:282` |
| `explained_queries_cache_maxsize` | `5000` | `:265` |
| `seen_samples_cache_maxsize` | `10000` | `:281` |
| `explain_errors_cache_maxsize` | `5000` | `:272` |
| `explain_errors_cache_ttl` | `7200` | `:274` |
| `collection_strategy_cache_maxsize` | `1000` | `:259` |
| `collection_strategy_cache_ttl` | `300` | `:260` |
| `events_statements_row_limit` | `5000` | `:236` |
| `explain_procedure` | `explain_statement` | `:238` |
| `fully_qualified_explain_procedure` | `datadog.explain_statement` | `:239` |
| `events_statements_temp_table_name` | `datadog.temp_events` | `:242` |
| `events_statements_enable_procedure` | `datadog.enable_events_statements_consumers` | `:245` |

---

## 3. ACTIVITY — `activity.py` (`MySQLActivity`)  — the analog of `pg_stat_activity`

### 3.1 Source of truth
Built around **`performance_schema.threads`** (the active session list), LEFT JOIN:
- `performance_schema.events_waits_current` (current wait event per thread — the wait-event dimension),
- `performance_schema.events_statements_current` (current SQL per thread).
Optionally LEFT JOINs lock tables to detect blocking (see 3.4). Db2 analog: `MON_GET_ACTIVITY` / `WLM_GET_SERVICE_CLASS_AGENTS` / `MON_GET_AGENT` + `SYSIBMADM.MON_LOCKWAITS` for blocking.

### 3.2 Base activity SQL — `ACTIVITY_QUERY`, `activity.py:29-89`
Selects per active thread:
- `thread_id, processlist_id, processlist_user, processlist_host, processlist_db, processlist_command, processlist_state`
- `COALESCE(statement.sql_text, thread_a.PROCESSLIST_info) AS sql_text`
- `statement.digest_text, statement.timer_start AS event_timer_start, statement.timer_end AS event_timer_end, statement.lock_time, statement.current_schema`
- `waits_a.event_id, waits_a.end_event_id`
- **wait_event** (computed): `'other'` if no wait row; else `'User sleep'` if processlist_state='User sleep'; else `'CPU'` if `event_id = end_event_id` (wait finished); else `waits_a.event_name`; default `'CPU'`. (`:46-52`)
- `waits_a.operation, wait_timer_start, wait_timer_end, object_schema, object_name, index_name, object_type, source`
- optional `{blocking_columns}`.

FROM/JOIN (`:62-66`): `threads thread_a` LEFT JOIN `events_waits_current waits_a` ON thread_id LEFT JOIN `events_statements_current statement` ON thread_id `{blocking_joins}`.

WHERE (`:67-88`) — keep only "active" sessions:
- `processlist_state IS NOT NULL`
- `processlist_id != CONNECTION_ID()` (exclude the agent's own connection)
- `PROCESSLIST_COMMAND != 'Daemon'` and `!= 'Sleep'`
- `(waits_a.EVENT_NAME != 'idle' OR NULL)` and `(waits_a.operation != 'idle' OR NULL)`
- take only the wait row with the max EVENT_ID per thread (most recent wait) — correlated subquery `:77-83`
- `COALESCE(statement.sql_text, PROCESSLIST_info) != ''`
- `{idle_blockers_subquery}` (OR-clause to also include idle sessions that are blocking others)

### 3.3 Run loop — `_collect_activity`, `activity.py:246-261`
`_get_activity(cursor)` → `_normalize_rows(rows)` → `_create_activity_event(rows, tags)` → `database_monitoring_query_activity(payload)`. Emits histogram `dd.mysql.activity.collect_activity.payload_size`.

### 3.4 Blocking-query detection (version-specific) — `_get_activity_query`, `activity.py:267-287`
Only if `query_activity.collect_blocking_queries=true` (`_should_collect_blocking_queries`, `:263-265`).
- **MySQL 8.0 (non-MariaDB)** — `BLOCKING_*_MYSQL8` (`:91-139`): uses `performance_schema.data_lock_waits` + `performance_schema.metadata_locks` (MDL). Adds columns `blocking_thread_id`, `blocking_processlist_id`, `mdl_object_type/schema/name`, `mdl_waiting_lock_type`, `mdl_blocking_lock_type`. Idle-blocker subquery includes threads in `data_lock_waits.blocking_thread_id` or MDL granted owners.
- **MySQL 5.7 / older / MariaDB** — `BLOCKING_*_MYSQL7` (`:141-162`): uses `information_schema.INNODB_TRX` + `INNODB_LOCK_WAITS`. Adds `blocking_thread_id`, `blocking_processlist_id`.

### 3.5 Version detection — `_check_version`, `activity.py:237-244`
`MySQLVersion.VERSION_80 / VERSION_57 / VERSION_56` via `version.version_compatible((8,))` etc.

### 3.6 Preflight: events_waits_current must be enabled — `run_job`, `activity.py:211-235`
- Reads `check.events_wait_current_enabled` (computed in `mysql.py:337-363` by `SELECT NAME, ENABLED FROM performance_schema.setup_consumers WHERE NAME='events_waits_current'`; also requires `performance_schema_enabled`).
- If `False` (and Azure deployment != `flexible_server`): records warning `events_waits_current_not_enabled` and returns.
- If still `None` (not yet determined): skips this run.

### 3.7 Normalization — `_normalize_rows`, `activity.py:297-388`
- Sort rows by `event_timer_start` (picoseconds; default to now if NULL) — `_sort_key` `:338-342`.
- Dedup multiple statement rows per thread, keeping the most recent (`seen`/`second_pass`/`_eliminate_duplicate_rows`) — `:304-336`.
- `query_truncated` = `get_truncation_state(sql_text).value`.
- `_sanitize_row` drops keys with `None` values (`:363-366`).
- `_obfuscate_and_sanitize_row` obfuscates `sql_text` → `row['sql_text']`; computes `query_signature` from `digest_text` if present else from `sql_text` (MySQL <8.0 sometimes NULL digest_text) — `_finalize_row` `:368-383`; on failure sets `sql_text="ERROR: failed to obfuscate"`.
- Adds `dd_commands`, `dd_tables`, `dd_comments` from metadata.
- **Payload cap**: stop appending rows once estimated size (`len(str(row))`) exceeds `MAX_PAYLOAD_BYTES = 19e6` (`:317-319, 385-388`).

### 3.8 Activity payload (track `dbm-activity`) — `_create_activity_event`, `activity.py:390-403`
```python
{
  "host": reported_hostname, "ddagentversion": ..., "ddsource": "mysql",
  "dbm_type": "activity",
  "collection_interval": self.collection_interval,   # default 10
  "ddtags": tags,                                     # list; dd.internal* stripped
  "timestamp": ms, "cloud_metadata": ..., "service": ...,
  "mysql_activity": active_sessions                   # list of normalized rows
}
```
Custom JSON encoder `_json_event_encoding` (`:405-415`): Decimal→float, date/datetime→isoformat, timedelta→int seconds.

### 3.9 Config (under `query_activity:`) — `config.py:56` (`activity_config`)
| key | default | code |
|---|---|---|
| `enabled` | `true` | `:191` |
| `collection_interval` | `10` (s) (`DEFAULT_COLLECTION_INTERVAL`) | `:179, 183-187` |
| `run_sync` | `false` | `:190` |
| `collect_blocking_queries` | `false` | `:265` |

---

## 4. METADATA / SETTINGS — `metadata.py` (`MySQLMetadata`)

This one job handles BOTH (a) global variables ("settings") and (b) schema collection (delegated to `DatabasesData`).

### 4.1 Scheduling — `metadata.py:50-90, 138-159`
- `_settings_enabled = collect_settings.enabled` (default `true`, `:55`). `_settings_collection_interval = collect_settings.collection_interval` (default `600`s, `DEFAULT_SETTINGS_COLLECTION_INTERVAL`, `:29, 57-59`).
- `_databases_data_enabled = collect_schemas.enabled` (default `false`, `:51`). `_databases_data_collection_interval = collect_schemas.collection_interval` (default `600`s, `:52-54`).
- Job `collection_interval` = min of the two enabled intervals; `enabled` = either feature enabled (`:61-68`).
- `run_job` (`:138-159`) gates each sub-task by its own elapsed-time vs its own interval (the job rate-limit only governs wakeups; the elapsed-time check enforces each feature's cadence). Errors are caught/logged, not fatal.
- `run_sync` from `collect_settings.run_sync` (default false, `:73`).
- Uses a dedicated `get_db_connection()` that calls `ping()` (auto-reconnect) because this job runs infrequently and idle connections can be dropped (`:92-111`).

### 4.2 Settings ("mysql_variables") — `report_mysql_metadata`, `metadata.py:164-193`
Table selection (`:167-171`): `performance_schema.global_variables` (MySQL ≥5.7, non-MariaDB) else `information_schema.GLOBAL_VARIABLES` (MariaDB / <5.7) — `MYSQL_TABLE_NAME` / `MARIADB_TABLE_NAME`, `:31-32`.
```sql
SELECT variable_name, variable_value FROM {table_name}     -- SETTINGS_QUERY :34-40
```
Payload (track `dbm-metadata`, `kind='mysql_variables'`):
```python
{
  "host": reported_hostname,
  "database_instance": check.database_identifier,
  "agent_version": ..., "dbms": "mysql", "kind": "mysql_variables",
  "collection_interval": self.collection_interval,
  "dbms_version": version.version + '+' + version.build,
  "tags": self._tags, "timestamp": ms, "cloud_metadata": ...,
  "metadata": [ {variable_name, variable_value}, ... ]      # list of dicts
}
```
This is the MySQL analog of Postgres `pg_settings`. Db2 analog: `SYSIBMADM.DBMCFG` (instance-level) + `SYSIBMADM.DBCFG` (db-level) + `SYSIBM.SYSVARIABLES`/registry.

---

## 5. SCHEMA / DATABASES COLLECTION — `databases_data.py` (`DatabasesData`) + `queries.py`

Driven by `MySQLMetadata.run_job` when `collect_schemas.enabled=true` (default off). Disabled by default. Submits via track `dbm-metadata` with `kind='mysql_databases'`.

### 5.1 Entry — `collect_databases_data(tags)`, `databases_data.py:185-268`
1. Reset `SubmitData` accumulator.
2. `_query_db_information(cursor)` → list of databases (`SQL_DATABASES`).
3. `store_db_infos(db_infos)`.
4. `_fetch_for_databases(db_infos, cursor)` → per-db tables/columns/etc.
5. `_data_submitter.submit()`.

### 5.2 Database list — `SQL_DATABASES`, `queries.py:93-98`
```sql
SELECT schema_name AS name, default_character_set_name, default_collation_name
FROM information_schema.SCHEMATA
WHERE schema_name NOT IN ('sys','mysql','performance_schema','information_schema')
```

### 5.3 Per-database fetch — `_fetch_database_data`, `databases_data.py:165-183`
- `_get_tables(db_name)` → `SQL_TABLES` (`queries.py:100-107`): `SELECT table_name AS name, engine, row_format, create_time FROM information_schema.TABLES WHERE TABLE_SCHEMA=%s AND TABLE_TYPE='BASE TABLE'`.
- Chunk tables by `TABLES_CHUNK_SIZE=500` (`:119`).
- For each chunk: if elapsed > `max_execution_time` (`min(collect_schemas.max_execution_time default 60, collection_interval)`, `:143-145`), submit what we have + a truncated message and raise `StopIteration` (`:169-178`).
- `_get_tables_data(chunk, db_name)` populates columns, partitions, foreign keys, indexes.
- If accumulated columns since last submit > `MAX_COLUMNS_PER_EVENT=100_000` (`:121, 181-182`) → submit early.

### 5.4 Columns — `_populate_with_columns_data` + `SQL_COLUMNS`, `databases_data.py:339-362`, `queries.py:109-120`
```sql
SELECT table_name, column_name AS name, column_type, column_default AS `default`,
       is_nullable AS nullable, ordinal_position, column_key, extra
FROM INFORMATION_SCHEMA.COLUMNS
WHERE table_schema=%s AND table_name IN ({placeholders})
```
`nullable` 'YES'/'NO' → bool; `default` → str.

### 5.5 Indexes — `_populate_with_index_data` + `get_indexes_query`, `databases_data.py:364-404`, `queries.py:122-156, 300-309`
Two variants: `SQL_INDEXES_8_0_13` (adds `expression` for functional indexes, MySQL ≥8.0.13 non-MariaDB) else `SQL_INDEXES` (`expression` = NULL). Source `INFORMATION_SCHEMA.STATISTICS`; columns: `index_name AS name, collation, cardinality, index_type, seq_in_index, column_name, sub_part, packed, nullable, non_unique, expression`. Aggregated per-(table,index) with nested `columns[]`. Cardinality NULL → 0 (in-memory BTREE bug ref).

### 5.6 Foreign keys — `_populate_with_foreign_keys_data` + `SQL_FOREIGN_KEYS`, `databases_data.py:406-415`, `queries.py:158-186`
From `INFORMATION_SCHEMA.KEY_COLUMN_USAGE kcu` LEFT JOIN `REFERENTIAL_CONSTRAINTS rc`; `GROUP_CONCAT` column names; emits `constraint_schema, name, table_name, column_names, referenced_table_schema, referenced_table_name, referenced_column_names, update_action, delete_action`.

### 5.7 Partitions — `_populate_with_partitions_data` + `SQL_PARTITION`, `databases_data.py:417-462`, `queries.py:188-205`
From `INFORMATION_SCHEMA.PARTITIONS WHERE table_schema=%s AND table_name IN ({}) AND partition_name IS NOT NULL`; aggregates partition + nested subpartitions, summing `table_rows`/`data_length`.

### 5.8 Payload shape (`kind='mysql_databases'`) — `SubmitData`, `databases_data.py:33-111`
Base event (`:131-140`): `{host, agent_version, dbms:'mysql', kind:'mysql_databases', collection_interval, dbms_version, tags, cloud_metadata, flavor, database_instance}`. `submit()` adds `metadata=[ {db_info..., "tables":[...]} ]` and `timestamp`. Truncation events carry `collection_errors=[{error_type:'truncated', message}]` (`:81-97`). Nested structure (db → tables → columns/indexes/foreign_keys/partitions) documented in the docstring at `databases_data.py:185-248`.

### 5.9 Config (under `collect_schemas:` / legacy `schemas_collection:`) — `config.py:58` (`schemas_config`)
| key | default | code |
|---|---|---|
| `enabled` | `false` | `metadata.py:51` |
| `collection_interval` | `600` (s) | `metadata.py:52-54` / `databases_data.py:30` |
| `max_execution_time` | `60` (s), capped at `collection_interval` | `databases_data.py:143-145` |

### 5.10 Config (under `collect_settings:`) — `config.py:55` (`settings_config`)
| key | default | code |
|---|---|---|
| `enabled` | `true` | `metadata.py:55` |
| `collection_interval` | `600` (s) | `metadata.py:57-59` |
| `run_sync` | `false` | `metadata.py:73` |

---

## 6. Cross-cutting details for the Db2 implementation

### 6.1 Obfuscation & signatures (shared)
- `obfuscate_sql_with_metadata(sql, obfuscator_options_json)` → `{'query': <obfuscated>, 'metadata': {'tables','commands','comments'}}`.
- `compute_sql_signature(obfuscated_query)` → `query_signature` (stable hash; matches metrics ↔ samples ↔ activity ↔ FQT).
- `compute_exec_plan_signature(normalized_plan)` → `plan_signature`.
- `datadog_agent.obfuscate_sql_exec_plan(plan, normalize=True|False)` for plans.
- Obfuscator options assembled in `config.py:76-106` from `obfuscator_options:` (dbms forced to `'mysql'`; `return_json_metadata`, `table_names`, `collect_commands`, `collect_comments`, `obfuscation_mode='obfuscate_and_normalize'`, etc.). For Db2 set `'dbms': 'db2'`.

### 6.2 Truncation — `util.py:36-49`
MySQL marks truncated `performance_schema` SQL text with a trailing `...`. `get_truncation_state` returns enum `truncated` / `not_truncated` (`.value` shipped in payloads). Db2: SQL text in `MON_GET_PKG_CACHE_STMT.STMT_TEXT` has a finite length too — define an analogous detection.

### 6.3 DatabaseConfigurationError warnings (`util.py`)
Codes referenced: `performance_schema_not_enabled`, `events_statements_consumer_missing`, `events_statements_time_instrumentation_not_enabled`, `events_waits_current_not_enabled`, `explain_plan_procedure_missing`, `explain_plan_fq_procedure_missing`. Surfaced via `check.record_warning(code, warning_with_tags(...))`. For Db2, define equivalent preflight checks (e.g. `MON_*` monitoring switches / `DFT_MON_*` dbm cfg must be ON).

### 6.4 Connections
Each job lazily opens its own pymysql connection via `connection_args_provider()` and `connect_with_session_variables(...)`. Metadata uses `ping()` to auto-reconnect. `ManagedAuthConnectionMixin` handles AWS IAM token refresh (reconnect when token age exceeds threshold). For Db2 (ibm_db), mirror: one dedicated connection per async job, closed on shutdown.

### 6.5 Tags
`dbm_tags` passed to `run_job_loop`. Jobs strip `dd.internal*` tags before putting them in DBM payloads (`statements.py:156`, `activity.py:250`). FQT events append `schema:<schema_name>`.

### 6.6 Units summary (important for Db2 mapping)
- `events_statements_summary_by_digest.sum_timer_wait` / `sum_lock_time` — **picoseconds** (shipped raw in metrics payload).
- `events_statements_current.timer_wait` / `lock_time` — picoseconds; divided by 1000 in the sample query → **nanoseconds** (`timer_wait_ns`, `lock_time_ns`).
- `events_waits_current.timer_*` — picoseconds.
- Db2 `MON_GET_*` timings are typically **milliseconds** (`TOTAL_*_TIME`) — conversion will differ; do NOT copy MySQL's picosecond math.
