# Metric Category Map: Sorting & Hashing

Raw input for the ibm_db2 fidelity implementation plan. This document maps the **sorting / hashing**
metric category (total sorts, sort overflows, hash joins, hash overflows, sort-heap usage, hash
group-bys, threshold spillage, sort-heap high-water marks) from the postgres/mysql DBM integrations
onto Db2 12.1 sources, and proposes concrete `ibm_db2.*` metric names, types, units, tags, and
version/config gating.

Target Db2: **12.1** (live container `icr.io/db2_community/db2:12.1.4.0`, DB `TESTDB`). All Db2
column lists below were captured **live on 2026-06-15** from that container via `DESCRIBE` /
`SYSCAT.COLUMNS` (commands shown in §6). All file paths absolute. Catalog `metric_type` uses the
metadata.csv vocabulary: `gauge` / `count` (a Db2 lifetime counter submitted as `monotonic_count`
is catalogued as `count`).

> Note on inputs: the task referenced several research files that do not exist in
> `/home/bits/dd/integrations-core/ibm_db2/dev-docs/db2-fidelity-plan/_research/`
> (`code-postgres-metrics.md`, `db2-monget-catalog-*.md`, `db2-sysibmadm-views.md`,
> `db2-live-monget.md`, `db2-live-sysibmadm.md`). I substituted the files that DO exist
> (`code-mysql-metrics.md`, `code-ibm_db2-current.md`, `db2-live-pkgcache.md`, `db2-live-activity.md`,
> `db2-config-settings.md`) and captured the missing Db2-source facts **directly from the live
> 12.1.4 container** (§6). The mysql/postgres/ibm_db2 `metadata.csv` files were all read in full.

---

## 0. TL;DR / load-bearing facts

1. **This category is essentially absent from the current `ibm_db2` integration.** The check has
   ZERO sort/hash metrics today (`metadata.csv` rows 2-50, none mention sort/hash;
   `code-ibm_db2-current.md` §4 confirms only INSTANCE/DATABASE/BUFFERPOOL/TABLESPACE/TRANSACTION_LOG
   queries, none selecting any `*SORT*`/`*HASH*` column). This is the single biggest pg/mysql gap
   in this category.

2. **Db2 has FAR richer sort/hash instrumentation than pg or mysql.** Postgres exposes only
   `temp_files`/`temp_bytes` (sort/hash spill to disk) at db level; mysql exposes
   `Sort_*`/`Created_tmp_*` at server level. Db2 exposes ~30 distinct sort+hash monitor elements
   at **database, workload, connection, and per-statement** granularity (live-confirmed §6).

3. **Primary source = `MON_GET_DATABASE(-1)`** for the database-wide aggregate of this whole
   category (one row, aggregated across members with `-1`). It carries every counter pg/mysql have
   an analog for plus Db2-native extras. Live-confirmed populated: `TOTAL_SORTS=63409`,
   `SORT_OVERFLOWS=35`, `TOTAL_HASH_JOINS=1653`, `SORT_SHRHEAP_TOP=912`,
   `TOTAL_SECTION_SORT_TIME=44182` (§6.1).

4. **Per-statement source = `MON_GET_PKG_CACHE_STMT`** (the `pg_stat_statements` analog) carries the
   same family per cached statement (`db2-live-pkgcache.md` §6e). Those go in the DBM **query
   metrics** payload (`db2.queries.*`-style, sibling category — NOT this metrics-check category) but
   are noted here for completeness because they are the per-query-signature analog of
   `mysql.queries.sort_*` / `postgres.queries.temp_blks_*`.

5. **Sort-heap configuration** (`sortheap`, `sheapthres_shr`, `sheapthres`) is read from
   `SYSIBMADM.DBCFG` / `SYSIBMADM.DBMCFG`, NOT from a MON_GET function. Live values:
   `sortheap=2133 (AUTOMATIC)`, `sheapthres_shr=42671 (AUTOMATIC)` (per-db, 4KB-page units),
   `sheapthres=0 (NONE)` (instance; 0 ⇒ shared sort memory model in effect) (§6.3). These are the
   capacity denominators for sort-heap utilization.

6. **Unit caveat:** the `*_TIME` sort columns (`TOTAL_SECTION_SORT_TIME`,
   `TOTAL_SECTION_SORT_PROC_TIME`) are **milliseconds**. The heap columns
   (`SORT_HEAP_ALLOCATED`, `SORT_SHRHEAP_ALLOCATED`, `SORT_SHRHEAP_TOP`, `SORT_HEAP_TOP`,
   `SORT_CONSUMER_*`) are in **4KB memory pages** (same unit as `sortheap`/`sheapthres_shr` config).
   Sort/hash *count* columns are dimensionless lifetime counters. (Confirm each per IBM element
   reference, §7.)

7. **All counters are cumulative-since-database-activation** (reset on db deactivate/reactivate).
   → submit as `monotonic_count` (catalogued `count`). The high-water `*_TOP` and `ACTIVE_*`
   columns are point-in-time → `gauge`.

8. **Authority:** `SYSMON` (or `DATAACCESS`/`DBADM`/`SQLADM`, or `EXECUTE` on the routine) is
   required to call `MON_GET_DATABASE` / `MON_GET_WORKLOAD` / `MON_GET_CONNECTION`. Same as the
   existing five queries (`code-ibm_db2-current.md` §13). No extra grant needed beyond what the
   integration already documents.

9. **No config gating required for the counts.** Sort/hash *count* + heap elements populate
   regardless of `mon_*_metrics` settings (they are request/object-level, always-on). The
   `TOTAL_SECTION_SORT_TIME` / `..._PROC_TIME` timing columns require `mon_act_metrics >= BASE`
   (live = `BASE`, satisfied — `db2-live-pkgcache.md` §8). Gate only the *timing-derived* metrics on
   `mon_act_metrics <> 'NONE'`.

---

## 1. The pg/mysql side of this category (exact existing metric names)

### 1.1 MySQL (from `/home/bits/dd/integrations-core/mysql/metadata.csv`)
Server-global (Paradigm A, `SHOW GLOBAL STATUS` → `OPTIONAL_STATUS_VARS`, gated by
`extra_status_metrics`):

| mysql metric | type | unit/per | server var | meaning |
|---|---|---|---|---|
| `mysql.performance.sort_merge_passes` | gauge (rate) | operation/second | `Sort_merge_passes` | multi-pass merge sorts (disk-spill sort signal) — the closest analog to Db2 `SORT_OVERFLOWS` |
| `mysql.performance.sort_range` | gauge (rate) | operation/second | `Sort_range` | sorts done with a range |
| `mysql.performance.sort_rows` | gauge (rate) | operation/second | `Sort_rows` | rows sorted |
| `mysql.performance.sort_scan` | gauge (rate) | operation/second | `Sort_scan` | sorts done via table scan |
| `mysql.performance.created_tmp_tables` | gauge (rate) | table/second | `Created_tmp_tables` | in-memory temp tables (hash/group-by spill into temp) |
| `mysql.performance.created_tmp_disk_tables` | gauge (rate) | table/second | `Created_tmp_disk_tables` | **on-disk** temp tables — hash/sort overflow analog |
| `mysql.performance.created_tmp_files` | gauge (rate) | file/second | `Created_tmp_files` | temp files created |

DBM per-query (Paradigm: statement digest):

| mysql metric | type | meaning |
|---|---|---|
| `mysql.queries.sort_merge_passes` | count | per-query multi-pass (disk) sorts |
| `mysql.queries.sort_range` | count | per-query range sorts |
| `mysql.queries.sort_rows` | count | per-query rows sorted |
| `mysql.queries.sort_scan` | count | per-query full-scan sorts |
| `mysql.queries.created_tmp_tables` | count | per-query in-memory temp tables |
| `mysql.queries.created_tmp_disk_tables` | count | per-query on-disk temp tables |

> mysql has **no** dedicated "hash join" metric (MySQL hash joins are not separately counted in
> SHOW STATUS); hash work surfaces only as temp tables. Db2 counts hash joins/loops/grpbys
> explicitly — Db2 is richer here.

### 1.2 Postgres (from `/home/bits/dd/integrations-core/postgres/metadata.csv`)
Postgres does NOT expose sort/hash operation counts at all. Its only sort/hash-category signal is
disk-spill of sort/hash work (and other temp usage) at the database level:

| postgres metric | type | unit/per | source | meaning |
|---|---|---|---|---|
| `postgresql.temp_bytes` | rate | byte/second | `pg_stat_database.temp_bytes` | bytes written to temp files by queries (sort/hash spill) |
| `postgresql.temp_files` | rate | file/second | `pg_stat_database.temp_files` | temp files created (sort/hash spill) |

DBM per-query (from `pg_stat_statements`, the `postgresql.queries.*` family):

| postgres metric | type | meaning |
|---|---|---|
| `postgresql.queries.temp_blks_read` | count (block) | per-query temp blocks read (sort/hash spill read-back) |
| `postgresql.queries.temp_blks_written` | count (block) | per-query temp blocks written (sort/hash spill) |

> postgres has **no** sort-count, no sort-overflow-count, no hash-join-count, no sort-heap concept
> (it uses `work_mem` per-node, not a shared sort heap). Its category is purely "did sort/hash spill
> to temp, and how much". Db2's `SORT_OVERFLOWS` / `HASH_JOIN_OVERFLOWS` are the conceptual analog of
> "spilled", and Db2's sort-heap-allocated columns are the analog of `work_mem` pressure.

---

## 2. The Db2 source of truth (live-confirmed)

### 2.1 `MON_GET_DATABASE(-1)` — sort/hash columns (PRIMARY, db-wide aggregate)
Live `DESCRIBE select * from table(mon_get_database(-1))` filtered to `SORT|HASH|SHEAP`
(§6.1). All BIGINT. One row (member `-1` aggregates all members).

| Db2 column | category | semantics | unit |
|---|---|---|---|
| `TOTAL_SORTS` | sort count | total sorts executed | count (cumulative) |
| `SORT_OVERFLOWS` | sort spill | sorts that ran out of sort heap and spilled to a temp table | count |
| `POST_THRESHOLD_SORTS` | sort spill | private sorts requested after `sheapthres` exceeded (got reduced heap) | count |
| `POST_SHRTHRESHOLD_SORTS` | sort spill | sorts requested after **shared** sort-heap threshold (`sheapthres_shr`) exceeded | count |
| `TOTAL_SECTION_SORTS` | sort count | sorts at the section (statement-execution) level | count |
| `TOTAL_SECTION_SORT_TIME` | sort time | total elapsed time spent in section sorts | **millisecond** |
| `TOTAL_SECTION_SORT_PROC_TIME` | sort time | CPU/processing time portion of section sorts | **millisecond** |
| `TOTAL_HASH_JOINS` | hash count | total hash joins executed | count |
| `TOTAL_HASH_LOOPS` | hash detail | hash-loop fallbacks (a hash join that could not complete in one pass — inefficiency signal) | count |
| `HASH_JOIN_OVERFLOWS` | hash spill | hash joins where hash table exceeded sort heap and spilled | count |
| `HASH_JOIN_SMALL_OVERFLOWS` | hash spill | hash-join overflows that exceeded heap by <10% (tunable signal) | count |
| `POST_THRESHOLD_HASH_JOINS` | hash spill | hash joins requested after `sheapthres` exceeded | count |
| `POST_SHRTHRESHOLD_HASH_JOINS` | hash spill | hash joins requested after shared threshold exceeded | count |
| `TOTAL_HASH_GRPBYS` | hash count | total hash GROUP BY operations | count |
| `HASH_GRPBY_OVERFLOWS` | hash spill | hash GROUP BYs that overflowed sort heap | count |
| `POST_THRESHOLD_HASH_GRPBYS` | hash spill | hash GROUP BYs after threshold exceeded | count |
| `TQ_SORT_HEAP_REQUESTS` | sort heap | table-queue sort-heap requests (DPF/parallel) | count |
| `TQ_SORT_HEAP_REJECTIONS` | sort heap | table-queue sort-heap requests rejected (heap pressure) | count |
| `ACTIVE_SORTS` | gauge | sorts currently active (point-in-time) | count (instantaneous) |
| `ACTIVE_SORTS_TOP` | gauge HWM | high-water mark of concurrent active sorts | count |
| `ACTIVE_HASH_JOINS` | gauge | hash joins currently active | count |
| `ACTIVE_HASH_JOINS_TOP` | gauge HWM | HWM of concurrent active hash joins | count |
| `ACTIVE_HASH_GRPBYS` | gauge | hash GROUP BYs currently active | count |
| `ACTIVE_HASH_GRPBYS_TOP` | gauge HWM | HWM of concurrent active hash GROUP BYs | count |
| `ACTIVE_SORT_CONSUMERS` | gauge | sort-heap consumers currently active | count |
| `ACTIVE_SORT_CONSUMERS_TOP` | gauge HWM | HWM of concurrent sort consumers | count |
| `SORT_HEAP_ALLOCATED` | gauge | total private sort-heap memory currently allocated | **page (4KB)** |
| `SORT_HEAP_TOP` | gauge HWM | private sort-heap high-water mark | page (4KB) |
| `SORT_SHRHEAP_ALLOCATED` | gauge | shared sort-heap memory currently allocated | **page (4KB)** |
| `SORT_SHRHEAP_TOP` | gauge HWM | shared sort-heap high-water mark | page (4KB) |
| `SORT_CONSUMER_HEAP_TOP` | gauge HWM | largest single private sort-heap consumer | page (4KB) |
| `SORT_CONSUMER_SHRHEAP_TOP` | gauge HWM | largest single shared sort-heap consumer | page (4KB) |

### 2.2 `MON_GET_WORKLOAD(NULL,-1)` — same family, per-workload (OPTIONAL, finer granularity)
Live `DESCRIBE` (§6.2) confirmed it carries the identical sort/hash column set as MON_GET_DATABASE
PLUS `SORT_SHRHEAP_UTILIZATION` (a percentage — workload-only). Tag by `WORKLOAD_NAME`. Use this only
if per-workload sort/hash breakdown is wanted (cardinality = number of WLM workloads; on the default
config there are only a handful: `SYSDEFAULTUSERWORKLOAD`, `SYSDEFAULTADMWORKLOAD`, etc.).

### 2.3 `MON_GET_CONNECTION(NULL,-1)` — same family, per-connection (OPTIONAL, high cardinality)
Live `DESCRIBE` (§6.4) confirmed it carries the same sort/hash columns. **Cardinality risk** — one
row per active connection. NOT recommended for steady-state metrics; if surfaced, cap/aggregate.
Better used in the DBM activity/sample path than as a metric.

### 2.4 `SYSIBMADM.SNAPDB` — legacy snapshot view (ALTERNATIVE, db-wide)
Live `SYSCAT.COLUMNS` (§6.5) shows SNAPDB exposes a subset: `TOTAL_SORTS`, `SORT_OVERFLOWS`,
`POST_SHRTHRESHOLD_SORTS`, `ACTIVE_SORTS`, `ACTIVE_HASH_JOINS`, `TOTAL_HASH_JOINS`,
`TOTAL_HASH_LOOPS`, `HASH_JOIN_OVERFLOWS`, `HASH_JOIN_SMALL_OVERFLOWS`, `POST_SHRTHRESHOLD_HASH_JOINS`,
`SORT_HEAP_ALLOCATED`, `SORT_SHRHEAP_ALLOCATED`, `SORT_SHRHEAP_TOP`, **`TOTAL_SORT_TIME`**.
Prefer `MON_GET_DATABASE` (MON_GET is the supported modern interface; SNAPDB is legacy and a heavier
view). SNAPDB is listed only as a fallback / for installs that restrict MON_GET. SNAPDB has
`TOTAL_SORT_TIME` (a single combined sort-time column) where MON_GET splits section sort time.

### 2.5 `SYSIBMADM.MON_DB_SUMMARY` — pre-computed ratios (ALTERNATIVE / supplement)
Live (§6.6): the ONLY sort/hash column is **`SECTION_SORT_PROC_TIME_PERCENT`** (DECIMAL, live=`0.31`)
— the percentage of total processing time spent in section sorts. This is a useful ready-made
**health ratio** (no client-side division needed). Consider emitting it as a gauge alongside the raw
counters. (The rest of the sort detail in MON_DB_SUMMARY is just the section-sort-time columns also
in MON_GET_DATABASE.)

### 2.6 Sort-heap CONFIG (capacity denominators) — `SYSIBMADM.DBCFG` / `DBMCFG`
Not MON_GET. Read once per run (mirror the postgres/mysql "settings cache" pattern;
`db2-config-settings.md` §1-2). Live values (§6.3):

| param | view | live value | unit | meaning |
|---|---|---|---|---|
| `sortheap` | `SYSIBMADM.DBCFG` | `2133` (AUTOMATIC) | page (4KB) | per-sort private sort-heap size |
| `sheapthres_shr` | `SYSIBMADM.DBCFG` | `42671` (AUTOMATIC) | page (4KB) | shared sort-heap threshold (the cap behind `POST_SHRTHRESHOLD_*`) |
| `sheapthres` | `SYSIBMADM.DBMCFG` | `0` (NONE) | page (4KB) | instance private sort-heap threshold; `0` ⇒ shared sort-memory model active |

Utilization = `SORT_SHRHEAP_ALLOCATED / sheapthres_shr * 100` (compute client-side, gauge percent),
mirroring how the existing check computes `tablespace.utilized` / `log.utilized`. Note both config
values are `AUTOMATIC` (STMM-managed) so the denominator can move — read it fresh each run.

---

## 3. PROPOSED `ibm_db2.*` MAPPING TABLE

Naming convention: this category has **no existing `ibm_db2.*` metrics**, so a new `ibm_db2.sort.*`
and `ibm_db2.hash.*` namespace is proposed, consistent with the existing flat dotted style
(`ibm_db2.lock.*`, `ibm_db2.row.*`, `ibm_db2.log.*`). Counters → `count` (submitted
`monotonic_count`); point-in-time/HWM/ratios → `gauge`. All db-wide metrics carry the global
`db:<db>` tag (auto-added, `code-ibm_db2-current.md` §5); workload-scoped metrics add
`workload:<name>`.

Columns: **pg/mysql analog** | **Db2 source (function + exact column)** | **proposed metric** |
**type** | **unit** | **tags** | **notes / gating**

### 3.1 Sorts (db-wide, from `MON_GET_DATABASE(-1)`)

| pg/mysql analog | Db2 source column | proposed `ibm_db2.*` | type | unit | tags | notes |
|---|---|---|---|---|---|---|
| `mysql.performance.sort_rows` (loosely) / no pg | `MON_GET_DATABASE.TOTAL_SORTS` | `ibm_db2.sort.total` | count | sort | db | core sort count |
| `mysql.performance.sort_merge_passes`, `postgresql.temp_files` (spill) | `SORT_OVERFLOWS` | `ibm_db2.sort.overflows` | count | sort | db | **key spill signal**; orientation -1 |
| no direct pg/mysql | `POST_THRESHOLD_SORTS` | `ibm_db2.sort.post_threshold` | count | sort | db | private-heap threshold pressure; orientation -1 |
| `postgresql.temp_files`/`temp_bytes` (loose) | `POST_SHRTHRESHOLD_SORTS` | `ibm_db2.sort.post_shrthreshold` | count | sort | db | shared-heap threshold pressure; orientation -1 |
| no analog | `TOTAL_SECTION_SORTS` | `ibm_db2.sort.section.total` | count | sort | db | section-level sorts |
| no analog | `TOTAL_SECTION_SORT_TIME` | `ibm_db2.sort.section.time` | count | millisecond | db | **ms**; gate on `mon_act_metrics<>'NONE'` |
| no analog | `TOTAL_SECTION_SORT_PROC_TIME` | `ibm_db2.sort.section.proc_time` | count | millisecond | db | **ms**; same gating |
| no analog | `TQ_SORT_HEAP_REQUESTS` | `ibm_db2.sort.tq_heap_requests` | count | request | db | DPF/parallel only meaningful; ~0 on single member |
| no analog | `TQ_SORT_HEAP_REJECTIONS` | `ibm_db2.sort.tq_heap_rejections` | count | request | db | heap-pressure signal; orientation -1 |
| no analog (point-in-time) | `ACTIVE_SORTS` | `ibm_db2.sort.active` | gauge | sort | db | instantaneous |
| no analog | `ACTIVE_SORTS_TOP` | `ibm_db2.sort.active.max` | gauge | sort | db | HWM since activation |
| no analog | `ACTIVE_SORT_CONSUMERS` | `ibm_db2.sort.consumers.active` | gauge | consumer | db | instantaneous |
| no analog | `ACTIVE_SORT_CONSUMERS_TOP` | `ibm_db2.sort.consumers.active.max` | gauge | consumer | db | HWM |

### 3.2 Sort-heap memory (db-wide, from `MON_GET_DATABASE(-1)` + DBCFG)

| pg/mysql analog | Db2 source | proposed `ibm_db2.*` | type | unit | tags | notes |
|---|---|---|---|---|---|---|
| `work_mem` pressure (postgres, loose) | `SORT_HEAP_ALLOCATED` | `ibm_db2.sort.heap.allocated` | gauge | page | db | 4KB pages; private sort heap in use |
| no analog | `SORT_HEAP_TOP` | `ibm_db2.sort.heap.allocated.max` | gauge | page | db | HWM |
| no analog | `SORT_SHRHEAP_ALLOCATED` | `ibm_db2.sort.shrheap.allocated` | gauge | page | db | shared sort heap in use |
| no analog | `SORT_SHRHEAP_TOP` | `ibm_db2.sort.shrheap.allocated.max` | gauge | page | db | HWM (live=912) |
| no analog | `SORT_CONSUMER_HEAP_TOP` | `ibm_db2.sort.consumer.heap.max` | gauge | page | db | largest single private consumer |
| no analog | `SORT_CONSUMER_SHRHEAP_TOP` | `ibm_db2.sort.consumer.shrheap.max` | gauge | page | db | largest single shared consumer |
| `sortheap` config | `DBCFG.sortheap` | `ibm_db2.sort.heap.configured` | gauge | page | db | capacity denominator; AUTOMATIC-managed |
| `sheapthres_shr` config | `DBCFG.sheapthres_shr` | `ibm_db2.sort.shrheap.threshold` | gauge | page | db | shared-heap cap (live=42671) |
| derived (`SORT_SHRHEAP_ALLOCATED/sheapthres_shr*100`) | computed | `ibm_db2.sort.shrheap.utilized` | gauge | percent | db | mirrors `tablespace.utilized` pattern; orientation -1 |

### 3.3 Hashing (db-wide, from `MON_GET_DATABASE(-1)`)

| pg/mysql analog | Db2 source column | proposed `ibm_db2.*` | type | unit | tags | notes |
|---|---|---|---|---|---|---|
| no analog (mysql/pg have no hash-join count) | `TOTAL_HASH_JOINS` | `ibm_db2.hash.joins.total` | count | join | db | core hash-join count (live=1653) |
| no analog | `TOTAL_HASH_LOOPS` | `ibm_db2.hash.loops.total` | count | loop | db | hash-loop fallback (inefficiency); orientation -1 |
| `mysql.performance.created_tmp_disk_tables` / `postgresql.temp_files` (loose) | `HASH_JOIN_OVERFLOWS` | `ibm_db2.hash.joins.overflows` | count | overflow | db | **key spill signal**; orientation -1 |
| no analog | `HASH_JOIN_SMALL_OVERFLOWS` | `ibm_db2.hash.joins.small_overflows` | count | overflow | db | <10%-over signal (tune sortheap); orientation -1 |
| no analog | `POST_THRESHOLD_HASH_JOINS` | `ibm_db2.hash.joins.post_threshold` | count | join | db | threshold pressure; orientation -1 |
| no analog | `POST_SHRTHRESHOLD_HASH_JOINS` | `ibm_db2.hash.joins.post_shrthreshold` | count | join | db | shared-threshold pressure; orientation -1 |
| no analog | `TOTAL_HASH_GRPBYS` | `ibm_db2.hash.grpbys.total` | count | operation | db | hash GROUP BY count |
| `mysql.performance.created_tmp_disk_tables` (loose) | `HASH_GRPBY_OVERFLOWS` | `ibm_db2.hash.grpbys.overflows` | count | overflow | db | hash GROUP BY spill; orientation -1 |
| no analog | `POST_THRESHOLD_HASH_GRPBYS` | `ibm_db2.hash.grpbys.post_threshold` | count | operation | db | threshold pressure; orientation -1 |
| no analog (point-in-time) | `ACTIVE_HASH_JOINS` | `ibm_db2.hash.joins.active` | gauge | join | db | instantaneous |
| no analog | `ACTIVE_HASH_JOINS_TOP` | `ibm_db2.hash.joins.active.max` | gauge | join | db | HWM |
| no analog | `ACTIVE_HASH_GRPBYS` | `ibm_db2.hash.grpbys.active` | gauge | operation | db | instantaneous |
| no analog | `ACTIVE_HASH_GRPBYS_TOP` | `ibm_db2.hash.grpbys.active.max` | gauge | operation | db | HWM |

### 3.4 Ready-made ratio (from `SYSIBMADM.MON_DB_SUMMARY`)

| pg/mysql analog | Db2 source | proposed `ibm_db2.*` | type | unit | tags | notes |
|---|---|---|---|---|---|---|
| no analog | `MON_DB_SUMMARY.SECTION_SORT_PROC_TIME_PERCENT` | `ibm_db2.sort.section.proc_time_percent` | gauge | percent | db | live=0.31; orientation -1; optional supplement to the raw ms counters in 3.1 |

### 3.5 Per-workload variant (OPTIONAL — gate behind a config flag)
Re-emit the §3.1/§3.2/§3.3 metrics from `MON_GET_WORKLOAD(NULL,-1)` with an added `workload:<name>`
tag, PLUS the workload-only `SORT_SHRHEAP_UTILIZATION` column:

| Db2 source | proposed `ibm_db2.*` | type | unit | tags | notes |
|---|---|---|---|---|---|
| `MON_GET_WORKLOAD.SORT_SHRHEAP_UTILIZATION` | `ibm_db2.sort.shrheap.utilized` (workload-tagged) | gauge | percent | db, workload | server-computed; reuse same metric name as 3.2 derived, distinguished by `workload` tag |

Recommendation: ship §3.1-3.4 (db-wide) in phase 1; make §3.5 (per-workload) opt-in like mysql's
`extra_*` flags / postgres `relations` (cardinality = #WLM workloads, low by default but unbounded if
the customer defines many).

---

## 4. Metrics with NO Db2 equivalent (flag for the plan)

- **`mysql.performance.sort_range` / `sort_scan`** (sort access-method breakdown): Db2 does NOT break
  sorts down by access method (range vs scan). No Db2 column. **No equivalent — drop.**
- **`mysql.performance.created_tmp_files` / `created_tmp_tables`**: Db2 has no "temp table created"
  counter in this category. The conceptual analog is the *overflow* counters (`SORT_OVERFLOWS`,
  `HASH_*_OVERFLOWS`) which count spills into the temp table space, plus temp-bufferpool reads
  (a *different* metric category — bufferpool — already partially covered by
  `ibm_db2.bufferpool.*` with the `POOL_TEMP_*` columns). **No 1:1 equivalent;** closest is the
  overflow family already mapped in §3.
- **`postgresql.temp_bytes`** (bytes spilled): Db2 has no direct "sort/hash bytes spilled to temp"
  counter at db level. The byte-volume of spill is observable only indirectly via temp-bufferpool
  page reads/writes (`POOL_TEMP_*`, bufferpool category) — **flag as not directly mappable in this
  category.**

## 5. Db2-native metrics with NO pg/mysql analog worth ADDING

Everything in §3 except `sort.total`/`sort.overflows`/`hash.*.overflows` is effectively Db2-native
(pg/mysql have no analog). The highest-value Db2-native additions (recommend including):
- **Hash-join family** (`hash.joins.total/overflows/loops`, `hash.grpbys.*`) — pg/mysql cannot count
  hash joins at all; this is a genuine Db2 observability advantage and a primary OLAP tuning signal.
- **Threshold-pressure counters** (`*.post_threshold`, `*.post_shrthreshold`) — these directly tell
  you `sheapthres`/`sheapthres_shr` is being exceeded (the #1 actionable sort-heap-tuning signal;
  no pg/mysql analog).
- **Sort-heap HWM gauges** (`sort.shrheap.allocated.max`, `sort.consumer.*.max`) — sizing signal for
  STMM / `sheapthres_shr` tuning.
- **`sort.shrheap.utilized` (derived percent)** — the single most dashboard-friendly metric; mirrors
  the check's existing `tablespace.utilized` / `log.utilized` design.

---

## 6. Live evidence (commands + raw output, container `db2-primary`, Db2 12.1.4, DB TESTDB, 2026-06-15)

Invocation pattern (cwd resets between calls; `su -` required):
`docker exec db2-primary su - db2inst1 -c "db2 connect to testdb > /dev/null; db2 -x \"<SQL>\"; db2 connect reset > /dev/null"`

### 6.1 MON_GET_DATABASE sort/hash columns + live values
`db2 "describe select * from table(mon_get_database(-1))" | grep -iE 'sort|hash|sheap'` → all BIGINT:
`ACTIVE_SORTS, ACTIVE_HASH_JOINS, TOTAL_SECTION_SORT_TIME, TOTAL_SECTION_SORT_PROC_TIME,
TOTAL_SECTION_SORTS, TOTAL_SORTS, POST_THRESHOLD_SORTS, POST_SHRTHRESHOLD_SORTS, SORT_OVERFLOWS,
TQ_SORT_HEAP_REQUESTS, TQ_SORT_HEAP_REJECTIONS, TOTAL_HASH_JOINS, TOTAL_HASH_LOOPS,
HASH_JOIN_OVERFLOWS, HASH_JOIN_SMALL_OVERFLOWS, POST_SHRTHRESHOLD_HASH_JOINS,
POST_THRESHOLD_HASH_JOINS, TOTAL_HASH_GRPBYS, HASH_GRPBY_OVERFLOWS, POST_THRESHOLD_HASH_GRPBYS,
ACTIVE_HASH_GRPBYS, SORT_HEAP_ALLOCATED, SORT_SHRHEAP_ALLOCATED, SORT_SHRHEAP_TOP,
ACTIVE_HASH_GRPBYS_TOP, ACTIVE_HASH_JOINS_TOP, ACTIVE_SORT_CONSUMERS, ACTIVE_SORT_CONSUMERS_TOP,
ACTIVE_SORTS_TOP, SORT_CONSUMER_HEAP_TOP, SORT_CONSUMER_SHRHEAP_TOP, SORT_HEAP_TOP`.

Live sample (`total_sorts, sort_overflows, post_threshold_sorts, post_shrthreshold_sorts,
total_hash_joins, hash_join_overflows, hash_join_small_overflows, total_hash_grpbys,
hash_grpby_overflows, active_sorts, sort_shrheap_allocated, sort_shrheap_top, sort_heap_allocated,
total_section_sort_time, total_section_sorts`):
`63409 | 35 | 0 | 0 | 1653 | 0 | 0 | 0 | 0 | 0 | 5 | 912 | 0 | 44182 | 63409`
→ proves the columns populate on the single-member community image (sorts and hash joins both
non-zero; overflows occurring; shared sort-heap HWM = 912 pages).

### 6.2 MON_GET_WORKLOAD sort/hash columns
`db2 "describe select * from table(mon_get_workload(NULL,-1))" | grep -iE 'SORT|HASH'` → same set as
6.1 PLUS `SORT_SHRHEAP_UTILIZATION` (workload-only percentage). Tag by `WORKLOAD_NAME`.

### 6.3 Sort-heap config
`select name,value,value_flags from sysibmadm.dbcfg where name in ('sortheap','sheapthres_shr') and member=0`
→ `sheapthres_shr=42671 AUTOMATIC`, `sortheap=2133 AUTOMATIC`.
`select name,value,value_flags from sysibmadm.dbmcfg where name='sheapthres'` → `sheapthres=0 NONE`.

### 6.4 MON_GET_CONNECTION
`db2 "describe select * from table(mon_get_connection(NULL,-1))" | grep -iE 'SORT|HASH'` → same
sort/hash column family present (per-connection). High cardinality — not recommended as a metric.

### 6.5 SYSIBMADM.SNAPDB
`select colname from syscat.columns where tabschema='SYSIBMADM' and tabname='SNAPDB' and (colname like
'%SORT%' or colname like '%HASH%' or colname like '%SHEAP%')` →
`ACTIVE_HASH_JOINS, ACTIVE_SORTS, HASH_JOIN_OVERFLOWS, HASH_JOIN_SMALL_OVERFLOWS,
POST_SHRTHRESHOLD_HASH_JOINS, POST_SHRTHRESHOLD_SORTS, SORT_HEAP_ALLOCATED, SORT_OVERFLOWS,
SORT_SHRHEAP_ALLOCATED, SORT_SHRHEAP_TOP, TOTAL_HASH_JOINS, TOTAL_HASH_LOOPS, TOTAL_SORTS,
TOTAL_SORT_TIME`. (Legacy fallback only.)

### 6.6 SYSIBMADM.MON_DB_SUMMARY
`select colname,typename from syscat.columns where tabschema='SYSIBMADM' and tabname='MON_DB_SUMMARY'
and (colname like '%SORT%' or colname like '%HASH%')` → `SECTION_SORT_PROC_TIME_PERCENT DECIMAL`.
Live value: `select section_sort_proc_time_percent from sysibmadm.mon_db_summary` → `0.31`.

### 6.7 Per-statement (sibling DBM category, for cross-reference)
From `db2-live-pkgcache.md` §6e (`MON_GET_PKG_CACHE_STMT`, all BIGINT):
`TOTAL_SECTION_SORTS, TOTAL_SORTS, POST_THRESHOLD_SORTS, POST_SHRTHRESHOLD_SORTS, SORT_OVERFLOWS,
TOTAL_HASH_JOINS, TOTAL_HASH_LOOPS, HASH_JOIN_OVERFLOWS, HASH_JOIN_SMALL_OVERFLOWS,
POST_SHRTHRESHOLD_HASH_JOINS, POST_THRESHOLD_HASH_JOINS, TOTAL_HASH_GRPBYS, HASH_GRPBY_OVERFLOWS,
POST_THRESHOLD_HASH_GRPBYS, TOTAL_OLAP_FUNCS, OLAP_FUNC_OVERFLOWS, POST_THRESHOLD_OLAP_FUNCS,
TQ_SORT_HEAP_REQUESTS, TQ_SORT_HEAP_REJECTIONS` plus `TOTAL_SECTION_SORT_TIME`,
`TOTAL_SECTION_SORT_PROC_TIME` (ms). These belong to the DBM **query-metrics** payload (per
`query_signature`), the analog of `mysql.queries.sort_*` / `postgresql.queries.temp_blks_*` — handle
in that category's plan, NOT the metrics check. Note OLAP-window-function sort spill
(`OLAP_FUNC_OVERFLOWS`) is also a per-statement-only Db2 extra with no pg/mysql analog.

---

## 7. Citations

Code / catalog (absolute paths):
- `/home/bits/dd/integrations-core/ibm_db2/metadata.csv` — current 49 metrics; NO sort/hash rows.
- `/home/bits/dd/integrations-core/mysql/metadata.csv` — `mysql.performance.sort_*` (rows 200-203),
  `created_tmp_*` (155-157), `mysql.queries.sort_*` (237-240).
- `/home/bits/dd/integrations-core/postgres/metadata.csv` — `postgresql.temp_bytes`/`temp_files`
  (rows 199-200), `postgresql.queries.temp_blks_*` (124-125).
- `/home/bits/dd/integrations-core/ibm_db2/dev-docs/db2-fidelity-plan/_research/code-ibm_db2-current.md`
  — §4 (no sort/hash queries today), §5 (tags), §13 (authorities).
- `/home/bits/dd/integrations-core/ibm_db2/dev-docs/db2-fidelity-plan/_research/code-mysql-metrics.md`
  — `OPTIONAL_STATUS_VARS` (sort vars), const→metric mapping, metric_type discipline (§3, §10).
- `/home/bits/dd/integrations-core/ibm_db2/dev-docs/db2-fidelity-plan/_research/db2-live-pkgcache.md`
  — §6e per-statement sort/hash columns; §8 `mon_act_metrics=BASE`.
- `/home/bits/dd/integrations-core/ibm_db2/dev-docs/db2-fidelity-plan/_research/db2-config-settings.md`
  — §1-2 DBMCFG/DBCFG (`sheapthres`, `sortheap`).
- Live container probes: §6 above (captured 2026-06-15, `db2-primary`, `icr.io/db2_community/db2:12.1.4.0`).

IBM docs (Db2 12.1 — note: ibm.com returned HTTP 403 to the automated fetcher, consistent with
`db2-live-pkgcache.md` §10; URLs are correct, verify in a browser):
- MON_GET_DATABASE table function: https://www.ibm.com/docs/en/db2/12.1?topic=mtf-mon-get-database-table-function
- MON_GET_WORKLOAD table function: https://www.ibm.com/docs/en/db2/12.1?topic=mtf-mon-get-workload-table-function
- MON_GET_CONNECTION table function: https://www.ibm.com/docs/en/db2/12.1?topic=mtf-mon-get-connection-table-function
- MON_DB_SUMMARY administrative view: https://www.ibm.com/docs/en/db2/12.1?topic=views-mon-db-summary-administrative-view
- SNAPDB administrative view: https://www.ibm.com/docs/en/db2/12.1?topic=views-snapdb-administrative-view-snapshot-database-information
- Monitor element reference (units/semantics for `total_sorts`, `sort_overflows`,
  `sort_shrheap_allocated`, `post_shrthreshold_sorts`, `total_hash_joins`, `hash_join_overflows`,
  etc.): https://www.ibm.com/docs/en/db2/12.1?topic=monitoring-monitor-elements
- sortheap / sheapthres_shr / sheapthres cfg parameters:
  https://www.ibm.com/docs/en/db2/12.1?topic=parameters-sortheap-sort-heap-size
  https://www.ibm.com/docs/en/db2/12.1?topic=parameters-sheapthres-shr-sort-heap-threshold-shared-sorts
  https://www.ibm.com/docs/en/db2/12.1?topic=parameters-sheapthres-sort-heap-threshold
