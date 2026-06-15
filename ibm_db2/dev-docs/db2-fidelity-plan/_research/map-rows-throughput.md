# Map: Rows / Throughput metric category (Db2 ⇄ Postgres/MySQL)

Scope of this category: **row activity** (read / returned / modified / inserted / updated /
deleted), **transaction throughput** (commits / rollbacks), and **activity/request throughput**
(activities completed/aborted/rejected, requests completed, SQL-statement-mix counters) sourced
from `MON_GET_DATABASE` / `MON_GET_CONNECTION` / `MON_GET_WORKLOAD` / `MON_GET_SERVICE_SUBCLASS`
(plus their `SYSIBMADM` summary-view equivalents).

Target Db2: **12.1** (live container **DB2/LINUXX8664 12.1.4.0**, confirmed in
`_research/_raw/01-version-and-monget-functions.txt:4,9`).

Code citations are absolute paths into `/home/bits/dd/integrations-core`. Db2 column claims cite the
live `DESCRIBE` dump `_research/_raw/02-monget-key-columns.txt` (column name + exact line) wherever
the dump supports them; anything not in the dump is marked **(general Db2 12.1 knowledge — verify)**.

---

## 0. TL;DR for the implementer

1. **This is the single highest-leverage, lowest-cost category to add.** Every commit/rollback/
   rows-inserted/updated/deleted/activities counter is already returned by `MON_GET_DATABASE(-1)` —
   the function the existing check **already calls** (`ibm_db2/datadog_checks/ibm_db2/queries.py:40`).
   Closing the gap is mostly *adding columns to one existing SELECT* and submitting them. No new
   round-trips, no new authority, no version gating for the core set.
2. **What exists today** (only 3 row metrics, no txn-throughput at all): `ibm_db2.row.reads.total`,
   `ibm_db2.row.returned.total`, `ibm_db2.row.modified.total`
   (`ibm_db2/datadog_checks/ibm_db2/ibm_db2.py:184-190`; metadata `ibm_db2/metadata.csv:44-46`).
   There is **no** `commits`, **no** `rollbacks`, **no** rows insert/update/delete split, **no**
   activity/request throughput. Postgres and MySQL both expose all of these as first-class core metrics.
3. **All confirmed present on the live 12.1.4 server** in `MON_GET_DATABASE` (515 cols):
   `TOTAL_APP_COMMITS`(L130), `INT_COMMITS`(L131), `TOTAL_APP_ROLLBACKS`(L134), `INT_ROLLBACKS`(L135),
   `ROWS_READ`(L90), `ROWS_RETURNED`(L91), `ROWS_MODIFIED`(L89), `ROWS_INSERTED`(L352),
   `ROWS_UPDATED`(L353), `ROWS_DELETED`(L351), `INT_ROWS_INSERTED`(L372), `INT_ROWS_UPDATED`(L373),
   `INT_ROWS_DELETED`(L371), `ACT_COMPLETED_TOTAL`(L39), `ACT_ABORTED_TOTAL`(L38),
   `ACT_REJECTED_TOTAL`(L40), `APP_ACT_COMPLETED_TOTAL`(L237), `RQSTS_COMPLETED_TOTAL`(L88),
   `APP_RQSTS_COMPLETED_TOTAL`(L106), `SELECT_SQL_STMTS`(L364), `UID_SQL_STMTS`(L365),
   `DDL_SQL_STMTS`(L366), `DYNAMIC_SQL_STMTS`(L361), `STATIC_SQL_STMTS`(L362),
   `FAILED_SQL_STMTS`(L363), `MERGE_SQL_STMTS`(L367), `CALL_SQL_STMTS`(L374),
   `TOTAL_APP_SECTION_EXECUTIONS`(L122).
4. **Type discipline**: every Db2 counter listed here is a monotonically increasing BIGINT since DB
   activation → submit as `monotonic_count` (catalog `count`). Postgres submits the analogous
   `pg_stat_database` values as `rate`; MySQL submits `Com_*` as `rate` and `Innodb_rows_*` as `rate`.
   Db2 should mirror **postgres** (emit raw `monotonic_count`; the backend derives per-second).
   Do **not** emit these as `rate` from the agent — keep them counters so dashboards can choose.
5. **Tagging**: instance/db level → tag `db:<DBNAME>` (existing global tag, `ibm_db2.py:48`) + base
   `database_hostname`/`database_instance`. Add `member:` when fanning out per-member (existing check
   passes `-1` = aggregate, `queries.py:40`). Per-connection fan-out (`MON_GET_CONNECTION`) and
   per-workload fan-out (`MON_GET_WORKLOAD`) are the Db2 analogs of pg per-`db`/MySQL per-schema
   tag-dicts — gate them behind config + top-N caps for cardinality.

---

## 1. Source objects for this category

| Db2 source | Granularity | Member arg | Confirmed | Use for |
|---|---|---|---|---|
| `MON_GET_DATABASE(member)` | one row per DB member | `-1` (current/agg), `-2` (all) | `_raw/02-monget-key-columns.txt:12-530` (515 cols) | **primary** — db/instance-wide throughput. Already called by the check (`queries.py:40`). |
| `MON_GET_CONNECTION(handle, member)` | one row per connection | `NULL,-2` | `_raw/02-monget-key-columns.txt:1452` header (417 cols) | per-connection rows/commits (optional, high-cardinality). |
| `MON_GET_WORKLOAD(workload_name, member)` | one row per WLM workload def | `NULL,-2` | `db2-monget-catalog-2.md:305-336` (371 cols) | per-logical-workload throughput. Default `SYSDEFAULTUSERWORKLOAD` always populated. |
| `MON_GET_SERVICE_SUBCLASS(super, sub, member)` | one row per WLM service subclass | `NULL,NULL,-2` | `db2-monget-catalog-2.md:188-301` (376 cols) | per-priority-class throughput; adds activity-completion fidelity. Default classes always populated. |
| `SYSIBMADM.MON_DB_SUMMARY` | single aggregate row over DB | n/a | `_raw/03-sysibmadm-objects.txt:43` (view present) | drop-in summary view (pre-aggregated subset of `MON_GET_DATABASE`) — cross-check / fallback. |
| `SYSIBMADM.MON_WORKLOAD_SUMMARY` | per-workload aggregate | n/a | `_raw/03-sysibmadm-objects.txt:49` | summary-view alt to `MON_GET_WORKLOAD`. |
| `SYSIBMADM.MON_SERVICE_SUBCLASS_SUMMARY` | per-subclass aggregate | n/a | `_raw/03-sysibmadm-objects.txt:46` | summary-view alt to `MON_GET_SERVICE_SUBCLASS`. |
| `SYSIBMADM.MON_CONNECTION_SUMMARY` | per-connection aggregate | n/a | `_raw/03-sysibmadm-objects.txt:40` | summary-view alt to `MON_GET_CONNECTION`. |
| `SYSIBMADM.SNAPDB` | single aggregate row (legacy snapshot) | n/a | `_raw/03-sysibmadm-objects.txt:62` | **deprecated** — has `COMMIT_SQL_STMTS`/`ROLLBACK_SQL_STMTS`/`ROWS_*`; only if `MON_GET_*` unavailable. |

**Recommendation:** standardize on `MON_GET_DATABASE` for the whole core set (matches the existing
check, one query, BASE monitor metrics are sufficient — `_raw/04-monitor-config.txt:9,17` show
`mon_act_metrics=BASE`, `mon_req_metrics=BASE`, which populate the activity/request families).

---

## 2. Commit / rollback semantics in Db2 (read before mapping)

Db2 splits commits/rollbacks into **application-issued** vs **internal**:

- `TOTAL_APP_COMMITS` (L130) = explicit COMMITs issued by applications. **This is the analog of
  `postgresql.commits` / `pg_stat_database.xact_commit`.**
- `INT_COMMITS` (L131) = internal commits the engine does on the app's behalf (e.g. autocommit of
  certain operations, internal cleanup). No direct pg/mysql analog; Db2-native, worth shipping.
- `TOTAL_APP_ROLLBACKS` (L134) = explicit ROLLBACKs. **Analog of `postgresql.rollbacks` /
  `xact_rollback`.**
- `INT_ROLLBACKS` (L135) = internal rollbacks (deadlock-victim rollbacks, statement-level rollbacks,
  etc.). Db2-native; high-signal for instability. orientation -1.

There is also `UID_SQL_STMTS` (Update/Insert/Delete statement count, L365) which is a **statement**
count, not a row count — don't confuse with the rows counters.

> ANALOG-FIDELITY NOTE: MySQL's `Com_commit`/`Com_rollback` (not currently in the mysql check's
> mapped set per `code-mysql-metrics.md`) ≈ Db2 `TOTAL_APP_COMMITS`/`TOTAL_APP_ROLLBACKS`. Postgres
> `xact_commit`/`xact_rollback` is the cleaner reference and Db2 maps to it 1:1 via the `*_APP_*`
> elements.

---

## 3. Rows semantics in Db2 (read before mapping)

`MON_GET_DATABASE` exposes both the **aggregate** row counters and an **insert/update/delete split**:

- `ROWS_READ` (L90) — rows the engine had to read to satisfy queries (i.e. rows examined, NOT rows
  returned to the client). **Analog of `pg tup_fetched` / `mysql Innodb_rows_read`.** A high
  `ROWS_READ`÷`ROWS_RETURNED` ratio = scan inefficiency (the classic Db2 "rows read per rows
  returned" health signal).
- `ROWS_RETURNED` (L91) — rows actually selected and returned to applications. **Analog of
  `pg tup_returned`** (semantically pg's `tup_returned` is "rows read by seq+index scans"; Db2's
  `ROWS_RETURNED` is closer to "rows returned to client" — note the mismatch, see §7).
- `ROWS_MODIFIED` (L89) — total rows inserted+updated+deleted (aggregate). Existing check emits this
  as `ibm_db2.row.modified.total`.
- `ROWS_INSERTED` (L352), `ROWS_UPDATED` (L353), `ROWS_DELETED` (L351) — the split. **Analogs of
  `pg tup_inserted`/`tup_updated`/`tup_deleted` and `mysql Innodb_rows_inserted/updated/deleted`.**
  Currently **NOT collected** — this is the main gap.
- `INT_ROWS_INSERTED` (L372), `INT_ROWS_UPDATED` (L373), `INT_ROWS_DELETED` (L371) — rows modified by
  internal activity (e.g. cascading RI, MQT maintenance, triggers). Db2-native; no pg/mysql analog.
- `FED_ROWS_*` (L474-477) — federated (nickname) row activity. Db2-native; only relevant with
  federation; skip unless federation in use.

> SEMANTIC WARNING for dashboards: `ROWS_INSERTED+ROWS_UPDATED+ROWS_DELETED` should ≈ `ROWS_MODIFIED`
> for *application* DML but `ROWS_MODIFIED` may also include internal — verify on the live target
> before asserting an identity in a monitor.

---

## 4. MAPPING TABLE — core (db/instance level, `MON_GET_DATABASE(-1)`)

All rows below: source = `MON_GET_DATABASE`, member arg `-1` (aggregate; existing convention
`queries.py:40`). Tags = `db:<DBNAME>` (global, `ibm_db2.py:48`) + base host/instance tags +
optional `member` if fanned out. Submit fn = `self.monotonic_count(...)` (catalog type `count`).
Add each column to `DATABASE_TABLE_COLUMNS` in `ibm_db2/datadog_checks/ibm_db2/queries.py:21-39`
and a submit line near `ibm_db2.py:184-190`.

### 4.1 Transaction throughput (NEW — no current equivalent)

| pg/mysql analog | Db2 source column (line) | proposed `ibm_db2.<name>` | type | unit / per_unit | tags | notes / version-gating |
|---|---|---|---|---|---|---|
| `postgresql.commits` (rate) / `pg xact_commit`; `mysql Com_commit` | `TOTAL_APP_COMMITS` (L130) | `ibm_db2.transaction.commits` | count (monotonic_count) | transaction | db, member | **primary commit metric.** orientation 0. BASE metrics; always available. |
| `postgresql.rollbacks` (rate) / `pg xact_rollback`; `mysql Com_rollback` | `TOTAL_APP_ROLLBACKS` (L134) | `ibm_db2.transaction.rollbacks` | count | transaction | db, member | orientation -1. |
| — (Db2-native) | `INT_COMMITS` (L131) | `ibm_db2.transaction.commits.internal` | count | transaction | db, member | engine-issued commits. orientation 0. |
| — (Db2-native; instability signal) | `INT_ROLLBACKS` (L135) | `ibm_db2.transaction.rollbacks.internal` | count | transaction | db, member | deadlock-victim & statement rollbacks. orientation -1. |
| — (statement count, loosely `mysql Com_*` family) | `UID_SQL_STMTS` (L365) | `ibm_db2.sql.uid_statements` | count | statement | db, member | update+insert+delete *statements* (not rows). orientation 0. |

> Naming alternative: to stay closer to the **existing flat style** (`ibm_db2.connection.total`,
> `ibm_db2.row.reads.total`), you could use `ibm_db2.commit.total` / `ibm_db2.rollback.total`. Pick
> one convention and apply consistently. The `transaction.*` namespace reads better on dashboards and
> matches pg's `transaction` unit. **Decision owed to plan.**

### 4.2 Row throughput (PARTIAL today — add the I/U/D split)

| pg/mysql analog | Db2 source column (line) | proposed `ibm_db2.<name>` | type | unit / per_unit | tags | notes |
|---|---|---|---|---|---|---|
| `pg tup_fetched` (`postgresql.rows_fetched`); `mysql.innodb.rows_read` | `ROWS_READ` (L90) | `ibm_db2.row.reads.total` **(EXISTS)** | count | row | db, member | already emitted (`ibm_db2.py:187`, `metadata.csv:45`). Keep. |
| `pg tup_returned` (`postgresql.rows_returned`) | `ROWS_RETURNED` (L91) | `ibm_db2.row.returned.total` **(EXISTS)** | count | row | db, member | already emitted (`ibm_db2.py:190`, `metadata.csv:46`). See §7 semantic mismatch. |
| (aggregate of I/U/D) | `ROWS_MODIFIED` (L89) | `ibm_db2.row.modified.total` **(EXISTS)** | count | row | db, member | already emitted (`ibm_db2.py:184`, `metadata.csv:44`). Keep. |
| `pg tup_inserted` (`postgresql.rows_inserted`); `mysql.innodb.rows_inserted` | `ROWS_INSERTED` (L352) | `ibm_db2.row.inserted.total` | count | row | db, member | **NEW.** orientation 0. |
| `pg tup_updated` (`postgresql.rows_updated`); `mysql.innodb.rows_updated` | `ROWS_UPDATED` (L353) | `ibm_db2.row.updated.total` | count | row | db, member | **NEW.** orientation 0. |
| `pg tup_deleted` (`postgresql.rows_deleted`); `mysql.innodb.rows_deleted` | `ROWS_DELETED` (L351) | `ibm_db2.row.deleted.total` | count | row | db, member | **NEW.** orientation 0. |
| — (Db2-native) | `INT_ROWS_INSERTED` (L372) | `ibm_db2.row.inserted.internal` | count | row | db, member | NEW; cascading RI / MQT / trigger inserts. Optional. |
| — (Db2-native) | `INT_ROWS_UPDATED` (L373) | `ibm_db2.row.updated.internal` | count | row | db, member | NEW. Optional. |
| — (Db2-native) | `INT_ROWS_DELETED` (L371) | `ibm_db2.row.deleted.internal` | count | row | db, member | NEW. Optional. |

> Naming consistency: existing metrics use `row.<verb>.total` (`row.reads.total`,
> `row.returned.total`, `row.modified.total`). The new I/U/D should follow the same pattern →
> `row.inserted.total` / `row.updated.total` / `row.deleted.total`. (Note existing uses `reads`
> plural but `returned`/`modified` past-participle — recommend `inserted`/`updated`/`deleted` to
> match `modified`.)

### 4.3 Activity / request throughput (NEW — no current equivalent)

These have **no postgres core analog** in the rows-throughput category (pg's closest is
`pg_stat_activity` *gauges* in §4.5 of `code-postgres-metrics.md`, and `sessions.count` etc. on
PG≥14). MySQL's closest is `Questions`/`Queries` (statement rates). Db2's
activity/request-completion counters are richer and are the native "work completed" throughput.

| pg/mysql analog | Db2 source column (line) | proposed `ibm_db2.<name>` | type | unit | tags | notes |
|---|---|---|---|---|---|---|
| `mysql.performance.questions`/`queries` (loose) | `ACT_COMPLETED_TOTAL` (L39) | `ibm_db2.activity.completed` | count | activity | db, member | coordinator activities completed. orientation 0. Primary "work done" counter. |
| — | `ACT_ABORTED_TOTAL` (L38) | `ibm_db2.activity.aborted` | count | activity | db, member | orientation -1. |
| — | `ACT_REJECTED_TOTAL` (L40) | `ibm_db2.activity.rejected` | count | activity | db, member | WLM-rejected activities. orientation -1. |
| — | `APP_ACT_COMPLETED_TOTAL` (L237) | `ibm_db2.activity.app_completed` | count | activity | db, member | coordinator app-level activities (excludes nested). Optional; pick one of `ACT_*`/`APP_ACT_*` to avoid redundancy. |
| — | `APP_ACT_ABORTED_TOTAL` (L238) | `ibm_db2.activity.app_aborted` | count | activity | db, member | optional. |
| — | `APP_ACT_REJECTED_TOTAL` (L239) | `ibm_db2.activity.app_rejected` | count | activity | db, member | optional. |
| `mysql Questions` (loose) | `RQSTS_COMPLETED_TOTAL` (L88) | `ibm_db2.request.completed` | count | request | db, member | requests completed (a request = one client/server interaction; broader than activity). orientation 0. |
| — | `APP_RQSTS_COMPLETED_TOTAL` (L106) | `ibm_db2.request.app_completed` | count | request | db, member | app-level requests completed. Optional. |
| — | `TOTAL_APP_SECTION_EXECUTIONS` (L122) | `ibm_db2.section.executions` | count | execution | db, member | number of SQL section executions (≈ statement executions). Good throughput proxy; closest to pg `calls`-style. orientation 0. |

### 4.4 SQL statement mix (NEW — optional; finer-grained throughput)

Optional sub-family that mirrors MySQL's `Com_select/insert/update/delete` statement-rate breakdown.
Db2 exposes statement counts by *category* (not by individual verb the way MySQL does) on
`MON_GET_DATABASE`. Gate behind a config flag (e.g. `collect_statement_mix_metrics`, default off) —
these are nice-to-have, not parity-critical.

| mysql analog | Db2 source column (line) | proposed `ibm_db2.<name>` | type | unit | tags | notes |
|---|---|---|---|---|---|---|
| `mysql.performance.com_select` | `SELECT_SQL_STMTS` (L364) | `ibm_db2.sql.select_statements` | count | statement | db, member | SELECT + SELECT INTO + VALUES INTO. orientation 0. |
| `mysql.performance.com_{insert,update,delete}` (combined) | `UID_SQL_STMTS` (L365) | `ibm_db2.sql.uid_statements` | count | statement | db, member | UPDATE+INSERT+DELETE *statements* (also listed in §4.1). |
| `mysql.performance.queries` (DDL portion) | `DDL_SQL_STMTS` (L366) | `ibm_db2.sql.ddl_statements` | count | statement | db, member | CREATE/ALTER/DROP/etc. orientation 0. |
| — | `MERGE_SQL_STMTS` (L367) | `ibm_db2.sql.merge_statements` | count | statement | db, member | MERGE. Db2-native. |
| — | `CALL_SQL_STMTS` (L374) | `ibm_db2.sql.call_statements` | count | statement | db, member | stored-procedure CALLs. |
| `mysql Com_stmt_*` (loose) | `DYNAMIC_SQL_STMTS` (L361) | `ibm_db2.sql.dynamic_statements` | count | statement | db, member | dynamic SQL executed. orientation 0. |
| — | `STATIC_SQL_STMTS` (L362) | `ibm_db2.sql.static_statements` | count | statement | db, member | static (packaged) SQL. |
| — (error signal) | `FAILED_SQL_STMTS` (L363) | `ibm_db2.sql.failed_statements` | count | statement | db, member | statements that returned a negative SQLCODE. orientation -1. Good error-rate metric. |
| — | `XQUERY_STMTS` (L368) | `ibm_db2.sql.xquery_statements` | count | statement | db, member | XQuery. Db2-native; skip unless XML workload. |
| — | `BINDS_PRECOMPILES` (L370) | `ibm_db2.sql.binds_precompiles` | count | operation | db, member | binds/precompiles. Db2-native; low value, skip by default. |
| — | `IMPLICIT_REBINDS` (L369) | `ibm_db2.sql.implicit_rebinds` | count | operation | db, member | implicit package rebinds (signals invalidated packages). Optional. |

---

## 5. MAPPING TABLE — per-dimension fan-out (optional, cardinality-gated)

These reuse the **same metric element names** as §4 but tagged by a finer dimension. They are the
Db2 analogs of MySQL's per-schema/per-table tag-dicts and Postgres's per-`db` rows. Gate each behind
a config flag + top-N cap (`FETCH FIRST n ROWS ONLY`), mirroring `index_metrics.py` `INDEX_LIMIT`
(`mysql/datadog_checks/mysql/index_metrics.py:7-34`).

### 5.1 Per-connection (`MON_GET_CONNECTION(NULL,-2)`)

Same throughput columns exist per connection: `ROWS_READ`(L1101), `ROWS_RETURNED`(L1102),
`ROWS_MODIFIED`(L1100), `ROWS_INSERTED`(L1276), `ROWS_UPDATED`(L1277), `ROWS_DELETED`(L1275),
`TOTAL_APP_COMMITS`(L1139), `INT_COMMITS`(L1140), `TOTAL_APP_ROLLBACKS`(L1143), `INT_ROLLBACKS`(L1144),
`ACT_COMPLETED_TOTAL`(L1049), `RQSTS_COMPLETED_TOTAL`(L1099), `UID_SQL_STMTS`(L1289),
`SELECT_SQL_STMTS`(L1288).

- Proposed metrics: same names as §4 but **tag** `application_name` (`APPLICATION_NAME` VARCHAR(128),
  L1033), `application_handle` (L1032), `client_user` (`CLIENT_USERID`, L1038), `member`.
- **Cardinality risk: HIGH** (one series per live connection). Default OFF. Cap to top-N by
  `ROWS_READ` or `TOTAL_APP_COMMITS`. This is closer to a DBM "activity" concern than a core metric —
  consider deferring to the DBM workstream (`code-mysql-dbm.md` / `db2-live-activity.md`).

### 5.2 Per-WLM-workload (`MON_GET_WORKLOAD(NULL,-2)`) — recommended fan-out

Default `SYSDEFAULTUSERWORKLOAD` (id 1) always returns a row (`db2-monget-catalog-2.md:329-331`), so
this is **safe to query unconditionally** and low-cardinality on a default config (1-3 workloads).
Columns confirmed present (`db2-monget-catalog-2.md:321-327`): `ACT_COMPLETED_TOTAL`,
`ACT_ABORTED_TOTAL`, `ACT_REJECTED_TOTAL`, `APP_ACT_COMPLETED_TOTAL`, `RQSTS_COMPLETED_TOTAL`,
`APP_RQSTS_COMPLETED_TOTAL`, `TOTAL_APP_COMMITS`, `INT_COMMITS`, `TOTAL_APP_ROLLBACKS`,
`INT_ROLLBACKS`. (Rows I/U/D also present — same element family as SUBCLASS, see
`db2-monget-catalog-2.md:266-269`.)

- Proposed: same metric names as §4 with a `workload:<WORKLOAD_NAME>` (+ `workload_id`, `member`) tag,
  OR a parallel namespace `ibm_db2.workload.activity.completed` etc. **Decision owed:** reuse-with-tag
  (cleaner catalog) vs separate namespace (clearer dashboards). Recommend reuse-with-tag + a
  `workload` tag, gated by `collect_workload_metrics` (default on; cardinality is naturally low).

### 5.3 Per-WLM-service-subclass (`MON_GET_SERVICE_SUBCLASS(NULL,NULL,-2)`)

Same element set as WORKLOAD (`db2-monget-catalog-2.md:214-218`: `ACT_COMPLETED_TOTAL`,
`ACT_RQSTS_TOTAL`, `RQSTS_COMPLETED_TOTAL`, `APP_RQSTS_COMPLETED_TOTAL`; commits/rollbacks at
`db2-monget-catalog-2.md:276-277`). Tag by `service_superclass_name` + `service_subclass_name` +
`member`. SUBCLASS and WORKLOAD **double-count the same activity along two axes**
(`db2-monget-catalog-2.md:332-336`) — ship at most one by default; WORKLOAD is the more intuitive
app-attribution axis. SUBCLASS only if WLM priority-class throughput is wanted.

---

## 6. SYSIBMADM summary-view equivalents (fallback / cross-check)

If `MON_GET_*` is unavailable (privilege/edition), the legacy + modern summary views carry the same
elements. Prefer `MON_GET_*`; these are documented for graceful-degradation paths.

| Db2 view (line in `_raw/03-sysibmadm-objects.txt`) | carries | maps to |
|---|---|---|
| `SYSIBMADM.MON_DB_SUMMARY` (L43) | `TOTAL_APP_COMMITS`, `TOTAL_APP_ROLLBACKS`, `ROWS_READ`, `ROWS_RETURNED`, `ROWS_MODIFIED`, `ACT_COMPLETED_TOTAL`, `RQSTS_COMPLETED_TOTAL`, `DEADLOCKS` *(general Db2 12.1 knowledge — this view is a curated MON_GET_DATABASE roll-up; verify column set on target)* | §4.1–§4.3 |
| `SYSIBMADM.SNAPDB` (L62, deprecated) | `COMMIT_SQL_STMTS`, `ROLLBACK_SQL_STMTS`, `ROWS_READ`, `ROWS_SELECTED`(≈returned), `ROWS_INSERTED`, `ROWS_UPDATED`, `ROWS_DELETED`, `INT_COMMITS`, `INT_ROLLBACKS` *(general Db2 12.1 knowledge — verify exact names)* | §4.1–§4.2 |
| `SYSIBMADM.MON_WORKLOAD_SUMMARY` (L49) | per-workload commits/rollbacks/rows/activities | §5.2 |
| `SYSIBMADM.MON_SERVICE_SUBCLASS_SUMMARY` (L46) | per-subclass | §5.3 |
| `SYSIBMADM.MON_CONNECTION_SUMMARY` (L40) | per-connection | §5.1 |

> Note: `SNAPDB` column names differ from `MON_GET_*` (e.g. `COMMIT_SQL_STMTS` vs
> `TOTAL_APP_COMMITS`, `ROWS_SELECTED` vs `ROWS_RETURNED`). If a fallback path is implemented, map
> carefully — don't assume identical names.

---

## 7. pg/mysql metrics in this category with NO clean Db2 equivalent (flag)

| pg/mysql metric | why no Db2 analog | closest Db2 (if any) |
|---|---|---|
| `postgresql.rows_hot_updated` (`pg rows_hot_updated`, relations) | HOT-update is a Postgres MVCC-specific optimization (heap-only tuple). Db2 has no HOT concept. | none. `NO_CHANGE_UPDATES` (`MON_GET_TABLE`, `db2-monget-catalog-2.md:77`) is loosely related (updates that changed no column value) but semantically different. |
| `postgresql.live_rows` / `dead_rows` / `toast.*_rows` (relations) | Postgres MVCC dead-tuple bookkeeping; Db2's MVCC-free locking model has no dead-row count. | none for "dead"; for live-row estimate use `SYSCAT.TABLES.CARD` or `MON_GET_TABLE`-joined RTS. Out of this category (belongs to a schema/relations map). |
| `postgresql.sessions.*` (PG≥14: session_time, active_time, idle_in_transaction_time, abandoned, fatal, killed) | pg14 session accounting. | partial: Db2 `CLIENT_IDLE_WAIT_TIME` (L60), `TOTAL_APP_RQST_TIME` (L98), `TOTAL_RQST_TIME` (L99), `UOW_CLIENT_IDLE_WAIT_TIME` (per-conn L1274) cover idle/active time at db/connection scope but not the pg session-lifecycle counts (abandoned/fatal/killed). Belongs more to a "time-spent"/activity map. |
| `mysql.performance.com_replace` / `com_insert_select` / `com_*_multi` | MySQL-verb-specific statement counters. | Db2 has no per-verb breakdown beyond SELECT/UID/DDL/MERGE/CALL categories (§4.4). MERGE ≈ REPLACE intent. |
| `mysql.replication.group.transactions*` | MySQL Group Replication. | HADR is the Db2 replication model → `MON_GET_HADR` (see `map-hadr-replication.md`), different shape. |

**Db2-native, no pg/mysql analog (worth adding):** `INT_COMMITS`, `INT_ROLLBACKS`,
`INT_ROWS_INSERTED/UPDATED/DELETED`, `ACT_REJECTED_TOTAL` (WLM admission rejects),
`MERGE_SQL_STMTS`, `CALL_SQL_STMTS`, `FAILED_SQL_STMTS`, `TOTAL_APP_SECTION_EXECUTIONS`.

**Semantic mismatch to document (existing metric):** `ibm_db2.row.returned.total` is mapped from
`ROWS_RETURNED` (rows returned *to the client*), whereas `postgresql.rows_returned` comes from
`tup_returned` (rows *read by scans*). The true Db2 analog of pg's `tup_returned`/`rows_fetched` is
`ROWS_READ` (→ `ibm_db2.row.reads.total`). When building parity dashboards, map
`postgresql.rows_returned`→`ibm_db2.row.reads.total` and treat `ibm_db2.row.returned.total` as a
*more useful* Db2-native "rows delivered to client" metric with no exact pg twin. (general Db2 12.1
knowledge on the semantic — verify against IBM monitor-element docs.)

---

## 8. Implementation notes (concrete)

1. **One-line-per-column change.** Add the new columns to
   `DATABASE_TABLE_COLUMNS` (`ibm_db2/datadog_checks/ibm_db2/queries.py:21-39`):
   `total_app_commits, int_commits, total_app_rollbacks, int_rollbacks, rows_inserted, rows_updated,
   rows_deleted, act_completed_total, act_aborted_total, act_rejected_total, rqsts_completed_total,
   total_app_section_executions` (+ optional `int_rows_*`, statement-mix). They join the existing
   `MON_GET_DATABASE(-1)` SELECT — **no new query, no new round-trip.**
2. **Submit lines** next to `ibm_db2.py:184-190` (the existing row block), e.g.
   `self.monotonic_count(self.m('transaction.commits'), db['total_app_commits'], tags=self._tags)`.
   Use `self.m(...)` (prefixes `ibm_db2.`, `ibm_db2.py:633-635`).
3. **No version gating needed** for the core set — all columns exist on 12.1.4 (cited above) and the
   activity/request families are populated by `mon_act_metrics=BASE` / `mon_req_metrics=BASE`
   (`_raw/04-monitor-config.txt:9,17`). If you later support Db2 < 11.1, gate the WLM
   `ACT_*`/`APP_ACT_*` columns — but the live target is 12.1.4, so unconditional is fine.
4. **Graceful degradation**: wrap submission so a missing key (NULL column on an edition that doesn't
   populate it, e.g. WLM disabled) is skipped, mirroring MySQL's `collect_scalar` returning `None`
   on missing keys (`mysql/datadog_checks/mysql/collection_utils.py:27-33`) and Postgres's
   per-scope error handling (`postgres.py:804-825`).
5. **metadata.csv**: add a row per new metric to `ibm_db2/metadata.csv` (header at line 1). Use
   catalog `metric_type=count` for all monotonic counters, `unit_name` ∈
   {`transaction`,`row`,`activity`,`request`,`statement`,`execution`,`operation`}, `orientation`
   per the tables above (0 for throughput, -1 for rollbacks/aborts/rejects/failures), `integration=ibm_db2`.
6. **Tags**: keep the global `db:` tag (`ibm_db2.py:48`). Add `member` only when switching the member
   arg off `-1` for per-member fidelity (pureScale/DPF). For §5 fan-outs, add the dimension tag and a
   top-N cap.
7. **tracked_query/operation naming** (if adopting the base-framework timing like MySQL's
   `tracked_query`): name the op `database_throughput_metrics`.

---

## 9. Proposed metadata.csv rows (ready to paste — core set, §4.1–§4.3)

```
ibm_db2.transaction.commits,count,,transaction,,The number of application-requested transaction commits (TOTAL_APP_COMMITS). This metric is tagged with db.,0,ibm_db2,,
ibm_db2.transaction.rollbacks,count,,transaction,,The number of application-requested transaction rollbacks (TOTAL_APP_ROLLBACKS). This metric is tagged with db.,-1,ibm_db2,,
ibm_db2.transaction.commits.internal,count,,transaction,,The number of internal commits initiated by the database manager (INT_COMMITS). This metric is tagged with db.,0,ibm_db2,,
ibm_db2.transaction.rollbacks.internal,count,,transaction,,The number of internal rollbacks initiated by the database manager (INT_ROLLBACKS). This metric is tagged with db.,-1,ibm_db2,,
ibm_db2.row.inserted.total,count,,row,,The total number of rows inserted (ROWS_INSERTED). This metric is tagged with db.,0,ibm_db2,,
ibm_db2.row.updated.total,count,,row,,The total number of rows updated (ROWS_UPDATED). This metric is tagged with db.,0,ibm_db2,,
ibm_db2.row.deleted.total,count,,row,,The total number of rows deleted (ROWS_DELETED). This metric is tagged with db.,0,ibm_db2,,
ibm_db2.activity.completed,count,,operation,,The number of coordinator activities that completed (ACT_COMPLETED_TOTAL). This metric is tagged with db.,0,ibm_db2,,
ibm_db2.activity.aborted,count,,operation,,The number of coordinator activities that aborted (ACT_ABORTED_TOTAL). This metric is tagged with db.,-1,ibm_db2,,
ibm_db2.activity.rejected,count,,operation,,The number of activities rejected by WLM thresholds (ACT_REJECTED_TOTAL). This metric is tagged with db.,-1,ibm_db2,,
ibm_db2.request.completed,count,,request,,The number of requests completed (RQSTS_COMPLETED_TOTAL). This metric is tagged with db.,0,ibm_db2,,
ibm_db2.section.executions,count,,operation,,The number of SQL section executions (TOTAL_APP_SECTION_EXECUTIONS). This metric is tagged with db.,0,ibm_db2,,
```
(`activity`/`request`/`statement`/`execution` are not standard Datadog unit names — `operation`/
`request` are valid; verify `transaction` and `row` are accepted, which they are per
`postgres/metadata.csv` and `ibm_db2/metadata.csv:44`. Use `operation` where no exact unit fits.)

---

## 10. Priority for the plan

1. **P0 (parity-critical, trivial):** §4.1 commits/rollbacks (`TOTAL_APP_COMMITS`,
   `TOTAL_APP_ROLLBACKS`) + §4.2 rows I/U/D split (`ROWS_INSERTED/UPDATED/DELETED`). Closes the
   biggest, clearest gap vs both pg and mysql. ~6 columns + 6 submit lines + 6 metadata rows.
2. **P1 (high value, cheap):** §4.1 internal commits/rollbacks; §4.3 `ACT_COMPLETED_TOTAL`,
   `RQSTS_COMPLETED_TOTAL`, `TOTAL_APP_SECTION_EXECUTIONS` (Db2-native throughput with no pg/mysql twin).
3. **P2 (optional, config-gated):** §4.4 SQL statement mix; §5.2 per-workload fan-out.
4. **P3 (defer to DBM workstream):** §5.1 per-connection fan-out (cardinality; overlaps activity sampling).
