# Postgres DBM — Query Samples & Explain Plans (code research)

Raw research extracted from the actual `integrations-core` Postgres DBM source. This is input for a
Db2 fidelity implementation plan (target Db2 12.1; live container 12.1.4). Everything below is taken
directly from source; absolute file paths and line numbers are cited inline.

Primary files:
- `/home/bits/dd/integrations-core/postgres/datadog_checks/postgres/statement_samples.py` (the
  `PostgresStatementSamples` DBMAsyncJob — sampling, EXPLAIN, payload shaping, rate limiting)
- `/home/bits/dd/integrations-core/postgres/datadog_checks/postgres/explain_parameterized_queries.py`
  (`ExplainParameterizedQueries` — generic-plan workaround for `$1` params)

Supporting files:
- `/home/bits/dd/integrations-core/postgres/datadog_checks/postgres/util.py` (`DBExplainError`,
  `DatabaseConfigurationError`, `trim_leading_set_stmts`, `warning_with_tags`)
- `/home/bits/dd/integrations-core/postgres/datadog_checks/postgres/config_models/instance.py`
  (`QuerySamples`, `QueryActivity`, `ObfuscatorOptions`, `CollectRawQueryStatement` models)
- `/home/bits/dd/integrations-core/postgres/datadog_checks/postgres/config_models/dict_defaults.py`
  (default values)
- `/home/bits/dd/integrations-core/postgres/datadog_checks/postgres/data/conf.yaml.example` (config docs)
- `/home/bits/dd/integrations-core/datadog_checks_base/datadog_checks/base/utils/db/sql.py`
  (`compute_sql_signature`, `compute_exec_plan_signature`)
- `/home/bits/dd/integrations-core/datadog_checks_base/datadog_checks/base/utils/db/utils.py`
  (`DBMAsyncJob`, `ConstantRateLimiter`, `RateLimitingTTLCache`, `obfuscate_sql_with_metadata`,
  `default_json_event_encoding`)
- `/home/bits/dd/integrations-core/postgres/tests/compose/resources/03_setup.sh` (canonical
  `datadog.explain_statement` / `datadog.pg_stat_activity` SQL function definitions)

There are three distinct event streams produced by this one job, all from one
`pg_stat_activity` snapshot per loop:
1. **Query Samples / Explain plans** (`dbm_type: "plan"`) — obfuscated EXPLAIN plan per
   (query_signature, plan_signature).
2. **Activity** (`dbm_type: "activity"`) — the full snapshot of currently-active sessions +
   aggregated connection counts.
3. **Raw query text / raw plan** (`dbm_type: "rqt"` and `"rqp"`) — only when
   `collect_raw_query_statement.enabled` (off by default).

---

## 1. The job: `PostgresStatementSamples` (DBMAsyncJob)

`statement_samples.py:143` `class PostgresStatementSamples(DBMAsyncJob)`.

### 1.1 Construction & scheduling (`__init__`, lines 148-222)

- **Collection interval / rate limit** (`statement_samples.py:148-164`):
  - `collection_interval = config.query_samples.collection_interval` (default **1 s**).
  - If `query_samples.enabled` is **false**, it falls back to
    `config.query_activity.collection_interval` (default **10 s**) — i.e. when only activity is on,
    the loop slows down.
  - `DBMAsyncJob` is created with `rate_limit = 1 / collection_interval`,
    `run_sync = config.query_samples.run_sync` (default false),
    `enabled = query_samples.enabled OR query_activity.enabled`,
    `dbms="postgres"`, `job_name="query-samples"`,
    `expected_db_exceptions=(psycopg.errors.DatabaseError,)`,
    `min_collection_interval=config.min_collection_interval`.
- The rate limit is enforced by `ConstantRateLimiter` inside `DBMAsyncJob` (see §6).
- `self._explain_function = config.query_samples.explain_function` (default
  `"datadog.explain_statement"`), passed to `ExplainParameterizedQueries`.
- **Obfuscator options** (`statement_samples.py:174-180`) are serialized once to a JSON string and
  reused. Old agent obfuscator keys are backfilled:
  - `table_names = obfuscator_options.collect_tables`
  - `dollar_quoted_func = obfuscator_options.keep_dollar_quoted_func`
  - `return_json_metadata = obfuscator_options.collect_metadata`
  - `dbms = 'postgresql'`
- **Activity gating** (`statement_samples.py:214-221`):
  - `self._activity_coll_enabled = query_activity.enabled`
  - `self._explain_plan_coll_enabled = query_samples.enabled`
  - `self._activity_coll_interval = max(query_activity.collection_interval, collection_interval)`
    — activity can never be reported more often than samples.
  - `self._activity_max_rows = query_activity.payload_row_limit` (default **3500**).

### 1.2 Main loop (`run_job` -> `_collect_statement_samples`, lines 472-568)

`run_job` (line 472): strips `dd.internal*` tags into `self.tags`, builds `self._tags_no_db`
(tags without the `db:` prefix), then calls `_collect_statement_samples`.

`_collect_statement_samples` (line 478) per tick:
1. `pg_activity_cols = self._get_pg_stat_activity_cols_cached(PG_STAT_ACTIVITY_COLS)` — discover
   which expected columns actually exist (cached after first call). If `None` (schema/permission
   problem) emit `dd.postgres.statement_samples.error` with `error:explain-no_plans_possible` and
   return.
2. `collect_activity = self._report_activity_event()` — true only if activity enabled AND
   `_activity_coll_interval` has elapsed since the last activity event (line 1026-1032).
3. `rows = self._get_new_pg_stat_activity(pg_activity_cols, PG_STAT_ACTIVITY_COLS_MAPPING, collect_activity)`
   — single query against `pg_stat_activity` view (see §2).
4. `rows = self._filter_and_normalize_statement_rows(rows)` — obfuscate + compute signatures (§3).
5. If `_explain_plan_coll_enabled`: for each plan event from `_collect_plans(rows)`, submit via
   `self._check.database_monitoring_query_sample(json.dumps(e, default=default_json_event_encoding))`
   and increment `submitted_count`.
6. If `collect_activity`: fetch `_get_active_connections()`, build `_create_activity_event(rows, conns)`,
   submit via `self._check.database_monitoring_query_activity(...)`.
7. Emit telemetry/histograms (see §8).

Note ordering: the **activity decision is computed before** sampling so `pg_blocking_pids()` is only
included when an activity snapshot will be produced (expensive call gated to the activity cadence).

---

## 2. How active queries are sampled (`pg_stat_activity`)

### 2.1 The activity view / function

The check reads from `self._config.pg_stat_activity_view` (default `pg_stat_activity`; commonly
overridden to a SECURITY DEFINER wrapper `datadog.pg_stat_activity()` so a non-superuser agent can
see all sessions' query text). Wrapper definition
(`/home/bits/dd/integrations-core/postgres/tests/compose/resources/03_setup.sh:60-63`):

```sql
CREATE OR REPLACE FUNCTION datadog.pg_stat_activity() RETURNS SETOF pg_stat_activity AS
$$ SELECT * FROM pg_catalog.pg_stat_activity; $$
LANGUAGE sql
SECURITY DEFINER;
```

### 2.2 Column discovery (`_get_available_activity_columns`, lines 306-351)

Runs `SELECT * FROM {pg_stat_activity_view} LIMIT 0`, reads `cursor.description` to get the actual
column set, and intersects with the expected column list so the check works across PG versions/managed
flavors (Aurora/Azure add or drop columns). Result is cached in `self._pg_stat_activity_cols`
(`_get_pg_stat_activity_cols_cached`, lines 299-304).

Expected columns — `PG_STAT_ACTIVITY_COLS` (`statement_samples.py:71-92`):
`datid, datname, pid, usesysid, usename, application_name, client_addr, client_hostname,
client_port, backend_start, xact_start, query_start, state_change, wait_event_type, wait_event,
state, backend_xid, backend_xmin, query, backend_type`.

Column casting — `PG_STAT_ACTIVITY_COLS_MAPPING` (lines 95-98): `backend_type` is selected as
`backend_type::bytea as backend_type` to dodge unicode-decode errors on Azure (decoded manually later,
line 361-365).

### 2.3 The activity query

`PG_STAT_ACTIVITY_QUERY` (`statement_samples.py:103-112`, whitespace-collapsed):

```sql
SELECT {current_time_func} {pg_stat_activity_cols} {pg_blocking_func} FROM {pg_stat_activity_view}
WHERE
    {backend_type_predicate}
    (coalesce(TRIM(query), '') != '' AND pid != pg_backend_pid() AND query_start IS NOT NULL {extra_filters})
```

Format substitutions (`_get_new_pg_stat_activity`, lines 263-297):
- `{current_time_func}` = `CURRENT_TIME_FUNC` = `"clock_timestamp() as now,"` (line 101) — server
  "now" used to compute durations consistently regardless of agent clock.
- `{backend_type_predicate}` = `"backend_type != 'client backend' OR"` when PG >= v10 (line 270-271),
  else empty. This widens the snapshot to include background/system processes (autovacuum, walwriter,
  etc.) in addition to client backends.
- `{pg_blocking_func}` = `PG_BLOCKING_PIDS_FUNC` = `",pg_blocking_pids(pid) as blocking_pids"`
  (line 100) — **only** when PG >= v9.6 AND `collect_activity` is true (lines 273-275). This is the
  lock-tree / blocking-session source.
- `{pg_stat_activity_cols}` = the discovered columns joined with `, ` (with the bytea cast applied).
- `{extra_filters}` = from `_get_extra_filters_and_params`.

### 2.4 Filtering predicates baked into the query

- `coalesce(TRIM(query), '') != ''` — skip empty query text.
- `pid != pg_backend_pid()` — never sample the agent's own session.
- `query_start IS NOT NULL` — must have a started query.

### 2.5 Extra filters (`_get_extra_filters_and_params`, lines 429-442)

Parameterized (`%s`) WHERE clauses appended:
- `dbstrict` true -> `AND datname = %s` (restrict to configured `dbname`).
- else if `ignore_databases` non-empty -> `AND datname NOT ILIKE %s` per entry.
- If `filter_stale_idle_conn` (used by `_get_new_pg_stat_activity` only) AND we have a recorded
  `_activity_last_query_start` -> `AND NOT (query_start < %s AND state = 'idle')`. This avoids
  re-reading idle connections we've already seen — important so old idle sessions don't keep
  generating duplicate samples. `_activity_last_query_start` is advanced in
  `_filter_and_normalize_statement_rows` (lines 377-380) to the max `query_start` seen.

### 2.6 Active connections aggregate query

`PG_ACTIVE_CONNECTIONS_QUERY` (`statement_samples.py:114-124`), run only when `collect_activity`
(`_get_active_connections`, lines 244-261):

```sql
SELECT application_name, state, usename, datname, count(*) as connections
FROM {pg_stat_activity_view}
WHERE pid != pg_backend_pid() AND client_port IS NOT NULL
{extra_filters}
GROUP BY application_name, state, usename, datname
```

Produces the `postgres_connections` array in the activity event (per-(app, state, user, db) counts).
`client_port IS NOT NULL` restricts to real client sessions (excludes background workers).

---

## 3. Row filtering, obfuscation & signatures

### 3.1 `_filter_and_normalize_statement_rows` (lines 353-396)

Per row:
- Decode `backend_type` from bytes (`utf-8`, `errors='backslashreplace'`).
- Skip if no `query`.
- Skip if `datname` empty AND `backend_type == 'client backend'` (lines 369-370).
- Stringify `client_addr` if present.
- Skip `query == '<insufficient privilege>'` (counts toward `insufficient_privilege_count`).
- Advance `_activity_last_query_start`.
- Append `_normalize_row(row)`.

If any `<insufficient privilege>` rows: log a warning and emit
`dd.postgres.statement_samples.error` count tagged `error:insufficient-privilege`.

### 3.2 `_normalize_row` (lines 398-427)

- For non-`client backend` rows (background processes), the obfuscated "query" is the `backend_type`
  string itself, and `query_signature = compute_sql_signature(backend_type)` (lines 403-405).
- For client backends: `statement = obfuscate_sql_with_metadata(row['query'], self._obfuscate_options)`.
  - `obfuscated_query = statement['query']`
  - `query_signature = compute_sql_signature(obfuscated_query)`
  - `dd_tables = metadata['tables']`, `dd_commands = metadata['commands']`,
    `dd_comments = metadata['comments']`
- On obfuscation failure: emit `dd.postgres.statement_samples.error` tagged `error:sql-obfuscate`;
  the obfuscated statement stays `None`.
- Sets `normalized_row['statement'] = obfuscated_query`.

### 3.3 Signature helpers (base)

`/home/bits/dd/integrations-core/datadog_checks_base/datadog_checks/base/utils/db/sql.py`:
- `compute_sql_signature(normalized_query)` (line 18): `mmh3.hash64(ensure_bytes(query), signed=False)[0]`
  formatted as lowercase hex (64-bit). **Must match the APM resource hash on the backend** — do not
  change casually.
- `compute_exec_plan_signature(normalized_json_plan)` (line 48): JSON-decode then re-encode with
  `sort_keys=True`, then `mmh3.hash64(..., signed=False)[0]` as hex. Sorting keys makes the signature
  order-independent.

### 3.4 Obfuscation of SQL (`obfuscate_sql_with_metadata`, base utils line 249)

Calls `datadog_agent.obfuscate_sql(query, options)` (Go obfuscator in the Agent). Returns
`{'query': <obfuscated>, 'metadata': {...}}`. Metadata includes `tables` (parsed from `tables_csv`),
`commands`, `comments`. Older agents return a plain obfuscated string (no leading `{`), handled
gracefully.

---

## 4. How EXPLAIN is run & plans are obfuscated/encoded

### 4.1 Statement eligibility (`_can_explain_statement`, lines 644-651)

Skip if obfuscated statement:
- starts with `SELECT {explain_function}` (don't explain the explain),
- starts with `autovacuum:`,
- first token (lowercased) not in `SUPPORTED_EXPLAIN_STATEMENTS`
  (`statement_samples.py:54`): `{select, table, delete, insert, replace, update, with}`.

### 4.2 Per-DB explain setup state (cached collection strategy)

Because EXPLAIN must run **in the same database** as the sampled query, the check opens a connection
per `datname` via `self._check.db_pool.get_connection(dbname)`.

`_get_db_explain_setup_state` (lines 653-703) validates explain works for a db by running
`EXPLAIN_VALIDATION_QUERY = "SELECT * FROM pg_stat_activity"` (line 126) through `_run_explain`.
Maps exceptions to `DBExplainError`:
- `psycopg.OperationalError` -> `connection_error`
- `psycopg.DatabaseError` (pre-validate) -> `database_error`
- `InvalidSchemaName` -> `invalid_schema`
- `DatatypeMismatch` -> `datatype_mismatch`
- other `DatabaseError` -> `failed_function` (also records `DatabaseConfigurationError.undefined_explain_function` warning)
- empty result -> `invalid_result`
- success -> `(None, None)`

`_get_db_explain_setup_state_cached` (lines 705-717): result cached in
`self._collection_strategy_cache` — `TTLCache(maxsize=1000, ttl=300)` (lines 184-187). So a broken
db is retried at most every 5 minutes.

### 4.3 Running EXPLAIN (`_run_explain`, lines 719-750)

```python
with self._check.db_pool.get_connection(dbname) as conn:
    if conn.info.encoding.lower() in ["ascii", "sqlascii", "sql_ascii"]:
        conn.execute("SET client_encoding TO UTF8")
    with conn.cursor() as cursor:
        cursor.execute("SELECT {}(%s)".format(self._explain_function), (statement,), ignore_query_metric=True)
        result = cursor.fetchone()
        ...
        return result[0][0]   # the JSON plan
```

Key points:
- The plan is produced by calling a **server-side function**, not by running `EXPLAIN` directly. The
  default function is `datadog.explain_statement` (a SECURITY DEFINER plpgsql wrapper) so the agent
  user needs no direct EXPLAIN privileges and the EXPLAIN runs as the function owner in a
  read-only transaction.
- The **raw (un-obfuscated) original** `statement` (`row['query']`) is passed as the parameter, not
  the obfuscated text — you need real literals/identifiers to plan.
- `ignore_query_metric=True` prevents this internal query from polluting query metrics.
- Forces UTF-8 client encoding for SQL_ASCII databases.

Canonical function definition
(`/home/bits/dd/integrations-core/postgres/tests/compose/resources/03_setup.sh:37-58`):

```sql
CREATE OR REPLACE FUNCTION datadog.explain_statement(
  l_query TEXT,
  OUT explain JSON
)
RETURNS SETOF JSON AS
$$
DECLARE
  curs REFCURSOR;
  plan JSON;
BEGIN
  SET TRANSACTION READ ONLY;
  OPEN curs FOR EXECUTE pg_catalog.concat('EXPLAIN (FORMAT JSON) ', l_query);
  FETCH curs INTO plan;
  CLOSE curs;
  RETURN QUERY SELECT plan;
END;
$$
LANGUAGE 'plpgsql'
RETURNS NULL ON NULL INPUT
SECURITY DEFINER;
```

So the plan is **`EXPLAIN (FORMAT JSON)`** (no ANALYZE — costs only, no execution). The function
returns the plan as a single JSON value.

### 4.4 Error handling wrapper (`_run_explain_safe`, lines 770-853)

Order of operations:
1. If obfuscated statement starts with `set` (case-insensitive 3 chars): strip leading SET statements
   from both raw and obfuscated via `trim_leading_set_stmts` (util.py:401, regex `SET_TRIM_PATTERN`).
2. `_can_explain_statement` gate -> `no_plans_possible`.
3. Truncation check on the **original** query via `_get_truncation_state`; if truncated ->
   `query_truncated` with msg `track_activity_query_size={N}`.
4. `_get_db_explain_setup_state_cached` -> bail with that error if set.
5. Check `_explain_errors_cache` (per-query-signature negative cache, see §5).
6. If `_is_parameterized_query(statement)`:
   - if `query_samples.explain_parameterized_queries` (default true) -> delegate to
     `ExplainParameterizedQueries.explain_statement` (§7);
   - else -> `parameterized_query` error (cached) + emit run_explain error.
7. Else `_run_explain(...)` -> `(plan, None, None)`.

Exception -> `DBExplainError` mapping (each emits `dd.postgres.run_explain.error`; most are cached
in `_explain_errors_cache`):
- `UndefinedTable` -> `undefined_table` (cached)
- `UndefinedFunction` -> `undefined_function` (cached)
- `IndeterminateDatatype` -> `indeterminate_datatype` (cached)
- other `DatabaseError` -> `database_error`; **only cached** if it is a `ProgrammingError` and not
  `InsufficientPrivilege` (permission errors may be fixed by the user, so they are re-tried).

`_run_and_track_explain` (lines 752-768) wraps `_run_explain_safe` and emits
`dd.postgres.statement_samples.error` tagged `error:explain-<code>[-<msg>]` for any error code other
than `explained_with_prepared_statement` (that one is a success).

### 4.5 Plan obfuscation & encoding (`_collect_plan_for_statement`, lines 866-966)

After getting `plan_dict`:
```python
raw_plan = json.dumps(plan_dict)                                  # JSON string (decode bytes if orjson)
normalized_plan  = datadog_agent.obfuscate_sql_exec_plan(raw_plan, normalize=True)
obfuscated_plan  = datadog_agent.obfuscate_sql_exec_plan(raw_plan)
plan_signature     = compute_exec_plan_signature(normalized_plan)
raw_plan_signature = compute_exec_plan_signature(raw_plan)
```
- `datadog_agent.obfuscate_sql_exec_plan` is the Agent Go function that strips literals from the JSON
  plan. `normalize=True` additionally canonicalizes the structure used for the signature; the
  non-normalized obfuscated plan is what gets shipped as the plan `definition`.
- On obfuscation failure it raises (optionally logging the raw plan if `log_unobfuscated_plans`).
- `plan_signature` (from normalized plan) groups identical plan trees; `raw_plan_signature` is only
  used in the RQP path.

Comment block (lines 873-877) on signatures:
- `plan_signature` — hash of the normalized JSON plan, groups identical plan trees.
- `resource_hash` — hash of raw SQL to match APM resources. **For Postgres, `resource_hash ==
  query_signature`** (both are the hash of the obfuscated SQL).
- `query_signature` — hash of obfuscated SQL to match query metrics.

---

## 5. Rate limiting & caches (concrete sizes/TTLs)

Two rate-limiting mechanisms: a global loop limiter (`ConstantRateLimiter`) and several per-key
`RateLimitingTTLCache`s. All `RateLimitingTTLCache` and `TTLCache` defaults from `__init__`
(`statement_samples.py:184-212`):

| Cache (attr) | Type | maxsize (default) | ttl | Purpose |
|---|---|---|---|---|
| `_collection_strategy_cache` | `TTLCache` | 1000 | 300 s | per-db explain setup state (don't re-probe broken dbs) |
| `_explain_errors_cache` | `TTLCache` | `query_samples.explain_errors_cache_maxsize` = **5000** | `explain_errors_cache_ttl` = **86400 s (1 day)** | negative cache of un-explainable queries by query_signature |
| `_explained_statements_ratelimiter` | `RateLimitingTTLCache` | `explained_queries_cache_maxsize` = **5000** | `3600 / explained_queries_per_hour_per_query` (= 3600/60 = **60 s**) | how often we EXPLAIN the same normalized query |
| `_seen_samples_ratelimiter` | `RateLimitingTTLCache` | `seen_samples_cache_maxsize` = **10000** | `3600 / samples_per_hour_per_query` (= 3600/15 = **240 s**) | ingestion rate per (query_signature, plan_signature) |
| `_raw_statement_text_cache` | `RateLimitingTTLCache` | 10000 (hardcoded) | `3600/1` = **3600 s** | RQT emission rate per (query_signature, raw_query_signature) |

`RateLimitingTTLCache.acquire(key)` (base utils.py:148-162): returns `False` if cache is full **or**
key already present; otherwise inserts key and returns `True`. So "acquire == may proceed". TTL
expiry frees the key so the next sample after the window is allowed.

Where they gate:
- `_explained_statements_ratelimiter.acquire((datname, query_signature))` at the top of
  `_collect_plan_for_statement` (line 869-871): limits EXPLAIN calls to the DB to once per query per
  ~60 s.
- `_seen_samples_ratelimiter.acquire((query_signature, plan_signature))` (line 901-902): limits
  emitting plan events to once per (query, plan) per ~240 s.
- `_raw_statement_text_cache.acquire((query_signature, raw_query_signature))`
  (`_row_to_raw_statement_event`, line 611-613): once per hour per raw statement.

`ConstantRateLimiter` (base utils.py:106-145): the DBMAsyncJob loop limiter. `period_s = 1/rate_limit`.
`update_last_time_and_sleep` sleeps in `max_sleep_chunk_s` (1 s) increments until the next period,
checking the cancel event. This enforces the `collection_interval`.

---

## 6. DBMAsyncJob mechanics (base)

`/home/bits/dd/integrations-core/datadog_checks_base/datadog_checks/base/utils/db/utils.py:289+`.
- Shared `ThreadPoolExecutor(100000)`. Each job runs `run_job_loop(tags)` in a background thread
  unless `run_sync=True`.
- `rate_limit` -> `ConstantRateLimiter(rate_limit, max_sleep_chunk_s=1)`; the loop calls
  `update_last_time_and_sleep(self._cancel_event)` each iteration.
- `_cancel_event` (threading.Event) — every DB query in the job first checks
  `if self._cancel_event.is_set(): raise Exception("Job loop cancelled...")` (e.g.
  `statement_samples.py:251, 286, 308, 721`).
- Health events submitted per job; missed-collection event can be disabled.

---

## 7. Parameterized-query EXPLAIN workaround (`ExplainParameterizedQueries`)

File `/home/bits/dd/integrations-core/postgres/datadog_checks/postgres/explain_parameterized_queries.py`.
This is the most Db2-relevant subtlety: clients using the extended query protocol / prepared
statements send queries with `$1, $2…` placeholders and the literals are bound separately, so
`pg_stat_activity.query` contains placeholders that can't be planned normally.

### 7.1 Detection (`_is_parameterized_query`, lines 195-200)

```python
PARAMETERIZED_QUERY_PATTERN = re.compile(r"(?<!')\$(?!'\$')[\d]+(?!')")
return PARAMETERIZED_QUERY_PATTERN.search(statement) is not None
```
Matches `$<digits>` not wrapped in single quotes (so `'$1'` string literal is not a parameter).

### 7.2 Strategy (docstring lines 35-68 + code)

Requires **PG >= 12** (`plan_cache_mode` setting). If `self._check.version < V12`, returns
`(None, DBExplainError.parameterized_query, ...)` (lines 77-85).

Steps (`explain_statement`, lines 76-114), all on one pooled connection per dbname:
1. `SET plan_cache_mode = force_generic_plan` (`_set_plan_cache_mode`, line 116-117) — forces a
   generic plan instead of a custom plan tied to specific bind values.
2. Create prepared statement (`_create_prepared_statement`, lines 119-136):
   `PREPARE dd_{query_signature} AS {statement}`
   (`PREPARE_STATEMENT_QUERY`, line 19). Catches `IndeterminateDatatype` -> `indeterminate_datatype`,
   `UndefinedFunction` -> `undefined_function`, other -> `failed_to_explain_with_prepared_statement`.
3. Determine parameter count (`_get_number_of_parameters_for_prepared_statement`, lines 138-141):
   ```sql
   SELECT CARDINALITY(parameter_types) FROM pg_prepared_statements WHERE name = 'dd_{query_signature}'
   ```
   (`PARAM_TYPES_COUNT_QUERY`, lines 21-23).
4. Build EXECUTE with N `null` args (`_generate_prepared_statement_query`, lines 143-152):
   `EXECUTE dd_{query_signature}(null,null,...)`
   (`EXECUTE_PREPARED_STATEMENT_QUERY`, line 25). No args -> no parens.
5. Explain it (`_explain_prepared_statement`, lines 154-173): call the explain function on the
   EXECUTE string — `SELECT {explain_function}(%s)` (`EXPLAIN_QUERY`, line 27) with the EXECUTE text
   as the bound `%s` parameter. Result is unwrapped `result[0][0][0]` (line 101) ->
   `(plan, DBExplainError.explained_with_prepared_statement, None)`. Empty result ->
   `no_plan_returned_with_prepared_statement`.
6. **Always** `DEALLOCATE PREPARE dd_{query_signature}` in a `finally` (`_deallocate_prepared_statement`,
   lines 175-183). (Prepared statements are also auto-dropped at session end.)

All queries use `ignore_query_metric=True`.

Why `null`: works with any datatype and, because `force_generic_plan` is set, Postgres still produces
a plan (without it, planning `id = null` would short-circuit to "no rows").

---

## 8. Payload shapes

### 8.1 Plan event (`dbm_type: "plan"`) — `_collect_plan_for_statement` lines 902-965

```jsonc
{
  "host": "<reported_hostname>",
  "database_instance": "<check.database_identifier>",
  "dbm_type": "plan",
  "ddagentversion": "<agent version>",
  "ddsource": "postgres",
  "ddtags": "db:<datname>,<...instance tags>",   // comma-joined string
  "timestamp": <ms epoch float>,
  "cloud_metadata": { ... },
  "service": "<config.service>",
  "network": { "client": { "ip": "<client_addr>", "port": <client_port>, "hostname": "<client_hostname>" } },
  "db": {
    "instance": "<datname>",
    "plan": {
      "definition": "<obfuscated JSON plan string>",
      "signature": "<plan_signature>",
      "collection_errors": [ { "code": "<DBExplainError.value>", "message": "<err msg|null>" } ] | null
      // "raw_signature": "<raw_plan_signature>"  // added only when collect_raw_query_statement
    },
    "query_signature": "<query_signature>",
    "resource_hash": "<query_signature>",          // == query_signature for postgres
    "application": "<application_name>",
    "user": "<usename>",
    "statement": "<obfuscated SQL>",
    "metadata": { "tables": [...], "commands": [...], "comments": [...] },
    "query_truncated": "truncated" | "not_truncated" | "unknown"
  },
  "postgres": { <all pg_stat_activity row cols except the excluded keys> }
}
```

- `postgres` sub-object = the row minus `pg_stat_activity_sample_exclude_keys`
  (`statement_samples.py:58-68`): `query, application_name, datname, usename, client_addr,
  client_hostname, client_port` (these are surfaced under the standard `db`/`network` keys instead).
  It therefore includes `pid, state, wait_event_type, wait_event, query_start, xact_start,
  state_change, backend_xid, backend_xmin, backend_type, blocking_pids, now, query_signature,
  dd_tables/...` etc.
- **Idle-transaction duration** (lines 943-953): if `state in {'idle', 'idle in transaction'}` and
  both `state_change` and `query_start` are set, `duration = (state_change - query_start) * 1e9` (ns),
  and if `state_change.tzinfo` is present, the event `timestamp` is overridden to `state_change`'s
  timestamp (so completed idle txns are timestamped at their real end, not collection time).
- A plan event is emitted **even when EXPLAIN failed** — `plan` fields are `None`/empty and
  `collection_errors` carries the `DBExplainError` code. It still goes through the
  `_seen_samples_ratelimiter` (key `(query_signature, None)`), so failures are recorded once per window.

### 8.2 Activity event (`dbm_type: "activity"`) — `_create_activity_event` lines 989-1011

```jsonc
{
  "host": "<reported_hostname>",
  "database_instance": "<database_identifier>",
  "ddagentversion": "...",
  "ddsource": "postgres",
  "dbm_type": "activity",
  "collection_interval": <_activity_coll_interval>,
  "ddtags": [<tags without db: prefix>],          // list, not comma-string
  "timestamp": <ms epoch>,
  "cloud_metadata": { ... },
  "service": "<config.service>",
  "postgres_activity": [ <active session rows> ],
  "postgres_connections": [ {application_name, state, usename, datname, connections}, ... ]
}
```

Active session rows (`_create_active_sessions` -> `_to_active_session`, lines 570-592):
- A row is "active" if `backend_type != 'client backend'` OR (`state` not null and not `'idle'`).
- Each active row gets `query_truncated` set and `statement` defaulted to `"ERROR: failed to
  obfuscate"` if obfuscation failed.
- In `_create_activity_event`, each row is stripped of `None` values and the raw `query` key
  (line 995) before being added (obfuscated `statement` is kept).
- Capped at `_activity_max_rows` (= `payload_row_limit`, default 3500). `_truncate_activity_rows`
  (lines 1013-1024) sorts by `(xact_start|query_start, query_start)` to keep the **longest-running**
  transactions when over the limit. (Note: in this revision `_create_active_sessions` simply breaks at
  the row limit; `_truncate_activity_rows`/`_sort_key` implement the "top-N longest" behavior.)

### 8.3 Raw query text event (`dbm_type: "rqt"`) — `_row_to_raw_statement_event` lines 594-642

Only when `collect_raw_query_statement.enabled` (default **false**) and only for `client backend`.
Rate-limited by `_raw_statement_text_cache` (once/hour per (query_signature, raw_query_signature)).

```jsonc
{
  "timestamp": <ms>,
  "host": "...", "database_instance": "...", "ddagentversion": "...",
  "ddsource": "postgres",
  "dbm_type": "rqt",
  "ddtags": "db:<datname>,...",
  "service": "...",
  "db": {
    "instance": "<datname>",
    "query_signature": "<query_signature>",
    "raw_query_signature": "<hash of raw query>",
    "statement": "<RAW (un-obfuscated) SQL>",
    "metadata": { "tables": ..., "commands": ..., "comments": ... }
  },
  "postgres": { "datname": "...", "rolname": "..." }
}
```

### 8.4 Raw plan event (`dbm_type: "rqp"`) — lines 955-964

Only when `collect_raw_query_statement.enabled` and a `plan_signature` exists. A deep copy of the
obfuscated plan event with: `dbm_type="rqp"`, `db.statement = raw query`,
`db.plan.definition = raw_plan`, `db.plan.raw_signature = raw_plan_signature`. The obfuscated plan
event also gets `db.plan.raw_signature` set in this case.

### 8.5 Submission methods

- `self._check.database_monitoring_query_sample(json_str)` — for plan / rqt / rqp events.
- `self._check.database_monitoring_query_activity(json_str)` — for activity events.
- All serialized with `json.dumps(event, default=default_json_event_encoding)`
  (`default_json_event_encoding`, base utils.py:237: Decimal->float, datetime/date->isoformat,
  IPv4Address->str, bytes->utf-8).

---

## 9. Truncation detection

`_get_track_activity_query_size` (lines 1034-1035): reads `track_activity_query_size` from
`self._check.pg_settings`; unknown -> `-1` (`TRACK_ACTIVITY_QUERY_SIZE_UNKNOWN_VALUE`).

`_get_truncation_state` (lines 1037-1070):
- `-1` -> `StatementTruncationState.unknown`.
- Else `truncated = len(utf8_bytes(statement)) >= track_activity_query_size - (MAX_CHARACTER_SIZE_IN_BYTES + 1)`
  where `MAX_CHARACTER_SIZE_IN_BYTES = 6` (lines 48, 1050). Compares **byte** length (Postgres counts
  bytes). Suggested min is `TRACK_ACTIVITY_QUERY_SIZE_SUGGESTED_VALUE = 4096` (line 52); below that a
  warning is logged.
- Returns `truncated` / `not_truncated` / `unknown` — surfaced as `db.query_truncated`.

For Db2: the analog is the statement-text length cap in the monitoring source (e.g. `MON_GET_*`
`STMT_TEXT` truncation / `STMT_HISTORY`); plan for an equivalent "unknown/truncated/not_truncated"
indicator.

---

## 10. Config knobs (defaults from dict_defaults.py + conf.yaml.example)

`config_models/dict_defaults.py`:

`query_samples` (`instance_query_samples`, lines 53-65):
| key | default |
|---|---|
| `enabled` | true |
| `collection_interval` | 1 (s) |
| `explain_function` | `datadog.explain_statement` |
| `explained_queries_per_hour_per_query` | 60 |
| `samples_per_hour_per_query` | 15 |
| `explained_queries_cache_maxsize` | 5000 |
| `seen_samples_cache_maxsize` | 10000 |
| `explain_parameterized_queries` | true |
| `explain_errors_cache_maxsize` | 5000 |
| `explain_errors_cache_ttl` | 86400 (s) |
| `run_sync` | false |

`query_activity` (`instance_query_activity`, lines 69-73):
| key | default |
|---|---|
| `enabled` | true |
| `collection_interval` | 10 (s) |
| `payload_row_limit` | 3500 |

`obfuscator_options` (`instance_obfuscator_options`, lines 116-125): `replace_digits=False`,
`collect_metadata=True`, `collect_tables=True`, `collect_commands=True`, `collect_comments=True`,
`keep_sql_alias=True`, `keep_dollar_quoted_func=True`.

`collect_raw_query_statement` (`instance_collect_raw_query_statement`, line 136): `enabled=false` by
default.

Other relevant instance-level knobs read by the job: `dbstrict`, `ignore_databases`, `dbname`,
`pg_stat_activity_view`, `idle_connection_timeout`, `service`, `log_unobfuscated_queries`,
`log_unobfuscated_plans`, `min_collection_interval`.

Config-model field declarations: `config_models/instance.py` — `QuerySamples` (lines 300-315),
`QueryActivity` (lines 275-282), `ObfuscatorOptions` (lines 253-272), `CollectRawQueryStatement`
(line 97).

---

## 11. Metrics emitted (internal telemetry)

All `raw=True`, hostname = `reported_hostname`, tagged with `self.tags + _get_debug_tags()` unless
noted. From `statement_samples.py`:

| Metric | Type | Where | Notes |
|---|---|---|---|
| `dd.postgres.statement_samples.error` | count | 390, 419, 485, 761, 981 | tags `error:<reason>`: `insufficient-privilege`, `sql-obfuscate`, `explain-no_plans_possible`, `explain-<code>[-msg]`, `collect-plan-for-statement-crash` |
| `dd.postgres.run_explain.error` | count | 857 | tag `error:explain-<code>-<exc type>` |
| `dd.postgres.run_explain.time` | histogram (ms) | 741 | per explain, tagged with db |
| `dd.postgres.get_active_connections.time/.rows` | histogram | 444-458 | via `_report_check_hist_metrics` |
| `dd.postgres.get_new_pg_stat_activity.time/.rows` | histogram | 444-458 | " |
| `dd.postgres.get_available_activity_columns.time/.rows` | histogram | 444-458 | " |
| `dd.postgres.collect_activity_snapshot.time` | histogram (ms) | 508 | |
| `dd.postgres.collect_statement_samples.time` | histogram (ms) | 522 | |
| `dd.postgres.collect_statement_samples.events_submitted.count` | count | 529 | number of plan events submitted |
| `dd.postgres.collect_statement_samples.seen_samples_cache.len` | gauge | 536 | cache occupancy |
| `dd.postgres.collect_statement_samples.explained_statements_cache.len` | gauge | 543 | |
| `dd.postgres.collect_statement_samples.explain_errors_cache.len` | gauge | 550 | |

Agent telemetry via `datadog_agent.emit_agent_telemetry("postgres", <name>, <val>, <type>)` (lines
459-470, 514-519, 557-568): `<method>_ms` (histogram), `<method>_count` (histogram),
`collect_activity_snapshot_ms`, `collect_statement_samples_ms` (histogram),
`collect_statement_samples_count` (gauge).

---

## 12. DBExplainError enum (full list) — util.py:271-324

`database_error, datatype_mismatch, invalid_schema, invalid_result, no_plans_possible,
failed_function, query_truncated, connection_error, parameterized_query, undefined_table,
undefined_function, explained_with_prepared_statement, failed_to_explain_with_prepared_statement,
no_plan_returned_with_prepared_statement, indeterminate_datatype, unknown_error`.

These string values are shipped in `db.plan.collection_errors[].code` and in error metric tags. A
Db2 implementation should mirror this taxonomy where the failure modes map (truncation, no-plan,
connection error, parameterized/host-var query, insufficient privilege, undefined object).

---

## 13. Db2-relevant translation notes

- **Sampling source**: Postgres reads one snapshot of `pg_stat_activity` per loop. Db2 analog =
  `SYSIBMADM.MON_GET_ACTIVITY` / `MON_GET_PKG_CACHE_STMT` / `WLM_GET_WORKLOAD_OCCURRENCE_ACTIVITIES`
  or `MON_GET_CONNECTION` for active in-flight statements, plus a "now" timestamp from the server
  (`CURRENT TIMESTAMP`) to compute durations consistently.
- **EXPLAIN**: Postgres uses a SECURITY DEFINER function returning `EXPLAIN (FORMAT JSON)`. Db2 has no
  inline JSON EXPLAIN; it uses the explain tables (`EXPLAIN_INSTANCE`, `EXPLAIN_STATEMENT`,
  `EXPLAIN_OPERATOR`, `EXPLAIN_STREAM`, …) populated by `EXPLAIN PLAN FOR <stmt>` or
  `db2expln`/`SET CURRENT EXPLAIN MODE`, or `EXPLAIN_FROM_*` table functions / section explain
  (`EXPLAIN_FROM_SECTION` from the package cache, which can explain the *actual* compiled section
  without re-binding). Section explain is the closest match to "explain the real plan" and avoids the
  parameterized-query problem entirely because the compiled section already has the access plan. The
  plan must be assembled from these tables into a JSON tree to mirror the Postgres plan payload shape.
- **Parameterized queries**: Postgres' `$1`/`force_generic_plan` workaround maps to Db2 host variables
  (`?` / `:hv`). Section explain (`EXPLAIN_FROM_SECTION`) sidesteps this because it reads the already
  compiled plan. If re-explaining text instead, Db2 needs representative values or `REOPT` handling.
- **Signatures**: reuse `compute_sql_signature` (mmh3 hash64 of obfuscated SQL) and
  `compute_exec_plan_signature` (mmh3 hash64 of normalized, key-sorted JSON plan) verbatim so backend
  grouping/APM-resource matching is consistent. Plan obfuscation: `datadog_agent.obfuscate_sql_exec_plan`
  expects a JSON plan string — Db2 must produce JSON in a compatible shape.
- **Rate limiting**: reuse `DBMAsyncJob` + `ConstantRateLimiter` for the loop and `RateLimitingTTLCache`
  for per-(signature) explain / per-(signature, plan_signature) sample limiting; same default cadences
  are a reasonable starting point (explain ≤60/hr/query, samples ≤15/hr/plan).
- **Payload shapes**: keep the same top-level keys (`host, database_instance, dbm_type, ddsource,
  ddtags, timestamp, cloud_metadata, service, db{...}`) and `dbm_type` values (`plan`, `activity`,
  `rqt`, `rqp`) so the existing DBM backend ingests them. `ddsource` would be `ibm_db2`.

---

## 14. Source citations summary

- Sampling / loop / payloads / rate limiting:
  `/home/bits/dd/integrations-core/postgres/datadog_checks/postgres/statement_samples.py`
- Parameterized EXPLAIN workaround:
  `/home/bits/dd/integrations-core/postgres/datadog_checks/postgres/explain_parameterized_queries.py`
- `DBExplainError` / helpers:
  `/home/bits/dd/integrations-core/postgres/datadog_checks/postgres/util.py`
- Defaults / models: `.../config_models/dict_defaults.py`, `.../config_models/instance.py`,
  `.../data/conf.yaml.example`
- Signatures / obfuscation / async job / rate limiter:
  `/home/bits/dd/integrations-core/datadog_checks_base/datadog_checks/base/utils/db/sql.py`,
  `/home/bits/dd/integrations-core/datadog_checks_base/datadog_checks/base/utils/db/utils.py`
- Canonical explain/activity SQL functions:
  `/home/bits/dd/integrations-core/postgres/tests/compose/resources/03_setup.sh`
