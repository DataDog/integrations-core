# 08 — DBM Schemas & Settings/Metadata Collection for Db2

> **Purpose.** Design the Db2 analogs of postgres `metadata.py` (settings/extensions) and `schemas.py`
> (catalog schema collection), shipped on the **`dbm-metadata`** event-platform track. This is the
> greenfield "P4" work item (see [`00-README.md`](00-README.md) §"Scope at a glance", and
> [`10-implementation-phases.md`](10-implementation-phases.md) P4): the existing `ibm_db2` check emits
> **none** of `database_monitoring_metadata`, `SchemaCollector`, settings, or a `database_instance`
> event. Everything here is new.
>
> **What this doc covers (the prompt's six pillars):**
> 1. SCHEMA collection from the Db2 catalog (`SYSCAT.*`) → the `"schemas"` payload.
> 2. SETTINGS collection (`SYSIBMADM.DBMCFG` ∪ `DBCFG` + `REG_VARIABLES`) → the settings/metadata payload.
> 3. Version / edition / instance metadata (`ENV_INST_INFO` etc.) for the `database_instance` payload.
> 4. Cardinality controls + collection interval (default ~600s).
> 5. Payload shapes (per the contract: `dbms:"db2"`, `ddtags`, ms timestamps) + `DBMAsyncJob` scheduling
>    + conf knobs.
> 6. Privileges.
>
> **Cross-references (by final filename; some are referenced-but-unwritten per
> [`00-README.md`](00-README.md)):**
> - [`03-reference-architecture.md`](03-reference-architecture.md) — `DatabaseCheck` subclassing,
>   identity properties, the five tracks.
> - [`04-metrics-fidelity-plan.md`](04-metrics-fidelity-plan.md) — `MON_GET_*` metrics; the metrics
>   counterpart to the metadata here.
> - `09-implementation-architecture.md` *(referenced-but-unwritten)* — where the async jobs are wired
>   into the check object; this doc defines the metadata job that 09 must instantiate.
> - `12-risks-open-questions.md` *(referenced-but-unwritten)* — privilege/`SYSMON` rollout risk, the
>   `REG_VARIABLES` startup-skew caveat, and Db2-has-no-`row_to_json` query-strategy risk are logged here.
> - [`05-dbm-query-metrics.md`](05-dbm-query-metrics.md), [`06-dbm-query-samples-activity.md`](06-dbm-query-samples-activity.md),
>   [`07-dbm-execution-plans.md`](07-dbm-execution-plans.md) — sibling `dbm-*` collectors that share the
>   `DBMAsyncJob` framework and identity/obfuscation infra.
>
> **Source grounding.** Live column lists/values cited `[LIVE]` come from the 12.1.4 container research
> in [`_research/db2-config-settings.md`](_research/db2-config-settings.md). Payload-envelope facts cite
> [`_research/code-dbm-payload-contract.md`](_research/code-dbm-payload-contract.md). Postgres/mysql
> patterns cite [`_research/code-postgres-dbm-metadata-schemas.md`](_research/code-postgres-dbm-metadata-schemas.md)
> and [`_research/code-mysql-dbm.md`](_research/code-mysql-dbm.md). Catalog-column claims not yet
> live-`DESCRIBE`'d on 12.1.4 are marked **(verify)** and should be promoted to `[LIVE]` during P4
> implementation (same discipline as [`04-metrics-fidelity-plan.md`](04-metrics-fidelity-plan.md)).

---

## 0. TL;DR — what gets built

A **single** `DBMAsyncJob` subclass, `Db2Metadata` (analog of postgres `PostgresMetadata` /
mysql `MySQLMetadata`), owns three sub-collections gated independently and self-throttled by their own
intervals:

| Sub-collection | Source | Track / `kind` | Default interval | Maps from postgres |
|---|---|---|---|---|
| **Settings** | `SYSIBMADM.DBMCFG` ∪ `SYSIBMADM.DBCFG` | `dbm-metadata` / `kind:"db2_settings"` | 600 s | `pg_settings` (`metadata.py`) |
| **Registry vars** *(optional sub-event)* | `SYSIBMADM.REG_VARIABLES` | `dbm-metadata` / `kind:"db2_registry_variables"` | 600 s (shares settings interval) | `pg_extension` slot (the "extra config layer") |
| **Schemas** | `SYSCAT.SCHEMATA/TABLES/COLUMNS/INDEXES/INDEXCOLUSE/TABCONST/KEYCOLUSE/REFERENCES` | `dbm-metadata` / `kind:"db2_databases"` | 600 s | `pg_databases` (`schemas.py` + base `SchemaCollector`) |

Separately, the **`database_instance`** registration event (`kind:"database_instance"`,
`metadata.dbm=true`) — the single must-have payload for the host to appear in the DBM UI — is emitted by
the **check object** (not this job), debounced per `database_identifier`. It carries the
version/edition/instance metadata derived in §3. See
[`03-reference-architecture.md`](03-reference-architecture.md) for where that lives.

The schema collector **subclasses the shared `SchemaCollector`** base
(`datadog_checks_base/datadog_checks/base/utils/db/schemas.py`) and overrides only `kind`,
`_get_databases`, `_get_cursor`, `_get_next`, `_map_row`. The base handles chunking, the event envelope,
`collection_payloads_count`, per-DB error isolation, and `dd.ibm_db2.schema.*` telemetry — all for free.

**Db2 vs postgres, the one structural difference that drives the design:** Db2 has **no `row_to_json` /
`array_agg(... FILTER ...)`** (postgres builds the whole nested payload in one statement,
`code-postgres-dbm-metadata-schemas.md` §2.2). Db2 *does* have `LISTAGG`/`JSON_OBJECT`/`JSON_ARRAYAGG`,
but the clean port is to issue **separate `SYSCAT` queries per object kind** and assemble the nested
`database → schemas → tables → {columns, indexes, foreign_keys}` structure **in Python** inside
`_get_next`/`_map_row`, still honoring `max_tables`/`max_columns`. The base collector's streaming +
chunking machinery is reused unchanged (`code-postgres-dbm-metadata-schemas.md` §9.2). This is logged in
`12-risks-open-questions.md`.

---

## 1. SCHEMA collection — `Db2SchemaCollector(SchemaCollector)` → `kind:"db2_databases"`

### 1.1 The base contract we inherit

`SchemaCollector.collect_schemas()` (base `schemas.py:60-133`) drives the loop: it calls
`_get_databases()`, then per database opens `_get_cursor(database_name)`, pulls rows with `_get_next`,
calls `_map_row(database, row)` → appends to `_queued_rows`, and calls `maybe_flush()` after each row.
`maybe_flush` (base `schemas.py:150-163`) emits a `dbm-metadata` event whenever the queue hits
`payload_chunk_size` (default 10_000) or the DB finishes; the **last** payload carries
`collection_payloads_count` (snapshot-completeness signal). Per-DB exceptions are caught and that DB is
skipped (base `schemas.py:101-105`). Telemetry `dd.ibm_db2.schema.{time,tables_count,payloads_count}` is
emitted in the `finally` (base `schemas.py:110-132`) — auto-namespaced via `self._check.dbms`.

So the Db2 subclass implements exactly five things. The non-obvious one is **streaming granularity**:
the base treats *one cursor row = one mapped object appended to the queue*. The cleanest Db2 mapping is
**one "row" = one fully-assembled table object's worth of catalog data**; we drive that by making
`_get_next` return the next table (with its columns/indexes/FKs already attached), and `_map_row`
wrap it into the `database → schemas → tables` shape. Because Db2 is single-DB-per-connection, there is
exactly **one** `DatabaseObject` per collection, and each flushed chunk's `metadata` array is a list of
**schema-grouped tables** belonging to that one database object. (We accumulate per-table and group into
schemas at flush; see §1.7 for the exact assembly to keep the payload shape identical to postgres.)

### 1.2 `_get_databases` — Db2 is single-DB-per-connection

Postgres iterates many databases (`code-postgres-dbm-metadata-schemas.md` §2.1). A Db2 connection is
bound to **one** database (the check connects to `CONFIG['db']`,
`ibm_db2.py:554-578`). So `_get_databases` returns a **single-element list** describing the connected DB.
Its name/version/owner come from §3's env views:

```python
def _get_databases(self) -> list[DatabaseInfo]:
    # Single DB per Db2 connection. No *_databases include/exclude filters (drop them — see §4.1).
    return [{
        "name":  self._check._config.db,           # connected database name (e.g. "TESTDB")
        "id":    self._check._config.db,            # no numeric DB oid in Db2; use the name as id
        "owner": self._dbadm_owner,                 # optional; from CURRENT_USER or SYSCAT (verify)
        # encoding/collation are DB CFG params (codeset/collate_info) — fold in from §2 if desired
    }]
```

> **Multi-DB note (future):** a Db2 *instance* can host multiple databases (`SYSIBMADM.DBMCFG numdb` is
> the limit; live `numdb=32` `[LIVE]`). Cataloging them requires either separate per-DB connections or
> `MON_GET_DATABASE`/`db2 list db directory`. Out of scope for P4; if added later, restore
> `include_databases`/`exclude_databases` filters. Logged in `12-risks-open-questions.md`.

### 1.3 Schemas — `SYSCAT.SCHEMATA`, filter system schemas

```sql
SELECT schemaname AS schema_name,
       owner      AS schema_owner
FROM   SYSCAT.SCHEMATA
WHERE  schemaname NOT LIKE 'SYS%'        -- SYSCAT, SYSIBM, SYSSTAT, SYSIBMADM, SYSIBMINTERNAL, SYSIBMTS, SYSPROC...
  AND  schemaname NOT IN ('SYSTOOLS', 'SYSPUBLIC', 'NULLID', 'SQLJ')
  AND  schemaname NOT LIKE 'SYSTOOLS%'
ORDER BY schemaname;
```

`SYSCAT.SCHEMATA` columns of interest **(verify exact set on 12.1.4)**: `SCHEMANAME`, `OWNER`,
`OWNERTYPE`, `DEFINER`, `CREATE_TIME`, `REMARKS`. The system-schema filter is the Db2 analog of
postgres excluding `pg_catalog`/`information_schema`/`pg_toast%`
(`code-postgres-dbm-metadata-schemas.md` §2.1). The canonical Db2 system-schema set to exclude (mirrors
the list in `code-postgres-dbm-metadata-schemas.md` §9.2):

`SYSCAT, SYSIBM, SYSSTAT, SYSPUBLIC, SYSTOOLS, NULLID, SYSIBMADM, SYSIBMINTERNAL, SYSIBMTS, SYSPROC, SQLJ`.

A single `schemaname NOT LIKE 'SYS%'` covers most (every system schema except `NULLID`, `SYSTOOLS`,
`SQLJ`, `SYSPUBLIC` starts with `SYS`); enumerate the rest explicitly. Apply
`include_schemas`/`exclude_schemas` filters here (§4.2).

### 1.4 Tables — `SYSCAT.TABLES`

```sql
SELECT tabschema  AS schema_name,
       tabname    AS table_name,
       owner      AS table_owner,
       type       AS table_type,        -- 'T' table, 'V' view, 'S' MQT/summary, 'A' alias, 'N' nickname, ...
       card       AS estimated_rows,    -- from last RUNSTATS (-1 if unknown); optional
       stats_time AS stats_time         -- last RUNSTATS timestamp; optional (analog of last_analyze)
FROM   SYSCAT.TABLES
WHERE  tabschema NOT LIKE 'SYS%'
  AND  tabschema NOT IN ('SYSTOOLS','SYSPUBLIC','NULLID','SQLJ')
  AND  type = 'T'                       -- ordinary tables only; add 'S' (MQT) if desired
ORDER BY tabschema, tabname
FETCH FIRST {max_tables} ROWS ONLY;     -- cardinality cap (§4.3); Db2 uses FETCH FIRST, not LIMIT
```

`SYSCAT.TABLES` columns **(verify)**: `TABSCHEMA`, `TABNAME`, `OWNER`, `TYPE`, `CARD`, `NPAGES`,
`FPAGES`, `STATS_TIME`, `TBSPACE`, `CREATE_TIME`, `REMARKS`. `TYPE` is the Db2 analog of postgres
`relkind`: filter to `'T'` (ordinary table); optionally include `'S'` (MQT/summary). **Drop
`toast_table`** entirely — Db2 has no TOAST (`code-postgres-dbm-metadata-schemas.md` §9.2). The
`FETCH FIRST {max_tables} ROWS ONLY` is the Db2 spelling of postgres' `LIMIT {max_tables}` applied at the
`schema_tables` stage (postgres `schemas.py:271-311`); like postgres, cap **before** assembling
columns/indexes so the limit bounds the work, not just the output.

Apply `include_tables`/`exclude_tables` filters here (§4.2). Order by `(tabschema, tabname)` so the
`FETCH FIRST` cut is deterministic.

### 1.5 Columns — `SYSCAT.COLUMNS`

```sql
SELECT tabschema, tabname,
       colname  AS name,
       colno    AS ordinal,
       typename AS data_type,           -- e.g. INTEGER, VARCHAR, DECIMAL, TIMESTAMP
       length   AS length,
       scale    AS scale,
       CASE nulls WHEN 'Y' THEN 1 ELSE 0 END AS nullable,   -- NULLS 'Y'/'N' -> bool
       default  AS default               -- DEFAULT clause text (may be NULL)
FROM   SYSCAT.COLUMNS
WHERE  tabschema NOT LIKE 'SYS%'
  AND  tabschema NOT IN ('SYSTOOLS','SYSPUBLIC','NULLID','SQLJ')
  AND  (tabschema, tabname) IN ( /* the in-scope tables from §1.4 */ )
ORDER BY tabschema, tabname, colno;
```

Mapping to the postgres per-column shape (`code-postgres-dbm-metadata-schemas.md` §2.1, "Columns"):
- `name` ← `COLNAME`
- `data_type` ← `TYPENAME` enriched with `LENGTH`/`SCALE` to render e.g. `VARCHAR(64)` /
  `DECIMAL(10,2)` (Db2 has no `format_type()`; build the string in Python — see `_render_data_type`
  sketch in §1.7).
- `nullable` ← `NULLS = 'Y'` (bool)
- `default` ← `DEFAULT` (expression text; drop the key if `None`, matching postgres' None-stripping,
  `code-postgres-dbm-metadata-schemas.md` §2.4).

`max_columns` truncation is applied per-table in Python (§4.3), exactly as postgres does it in `_map_row`
(`code-postgres-dbm-metadata-schemas.md` §2.4), **not** in SQL.

### 1.6 Indexes (+ key columns) and constraints/FKs

**Indexes** — `SYSCAT.INDEXES` joined to `SYSCAT.INDEXCOLUSE` for the ordered column list (Db2 has no
`pg_get_indexdef`; assemble structured fields + a synthesized `definition` string):

```sql
SELECT i.indschema, i.indname AS name,
       i.tabschema, i.tabname,
       i.uniquerule,                    -- 'P' primary, 'U' unique, 'D' duplicates-allowed (non-unique)
       CASE WHEN i.uniquerule IN ('U','P') THEN 1 ELSE 0 END AS is_unique,
       CASE WHEN i.uniquerule = 'P'       THEN 1 ELSE 0 END AS is_primary,
       i.indextype,                     -- 'REG','CLUS','BLOK','DIM','XPTH','XRGN','XVIL', etc.
       i.colcount
FROM   SYSCAT.INDEXES i
WHERE  i.tabschema NOT LIKE 'SYS%'
  AND  i.tabschema NOT IN ('SYSTOOLS','SYSPUBLIC','NULLID','SQLJ')
  AND  (i.tabschema, i.tabname) IN ( /* in-scope tables */ )
ORDER BY i.indschema, i.indname;

-- Ordered key columns per index (join in Python by (indschema, indname)):
SELECT indschema, indname, colname, colseq,
       colorder                         -- 'A' asc, 'D' desc, 'I' include
FROM   SYSCAT.INDEXCOLUSE
ORDER BY indschema, indname, colseq;
```

`SYSCAT.INDEXES` columns **(verify)**: `INDSCHEMA`, `INDNAME`, `TABSCHEMA`, `TABNAME`, `UNIQUERULE`,
`INDEXTYPE`, `COLCOUNT`, `COLNAMES` (a `+col-col` encoded string — usable but prefer the structured
`INDEXCOLUSE` join), `MADE_UNIQUE`, `SYSTEM_REQUIRED`, `CREATE_TIME`. Per-index payload fields (analog of
postgres `code-postgres-dbm-metadata-schemas.md` §2.1, "Indexes"):
- `name` ← `INDNAME`
- `is_unique` ← `UNIQUERULE IN ('U','P')`
- `is_primary` ← `UNIQUERULE = 'P'`
- `index_type` ← `INDEXTYPE`
- `columns` ← ordered `COLNAME` list from `INDEXCOLUSE` (with `colorder` to mark `INCLUDE` cols)
- `definition` ← synthesize, e.g. `CREATE [UNIQUE] INDEX "indschema"."indname" ON "tabschema"."tabname" (col1 ASC, col2 DESC) [INCLUDE (col3)]` — gives the UI a postgres-like `definition` string while also shipping structured fields.

**Primary key / unique constraints** — `SYSCAT.TABCONST` (+ `SYSCAT.KEYCOLUSE` for columns). Useful to
emit alongside indexes or as a separate `constraints` list:

```sql
SELECT c.constname AS name,
       c.tabschema, c.tabname,
       c.type            -- 'P' primary key, 'U' unique, 'F' foreign key, 'K' check, 'I' info, ...
FROM   SYSCAT.TABCONST c
WHERE  c.tabschema NOT LIKE 'SYS%'
  AND  c.type IN ('P','U')
  AND  (c.tabschema, c.tabname) IN ( /* in-scope tables */ )
ORDER BY c.tabschema, c.tabname, c.constname;

SELECT constname, tabschema, tabname, colname, colseq
FROM   SYSCAT.KEYCOLUSE
ORDER BY constname, colseq;            -- ordered constraint columns; join in Python
```

**Foreign keys** — `SYSCAT.REFERENCES` (the dedicated FK catalog; richer than filtering `TABCONST` type
`'F'` because it carries the referenced table + the FK/PK column lists + rules):

```sql
SELECT r.constname              AS name,
       r.tabschema, r.tabname,
       r.reftabschema           AS referenced_table_schema,
       r.reftabname             AS referenced_table_name,
       r.refkeyname             AS referenced_key_name,
       r.fk_colnames            AS fk_column_names,    -- space/+ -delimited col list (verify delimiter)
       r.pk_colnames            AS pk_column_names,
       r.deleterule, r.updaterule              -- 'A' no action, 'C' cascade, 'N' set null, 'R' restrict
FROM   SYSCAT.REFERENCES r
WHERE  r.tabschema NOT LIKE 'SYS%'
  AND  r.tabschema NOT IN ('SYSTOOLS','SYSPUBLIC','NULLID','SQLJ')
  AND  (r.tabschema, r.tabname) IN ( /* in-scope tables */ )
ORDER BY r.tabschema, r.tabname, r.constname;
```

`SYSCAT.REFERENCES` columns **(verify)**: `CONSTNAME`, `TABSCHEMA`, `TABNAME`, `REFKEYNAME`,
`REFTABSCHEMA`, `REFTABNAME`, `FK_COLNAMES`, `PK_COLNAMES`, `COLCOUNT`, `DELETERULE`, `UPDATERULE`,
`CREATE_TIME`. The `FK_COLNAMES`/`PK_COLNAMES` columns are Db2's packed column-name encoding; for robust
ordering prefer joining `SYSCAT.KEYCOLUSE` by `constname` (same approach as indexes). Per-FK payload
fields go under the **`foreign_keys`** key (the exact key postgres uses,
`code-postgres-dbm-metadata-schemas.md` §2.1):
- `name` ← `CONSTNAME`
- `referenced_table` ← `REFTABSCHEMA.REFTABNAME`
- `column_names` / `referenced_column_names` ← ordered lists
- `definition` ← synthesize `FOREIGN KEY (...) REFERENCES "reftab" (...) ON DELETE <rule> ON UPDATE <rule>`.

### 1.7 Python assembly — `_get_next` / `_map_row` (the JSON build Db2 must do itself)

Because there is no `row_to_json`, the collector loads the per-object catalog queries above into Python
dicts keyed by `(schema, table)` once per collection, then `_get_next` yields one assembled table at a
time. Sketch:

```python
class Db2SchemaCollector(SchemaCollector):
    @property
    def kind(self) -> str:
        return "db2_databases"               # the discriminator on the dbm-metadata track

    def _get_databases(self):
        return [{"name": self._check._config.db, "id": self._check._config.db}]

    def _get_cursor(self, database):
        # Reuse the check's persistent ibm_db connection; set a statement timeout for safety (§4.4).
        # ibm_db has no DB-API cursor; we wrap iter_rows(...) into a generator-backed pseudo-cursor.
        return _Db2SchemaCursor(self._check, self._config, database)

    def _get_next(self, cursor):
        # Returns the next fully-assembled (schema_name, table_name, table_obj) tuple, or None when done.
        return cursor.next_table()

    def _map_row(self, database, row):
        schema_name, table_obj = row
        # One mapped object per table; the queue is later regrouped into schemas at flush time.
        # To preserve the postgres database->schemas->tables nesting, we attach a single-schema/single-table
        # DatabaseObject per row; the backend merges by (database, schema) keys.
        return {
            **database,                       # name, id, owner...
            "schemas": [{
                "name": schema_name,
                "owner": table_obj.pop("_schema_owner", None),
                "tables": [table_obj],        # columns/indexes/foreign_keys already attached
            }],
        }
```

`_Db2SchemaCursor` runs the five `SYSCAT` queries via the existing `iter_rows(...)` generator
(`ibm_db2.py:610-631`, which uses `ibm_db.fetch_assoc` and returns **lowercase** keys because the check
sets `ibm_db.ATTR_CASE = ibm_db.CASE_LOWER`, `ibm_db2.py:567` — see `db2-config-settings.md` §8.4),
buckets columns/indexes/FKs by `(tabschema, tabname)` in dicts, applies `max_columns` truncation per
table, builds the `data_type` strings and `definition` strings, and yields tables in `(schema, table)`
order. Helper:

```python
def _render_data_type(typename, length, scale):
    t = typename.upper()
    if t in ("DECIMAL", "NUMERIC"):
        return f"{t}({length},{scale})"
    if t in ("VARCHAR", "CHARACTER", "CHAR", "VARGRAPHIC", "GRAPHIC"):
        return f"{t}({length})"
    return t                                  # INTEGER, BIGINT, DATE, TIMESTAMP, etc.
```

The resulting per-table object matches the postgres table shape (modulo Db2-specific extras and dropping
`toast_table`):

```python
{
    "name": table_name,
    "id": f"{schema_name}.{table_name}",      # no numeric oid in Db2; use qualified name
    "owner": table_owner,
    "columns":      [ {name, data_type, nullable, default(opt), ordinal(opt)}, ... ][:max_columns],
    "indexes":      [ {name, is_unique, is_primary, index_type, columns, definition}, ... ],
    "foreign_keys": [ {name, definition, referenced_table, column_names, ...}, ... ],
    # optional Db2 extras: "table_type" (T/S), "estimated_rows" (CARD), "stats_time"
}
```

**Dedup + None-stripping** mirror postgres (`code-postgres-dbm-metadata-schemas.md` §2.4): dedup
columns/indexes/FKs by `name`; drop dict keys whose value is `None`.

### 1.8 Empty-DB / no-rows behavior

If a schema has no tables (all filtered or genuinely empty), it still appears with `tables: []` (postgres
behavior). If the whole DB has zero in-scope tables, `_get_next` returns `None` immediately and the base
flushes a single payload with empty `metadata` and `collection_payloads_count: 1` — harmless.

---

## 2. SETTINGS collection — `kind:"db2_settings"` (+ optional `db2_registry_variables`)

This is the Db2 analog of postgres `_collect_postgres_settings` / `report_postgres_metadata`
(`code-postgres-dbm-metadata-schemas.md` §1.1) and mysql `report_mysql_metadata`
(`code-mysql-dbm.md` §4.2). Full SQL + caveats live in
[`_research/db2-config-settings.md`](_research/db2-config-settings.md); summarized and made
implementation-ready here.

### 2.1 The four config layers, and which we ship

Db2 config is layered (`db2-config-settings.md` §0). For the settings payload we union the two that map
cleanly to a flat `name/value` settings list, and ship the registry layer as an optional separate event:

| Layer | View | Rows (12.1.4 `[LIVE]`) | Where it goes |
|---|---|---|---|
| DBM CFG (instance) | `SYSIBMADM.DBMCFG` | 113 | `db2_settings` (tagged `config_scope:dbm`) |
| DB CFG (database) | `SYSIBMADM.DBCFG` | 194 | `db2_settings` (tagged `config_scope:db`) |
| Registry / env | `SYSIBMADM.REG_VARIABLES` | 3 | optional `db2_registry_variables` event |
| Env / build / edition | `SYSIBMADM.ENV_*` | — | folded into `database_instance` (§3), not here |

All four are **SQL views requiring a connection** — the check already holds one
(`ibm_db2.py:554-578`), so this collector reuses it.

### 2.2 The one-round-trip settings query (UNION, source-tagged)

From `db2-config-settings.md` §8.2 — DBMCFG ∪ DBCFG, source-tagged via a literal `config_scope` column,
single member to avoid DPF/pureScale row multiplication:

```sql
SELECT 'dbm' AS config_scope, name, value, value_flags,
       deferred_value, deferred_value_flags, datatype,
       CAST(NULL AS SMALLINT) AS member
FROM   SYSIBMADM.DBMCFG
UNION ALL
SELECT 'db'  AS config_scope, name, value, value_flags,
       deferred_value, deferred_value_flags, datatype,
       member
FROM   SYSIBMADM.DBCFG
WHERE  member = 0           -- collapse multi-member topologies; drop to capture all members
ORDER BY config_scope, name;
```

> **DPF/pureScale (`db2-config-settings.md` §2.1, §7):** `DBCFG` and `REG_VARIABLES` carry
> `DBPARTITIONNUM`/`MEMBER`; a multi-member instance returns one row per parameter per member, so a naive
> select multiplies rows. `member = 0` collapses it (single-node has `member=0` already). The metrics
> path passes `-1` to `MON_GET_*` to aggregate across members
> ([`04-metrics-fidelity-plan.md`](04-metrics-fidelity-plan.md)); for settings we instead pin member 0.

### 2.3 Per-row settings shape

From `db2-config-settings.md` §8.2 — the normalized row keys (note the **`pending_change`** derived field,
Db2's analog of postgres `pending_restart`, computed as `value != deferred_value`,
`db2-config-settings.md` §2.4):

```python
{
  "name":                 row["name"],                       # e.g. "diaglevel", "sortheap"
  "value":                row["value"],                      # current in-memory value (str)
  "value_flags":          row["value_flags"],                # "NONE" | "AUTOMATIC"
  "deferred_value":       row["deferred_value"],             # on-disk value (next activation/restart)
  "deferred_value_flags": row["deferred_value_flags"],
  "datatype":             row["datatype"],                   # "INTEGER" | "BIGINT" | "VARCHAR(n)" | ...
  "config_scope":         row["config_scope"],               # "dbm" | "db"
  "pending_change":       row["value"] != row["deferred_value"],
  # include "member" only when collecting all members
}
```

`value_flags == "AUTOMATIC"` means the parameter is STMM/autonomic self-tuning; the numeric `value` is the
current computed value and the flag is the load-bearing signal (`db2-config-settings.md` §2.3) — keep both.

The monitoring switches surfaced here are operationally important: this payload is where an operator (and
the DBM preflight in [`05-dbm-query-metrics.md`](05-dbm-query-metrics.md)) can verify
`mon_act_metrics`/`mon_obj_metrics`/`mon_req_metrics`/`mon_uow_data` (live values `BASE`/`EXTENDED`/
`BASE`/`NONE`, `_research/_raw/04-monitor-config.txt:9-22`). These are DB CFG params and ride along in the
`config_scope:db` rows automatically — no special handling.

### 2.4 Settings payload envelope (`kind:"db2_settings"`)

Per `db2-config-settings.md` §8.1 and the contract (`code-dbm-payload-contract.md` §6.2 — same envelope
postgres uses for `pg_settings`):

```python
event = {
    "host":                self._check.reported_hostname,
    "database_instance":   self._check.database_identifier,
    "agent_version":       datadog_agent.get_version(),
    "dbms":                "db2",
    "kind":                "db2_settings",
    "collection_interval": self._settings_collection_interval,   # 600s default
    "dbms_version":        self._check.dbms_version,             # "12.1.4.0" (§3)
    "tags":                self._tags_no_db,                     # dd.internal stripped, db: stripped
    "timestamp":           time.time() * 1000,                   # epoch ms
    "cloud_metadata":      self._check.cloud_metadata,
    "metadata":            settings_rows,                        # list[dict] from §2.3
}
self._check.database_monitoring_metadata(
    json.dumps(event, default=default_json_event_encoding))
```

### 2.5 Optional registry-variables event (`kind:"db2_registry_variables"`)

`SYSIBMADM.REG_VARIABLES` is the closest analog to postgres extension GUCs / the "third config layer"
(`db2-config-settings.md` §3). It shares the settings interval and the same envelope (just a different
`kind` and `metadata`). Query (`db2-config-settings.md` §3.2):

```sql
SELECT reg_var_name, reg_var_value, level, is_aggregate, aggregate_name, dbpartitionnum
FROM   SYSIBMADM.REG_VARIABLES
ORDER BY reg_var_name;
```

> **Startup-skew caveat (must document in the payload, `db2-config-settings.md` §3.4):**
> `REG_VARIABLES` reflects the registry **as of the last instance start**, not live `db2set`. It can
> disagree with `db2set -all` (live `[LIVE]`: view shows 3 rows including an env-level `DB2_FED_LIBPATH`
> that `db2set -all` omits). Stamp a note (or a `reg_vars_as_of: "instance_start"` marker) so the UI
> doesn't present it as live. Logged in `12-risks-open-questions.md`.

`level` decodes to the profile-registry source: `E`=environment, `N`=instance-node, `I`=instance,
`G`=global (`db2-config-settings.md` §3.3).

---

## 3. Version / edition / instance metadata → the `database_instance` payload

The `database_instance` event (`kind:"database_instance"`, `metadata.dbm=true`) is the **single must-have
payload** — without it the host never appears in the DBM UI (`code-dbm-payload-contract.md` §6.1). It is
emitted by the **check object**, debounced per `database_identifier`
(see [`03-reference-architecture.md`](03-reference-architecture.md)), **not** by the metadata job — but
its version/edition fields are derived from the same `SYSIBMADM.ENV_*` views, so the queries belong here.

### 3.1 Version — `SYSIBMADM.ENV_INST_INFO` (primary)

```sql
SELECT service_level,   -- "DB2 v12.1.4.0"  <- canonical human version string
       bld_level,       -- "s2602211313"
       fixpack_num,     -- 0
       release_num,     -- "02050110"
       num_members      -- 1
FROM SYSIBMADM.ENV_INST_INFO;
```

Parse the `VV.RR.MM.FF` four-part token from `SERVICE_LEVEL` (`DB2 v12.1.4.0` → `db2_version="12.1.4.0"`)
to feed `dbms_version` everywhere it appears (`db2-config-settings.md` §6.1). A `payload_db2_version()`
helper (analog of postgres `payload_pg_version`, `code-dbm-payload-contract.md` §8) returns `"12.1.4.0"`.

Fallbacks (`db2-config-settings.md` §6): the table-function form
`TABLE(SYSPROC.ENV_GET_INST_INFO())`; the packed integer `SYSIBM.SYSVERSIONS.versionnumber` (`12010400`,
ideal for `>=`/`<` feature gating across 11.5 vs 12.1); `MON_GET_INSTANCE(-1)` (`PRODUCT_NAME`/
`SERVICE_LEVEL`/`SERVER_PLATFORM`, already partly used by the check, `queries.py:15-17`); and the
driver-level `ibm_db.get_db_info(conn, ibm_db.SQL_DBMS_VER)` (`utils.py:27-28`). The existing check
already parses a version in `parse_version`/`get_version` (`ibm_db2.py:109-125`) — reuse/extend it.

### 3.2 Edition — `SYSIBMADM.ENV_PROD_INFO`

```sql
SELECT installed_prod, prod_release, license_type
FROM   SYSIBMADM.ENV_PROD_INFO
WHERE  license_installed = 'Y';     -- the active edition (live: DEC / 12.1 / COMMUNITY)
```

Don't enumerate product codes; filter by `LICENSE_INSTALLED='Y'` (`db2-config-settings.md` §4.2, §6.4 —
the code list expands across versions, incl. AI editions in 12.1).

### 3.3 Host facts — `SYSIBMADM.ENV_SYS_INFO` (optional)

`OS_NAME/VERSION/RELEASE`, `HOST_NAME`, `TOTAL_CPUS`, `CONFIGURED_CPUS`, `TOTAL_MEMORY` (MB), and the
12.1-only `OS_FULL_VERSION`/`OS_KERNEL_VERSION`/`OS_ARCH_TYPE` (select defensively — may be absent on
older builds, `db2-config-settings.md` §4.3, §7). These are best folded into the `database_instance`
event's metadata or shipped as an optional `kind:"db2_env_info"` only if richer host facts are wanted
(`db2-config-settings.md` §8.3).

### 3.4 The `database_instance` event (for completeness; lives in the check, per §03)

```python
event = {
    "host":                self.reported_hostname,
    "port":                self._config.port,
    "database_instance":   self.database_identifier,
    "database_hostname":   self.database_hostname,
    "agent_version":       datadog_agent.get_version(),     # NB: "agent_version", not ddagentversion
    "ddagenthostname":     self.agent_hostname,
    "dbms":                "db2",
    "kind":                "database_instance",
    "collection_interval": self._config.database_instance_collection_interval,   # default 300s
    "dbms_version":        self.dbms_version,                # "12.1.4.0" (§3.1)
    "integration_version": __version__,
    "tags":                [t for t in self._non_internal_tags if not t.startswith('db:')],
    "timestamp":           time.time() * 1000,
    "cloud_metadata":      self.cloud_metadata,
    "metadata": {
        "dbm":             self._config.dbm,                 # MUST be true to register as a DBM instance
        "connection_host": self._config.host,
        # optional: "edition": "DEC", "license_type": "COMMUNITY" (§3.2)
    },
}
```

(Source-of-truth envelope: `code-dbm-payload-contract.md` §6.1.)

---

## 4. Cardinality controls + collection interval

### 4.1 Drop the `*_databases` filters

Postgres exposes `include_databases`/`exclude_databases` (`code-postgres-dbm-metadata-schemas.md` §7.2).
Db2 is single-DB-per-connection (§1.2), so these are **dropped** unless multi-DB autodiscovery is added
later (`code-postgres-dbm-metadata-schemas.md` §9.4). Keep `include_schemas`/`exclude_schemas` and
`include_tables`/`exclude_tables`.

### 4.2 Schema/table include & exclude filters

Postgres uses POSIX regex (`~`/`!~`) for schema/table filters but **LIKE** for settings ignore-patterns
(`code-postgres-dbm-metadata-schemas.md` §7.2, §9.4). **Db2 has no POSIX `~` operator.** Two options:
- **`LIKE`** (always available, simplest) — push `schemaname LIKE/NOT LIKE` predicates into the catalog
  query. Recommended default for Db2.
- **`REGEXP_LIKE(...)`** (Db2 11.1+; built-in regex) — for parity with postgres' regex semantics, gate on
  version (`versionnumber >= 11010000`) and fall back to LIKE otherwise **(verify availability on the
  target floor)**.

Recommend documenting Db2 filters as **LIKE patterns** to avoid the regex-dialect mismatch, while noting
`REGEXP_LIKE` as an opt-in. (This is the inverse of the settings `ignored_settings_patterns`, which is
*already* LIKE in postgres — so Db2 is internally consistent if both use LIKE.)

### 4.3 `max_tables` / `max_columns`

- **`max_tables`** — enforced in SQL via `FETCH FIRST {max_tables} ROWS ONLY` on the `SYSCAT.TABLES`
  query (§1.4), applied **before** assembling per-table columns/indexes so it bounds the work (mirrors
  postgres applying `LIMIT` in the `schema_tables` CTE, `code-postgres-dbm-metadata-schemas.md` §2.2,
  §2.5). Default **300** (postgres `collect_schemas.max_tables` default).
- **`max_columns`** — enforced in Python per table during assembly (§1.7), exactly as postgres does it in
  `_map_row` (`code-postgres-dbm-metadata-schemas.md` §2.4). Default **50** (postgres default).
- **`payload_chunk_size`** — inherited from base `SchemaCollectorConfig` (10_000); no override needed.

### 4.4 `max_query_duration` → a Db2 statement timeout

Postgres wraps the schema query in `SET LOCAL statement_timeout = '{max_query_duration}s'`
(`code-postgres-dbm-metadata-schemas.md` §2.3). Db2 has no exact `SET LOCAL statement_timeout`. Options
(`code-postgres-dbm-metadata-schemas.md` §9.4) **(verify on 12.1.4)**:
- `SET CURRENT QUERY OPTIMIZATION` is **unrelated** — do not use.
- Connection-level `QueryTimeout` driver attribute, or a client-side cursor timeout on the `ibm_db`
  connection, is the pragmatic choice.
- `WLM_SET_CONN_ENV` / a WLM threshold can cap activity time but is heavier-weight.

Default **60 s** (postgres default). Whatever mechanism, scope it so it reverts after the collection.

### 4.5 Collection interval (default ~600 s)

All three sub-collections default to **600 s** (postgres `collect_settings`/`collect_schemas`
`collection_interval=600`, `code-postgres-dbm-metadata-schemas.md` §7.1-§7.2; mysql settings default 600,
`code-mysql-dbm.md` §5.10). The owning `Db2Metadata` job ticks at the **min (or GCD)** of the enabled
sub-intervals and each sub-collection self-throttles by comparing `now` against its own last-run time and
its own interval (postgres GCD approach, `code-postgres-dbm-metadata-schemas.md` §1; mysql min approach,
`code-mysql-dbm.md` §4.1). Use **min** for simplicity (mysql style) since Db2 has only two distinct
intervals (settings, schemas).

The `database_instance` event re-emits on its own `database_instance_collection_interval` (default
**300 s**, `code-dbm-payload-contract.md` §10), debounced by the backend.

---

## 5. Payload shapes, scheduling, conf knobs

### 5.1 The `Db2Metadata(DBMAsyncJob)` job

One async job owns settings + registry + schemas, mirroring `MySQLMetadata`/`PostgresMetadata`
(`code-mysql-dbm.md` §4.1, `code-postgres-dbm-metadata-schemas.md` §1). It subclasses `DBMAsyncJob`
(`datadog_checks_base/.../utils/db/utils.py:289+`, `code-dbm-payload-contract.md` §9):

```python
class Db2Metadata(DBMAsyncJob):
    def __init__(self, check, config):
        self._collect_settings_enabled = config.collect_settings.enabled        # default True
        self._collect_schemas_enabled  = config.collect_schemas.enabled         # default False
        self._settings_collection_interval = config.collect_settings.collection_interval  # 600
        self._schemas_collection_interval  = config.collect_schemas.collection_interval   # 600
        self._schema_collector = Db2SchemaCollector(check, _Db2SchemaCollectorConfig(config))
        collection_interval = min(
            i for i, on in [
                (self._settings_collection_interval, self._collect_settings_enabled),
                (self._schemas_collection_interval,  self._collect_schemas_enabled),
            ] if on
        )
        super().__init__(
            check,
            run_sync=config.collect_settings.run_sync,                          # default False
            enabled=self._collect_settings_enabled or self._collect_schemas_enabled,
            min_collection_interval=collection_interval,
            dbms="db2",
            rate_limit=1 / collection_interval,
            job_name="database-metadata",
            expected_db_exceptions=(Exception,),    # narrow to ibm_db's error type (verify)
            shutdown_callback=self._close_db_conn,
        )

    def run_job(self):
        self.tags = [t for t in self._tags if not t.startswith('dd.internal')]
        self._tags_no_db = [t for t in self.tags if not t.startswith('db:')]
        now = time.time()
        if self._collect_settings_enabled and (now - self._last_settings_ts) >= self._settings_collection_interval:
            self._collect_settings()           # §2.4 + optional §2.5
            self._last_settings_ts = now
        if self._collect_schemas_enabled and (now - self._last_schemas_ts) >= self._schemas_collection_interval:
            self._schema_collector.collect_schemas()   # base engine; §1
            self._last_schemas_ts = now
```

Wired from the check's `check()` method only when `dbm_enabled` (mysql `mysql.py:425-428`,
`code-mysql-dbm.md` §0), alongside the metrics/samples/activity jobs from
[`05`](05-dbm-query-metrics.md)/[`06`](06-dbm-query-samples-activity.md)/[`07`](07-dbm-execution-plans.md).
The check holds one **dedicated `ibm_db` connection per async job**, closed on shutdown via
`shutdown_callback` (mysql pattern, `code-mysql-dbm.md` §6.4; the metadata job runs infrequently so it
should `ping`/reconnect on each run since idle connections can drop, `code-mysql-dbm.md` §4.1). The exact
wiring belongs in `09-implementation-architecture.md`.

### 5.2 Submission + serialization

All payloads go via `self._check.database_monitoring_metadata(json.dumps(event, default=default_json_event_encoding))`
→ track **`dbm-metadata`** (`code-dbm-payload-contract.md` §0). The encoder coerces Decimal→float,
date/datetime→ISO-8601, etc. (`code-dbm-payload-contract.md` §0). The schema collector calls this inside
the base `maybe_flush`; settings/registry call it directly.

### 5.3 `kind` / `metadata` quick reference (Db2)

| Sub-collection | `kind` | rows key | extra keys |
|---|---|---|---|
| Settings | `db2_settings` | `metadata` (list) | — |
| Registry | `db2_registry_variables` | `metadata` (list) | reg-vars-as-of note |
| Schemas | `db2_databases` | `metadata` (list of DatabaseObjects) | `collection_started_at` (ms); `collection_payloads_count` on final chunk |

`ddtags`/`tags` discipline (`code-dbm-payload-contract.md` §2.6, §8): strip `dd.internal.*` from all DBM
payloads; settings/registry use `_tags_no_db` (also strip `db:`); the base schema collector uses full
`check.tags`. All `timestamp`s are epoch **milliseconds**.

### 5.4 Conf knobs (mirror postgres `collect_settings`/`collect_schemas`)

Add to `ibm_db2` `spec.yaml` / generated `config_models/instance.py`
(`code-postgres-dbm-metadata-schemas.md` §7; `code-mysql-dbm.md` §5.9-§5.10):

```yaml
# Master switch (already needed for all DBM; see 03/05).
dbm: false

collect_settings:
  enabled: true                  # gate
  collection_interval: 600       # seconds
  run_sync: false                # testing only (hidden)
  ignored_settings_patterns: []  # Db2 LIKE patterns; NOT LIKE pushed into the UNION query
  # consider redacting topology-leaking params, e.g. ['%keystore%','%group%'] (db2-config-settings.md §9)

collect_schemas:
  enabled: false                 # off by default (mysql parity)
  collection_interval: 600       # seconds
  max_tables: 300
  max_columns: 50
  max_query_duration: 60         # seconds; mapped to a Db2 query timeout (§4.4)
  include_schemas: []            # LIKE patterns (§4.2); regex via REGEXP_LIKE opt-in
  exclude_schemas: []
  include_tables: []
  exclude_tables: []
  # NOTE: no *_databases filters — single DB per Db2 connection (§4.1)

database_instance_collection_interval: 300   # re-emit cadence for the database_instance event
```

The generated `CollectSettings`/`CollectSchemas` pydantic models follow the postgres field set minus the
`*_databases` tuples (`code-postgres-dbm-metadata-schemas.md` §7.4).

`ignored_settings_patterns` is applied as `NOT LIKE` against `name` in the §2.2 UNION query, e.g.:

```sql
... FROM SYSIBMADM.DBMCFG WHERE name NOT LIKE '%keystore%' AND name NOT LIKE '%group%'
```

### 5.5 Telemetry (free from the base + analogs)

The base `SchemaCollector` already emits `dd.ibm_db2.schema.{time,tables_count,payloads_count}` tagged
`status:success|error` (base `schemas.py:110-132`, `code-postgres-dbm-metadata-schemas.md` §3.4). The
settings sub-collection should emit an analogous `dd.ibm_db2.settings.time` / `.rows` gauge for
self-monitoring (optional; mirrors mysql/postgres debug metrics).

---

## 6. Privileges

From `db2-config-settings.md` §5 and the existing setup guidance (`ibm_db2/README.md:58-106`):

**Settings + env views** (`SYSIBMADM.DBMCFG`/`DBCFG`/`REG_VARIABLES`/`ENV_*`) require a connection plus
**one of** these data-access authorities (any one suffices), plus implicit `SELECT` on the view (granted
to PUBLIC by default in a non-restrictive DB):

- **`SYSMON`** — the least-privileged, monitoring-intended authority; **the right one to recommend for a
  read-only DBM user**. Covers all the config/env routines.
- or `DBADM` / `SQLADM` / `SYSADM` / `SYSCTRL` / `SYSMAINT`.
- or `EXECUTE` on the backing routines: `SYSPROC.DBM_GET_CFG`, `SYSPROC.DB_GET_CFG`,
  `SYSPROC.REG_LIST_VARIABLES`, `SYSPROC.ENV_GET_INST_INFO`, `SYSPROC.ENV_GET_SYS_INFO`,
  `SYSPROC.ENV_GET_PROD_INFO`, `SYSPROC.ENV_GET_FEATURE_INFO`.

**Schema views** (`SYSCAT.*`) — the `SYSCAT` catalog views are granted **`SELECT` to PUBLIC by default**,
so a normal connected user can read schema metadata without extra grants (on a non-restrictive DB). For a
restrictive DB, grant `SELECT` on the specific `SYSCAT` views or `DATAACCESS`/`DBADM`.

**Recommendation for the DBM user:** `SYSMON` + the default PUBLIC `SELECT` on `SYSCAT`/`SYSIBMADM`
covers settings, env/version, and schemas. This extends the existing README grant guidance (which today
covers only the five `MON_GET` table functions or `DATAACCESS`/`DBADM`/`SQLADM`, `README.md:58-106`); P4
should add the `SYSMON` recommendation and the config/env routine EXECUTE grants. On the live community
container the check connects as `db2inst1` (instance owner, full authority), so everything succeeds there
without extra grants (`db2-config-settings.md` §5) — but CI/test must validate the least-privilege path.
Privilege-rollout risk is logged in `12-risks-open-questions.md`.

---

## 7. Db2 12.1 vs 11.5 stability notes

- **View shapes are stable 11.5 → 12.1** for `DBMCFG`/`DBCFG`/`REG_VARIABLES` (6/8/6 cols verified live
  on 12.1.4, `db2-config-settings.md` §7). What changes is the **set of parameter rows**, not the
  columns — the settings collector must be **schema-agnostic over rows** (select all rows; never hard-code
  a parameter list).
- `ENV_SYS_INFO` gained `OS_FULL_VERSION`/`OS_KERNEL_VERSION`/`OS_ARCH_TYPE` in 12.1 — select defensively.
- `SYSCAT.*` catalog columns are broadly stable but the exact lists in §1.3-§1.6 are marked **(verify)**
  and must be live-`DESCRIBE`'d on 12.1.4 during P4 (same discipline as the metrics `[DOC]→[LIVE]`
  promotion in [`04-metrics-fidelity-plan.md`](04-metrics-fidelity-plan.md) and
  [`00-README.md`](00-README.md) "Key risks" #1).
- Feature-gate via the packed integer `SYSIBM.SYSVERSIONS.versionnumber` (`12010400`) rather than string
  parsing where you need `>=`/`<` comparisons (e.g. `REGEXP_LIKE` availability, §4.2).

---

## 8. Implementation checklist (P4)

1. `Db2SchemaCollector(SchemaCollector)` — implement `kind`/`_get_databases`/`_get_cursor`/`_get_next`/
   `_map_row`; assemble nested payload in Python (§1.7); reuse `iter_rows` + lowercase keys.
2. `Db2Metadata(DBMAsyncJob)` — owns settings (§2) + registry (§2.5) + schemas (§1); min-interval ticking,
   per-sub self-throttle (§5.1).
3. `database_instance` event in the check object with `metadata.dbm=true` + parsed `dbms_version`/edition
   from `ENV_INST_INFO`/`ENV_PROD_INFO` (§3) — **the must-have payload**.
4. `payload_db2_version()` helper → `"12.1.4.0"` (§3.1).
5. Conf surface: `dbm`, `collect_settings`, `collect_schemas`, `database_instance_collection_interval`
   (§5.4) + generated models.
6. README: `SYSMON` recommendation + config/env routine EXECUTE grants (§6).
7. CI: live-`DESCRIBE` every **(verify)** `SYSCAT` column on 12.1.4; promote to `[LIVE]`. Validate the
   least-privilege (`SYSMON`) path, not just the instance-owner path.
8. Tests: assert payload `kind`/envelope shape (`dbms:"db2"`, ms `timestamp`, stripped tags), the
   `database → schemas → tables → {columns,indexes,foreign_keys}` nesting, `max_tables`/`max_columns`
   caps, system-schema filtering, and `pending_change` derivation. See
   [`11-testing-and-validation.md`](11-testing-and-validation.md).
