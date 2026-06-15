# 02 — Current `ibm_db2` Integration Audit & Gap to Target

**Audience.** You know the Datadog `postgres` and `mysql` integrations well — `pg_stat_statements`,
`DBMAsyncJob`, the `dbm-*` event-platform tracks, obfuscation/signatures — but you may know little
about IBM Db2. This document audits what the `ibm_db2` integration ships **today**, then measures the
gap to a high-fidelity, DBM-enabled target. Every Db2 concept is explained inline and every design
claim is cited to a file in `_research/` or to source under
`/home/bits/dd/integrations-core/ibm_db2`.

**Where this sits in the plan.** This is doc `02`. It is the "before" picture and the punch list.

- `_research/code-ibm_db2-current.md` — the exhaustive code audit this doc condenses. **Read it for
  line-level detail**; this doc summarizes and adds the gap framing.
- `_research/code-dbm-payload-contract.md` — the `dbm-*` payload envelope the target must fill
  (cross-referenced throughout §5/§7).
- `_research/code-integration-scaffolding.md` — `ddev`, `spec.yaml`, `metadata.csv`, `hatch.toml`
  conventions for landing the changes (cross-referenced in §6/§7).
- `_research/code-postgres-dbm-statements.md`, `_research/db2-live-pkgcache.md` — the query-metrics
  design + the live `MON_GET_PKG_CACHE_STMT` probe (the `pg_stat_statements` analog) (§5.1, §7).
- `_research/db2-live-activity.md` — the live activity/sampling probe (the `pg_stat_activity`
  analog) (§5.2, §7).
- `_research/map-bufferpool.md`, `_research/map-io-disk.md`, `_research/map-sorting-hashing.md`,
  `_research/map-hadr-replication.md` — per-category metric maps that flesh out the standard-metric
  punch list (§4, §7).
- `_research/db2-config-settings.md` — the Db2 config-exposure research for a `dbm-metadata`
  settings payload (§5.4).

> When this doc says "the check", it means the single class `IbmDb2Check` in
> `/home/bits/dd/integrations-core/ibm_db2/datadog_checks/ibm_db2/ibm_db2.py`.

---

## 0. Db2 in five paragraphs (orientation for a pg/mysql engineer)

**Monitoring surface.** Db2's equivalent of `pg_stat_*` views is a family of **table functions**
named `MON_GET_*`, called as `TABLE(MON_GET_FOO(args))` in a `FROM` clause. They return cumulative,
monotonically-increasing counters since the database was last *activated* (the Db2 word for "opened
for connections"). There are also older snapshot **admin views** under the `SYSIBMADM` schema
(e.g. `SYSIBMADM.SNAPHADR`, `SYSIBMADM.MON_CURRENT_SQL`); prefer the `MON_GET_*` functions where both
exist (`map-hadr-replication.md:14`).

**Member argument.** Almost every `MON_GET_*` function takes a trailing **member** argument. Db2 can
run as a single node, as **DPF** (Database Partitioning Feature — sharded across multiple "members"),
or as **pureScale** (shared-disk cluster with a group buffer pool). Passing `-1` means "current
member"; `-2` means "aggregate all members"; `NULL` in the object slot means "all objects". The
existing check passes `-1`/`NULL` everywhere, which **flattens** any multi-member topology
(`code-ibm_db2-current.md:99`, `:367`).

**The package cache = `pg_stat_statements`.** Db2 keeps a **package cache** of prepared statement
sections. `TABLE(MON_GET_PKG_CACHE_STMT(NULL,NULL,NULL,-1))` returns cumulative per-cached-statement
counters — execution count, CPU, rows, I/O, sorts, locks — keyed by an opaque binary
**`EXECUTABLE_ID`**. This is the Db2 analog of `pg_stat_statements` and the foundation of DBM query
metrics (`db2-live-pkgcache.md:48`, `:53`). **Db2 does NOT normalize literals**: `... WHERE sku =
'item1'` and `... WHERE sku = 'item2'` get separate cache entries / `EXECUTABLE_ID`s, so the agent
must obfuscate client-side exactly like postgres (`db2-live-pkgcache.md:62`, `:193`).

**Live activity = `pg_stat_activity`.** `SYSIBMADM.MON_CURRENT_SQL` (a thin view over
`TABLE(MON_GET_ACTIVITY(NULL,-2))` joined to `MON_GET_CONNECTION`) is the "what is running right now"
source, with `STMT_TEXT`, application identity, activity state, and a wall-clock
`ELAPSED_TIME_MSEC` (`db2-live-activity.md:67`, `:74`).

**The Python driver.** The check talks to Db2 through the **`ibm_db`** C-extension (PyPI `ibm-db`,
pinned `3.2.6`). It is **not bundled** with the Agent — the operator must `pip install ibm_db` into
the Agent's embedded Python plus install the IBM CLI/ODBC driver
(`code-ibm_db2-current.md:12`, README `:19-53`). Column names come back **lowercase** because the
check sets `ibm_db.ATTR_CASE = ibm_db.CASE_LOWER` on the connection
(`code-ibm_db2-current.md:72`, `ibm_db2.py:567`). Keep all result-dict keys lowercase in any new code.

---

## 1. File-by-file inventory (what exists today)

Integration version **4.3.0** (`datadog_checks/ibm_db2/__about__.py:4`), min Agent **6.11.0**, min
`datadog-checks-base` **>=37.33.0** (`pyproject.toml:31`). Target Db2 is **12.1** (live container
12.1.4); CI currently tests only **11.1** (`hatch.toml:5-8`).

| Path (relative to `ibm_db2/`) | What it is | State vs. target |
|---|---|---|
| `datadog_checks/ibm_db2/ibm_db2.py` | The whole check: `IbmDb2Check(AgentCheck)`, connection mgmt, 6 query methods, events. ~635 lines. | **Subclasses plain `AgentCheck`**, not `DatabaseCheck`. No DBM. Must change (§5). |
| `datadog_checks/ibm_db2/queries.py` | SQL strings + column tuples for the 5 built-in `MON_GET_*` calls. No YAML manifest, no `QueryManager`. | Keep style; add new `MON_GET_*` SQL for parity + DBM. |
| `datadog_checks/ibm_db2/utils.py` | `get_version` (`SQL_DBMS_VER`), `status_to_service_check` (`DB_STATUS_MAP`), connection-string scrubber. | Reusable. Version parse must be confirmed against 12.1.4 (§6). |
| `datadog_checks/ibm_db2/config_models/{instance,shared,defaults}.py` | **Autogenerated** pydantic models from `spec.yaml`. Do not hand-edit. | Need new DBM fields generated (§6). |
| `datadog_checks/ibm_db2/config_models/{validators,__init__}.py` | Hand-editable validator stub + `ConfigMixin`. Check does **not** use `ConfigMixin` today (reads `self.instance.get`). | Adopt `ConfigMixin` for DBM (`code-integration-scaffolding.md:217-223`). |
| `datadog_checks/ibm_db2/data/conf.yaml.example` | **Autogenerated** sample config. | Regenerate after spec changes. |
| `assets/configuration/spec.yaml` | **Source of truth** for config (generates models + example). | Add `dbm`, `query_metrics`, `query_activity`, `collect_settings`, cloud blocks (§6). |
| `metadata.csv` | Metric catalog. **49 metrics** (50 lines incl. header). | Grow toward pg/mysql breadth (§3, §4). |
| `manifest.json` | Tile/asset metadata. `source_type_id: 10054`, `app_id: ibm-db2`, `owner: agent-integrations`, `metrics.check: ibm_db2.connection.active`. | No DBM manifest flag exists; DBM is payload-driven (`code-dbm-payload-contract.md:564-571`). Consider `owner: database-monitoring`. |
| `assets/service_checks.json` | 2 service checks (`can_connect`, `status`). | Possibly add a DBM-job service check (§3.3). |
| `assets/dashboards/overview.json` | "IBM Db2 Overview", `layout_type: free`, 29 widgets. | No DBM widgets, no query-perf widgets (§3.4). |
| `assets/logs/ibm_db2.yaml` (+ `_tests.yaml`) | Grok pipeline for `db2diag.log`. | Fine; orthogonal to DBM. |
| `assets/dataflows.yaml` | Declares `metrics`/`logs`/`events` inbound. | DBM is **not** a dataflows entry (`code-integration-scaffolding.md:613-619`); no change. |
| `tests/{test_unit,test_integration,test_integration_e2e,test_bench}.py`, `common.py`, `conftest.py`, `metrics.py` | Unit + integration + e2e tests; `DbManager` bootstraps the test DB. | Need DBM tests; matrix only 11.1 (§6). |
| `tests/docker/docker-compose.yaml` | `taskana/db2:${DB2_VERSION}`. | May not publish a 12.1 tag — switch to `icr.io/db2_community/db2` (`code-integration-scaffolding.md:504-507`). |
| `hatch.toml` | Test matrix `python=["3.13"]`, `version=["11.1"]`. | Add `"12.1"` (§6). |

> There is currently **no DBM module** under `datadog_checks/ibm_db2/` — no `statements.py`,
> `statement_samples.py`/`activity.py`, `metadata.py`, `schemas.py`, `health.py`. All of that is
> net-new (`code-integration-scaffolding.md:59-60`).

---

## 2. The check at runtime (how the 49 metrics are produced)

The check is a classic synchronous `AgentCheck`. On each run (default `min_collection_interval` = 15s)
it lazily opens **one persistent `ibm_db` connection**, emits the connect service check, collects
version metadata, then runs six query methods in order, swallowing per-method exceptions at WARNING
(`code-ibm_db2-current.md:17-45`, `ibm_db2.py:76-91`):

```python
self._query_methods = (
    self.query_instance,        # MON_GET_INSTANCE(-1)
    self.query_database,        # MON_GET_DATABASE(-1)
    self.query_buffer_pool,     # MON_GET_BUFFERPOOL(NULL,-1)   -> per buffer pool
    self.query_table_space,     # MON_GET_TABLESPACE(NULL,-1)   -> per table space
    self.query_transaction_log, # MON_GET_TRANSACTION_LOG(-1)
    self.query_custom,          # user custom_queries
)
```

Key runtime properties, each a **limitation vs. the target**:

- **Single unguarded persistent connection.** No pool, no statement/query timeout, no read-only
  enforcement. Reconnect is best-effort in `iter_rows` with an acknowledged `# ToDo`
  (`ibm_db2.py:617-618`). `connection_timeout` only sets `connecttimeout`, not a per-query timeout
  (`code-ibm_db2-current.md:76-78`, `:375-376`).
- **Everything synchronous, one interval.** No `DBMAsyncJob`, so there is no way to run a heavy
  collector (samples at 1s, metrics at 10s) on its own schedule
  (`code-ibm_db2-current.md:362-363`).
- **Coarse granularity.** All `MON_GET_*` calls use `-1`/`NULL`, so metrics are aggregated to
  instance / database / buffer-pool / table-space / log only. **No per-table, per-index,
  per-statement, per-connection, per-workload (WLM), or per-member dimension**
  (`code-ibm_db2-current.md:365-367`).
- **`only_custom_queries` is documented but not enforced.** The option exists in the config models
  and the sample, but `check()` never branches on it — the five built-ins always run
  (`code-ibm_db2-current.md:259`, `:383`).

### Tags

- Global on every metric/event/service check: `db:<db>` (auto-added, `ibm_db2.py:48`) + user `tags`.
- Buffer-pool metrics add `bufferpool:<bp_name>`; table-space metrics add `tablespace:<tbsp_name>`.
- **No `host`/instance/member/partition tag from the check** (host = Agent hostname). No
  `application`, `schema`, `table`, `query_signature`, or `member` dimension
  (`code-ibm_db2-current.md:222`). The DBM identity tags (`database_instance:`,
  `database_hostname:`, `dd.internal.resource:*`) used by postgres
  (`code-dbm-payload-contract.md:138-147`) are entirely absent.

---

## 3. Exhaustive inventory of the 49 metrics + their SQL

All metrics use prefix `ibm_db2.`. Counts are submitted via `self.monotonic_count(...)` in code but
catalogued in `metadata.csv` as type `count` (only `count`/`gauge`/`rate` are valid in metadata.csv —
`code-integration-scaffolding.md:87-93`). Source lines below are in `ibm_db2.py` /
`queries.py`. Full detail: `code-ibm_db2-current.md` §4.

### 3.1 `query_instance` — `MON_GET_INSTANCE(-1)` (`ibm_db2.py:127-131`, `queries.py:15-17`)

```sql
SELECT total_connections FROM TABLE(MON_GET_INSTANCE(-1))
```

| Metric | Type | Source |
|---|---|---|
| `ibm_db2.connection.active` | gauge | `total_connections` (this is also the manifest "check" canary) |

### 3.2 `query_database` — `MON_GET_DATABASE(-1)` (`ibm_db2.py:133-190`, `queries.py:20-40`)

```sql
SELECT appls_cur_cons, appls_in_db2, connections_top, current timestamp AS current_time,
       db_status, deadlocks, last_backup, lock_list_in_use, lock_timeouts, lock_wait_time,
       lock_waits, num_locks_held, num_locks_waiting, rows_modified, rows_read, rows_returned,
       total_cons
FROM TABLE(MON_GET_DATABASE(-1))
```

`current timestamp` is a SQL special register (not a column) used only to compute backup age.

| Metric | Type | Source / formula |
|---|---|---|
| (service check) `ibm_db2.status` | service_check | `db_status` via `status_to_service_check` |
| `ibm_db2.application.active` | gauge | `appls_cur_cons` |
| `ibm_db2.application.executing` | gauge | `appls_in_db2` |
| `ibm_db2.connection.max` | gauge | `connections_top` |
| `ibm_db2.connection.total` | count | `total_cons` |
| `ibm_db2.lock.dead` | count | `deadlocks` |
| `ibm_db2.lock.timeouts` | count | `lock_timeouts` |
| `ibm_db2.lock.active` | gauge | `num_locks_held` |
| `ibm_db2.lock.waiting` | gauge | `num_locks_waiting` |
| `ibm_db2.lock.wait` | gauge | `lock_wait_time / lock_waits` (avg ms, 0 if no waits) |
| `ibm_db2.lock.pages` | gauge | `lock_list_in_use / 4096` (bytes → 4 KiB pages) |
| `ibm_db2.backup.latest` | gauge | `(current_time - last_backup)` seconds, else `-1` |
| `ibm_db2.row.modified.total` | count | `rows_modified` |
| `ibm_db2.row.reads.total` | count | `rows_read` |
| `ibm_db2.row.returned.total` | count | `rows_returned` |

### 3.3 `query_buffer_pool` — `MON_GET_BUFFERPOOL(NULL,-1)` (`ibm_db2.py:192-377`, `queries.py:43-79`)

One row **per buffer pool**, tagged `bufferpool:<bp_name>`. Db2 has **four page classes** —
`data`, `index`, `xda` (XML storage object), and `column` (BLU/columnar; Db2-native, no pg/mysql
analog) — and for reads each class sums a regular and a `temp` counter
(`map-bufferpool.md:42-51`). For each class `<x>`:

- `bufferpool.<x>.reads.physical` (count) = `pool_<x>_p_reads + pool_temp_<x>_p_reads`
- `bufferpool.<x>.reads.logical` (count) = `pool_<x>_l_reads + pool_temp_<x>_l_reads`
- `bufferpool.<x>.reads.total` (count) = physical + logical
- `bufferpool.<x>.hit_percent` (gauge) = `(pool_<x>_lbp_pages_found − pool_async_<x>_lbp_pages_found) / logical_reads × 100`

Plus the four-class aggregates `bufferpool.reads.{physical,logical,total}` (count) and
`bufferpool.hit_percent` (gauge). Plus pureScale **group buffer pool** variants
`bufferpool.group.{column,data,index,xda,}.hit_percent` (gauge) — declared in `metadata.csv:13-17`
but only emitted on pureScale (`# no cov`). That is **25 buffer-pool metric names** (the largest
group). The unit for read counts is `get` ("buffer pool gets" = logical reads, a Db2-ism —
`map-bufferpool.md:72`).

> Existing bug to fix while here: `ibm_db2.bufferpool.xda.hit_percent` description in
> `metadata.csv:26` wrongly says "index page request" (copy/paste error — `map-bufferpool.md:73`).

### 3.4 `query_table_space` — `MON_GET_TABLESPACE(NULL,-1)` (`ibm_db2.py:379-412`, `queries.py:82-91`)

One row **per table space**, tagged `tablespace:<tbsp_name>`.

```sql
SELECT tbsp_name, tbsp_page_size, tbsp_state, tbsp_total_pages, tbsp_usable_pages, tbsp_used_pages
FROM TABLE(MON_GET_TABLESPACE(NULL,-1))
```

| Metric | Type | Formula |
|---|---|---|
| `ibm_db2.tablespace.size` | gauge | `tbsp_total_pages × tbsp_page_size` (bytes) |
| `ibm_db2.tablespace.usable` | gauge | `tbsp_usable_pages × tbsp_page_size` (bytes) |
| `ibm_db2.tablespace.used` | gauge | `tbsp_used_pages × tbsp_page_size` (bytes) |
| `ibm_db2.tablespace.utilized` | gauge | `tbsp_used_pages / tbsp_usable_pages × 100` (percent) |

`tbsp_state` drives the `tablespace_state_change` event (§3.6), not a metric.

### 3.5 `query_transaction_log` — `MON_GET_TRANSACTION_LOG(-1)` (`ibm_db2.py:414-441`, `queries.py:94-98`)

```sql
SELECT log_reads, log_writes, total_log_available, total_log_used FROM TABLE(MON_GET_TRANSACTION_LOG(-1))
```

| Metric | Type | Formula |
|---|---|---|
| `ibm_db2.log.used` | gauge | `total_log_used / 4096` (4 KiB blocks) |
| `ibm_db2.log.available` | gauge | `total_log_available / 4096`; **0 if infinite log (`-1`)** |
| `ibm_db2.log.utilized` | gauge | `total_log_used / total_log_available × 100`; 0 if infinite |
| `ibm_db2.log.reads` | count | `log_reads` |
| `ibm_db2.log.writes` | count | `log_writes` |

> Correctness nit to carry forward: when the log is infinite (`available == -1`) the gauge
> `log.available` is submitted as `0`, conflating "infinite" with "none"
> (`code-ibm_db2-current.md:207`, `:384`).

### 3.6 Service checks & events (the non-metric signals)

- **`ibm_db2.can_connect`** — ok/critical, emitted every run + on reconnect (`ibm_db2.py:580-589`).
- **`ibm_db2.status`** — ok/warning/critical/unknown, mapped from `db_status` via `DB_STATUS_MAP`
  (`utils.py:13-20`): `ACTIVE`/`ACTIVE_STANDBY`/`STANDBY`→OK, `QUIESCE_PEND`/`ROLLFWD`→WARNING,
  `QUIESCED`→CRITICAL, else UNKNOWN. (`STANDBY` entries exist but **no HADR metrics** back them —
  see §4.)
- **`ibm_db2.tablespace_state_change`** event — fires when a table-space `tbsp_state` changes between
  runs. State is **in-memory only**, lost on Agent restart (`code-ibm_db2-current.md:251-253`).

### 3.7 Custom queries

`custom_queries` (instance) + `global_custom_queries` (init_config), merged by
`use_global_custom_queries`. 3-field format (`metric_prefix`, `query`, `columns`; optional `tags`),
columns map to a submission method or `type: tag`, executed via `ibm_db.fetch_tuple`
(`code-ibm_db2-current.md:257-261`). This is the only escape hatch a customer has today for
query-level or table-level data — and it is manual, untyped, and undashboarded.

---

## 4. Gap analysis vs. postgres (244 metrics) / mysql (254 metrics)

Standard-metric breadth (counting `metadata.csv` rows, header excluded):

| Integration | Standard metrics | Largest groups |
|---|---|---|
| **postgres** | **244** | `queries.*` (DBM per-query, 17), `replication*` (33 across replication/slots/receiver/conflicts/archiver), `io.*` (10, pg_stat_io), `bgwriter.*` (10), `toast.*` (10), `vacuum`/`analyze`/`cluster_vacuum` (17), `wal*` (11), `sessions.*` (7), `buffercache.*` (5), per-relation `relation/index/function` |
| **mysql** | **254** | `innodb.*` (101), `performance.*` (80, performance_schema), `queries.*` (20, DBM per-query), `replication.*` (14 + galera 15), `myisam.*` (7), `index.*` (4) |
| **ibm_db2** | **49** | `bufferpool.*` (25), `lock.*` (6), `log.*` (5), `tablespace.*` (4), `row.*` (3), `connection.*` (3), `application.*` (2), `backup` (1) |

So Db2 ships **~20% of postgres's and ~19% of mysql's standard-metric breadth**, and the breadth it
does have is heavily concentrated in buffer pools. The category-by-category gap (each category has a
dedicated `_research/map-*.md` with exact `MON_GET_*` columns and proposed metric names):

| Category | postgres / mysql have | Db2 today | Db2 source to add | Map doc |
|---|---|---|---|---|
| **Buffer pool reads/hit ratio** | yes | **yes (25)** — the strong suit | — | `map-bufferpool.md` |
| **Buffer pool WRITES / page cleaning / victim** | `bgwriter.buffers_*`, `innodb.buffer_pool_pages_flushed` | **none** | `POOL_*_WRITES`, `POOL_DRTY_PG_*`, `POOL_NO_VICTIM_BUFFER` on `MON_GET_BUFFERPOOL` | `map-bufferpool.md:81-90`, `map-io-disk.md` |
| **Prefetch / async I/O** | `recovery_prefetch.*` (9) | **none** | `POOL_ASYNC_*`, `UNREAD_PREFETCH_PAGES`, `PREFETCH_WAIT_TIME` | `map-io-disk.md:26` |
| **Direct (non-buffered) I/O + I/O timing** | `io.*` (10) | **none** | `DIRECT_READS/WRITES`, `DIRECT_*_REQS`, `POOL_READ_TIME`, `POOL_WRITE_TIME`, `DIRECT_READ_TIME`, `DIRECT_WRITE_TIME` | `map-io-disk.md` |
| **Container / filesystem capacity** | `total_size`, `*_size` | **none** (only tablespace bytes) | `MON_GET_CONTAINER`: `FS_USED_SIZE`, `FS_TOTAL_SIZE` | `map-io-disk.md:35` |
| **Sorting / hashing / spills** | mysql `sort_*`, pg `temp_*` | **none** | `TOTAL_SORTS`, `SORT_OVERFLOWS`, `TOTAL_HASH_JOINS`, `HASH_JOIN_OVERFLOWS`, `POST_THRESHOLD_SORTS` (on `MON_GET_DATABASE`) | `map-sorting-hashing.md` |
| **HADR / replication** | pg 33, mysql 14 | **none** (despite `STANDBY` in the status map) | `MON_GET_HADR(-1)`: `HADR_STATE`, `HADR_CONNECT_STATUS`, `HADR_LOG_GAP`, `STANDBY_RECV_REPLAY_GAP`, log positions | `map-hadr-replication.md` |
| **Per-table / per-index** | pg `relation/index`, mysql `index.*` | **none** | `MON_GET_TABLE`, `MON_GET_INDEX` | `code-ibm_db2-current.md:366` |
| **Per-connection / per-workload (WLM)** | pg `sessions`, `activity` | **none** | `MON_GET_CONNECTION`, `MON_GET_WORKLOAD`, `MON_GET_SERVICE_SUBCLASS` | `code-ibm_db2-current.md:366` |
| **Memory pools** | pg shared mem, mysql `innodb` mem | **none** | `MON_GET_MEMORY_POOL` / `MON_GET_MEMORY_SET` | `code-ibm_db2-current.md:366` |
| **Per-query metrics (DBM)** | pg `queries.*` (17), mysql `queries.*` (20) | **none** | `MON_GET_PKG_CACHE_STMT` → `dbm-metrics` (NOT metadata.csv) | §5.1 |

> **Naming guidance from the maps:** name the HADR namespace `ibm_db2.hadr.*`, **not**
> `ibm_db2.replication.*` — in Db2-land "replication" means SQL/Q Replication, a different product;
> the HA feature is literally "HADR" (`map-hadr-replication.md:12`). On a non-HADR database,
> `MON_GET_HADR(-1)` returns **0 rows** — treat that as "not configured" and emit nothing, do not
> error (`map-hadr-replication.md:15`). For new read counters reuse `unit_name=get`
> (`map-bufferpool.md:72`).

---

## 5. The total absence of DBM (the headline gap)

Postgres/mysql/sqlserver ship **Database Monitoring**: per-query metrics, normalized query samples,
execution plans, active-session sampling, and instance/settings/schema metadata — all delivered on
the five **event-platform tracks** (`dbm-metrics`, `dbm-samples`, `dbm-activity`, `dbm-metadata`,
`dbm-health`), not as standard metrics (`code-dbm-payload-contract.md:49`). **`ibm_db2` ships none of
it.** A grep over `datadog_checks/ibm_db2/` for `mon_get_pkg_cache_stmt|mon_current_sql|
mon_get_activity|dbm|database_monitoring|obfuscate|query_signature|DBMAsyncJob` returns nothing
(`code-ibm_db2-current.md:355-360`, `db2-live-activity.md:119-122`,
`db2-live-pkgcache.md:421`).

The check subclasses plain `AgentCheck`. The target must subclass **`DatabaseCheck`**
(`datadog_checks/base/checks/db.py`) to get the `database_monitoring_query_{sample,metrics,activity}`
/ `database_monitoring_metadata` / `database_monitoring_health` helpers and the identity properties
(`reported_hostname`, `database_identifier`, `dbms`→`"db2"`, `dbms_version`, `tags`,
`cloud_metadata`) every payload needs (`code-dbm-payload-contract.md:30-47`, `:592-596`). Each
collector below is a `DBMAsyncJob` subclass with its own `job_name` and interval, kicked off from
`check()` and gated by a config `enabled` flag (`code-dbm-payload-contract.md:503-516`).

### 5.1 Query metrics (`dbm-metrics`) — the `pg_stat_statements` analog

- **Source:** `TABLE(MON_GET_PKG_CACHE_STMT(NULL,NULL,NULL,-1))`. **327 columns** on 12.1.4;
  introspect at runtime (do not hard-code by fixpack) exactly like postgres reads `cursor.description`
  of a `LIMIT 0` probe (`db2-live-pkgcache.md:51`, `:384-386`; pattern at
  `code-postgres-dbm-statements.md:108`).
- **Stable identity:** `HEX(EXECUTABLE_ID)` — a 32-byte opaque binary, verified stable across
  snapshots (`db2-live-pkgcache.md:53`, `:158-166`). Use it as the snapshot diff key (the analog of
  postgres `(queryid,dbid,userid)`), then **re-merge by `query_signature`** so churned identities and
  literal variants collapse (`db2-live-pkgcache.md:170`, `:392`).
- **Reuse the base delta engine** `StatementMetrics.compute_derivative_rows` — diff cumulative
  counters, drop whole rows on any negative diff (cache eviction = stats reset), require the
  execution indicator to increase. The execution indicator is **`NUM_EXEC_WITH_METRICS`** (IBM's
  recommended average divisor — some executions run without metrics), guard against 0
  (`db2-live-pkgcache.md:69`, `:395`; engine at `code-postgres-dbm-statements.md:116-157`).
- **Obfuscation:** Db2 does NOT normalize literals, and the orders app prepends a Datadog SQL-comment
  tag `/*dddbs=...,dde=...,ddps=...,ddprs=...*/` to `STMT_TEXT` — the obfuscator/signature step must
  strip leading comments and reuse `compute_sql_signature` (MurmurHash3-64 of the obfuscated text) so
  DBM↔APM correlation works. Call `obfuscate_sql_with_metadata(..., replace_null_character=True)` for
  Db2 (`db2-live-pkgcache.md:62`, `:78`; `code-postgres-dbm-statements.md:180-194`, `:209`).
- **Units gotcha:** `TOTAL_CPU_TIME` is **microseconds**; `STMT_EXEC_TIME`/`TOTAL_ACT_TIME`/etc. are
  **milliseconds**. Convert before mixing (`db2-live-pkgcache.md:66`, `:397`). Timing columns require
  `mon_act_metrics >= BASE` — introspect and gate (`db2-live-pkgcache.md:73`).
- **Payload:** wrapper key **`db2_rows`**, version key **`db2_version`**, `ddsource:"db2"`. FQT events
  go on `dbm-samples` (`code-dbm-payload-contract.md:188-218`, `:271-284`).
- **`STMT_TEXT` is a 2 MB CLOB** — bound the fetch (e.g. first 4–16 KB), set a `query_truncated` flag
  via `LENGTH(STMT_TEXT)` vs the cap (mirror mysql's enum), and consider the two-step
  "fetch counters broadly, fetch text per top-N `EXECUTABLE_ID`" pattern on busy caches
  (`db2-live-pkgcache.md:58`, `:336-348`, `:398-399`).
- **Grant required:** the monitoring user needs `EXECUTE ON FUNCTION SYSPROC.MON_GET_PKG_CACHE_STMT`
  (`db2-live-pkgcache.md:407-409`).

### 5.2 Activity / samples (`dbm-activity` + `dbm-samples`) — the `pg_stat_activity` analog

- **Source:** `SYSIBMADM.MON_CURRENT_SQL` (19 columns: identity + `ELAPSED_TIME_MSEC` wall-clock +
  `ACTIVITY_STATE`/`ACTIVITY_TYPE` + `STMT_TEXT`); fall back to `TABLE(MON_GET_ACTIVITY(NULL,-2))`
  joined to `MON_GET_CONNECTION` when you need `EXECUTABLE_ID`/wait-time columns
  (`db2-live-activity.md:67`, `:153-181`, `:191-209`).
- **Caveat the design must account for:** fast OLTP is invisible to point-in-time sampling — the
  sub-millisecond orders statements were never caught across 40–80 samples
  (`db2-live-activity.md:94-101`). Activity sampling is an ASH-style long-query/wait signal; the
  package cache (§5.1) is what captures every statement. Same `STMT_TEXT` obfuscation rules apply.
- **Payload:** `db2_activity` (+ optional `db2_connections`), `dbm_type:"activity"`,
  `ddtags` is a **list** here (it is a comma-joined **string** in samples/plan/fqt — do not unify)
  (`code-dbm-payload-contract.md:331-353`, `:268-269`).
- Execution plans (`dbm_type:"plan"`) are a later increment — Db2 has `EXPLAIN`/`db2exfmt` but no
  cheap per-sample plan; treat as out of scope for first fidelity.

### 5.3 Instance registration (`dbm-metadata`, `kind:"database_instance"`) — the must-have

This is **the single most important payload**: without it the host never appears as a DBM instance in
the product UI. Emit once per `database_identifier` (debounced), with `metadata.dbm = true`,
`dbms:"db2"`, `dbms_version`, `integration_version`, `port`, `database_hostname`, `ddagenthostname`
(`code-dbm-payload-contract.md:360-390`, `:600-603`). There is **no manifest flag** for DBM — it is
purely this payload + `ddsource`/`dbms` strings + `source_type_id`
(`code-dbm-payload-contract.md:564-571`).

### 5.4 Settings / schemas / health (optional first-fidelity)

- `kind:"db2_settings"` from `SYSIBMADM.DBCFG`/`DBMCFG`/registry (`db2-config-settings.md`).
- Schema collection by subclassing the base `SchemaCollector` (`SYSCAT.*`)
  (`code-dbm-payload-contract.md:410-436`).
- `dbm-health` by subclassing the base `Health` class (`code-dbm-payload-contract.md:440-468`).

---

## 6. Scaffolding/correctness gaps to clear before/while implementing

- **Version coverage.** `hatch.toml` matrix is `version=["11.1"]`; target is 12.1.4. Add `"12.1"` and
  ensure a 12.1 docker tag exists — `taskana/db2` may not publish one; switch to
  `icr.io/db2_community/db2` (`code-integration-scaffolding.md:662-665`, `:504-507`).
- **Version parser.** `parse_version` assumes `MM.mm.uuuu`; confirm 12.1.4's `SQL_DBMS_VER` still
  parses, and that the string feeds `db2_version`/`dbms_version`
  (`code-integration-scaffolding.md:669`).
- **base pin.** `pyproject.toml` pins `datadog-checks-base>=37.33.0`; DBM utilities may require a
  bump (add a changelog fragment) (`code-integration-scaffolding.md:483-485`).
- **spec.yaml DBM blocks.** Add `dbm` (bool), `query_metrics`, `query_activity`, `collect_settings`,
  `aws`/`azure`/`gcp`, `obfuscator_options`, `reported_hostname`/`exclude_hostname`,
  `database_identifier.template` — mirror the sqlserver spec — then regenerate models + example with
  `ddev -x validate config -s` then `ddev -x validate models -s`
  (`code-integration-scaffolding.md:599-609`, `:387-391`).
- **`ConfigMixin`.** The check reads raw `self.instance.get(...)`; adopt `ConfigMixin` for the nested
  DBM models (`code-integration-scaffolding.md:217-223`).
- **Fix `only_custom_queries`** to actually gate the built-ins (`code-ibm_db2-current.md:259`).
- **DBM does NOT add metadata.csv rows** — query-level data is event-platform, not metrics; only any
  self-telemetry gauges go in metadata.csv (`code-integration-scaffolding.md:621-626`).

---

## 7. Punch list (what must be added, ordered)

**P0 — DBM foundation (turns the host into a DBM instance):**

1. Subclass `DatabaseCheck`; implement identity properties (`dbms="db2"`, `dbms_version`,
   `reported_hostname`, `database_identifier`, `tags`, `cloud_metadata`). [§5; `code-dbm-payload-contract.md:592-596`]
2. Emit the `database_instance` metadata event with `metadata.dbm=true`, debounced. [§5.3]
3. Add the `dbm` master switch + cloud/identity config to `spec.yaml`; regenerate models. [§6]
4. Bump base pin if required; add `changelog.d/<PR>.added`. [§6]

**P1 — Query metrics (the `pg_stat_statements` analog, highest-value DBM signal):**

5. `Db2StatementMetrics(DBMAsyncJob)` over `MON_GET_PKG_CACHE_STMT`: runtime column introspection;
   snapshot diff keyed by `HEX(EXECUTABLE_ID)`+member+db via `StatementMetrics.compute_derivative_rows`
   with `execution_indicators=['num_exec_with_metrics']`; client-side obfuscation (strip leading
   `/*dd*/` comment, `replace_null_character=True`); re-merge by `query_signature`; us→ms unit
   normalization; gate timing on `mon_act_metrics>=BASE`; bound/flag CLOB `STMT_TEXT`. Emit `db2_rows`
   on `dbm-metrics` + FQT on `dbm-samples`. Grant `EXECUTE` on the function. [§5.1]
6. `query_metrics` config block (`enabled`, `collection_interval` default 10s, caches). [§6]

**P2 — Activity sampling (the `pg_stat_activity` analog):**

7. `Db2StatementSamples/Activity(DBMAsyncJob)` over `MON_CURRENT_SQL` (fallback `MON_GET_ACTIVITY` +
   `MON_GET_CONNECTION`): exclude the agent's own handle, obfuscate `STMT_TEXT`, emit `db2_activity`
   (+ `db2_connections`) with `ddtags` as a **list**. Document the fast-OLTP-invisibility caveat. [§5.2]
8. `query_activity` config block (`enabled`, `collection_interval` default 10s, `payload_row_limit`). [§6]

**P3 — Standard-metric breadth toward pg/mysql parity (per the map docs):**

9. Buffer-pool **writes / page-cleaning / async / I/O timing** (`map-bufferpool.md`, `map-io-disk.md`).
10. **Direct I/O** + **container/filesystem capacity** (`MON_GET_CONTAINER`) (`map-io-disk.md`).
11. **Sorting/hashing/spills** from `MON_GET_DATABASE` (`map-sorting-hashing.md`).
12. **HADR** namespace `ibm_db2.hadr.*` from `MON_GET_HADR(-1)`, with the "0 rows = not configured"
    guard (`map-hadr-replication.md`).
13. Per-table / per-index / per-connection / WLM / memory-pool metrics (longer tail).

**P4 — Robustness, settings/schema, hygiene:**

14. Connection robustness: cleaner reconnect (null `self._conn`, retry next run), per-query timeout,
    read-only enforcement (`code-ibm_db2-current.md:375-378`, `:617-618`).
15. `dbm-metadata` settings (`SYSIBMADM.DBCFG`/`DBMCFG`) and optional schema collection
    (`SchemaCollector` over `SYSCAT.*`) and `dbm-health`. [§5.4]
16. Fix `only_custom_queries` enforcement; fix infinite-log `log.available` sentinel; fix
    `bufferpool.xda.hit_percent` description; persist or accept loss of tablespace-state events.
17. Add `12.1` to the test matrix + a 12.1 docker image; add DBM unit/integration tests; verify
    `parse_version` against 12.1.4. [§6]

---

## 8. One-paragraph summary

`ibm_db2` 4.3.0 is a competent but narrow classic check: one synchronous `AgentCheck`, one persistent
`ibm_db` connection, five `MON_GET_*` table-function queries producing **49 standard metrics**
(25 of them buffer-pool), two service checks, and one tablespace-state event. Against postgres (244)
and mysql (254) it has **~20% of the metric breadth** and — the decisive gap — **zero Database
Monitoring**: no `DatabaseCheck`, no `DBMAsyncJob`, no query metrics (`MON_GET_PKG_CACHE_STMT`), no
activity samples (`MON_CURRENT_SQL`), no instance/settings/schema metadata, and no `database_instance`
event, so the host never registers as a DBM instance. The live 12.1.4 probes confirm the required Db2
sources exist and behave like their pg analogs (cumulative monotonic counters, stable
`EXECUTABLE_ID`, client-side obfuscation required). The punch list above sequences the work P0→P4,
with the `database_instance` event (P0) and `MON_GET_PKG_CACHE_STMT` query metrics (P1) as the
load-bearing first deliverables.
