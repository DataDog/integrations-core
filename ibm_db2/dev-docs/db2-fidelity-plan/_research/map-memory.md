# Memory metric-category mapping — ibm_db2 fidelity plan

Maps the **memory** category (instance/database memory sets + pools, sort heap, lock list,
package cache, catalog cache, bufferpool memory) from the postgres/mysql metric model onto
Db2 12.1 monitoring sources. Goal: bring `ibm_db2` to pg/mysql fidelity for "how much memory
has Db2 reserved, and which heap is growing / under pressure".

## Db2 memory model in one paragraph

Db2 memory is a two-level tree. **Memory SETS** are the top-level OS reservations Db2 makes
(`DATABASE`, `DBMS`/instance, `APPLICATION`, `BUFFERPOOL`, `FCM`, `FMP`, `PRIVATE`). Within
each set live **memory POOLS** — the individual heaps (`BP` buffer-pool heap, `LOCKMGR` lock
list, `PACKAGE_CACHE`, `CAT_CACHE` catalog cache, `SORTHEAP`/`SHARED_SORTHEAP`, `UTILITY`,
`DATABASE`, `APPL_CONTROL`, `APP_GROUP`, `XMLCACHE`, etc.). The two table functions are:

- **`MON_GET_MEMORY_SET(memory_set_type, db_name, member)`** — per-set committed/used sizes.
  The coarse "OS-committed memory per area" layer. **NOT in the live DESCRIBE dump** — column
  list below is general Db2 12.1 knowledge and is flagged **(verify)**.
- **`MON_GET_MEMORY_POOL(memory_set_type, db_name, member)`** — per-pool used + high-water.
  The granular heap-attribution layer. **Live DESCRIBE confirmed** (10 cols), see below.

Both return point-in-time **gauges** (current usage / high-water), NOT monotonic counters —
so emit as `gauge`. One row per (member, db, set[, pool[, application_handle/edu_id]]).

### MON_GET_MEMORY_POOL — confirmed columns (live DESCRIBE, `_raw/02-monget-key-columns.txt` L1665-1676)

| Column | SQL type | Role |
|---|---|---|
| `MEMBER` | SMALLINT | tag (`member`) |
| `HOST_NAME` | VARCHAR(255) | tag (`host`) — pureScale/MPP |
| `DB_NAME` | VARCHAR(128) | tag (`db`) |
| `MEMORY_SET_TYPE` | VARCHAR(32) | tag (`memory_set`) |
| `MEMORY_POOL_TYPE` | VARCHAR(32) | tag (`memory_pool`) |
| `MEMORY_POOL_ID` | BIGINT | id (not tagged) |
| `APPLICATION_HANDLE` | BIGINT | nullable — set only for per-app pools; **cardinality risk**, do not tag by default |
| `EDU_ID` | BIGINT | nullable — per-EDU pools; do not tag by default |
| `MEMORY_POOL_USED` | BIGINT | **metric** — bytes used now (gauge) |
| `MEMORY_POOL_USED_HWM` | BIGINT | **metric** — bytes high-water (gauge) |

> NOTE: the live dump has only `MEMORY_POOL_USED`/`_HWM` (no `*_CONFIG_SIZE`/`POOL_CUR_SIZE`/
> `BP_ID` that older catalog notes list). For *configured* heap limits, join to DB/DBM CFG
> (`LOCKLIST`, `PCKCACHESZ`, `CATALOGCACHE_SZ`, `SHEAPTHRES_SHR`, `DATABASE_MEMORY`,
> `INSTANCE_MEMORY`) — those come from `SYSIBMADM.DBCFG`/`DBMCFG`, not MON_GET.
> **Units (verify):** MON_GET memory-pool/set sizes are documented in **bytes** in Db2 9.7+
> (the deprecated SNAP*_MEMORY_POOL `POOL_CUR_SIZE`/`POOL_WATERMARK` used bytes too). Confirm
> with one live `SELECT MEMORY_POOL_USED ... fits a sane byte magnitude` before shipping; if
> it is actually KB, set `unit_name=kibibyte` instead of `byte`.

### MON_GET_MEMORY_SET — proposed columns (NOT in dump — general Db2 12.1 knowledge, **verify** with live DESCRIBE)

`MEMBER, HOST_NAME, DB_NAME, MEMORY_SET_TYPE, MEMORY_SET_ID, MEMORY_SET_USED,
MEMORY_SET_COMMITTED, MEMORY_SET_USED_HWM, ADDITIONAL_COMMITTED, MEMORY_SET_SIZE`
(plus `EDU_ID`/`BP_ID` for the bufferpool set). All bytes (verify), all gauges.

---

## MAPPING TABLE

Metric name prefix `ibm_db2.`. `type` is the Datadog submit fn; metadata.csv catalog type in
parens where it differs (`monotonic_count`/`rate` → `count`/`gauge` in the CSV). Default tags
on every memory metric: `db`, `member`, plus base `database_hostname`/`database_instance` and
a `db2_version` tag (mirror `postgresql_version`). Set/pool-specific tags noted per row.

### A. Memory SET level — `MON_GET_MEMORY_SET` (coarse, "OS-committed per area")

| pg/mysql analog | Db2 source: function + exact column | proposed `ibm_db2.<name>` | type | unit | tags | notes / version-gating |
|---|---|---|---|---|---|---|
| (no direct pg/mysql analog; closest = mysql `innodb.mem_total`) | `MON_GET_MEMORY_SET.MEMORY_SET_COMMITTED` | `memory.set.committed` | gauge | byte | `memory_set`, db, member | Bytes committed from OS per set. Highest-value capacity gauge. **verify column+unit** |
| pg `shared_buffers` setting (no live equiv) / mysql buffer-pool total | `MON_GET_MEMORY_SET.MEMORY_SET_USED` | `memory.set.used` | gauge | byte | `memory_set`, db, member | Bytes actually used within the set. **verify** |
| (no analog) | `MON_GET_MEMORY_SET.MEMORY_SET_USED_HWM` | `memory.set.used_hwm` | gauge | byte | `memory_set`, db, member | High-water used. **verify** |
| (no analog) | `MON_GET_MEMORY_SET.ADDITIONAL_COMMITTED` | `memory.set.additional_committed` | gauge | byte | `memory_set`, db, member | Over-commit headroom. **verify**; optional/low-priority |
| pg `effective_cache_size`/config limit | `MON_GET_MEMORY_SET.MEMORY_SET_SIZE` | `memory.set.size` | gauge | byte | `memory_set`, db, member | Configured set size. **verify**; or derive from `INSTANCE_MEMORY`/`DATABASE_MEMORY` cfg instead |

Key `memory_set` tag values to expect: `DATABASE`, `DBMS` (instance), `APPLICATION`,
`BUFFERPOOL`, `FCM`, `FMP`, `PRIVATE`. The `DATABASE` and `DBMS` sets are the top-line
"total Db2 memory" gauges — analogous to mysql `innodb.mem_total` / `buffer_pool_total`.

### B. Memory POOL level — `MON_GET_MEMORY_POOL` (granular, "which heap is growing")

These two columns are the whole function; you get full heap fidelity by **tagging with
`memory_pool` (and `memory_set`)** rather than minting one metric name per heap. This is the
mysql per-schema/per-tag-dict pattern (`collect_all_scalars`) applied to heaps.

| pg/mysql analog | Db2 source: function + exact column | proposed `ibm_db2.<name>` | type | unit | tags | notes / version-gating |
|---|---|---|---|---|---|---|
| mysql `innodb.mem_*` (per-subsystem heap bytes) | `MON_GET_MEMORY_POOL.MEMORY_POOL_USED` | `memory.pool.used` | gauge | byte | `memory_pool`, `memory_set`, db, member | One series per heap type via `memory_pool` tag. The core memory-pressure metric. |
| (no analog — pg/mysql don't expose per-heap HWM) | `MON_GET_MEMORY_POOL.MEMORY_POOL_USED_HWM` | `memory.pool.used_hwm` | gauge | byte | `memory_pool`, `memory_set`, db, member | High-water per heap — best near-limit signal. |

`memory_pool` tag values of highest interest (all surfaced by the two rows above; no extra
metric names needed): `BP` (bufferpool heap), `LOCKMGR` (lock list), `PACKAGE_CACHE`,
`CAT_CACHE` (catalog cache), `SORTHEAP` + `SHARED_SORTHEAP`, `UTILITY`, `DATABASE`,
`APPL_CONTROL`, `APP_GROUP`, `XMLCACHE`.

**Cardinality control:** do NOT tag by `application_handle`/`edu_id` by default (per-app/per-EDU
pools explode cardinality). Filter the query to instance/db-level pools, or gate per-app pools
behind a config flag (mirror mysql `extra_*`/`index_config` opt-ins). Consider
`WHERE APPLICATION_HANDLE IS NULL` for the default collection.

### C. Specific pg/mysql heaps → Db2 pool tag-value (same two metrics, narrated)

These are NOT new metric names — they are the named `memory_pool` tag-values of
`ibm_db2.memory.pool.used`/`_used_hwm`. Listed so the plan can assert coverage parity.

| pg/mysql analog metric | Db2 source (filter on MON_GET_MEMORY_POOL.MEMORY_POOL_TYPE =) | covered by | type | unit | tags | notes |
|---|---|---|---|---|---|---|
| mysql `myisam.key_buffer_bytes_used`, `innodb.buffer_pool_used`; pg `shared_buffers` | `'BP'` | `memory.pool.used{memory_pool:BP}` | gauge | byte | memory_pool, db, member | Buffer-pool heap memory (distinct from per-BP page counters in `map-bufferpool.md`). Pair with `MON_GET_BUFFERPOOL`. |
| (no pg/mysql analog — lock memory) | `'LOCKMGR'` | `memory.pool.used{memory_pool:LOCKMGR}` | gauge | byte | memory_pool, db, member | Lock-list memory. Complements existing `ibm_db2.lock.pages` (page-count from SNAPDB). Compare vs `LOCKLIST`×`MAXLOCKS` cfg for escalation risk. |
| mysql `performance.qcache_size` / pg plan cache (loose) | `'PACKAGE_CACHE'` | `memory.pool.used{memory_pool:PACKAGE_CACHE}` | gauge | byte | memory_pool, db, member | Package (section) cache memory. Pair with PKG_CACHE_INSERTS/LOOKUPS hit-ratio (`db2-live-pkgcache.md`). Compare vs `PCKCACHESZ`. |
| pg system catalog cache (no live metric) | `'CAT_CACHE'` | `memory.pool.used{memory_pool:CAT_CACHE}` | gauge | byte | memory_pool, db, member | Catalog cache memory. Compare vs `CATALOGCACHE_SZ`. |
| pg `work_mem` usage / mysql `sort_buffer`; mysql `created_tmp_disk_tables` (spill) | `'SORTHEAP'` + `'SHARED_SORTHEAP'` | `memory.pool.used{memory_pool:SORTHEAP\|SHARED_SORTHEAP}` | gauge | byte | memory_pool, db, member | Sort-heap memory currently allocated. The *spill/overflow counters* (SORT_OVERFLOWS, POST_THRESHOLD_SORTS, SORT_SHRHEAP_ALLOCATED) live in `MON_GET_DATABASE`/`SERVICE_SUBCLASS` — see `map-sorting-hashing.md`; this row is the standing heap footprint only. Compare vs `SHEAPTHRES_SHR`/`SORTHEAP`. |
| (no analog) | `'UTILITY'` | `memory.pool.used{memory_pool:UTILITY}` | gauge | byte | memory_pool, db, member | Backup/load/runstats utility heap. Optional. |

---

## Db2-native memory metrics worth adding with NO pg/mysql analog

- **Per-heap high-water (`memory.pool.used_hwm`)** — neither pg nor mysql exposes per-heap
  peak usage. This is Db2's single best "heap was near its limit" signal; high value.
- **`memory_set` committed-vs-used split (`memory.set.committed` vs `.used`)** — pg/mysql have
  no notion of OS-committed-but-unused engine memory; useful for STMM/over-commit tracking.
- **`SHARED_SORTHEAP` as a distinct pool** — shared sort memory under `SHEAPTHRES_SHR` is a
  Db2-specific concept (vs mysql per-session sort_buffer); worth its own tag value.
- **`memory.set.used{memory_set:DBMS}`** — total instance (database-manager) memory, the
  Db2 analog of "engine total memory" that mysql only approximates via `innodb.mem_total`.

## pg/mysql memory metrics with NO Db2 (MON_GET memory) equivalent — flagged

- **mysql `innodb.buffer_pool_pages_dirty`/`_free`/`_data` (page-count breakdown)** — Db2
  exposes buffer-pool *activity* (logical/physical reads, writes) via `MON_GET_BUFFERPOOL`
  (already in the integration / `map-bufferpool.md`) but not a dirty/free/clean **page**
  partition of BP memory. No memory-pool equivalent; only `BP` heap **bytes**.
- **mysql `innodb.buffer_pool_utilization` / `key_cache_utilization` (fraction)** — Db2 has no
  pre-computed memory utilization fraction. Derivable client-side as
  `MEMORY_POOL_USED / <config limit>` (e.g. PACKAGE_CACHE used / PCKCACHESZ); propose computing
  it in-check if a utilization gauge is wanted, else omit.
- **mysql `performance.qcache_free_blocks`/`free_memory`** — query-cache internals; no Db2
  analog (Db2 package cache is not block-structured and exposes only used/HWM).
- **mysql `thread_cache_size` / `table_open_cache`** — agent-pool / table-handle caches; the
  Db2 analog is agent counts in `MON_GET_INSTANCE` (`IDLE_AGENTS`, `AGENTS_REGISTERED`), NOT a
  memory metric — map under the connections/agents category, not memory.
- **pg `temp_bytes`/`temp_files`, mysql `created_tmp_disk_tables`** — these are sort/hash
  **spill** metrics, not standing memory; Db2 analog is in `map-sorting-hashing.md`
  (SORT_OVERFLOWS etc.), not the memory category.
- **pg `*_work_mem` / `shared_buffers` settings** — these are config, not runtime memory; Db2
  analog = DB/DBM CFG (`SORTHEAP`, `SHEAPTHRES_SHR`, `LOCKLIST`, `PCKCACHESZ`,
  `DATABASE_MEMORY`, `INSTANCE_MEMORY`) from `SYSIBMADM.DBCFG`/`DBMCFG` — collect as a separate
  config-snapshot, not from MON_GET.

## Implementation notes

1. **Two queries, declarative (Paradigm B / QueryExecutor `columns` dicts):** one
   `MON_GET_MEMORY_POOL(NULL,NULL,-2)` and one `MON_GET_MEMORY_SET(NULL,NULL,-2)` (`-2` = all
   members). Tag columns `MEMBER→member`, `DB_NAME→db`, `MEMORY_SET_TYPE→memory_set`,
   `MEMORY_POOL_TYPE→memory_pool`; metric columns → gauges.
2. **All gauges** — none of these are counters; never submit as rate/monotonic_count.
3. **Graceful degradation** — wrap each query; `MON_GET_MEMORY_SET` is unconfirmed on the
   target, so a missing-function error must skip just that collector (mirror postgres
   `UndefinedFunction` handling). `MON_GET_MEMORY_POOL` is confirmed present (`_raw/01...txt` L39).
4. **Before coding, run a live DESCRIBE of `MON_GET_MEMORY_SET`** to lock its exact column
   names/types (the set-level rows above are knowledge-based) and confirm the **byte vs KB**
   unit for both functions.
5. **Add a metadata.csv row per emitted metric** (`integration=ibm_db2`, `unit_name=byte`,
   `curated_metric=memory`, orientation 0, describe the `memory_set`/`memory_pool`/`member`
   tags) — currently `ibm_db2/metadata.csv` has zero `memory.*` rows.
