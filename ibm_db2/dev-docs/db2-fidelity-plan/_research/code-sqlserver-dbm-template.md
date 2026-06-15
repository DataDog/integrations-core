# SQL Server as the "DBM-added-to-an-existing-engine" TEMPLATE — Code Research

Raw input for the Db2 DBM implementation plan. Reverse-engineered from the **actual** source in
`/home/bits/dd/integrations-core/sqlserver` (the canonical example of bolting DBM onto a pre-existing
metrics-only integration, which is exactly Db2's situation). Every claim cites an absolute file path +
line range. Target Db2 version: **12.1** (live container 12.1.4).

> Scope: This file documents the **module layout, the DBM-enable config surface, connection handling,
> the async-job scheduling, and the precise file list** an engine must add to gain DBM. It is the
> structural / "how is the integration wired together" companion to
> `code-dbm-payload-contract.md` (which documents the JSON envelope each collector emits). Read both.
> Where the payload contract already covers a field shape, this doc points at it rather than repeating it.

---

## 0. TL;DR — what SQL Server adds on top of a plain metrics check

SQL Server is structured exactly like a metrics-only integration (it has `metrics.py`,
`database_metrics/`, custom-query support via `QueryManager`) **plus** six independent DBM collectors,
each its own module and each a `DBMAsyncJob`:

| Concern | Module | Class | Job name | dbm_type/kind emitted | Default interval |
|---|---|---|---|---|---|
| Query metrics + plans | `statements.py` | `SqlserverStatementMetrics` | `query-metrics` | `metrics` + `plan`/`fqt`/`rqp` | 60s |
| Active sessions | `activity.py` | `SqlserverActivity` | `query-activity` | `activity` + `rqt` | 10s |
| Settings + schemas | `metadata.py` (+ `schemas.py`) | `SqlserverMetadata` | `database-metadata` | `sqlserver_configs` + schemas | 600s / 600s |
| Procedure metrics | `stored_procedures.py` | `SqlserverProcedureMetrics` | (procedure metrics) | `metrics` | 60s |
| Agent jobs history | `agent_history.py` | `SqlserverAgentHistory` | (agent jobs) | — | — |
| Deadlocks | `deadlocks.py` | `Deadlocks` | `deadlocks` | `deadlocks` (on activity track) | 600s |

Plus supporting infra: `config.py` (parses every DBM block), `connection.py` (per-job isolated raw
connections keyed by a `key_prefix`), `cursor.py` (dict-cursor + comment wrapper), `health.py`
(`dbm-health` events), `const.py` (static-info cache keys + default intervals), and the
`base.checks.db.DatabaseCheck` superclass (gives the five `database_monitoring_*` helpers).

**For Db2 the minimum viable DBM build = statements + activity + metadata(settings) + the
`database_instance` registration event.** Procedures/agent-jobs/deadlocks/schemas are SQL-Server-specific
extras; map only the ones that have a Db2 analog.

Source of the table:
- check wiring `/home/bits/dd/integrations-core/sqlserver/datadog_checks/sqlserver/sqlserver.py:173-179, 213-225, 913-926`
- job names: `statements.py:276`, `activity.py:206`, `metadata.py:78`, `deadlocks.py:72`

---

## 1. Module layout — every file in `datadog_checks/sqlserver/` and its role

Directory: `/home/bits/dd/integrations-core/sqlserver/datadog_checks/sqlserver/`

| File | Role | DBM-relevant? |
|---|---|---|
| `sqlserver.py` | The `SQLServer(DatabaseCheck)` check class — orchestrator. Instantiates all collectors, runs them in `check()`, owns identity props (`reported_hostname`, `database_identifier`, `dbms_version`), `static_info_cache`, `tag_manager`, the `database_instance` event. | **Core** |
| `config.py` | `SQLServerConfig` — parses **every** config option incl. all DBM blocks into typed attributes; builds `obfuscator_options`; `sanitize()` redacts password. | **Core** |
| `connection.py` | `Connection` — manages raw driver connections; **per-job isolation via `key_prefix`**; context managers `open_managed_default_connection` / `get_managed_cursor`; service-check on connect; `SET TRANSACTION ISOLATION LEVEL READ UNCOMMITTED` on every new conn. | **Core** |
| `cursor.py` | `CommenterCursorWrapper` — wraps the driver cursor; adds `fetchall_dict()` / `fetchone_dict()` (no native DictCursor in pyodbc) and injects a SQL comment. | **Core** |
| `const.py` | Static-info cache keys (`STATIC_INFO_VERSION`, `_ENGINE_EDITION`, `_MAJOR_VERSION`, `_RDS`, `_SERVERNAME`…), default intervals (`DEFAULT_SCHEMAS_COLLECTION_INTERVAL=600`, `DEFAULT_LONG_METRICS_COLLECTION_INTERVAL=300`, `PROC_CHAR_LIMIT=500`, `DEFAULT_AUTODISCOVERY_INTERVAL=3600`), metric lists, `DBM_MIGRATED_METRICS`. | **Core** |
| `health.py` | `SqlServerHealth(Health)` — emits `dbm-health` events. | Optional |
| `statements.py` | `SqlserverStatementMetrics(DBMAsyncJob)` — query metrics + execution plans + FQT/RQP. | **DBM collector** |
| `activity.py` | `SqlserverActivity(DBMAsyncJob)` — active sessions + connections + idle-blockers + RQT. | **DBM collector** |
| `metadata.py` | `SqlserverMetadata(DBMAsyncJob)` — settings (`sys.configurations`) + delegates schema collection. | **DBM collector** |
| `schemas.py` | `SQLServerSchemaCollector(SchemaCollector)` — table/column/index/FK metadata. | DBM collector (optional) |
| `stored_procedures.py` | `SqlserverProcedureMetrics(DBMAsyncJob)` — per-proc metrics. | DBM collector (SS-specific) |
| `agent_history.py` | `SqlserverAgentHistory(DBMAsyncJob)` — SQL Agent job history. | DBM collector (SS-specific) |
| `deadlocks.py` | `Deadlocks(DBMAsyncJob)` — deadlock graphs from XE. | DBM collector (SS-specific) |
| `queries.py` | Schema-collection SQL templates (`DB_QUERY`, `SCHEMA_QUERY`, `TABLES_QUERY`, `COLUMN_QUERY`, `INDEX_QUERY`, `FOREIGN_KEY_QUERY`, deadlock/XE query builders). | DBM SQL |
| `metrics.py` | Legacy perf-counter metric classes (`SqlSimpleMetric`, `SqlFractionMetric`, …) + `TABLE_MAPPING`. | Metrics (non-DBM) |
| `database_metrics/` | 20+ classes, one per DMV-backed metric group, all subclass `SqlserverDatabaseMetricsBase`; driven by `QueryExecutor`. | Metrics (non-DBM) |
| `xe_collection/` | Extended-Events session handlers (query completion / errors). | DBM (SS-specific, modern) |
| `utils.py` | `Database` namedtuple, `construct_use_statement`, version parsers, `is_azure_*`. | Helpers |
| `azure.py`, `diagnose.py`, `connection_errors.py` | Cloud auth, diagnostics, error classification. | Helpers |
| `config_models/` | **Auto-generated** Pydantic models from `assets/configuration/spec.yaml` (`instance.py`, `defaults.py`, `shared.py`, `validators.py`, `deprecations.py`). | Generated |
| `data/conf.yaml.example` | **Auto-generated** example config from the spec. | Generated |

---

## 2. How DBM is ENABLED via config (the master switch + per-collector blocks)

### 2.1 Master switch: `dbm: true`
Parsed in `config.py:55`:
```python
self.dbm_enabled: bool = is_affirmative(instance.get('dbm', False))
```
This single boolean:
1. Gates the entire DBM collector fan-out in `check()`
   (`sqlserver.py:913-926` — `if self._config.dbm_enabled:` then `.run_job_loop(...)` for each collector).
2. Is stamped into the `database_instance` registration event as `metadata.dbm`
   (`sqlserver.py:1167-1170`) — this is what makes the host appear as a DBM instance.
3. Changes which "migrated" perf-counter metrics are collected — when DBM is on, the metrics that DBM
   now provides are **dropped** from the legacy path (`sqlserver.py:645-646`,
   `common_metrics.extend(DBM_MIGRATED_METRICS)` only runs `if not self._config.dbm_enabled`).

### 2.2 Per-collector config blocks — each maps to one `instance.get(...)` dict
`config.py:56-65`:
```python
self.database_metrics_config: dict = self._build_database_metrics_configs(instance)
self.statement_metrics_config: dict = instance.get('query_metrics', {}) or {}
self.agent_jobs_config: dict       = instance.get('agent_jobs', {}) or {}
self.procedure_metrics_config: dict= instance.get('procedure_metrics', {}) or {}
self.settings_config: dict         = instance.get('collect_settings', {}) or {}
self.activity_config: dict         = instance.get('query_activity', {}) or {}
self.schema_config: dict   = instance.get('collect_schemas', instance.get('schemas_collection', {})) or {}
self.deadlocks_config: dict= instance.get('collect_deadlocks', instance.get('deadlocks_collection', {})) or {}
self.xe_collection_config: dict = instance.get('collect_xe', instance.get('xe_collection', {})) or {}
```
**Pattern to copy for Db2:** one top-level YAML key per collector, each a dict with at least
`enabled` (bool) and `collection_interval` (seconds), plus collector-specific knobs. Backward-compat
fallbacks (`collect_schemas` vs legacy `schemas_collection`) are optional for a greenfield Db2 build.

### 2.3 Each collector reads its block in its own `__init__` to set `enabled`/`interval`
Canonical pattern (`statements.py:257-277`):
```python
collection_interval = float(self._config.statement_metrics_config.get('collection_interval', DEFAULT_COLLECTION_INTERVAL))
if collection_interval <= 0:
    collection_interval = DEFAULT_COLLECTION_INTERVAL
self.collection_interval = collection_interval
super().__init__(
    check,
    run_sync=is_affirmative(self._config.statement_metrics_config.get('run_sync', False)),
    enabled=is_affirmative(self._config.statement_metrics_config.get('enabled', True)),
    expected_db_exceptions=(),
    min_collection_interval=self._config.min_collection_interval,
    dbms="sqlserver",
    rate_limit=1 / float(collection_interval),
    job_name="query-metrics",
    shutdown_callback=self._close_db_conn,
)
```
Identical shape in `activity.py:192-208`, `metadata.py:66-80`, `deadlocks.py:50-74`.
**Defaults seen:** statements `enabled=True` interval 60; activity `enabled=True` interval 10;
metadata/settings `enabled=True` interval 600; deadlocks `enabled=False` interval 600.

### 2.4 The DBM config-block reference (from `conf.yaml.example`)
File: `/home/bits/dd/integrations-core/sqlserver/datadog_checks/sqlserver/data/conf.yaml.example`.
Each DBM block is annotated `Requires dbm: true`. Key blocks & their line anchors:

| YAML key | Line | Sub-keys (defaults) |
|---|---|---|
| `dbm` | 372 | `false` (master switch) |
| `collect_settings` | 376 | `enabled: true`, `collection_interval: 600` |
| `query_metrics` | 391 | `enabled: true`, `collection_interval: 60`, `dm_exec_query_stats_row_limit: 10000`, `samples_per_hour_per_query: 4`, `lookback_window` |
| `procedure_metrics` | 425 | `enabled: true`, `collection_interval: 60`, `dm_exec_procedure_stats_row_limit: 10000` |
| `query_activity` | 447 | `enabled: true` (interval 10 in code) |
| `stored_procedure_characters_limit` | 454 | `500` |
| `aws` / `gcp` / `azure` | 470 / 489 / — | cloud enrichment (only applied when `dbm: true`) |
| `obfuscator_options` | 573 | see §6 |
| `collect_raw_query_statement` | 676 | `enabled: false`, `cache_max_size: 10000`, `samples_per_hour_per_query: 1` |
| `collect_schemas` | 791 | `enabled: false`, `collection_interval`, `max_tables: 300` |
| `propagate_agent_tags` | 854 | `false` |
| `collect_xe` | 860 | XE session collection |
| `collect_deadlocks` | 937 | `enabled: false`, `collection_interval: 600`, `max_deadlocks: 100` |

Shared (not DBM-gated but DBM-relevant) identity keys, same file:
`propagate_agent_tags` (19), `reported_hostname` (81), `exclude_hostname` (86),
`database_identifier` (97), `database_metrics` (164).

`database_instance_collection_interval` default = `DEFAULT_LONG_METRICS_COLLECTION_INTERVAL` (300s)
(`config.py:38-40`, `const.py:312`). NOTE postgres uses 1800 — pick one for Db2 and document it.

---

## 3. The check class — `SQLServer(DatabaseCheck)` wiring (the orchestrator)

File: `/home/bits/dd/integrations-core/sqlserver/datadog_checks/sqlserver/sqlserver.py`.

### 3.1 Subclass + namespace
`sqlserver.py:14-15, 132-133`:
```python
from datadog_checks.base.checks.db import DatabaseCheck
class SQLServer(DatabaseCheck):
    __NAMESPACE__ = "sqlserver"
```
`DatabaseCheck` gives the five `database_monitoring_*` helpers and the abstract identity properties.
**Db2 currently subclasses bare `AgentCheck`** (`ibm_db2/datadog_checks/ibm_db2/ibm_db2.py:28`) — it must
switch to `DatabaseCheck`.

### 3.2 Collector instantiation (one attribute per collector)
`sqlserver.py:173-179`:
```python
# DBM
self.statement_metrics = SqlserverStatementMetrics(self, self._config)
self.procedure_metrics = SqlserverProcedureMetrics(self, self._config)
self.sql_metadata      = SqlserverMetadata(self, self._config)
self.activity          = SqlserverActivity(self, self._config)
self.agent_history     = SqlserverAgentHistory(self, self._config)
self.deadlocks         = Deadlocks(self, self._config)
```
Each collector receives `(check, config)`. They pull everything else (connection, tags, identity,
static_info_cache) off `check`.

### 3.3 Fan-out in `check()` (gated by `dbm_enabled`)
`sqlserver.py:913-926`:
```python
if self._config.dbm_enabled:
    self.agent_history.run_job_loop(self.tag_manager.get_tags())
    self.statement_metrics.run_job_loop(self.tag_manager.get_tags())
    self.procedure_metrics.run_job_loop(self.tag_manager.get_tags())
    self.activity.run_job_loop(self.tag_manager.get_tags())
    self.sql_metadata.run_job_loop(self.tag_manager.get_tags())
    self.deadlocks.run_job_loop(self.tag_manager.get_tags())
```
`run_job_loop(tags)` is the `DBMAsyncJob` entry point (§7). It is **idempotent / non-blocking**: it
spawns/keeps a background thread and returns immediately (or runs synchronously if `run_sync`).

### 3.4 `cancel()` must tear down every collector
`sqlserver.py:212-225` calls `.cancel()` on each collector so background threads stop on check teardown.
Db2 must do the same for every `DBMAsyncJob` it creates.

### 3.5 The registration / heartbeat event (`_send_database_instance_metadata`)
`sqlserver.py:1151-1173` — emitted every `check()` run (`sqlserver.py:904`), debounced by a 1-entry
`TTLCache` keyed on `database_identifier` with `ttl=database_instance_collection_interval`
(`sqlserver.py:185-188`). The event carries `metadata.dbm = self._config.dbm_enabled`. This is the
single payload that registers the host as a DBM instance — see payload-contract doc §6.1.

### 3.6 Static info cache (version / edition discovery, populated once per day)
`sqlserver.py:142-146` (TTLCache, ttl = 24h) + `load_static_information()` (`sqlserver.py:413-494`):
runs SQL once to populate `STATIC_INFO_VERSION`, `_MAJOR_VERSION`, `_ENGINE_EDITION`, `_RDS`,
`_SERVERNAME`. Every collector reads these from `check.static_info_cache` to stamp `<dbms>_version`
into payloads. **Db2 equivalent:** cache the `SERVICE_LEVEL` / version from `sysibmadm.env_inst_info`
(or reuse `utils.get_version` already in `ibm_db2.py:96-119`) into a similar cache and expose
`dbms_version`.

### 3.7 Tag management
`sqlserver.py:162-163` builds a `TagManager` (`datadog_checks.base.utils.db.utils.TagManager`),
seeded from `config.tags`. `add_core_tags()` (`sqlserver.py:267-272`) injects
`database_hostname:<host>` and `database_instance:<identifier>` on every metric/event;
`set_resource_tags()` (`sqlserver.py:274-320`) injects `dd.internal.resource:database_instance:<id>`
plus cloud resource tags. Collectors fetch tags via `check.tag_manager.get_tags()`.

---

## 4. Connection handling — the per-job isolation pattern (CRITICAL for Db2)

File: `/home/bits/dd/integrations-core/sqlserver/datadog_checks/sqlserver/connection.py`.

### 4.1 Why DBM needs its own connections
The main check connection and each background DBM thread must NOT share a raw connection (drivers'
connection objects are not thread-safe even when the module is). SQL Server solves this with a
**`key_prefix`** that namespaces the connection cache.

`_conn_key` (`connection.py:521-526`):
```python
def _conn_key(self, db_key, db_name=None, key_prefix=None):
    dsn, host, username, password, database, driver = self._get_access_info(db_key, db_name)
    if not key_prefix: key_prefix = ""
    return '{}{}:{}:{}:{}:{}:{}'.format(key_prefix, dsn, host, username, password, database, driver)
```
Connections are cached in `self._conns[conn_key]` (`connection.py:170, 276-285`).

### 4.2 Each subsystem uses a distinct prefix
- main check: `KEY_PREFIX = "dbm-sqlserver-"` (`sqlserver.py:129`)
- statements: `self._conn_key_prefix = "dbm-"` (`statements.py:289`)
- activity: `"dbm-activity-"` (`activity.py:209`)
- metadata: `"dbm-metadata-"` (`metadata.py:84`)
- deadlocks: `"dbm-deadlocks-"` (`deadlocks.py:75`)
- schemas: `"dbm-schemas-"` / `"dbm-schemas-pre-2017"` (`schemas.py:34-35`)

So a collector opens **its own** raw connection, never colliding with the main check or sibling jobs.

### 4.3 Context-manager API every collector uses
`connection.py:179-185, 228-239`:
```python
with self._check.connection.open_managed_default_connection(self._conn_key_prefix):
    with self._check.connection.get_managed_cursor(self._conn_key_prefix) as cursor:
        cursor.execute(query)
        rows = cursor.fetchall()
```
`open_managed_default_connection` opens (and on exit closes) the connection for that prefix;
`get_managed_cursor` yields a `CommenterCursorWrapper` and closes it on exit.
SQL Server **explicitly closes** connections after each use to avoid holding DB locks
(`connection.py:241-247, 327-341`).

### 4.4 Connection setup hardening
Every new raw connection runs `SET TRANSACTION ISOLATION LEVEL READ UNCOMMITTED`
(`connection.py:322-325`) so the agent's reads never block writers. **Db2 analog:** consider
`SET CURRENT ISOLATION = UR` (uncommitted read) on each DBM connection, or open with
`ibm_db` isolation attr, so monitoring queries don't take locks.

### 4.5 Cursor wrapper (dict rows)
`cursor.py:11-46` — `CommenterCursorWrapper` wraps the driver cursor; collectors that need dict rows
either call `fetchall_dict()`/`fetchone_dict()` (schemas) or build dicts manually:
```python
columns = [i[0] for i in cursor.description]
rows = [dict(zip(columns, row)) for row in cursor.fetchall()]
```
(`statements.py:367-369`, `activity.py:261-263`, `metadata.py:134-136`). The manual form is used
because pyodbc has no DictCursor.

### 4.6 Db2 driver gap (what differs)
Db2 uses the **`ibm_db`** C driver, not pyodbc/adodbapi. Current Db2 connection:
`ibm_db2.py:554-578` (`ibm_db.connect(target, user, pwd, options)`), connection string built in
`get_connection_data` (`ibm_db2.py:591-608`), query exec via `ibm_db.exec_immediate` +
`ibm_db.fetch_assoc` in `iter_rows` (`ibm_db2.py:610-631`). **`ibm_db` has no cursor object** — it
returns a statement handle and you iterate with `ibm_db.fetch_assoc`/`fetch_tuple`. Db2 must therefore
build its **own** connection-isolation layer mirroring §4.1-4.4 (a dict of statement-handle-producing
connections keyed by `key_prefix`), or open a fresh `ibm_db.connect` per DBM job. `ibm_db.fetch_assoc`
already returns dict rows (lowercased via `ATTR_CASE=CASE_LOWER`, `ibm_db2.py:567`), so the
`dict(zip(columns,row))` step is unnecessary for Db2.

---

## 5. The DBM collectors in detail (what each does, what Db2 maps to)

### 5.1 `statements.py` — `SqlserverStatementMetrics` (query metrics + plans)
File: `/home/bits/dd/integrations-core/sqlserver/datadog_checks/sqlserver/statements.py`.

Flow (`collect_statement_metrics_and_plans`, lines 524-560):
1. `_collect_metrics_rows(cursor)` (483-490): run `STATEMENT_METRICS_QUERY` against the Query Plan
   Cache (`sys.dm_exec_query_stats` + `sys.dm_exec_sql_text`), obfuscate each statement, compute
   signatures, then **first-derivative diff** via `self._state.compute_derivative_rows(...)`
   (`StatementMetrics` from `base.utils.db.statement_metrics`).
2. Emit one **FQT** sample per new (db, query_signature) — `_rows_to_fqt_events` (562-595),
   rate-limited by `_full_statement_text_cache` TTLCache.
3. Emit the **metrics** payload — `_to_metrics_payload` (505-522): top-level wrapper + `sqlserver_rows`.
4. Emit **plan** samples — `_collect_plans` (614-719): for each row look up the XML plan
   (`PLAN_LOOKUP_QUERY`, 202-205), obfuscate via `obfuscate_xml_plan` (234-251), emit `dbm_type:"plan"`
   (+ `rqp` when raw collection on). Rate-limited per plan by `_seen_plans_ratelimiter`.

Key reusable pieces:
- `compute_sql_signature` (line 420), `obfuscate_sql_with_metadata` (399), `RateLimitingTTLCache` /
  `TTLCache` for sample rate-limiting (296-310).
- `_row_key = (database_name, query_signature, query_hash, procedure_name)` (208-213) — the stable
  diff key. **Db2 key:** `(query_signature, db/schema, user)` over `MON_GET_PKG_CACHE_STMT`.
- metric columns to diff: those starting `total_` or `== execution_count` (488).
- `dm_exec_query_stats_row_limit` (281-283, default 10000), `max_queries` (292, default 250),
  `lookback_window` (350-351), `stored_procedure_characters_limit` (346).

**Db2 source:** `MON_GET_PKG_CACHE_STMT` table function provides per-statement aggregate metrics
(NUM_EXECUTIONS, TOTAL_CPU_TIME, ROWS_READ, STMT_EXEC_TIME, etc.) and `STMT_TEXT` — the direct analog
of `dm_exec_query_stats`. Plans: `EXPLAIN` / `db2exfmt` or `MON_GET_PKG_CACHE_STMT` doesn't carry plans
inline (Db2 plans live in EXPLAIN tables) — plan collection is harder and may be deferred.

### 5.2 `activity.py` — `SqlserverActivity` (active sessions)
File: `/home/bits/dd/integrations-core/sqlserver/datadog_checks/sqlserver/activity.py`.

Flow (`collect_activity`, 482-509):
1. `_get_active_connections` (226-234): `CONNECTIONS_QUERY` (35-44) → connection counts grouped by
   user/status/db.
2. `_get_activity` (249-273): `ACTIVITY_QUERY` (47-95) joins `dm_exec_sessions` + `dm_exec_connections`
   + `dm_exec_requests` + `dm_exec_sql_text`, filtering out the agent's own spid and sleeping sessions;
   then pulls **idle blockers** separately (`IDLE_BLOCKING_SESSIONS_QUERY`, 102-133).
3. `_normalize_queries_and_filter_rows` (275-298): obfuscate + signature each row, drop null fields,
   enforce a **byte budget** (`MAX_PAYLOAD_BYTES = 19e6`, line 31) on the sorted tail.
4. `_create_activity_event` (463-480): wrapper with `sqlserver_activity` (sessions) +
   `sqlserver_connections` (counts). `ddtags` here is a **list** (contrast samples = comma-joined str).

**Db2 source:** `MON_GET_CONNECTION` / `MON_GET_ACTIVITY` (or `SYSIBMADM.MON_CURRENT_SQL`,
`WLM_GET_WORKLOAD_OCCURRENCE_ACTIVITIES`) for active statements; `MON_GET_CONNECTION` /
`SYSIBMADM.APPLICATIONS` for connection counts. Blocking: `MON_GET_APPL_LOCKWAIT` /
`SYSIBMADM.MON_LOCKWAITS` to identify blockers.

### 5.3 `metadata.py` — `SqlserverMetadata` (settings + schema delegation)
File: `/home/bits/dd/integrations-core/sqlserver/datadog_checks/sqlserver/metadata.py`.

- Settings: `SETTINGS_QUERY = "SELECT {columns} FROM sys.configurations"` (29-31); columns probed for
  availability and `sql_variant` cols cast to `varchar(max)` (43-50, 113-126). Emits
  `kind:"sqlserver_configs"` on `dbm-metadata` (`report_sqlserver_metadata`, 140-162).
- Schemas: delegates to `SQLServerSchemaCollector` (88, `collect_schemas`, 164-170), gated by
  `schema_config.enabled` and its own interval.

**Db2 source for settings:** `SYSIBMADM.DBCFG` (database config), `SYSIBMADM.DBMCFG` (instance/dbm
config), `SYSIBMADM.REG_VARIABLES` (registry vars) — emit each as a `db2_<x>_settings` `kind`.

### 5.4 `schemas.py` — `SQLServerSchemaCollector(SchemaCollector)`
File: `/home/bits/dd/integrations-core/sqlserver/datadog_checks/sqlserver/schemas.py`.
Subclasses the shared `SchemaCollector` (`base.utils.db.schemas`) and overrides only:
`kind` (→`"sqlserver_databases"`, line 93), `_get_databases` (96-106), `_get_cursor` (108-129),
`_get_next`/`_get_all` (211-215), `_map_row` (217-276). The base handles chunking
(`collection_payloads_count`) and the envelope. SQL templates in `queries.py` (§ DB/SCHEMA/TABLES/
COLUMN/INDEX/FOREIGN_KEY queries). **Db2 analog:** override the same 5 methods, query
`SYSCAT.TABLES`, `SYSCAT.COLUMNS`, `SYSCAT.INDEXES`, `SYSCAT.REFERENCES`, `SYSCAT.SCHEMATA`.

### 5.5 `deadlocks.py` — `Deadlocks` (SS-specific; Db2 has no direct analog)
Uses Extended-Events XML; **disabled by default** (`enabled` default False, `deadlocks.py:67`).
Emitted on the **activity** track with `dbm_type:"deadlocks"`. Db2 deadlock events live in the
`db2diag.log` / event monitors — out of scope for first fidelity; skip.

### 5.6 `stored_procedures.py` / `agent_history.py` / `xe_collection/`
SQL-Server-specific. Db2 has stored procedures (could map a `MON_GET_ROUTINE`-based collector later)
but no SQL Agent and no Extended Events — skip for first fidelity.

---

## 6. Obfuscation config (built once in `config.py`, used by every collector)

`config.py:81-122` builds `self.obfuscator_options` as a JSON string passed to the Go obfuscator.
Critical field: `'dbms': 'mssql'` (line 87) — sets the SQL dialect. **Db2 must set the right dialect
hint** (likely `'db2'` if the Go obfuscator supports it, else fall back to generic SQL — verify against
the agent obfuscator). Other toggles (all `is_affirmative`, with shown defaults):
`replace_digits` (False), `keep_sql_alias` (True), `return_json_metadata`/collect_metadata (True),
`table_names`/collect_tables (True), `collect_commands` (True), `collect_comments` (True),
`collect_procedures` (True), `obfuscation_mode` ('obfuscate_and_normalize'),
`keep_null`/`keep_boolean`/`keep_positional_parameter`/`replace_bind_parameter`/
`keep_trailing_semicolon`/`keep_identifier_quotation` (all False), `remove_space_between_parentheses`
(False). Collectors call `obfuscate_sql_with_metadata(text, self._config.obfuscator_options, replace_null_character=True)`.

`collect_raw_query_statement` block (`config.py:123-128`) toggles RQT/RQP emission and sets a cache size
+ rate; adds a `raw_query_statement:enabled` tag when on (`config.py:139`).

---

## 7. The async-job framework — `DBMAsyncJob`

File: `/home/bits/dd/integrations-core/datadog_checks_base/datadog_checks/base/utils/db/utils.py`.
`class DBMAsyncJob` at line 289; `__init__` at 299-342; constructor args:
`check, run_sync=False, enabled=True, min_collection_interval=15, rate_limit=1,
expected_db_exceptions=(), shutdown_callback=None, job_name=None, dbms=...`.

Lifecycle:
- `run_job_loop(tags)` (354-408): no-op if `enabled` is False (359-360); if `run_sync` (or env
  `DBM_THREADED_JOB_RUN_SYNC`) runs inline (369-371); else submits `self._job_loop` to a shared
  `ThreadPoolExecutor` if not already running (372-373). Sets `_job_tags = tags + ["job:<name>"]`.
- `_job_loop` (410-471): loops, rate-limited by `ConstantRateLimiter(rate_limit)`, calls the subclass's
  `run_job()`; submits health events on missed collections / exceptions; calls `shutdown_callback` on exit.
- `cancel()` (348-352): signals the loop to stop. **Every collector must be cancelled** from the
  check's `cancel()`.
- Subclass overrides **`run_job()`** only (498) — does the actual collection.

`rate_limit = 1/collection_interval` (seconds → executions/sec). `min_collection_interval` is the main
check interval, used to detect missed collections.

---

## 8. The complete FILE LIST an engine adds to gain DBM

To replicate the SQL Server template, Db2 needs to **add/modify** the following under
`/home/bits/dd/integrations-core/ibm_db2/`:

### 8.1 New collector modules (`datadog_checks/ibm_db2/`)
| New file | Mirrors | Minimum-viable? |
|---|---|---|
| `statements.py` | `sqlserver/statements.py` | **Yes** — `Db2StatementMetrics(DBMAsyncJob)` over `MON_GET_PKG_CACHE_STMT` |
| `activity.py` | `sqlserver/activity.py` | **Yes** — `Db2Activity(DBMAsyncJob)` over `MON_GET_*` |
| `metadata.py` | `sqlserver/metadata.py` | **Yes** — `Db2Metadata(DBMAsyncJob)` for `DBCFG`/`DBMCFG` settings (+ optional schemas) |
| `config.py` | `sqlserver/config.py` | **Yes** — `IbmDb2Config` parsing `dbm`, `query_metrics`, `query_activity`, `collect_settings`, identity, obfuscator |
| `connection.py` (or refactor existing in `ibm_db2.py`) | `sqlserver/connection.py` | **Yes** — per-`key_prefix` `ibm_db` connection isolation + managed-cursor context managers |
| `cursor.py` | `sqlserver/cursor.py` | Optional — `ibm_db.fetch_assoc` already gives dict rows |
| `schemas.py` | `sqlserver/schemas.py` | Optional — `Db2SchemaCollector(SchemaCollector)` over `SYSCAT.*` |
| `health.py` | `sqlserver/health.py` | Optional — `Db2Health(Health)` |
| `queries.py` (extend existing) | `sqlserver/queries.py` | DBM SQL templates (schema/settings/statement/activity) |
| `const.py` (new or extend `utils.py`) | `sqlserver/const.py` | Static-info keys + default intervals |

### 8.2 Modified existing files
| File | Change |
|---|---|
| `datadog_checks/ibm_db2/ibm_db2.py` | `IbmDb2Check(AgentCheck)` → `IbmDb2Check(DatabaseCheck)`; add `__NAMESPACE__`; instantiate the collectors in `__init__`; gate `.run_job_loop()` calls in `check()` behind `config.dbm_enabled`; add `cancel()` tearing down collectors; add identity props (`reported_hostname`, `resolved_hostname`, `database_identifier`, `database_hostname`, `dbms`→`"db2"`, `dbms_version`, `tags`, `cloud_metadata`); emit `_send_database_instance_metadata` with `metadata.dbm`. (Existing import: `from datadog_checks.base.checks.db import DatabaseCheck`.) |
| `datadog_checks/ibm_db2/__init__.py` | Export the check (already exists). |
| `datadog_checks/ibm_db2/__about__.py` | Version string feeds `integration_version` (already exists). |

### 8.3 Spec / generated files
| File | Change |
|---|---|
| `assets/configuration/spec.yaml` | Add the DBM option blocks (`dbm`, `query_metrics`, `query_activity`, `collect_settings`, `collect_schemas`, `obfuscator_options`, `collect_raw_query_statement`, `reported_hostname`, `exclude_hostname`, `database_identifier`, `propagate_agent_tags`, cloud blocks). This is the **source of truth**. |
| `datadog_checks/ibm_db2/config_models/*` | **Regenerated** from spec via `ddev validate config --sync` (do not hand-edit). |
| `datadog_checks/ibm_db2/data/conf.yaml.example` | **Regenerated** from spec. |

### 8.4 Tests
Mirror `sqlserver/tests/`: `test_statements.py`, `test_activity.py`, `test_metadata.py`,
`test_connection.py`, plus fixtures in `conftest.py`/`common.py`. (The existing
`code-testing-harness.md` research covers the harness.)

### 8.5 Manifest / metadata.csv — NOTE
DBM is **not** enabled by a manifest flag. There is no `"dbm": true` in `manifest.json` and DBM
telemetry is **not** declared in `metadata.csv` (it rides the event-platform tracks). See
`code-dbm-payload-contract.md` §11 for the authoritative finding. Optionally move `manifest.json`
`owner` to `database-monitoring` and add DBM classifier tags for parity.

---

## 9. Db2-specific call-outs (template-adaptation gotchas)

1. **Driver:** SQL Server uses pyodbc/adodbapi cursors; Db2 uses `ibm_db` statement handles
   (`ibm_db.exec_immediate` + `ibm_db.fetch_assoc`). Build the per-job connection-isolation layer
   yourself (§4.6); reuse the existing `get_connection`/`get_connection_data`
   (`ibm_db2.py:554-608`) but namespace connections by `key_prefix`.
2. **No DictCursor needed:** `ibm_db.fetch_assoc` with `ATTR_CASE=CASE_LOWER` already yields
   lowercase-keyed dict rows (`ibm_db2.py:567`) — skip the `dict(zip(columns,row))` step.
3. **Isolation level:** open DBM connections with uncommitted read (`SET CURRENT ISOLATION = UR`) to
   avoid locking, mirroring SQL Server's READ UNCOMMITTED (`connection.py:322-325`).
4. **Naming convention (payload):** `db2_rows`, `db2_activity`, `db2_connections`, `db2_version`,
   `ddsource:"db2"`, `dbms:"db2"`. (Payload-contract doc §12.)
5. **Static info:** cache the Db2 version (`get_version`, `ibm_db2.py:96-119`) into a TTLCache analog to
   `static_info_cache`; expose as `dbms_version`.
6. **Diff key & execution indicator:** for `compute_derivative_rows`, key on
   `(query_signature, db_or_schema, user)`; the execution-indicator column is `NUM_EXECUTIONS`
   (or `NUM_EXEC_WITH_METRICS`) from `MON_GET_PKG_CACHE_STMT`.
7. **Obfuscator dialect:** set `obfuscator_options['dbms']` to the correct Db2 hint (verify the Go
   obfuscator supports `'db2'`; else generic SQL).
8. **Config block names:** copy SQL Server's keys verbatim where a Db2 analog exists
   (`query_metrics`, `query_activity`, `collect_settings`, `collect_schemas`) so the DBM UI / docs are
   consistent; default intervals: query_metrics 60, query_activity 10, settings/schemas 600.
9. **`run_job_loop` is per-check-run + idempotent** — call it every `check()` when `dbm_enabled`; it
   manages its own thread. Always wire `cancel()`.
10. **Skip:** deadlocks, agent-jobs, XE, stored-procedure metrics for first fidelity (no clean Db2
    analog or low value); schemas optional.

---

## 10. Primary source index (absolute paths)

- Check orchestrator: `sqlserver/datadog_checks/sqlserver/sqlserver.py:14-15, 132-205, 212-225, 267-320, 413-494, 892-926, 931-994, 1151-1173`
- Config / DBM blocks: `sqlserver/datadog_checks/sqlserver/config.py:55-65, 81-140, 203-282`
- Connection isolation: `sqlserver/datadog_checks/sqlserver/connection.py:155-200, 228-247, 276-341, 521-526`
- Cursor wrapper: `sqlserver/datadog_checks/sqlserver/cursor.py:11-46`
- Statements collector: `sqlserver/datadog_checks/sqlserver/statements.py:37-110, 202-213, 254-310, 350-371, 483-595, 600-719`
- Activity collector: `sqlserver/datadog_checks/sqlserver/activity.py:30-44, 47-166, 177-298, 463-509`
- Metadata collector: `sqlserver/datadog_checks/sqlserver/metadata.py:29-50, 57-170`
- Schema collector: `sqlserver/datadog_checks/sqlserver/schemas.py:34-37, 78-276`; queries `sqlserver/datadog_checks/sqlserver/queries.py:8-142`
- Deadlocks: `sqlserver/datadog_checks/sqlserver/deadlocks.py:49-292`
- Const (cache keys / intervals): `sqlserver/datadog_checks/sqlserver/const.py:25-56, 82, 96, 308-312`
- DB metrics base (QueryExecutor pattern): `sqlserver/datadog_checks/sqlserver/database_metrics/base.py:15-123`
- conf.yaml.example DBM blocks: `sqlserver/datadog_checks/sqlserver/data/conf.yaml.example:372, 376, 391, 425, 447, 454, 470, 573, 676, 791, 854, 860, 937`
- DBMAsyncJob framework: `datadog_checks_base/datadog_checks/base/utils/db/utils.py:289-498`
- DatabaseCheck base: `datadog_checks_base/datadog_checks/base/checks/db.py`
- Existing Db2 check (to modify): `ibm_db2/datadog_checks/ibm_db2/ibm_db2.py:28-119, 554-631`
- Companion research: `ibm_db2/dev-docs/db2-fidelity-plan/_research/code-dbm-payload-contract.md`
</content>
</invoke>
