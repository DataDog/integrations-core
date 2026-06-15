# Shared DBM Framework — Code-Base Reference

Raw input for the Db2 (target version 12.1; live container 12.1.4) fidelity implementation plan.
All code findings are from the `datadog_checks_base` shared library and three reference integrations
(`sqlserver`, `postgres`, `mysql`) in `/home/bits/dd/integrations-core`.

The shared DBM framework lives in `datadog_checks_base/datadog_checks/base/utils/db/`. There is **no
single "DBM check" base class** — each integration assembles the pieces below. The pieces split into
two largely independent halves:

1. **Plain metrics collection** — `QueryManager`/`QueryExecutor` + `Query` + `transform.py` column/extra
   transformers. This is the `custom_queries`-style declarative query→metric engine. The current
   `ibm_db2` check does **not** use it (it hand-rolls metric submission in `ibm_db2.py`), but it is the
   recommended path for declarative metric collection.
2. **DBM async features** — `DBMAsyncJob` background threads that emit *event-platform* payloads
   (`dbm-metrics`, `dbm-samples`, `dbm-activity`, `dbm-metadata`, `dbm-health`) plus the `StatementMetrics`
   delta engine, SQL obfuscation/signature helpers, and the `SchemaCollector` base.

---

## Part A — Files and their roles

| File | Role |
|---|---|
| `utils/db/query.py` | `Query` — one declarative query spec (name/query/columns/extras/tags/collection_interval). Validation + compilation. |
| `utils/db/core.py` | `QueryExecutor` (low-level, multi-instance) and `QueryManager` (per-check). Runs queries, applies transformers, submits metrics. |
| `utils/db/transform.py` | Column transformers (`gauge`, `count`, `tag`, etc.) and extra transformers (`expression`, `percent`, `log`). Defines `COLUMN_TRANSFORMERS` / `EXTRA_TRANSFORMERS`. |
| `utils/db/statement_metrics.py` | `StatementMetrics` — first-derivative (delta) engine over monotonic stat tables, with row-merge and stats-reset handling. |
| `utils/db/sql.py` | `compute_sql_signature`, `compute_exec_plan_signature`, `normalize_query_tag`. mmh3 64-bit hex hashing. |
| `utils/db/sql_commenter.py` | `generate_sql_comment`, `add_sql_comment` — SQLCommenter-style comment propagation onto outgoing SQL. |
| `utils/db/schemas.py` | `SchemaCollector` (ABC), `SchemaCollectorConfig`, `DatabaseInfo`/`DatabaseObject` TypedDicts. Emits `dbm-metadata` schema payloads. |
| `utils/db/utils.py` | `DBMAsyncJob` (the background-thread base), `obfuscate_sql_with_metadata`, `default_json_event_encoding`, `ConstantRateLimiter`, `RateLimitingTTLCache`, `TagManager`, `resolve_db_host`, `tracked_query`, `now_ms`. |
| `utils/db/health.py` | `Health`, `HealthEvent`, `HealthStatus` — `dbm-health` event submission with cooldown. |
| `utils/db/types.py` | Type aliases: `Transformer`, `TransformerFactory`, `QueriesExecutor`, `QueriesSubmitter`. |
| `utils/db/timed_cache.py` | (TTL cache helper — not central to DBM.) |
| `checks/db.py` | `DatabaseCheck(AgentCheck)` — abstract base exposing `database_monitoring_*` submitters + the required `reported_hostname`/`database_identifier`/`dbms`/`dbms_version`/`tags`/`cloud_metadata` properties used by `SchemaCollector` and DBM events. |
| `checks/base.py` (lines 772-798) | The concrete `AgentCheck.database_monitoring_query_sample/metrics/activity/metadata` implementations that call `aggregator.submit_event_platform_event(...)`. |
| `utils/tracking.py` | `tracked_method` decorator — debug timing/error/result-length metrics for DBM methods. |

---

## Part B — Plain metrics: `QueryManager` / `Query` / transformers

### B.1 `Query` spec (`utils/db/query.py`)

A `Query` is built from a single dict (`query_data`). Fields (from the docstring, `query.py:24-50`):

- `name` (str, **required**) — query name; used in error messages and as namespace.
- `query` (str, **required**) — the SQL to run. May contain `{}`-style format placeholders the integration fills before constructing the `Query`.
- `columns` (List[dict], **required**) — one entry per result column, in order. Each: `name` (str), `type` (str), plus type-specific modifier keys. A falsy entry (`None`/`{}`) means "ignore this column". `type: 'source'` means "collect value for reference but do not submit".
- `extras` (List[dict], optional) — post-processing transformers computed from already-collected column values (`expression`, `percent`, `log`, or any submission transformer with a `source`).
- `tags` (List[str], optional) — base tags applied to every submission from the query.
- `collection_interval` (int seconds, optional) — per-query throttle. See `should_execute()` semantics (`query.py:265-283`): if `None`, runs every check; if set, runs only when `now - last_execution >= interval`. It does NOT run exactly on the interval — it runs on the next check tick after the interval elapses.
- `metric_prefix` (str, optional) — when set, `metric_name_raw=True` and the prefix is prepended to non-tag column names; the agent's namespace prefix (`<integration>.`) is then NOT applied (submitted with `raw=True`).
- `params` (Sequence, optional) — bound parameters forwarded as `cursor.execute(query, params)` (`core.py:166`).

Compilation (`Query.compile`, `query.py:72-263`) is idempotent and called by `QueryManager.compile_queries`. It validates everything, builds `column_transformers` and `extra_transformers` tuples, and is where unknown column `type`s raise `unknown type`. Tag column types are `tag`, `tag_list`, `tag_not_null`.

### B.2 `QueryManager` (`utils/db/core.py`)

Typical wiring (from `core.py:181-202` docstring):

```python
self._query_manager = QueryManager(
    self,                       # the AgentCheck
    self.execute_query,         # callable(query[, params]) -> iterable of row tuples
    queries=[queries.Q1, queries.Q2, ...],
    tags=self.instance.get('tags', []),
    error_handler=self._error_sanitizer,
    hostname=...,               # optional, attaches to every submission
)
self.check_initializations.append(self._query_manager.compile_queries)
```

- `QueryManager` is a subclass of `QueryExecutor` where `submitter=check`. It additionally merges `custom_queries` / `global_custom_queries` from instance/init_config (`core.py:236-258`) and honors `only_custom_queries`, `use_global_custom_queries` (incl. `'extend'`).
- The **executor** is a callable accepting the query string (and optional `params`) returning an iterable of row sequences. `execute_query` triggers execution immediately to surface errors (`core.py:161-178`).
- `execute(extra_tags=None)` runs each query that `should_execute()`, validates row width (`_is_row_valid`, `core.py:143-159`), and for each row maps column values → transformers → `AgentCheck` submission methods, then runs extras (`core.py:63-141`).
- The submitter must implement all `SUBMISSION_METHODS` (`utils.py:32-44`); `QueryManager` passes `check` which satisfies this. Missing methods raise at construction (`core.py:38-42`).

### B.3 Transformers (`utils/db/transform.py`)

**`COLUMN_TRANSFORMERS`** registry (`transform.py:607-616`) plus the submission methods injected at compile time:

Submission column types (mapped from `AgentCheck` methods, `utils.py:32-44`, injected by `QueryExecutor.compile_queries` `core.py:53-58`):
`gauge`, `count`, `monotonic_count`, `rate`, `histogram`, `historate`, `service_check` (custom), `send_log` (custom), and `metadata` (→ `set_metadata`).

Built-in transform types:
- `tag` (`get_tag`, `transform.py:99`) — value → `column_name:value` tag on all subsequent submissions in the row; supports `boolean: true` modifier.
- `tag_not_null` — same as `tag` but only when value is not None (`core.py:122-124`).
- `tag_list` (`get_tag_list`, `transform.py:124`) — comma-separated string or list → multiple `column_name:v` tags.
- `monotonic_gauge` (`transform.py:147`) — emits `<name>.total` gauge AND `<name>.count` monotonic_count.
- `temporal_percent` (`transform.py:163`) — value treated as cumulative time in `scale` units (`second|millisecond|microsecond|nanosecond` or int parts-per-second); submitted as a `rate` of percent-of-wall-time.
- `time_elapsed` (`transform.py:330`) — seconds since a past timestamp as a `gauge`; `format: native|unix_time|<strptime>`.
- `match` (`transform.py:207`) — key/value EAV-style routing of a `metric`/`value` pair to per-key transformers via `items`.
- `service_check` (`transform.py:293`) — `status_map` value→status, optional `message` template.

**`EXTRA_TRANSFORMERS`** (`transform.py:618-622`), computed after columns from collected `sources`:
- `expression` (`transform.py:392`) — safe restricted-AST Python expression over source names; optional `submit_type`. Allowed builtins: `abs,all,any,bool,divmod,float,int,len,max,min,pow,str,sum` (`transform.py:23-29`). AST whitelist at `transform.py:35-83`.
- `percent` (`transform.py:501`) — `part`/`total` → gauge of `part/total*100` (0 when total is 0).
- `log` (`transform.py:555`) — emits a log via `send_log` using an `attributes` map of source columns.

**Relevance to Db2:** the current `ibm_db2.py` does NOT use `QueryManager`; it submits gauges directly. For new declarative metrics the `Query`/`QueryManager` engine is available, but the existing pattern (hand-rolled `self.gauge(...)`) is also acceptable. The transformer list above is the full vocabulary if going declarative.

---

## Part C — `StatementMetrics` delta engine (`utils/db/statement_metrics.py`)

This is the core of **query metrics** for every DBMS. Statement stat tables (Postgres `pg_stat_statements`,
MySQL `events_statements_summary_by_digest`, SQL Server `sys.dm_exec_query_stats`) are monotonically
increasing; the framework computes per-interval deltas.

API:

```python
StatementMetrics()                       # holds self._previous_statements cache
.compute_derivative_rows(rows, metrics, key, execution_indicators=None) -> List[dict]
```

Semantics (`statement_metrics.py:25-123`):
- `rows`: current-run list of dict rows.
- `metrics`: list of column names to diff (the monotonic counters). All others are passed through unchanged.
- `key`: callable `row -> hashable` uniquely identifying a statement across runs (the row-identity tuple).
- `execution_indicators` (optional): columns that must have increased (>0) for the row to be emitted. Filters phantom rows where a normalized query was evicted then re-inserted with the same call count. Examples cited in code: Postgres `calls`, MySQL `exec_count`, SQL Server `execution_count` (`statement_metrics.py:42-49`).
- Duplicate rows (same `key` after agent normalization) are **summed** first (`_merge_duplicate_rows`, `statement_metrics.py:126-150`).
- **Stats-reset handling:** if ANY diffed metric goes negative for a row, the entire row is dropped (treated as a counter reset / new baseline). Rows with zero total change are dropped.
- The function mutates the cache in place and **must be called exactly once per collection run**.

**Reference usage (SQL Server, `sqlserver/statements.py:483-490`):**
```python
metric_columns = [c for c in rows[0].keys() if c.startswith("total_") or c == 'execution_count']
rows = self._state.compute_derivative_rows(rows, metric_columns, key=_row_key)
```
with `_row_key = (database_name, query_signature, query_hash, procedure_name)` (`statements.py:208-213`).

**For Db2:** the natural monotonic source is `MON_GET_PKG_CACHE_STMT` (package cache statement metrics:
`NUM_EXECUTIONS`, `TOTAL_CPU_TIME`, `TOTAL_ACT_TIME`, `ROWS_READ`, `ROWS_RETURNED`, `TOTAL_SORTS`, etc.,
keyed by `EXECUTABLE_ID`/`STMT_TEXT`). The key would be `(query_signature, EXECUTABLE_ID)` (or include
schema). `execution_indicators=['num_executions']`.

---

## Part D — SQL obfuscation, signatures, comment propagation

### D.1 `obfuscate_sql_with_metadata` (`utils/db/utils.py:249-286`)

```python
obfuscate_sql_with_metadata(query, options=None, replace_null_character=False) -> dict
# returns {'query': <obfuscated str>, 'metadata': {'tables': [...]|None, 'commands': [...], 'comments': [...], 'procedures': [...]}}
```
- Calls `datadog_agent.obfuscate_sql(query, options)` (Go obfuscator in the Agent). `options` is a **JSON string** of obfuscator options.
- `replace_null_character=True` strips `\x00` before obfuscation — set this when the DB allows embedded nulls in text (SQL Server does so; **enable for Db2** to be safe with CLOB/VARCHAR text).
- Backward-compat: on Agent < 7.34 the obfuscator returns a bare string (no metadata) — handled at `utils.py:278-279`.
- `metadata.tables_csv` is split into `metadata['tables']` (`utils.py:283-285`).

### D.2 Obfuscator options dict (passed as JSON string)

Built per-integration from `instance['obfuscator_options']`. Canonical full set (SQL Server `config.py:81-122`):
```python
{
  'dbms': 'mssql',                        # OTel db.system value; for Db2 use 'db2'
  'replace_digits': <bool>,               # also accepts legacy 'quantize_sql_tables'
  'keep_sql_alias': <bool, default True>,
  'return_json_metadata': <bool, default True>,   # from 'collect_metadata'
  'table_names': <bool, default True>,            # from 'collect_tables'
  'collect_commands': <bool, default True>,
  'collect_comments': <bool, default True>,
  'collect_procedures': <bool, default True>,
  'obfuscation_mode': 'obfuscate_and_normalize',  # or 'normalize_only'
  'remove_space_between_parentheses': <bool>,
  'keep_null': <bool>, 'keep_boolean': <bool>,
  'keep_positional_parameter': <bool>, 'replace_bind_parameter': <bool>,
  'keep_trailing_semicolon': <bool>, 'keep_identifier_quotation': <bool>,
}
```
The `dbms` value (`'mssql'`, `'postgres'`, `'mysql'`) selects the Go obfuscator dialect. **Confirm the Agent
obfuscator supports `'db2'`** — if not, fall back to a generic/`'sql'` value (research item for the plan;
the Agent's `pkg/obfuscate` is the source of truth).

### D.3 Signatures (`utils/db/sql.py`)

- `compute_sql_signature(normalized_query) -> hex str` — `mmh3.hash64(bytes, signed=False)[0]` as hex (`sql.py:18-26`). **Must match the APM resource hash** — do not alter. This is the `query_signature`.
- `compute_exec_plan_signature(normalized_json_plan) -> hex str` — re-serializes JSON with sorted keys, then mmh3 hex (`sql.py:48-56`). This is the `plan` `signature`.
- `normalize_query_tag(query)` — replaces commas with Arabic Decimal Separator (U+066B) so SQL-as-tag survives the metrics backend (`sql.py:29-45`).

### D.4 SQLCommenter (`utils/db/sql_commenter.py`)

- `generate_sql_comment(**kwargs) -> "/* k='v',... */"` (keys sorted, empty values skipped) (`sql_commenter.py:4-19`).
- `add_sql_comment(sql, prepand=True, **kwargs)` — prepend (default) or append the comment, handling trailing `;` (`sql_commenter.py:22-47`).
- Used for **comment propagation** (injecting `dddbs`, `traceparent`, etc. into queries the agent itself issues, or to demonstrate trace linking). Lower priority for a metrics-first Db2 plan; relevant for trace-to-query linking later.

---

## Part E — `DBMAsyncJob` base (`utils/db/utils.py:289-499`)

The background-thread engine that every DBM feature (query metrics, samples/plans, activity, metadata) subclasses.

### E.1 Constructor parameters (`utils.py:299-346`)
```python
DBMAsyncJob(
  check,                       # the DatabaseCheck/AgentCheck instance
  config_host=None,            # DB host, resolved via resolve_db_host()
  min_collection_interval=15,  # main check interval; used for inactivity stop (×2)
  dbms="TODO",                 # e.g. "db2" — used in all dd.<dbms>.async_job.* metric names
  rate_limit=1,                # executions/sec; job loop sleeps to hold this. Usually 1/collection_interval_s
  max_sleep_chunk_s=1,
  run_sync=False,              # run inline in check() instead of background thread (tests / low intervals)
  enabled=True,
  expected_db_exceptions=(),   # exception classes treated as warnings not crashes
  shutdown_callback=None,      # e.g. close the dedicated DBM connection
  job_name=None,               # e.g. "query-metrics" — becomes job:<name> tag
  enable_missed_collection_event=True,
  features=None,               # list of feature names for health events; default [None]
)
```

### E.2 Lifecycle
- The check calls `job.run_job_loop(tags)` once per check run (`utils.py:354-408`). First call resolves `_db_hostname`, sets `_tags`/`_job_tags`, and either runs synchronously (`run_sync` or env `DBM_THREADED_JOB_RUN_SYNC=true`) or submits `self._job_loop` to a shared `ThreadPoolExecutor(100000)` (`utils.py:293`).
- `_job_loop` (`utils.py:410-471`) loops: checks `_cancel_event`; **stops if `time.time() - _last_check_run > min_collection_interval*2`** (check went inactive); runs `_run_job_rate_limited` which calls `run_job()` then sleeps to honor `rate_limit`.
- The check must call `job.cancel()` on its own `cancel()`/shutdown (`utils.py:348-352`; e.g. SQL Server `sqlserver.py:213-218`).
- **Subclasses override `run_job(self)`** (`utils.py:498-499`, raises `NotImplementedError`). This is where the feature does its work (query, obfuscate, emit events).

### E.3 Emitted health/telemetry (`raw=True`, count metrics)
- `dd.<dbms>.async_job.missed_collection` (count) + `HealthEvent.MISSED_COLLECTION` warning when an interval is missed (`utils.py:384-406`).
- `dd.<dbms>.async_job.cancel`, `dd.<dbms>.async_job.inactive_stop`, `dd.<dbms>.async_job.error` (with `error:database-<type>` / `error:crash-<type>` tag) (`utils.py:416-459`).
- On crash, `check.health.submit_exception_health_event(...)` (`utils.py:461-467`).

### E.4 Rate-limiting / dedup caches (used by feature subclasses, all from `utils.py`)
- `ConstantRateLimiter(rate_limit_s, max_sleep_chunk_s=5)` (`utils.py:106-145`) — internal job pacing.
- `RateLimitingTTLCache(maxsize, ttl)` (`utils.py:148-162`) — `.acquire(key)` returns True at most once per ttl per key, bounded by maxsize. Used for "1 plan/sample per query per hour" rate limits. Pattern: `seen_plans_ratelimiter`, `seen_samples_ratelimiter`, `raw_statement_text_cache`.
- `cachetools.TTLCache` — used for `full_statement_text_cache` (FQT dedup).

---

## Part F — DBM event submission methods and payload shapes

### F.1 Submitters (`checks/base.py:772-798`, `checks/db.py:11-24`)
All take a JSON string and forward to the event platform via `aggregator.submit_event_platform_event(self, check_id, raw, <track>)`:

| Method | Track type | Used for |
|---|---|---|
| `database_monitoring_query_metrics(raw)` | `dbm-metrics` | query metrics payload (one per run) |
| `database_monitoring_query_sample(raw)` | `dbm-samples` | FQT events, plan events, raw query/plan events |
| `database_monitoring_query_activity(raw)` | `dbm-activity` | active session snapshot |
| `database_monitoring_metadata(raw)` | `dbm-metadata` | settings + schema payloads |
| `database_monitoring_health(raw)` (db.py only) | `dbm-health` | health events |

All JSON is serialized with `json.dumps(event, default=default_json_event_encoding)` where
`default_json_event_encoding` (`utils.py:237-246`) coerces `Decimal→float`, `datetime/date→isoformat`,
`IPv4Address→str`, `bytes→utf-8`.

### F.2 Query-metrics payload (canonical, SQL Server `statements.py:505-522`; Postgres `statements.py:252-282`)
One event per collection run, top-level keys:
```json
{
  "host": "<reported_hostname>",
  "database_instance": "<database_identifier>",
  "timestamp": <epoch_ms>,
  "min_collection_interval": <seconds>,
  "tags": [ ... ],                      // tag_manager.get_tags() (db tag excluded for pg)
  "cloud_metadata": { ... },
  "kind": "query_metrics",              // sqlserver includes; pg omits
  "ddagentversion": "<x.y.z>",
  "service": "<service>",
  "<dbms>_version": "...",              // e.g. "postgres_version", "sqlserver_version"
  "<dbms>_rows": [ <per-statement metric dict>, ... ]   // "postgres_rows" / "sqlserver_rows"
}
```
Each row dict carries `query_signature`, `query_hash`, the **delta** counters, and obfuscated `text` plus
`dd_tables`/`dd_commands`/`dd_comments`. Deobfuscated `statement_text` is stripped before sending
(`_to_metrics_payload_row`, `statements.py:492-503`). **For Db2 the array key would be `db2_rows`** and
the version key `db2_version` (confirm exact naming the backend expects — this is set by the integration,
and the DBM backend keys off `dbms`).

### F.3 FQT (full query text) event — `dbm_type: "fqt"` (SQL Server `statements.py:562-595`)
Emitted once per unique query (rate-limited by `full_statement_text_cache`):
```json
{
  "timestamp": <ms>, "host": ..., "database_instance": ...,
  "ddagentversion": ..., "ddsource": "<dbms>", "ddtags": "<csv>",
  "dbm_type": "fqt", "service": ...,
  "db": {
    "instance": "<db name>",
    "query_signature": "...",
    "statement": "<obfuscated text>",
    "metadata": {"tables": [...], "commands": [...], "comments": [...]}
  },
  "<dbms>": { "query_hash": ..., "query_plan_hash": ... }   // dbms-specific block
}
```

### F.4 Plan event — `dbm_type: "plan"` (Postgres `statement_samples.py:903-942`; SQL Server `statements.py:672-710`)
```json
{
  "host": ..., "database_instance": ..., "dbm_type": "plan",
  "ddagentversion": ..., "ddsource": "<dbms>", "ddtags": "<csv>",
  "timestamp": <ms>, "cloud_metadata": {...}, "service": ...,
  "db": {
    "instance": "<db>",
    "plan": {
      "definition": "<obfuscated JSON/XML plan>",
      "signature": "<compute_exec_plan_signature(normalized_plan)>",
      "collection_errors": [{"code": "...", "message": "..."}] | null
    },
    "query_signature": "...",
    "statement": "<obfuscated text>",
    "metadata": {"tables": ..., "commands": ..., "comments": ...}
  },
  "<dbms>": { ...engine-specific (query_hash, query_plan_hash, execution_count, total_elapsed_time)... }
}
```
- Postgres obtains the plan via `EXPLAIN` (a configured `explain_function`, `statement_samples.py:736`), JSON-dumps it, then `datadog_agent.obfuscate_sql_exec_plan(raw, normalize=True/False)` for the normalized + obfuscated forms (`statement_samples.py:891-892`), then `compute_exec_plan_signature`.
- SQL Server pulls the cached XML plan and obfuscates it with `obfuscate_xml_plan` (`statements.py:234-251`).
- Plans are rate-limited per `(query_signature, plan_signature)` via `seen_samples_ratelimiter`.
- **`raw` variants:** with `collect_raw_query_statement.enabled`, integrations also emit `dbm_type: "rqt"` (raw query text) and `dbm_type: "rqp"` (raw query plan) events (`statements.py:711-719`, `activity.py:319-345`, `statement_samples.py:955-964`).
- **For Db2:** the EXPLAIN facility writes to explain tables (`EXPLAIN_STATEMENT`, `EXPLAIN_OPERATOR`, etc.) via `EXPLAIN PLAN FOR` / `db2expln` / `db2exfmt`, or `CURRENT EXPLAIN MODE`. There is no single JSON plan column; the plan tree must be assembled from explain tables and serialized to JSON before `compute_exec_plan_signature`. This is the highest-complexity DBM feature for Db2 (call out in the plan).

### F.5 Activity payload — `dbm_type: "activity"` (SQL Server `activity.py:463-505`)
```json
{
  "host": ..., "database_instance": ..., "ddagentversion": ...,
  "ddsource": "<dbms>", "dbm_type": "activity",
  "collection_interval": <s>, "ddtags": [ ... ],   // list, not csv, for activity
  "timestamp": <ms>, "cloud_metadata": {...}, "service": ...,
  "<dbms>_version": "...", "<dbms>_engine_edition": "...",
  "<dbms>_activity": [ <active session row>, ... ],
  "<dbms>_connections": [ <connection summary row>, ... ]
}
```
- Active-session rows include `now`, `query_start`, `user_name`, `id` (session id), `database_name`, `session_status`/`request_status`, obfuscated `text`, `query_signature`, `query_hash`, wait/blocking info, client address/port, host/program name, and (Db2-relevant) blocking-session linkage.
- Payload is size-capped at `MAX_PAYLOAD_BYTES = 19e6` with row dropping after sort (`activity.py:31`, `275-298`).
- **For Db2:** sources are `MON_GET_ACTIVITY` / `WLM_GET_WORKLOAD_OCCURRENCE_ACTIVITIES` / `MON_GET_CONNECTION` (+ `SYSIBMADM.MON_LOCKWAITS` / `SNAPLOCKWAIT` for blocking). Default collection interval pattern: 10s (`activity.py:30`).

### F.6 Settings/metadata payload — `dbm-metadata` (SQL Server `metadata.py:140-161`)
```json
{
  "host": ..., "database_instance": ..., "agent_version": ...,
  "dbms": "<dbms>", "kind": "<dbms>_configs",
  "collection_interval": <s>, "dbms_version": "...",
  "tags": [ ... ], "timestamp": <ms>, "cloud_metadata": {...},
  "metadata": [ <settings row>, ... ]
}
```
Default settings interval: 600s (`metadata.py:27`). **For Db2** the settings source is
`SYSIBMADM.DBMCFG` (instance/DBM config) and `SYSIBMADM.DBCFG` (database config), plus
`MON_GET_INSTANCE`/registry. `kind` would be `db2_configs`.

---

## Part G — Schema collection (`utils/db/schemas.py`)

`SchemaCollector(ABC)` drives streamed schema metadata into `dbm-metadata` events. Subclass contract:

- **Required abstract members:** `kind` (property, e.g. `"db2_databases"`), `_get_databases() -> list[DatabaseInfo]`, `_get_cursor(database) -> contextmanager`, `_get_next(cursor) -> row|None`.
- **Override `_map_row(database, cursor_row) -> DatabaseObject`** to attach `schemas`→`tables`→`columns`/`indexes`/`foreign_keys`/`partitions` (`schemas.py:198-204` default; SQL Server example `schemas.py:217-276`).
- `collect_schemas()` (`schemas.py:60-133`) iterates databases, streams the cursor, batches rows into chunks of `payload_chunk_size` (default 10,000, `schemas.py:39`) via `maybe_flush`, and emits each chunk through `check.database_monitoring_metadata`.
- `base_event` (`schemas.py:135-148`) assembles `host`, `database_instance`, `kind`, `agent_version`, `collection_interval`, `dbms`, `dbms_version`, `tags`, `cloud_metadata`, `collection_started_at`; `maybe_flush` adds `timestamp`, `metadata` (the row array), and on the last payload `collection_payloads_count` (used for snapshot completion).
- Telemetry (`schemas.py:111-131`, `raw=True`): `dd.<dbms>.schema.time` (histogram), `dd.<dbms>.schema.tables_count` (gauge), `dd.<dbms>.schema.payloads_count` (gauge).
- `SchemaCollectorConfig` (`schemas.py:36-39`): `collection_interval=3600`, `payload_chunk_size=10_000`. Subclasses often add `max_tables` (SQL Server default 300, `schemas.py:86`).
- **Scheduling:** the schema collector is **not** itself a `DBMAsyncJob`; it is invoked by the metadata `DBMAsyncJob` on its own interval (SQL Server `metadata.py:164-170`).
- **For Db2:** databases from `SYSIBMADM.ENV_INST_INFO`/connection; schemas/tables/columns/indexes/FKs from `SYSCAT.SCHEMATA`, `SYSCAT.TABLES`, `SYSCAT.COLUMNS`, `SYSCAT.INDEXES`/`SYSCAT.INDEXCOLUSE`, `SYSCAT.REFERENCES`/`SYSCAT.KEYCOLUSE`.

---

## Part H — Health events (`utils/db/health.py`)

`check.health` is a `Health` instance. `submit_health_event(name: HealthEvent, status: HealthStatus, tags, cooldown_time, cooldown_values, data)` emits a `dbm-health` event (`health.py:68-118`) with `version: 1`, `check_id`, `category` (`__NAMESPACE__` or class name lc), `name`, `status`, `tags`, `ddagentversion`, `ddagenthostname`, `data`. Cooldown dedups identical events for `cooldown_time` seconds (`TLRUCache`, `health.py:94-101`). `HealthEvent`: `INITIALIZATION`, `UNKNOWN_ERROR`, `MISSED_COLLECTION`. `HealthStatus`: `OK`, `WARNING`, `ERROR`. `submit_exception_health_event` auto-extracts file/line/function/type from a traceback (`health.py:120-134`). `DBMAsyncJob` calls these automatically on missed collections and crashes (Part E.3).

---

## Part I — `DatabaseCheck` base contract (`checks/db.py`)

To use `SchemaCollector` and the standard DBM event helpers, the integration's check should subclass
`DatabaseCheck` (or duck-type these). SQL Server (`sqlserver.py:132`) and the Db2 phase-2 check should do
the same. Required overrides:

| Member | Purpose | SQL Server impl ref |
|---|---|---|
| `reported_hostname -> str\|None` | event `host` field; `None` when `exclude_hostname` | `sqlserver.py:348-353` |
| `database_identifier -> str` | event `database_instance`; templated from tags (`$resolved_hostname` default) | `sqlserver.py:365-397` |
| `dbms -> str` | defaults to `self.__class__.__name__.lower()`; override to `"db2"` | `db.py:36-38` |
| `dbms_version -> str` | version string in payloads | `sqlserver.py:407+` |
| `tags -> list[str]` | base tags; usually `tag_manager.get_tags()` | `sqlserver.py:340-342` |
| `cloud_metadata -> dict` | cloud provider metadata block | `sqlserver.py:344-346` |

Provided by the base: `database_monitoring_query_sample/metrics/activity/metadata/health`.

### I.1 `TagManager` (`utils/db/utils.py:548-710`)
- Stores tags as key→[values] (plus keyless bucket). `set_tag(key, value, replace=False, normalize=False)`, `set_tags_from_list(list, replace=, normalize=)`, `delete_tag(...)`.
- `get_tags(include_internal=True, include_db=True)` returns rendered `key:value` (or bare keyless) tag list. Internal tags are keys prefixed `dd.internal` (e.g. `dd.internal.resource`), excluded from non-pipeline payloads. The per-database `db` key is excludable for instance-level/metrics payloads.
- Instantiate with a normalizer: `TagManager(normalizer=lambda t: self.normalize_tag(t).lower())` (`sqlserver.py:162`).

### I.2 `debug_stats_kwargs()` / `tracked_method` / `tracked_query`
- DBM jobs wrap their methods with `@tracked_method(agent_check_getter=lambda self: self._check)` to emit `dd.<check.name>.<method>.time/error/result_length` debug metrics (`tracking.py`). The check should expose `name`, `log`, `count`, `gauge`, `histogram` (it does, via `AgentCheck`), and optionally `debug_stats_kwargs()` returning common kwargs (tags, `raw=True`).
- `tracked_query(check, operation, tags=None)` (`utils.py:502-529`) is a context manager that emits `dd.<check.name>.operation.time` histogram around a query block (used when `QueryExecutor(track_operation_time=True)`).

---

## Part J — Reference assembly in the SQL Server check (closest analog to Db2)

`sqlserver/datadog_checks/sqlserver/sqlserver.py`:
- Subclasses `DatabaseCheck` (`:132`), builds a `TagManager` (`:162`), instantiates jobs in `__init__`:
  `SqlserverStatementMetrics` (`:174`), `SqlserverActivity` (`:177`), `SqlserverMetadata` (which owns `SQLServerSchemaCollector`), procedure metrics, deadlocks, agent history.
- Each check run calls `<job>.run_job_loop(self.tag_manager.get_tags())` (`:914-924`).
- `cancel()` calls `<job>.cancel()` for every job (`:213-218`).
- Each job opens its **own** dedicated DBM connection via a `_conn_key_prefix` (e.g. `"dbm-"`, `"dbm-activity-"`, `"dbm-metadata-"`) so background threads never share the main check's cursor (`statements.py:289`, `activity.py:209`, `metadata.py:84`).

The same scaffold is what the Db2 phase-2 backend should follow: convert `IbmDb2Check` to subclass
`DatabaseCheck`, add a `TagManager`, add `Db2StatementMetrics` / `Db2Activity` / `Db2Metadata`(+schemas)
`DBMAsyncJob`s, each with its own `ibm_db` connection, wired through `run_job_loop` / `cancel`.

---

## Part K — Db2-specific source mapping (synthesized for the plan; verify against 12.1)

These are **proposed** mappings derived from how the framework consumes data; each must be validated
against the 12.1.4 container's available monitoring views.

| DBM feature | Framework piece | Db2 source(s) |
|---|---|---|
| Query metrics (delta) | `StatementMetrics.compute_derivative_rows` | `TABLE(MON_GET_PKG_CACHE_STMT(NULL,NULL,NULL,-1))` — `EXECUTABLE_ID`, `STMT_TEXT`, `NUM_EXECUTIONS`, `TOTAL_CPU_TIME`, `TOTAL_ACT_TIME`, `ROWS_READ`, `ROWS_RETURNED`, `ROWS_MODIFIED`, `TOTAL_SORTS`, `POOL_*_L_READS`, `STMT_EXEC_TIME` |
| FQT / statement text | obfuscation + `compute_sql_signature` | `STMT_TEXT` from package cache (CLOB; enable `replace_null_character`) |
| Execution plans | plan event + `compute_exec_plan_signature` | EXPLAIN tables (`EXPLAIN_STATEMENT`, `EXPLAIN_OPERATOR`, `EXPLAIN_STREAM`, `EXPLAIN_OBJECT`) via `EXPLAIN PLAN FOR`/`CURRENT EXPLAIN MODE`; assemble JSON tree |
| Active sessions / activity | activity event | `TABLE(MON_GET_ACTIVITY(NULL,-1))`, `WLM_GET_WORKLOAD_OCCURRENCE_ACTIVITIES`, `TABLE(MON_GET_CONNECTION(NULL,-1))`; blocking via `SYSIBMADM.MON_LOCKWAITS` |
| Settings metadata | `dbm-metadata` settings event | `SYSIBMADM.DBMCFG`, `SYSIBMADM.DBCFG`, `MON_GET_INSTANCE` |
| Schema metadata | `SchemaCollector` subclass | `SYSCAT.SCHEMATA`, `SYSCAT.TABLES`, `SYSCAT.COLUMNS`, `SYSCAT.INDEXES`+`SYSCAT.INDEXCOLUSE`, `SYSCAT.REFERENCES`+`SYSCAT.KEYCOLUSE` |
| Obfuscator dialect | `obfuscate_sql_with_metadata` `options.dbms` | Verify Agent `pkg/obfuscate` supports `'db2'`; otherwise generic |

Existing plain metrics (already shipped, `ibm_db2/datadog_checks/ibm_db2/queries.py`) use
`MON_GET_INSTANCE`, `MON_GET_DATABASE`, `MON_GET_BUFFERPOOL`, `MON_GET_TABLESPACE`,
`MON_GET_TRANSACTION_LOG` — submitted directly (not via `QueryManager`).

---

## Citations (absolute paths)

- Framework: `/home/bits/dd/integrations-core/datadog_checks_base/datadog_checks/base/utils/db/{query,core,transform,statement_metrics,sql,sql_commenter,schemas,utils,health,types}.py`
- DBM submitters: `/home/bits/dd/integrations-core/datadog_checks_base/datadog_checks/base/checks/base.py:772-798`; `/home/bits/dd/integrations-core/datadog_checks_base/datadog_checks/base/checks/db.py`
- Tracking: `/home/bits/dd/integrations-core/datadog_checks_base/datadog_checks/base/utils/tracking.py`
- SQL Server reference: `/home/bits/dd/integrations-core/sqlserver/datadog_checks/sqlserver/{statements,activity,metadata,schemas,config,sqlserver}.py`
- Postgres reference: `/home/bits/dd/integrations-core/postgres/datadog_checks/postgres/{statements,statement_samples,config}.py`
- Current Db2 integration: `/home/bits/dd/integrations-core/ibm_db2/datadog_checks/ibm_db2/{ibm_db2,queries,utils}.py`
- Db2 monitoring views / obfuscator dialect support are **research items** to verify against the 12.1.4 container and the Agent `pkg/obfuscate` source (no URL fetched; flagged for plan).
