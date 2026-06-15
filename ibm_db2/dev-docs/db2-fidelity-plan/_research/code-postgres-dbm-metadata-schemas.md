# Postgres DBM: Metadata, Schemas & Settings Collection — Deep Dive

Raw input for the Db2 fidelity plan. Documents exactly how the Postgres integration
collects and ships **settings (`pg_settings`)**, **extensions (`pg_extension`)**,
**schema metadata (`pg_databases`)**, and **column statistics**, plus all config
knobs and the base `SchemaCollector` framework. Concludes with concrete Db2 12.1
mapping guidance.

Code citations are absolute paths in `/home/bits/dd/integrations-core`. Db2 claims
cite the live-empirical raw files under
`ibm_db2/dev-docs/db2-fidelity-plan/_research/_raw/` where supported, else marked
"(general Db2 12.1 knowledge — verify)".

---

## 0. File map (what each module does)

| File | Role |
|------|------|
| `postgres/datadog_checks/postgres/metadata.py` | `PostgresMetadata(DBMAsyncJob)` — the single async job that orchestrates settings + extensions + schemas + column-stats collection on a GCD-derived interval. |
| `postgres/datadog_checks/postgres/schemas.py` | `PostgresSchemaCollector(SchemaCollector)` — builds the giant schema/table/column/index/FK query and maps rows into the `pg_databases` payload. |
| `postgres/datadog_checks/postgres/column_statistics.py` | `PostgresColumnStatisticsCollector` — collects `pg_stats`-derived column statistics via a `datadog.column_statistics()` helper function, ships on its own `dbm_type: column_statistics` track. |
| `postgres/datadog_checks/postgres/data_observability.py` | `PostgresDataObservability(DBMAsyncJob)` — unrelated to schema metadata; runs RC-delivered customer SQL on cron/interval, ships results on `do-query-results` track. Included because the prompt named it. |
| `postgres/datadog_checks/postgres/relationsmanager.py` | `RelationsManager` + relation metric query defs (`pg_class`, `pg_class_size`, `pg_index`, `pg_locks`, statio, bloat). This is **metrics**, not metadata, and is **deprecation-pending**, but it is the canonical source of per-relation size/scan/tuple metrics that the Db2 schema/table-metrics work will want to mirror. |
| `postgres/datadog_checks/postgres/filters.py` | `regex_exclude_clauses` / `regex_include_clause` — shared SQL-fragment builders for include/exclude regex filtering. |
| `datadog_checks_base/datadog_checks/base/utils/db/schemas.py` | Abstract `SchemaCollector` base + `SchemaCollectorConfig`. The chunking/flushing/event-envelope engine every DBMS schema collector inherits. |
| `datadog_checks_base/datadog_checks/base/checks/base.py:793` | `database_monitoring_metadata(raw_event)` — submits to the `dbm-metadata` event-platform track. |

ibm_db2 today has **none** of this: `grep -rln "database_monitoring_metadata|collect_schemas|SchemaCollector|pg_settings|collect_settings|DBMAsyncJob" ibm_db2/datadog_checks/` returns nothing. The whole metadata/schemas surface is greenfield for Db2.

---

## 1. Orchestration: `PostgresMetadata` (metadata.py)

`PostgresMetadata` extends `DBMAsyncJob` and is the **single** job that owns four
sub-collections. Lifecycle (`metadata.py:80-167`):

- **Enable gate** (`__init__`, lines 104-115): job runs if **any** of
  `collect_settings.enabled OR collect_schemas.enabled OR collect_column_statistics.enabled`.
  `dbms="postgres"`, `job_name="database-metadata"`,
  `expected_db_exceptions=(psycopg.errors.DatabaseError,)`,
  `run_sync=collect_settings.run_sync`.
- **Interval = GCD of the four sub-intervals** (`metadata.py:97-102`) via
  `collection_interval_gcd(pg_extensions, pg_settings, schemas, column_statistics)`.
  The job ticks at the GCD; each sub-collection self-throttles by comparing
  `time.time()` against its own last-run timestamp and its own configured interval.
  - settings/extensions share one interval (`pg_extensions_collection_interval = pg_settings_collection_interval`, line 93).
- **Column statistics extra gate**: `collect_column_statistics.enabled AND config.dbm` (line 122). Settings/schemas do not re-check `dbm` here (the spec docs say they "Requires `dbm: true`" but the gate is at a higher layer).
- `run_job()` (lines 163-168): strips `dd.internal` tags, computes `_tags_no_db`
  (tags minus any `db:` tag), then calls `report_postgres_metadata()` and
  `report_postgres_extensions()`.

### 1.1 Settings collection — `report_postgres_metadata` / `_collect_postgres_settings`

Throttle: only runs if `elapsed_s >= pg_settings_collection_interval AND _collect_pg_settings_enabled` (lines 210-211).

The core query (`PG_SETTINGS_QUERY`, lines 53-61):

```sql
SELECT
  name,
  case when source = 'session' then reset_val else setting end as setting,
  source,
  sourcefile,
  pending_restart
FROM pg_settings
```

Edge case (commented at lines 50-52): if a setting's `source = 'session'`, report
`reset_val` (the value it would revert to) rather than the live `setting`.

**Extension-loader prelude** (`_collect_postgres_settings`, lines 248-291): before the
settings query, it runs `PG_EXTENSIONS_QUERY` (`SELECT extname, nspname ... FROM
pg_extension`). For each loaded extension that appears in `PG_EXTENSION_LOADER_QUERY`
(`pg_trgm`, `plpgsql`, `pgcrypto`, `hstore` — lines 68-73) **and** lives in
`pg_catalog`/`public`, it prepends a tiny no-op call (e.g. `SELECT
word_similarity('foo','bar');`) so the extension's GUCs become visible in
`pg_settings` for that session. Multiple statements are concatenated; pg3 returns
one result set per statement and the code walks `cursor.nextset()` keeping the last
`TUPLES_OK` result (lines 283-289).

**Ignore patterns** (lines 271-280): if `pg_settings_ignored_patterns` is set,
appends `WHERE name NOT LIKE ALL(%s)` and binds the pattern list. **LIKE** semantics
(SQL wildcards `%`/`_`), e.g. default `['plpgsql%']`.

Settings payload (`report_postgres_metadata`, lines 213-226):

```python
event = {
  "host": reported_hostname,
  "database_instance": database_identifier,
  "agent_version": datadog_agent.get_version(),
  "dbms": "postgres",
  "kind": "pg_settings",
  "collection_interval": pg_settings_collection_interval,
  "dbms_version": payload_pg_version(check.version),
  "tags": _tags_no_db,
  "timestamp": time.time() * 1000,      # ms
  "cloud_metadata": check.cloud_metadata,
  "metadata": settings,                  # list of {name,setting,source,sourcefile,pending_restart}
}
check.database_monitoring_metadata(json.dumps(event, default=default_json_event_encoding))
```

### 1.2 Extensions collection — `report_postgres_extensions` / `_collect_postgres_extensions`

Throttle: `elapsed_s >= pg_extensions_collection_interval AND _collect_extensions_enabled`
(`_collect_extensions_enabled` is just an alias for the settings-enabled flag, line 119).

`PG_EXTENSION_INFO_QUERY` (lines 36-47):

```sql
SELECT e.oid::text AS id, e.extname AS name, r.rolname AS owner,
       ns.nspname AS schema_name, e.extrelocatable AS relocatable, e.extversion AS version
FROM pg_extension e
LEFT JOIN pg_namespace ns on e.extnamespace = ns.oid
     JOIN pg_roles r ON e.extowner = r.oid;
```

Payload identical envelope to settings but `kind: "pg_extension"`, `metadata` =
list of extension dicts (lines 176-189).

### 1.3 Schemas / column-stats dispatch

`report_postgres_metadata` also fires (lines 228-238):
- `_collect_postgres_schemas()` if `_collect_schemas_enabled AND (now - _last_schemas_query_time) > schemas_collection_interval`. Delegates to `PostgresSchemaCollector.collect_schemas()`; if a previous run is still in flight, `collect_schemas` returns falsy and a warning is logged (lines 240-245).
- `_collect_column_statistics()` on its own interval (lines 234-238, 293-298).

---

## 2. The schema payload — `PostgresSchemaCollector` (schemas.py)

`kind = "pg_databases"` (schemas.py:204-205). This is the big one: a single
recursive CTE per database returns one row **per table** with columns/indexes/FKs
aggregated as JSON arrays, then `_map_row` reshapes each row into the nested
`database → schemas → tables → {columns,indexes,foreign_keys}` payload.

### 2.1 Per-DBMS query building blocks

**Databases** — `DATABASE_INFORMATION_QUERY` (lines 160-170), run once against the
main DB by `_get_databases`:

```sql
SELECT db.oid::text AS id, datname AS NAME, pg_encoding_to_char(encoding) AS encoding,
       rolname AS owner, shobj_description(db.oid,'pg_database') AS description
FROM pg_catalog.pg_database db JOIN pg_roles a ON datdba = a.oid
WHERE datname NOT LIKE 'template%'
```
`_get_databases` then appends exclude/include regex clauses on `datname` and an
autodiscovery `IN (...)` clause that **trumps** include/exclude (lines 207-227).
`DatabaseInfo` fields: `description, name, id, encoding, owner` (TypedDict lines 20-26).

**Schemas** — `SCHEMA_QUERY` (lines 67-76): `pg_namespace` joined to `pg_roles`,
excludes `information_schema`, `pg_catalog`, `pg_toast%`, `pg_temp_%`. Selects
`schema_id, schema_name, schema_owner`. `_get_schemas_query` adds exclude/include
regex on `nspname` and an `ignore_schemas_owned_by` clause (lines 240-254).

**Tables** — version-split:
- `PG_TABLES_QUERY_V10_PLUS` (lines 39-51): `relkind IN ('r','p','f')` (ordinary,
  partitioned, foreign) **and** `relispartition != 't'` (excludes partition children).
- `PG_TABLES_QUERY_V9` (lines 53-64): `relkind IN ('r','f')` only.
- Selects `table_id (oid), schema_id (relnamespace), table_name, table_owner
  (relowner::regrole::text), relkind::text, toast_table (joined pg_class via reltoastrelid)`.
- `_get_tables_query` adds exclude/include regex on `c.relname` (lines 256-269).

**Columns** — `COLUMNS_QUERY` (lines 78-90):
```sql
SELECT attname AS name, Format_type(atttypid,atttypmod) AS data_type,
       NOT attnotnull AS nullable, pg_get_expr(adbin,adrelid) AS default, attrelid AS table_id
FROM pg_attribute LEFT JOIN pg_attrdef ad ON adrelid=attrelid AND adnum=attnum
WHERE attnum > 0 AND NOT attisdropped
```
Per-column fields shipped: `name`, `data_type`, `nullable` (bool), `default` (expr text).

**Indexes** — `PG_INDEXES_QUERY` (lines 93-114). `pg_index` joined to `pg_class`.
Fields per index: `name`, `definition` (`pg_get_indexdef`), and booleans
`is_unique, is_exclusion, is_immediate, is_clustered, is_valid, is_checkxmin,
is_ready, is_live, is_replident, is_partial` (`indpred IS NOT NULL`).

**Foreign keys** — `PG_CONSTRAINTS_QUERY` (lines 117-123): `pg_constraint WHERE
contype='f'`. Fields: `name`, `definition` (`pg_get_constraintdef`), `table_id`.
Shipped under key **`foreign_keys`**.

**Partitions (≥ v11 only)** — `PARTITION_KEY_QUERY` (`pg_get_partkeydef`, lines
126-131) and `NUM_PARTITIONS_QUERY` (`count` over `pg_inherits` grouped by
`inhparent`, lines 133-137). Added as CTEs + joins + `(array_agg(...))[1]` selects
only when `version >= V11` (lines 277-310).

### 2.2 The assembled `get_rows_query` (lines 271-359)

One statement per DB, structured as CTEs `schemas`, `tables`, `schema_tables`
(schemas LEFT JOIN tables, `ORDER BY schema_name,table_name LIMIT {max_tables}`),
`columns`, `indexes`, `constraints`, plus partition CTEs on v11+. The final SELECT
LEFT JOINs everything onto `schema_tables` and aggregates:

```sql
array_agg(row_to_json(columns.*))     FILTER (WHERE columns.name IS NOT NULL)     AS columns,
array_agg(row_to_json(indexes.*))     FILTER (WHERE indexes.name IS NOT NULL)     AS indexes,
array_agg(row_to_json(constraints.*)) FILTER (WHERE constraints.name IS NOT NULL) AS foreign_keys
-- v11+ also: (array_agg(partition_keys.partition_key))[1], (array_agg(num_partitions))[1]
GROUP BY schema_id,schema_name,schema_owner,table_id,table_name,table_owner,relkind,toast_table
```

`max_tables` LIMIT defaults to `1_000_000` if unset (line 311). **LIMIT is applied
in `schema_tables` (before grouping)** so it caps schema×table rows, not output rows.

### 2.3 Cursor & per-DB execution — `_get_cursor` (lines 229-238)

Connects to each DB via `check.db_pool.get_connection(database_name)`. Wraps the
single big query in an **explicit transaction** and sets
`SET LOCAL statement_timeout = '{max_query_duration}s'` so the timeout reverts on
commit. `_get_next` = `cursor.fetchone()` (streamed one table at a time, line
361-362).

### 2.4 Row → payload mapping — `_map_row` (lines 367-406)

Calls base `_map_row` (returns the DB dict splat) then attaches `schemas`. Shape:

```
{   # DatabaseObject (PostgresDatabaseObject)
  description, name, id, encoding, owner,     # from DATABASE_INFORMATION_QUERY
  "schemas": [{
     "id": str(schema_id), "name": schema_name, "owner": schema_owner,
     "tables": [{
        "id": str(table_id), "name": table_name, "owner": table_owner,
        "columns":      [ {name,data_type,nullable,default}, ... ][:max_columns],
        "indexes":      [ {name,definition,is_unique,...}, ... ],
        "foreign_keys": [ {name,definition}, ... ],
        "relkind": ..., "toast_table": ..., "num_partitions": ..., "partition_key": ...
     }]  # [] when table_name is NULL (empty schema)
  }]
}
```

Important shaping details:
- **Dedup** of columns/indexes/FKs via `{v['name']: v for v in ...}.values()` — the
  multi-LEFT-JOIN can produce duplicate rows; dedup keys on the object's `name`
  (lines 385-391).
- **`max_columns` truncation** is applied here per table (line 386-387), distinct
  from the row-level `max_tables` LIMIT in SQL.
- **None-stripping**: every dict comprehension drops keys whose value is `None`
  (`if v is not None`), so optional fields (`toast_table`, `num_partitions`,
  `partition_key`) simply don't appear when absent.
- One database = one `DatabaseObject`; `_map_row` returns exactly one element in
  `schemas` per cursor row (because each row is one schema+table combo), and the
  base collector accumulates these into `_queued_rows`.

### 2.5 PostgresSchemaCollectorConfig (lines 173-201)

Maps from `check._config.collect_schemas.*`:
`collection_interval, max_tables, exclude/include_databases, exclude/include_schemas,
exclude/include_tables, max_columns (int), max_query_duration (int)`. Note
`payload_chunk_size` is inherited from base (`10_000`, not overridden).

---

## 3. Base `SchemaCollector` framework (datadog_checks_base .../db/schemas.py)

The reusable engine. **A Db2 schema collector should subclass this**, implementing 5
methods: `kind` (property), `_get_databases`, `_get_cursor`, `_get_next`, `_map_row`.

### 3.1 `SchemaCollectorConfig` (lines 36-39)
- `collection_interval = 3600`
- `payload_chunk_size = 10_000`

### 3.2 `collect_schemas()` engine (lines 60-133)

- Returns `True` to signal "started/completed"; the calling check handles scheduling.
- Calls `_get_databases()`, then per database: opens `_get_cursor(database_name)`,
  streams rows via `_get_next`, calls `_map_row(database, next_row)` and appends to
  `_queued_rows`, calling `maybe_flush(is_last_payload=False)` after each row.
- After a DB finishes, `maybe_flush(is_last_payload=True)`.
- **Per-DB error isolation**: an exception inside one DB's loop is caught, that DB is
  skipped with a warning, the loop continues (lines 101-105). A failure in
  `_get_databases` itself sets status=error and re-raises (lines 106-109).

### 3.3 `maybe_flush` & event envelope (lines 135-163)

Flushes when `is_last_payload` OR `len(_queued_rows) >= payload_chunk_size`.
`base_event` (lines 135-148):
```python
{ "host", "database_instance", "kind": self.kind, "agent_version",
  "collection_interval", "dbms": check.dbms, "dbms_version": str(check.dbms_version),
  "tags": check.tags, "cloud_metadata", "collection_started_at" }  # ms
```
On flush, adds `timestamp` (ms) and `metadata` = the queued rows (an **array of
DatabaseObjects**). On the **last** payload only, adds
`collection_payloads_count` (snapshot-completeness signal so the backend knows the
full set was received). Ships via `check.database_monitoring_metadata(json.dumps(event))`.

### 3.4 Telemetry emitted by the base collector (lines 110-132, "finally")

Always emitted (raw, `hostname=reported_hostname`, tags include `status:success|error`):
- `dd.{dbms}.schema.time` — **histogram**, ms, wall-clock of the whole run.
- `dd.{dbms}.schema.tables_count` — **gauge**, cumulative rows mapped.
- `dd.{dbms}.schema.payloads_count` — **gauge**, total payloads sent.

For Db2 these become `dd.ibm_db2.schema.time` / `.tables_count` / `.payloads_count`
(driven by `check.dbms`).

---

## 4. Column statistics — `PostgresColumnStatisticsCollector` (column_statistics.py)

**Separate track** from schemas: ships via
`check.database_monitoring_column_statistics(...)` (line 340) and tags the envelope
`"dbm_type": "column_statistics"` (line 137) — NOT a `kind`-discriminated
`dbm-metadata` event.

### 4.1 Query — `COLUMN_STATISTICS_QUERY` (lines 36-81)

Relies on a **customer-installed helper function `datadog.column_statistics()`**
(line 65) that surfaces `pg_stats` per (schema, table). CTE `tables` selects
`relkind='r'` user tables (excluding `pg_catalog`/`information_schema`) ordered &
`LIMIT %s` (= `max_tables`). `column_data` joins the helper to `pg_stat_all_tables`,
building a per-column JSON object:
```json
{ "name", "avg_width", "n_distinct", "null_frac", "inherited",
  "correlation", "most_common_freqs" }
```
and age columns from `pg_stat_all_tables`: `last_analyze_age`,
`last_autoanalyze_age`, `last_vacuum_age`, `last_autovacuum_age`, `stats_age`
(EXTRACT EPOCH of `NOW() - <ts>`, bigint seconds). Final SELECT groups by
schema+table, `json_agg(col ORDER BY col->>'name') AS columns`.

### 4.2 Behavior & constants
- `PAYLOAD_MAX_COLUMNS = 5_000`, `MAX_QUERY_DURATION_SECONDS = 60` (lines 84-85).
- Config defaults (lines 88-98): `collection_interval=3600, max_tables=500`, plus
  include/exclude databases/schemas/tables.
- Filters built by `_build_filters` (lines 141-157) via the same
  `regex_exclude_clauses`/`regex_include_clause` (on `n.nspname` and `c.relname`).
- `_get_databases` (159-168): autodiscovery items or `[dbname]`, then exclude/include
  regex via `re.search`.
- Per-DB collection sets `SET statement_timeout` then `RESET`s in finally (lines
  243-265). Flushes at `PAYLOAD_MAX_COLUMNS` and at DB boundary.
- **Graceful degradation / health events**: `UndefinedFunction` →
  `COLUMN_STATISTICS_FUNCTION_NOT_FOUND` WARNING (once per DB);
  `InsufficientPrivilege` → `COLUMN_STATISTICS_INSUFFICIENT_PRIVILEGE` WARNING;
  recovery re-emits OK health events (lines 271-318).
- `table_data['version'] = 1` stamped on each table (line 252).

### 4.3 Payload (`_base_event` lines 128-139, `_flush` lines 333-342)
```python
{ "host", "database_instance", "ddagentversion", "dbms":"postgres",
  "dbms_version": payload_pg_version(...), "cloud_metadata",
  "dbm_type":"column_statistics", "collection_interval",
  "tags": tags_no_db, "timestamp": ms,
  "column_statistics": [ {db,schema,table,last_*_age,stats_age,columns:[...],version:1}, ... ] }
```

### 4.4 Telemetry (lines 205-232)
`dd.postgres.column_statistics.time` (histogram, ms),
`.tables_count`, `.columns_count`, `.payloads_count` (gauges), all tagged
`status:success|error`.

---

## 5. Data Observability — `PostgresDataObservability` (data_observability.py)

Named in the prompt but **orthogonal to schema/metadata**: it executes
**RC-delivered customer SELECT queries** on a cron or fixed interval and ships
result sets. Track = `do-query-results` (`EVENT_TRACK_TYPE`, line 21).

- `DBMAsyncJob`, `job_name="data-observability"`, interval = `collection_interval or 10` (lines 44-59).
- Queries validated on construction (`_filter_valid_queries`, 70-94): each `Query`
  needs either a valid cron `schedule` (→ `CronScheduler`, startup lookback 300s,
  line 29) or a positive `interval_seconds`.
- `MAX_RESULT_ROWS = 10_000` (line 23); per-query `query_timeout` (ms) applied via
  `SELECT set_config('statement_timeout', %s, true)` inside an explicit transaction
  on a pooled autocommit connection (lines 145-151, see comment 138-144 on why
  `set_config` not `SET LOCAL` under psycopg3 extended protocol).
- Non-SELECT (cursor.description None) → per-query ProgrammingError, loop continues
  (lines 156-159).
- Event payload (`_build_event_payload`, 194-213): `timestamp(ms), config_id,
  db_type:'postgres', db_host, db_port, db_name, monitor_id, query, entity,
  custom_sql_select_fields, **result(status,columns,rows,row_count,duration_s,error)`.
  Shipped via `check.event_platform_event(raw_event, "do-query-results")` (line 275).
- Telemetry (raw gauges/counts): `dd.postgres.data_observability.query_execution_time`,
  `.query_executions` (tagged `status:`), `.query_fire_lateness_seconds` (tagged
  `mode:cron|interval`), `.emit_failures` (tagged `exc_class:`). Tags include
  `config_id:`, `db_type:postgres`, `monitor_id:`.

**Db2 relevance:** this is a generic "run customer SQL, return rows" capability and
is the lowest-priority port; mention only as a possible later phase.

---

## 6. Relations metrics — `relationsmanager.py` (metrics, deprecation-pending)

Not metadata, but the authoritative per-relation metric catalog. Module header marks
it **pending deprecation** (new queries should use QueryExecutor/QueryManager and
support autodiscovery instead of requiring per-DB connections). Still, the metric
shapes here are what Db2 table-level metrics should mirror.

`RelationsManager` (lines 425-512) builds a WHERE clause from `relations` config
(`relation_name` exact / `relation_regex` / `schemas` / `relkind`) and a
`LIMIT max_relations`, then `.format(relations=..., limits=...)` into the query
templates. `validate_relations_config` enforces exactly one of name/regex.

Metric definitions (all relation-scoped, tags `db`, `schema`, `table`, …):

| Const | Source view/fns | Notable metric columns (name → type) |
|-------|-----------------|--------------------------------------|
| `LOCK_METRICS` (`pg_locks`) | `pg_locks` joined to db/class/namespace | `locks`→gauge; tags lock_mode/lock_type/granted/fastpath |
| `IDX_METRICS` (`pg_index`) | `pg_stat_get_*` index fns | `index_scans/index_rows_read/index_rows_fetched/index.index_blocks_read/index.index_blocks_hit`→rate; `individual_index_size`→gauge |
| `QUERY_PG_CLASS_SIZE` | `pg_relation_size`/`pg_indexes_size` | `relation.pages/relation.tuples/relation.all_visible`→gauge; `table_size/relation_size/index_size/toast_size/total_size`→gauge |
| `QUERY_PG_CLASS` | `pg_stat_get_*` table fns | `seq_scans/seq_rows_read/index_rel_scans/index_rel_rows_fetched/rows_inserted/rows_updated/rows_deleted/rows_hot_updated`→rate; `live_rows/dead_rows`→gauge; `vacuumed/autovacuumed/analyzed/autoanalyzed`→monotonic_count; `last_*_age`→gauge; toast.* mirror set |
| `STATIO_METRICS` | `pg_statio_user_tables` | heap/idx/toast/tidx `_blks_read/_blks_hit`→rate |
| `TABLE_BLOAT` / `INDEX_BLOAT` | `pg_stats`-based estimation | `table_bloat`/`index_bloat`→gauge |

Sizing is deliberately approximated to limit lock-taking stat syscalls; explicitly
**skips relations under AccessExclusiveLock** (`NOT EXISTS (... pg_locks ...)`) to
avoid timeouts. Filters out `pg_catalog`/`information_schema`.

---

## 7. Config knobs (postgres spec + config_models)

Spec: `postgres/assets/configuration/spec.yaml`. Generated models:
`postgres/datadog_checks/postgres/config_models/instance.py`. All fields are
`Optional[...] = None` in the model; **runtime defaults live in the generated
`defaults.py` / `init_config` deprecations and in the example values below**, not in
the model class.

### 7.1 `collect_settings` (spec 938-979)
| Option | Type | Example/Default | Notes |
|--------|------|-----------------|-------|
| `enabled` | bool | `true` | gate; "Requires dbm:true" |
| `collection_interval` | number | `600` | seconds |
| `ignored_settings_patterns` | array[str] | default `['plpgsql%']` | **LIKE** patterns (`NOT LIKE ALL`) |
| `run_sync` | bool (hidden) | `false` | testing only |

### 7.2 `collect_schemas` (spec 980-1104)
| Option | Type | Example / display_default |
|--------|------|---------------------------|
| `enabled` | bool | `true` |
| `max_tables` | number | `300` |
| `max_query_duration` | number | `60` (s) |
| `max_columns` | number | `50` |
| `collection_interval` | number | `600` (s) |
| `include_databases` / `exclude_databases` | array[str] **regex** | exclude default `[template0,template1,rdsadmin,azure_maintenance,cloudsqladmin,alloydbadmin,alloydbmetadata]` |
| `include_schemas` / `exclude_schemas` | array[str] **regex** | — |
| `include_tables` / `exclude_tables` | array[str] **regex** | — |

Plus, at the top instance level: `ignore_schemas_owned_by` (spec line 304) — list of
role names; schemas owned by these roles are filtered out in `_get_schemas_query`
(schemas.py:250-253).

Note the **filter semantics differ**: `collect_settings.ignored_settings_patterns`
uses SQL **LIKE**; everything in `collect_schemas`/`collect_column_statistics` uses
**POSIX regex** (`~` / `!~` via `filters.py`, and `re.search` for databases).

### 7.3 `collect_column_statistics` (spec 1106-1205)
All `fleet_configurable: false`. `enabled`(false), `collection_interval`(3600),
`max_tables`(500), include/exclude databases/schemas/tables (regex). Requires the
`datadog.column_statistics()` function + `dbm:true`.

### 7.4 Generated models (instance.py)
`CollectSettings` (123-): `collection_interval, enabled, ignored_settings_patterns,
run_sync`. `CollectSchemas` (105-): adds `max_columns, max_query_duration,
max_tables` + the 6 include/exclude tuples. `CollectColumnStatistics` (81-): same
include/exclude set + `max_tables`. All frozen pydantic models.

---

## 8. Event-platform envelope reference (cross-cutting)

`database_monitoring_metadata(raw_event)` (base.py:793-798) → track **`dbm-metadata`**.
Within that track, sub-types are discriminated by **`kind`**:
- `"pg_settings"` (settings), `"pg_extension"` (extensions), `"pg_databases"`
  (schemas), and the instance-registration `"database_instance"` heartbeat (emitted
  elsewhere in `postgres.py`, see `_research/code-dbm-payload-contract.md`).

Column statistics use a different submitter
(`database_monitoring_column_statistics`) and `dbm_type: "column_statistics"`, not
`kind`.

Common identity fields on every payload: `host` (= `reported_hostname`),
`database_instance` (= `database_identifier`), `dbms`, `dbms_version`, `tags`
(settings/extensions/column-stats use `_tags_no_db`; the base schema collector uses
full `check.tags`), `cloud_metadata`, `agent_version`/`ddagentversion`, `timestamp`
(ms). Schema events additionally carry `collection_started_at` (ms) and, on the final
chunk, `collection_payloads_count`.

---

## 9. Db2 12.1 mapping guidance (for the planning agent)

### 9.1 Settings → "db2_settings" (analog of `pg_settings`)
Postgres has one flat `pg_settings`. Db2 splits configuration across **three+ scopes**;
a faithful port emits one or several settings payloads sourced from:
- **DBM config** (instance-level): `SYSIBMADM.DBMCFG` view exists
  (`_raw/03-sysibmadm-objects.txt:25`). Columns `NAME, VALUE, DEFERRED_VALUE,
  DATATYPE` (general Db2 12.1 knowledge — verify).
- **DB config** (database-level): `SYSIBMADM.DBCFG` view exists
  (`_raw/03-sysibmadm-objects.txt:24`). Per-member rows; columns `NAME, VALUE,
  DEFERRED_VALUE, MEMBER, DATATYPE` (general Db2 12.1 knowledge — verify). This is
  where the monitoring switches live; the live instance has e.g.
  `mon_act_metrics=BASE, mon_obj_metrics=EXTENDED, mon_req_metrics=BASE,
  mon_uow_data=NONE` (`_raw/04-monitor-config.txt:9-22`).
- **Registry variables**: `SYSIBMADM.REG_VARIABLES` view exists
  (`_raw/03-sysibmadm-objects.txt:54`). Columns `REG_VAR_NAME, REG_VAR_VALUE,
  IS_AGGREGATE, AGGREGATE_NAME, LEVEL` (general Db2 12.1 knowledge — verify) — the
  closest analog to extension GUCs.
- The Postgres `source='session' → reset_val` edge case maps to Db2's
  `VALUE` vs `DEFERRED_VALUE` (the value pending next activation/restart) — i.e.
  `DEFERRED_VALUE` is the `pending_restart`/`reset_val` analog (general Db2 12.1
  knowledge — verify). Postgres `pending_restart` ≈ "VALUE != DEFERRED_VALUE".
- Suggested envelope: `kind: "db2_settings"` (or per-scope kinds
  `db2_database_config`/`db2_dbm_config`/`db2_registry`), `metadata` = rows of
  `{name, value, deferred_value, scope/member, datatype}`. Mirror the
  `code-dbm-payload-contract.md` note (line 407): "Db2 equivalents would be
  `kind: db2_settings`".

### 9.2 Schemas → subclass base `SchemaCollector`, `kind="db2_databases"`
Db2 catalog tables (in `SYSCAT`) provide every piece (general Db2 12.1 knowledge —
verify exact columns):
- **Databases**: Db2 has one database per connection; a Db2 collector's
  `_get_databases` likely returns the single connected DB (`ENV_INST_INFO` /
  `ENV_PROD_INFO` views exist, `_raw/03-sysibmadm-objects.txt:30-31`, for
  name/version). Encoding/owner come from the database config / catalog.
- **Schemas** ≈ `SYSCAT.SCHEMATA` (`SCHEMANAME, OWNER`). Exclude system schemas
  `SYSCAT, SYSIBM, SYSSTAT, SYSPUBLIC, SYSTOOLS, NULLID, SYSIBMADM, SYSIBMINTERNAL,
  SYSIBMTS` (analogous to Postgres excluding `pg_catalog`/`information_schema`).
- **Tables** ≈ `SYSCAT.TABLES` (`TABSCHEMA, TABNAME, OWNER, TYPE, CARD, NPAGES,
  FPAGES`). `TYPE` codes: `T`=table, `V`=view, `S`=MQT/summary, `A`=alias,
  `N`=nickname — analog of `relkind`; filter to `T` (and maybe `S`).
- **Columns** ≈ `SYSCAT.COLUMNS` (`TABSCHEMA, TABNAME, COLNAME, TYPENAME, LENGTH,
  SCALE, NULLS('Y'/'N'), DEFAULT, COLNO`). `NULLS='Y'` → `nullable: true`;
  `DEFAULT` → `default`; `TYPENAME(+LENGTH/SCALE)` → `data_type`.
- **Indexes** ≈ `SYSCAT.INDEXES` (`INDSCHEMA, INDNAME, TABSCHEMA, TABNAME,
  UNIQUERULE('U'/'P'/'D'), COLNAMES, INDEXTYPE`). `UNIQUERULE in ('U','P')` →
  `is_unique`; column list from `COLNAMES` or `SYSCAT.INDEXCOLUSE`. Db2 lacks
  Postgres' `pg_get_indexdef`; build the definition string or ship structured
  fields.
- **Foreign keys** ≈ `SYSCAT.REFERENCES` (`CONSTNAME, TABSCHEMA, TABNAME,
  REFTABSCHEMA, REFTABNAME, FK_COLNAMES, PK_COLNAMES`).
- Db2 has **no TOAST and (pre-12 partitioning differs)**: drop `toast_table`; map
  partitioning to Db2 range/MDC partitioning via `SYSCAT.DATAPARTITIONS` if desired
  (general Db2 12.1 knowledge — verify) — lowest priority.
- **Query strategy difference**: the Postgres single-statement `row_to_json` +
  `array_agg(... FILTER ...)` approach won't translate directly (Db2 has
  `LISTAGG`/`XMLAGG`/`JSON_OBJECT` but no `row_to_json`). Cleaner for Db2 to issue
  separate catalog queries per object kind and assemble the nested payload in Python
  inside `_map_row`/`_get_next` (still honoring `max_tables`/`max_columns`). The base
  collector's streaming + chunking + `collection_payloads_count` machinery is reused
  unchanged.
- Emitted telemetry auto-namespaces to `dd.ibm_db2.schema.{time,tables_count,payloads_count}`.

### 9.3 Column statistics (optional later phase)
Db2 column stats live in `SYSCAT.COLUMNS`/`SYSSTAT.COLUMNS`
(`COLCARD`≈`n_distinct`, `NUMNULLS`/`CARD`→`null_frac`, `AVGCOLLEN`≈`avg_width`,
`HIGH2KEY`/`LOW2KEY`, no direct `correlation`/`most_common_freqs` equivalent unless
distribution stats / `SYSSTAT.COLDIST` are read) (general Db2 12.1 knowledge —
verify). Table analyze ages come from RUNSTATS timestamps
(`SYSCAT.TABLES.STATS_TIME`). No customer-installed helper function needed; Db2
exposes these directly to a privileged user.

### 9.4 Config knobs to add for Db2
Mirror `collect_settings` (interval + ignore patterns) and `collect_schemas`
(`enabled, collection_interval, max_tables, max_columns, max_query_duration`,
include/exclude `schemas`/`tables`). **Drop the `*_databases` filters** (single DB
per Db2 connection) unless multi-DB autodiscovery is added. Decide LIKE-vs-regex
filtering — recommend regex via the shared `filters.py` helpers for consistency with
the rest of DBM, noting Db2 catalog filtering must push the predicate as LIKE/regex
that Db2 SQL supports (Db2 has no POSIX `~`; use `LIKE` or `REGEXP_LIKE`).
`max_query_duration` maps to a Db2 statement-level timeout
(`SET CURRENT QUERY OPTIMIZATION` is unrelated; use a connection attribute /
`STMTHEAP`-independent timeout such as `CURRENT_QUERY_TIMEOUT` if available, else a
client-side cursor timeout) (general Db2 12.1 knowledge — verify).

---

## 10. Quick reference — exact payload `kind`/track values

| Collector | Method/track | Discriminator | Payload key for rows |
|-----------|--------------|---------------|----------------------|
| Settings | `database_monitoring_metadata` → `dbm-metadata` | `kind:"pg_settings"` | `metadata` (list) |
| Extensions | `database_monitoring_metadata` → `dbm-metadata` | `kind:"pg_extension"` | `metadata` (list) |
| Schemas | `database_monitoring_metadata` → `dbm-metadata` | `kind:"pg_databases"` | `metadata` (list of DatabaseObjects) + `collection_started_at`, `collection_payloads_count` |
| Column stats | `database_monitoring_column_statistics` | `dbm_type:"column_statistics"` | `column_statistics` (list) |
| Data observability | `event_platform_event` → `do-query-results` | n/a | `rows`/`columns`/`row_count` inline |
