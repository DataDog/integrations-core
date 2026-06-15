# Postgres Integration — METRICS Collection (non-DBM core check)

Raw research input for the IBM Db2 fidelity plan. Covers how the Postgres integration collects
standard *metrics* (the `_collect_stats` path), **excluding** DBM (statements/samples/metadata/schemas).
All code refs are absolute paths into `/home/bits/dd/integrations-core`. Db2 claims cite the live raw
files under `.../ibm_db2/dev-docs/db2-fidelity-plan/_research/_raw/` where supported, else marked
"(general Db2 12.1 knowledge — verify)".

Key files:
- `/home/bits/dd/integrations-core/postgres/datadog_checks/postgres/postgres.py` — orchestration (`check`, `_collect_stats`, `dynamic_queries`, `_query_scope`, `_run_query_scope`, tags).
- `/home/bits/dd/integrations-core/postgres/datadog_checks/postgres/metrics_cache.py` — version-conditional metric set selection for the legacy scope-dict path.
- `/home/bits/dd/integrations-core/postgres/datadog_checks/postgres/util.py` — almost all metric dicts + SQL (both legacy "scope" dicts and new QueryExecutor dicts).
- `/home/bits/dd/integrations-core/postgres/datadog_checks/postgres/relationsmanager.py` — per-relation metric dicts + relation WHERE-clause builder.
- `/home/bits/dd/integrations-core/postgres/datadog_checks/postgres/version_utils.py` — version parsing and `V*` constants, Aurora detection.
- `/home/bits/dd/integrations-core/postgres/metadata.csv` — metric catalog (name, type, unit, description, tags).
- `/home/bits/dd/integrations-core/postgres/datadog_checks/postgres/config_models/defaults.py` + `config.py` — config flags/defaults that gate metric categories.

---

## 1. Two parallel metric-collection mechanisms

The Postgres integration uses **two different in-code representations** for metrics. This is important
for Db2: the integration is mid-migration from the old style to the new style.

### A. Legacy "scope dict" path (`_query_scope` / `_run_query_scope`)
Used for the core `pg_stat_database`-style metrics. A *scope* is a dict shaped like:

```python
{
  'descriptors': [('psd.datname', 'db')],          # (sql_column_or_expr, tag_name) — produce tags
  'metrics': {'xact_commit': ('commits', AgentCheck.rate), ...},  # sql_col/expr -> (metric_suffix, submit_fn)
  'query': "SELECT psd.datname, {metrics_columns} FROM pg_stat_database psd ...",
  'relation': False,
  'name': 'instance_metrics',
  'use_global_db_tag': False,   # optional
}
```
The submit function is one of `AgentCheck.gauge`, `AgentCheck.rate`, `AgentCheck.monotonic_count`,
`AgentCheck.count`. The `{metrics_columns}` placeholder is filled by joining the keys of `metrics`
(`postgres.py:768` `fmt.format(scope['query'], metrics_columns=", ".join(cols))`). Result rows are
parsed positionally: first `len(descriptors)` columns become tags, remaining columns map 1:1 to
`metrics` keys in dict order (`_query_scope`, `postgres.py:843-892`). The metric name submitted is
`__NAMESPACE__` (`'postgresql'`, `postgres.py:111`) + `.` + the suffix, i.e. `commits` →
`postgresql.commits`.

### B. New "QueryExecutor / QueryManager" path (the `datadog_checks.base` framework)
Used for all the newer dicts in `util.py` (those with a `columns` list instead of `metrics`/`descriptors`).
Shape:

```python
{
  'name': 'pg_stat_database',
  'query': "SELECT datname, deadlocks FROM pg_stat_database",
  'columns': [
    {'name': 'db', 'type': 'tag'},
    {'name': 'deadlocks.count', 'type': 'monotonic_count'},
  ],
}
```
Column `type` values seen: `tag`, `tag_not_null` (drops the tag when value is NULL), `gauge`,
`monotonic_count`, `rate`, `count`. These are resolved by the base transformer registry
(`/home/bits/dd/integrations-core/datadog_checks_base/datadog_checks/base/utils/db/transform.py:611`,
`'tag_not_null': get_tag`). These dicts are wrapped by `_new_query_executor` (`postgres.py:298`) which
attaches `tags=self.tags_without_db` and `hostname=self.reported_hostname`, then `compile_queries()`.
They run via `self.dynamic_queries` (`postgres.py:364-484`) and execute at the end of `_collect_stats`
(`postgres.py:1065`). The framework prefixes metric names with `postgresql.` automatically via
`__NAMESPACE__`. **For Db2, prefer this new style for all new queries** — `relationsmanager.py:5-17`
explicitly marks the legacy scope-dict approach as pending deprecation.

---

## 2. Top-level orchestration (`check` → `_collect_stats`)

`check()` (`postgres.py:1230`):
1. `_connect()`, `load_version()` (re-read every run to catch minor upgrades; not cached, `postgres.py:1242`).
2. `wal_level = _get_wal_level()`.
3. Append dynamic instance tags: `postgresql_version:<raw_version>`, `system_identifier:<id>`,
   `postgresql_cluster_name:<name>`, `replication_role:<primary|standby>` (if `tag_replication_role`).
   (`postgres.py:1248-1265`).
4. `_send_database_instance_metadata()`, `_emit_running_metric()` (emits `postgresql.running=1`).
5. If not `only_custom_queries`: `_collect_stats(tags)`; then DBM job loops if `dbm`; then WAL metrics
   for PG<10 if `collect_wal_metrics is True`.
6. Run `_query_manager` for custom queries.

`_collect_stats(instance_tags)` (`postgres.py:961-1063`) assembles the scope list, then runs each:
- `db_instance_metrics = metrics_cache.get_instance_metrics(version)` (pg_stat_database core).
- `bgw_instance_metrics = metrics_cache.get_bgw_metrics(version)` (bgwriter/checkpointer).
- `archiver_instance_metrics = metrics_cache.get_archiver_metrics(version)` (pg_stat_archiver).
- `metric_scope = [CONNECTION_METRICS]`; append `CONNECTION_METRICS_BY_DB` (formatted with
  ignore-database filter).
- `per_database_metric_scope`: `FUNCTION_METRICS` if `collect_function_metrics`; `COUNT_METRICS` if
  `collect_count_metrics`.
- `SLRU_METRICS` appended to `metric_scope` if `version >= V13`.
- If `relations`: `RELATION_METRICS` (= `[STATIO_METRICS]`); plus `INDEX_BLOAT`, `TABLE_BLOAT` if
  `collect_bloat_metrics`. Run per-database via autodiscovery, else added to `metric_scope`.
- `replication_metrics = metrics_cache.get_replication_metrics(version, is_aurora)`; wraps into
  `REPLICATION_METRICS` scope.
- Submits `db_instance_metrics`, emits `postgresql.db.count` = number of rows returned (databases seen).
- `bgw`, `archiver` scopes.
- Checksums: if `collect_checksum_metrics and version >= V12`, runs `SHOW data_checksums;` and emits
  `postgresql.checksums.enabled` count with tag `enabled:true|false` (`postgres.py:1031-1042`).
- Activity metrics if `collect_activity_metrics` (`get_activity_metrics`).
- Per-database scopes via autodiscovery if enabled, else added to `metric_scope`.
- Loops all `metric_scope` via `_query_scope`.
- Custom metrics via `_query_scope(scope, ..., is_custom_metrics=True)`.
- Finally `dynamic_queries` (the new-style QueryExecutor dicts) are executed (`postgres.py:1065-1067`).

Error handling (`_run_query_scope`, `postgres.py:804-825`): `FeatureNotSupported` (Aurora reader) →
disable replication metrics; `UndefinedFunction` → wrong version assumed, `_clean_state()` to re-detect;
`ProgrammingError`/`QueryCanceled` → "not all metrics available"; generic `psycopg.Error` → log+skip.
**Db2 analog:** wrap each monitoring-table query so a missing `MON_GET_*` function or insufficient
privilege degrades gracefully rather than failing the whole check.

---

## 3. Version detection & gating

- `version_utils.py` defines `V8_3 … V18` as `semver.VersionInfo`. `get_raw_version` runs
  `SHOW SERVER_VERSION;`. `parse_version` handles MAJOR.MINOR.PATCH, missing-minor (`10.0`),
  edition suffixes (`12.3_TDE_1.0`), dev versions (`16beta1`), and RDS EOL format (`11.22-rds.20241121`).
- `is_aurora(db)`: queries `pg_available_extension_versions` for `%aurora%` then `AURORA_VERSION()`.
  Aurora suppresses replication metrics, WAL receiver, `pg_stat_wal`, and (when not logical wal_level)
  control checkpoint LSN diffs.
- Version gating is done in **two places**:
  - `metrics_cache.py` for the legacy scopes (instance/bgw/archiver/replication/activity).
  - `postgres.py:dynamic_queries` (`375-454`) for the new-style dicts (explicit `if self.version >= V*`).

**Db2 analog (general Db2 12.1 knowledge — verify):** detect version via `SELECT service_level,
fixpack_num FROM TABLE(SYSPROC.ENV_GET_INST_INFO())` or `db2level`. The raw file
`_raw/01-version-and-monget-functions.txt` confirms which `MON_GET_*` table functions exist on the live
target; gate any version-specific monitoring functions on that. Db2 monitoring views vary by edition
(e.g., pureScale-only `MON_GET_*` member columns).

---

## 4. Metric CATEGORIES (exhaustive)

Below, each category lists: trigger/gating, SQL source object, the metric→column mapping, types, units,
tags. Metric name = `postgresql.<suffix>`. Source unless noted is `util.py`.

### 4.1 Instance / database stats — `pg_stat_database` (legacy scope `instance_metrics`)
`metrics_cache.get_instance_metrics` (`metrics_cache.py:63-115`). Query (`metrics_cache.py:100`):
```sql
SELECT psd.datname, {metrics_columns}
FROM pg_stat_database psd JOIN pg_database pd ON psd.datname = pd.datname
WHERE 1=1 [AND psd.datname in('<dbname>')  -- if dbstrict]
          [AND psd.datname not ilike '<db>' ... -- per ignore_databases]
```
Descriptor: `('psd.datname','db')` → tag `db:<name>`. Submitted per-database (pg_stat_database returns
ALL databases regardless of connection; `db` descriptor overrides the instance `db` tag,
`postgres.py:867-870`).

`COMMON_METRICS` (`util.py:418`) — always:
| SQL column/expr | metric (`postgresql.`) | type |
|---|---|---|
| `xact_commit` | `commits` | rate |
| `xact_rollback` | `rollbacks` | rate |
| `blks_read` | `disk_read` | rate (unit block/s) |
| `blks_hit` | `buffer_hit` | rate (unit hit/s) |
| `tup_returned` | `rows_returned` | rate |
| `tup_fetched` | `rows_fetched` | rate |
| `tup_inserted` | `rows_inserted` | rate |
| `tup_updated` | `rows_updated` | rate |
| `tup_deleted` | `rows_deleted` | rate |
| `2^31 - age(datfrozenxid) as wraparound` | `before_xid_wraparound` | gauge |

`DBM_MIGRATED_METRICS` (`util.py:414`) — added **only when NOT dbm** (`metrics_cache.py:79`):
`numbackends` → `connections` (gauge). When `dbm`, `connections` is collected by DBM instead.

`NEWER_92_METRICS` (`util.py:433`, version ≥ V9_2): `deadlocks`→`deadlocks` (rate),
`temp_bytes`→`temp_bytes` (rate), `temp_files`→`temp_files` (rate),
`blk_read_time`→`blk_read_time` (monotonic_count, ms), `blk_write_time`→`blk_write_time` (monotonic_count, ms).

`NEWER_14_METRICS` (`util.py:443`, version ≥ V14): session timing/counters →
`sessions.session_time`, `sessions.active_time`, `sessions.idle_in_transaction_time`, `sessions.count`,
`sessions.abandoned`, `sessions.fatal`, `sessions.killed` (all monotonic_count).

`DATABASE_SIZE_METRICS` (`util.py:431`, if `collect_database_size_metrics` — default **True**):
`pg_database_size(psd.datname) as pg_database_size` → `database_size` (gauge, byte).

`CHECKSUM_METRICS` (`util.py:441`, if `collect_checksum_metrics` and version ≥ V12):
`checksum_failures` → `checksums.checksum_failures` (monotonic_count).

**Db2 analog:** `MON_GET_DATABASE` (per-database/member; columns confirmed in `_raw/02-monget-key-columns.txt`)
provides commit/rollback (`COMMIT_SQL_STMTS`, `ROLLBACK_SQL_STMTS`), buffer pool logical/physical reads
(`POOL_DATA_L_READS`/`POOL_DATA_P_READS`...), rows read/returned (`ROWS_READ`, `ROWS_RETURNED`),
deadlocks (`DEADLOCKS`), `LOG_READS`/`LOG_WRITES`, `TOTAL_APP_COMMITS`. Database size via
`SYSPROC.ADMIN_GET_DBSIZE_INFO()` or `MON_GET_TABLESPACE` summation (general Db2 12.1 knowledge — verify).

### 4.2 Background writer / checkpointer — `pg_stat_bgwriter` (+ `pg_stat_checkpointer` on PG17+)
`metrics_cache.get_bgw_metrics` (`metrics_cache.py:117-143`).
- **PG ≥ V17:** returns `QUERY_PG_BGWRITER_CHECKPOINTER` (`util.py:567`) — joins
  `pg_stat_bgwriter bg, pg_stat_checkpointer cp` (checkpoint counters moved to the new view in PG17).
- **PG < V17:** `COMMON_BGW_METRICS_LT_17` (`util.py:595`) +`NEWER_91_BGW_METRICS_LT_17` (V9_1+) +
  `NEWER_92_BGW_METRICS_LT_17` (V9_2+). Query `select {metrics_columns} FROM pg_stat_bgwriter`.

Metrics (all `postgresql.bgwriter.*`, monotonic_count): `checkpoints_timed`, `checkpoints_requested`
(from `checkpoints_req`), `buffers_checkpoint`, `buffers_clean`, `maxwritten_clean`,
`buffers_backend` (LT_17 only), `buffers_backend_fsync` (V9_1 LT_17 only), `buffers_alloc`,
`write_time` (from `checkpoint_write_time`, ms), `sync_time` (from `checkpoint_sync_time`, ms).

**Db2 analog:** page cleaner / write activity from `MON_GET_BUFFERPOOL` and `MON_GET_DATABASE`
(`POOL_WRITES`, `POOL_ASYNC_DATA_WRITES`, `NUM_LOG_WRITE_IO`, ...). See `_research/map-bufferpool.md`.

### 4.3 Archiver — `pg_stat_archiver` (PG ≥ V9_4)
`metrics_cache.get_archiver_metrics` (`metrics_cache.py:145-164`). `COMMON_ARCHIVER_METRICS` (`util.py:612`):
`archived_count`→`archiver.archived_count`, `failed_count`→`archiver.failed_count` (monotonic_count).
Query: `select {metrics_columns} FROM pg_stat_archiver`.

**Db2 analog (general — verify):** log archiving status via `MON_GET_TRANSACTION_LOG` /
`db2pd -logs`; HADR log shipping in `MON_GET_HADR` (see `_research/map-hadr-replication.md`).

### 4.4 Connections — instance-wide + per-database
`CONNECTION_METRICS` (`util.py:849`) — always (in `metric_scope`):
```sql
WITH max_con AS (SELECT setting::float FROM pg_settings WHERE name='max_connections')
SELECT {metrics_columns} FROM pg_stat_database, max_con
```
`MAX(setting) AS max_connections` → `max_connections` (gauge); `SUM(numbackends)/MAX(setting) AS
pct_connections` → `percent_usage_connections` (gauge). No descriptors (instance-level).

`CONNECTION_METRICS_BY_DB` (`util.py:826`) — always, per-database tag `db`:
`connections`→`database_connections` (gauge), `pct_connections`→`percent_database_usage_connections`
(gauge). `{ignore_database_filter}` filled from `ignore_databases` at runtime (`postgres.py:973-980`).

**Db2 analog:** `MON_GET_CONNECTION` / `MON_GET_DATABASE` (`APPLS_CUR_CONS`, `APPLS_IN_DB2`),
`SYSIBMADM.APPLICATIONS`; max via `MAXAPPLS`/`MAX_CONNECTIONS` DB cfg (general Db2 12.1 knowledge — verify).

### 4.5 Activity — `pg_stat_activity` aggregates (if `collect_activity_metrics`, default **False**)
`metrics_cache.get_activity_metrics` (`metrics_cache.py:186-251`). Two base queries selected by version:
`ACTIVITY_QUERY_10` (PG≥10; `WHERE backend_type='client backend' AND query !~* '^vacuum '`) or
`ACTIVITY_QUERY_LT_10` (`util.py:1260-1274`). `GROUP BY datid {aggregation_columns}`.

Aggregation/descriptor columns (`metrics_cache.py:198`): `application_name`→`app`, `datname`→`db`,
`usename`→`user`. `datname` is required; users can drop `app`/`user` via
`activity_metrics_excluded_aggregations`. PG<9 drops `application_name`.

The metric expressions are version-tiered lists (`ACTIVITY_METRICS_10` / `_9_6` / `_9_2` / `_8_3` /
`_LT_8_3`, `util.py:1134-1245`) zipped against `ACTIVITY_DD_METRICS` (`util.py:1248`):
| position | expr (PG10) | metric (`postgresql.`) | type |
|---|---|---|---|
| 1 | `SUM(CASE WHEN xact_start IS NOT NULL ...)` | `transactions.open` | gauge |
| 2 | `SUM(CASE WHEN state='idle in transaction' ...)` | `transactions.idle_in_transaction` | gauge |
| 3 | `COUNT(... state='active' AND usename NOT IN ('postgres','{dd__user}'))` | `active_queries` | gauge |
| 4 | `COUNT(... wait_event IS NOT NULL)` | `waiting_queries` | gauge |
| 5 | `COUNT(... wait_event IS NOT NULL AND state='active')` | `active_waiting_queries` | gauge |
| 6 | `max(EXTRACT(EPOCH FROM clock_timestamp()-xact_start))` | `activity.xact_start_age` | gauge |
| 7 | `max(age(backend_xid))` | `activity.backend_xid_age` | gauge |
| 8 | `max(age(backend_xmin))` | `activity.backend_xmin_age` | gauge |
`{dd__user}` is substituted with the configured username (`metrics_cache.py:236`). Older versions use
`waiting='t'` instead of `wait_event`, and `current_query LIKE '<IDLE> in transaction'`.

`QUERY_PG_WAIT_EVENT_METRICS` (`util.py:809`, new-style, PG≥10): per `(app, db, user, wait_event,
backend_type)` COUNT(*) → `activity.wait_event` (gauge); `wait_event` COALESCE'd to `'NoWaitEvent'`.

**Db2 analog:** `MON_GET_ACTIVITY` / `MON_GET_AGENT` / `WLM_GET_WORKLOAD_OCCURRENCE_ACTIVITIES`;
wait events via `MON_GET_ACTIVITY` `WLM_QUEUE_TIME_TOTAL`, lock waits, agent states. See
`_research/db2-live-activity.md`.

### 4.6 Replication
**`get_replication_metrics`** (`metrics_cache.py:166-184`) wrapped in `REPLICATION_METRICS`
(`util.py:673`, `WHERE (SELECT pg_is_in_recovery())`). Suppressed on Aurora.
- PG≥10 `REPLICATION_METRICS_10` (`util.py:653`): `replication_delay` (gauge, seconds, via
  `pg_last_xact_replay_timestamp`), `replication_delay_bytes` (gauge, via `pg_wal_lsn_diff`).
- PG9_1 `REPLICATION_METRICS_9_1`; PG9_2 adds `_9_2` (`replication_delay_bytes`).

**New-style replication dicts (PG≥10, non-Aurora) in `dynamic_queries`:**
- `QUERY_PG_REPLICATION_STATS_METRICS` (`util.py:684`): from `pg_stat_replication` LEFT JOIN
  `pg_replication_slots`. Tags: `wal_app_name`, `wal_state`, `wal_sync_state`, `wal_client_addr`,
  `slot_name`/`slot_type` (tag_not_null). Metrics (`replication.*`, gauge): `backend_xmin_age`,
  `sent_lsn_delay`, `write_lsn_delay`, `flush_lsn_delay`, `replay_lsn_delay`, `wal_write_lag`,
  `wal_flush_lag`, `wal_replay_lag`.
- `QUERY_PG_STAT_WAL_RECEIVER` (`util.py:729`): tag `status`; `wal_receiver.connected`,
  `received_timeline`, `last_msg_send_age`, `last_msg_receipt_age`, `latest_end_age` (gauge).
- `QUERY_PG_REPLICATION_SLOTS` (`util.py:752`): tags `slot_name/type/persistence/state`;
  `replication_slot.{xmin_age,catalog_xmin_age,restart_delay_bytes,confirmed_flush_delay_bytes}` (gauge).
- `QUERY_PG_REPLICATION_SLOTS_STATS` (`util.py:781`, PG≥14): from `pg_stat_replication_slots`;
  `replication_slot.{spill_txns,spill_count,spill_bytes,stream_txns,stream_count,stream_bytes,
  total_txns,total_bytes}` (monotonic_count).
- Subscriptions: `STAT_SUBSCRIPTION_METRICS` (PG≥10), `SUBSCRIPTION_STATE_METRICS` (PG≥14),
  `STAT_SUBSCRIPTION_STATS_METRICS` (PG≥15) — `subscription.*`.

**Db2 analog:** HADR via `MON_GET_HADR` (log gap, standby state, connect status, time-to-replay).
See `_research/map-hadr-replication.md`.

### 4.7 Control / checkpoint / WAL / snapshot (new-style, in `dynamic_queries`)
- `QUERY_PG_CONTROL_CHECKPOINT` (PG≥10, `util.py:546`) / `_LT_10` (`util.py:525`): from
  `pg_control_checkpoint()`. `control.{timeline_id,checkpoint_delay,checkpoint_delay_bytes,
  redo_delay_bytes}` (gauge). Suppressed on Aurora unless logical wal_level.
- `WAL_FILE_METRICS` (PG≥10 non-Aurora, unless `collect_wal_metrics is False`, `util.py:1048`): from
  `pg_ls_waldir()`. `wal_count` (gauge), `wal_size` (gauge, byte), `wal_age` (gauge, second).
- `STAT_WAL_METRICS_LT_18` (PG14–17) / `STAT_WAL_METRICS` (PG≥18, `util.py:1064/1086`): from
  `pg_stat_wal`. `wal.{records,full_page_images,bytes,buffers_full,write,sync,write_time,sync_time}`
  (monotonic_count; the last 4 dropped on PG18). Non-Aurora.
- `SNAPSHOT_TXID_METRICS` (PG≥13) / `_LT_13` (`util.py:883/903`): `snapshot.{xmin,xmax,xip_count}` (gauge).
- `QUERY_PG_UPTIME` (`util.py:517`, PG≥9_2): `uptime` (gauge, second) from `pg_postmaster_start_time()`.
- `QUERY_PG_STAT_RECOVERY_PREFETCH` (PG≥15, `util.py:489`): `recovery_prefetch.*`.

**WAL collection for PG<10** (`postgres.py:1283`, `_collect_wal_metrics`): only if `collect_wal_metrics
is True`; reads the local WAL directory on the filesystem (needs agent co-located). Emits
`postgresql.wal_age` / `wal_count` / `wal_size` from local files.

### 4.8 Conflicts & deadlocks — `pg_stat_database` / `pg_stat_database_conflicts` (new-style, PG≥9_2)
- `QUERY_PG_STAT_DATABASE` (`util.py:453`): `datname`→`db` tag, `deadlocks`→`deadlocks.count`
  (monotonic_count). (This complements the rate-based `postgresql.deadlocks` from §4.1.)
- `QUERY_PG_STAT_DATABASE_CONFLICTS` (`util.py:467`): tag `db`; `conflicts.{tablespace,lock,snapshot,
  bufferpin,deadlock}` (monotonic_count). Both honor `ignore_databases` and `dbstrict` filters
  appended at runtime (`postgres.py:377-392`).

### 4.9 SLRU — `pg_stat_slru` (PG≥V13, in `metric_scope`)
`SLRU_METRICS` (`util.py:864`): descriptor `name`→`slru_name`; `slru.{blks_zeroed,blks_hit,blks_read,
blks_written,blks_exists,flushes,truncates}` (monotonic_count).

### 4.10 Functions — `pg_stat_user_functions` (if `collect_function_metrics`, default **False**)
`FUNCTION_METRICS` (`util.py:1101`), per-database (`use_global_db_tag: True`). Descriptors
`schemaname`→`schema`, `funcname`→`function` (overloaded functions disambiguated by arg names).
Metrics: `function.calls` (rate), `function.total_time` (rate), `function.self_time` (rate).

### 4.11 Table count — `pg_class` (if `collect_count_metrics`, default **True**)
`COUNT_METRICS` (`util.py:629`), per-database (`use_global_db_tag: True`). Counts ordinary + partitioned
tables (`relkind IN ('r','p')`) grouped by schema, excluding `pg_catalog`/`information_schema`.
Descriptor `schemaname`→`schema`; `count (*)`→`table.count` (gauge). Comment (`util.py:618-628`)
explains it deliberately avoids `pg_stat_user_tables` to dodge sorts/temp-spill.

### 4.12 Buffercache — `pg_buffercache` (if `collect_buffercache_metrics`, PG≥10, default **False**)
`BUFFERCACHE_METRICS` (`util.py:1158`), new-style. CTE aggregates by `(reldatabase, relfilenode)` then
joins `pg_database`/`pg_class`/`pg_namespace`. Tags `db`, `schema`/`relation` (tag_not_null). Metrics
(`buffercache.*`, gauge): `used_buffers`, `unused_buffers`, `usage_count`, `dirty_buffers`,
`pinning_backends`. Detailed perf rationale in `util.py:1145-1157`.

### 4.13 Progress views (new-style)
- `VACUUM_PROGRESS_METRICS` (PG≥17) / `_LT_17` (PG≥10) (`util.py:920/943`): from
  `pg_stat_progress_vacuum` JOIN `pg_class`. Tags `db,table,phase`; `vacuum.{heap_blks_total,
  heap_blks_scanned,heap_blks_vacuumed,index_vacuum_count,max_dead_tuples,num_dead_tuples}` (gauge).
- `CLUSTER_VACUUM_PROGRESS_METRICS` (PG≥12, `util.py:992`): `pg_stat_progress_cluster`. `cluster_vacuum.*`.
- `INDEX_PROGRESS_METRICS` (PG≥12, `util.py:1018`): `pg_stat_progress_create_index`. `create_index.*`.
- `ANALYZE_PROGRESS_METRICS` (PG≥13, `util.py:966`): `pg_stat_progress_analyze`. `analyze.*`.

### 4.14 I/O — `pg_stat_io` (PG≥16, **only if `dbm`**, `postgres.py:452-454`)
`STAT_IO_METRICS` (`util.py:1339`), `LIMIT 200`. Tags `backend_type,object,context`; `io.{evictions,
extend_time,extends,fsync_time,fsyncs,hits,read_time,reads,write_time,writes}` (monotonic_count).
**Db2 analog:** `MON_GET_TABLESPACE` / `MON_GET_CONTAINER` (`POOL_READ_TIME`, `DIRECT_READS`,
`DIRECT_READ_TIME`, ...). See `_research/map-io-disk.md`.

### 4.15 Idle-in-transaction lock age (PG, **only if `dbm` + `locks_idle_in_transaction.enabled`**)
`IDLE_TX_LOCK_AGE_METRICS` (`util.py:1377`), per-database, `LIMIT {max_rows}`, configurable
`collection_interval`. Joins `pg_locks`/`pg_stat_activity`/`pg_class`/`pg_roles`. Many tags (pid, db,
session_user, app, client_hostname, lock_mode, relation, relation_owner); metric
`locks.idle_in_transaction_age` (gauge, second).

### 4.16 Per-RELATION metrics (only if `relations` configured) — `relationsmanager.py`
Gated by `self._config.relations` (a list of relation name/regex + optional schemas/relkind). Two sub-paths:
- **`RELATION_METRICS = [STATIO_METRICS]`** (`relationsmanager.py:421`, legacy scope) — from
  `pg_statio_user_tables`. Descriptors `relname`→`table`, `schemaname`→`schema`; metrics (rate):
  `heap_blocks_read/hit`, `index_blocks_read/hit`, `toast_blocks_read/hit`, `toast_index_blocks_read/hit`.
- **`DYNAMIC_RELATION_QUERIES = [QUERY_PG_CLASS, QUERY_PG_CLASS_SIZE, IDX_METRICS, LOCK_METRICS]`**
  (`relationsmanager.py:422`, new-style, added to `dynamic_queries` per database):
  - `QUERY_PG_CLASS` (`relationsmanager.py:194`): direct `pg_stat_get_*(oid)` calls (avoids
    `pg_stat_user_tables` sorts). Tags `db,schema,table`. Metrics include `seq_scans` (rate),
    `seq_rows_read` (rate), `index_rel_scans`/`index_rel_rows_fetched` (rate), `rows_inserted/updated/
    deleted/hot_updated` (rate), `live_rows`/`dead_rows` (gauge), `vacuumed`/`autovacuumed`/`analyzed`/
    `autoanalyzed` (monotonic_count), `last_{vacuum,autovacuum,analyze,autoanalyze}_age` (gauge), a full
    `toast.*` set, and `relation.xmin` (gauge). Filters out tables under `AccessExclusiveLock`.
  - `QUERY_PG_CLASS_SIZE` (`relationsmanager.py:136`): from `pg_class` + `pg_relation_size`/
    `pg_indexes_size`. Tags `db,schema,table,partition_of(tag_not_null)`; `relation.{pages,tuples,
    all_visible}`, `table_size` (= relation+toast), `relation_size`, `index_size`, `toast_size`,
    `total_size` (all gauge, byte). Also excludes `AccessExclusiveLock` tables.
  - `IDX_METRICS` (`relationsmanager.py:65`): like `pg_stat_user_indexes`. Tags `db,schema,table,
    index,valid`; `index_scans`/`index_rows_read`/`index_rows_fetched` (rate),
    `index.index_blocks_read`/`index.index_blocks_hit` (rate), `individual_index_size` (gauge, byte).
  - `LOCK_METRICS` (`relationsmanager.py:32`): from `pg_locks`. Tags `lock_mode,lock_type,schema,db,
    table,granted,fastpath`; `locks` (gauge).
- **Bloat (if `collect_bloat_metrics`, default False):** `TABLE_BLOAT` → `table_bloat` (gauge),
  `INDEX_BLOAT` → `index_bloat` (gauge) — estimated via the `check_postgres` bloat heuristic SQL
  (`relationsmanager.py:312-419`).

The relation WHERE-clause builder is `RelationsManager.filter_relation_query`
(`relationsmanager.py:435-466`): builds `(relname='x' AND schema=ANY(...)) OR (relname ~ 'regex' ...)`
and appends `LIMIT max_relations` (default 300). `index_scans`/`seq_scans` values are cached
(`_cache_table_activity`, `postgres.py:896`) for DBM activity correlation.

**Db2 analog:** `MON_GET_TABLE` (rows read/inserted/updated/deleted, overflow accesses, table scans),
`MON_GET_INDEX` (index scans, page allocs), `MON_GET_TABLESPACE` (sizes), `MON_GET_LOCKS` /
`MON_GET_APPL_LOCKWAIT` (locks). Confirm columns against `_raw/02-monget-key-columns.txt`. The
`relations`-style include/exclude filtering maps well to Db2 schema/table allowlists.

### 4.17 Custom metrics & custom queries
`custom_metrics` (legacy scope dicts) run via `_query_scope(..., is_custom_metrics=True)`
(`postgres.py:1062`, truncated at `MAX_CUSTOM_RESULTS`). `custom_queries` run through the QueryManager
(`postgres.py:1288`). `only_custom_queries` skips all built-in stat collection.

---

## 5. Tagging model (applies to ALL metrics)

- Base instance tags from config `tags` (`postgres.py:145`) plus `add_core_tags` (`postgres.py:258`):
  `database_hostname:<host>`, `database_instance:<identifier>`, and `dd.internal.resource:*` resource
  tags (GCP CloudSQL, AWS RDS, Azure) set in `set_resource_tags` (`postgres.py:265-296`).
- Per-run dynamic tags: `postgresql_version:<raw>`, `system_identifier:<id>`,
  `postgresql_cluster_name:<name>`, `replication_role:<role>` (`postgres.py:1248-1265`).
- `tags_without_db` = tags minus any `db:` tag — used for instance-level metrics and the QueryExecutor
  default tags (`postgres.py:189,303`). The `db` tag is then (re)attached per-row from the descriptor so
  pg_stat_database rows get the *right* db, not the connection's (`postgres.py:867-876`).
- Scope descriptors add per-row tags `name:value` (`postgres.py:881`). New-style `columns` with
  `type:'tag'`/`'tag_not_null'` do the same via the base framework.
- Metric hostname is `self.reported_hostname` (the resolved DB host, not the agent host).

**Db2 analog:** equivalent base tags should be `db:<DBNAME>`, `database_hostname`,
`database_instance`, plus Db2-specific `member`/`db2_member` (MPP/pureScale), `tablespace`,
`bufferpool`, `schema`, `table` where relevant. Db2 `MON_GET_*` functions take a `member` argument
(`-1` = current, `-2` = all) — equivalent to per-database row fan-out in Postgres.

---

## 6. Config flags that gate metric categories (defaults)

From `config_models/defaults.py`:
| flag | default | gates |
|---|---|---|
| `collect_database_size_metrics` | True | `postgresql.database_size` (§4.1) |
| `collect_count_metrics` | True | `postgresql.table.count` (§4.11) |
| `collect_default_database` | True | whether `postgres` db is excluded from ignore list |
| `collect_activity_metrics` | False | activity aggregates (§4.5) |
| `collect_function_metrics` | False | function metrics (§4.10) |
| `collect_bloat_metrics` | False | table/index bloat (§4.16) |
| `collect_buffercache_metrics` | False | buffercache (§4.12) |
| `collect_checksum_metrics` | False | checksum metrics (§4.1/§2, PG≥12) |
| `collect_wal_metrics` | None/True-ish | WAL file metrics; PG≥10 via SQL by default, PG<10 only if True |
| `dbm` | False | gates DBM jobs + `pg_stat_io` + idle-tx-lock + drops `connections` from core |
| `relations` | (none) | ALL per-relation metrics (§4.16) |
| `dbstrict` | False | restrict pg_stat_database rows to configured `dbname` |
| `ignore_databases` | template0/1, rdsadmin, azure_maintenance, cloudsqladmin, alloydb* | excluded from per-db metrics |
| `max_relations` | 300 | LIMIT on relation queries |
| `max_connections` | 30 | connection-pool size for autodiscovery |

`config.py` validation: `relations` requires `dbname` or autodiscovery (`config.py:403`);
`collect_default_database` + `postgres` in `ignore_databases` is rejected (`config.py:219`).

---

## 7. metadata.csv structure (the metric catalog)

Header (`metadata.csv:1`): `metric_name,metric_type,interval,unit_name,per_unit_name,description,
orientation,integration,short_name,curated_metric,sample_tags`. 244 metric rows. `metric_type` ∈
{`gauge`,`rate`,`count`}. Note: Agent submit fns `monotonic_count`/`count` both surface as
`count` in metadata; `AgentCheck.rate` → `rate`; `AgentCheck.gauge` → `gauge`. `unit_name`/
`per_unit_name` carry units (e.g. `byte`, `second`, `transaction`+`second` for rates, `millisecond`
for timing). `description` documents which tags apply and which config flag enables the metric (e.g.
"Enabled with `relations`", "(DBM only)"). `sample_tags` lists tag keys for tag-bearing metrics.

**For Db2:** every metric the integration emits MUST have a row in `ibm_db2/metadata.csv` with the
`ibm_db2.` prefix, correct type/unit, and a description naming the enabling config flag and tags —
mirror the Postgres conventions above.

---

## 8. Concrete porting checklist for Db2 metrics (derived)

1. Use the **new QueryExecutor `columns` dict style** for every query (avoid the deprecated scope dicts).
2. Version/edition gate via `MON_GET_*` availability (check `_raw/01-version-and-monget-functions.txt`),
   mirroring the `if version >= V*` pattern in `dynamic_queries`.
3. Wrap each query so a missing function / insufficient privilege degrades gracefully (Postgres catches
   `UndefinedFunction`, `ProgrammingError`, `FeatureNotSupported`).
4. Category coverage to target (Postgres → Db2 source):
   database/throughput → `MON_GET_DATABASE`; buffer pool → `MON_GET_BUFFERPOOL`
   (`_research/map-bufferpool.md`); I/O/tablespace → `MON_GET_TABLESPACE`/`MON_GET_CONTAINER`
   (`map-io-disk.md`); connections → `MON_GET_CONNECTION`; activity/locks →
   `MON_GET_ACTIVITY`/`MON_GET_LOCKS` (`db2-live-activity.md`); sort/hash spills →
   `map-sorting-hashing.md`; HADR (replication) → `MON_GET_HADR` (`map-hadr-replication.md`);
   table/index → `MON_GET_TABLE`/`MON_GET_INDEX`; package cache → `db2-live-pkgcache.md`;
   catalog inventory → `db2-monget-catalog-2.md`.
5. Tagging: `db`, `member`, `tablespace`, `bufferpool`, `schema`, `table`, plus base
   `database_hostname`/`database_instance` and version tag (mirror `postgresql_version`).
6. Add every metric to `ibm_db2/metadata.csv` with correct type/unit/tags.
