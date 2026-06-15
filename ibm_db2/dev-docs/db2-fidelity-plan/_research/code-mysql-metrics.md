# MySQL Integration — Metric Collection Architecture (raw research)

Purpose: exhaustive map of how the Datadog **mysql** integration collects metrics, as a reference template for building Db2 12.1 (live container 12.1.4) metric-collection fidelity. This is raw input for an implementation plan — completeness over brevity. All file paths are absolute. Line numbers are as of the snapshot read on 2026-06-15.

Source tree: `/home/bits/dd/integrations-core/mysql/datadog_checks/mysql/`

Files mapped here:
- `mysql.py` — orchestrator (1462 lines)
- `const.py` — metric-name dictionaries (variable → (metric_name, metric_type))
- `innodb_metrics.py` — parses `SHOW ENGINE INNODB STATUS` text
- `index_metrics.py` — per-index size/usage via QueryExecutor
- `queries.py` — declarative `QueryExecutor` query dicts + raw SQL strings
- `collection_utils.py` — type coercion helpers
- `global_variables.py` — `SHOW GLOBAL VARIABLES` cache + typed accessors
- `metadata.csv` — `/home/bits/dd/integrations-core/mysql/metadata.csv` (the metric catalog)

---

## 0. Two collection paradigms in this integration

The mysql check uses **two distinct mechanisms** to turn DB data into Datadog metrics. Db2 should be aware of both because they imply different code patterns.

### Paradigm A — "variable dict" submission (the dominant pattern)
1. Run a SQL/command that returns **key→value rows** (e.g. `SHOW GLOBAL STATUS`, `SHOW GLOBAL VARIABLES`), or parse text (`SHOW ENGINE INNODB STATUS`) into a flat `results` dict keyed by the **server's own variable name** (e.g. `Innodb_data_reads`).
2. Build a `metrics` mapping (a plain dict) of `{server_variable_name: (datadog_metric_name, metric_type)}`. These mappings live in `const.py` (`STATUS_VARS`, `INNODB_VARS`, `VARIABLES_VARS`, `OPTIONAL_*`, etc.).
3. `_submit_metrics(metrics, results, tags)` iterates the mapping, looks each variable up in `results`, coerces to float, and calls `self.gauge/rate/count/monotonic_count`.
   - Code: `mysql.py:969-997` (`_submit_metrics` / `__submit_metric`).
4. A value can itself be a **dict of tag→value** (used for per-schema / per-table / per-channel metrics). `collect_all_scalars` (`collection_utils.py:9-16`) yields `(tag, value)` pairs; the tag string can be comma-joined (`"schema:x,table:y"`) and is split into multiple tags in `__submit_metric` (`mysql.py:983-988`).

### Paradigm B — declarative `QueryExecutor`/`QueryManager` (from `datadog_checks.base.utils.db`)
1. A query is described as a dict: `{'name', 'query', 'columns': [{'name','type'}, ...], optional 'collection_interval'}`.
2. Each column is either a metric (`type` = `gauge`/`monotonic_count`/...) or a `tag`.
3. The base `QueryExecutor` runs the SQL, maps columns positionally, tags rows, and submits metrics — no per-check submission code needed.
   - Examples in `queries.py`: `QUERY_DEADLOCKS`, `QUERY_USER_CONNECTIONS`, `QUERY_ERRORS_RAISED`, `QUERY_WAIT_EVENT_SUMMARY`.
   - Index metrics use the same: `index_metrics.py` `QUERY_INDEX_SIZE`, `QUERY_INDEX_USAGE`.
   - Wired in via `_new_query_executor` (`mysql.py:449-456`) and `_get_runtime_queries` (`mysql.py:458-481`).

> Db2 NOTE: the **existing** `ibm_db2` integration (`/home/bits/dd/integrations-core/ibm_db2/datadog_checks/ibm_db2/`) already uses neither of these — it hand-rolls cursors. When porting MySQL-style breadth, Paradigm B (declarative query dicts) is the cleanest to replicate for the bulk of Db2's `MON_GET_*` table functions; Paradigm A is only needed if you parse text output (Db2 has no `SHOW ENGINE STATUS` analog, so Paradigm A is largely irrelevant — everything in Db2 12.1 is a relational table function: `MON_GET_*`, `SYSIBMADM.*`, `ENV_*`).

---

## 1. Check entrypoint and ordering — `mysql.py`

`class MySql(DatabaseCheck)` — `mysql.py:106`. Service check names (`mysql.py:107-110`):
- `mysql.can_connect`
- `mysql.replication.slave_running` (deprecated)
- `mysql.replication.replica_running`
- `mysql.replication.group.status`

`check(self, _)` — `mysql.py:382-441`. Per-run sequence:
1. `self._set_qcache_stats()` — restore prior qcache counters for instant-utilization delta (`mysql.py:483-505`).
2. Connect (`self._connect()`, contextmanager, `mysql.py:556-588`). Emits `mysql.can_connect` OK/CRITICAL.
3. `self.global_variables.collect(db)` — single `SHOW GLOBAL VARIABLES` query cached for the whole run (`global_variables.py:25-34`).
4. `self.set_version()` (`mysql.py:320-323`) → sets `dbms_flavor` tag.
5. `self._send_metadata()` (`mysql.py:196-200`) → version/flavor/resolved_hostname metadata.
6. `self._check_database_configuration(db)` (`mysql.py:333-335`): checks `events_waits_current` consumer + group replication active.
7. `self.set_server_uuid()` / `self.set_cluster_tags(db)` (`mysql.py:325-331`, `1438-1462`).
8. Aurora role detection (`mysql.py:408-410`).
9. `self._send_database_instance_metadata()` (`mysql.py:1413-1436`) — DBM database_instance event.
10. **Metric collection** (skipped if `only_custom_queries`):
    - `self._collect_metrics(db, tags)` — the big one (`mysql.py:590-782`).
    - `self._collect_system_metrics(host, db, tags)` — CPU via psutil (`mysql.py:1062-1118`).
    - `self._get_runtime_queries(db).execute(extra_tags=tags)` — Paradigm B queries (`mysql.py:420-421`).
11. If `dbm_enabled`: async job loops for statement metrics, statement samples, query activity, metadata (`mysql.py:423-428`). (Out of scope for "metrics" but noted.)
12. `self._query_manager.execute()` — custom queries (`mysql.py:434`).

`tracked_query(self, operation=...)` context manager wraps each sub-collection so the agent records per-operation timing (`mysql.py:595-712`). Operation names: `status_metrics`, `variables_metrics`, `innodb_metrics`, `binary_log_metrics`, `exec_time_95th_metrics`, `exec_time_per_schema_metrics`, `schema_size_metrics`, `table_rows_stats_metrics`, `table_size_metrics`, `system_table_size_metrics`, `replication_metrics`, `group_replication_metrics`.

### Cursor wrappers — `cursor.py`
`CommenterCursor`, `CommenterDictCursor`, `CommenterSSCursor` (server-side/unbuffered). They inject an SQL comment for attribution. `execute_query_raw` uses `CommenterSSCursor` and `fetchall_unbuffered()` for the QueryExecutor path (`mysql.py:190-194`).

---

## 2. `_collect_metrics` — the core flow — `mysql.py:590-782`

```
metrics = copy.deepcopy(STATUS_VARS)                 # base metric mapping
results = self._get_stats_from_status(db)            # SHOW GLOBAL STATUS  -> dict
results.update(self.global_variables.all_variables)  # SHOW GLOBAL VARIABLES (cached)
... conditional collectors add to results + metrics ...
self._submit_metrics(metrics, results, tags)
```

`_get_stats_from_status` (`mysql.py:1120-1126`): `SHOW /*!50002 GLOBAL */ STATUS;` → `dict(cursor.fetchall())`. This single command yields **most** `mysql.performance.*`, `mysql.net.*`, `mysql.myisam.*` and base `mysql.innodb.*` (the `_data_reads` etc. that appear as STATUS vars).

Conditional blocks (each gated by config option and/or server capability):

| Block | Gate | Adds to `results` | Adds to `metrics` (const.py) | Code |
|---|---|---|---|---|
| InnoDB status text | `_check_innodb_engine_enabled` and not Aurora-reader | `get_stats_from_innodb_status()` output | `INNODB_VARS` (+ computed bytes) | `mysql.py:601-608`, `635` |
| Binary log size | `global_variables.log_bin_enabled` | `Binlog_space_usage_bytes` | `BINLOG_VARS` | `mysql.py:610-613`, `636` |
| Key cache utilization | always (computed) | `Key_cache_utilization`, `Key_buffer_bytes_used`, `Key_buffer_bytes_unflushed`, `Key_buffer_size` | `VARIABLES_VARS` | `mysql.py:615-634` |
| Extra status | `options.extra_status_metrics` (defaults to `dbm_enabled`) | (already in SHOW STATUS) | `OPTIONAL_STATUS_VARS`, +`OPTIONAL_STATUS_VARS_5_6_6` if ≥5.6.6 | `mysql.py:638-643` |
| Galera | `options.galera_cluster` | (already in SHOW STATUS) | `GALERA_VARS` | `mysql.py:645-648` |
| Extra performance (deprecated) | `options.extra_performance_metrics` AND ≥5.6.0 AND perf_schema | `perf_digest_95th_percentile_avg_us`, `query_run_time_avg` (dict per schema) | `PERFORMANCE_VARS` | `mysql.py:650-664` |
| Schema size | `options.schema_size_metrics` | `information_schema_size` (dict per schema) | `SCHEMA_VARS` | `mysql.py:666-670` |
| Table row stats | `config.table_rows_stats_enabled` AND `userstat_enabled` | `information_table_rows_read_total`, `..._changed_total` (dicts) | `TABLE_ROWS_STATS_VARS` | `mysql.py:672-679` |
| Table size | `options.table_size_metrics` | `information_table_index_size`, `..._data_size` (dicts) | `TABLE_VARS` | `mysql.py:681-687` |
| System table size | `options.system_table_size_metrics` | merges into the same two dicts | `TABLE_VARS` | `mysql.py:689-701` |
| Replication | `config.replication_enabled` | replica status fields, `Replicas_connected` | `REPLICA_VARS` | `mysql.py:703-708` |
| Group replication | perf_schema AND group repl active | `Transactions_*` | `GROUP_REPLICATION_VARS(_8_0_2)` | `mysql.py:710-713` |
| Additional status/variable (user config) | non-empty config lists | user-named | user-defined (name, type) | `mysql.py:715-748` |
| Synthetic (qcache) | always | `Qcache_utilization`, `Qcache_instant_utilization` | `SYNTHETIC_VARS`; popped if not computed | `mysql.py:750-757`, `1373-1399` |
| Duped rate/gauge | always | copies `Table_locks_waited`→`_rate`, `Table_locks_immediate`→`_rate` | (already mapped) | `mysql.py:759-766` |

Capability gating helper `version.version_compatible((maj,min,patch))` is used throughout (e.g. `mysql.py:642`, `474`). Db2 analog: gate on 12.1 vs older; our live container is **12.1.4** so all 12.1 monitoring table functions are available.

---

## 3. `const.py` — variable→metric mappings (the metric catalog source of truth)

`/home/bits/dd/integrations-core/mysql/datadog_checks/mysql/const.py`. Type constants (`const.py:5-8`): `GAUGE="gauge"`, `RATE="rate"`, `COUNT="count"`, `MONOTONIC="monotonic_count"`.

Each dict entry is `'Server_Var_Name': ('datadog.metric.name', TYPE)`. A value may also be a **list** of `(name, type)` tuples to emit one server var to multiple metric names (used for backward-compat aliases — see `REPLICA_VARS`).

### `STATUS_VARS` (`const.py:18-68`) — from `SHOW GLOBAL STATUS`, always collected
Command metrics (all `RATE` unless noted):
- `Prepared_stmt_count`→`mysql.performance.prepared_stmt_count` (GAUGE)
- `Slow_queries`→`mysql.performance.slow_queries`
- `Questions`→`mysql.performance.questions`; `Queries`→`mysql.performance.queries`
- `Com_select/insert/update/delete/replace/load/insert_select/update_multi/delete_multi/replace_select`→`mysql.performance.com_*`
Connection: `Connections`→`mysql.net.connections`; `Max_used_connections`→`mysql.net.max_connections` (GAUGE); `Aborted_clients`→`mysql.net.aborted_clients`; `Aborted_connects`→`mysql.net.aborted_connects`.
Table cache: `Open_files`→`mysql.performance.open_files` (GAUGE); `Open_tables`→`mysql.performance.open_tables` (GAUGE).
Perf schema: `Performance_schema_digest_lost`→`mysql.performance.performance_schema_digest_lost` (GAUGE).
Network: `Bytes_sent`→`mysql.performance.bytes_sent`; `Bytes_received`→`mysql.performance.bytes_received`.
Query cache: `Qcache_hits/inserts/lowmem_prunes`→`mysql.performance.qcache_*`.
Table locks: `Table_locks_waited`→`mysql.performance.table_locks_waited` (GAUGE); `Table_locks_waited_rate`→`...table_locks_waited.rate` (RATE).
Temp tables: `Created_tmp_tables/Created_tmp_disk_tables/Created_tmp_files`→`mysql.performance.created_tmp_*`.
Threads: `Threads_connected`→`mysql.performance.threads_connected` (GAUGE); `Threads_running`→`...threads_running` (GAUGE).
MyISAM: `Key_buffer_bytes_unflushed/used` (GAUGE), `Key_read_requests/Key_reads/Key_write_requests/Key_writes`→`mysql.myisam.key_*`.

### `VARIABLES_VARS` (`const.py:71-79`) — from `SHOW GLOBAL VARIABLES`, all GAUGE
`Key_buffer_size`→`mysql.myisam.key_buffer_size`; `Key_cache_utilization`→`mysql.performance.key_cache_utilization`; `max_connections`→`mysql.net.max_connections_available`; `max_prepared_stmt_count`→`mysql.performance.max_prepared_stmt_count`; `query_cache_size`→`mysql.performance.qcache_size`; `table_open_cache`→`mysql.performance.table_open_cache`; `thread_cache_size`→`mysql.performance.thread_cache_size`.

### `INNODB_VARS` (`const.py:81-100`) — base InnoDB, always (from SHOW STATUS + computed)
`Innodb_data_reads/writes`(RATE), `Innodb_os_log_fsyncs`(RATE), `Innodb_mutex_spin_waits/rounds/os_waits`(RATE), `Innodb_row_lock_waits/time`(RATE), `Innodb_row_lock_current_waits`(GAUGE), `Innodb_current_row_locks`(GAUGE), `Innodb_buffer_pool_bytes_dirty/free/used/total`(GAUGE), `Innodb_buffer_pool_read_requests/reads`(RATE), `Innodb_buffer_pool_pages_utilization`(GAUGE).

### `BINLOG_VARS` (`const.py:104`)
`Binlog_space_usage_bytes`→`mysql.binlog.disk_use` (GAUGE).

### `OPTIONAL_STATUS_VARS` (`const.py:108-142`) — gated by `extra_status_metrics`
Binlog cache, Handler_* (RATE), Opened_tables, Qcache_* extras, Select_* (RATE), Sort_* (RATE), Table_locks_immediate(+rate), Threads_cached(GAUGE), Threads_created(MONOTONIC). Full list in file.

### `OPTIONAL_STATUS_VARS_5_6_6` (`const.py:145-148`)
`Table_open_cache_hits/misses`→`mysql.performance.table_cache_hits/misses` (RATE). Gated on ≥5.6.6.

### `OPTIONAL_INNODB_VARS` (`const.py:151-237`) — gated by `extra_innodb_metrics`
~80 metrics, mostly parsed out of `SHOW ENGINE INNODB STATUS` text (see §4). Added to the `metrics` mapping in `process_innodb_stats` (`innodb_metrics.py:418-420`). Covers: active/current transactions, buffer pool pages (data/dirty/flushed/free/total/read_ahead*), checkpoint_age, data_fsyncs/pending_*, dblwr_*, hash_index_cells_*, history_list_length, ibuf_* (insert buffer), lock_structs, locked_tables/transactions, log_* (writes/waits/write_requests), lsn_* (current/flushed/last_checkpoint), mem_* (adaptive_hash/dictionary/file_system/lock_system/page_hash/recovery_system/thread_hash/total/additional_pool), os_file_* and os_log_*, pages_created/read/written, pending_* aio/log/checkpoint/buffer flushes, queries_inside/queued, read_views, rows_inserted/updated/deleted/read, s_lock_*/x_lock_* (semaphores), semaphore_wait_time/waits, tables_in_use.

### `GALERA_VARS` (`const.py:239-255`), `PERFORMANCE_VARS` (`const.py:257-260`), `SCHEMA_VARS` (`const.py:262`), `TABLE_VARS` (`const.py:264-267`), `TABLE_ROWS_STATS_VARS` (`const.py:269-272`), `REPLICA_VARS` (`const.py:275-288`, list-of-tuples for aliases), `GROUP_REPLICATION_VARS` (`const.py:290-303`), `SYNTHETIC_VARS` (`const.py:305-308`).

---

## 4. InnoDB status text parsing — `innodb_metrics.py` (NOT applicable to Db2, but documents an anti-pattern)

`InnoDBMetrics.get_stats_from_innodb_status(db)` (`innodb_metrics.py:26-376`): runs `SHOW /*!50000 ENGINE*/ INNODB STATUS`, fetches the free-form text blob (`innodb_status[2]`), then **line-by-line regex/`str.find` parsing** to extract ~80 counters across sections SEMAPHORES, TRANSACTIONS, FILE I/O, INSERT BUFFER AND ADAPTIVE HASH INDEX, LOG, BUFFER POOL AND MEMORY, ROW OPERATIONS. Requires `PROCESS` privilege; degrades gracefully (returns `{}`) on permission/engine errors (`innodb_metrics.py:35-46`).

`process_innodb_stats(results, options, metrics)` (`innodb_metrics.py:378-420`): post-processes — derives byte counts from page counts × `Innodb_page_size`, computes `Innodb_buffer_pool_pages_utilization` and `..._bytes_used`, and conditionally merges `OPTIONAL_INNODB_VARS` into the metric mapping when `extra_innodb_metrics` is set.

> Db2 takeaway: **do not** replicate text parsing. Db2 12.1 exposes equivalent counters relationally:
> - Buffer pool: `MON_GET_BUFFERPOOL` (POOL_DATA_L_READS, POOL_DATA_P_READS, POOL_INDEX_*_READS, POOL_*_WRITES, etc.) — already used by the existing ibm_db2 check.
> - Transactions/locks: `MON_GET_DATABASE`, `MON_GET_CONNECTION`, `MON_GET_LOCKS`, `SYSIBMADM.SNAPDB`, `MON_GET_TRANSACTION_LOG`.
> - Rows: `MON_GET_TABLE`/`MON_GET_DATABASE` (ROWS_READ, ROWS_RETURNED, ROWS_MODIFIED).
> - Log/LSN: `MON_GET_TRANSACTION_LOG` (CUR_COMMIT_DISK_LOG_READS, LOG_WRITES, etc.).
> Map MySQL's InnoDB metric *intent* to the right Db2 monitoring function rather than its representation.

---

## 5. Index metrics — `index_metrics.py` (Paradigm B template — directly relevant to Db2)

`class MySqlIndexMetrics` (`index_metrics.py:83-111`). Config-driven: `index_config.enabled` (default True), `collection_interval` (default 300s, `index_metrics.py:79`), `limit` (default 1000 top indexes, `index_metrics.py:80`). The `queries` property returns two query dicts with the `INDEX_LIMIT` formatted in and `collection_interval` attached (`index_metrics.py:99-111`). Wired in `_get_runtime_queries` (`mysql.py:476-477`).

`QUERY_INDEX_SIZE` (`index_metrics.py:7-34`): from `mysql.innodb_index_stats`, `SUM(stat_value * @@innodb_page_size)` where `stat_name='size'`, grouped by db/base_table/index, `LIMIT {INDEX_LIMIT}`. Columns → tags `db`,`table`,`index`; metric `mysql.index.size` (gauge).

`QUERY_INDEX_USAGE` (`index_metrics.py:35-77`): joins `performance_schema.table_io_waits_summary_by_index_usage` against the size subquery; metrics `mysql.index.reads/updates/deletes` (gauge) with the same three tags.

> Db2 analog: `MON_GET_INDEX` (or `SYSCAT.INDEXES` + `MON_GET_TABLE`) for index reads/scans/size; the declarative-query-dict pattern with a `collection_interval` and a top-N `LIMIT` (Db2: `FETCH FIRST n ROWS ONLY`) ports cleanly.

---

## 6. Declarative runtime queries — `queries.py` (Paradigm B)

`_get_runtime_queries` (`mysql.py:458-481`) assembles these conditionally and compiles via the base `QueryExecutor`:
- `QUERY_DEADLOCKS` (`queries.py:207-218`) — added iff InnoDB enabled. From `information_schema.INNODB_METRICS WHERE NAME='lock_deadlocks'`; metric `mysql.innodb.deadlocks` (`monotonic_count`).
- `QUERY_USER_CONNECTIONS` (`queries.py:220-243`) — added iff perf_schema. From `performance_schema.threads` grouped by user/host/db/state; metric `mysql.performance.user_connections` (gauge) + 4 tag columns (`processlist_user/host/db/state`).
- `QUERY_WAIT_EVENT_SUMMARY` (`queries.py:265-286`) — added iff perf_schema AND dbm_enabled. From `events_waits_summary_global_by_event_name`, top 200 by `sum_timer_wait`; metrics `mysql.performance.wait_event.count` (monotonic_count), `.time` (monotonic_count, /1000 ns), `.avg_time` (gauge), `.max_time` (gauge); tag `wait_event`.
- `QUERY_ERRORS_RAISED` (`queries.py:245-263`) — added iff perf_schema AND dbm AND ≥8.0.0. From `events_errors_summary_global_by_error`; metric `mysql.performance.errors_raised` (monotonic_count); tags `error_number`,`error_name`.

Raw SQL strings (used by Paradigm A helper methods, not QueryExecutor) in `queries.py`:
- `SQL_95TH_PERCENTILE` (`queries.py:5-13`) → `_get_query_exec_time_95th_us` (`mysql.py:1242-1262`).
- `SQL_AVG_QUERY_RUN_TIME` (`queries.py:43-47`) → `_query_exec_time_per_schema` (`mysql.py:1264-1290`), builds `{"schema:<name>": avg_us}` dict.
- `SQL_QUERY_SCHEMA_SIZE` (`queries.py:24-27`) → `_query_size_per_schema` (`mysql.py:1322-1345`), `{"schema:<name>": MiB}`.
- `SQL_QUERY_TABLE_SIZE` / `SQL_QUERY_SYSTEM_TABLE_SIZE` (`queries.py:29-41`) → `_query_size_per_table` (`mysql.py:1292-1320`), `{"schema:<s>,table:<t>": MiB}` for index and data.
- `SQL_QUERY_TABLE_ROWS_STATS` (`queries.py:15-22`) → `_query_rows_stats_per_table` (`mysql.py:1347-1371`) — from `performance_schema.table_io_waits_summary_by_table`.
- `SQL_INNODB_ENGINES` (`queries.py:55-58`) → `_check_innodb_engine_enabled` (`mysql.py:1144-1164`).
- Replication SQL: `SQL_REPLICA_WORKER_THREADS`, `SQL_REPLICA_PROCESS_LIST`, `SQL_REPLICATION_ROLE_AWS_AURORA`, `SQL_GROUP_REPLICATION_*`, `show_replica_status_query()` (`queries.py:49-90`, `289-297`).

These per-schema / per-table dicts are submitted through Paradigm A: the dict value is recognized by `collect_all_scalars` and expanded into one metric-per-tag (`collection_utils.py:9-16`, `mysql.py:980-988`).

---

## 7. Submission internals — `_submit_metrics` / type coercion

`_submit_metrics(variables, db_results, tags)` (`mysql.py:969-977`): for each `(variable, metric)` in the mapping, if `metric` is a list (aliases) submit each, else submit one.

`__submit_metric(metric_name, metric_type, variable, db_results, tags)` (`mysql.py:979-997`):
- `collect_all_scalars(variable, db_results)` yields `(tag, value)`. If the result is a plain scalar → `(None, float(value))`; if a dict → one yield per key (`collection_utils.py:9-16`).
- Tag handling: comma-separated tag string is split into multiple tags (`mysql.py:983-988`).
- Dispatch by type: `RATE`→`self.rate`, `GAUGE`→`self.gauge`, `COUNT`→`self.count`, `MONOTONIC`→`self.monotonic_count` (`mysql.py:990-997`). All carry `hostname=self.reported_hostname`.

Type coercion (`collection_utils.py`):
- `collect_scalar(key, mapping)` = `collect_type(key, mapping, float)` (`:19-20`)
- `collect_string` = `..., str` (`:23-24`)
- `collect_type` returns `None` if key missing, else `the_type(mapping[key])` (`:27-33`)
- Missing keys silently produce no metric — graceful degradation is the norm.

`_collect_dict(metric_type, field_metric_map, query, db, tags)` (`mysql.py:999-1040`): used for **custom queries**; runs SQL, matches result columns by name (case-insensitive against `cursor.description`), submits each mapped field as gauge/rate.

---

## 8. Global variables cache — `global_variables.py` (directly portable concept)

`class GlobalVariables` (`global_variables.py:14-122`):
- `collect(db)` runs `SHOW GLOBAL VARIABLES;` once and stores `dict(cursor.fetchall())` (`:25-34`).
- `_get_variable(name, default)` / `_get_variable_enabled(name)` (ON/YES/1 via `is_affirmative`) (`:36-62`).
- Typed properties used as capability/config gates throughout: `version`, `version_comment`, `server_uuid`, `performance_schema_enabled`, `userstat_enabled`, `pid_file`, `aurora_server_id`, `is_aurora`, `log_bin_enabled`, `key_buffer_size`, `key_cache_block_size`, `all_variables` (`:64-121`).
- `all_variables` is merged straight into `results` so `VARIABLES_VARS` can be submitted (`mysql.py:599`).

> Db2 analog: collect `SYSIBMADM.DBMCFG` / `DB CFG` / `MON_GET_*` configuration once per run, expose typed accessors and capability gates (e.g. whether a given monitoring function/authority is available, edition features), mirror this caching pattern to avoid repeated round-trips.

---

## 9. System (CPU) metrics — `mysql.py:1062-1118` (host-local only)
`_collect_system_metrics`: only when MySQL runs locally (`localhost`/`127.0.0.1`/`0.0.0.0` or port 0) and `psutil` available. Resolves server PID (`pid_file` then `psutil.process_iter()` matching `mysqld`/`mariadbd`, `mysql.py:1090-1118`), then emits `mysql.performance.user_time`, `mysql.performance.kernel_time`, `mysql.performance.cpu_time` (all RATE, from `proc.cpu_times()`). Db2: not portable in containerized/remote setups; Db2 exposes CPU via `ENV_SYS_RESOURCES` / `MON_GET_*` instead — prefer SQL.

---

## 10. metadata.csv — the metric catalog & how it maps

`/home/bits/dd/integrations-core/mysql/metadata.csv` (256 rows incl. header). Header columns:
`metric_name,metric_type,interval,unit_name,per_unit_name,description,orientation,integration,short_name,curated_metric`

Mapping rules observed:
- **`metric_name`** is exactly the Datadog metric name from the `const.py` mapping value or the QueryExecutor `columns[].name` (e.g. `mysql.innodb.data_reads`, `mysql.index.size`, `mysql.performance.user_connections`).
- **`metric_type`** in CSV uses `gauge` / `count` (note: `RATE` metrics are catalogued as `gauge` because the agent submits rate-per-second as a gauge sample; `MONOTONIC` → `count`). Examples: `mysql.innodb.deadlocks,count` (from a `monotonic_count`); `mysql.performance.wait_event.count,count`; `mysql.galera.wsrep_flow_control_paused_ns,count`. Most RATE entries (e.g. `mysql.performance.com_select`) appear as `gauge`.
- **`unit_name`/`per_unit_name`**: human units, e.g. `byte`, `page`,`second`; `read`/`second`, `query`/`second`, `mebibyte`, `microsecond`, `nanosecond`, `connection`, `transaction`, `operation`, `fraction`, `percent`. (See examples: `mysql.innodb.data_read,gauge,,byte,second,...`; `mysql.info.schema.size,gauge,,mebibyte,...`.)
- **`description`**: prose; several DBM-only metrics annotate `(DBM only)` and list tag keys, e.g. `mysql.performance.user_connections` lists `processlist_*` tags; `mysql.performance.errors_raised` lists `error_number,error_name`.
- **`orientation`**: -1 / 0 / 1 (good-direction hint). e.g. `mysql.innodb.buffer_pool_free` =1, `mysql.innodb.buffer_pool_used` =-1, `mysql.replication.seconds_behind_*` =-1.
- **`integration`** = `mysql` for all rows.
- **`short_name`**: free-text display label.
- **`curated_metric`**: tag like `cpu` / `memory` for curated dashboards (e.g. `mysql.net.connections,...,cpu`; `mysql.innodb.mem_total,...,memory`).

Notable catalog groupings present in metadata.csv (line ranges):
- `mysql.binlog.*` (2-4), `mysql.galera.*` (5-19), `mysql.index.*` (20-23), `mysql.info.*` (24-28), `mysql.innodb.*` (29-129), `mysql.myisam.*` (130-136), `mysql.net.*` (137-141), `mysql.performance.*` (142-221), `mysql.queries.*` (222-241, DBM statement metrics), `mysql.replication.*` (242-255).

> Db2 takeaway: every metric the check emits MUST have a matching row in `/home/bits/dd/integrations-core/ibm_db2/metadata.csv` (currently only 49 metrics + header — `wc -l` = 50). The fidelity plan should produce: (a) the variable→metric mapping (const-style), (b) the corresponding metadata.csv rows with units/orientation/curated tags. CSV `metric_type` must use the **catalog** vocabulary (`gauge`/`count`/`rate`/`monotonic_count` as appropriate), not the Python constant string.

---

## 11. Db2-specific implications (synthesis for the implementer)

1. **Prefer Paradigm B** (declarative query dicts like `index_metrics.py`/`queries.py`) for almost all Db2 metrics. Db2 12.1 monitoring is fully relational (`MON_GET_*` table functions, `SYSIBMADM` admin views, `ENV_*`), so each metric family is one `SELECT` with metric/tag columns. This avoids the brittle text-parsing of `innodb_metrics.py`.
2. **One cached config/variables fetch per run** (mirror `GlobalVariables`): pull DBM CFG / DB CFG / edition / monitoring-authority once, expose typed gates.
3. **Capability gating**: replace `version.version_compatible(...)` with Db2-version / edition / authority checks. Target is 12.1 (live 12.1.4) — all 12.1 monitoring functions assumed available; still gate optional/heavy collectors (e.g. per-table, per-index top-N) behind config options exactly like `extra_status_metrics`, `table_size_metrics`, `index_config.enabled`.
4. **Graceful degradation**: wrap each collector, catch driver errors, log a warning about the missing authority (MySQL warns "must grant PROCESS/REPLICATION CLIENT"; Db2 analog: SYSMON/DBADM/required authorities) and continue. See `innodb_metrics.py:35-46`, `mysql.py:1140-1142`, `1229-1231`.
5. **Per-object metrics via tag-dicts or query columns**: MySQL emits per-schema/per-table/per-index with `schema:`/`table:`/`index:` tags. Db2 equivalents: tag by `tabschema`,`tabname`,`indschema`,`indname`,`bp_name` (buffer pool), `tbsp_name` (table space), `member` (for pureScale/MPP). Cap cardinality with top-N limits like `index_limit`.
6. **metric_type discipline**: counters that monotonically increase (Db2 `MON_GET_*` lifetime counters like `ROWS_READ`, `POOL_DATA_L_READS`) → `monotonic_count` (CSV `count`); point-in-time gauges (`APPLS_CUR_CONS`, buffer pool hit ratio) → `gauge`. The existing ibm_db2 metadata.csv already follows this (`...reads.logical,count`, `...hit_percent,gauge`).
7. **Every emitted metric needs a metadata.csv row** with `integration=ibm_db2`, sensible `unit_name`/`per_unit_name`, `orientation`, and optional `curated_metric` (`cpu`/`memory`).
8. **tracked_query timing**: wrap each Db2 collector in `tracked_query(self, operation="...")` for per-operation observability, as MySQL does.

---

## 12. Quick file-reference index (all absolute)
- Orchestrator / flow: `/home/bits/dd/integrations-core/mysql/datadog_checks/mysql/mysql.py`
  - `check()` 382-441; `_collect_metrics()` 590-782; `_submit_metrics/__submit_metric` 969-997; `_get_runtime_queries` 458-481; `_get_stats_from_status` 1120-1126; per-schema/table helpers 1264-1371; `_collect_system_metrics` 1062-1118; replication 784-967, 1166-1232, 1438-1462.
- Metric mappings: `/home/bits/dd/integrations-core/mysql/datadog_checks/mysql/const.py` (all dicts, lines per §3).
- InnoDB text parse: `/home/bits/dd/integrations-core/mysql/datadog_checks/mysql/innodb_metrics.py` (parse 26-376; post-process 378-420).
- Index (Paradigm B): `/home/bits/dd/integrations-core/mysql/datadog_checks/mysql/index_metrics.py`.
- Declarative + raw SQL: `/home/bits/dd/integrations-core/mysql/datadog_checks/mysql/queries.py`.
- Coercion helpers: `/home/bits/dd/integrations-core/mysql/datadog_checks/mysql/collection_utils.py`.
- Variable cache: `/home/bits/dd/integrations-core/mysql/datadog_checks/mysql/global_variables.py`.
- Metric catalog: `/home/bits/dd/integrations-core/mysql/metadata.csv`.
- Db2 target (to extend): `/home/bits/dd/integrations-core/ibm_db2/datadog_checks/ibm_db2/` (`ibm_db2.py`, `queries.py`, `utils.py`) and `/home/bits/dd/integrations-core/ibm_db2/metadata.csv`.
