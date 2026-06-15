# Metric Category Mapping: `io-disk` (Db2 12.1 fidelity)

Raw research input for the Db2 high-fidelity metric implementation plan. **Category scope:** physical/disk I/O that is *not* buffer-pool-cache-hit accounting — i.e. **direct (non-buffered) reads/writes**, **buffer-pool physical page writes** (page cleaners / async write activity), **buffer-pool async vs synchronous read accounting (prefetchers)**, **I/O timing** (read/write/direct time), **log disk I/O + log-disk waits**, **table-space container I/O & containers**, and **temp-table-space spill I/O**. Target Db2 version **12.1** (live container **12.1.4.0**, image `icr.io/db2_community/db2:12.1.4.0`).

> Scope boundary note: buffer-pool **logical reads** and **hit_percent** (the cache-effectiveness numbers) belong to the separate `bufferpool`/cache-hit category and are NOT re-mapped here except where a write/async/timing counter rides on the same `MON_GET_BUFFERPOOL` row. The existing `ibm_db2.bufferpool.*.reads.physical` metrics (already shipped) ARE in-scope here because "physical reads" = disk reads, and this doc reconciles them with pg/mysql disk-read analogs.

Sources consulted:
- pg metric catalog: `/home/bits/dd/integrations-core/postgres/metadata.csv`
- mysql metric catalog: `/home/bits/dd/integrations-core/mysql/metadata.csv`
- mysql collection architecture: `/home/bits/dd/integrations-core/ibm_db2/dev-docs/db2-fidelity-plan/_research/code-mysql-metrics.md`
- existing ibm_db2 audit (every shipped metric + exact SQL columns): `/home/bits/dd/integrations-core/ibm_db2/dev-docs/db2-fidelity-plan/_research/code-ibm_db2-current.md`
- existing ibm_db2 SQL: `/home/bits/dd/integrations-core/ibm_db2/datadog_checks/ibm_db2/queries.py`
- existing ibm_db2 emission code: `/home/bits/dd/integrations-core/ibm_db2/datadog_checks/ibm_db2/ibm_db2.py` (`query_buffer_pool` 192-377, `query_table_space` 379-412, `query_transaction_log` 414-441)
- existing ibm_db2 catalog: `/home/bits/dd/integrations-core/ibm_db2/metadata.csv`
- **live-confirmed Db2 12.1.4 column names** (from `MON_GET_PKG_CACHE_STMT_DETAILS` DESCRIBE probe — same I/O monitor elements exist on `MON_GET_DATABASE`/`MON_GET_BUFFERPOOL`/`MON_GET_TABLESPACE`/`MON_GET_CONNECTION`): `/home/bits/dd/integrations-core/ibm_db2/dev-docs/db2-fidelity-plan/_research/db2-live-pkgcache.md` §6c (time/wait), §6d (buffer-pool/IO), §6g (logging)
- live activity columns (DIRECT_READS/WRITES on activity): `/home/bits/dd/integrations-core/ibm_db2/dev-docs/db2-fidelity-plan/_research/db2-live-activity.md` lines 208-209, 298-324
- config/version detection: `/home/bits/dd/integrations-core/ibm_db2/dev-docs/db2-fidelity-plan/_research/db2-config-settings.md`

> ⚠️ The task referenced staged files `db2-monget-catalog-*.md`, `db2-sysibmadm-views.md`, `db2-live-monget.md`, `db2-live-sysibmadm.md`, `code-postgres-metrics.md` — **none of these exist in the `_research/` directory** (verified). All Db2 column names below are grounded in (a) the live `db2-live-pkgcache.md`/`db2-live-activity.md` probes, (b) the exact columns already selected by the shipped check (`queries.py`), and (c) IBM 12.1 monitor-element documentation. Columns marked `[LIVE]` are confirmed present in the 12.1.4 container; columns marked `[DOC]` are from IBM 12.1 docs and should be validated against the live container before shipping.

---

## 0. Db2 I/O model in one paragraph (so the mapping makes sense)

Db2 splits page I/O into two worlds:
1. **Buffer-pool I/O** — pages that go *through* a buffer pool. Counted in `MON_GET_BUFFERPOOL` (and rolled up in `MON_GET_DATABASE`). "Logical reads" (`POOL_*_L_READS`) = logical page requests; "physical reads" (`POOL_*_P_READS`) = the subset that missed cache and hit disk; "writes" (`POOL_*_WRITES`) = dirty pages flushed to disk (by page cleaners or victim writes). `POOL_ASYNC_*` columns isolate the portion done by **prefetcher EDUs** (async reads) and **page-cleaner EDUs** (async writes), so `synchronous = total − async`.
2. **Direct I/O** — I/O that bypasses the buffer pool: LOBs, LONG VARCHAR, some utility/backup paths, XML. Counted as `DIRECT_READS`/`DIRECT_WRITES` (bytes-ish "sectors"/operations) and `DIRECT_READ_REQS`/`DIRECT_WRITE_REQS` (number of physical I/O requests). This is the closest Db2 analog to postgres "blocks read from disk" for non-cached objects.

I/O **timing** is `POOL_READ_TIME`/`POOL_WRITE_TIME` (buffer-pool disk read/write ms) and `DIRECT_READ_TIME`/`DIRECT_WRITE_TIME` (direct I/O ms). Log I/O is `LOG_READS`/`LOG_WRITES` (pages) plus `LOG_DISK_WAIT_TIME` + `LOG_DISK_WAITS_TOTAL` (waiting on log disk). Page-cleaner trigger counters (`POOL_DRTY_PG_*`, `POOL_NO_VICTIM_BUFFER`, `UNREAD_PREFETCH_PAGES`, `FILES_CLOSED`, `VECTORED_*`, `BLOCK_*`) live on `MON_GET_BUFFERPOOL`.

**Where to read each element (all `-1`/`NULL` member arg for whole-DB aggregation, matching the existing check):**
- Whole-DB rollup of every element below: `MON_GET_DATABASE(-1)` (single row, lowest cardinality) — **preferred** for the DB-level disk I/O metrics.
- Per-buffer-pool: `MON_GET_BUFFERPOOL(NULL, -1)` (one row per BP, tag `bufferpool:`).
- Per-table-space: `MON_GET_TABLESPACE(NULL, -1)` (one row per TS, tag `tablespace:`) — carries its own `POOL_*`, `DIRECT_*`, `POOL_READ_TIME`/`WRITE_TIME` columns.
- Per-container (file/device level): `MON_GET_CONTAINER(NULL, -1)` — physical reads/writes per container + `FS_USED_SIZE`/`FS_TOTAL_SIZE` for filesystem-level disk capacity.
- Log: `MON_GET_TRANSACTION_LOG(-1)` (single row).

---

## 1. MAPPING TABLE — pg/mysql analog → Db2 source → proposed ibm_db2 metric

Legend for **type**: `count` = monotonic_count (lifetime cumulative counter → submit `monotonic_count`, declare `count` in metadata.csv); `gauge` = point-in-time / computed ratio; `rate` = avoid (we follow ibm_db2 convention of submitting `monotonic_count` and letting the app `.as_rate()`/`.as_count()`).

### 1.1 Buffer-pool / data-file physical reads (disk reads via BP)

| pg/mysql analog | Db2 source: function + exact column | proposed `ibm_db2.<name>` | type | unit | tags | notes / caveats / version-gating |
|---|---|---|---|---|---|---|
| `postgresql.disk_read` (rate, block/s); `postgresql.heap_blocks_read`; `mysql.innodb.pages_read`; `mysql.innodb.buffer_pool_reads` (logical reads that hit disk) | `MON_GET_DATABASE(-1)`: `POOL_DATA_P_READS` + `POOL_TEMP_DATA_P_READS` + `POOL_INDEX_P_READS` + `POOL_TEMP_INDEX_P_READS` + `POOL_XDA_P_READS` + `POOL_TEMP_XDA_P_READS` + `POOL_COL_P_READS` + `POOL_TEMP_COL_P_READS` | **`ibm_db2.bufferpool.reads.physical`** (ALREADY SHIPPED, but currently DB-wide is computed by summing per-BP rows in `query_buffer_pool`; metadata.csv:24) | count | get (page) | `db`, (per-BP via `bufferpool:`) | **EXISTS.** `[LIVE]` columns. This IS the pg `disk_read` analog. Already emitted per-bufferpool AND aggregate. No new metric needed; keep. |
| `postgresql.index_blocks_read`; `mysql.innodb` (no direct) | `MON_GET_BUFFERPOOL`: `POOL_INDEX_P_READS`+`POOL_TEMP_INDEX_P_READS` | **`ibm_db2.bufferpool.index.reads.physical`** (SHIPPED, metadata.csv:21) | count | get | `db`,`bufferpool` | EXISTS. |
| `postgresql.heap_blocks_read` | `MON_GET_BUFFERPOOL`: `POOL_DATA_P_READS`+`POOL_TEMP_DATA_P_READS` | **`ibm_db2.bufferpool.data.reads.physical`** (SHIPPED, metadata.csv:11) | count | get | `db`,`bufferpool` | EXISTS. |
| (no pg/mysql analog — XML) | `MON_GET_BUFFERPOOL`: `POOL_XDA_P_READS`+`POOL_TEMP_XDA_P_READS` | **`ibm_db2.bufferpool.xda.reads.physical`** (SHIPPED, metadata.csv:28) | count | get | `db`,`bufferpool` | EXISTS. |
| (no analog — columnar/BLU) | `MON_GET_BUFFERPOOL`: `POOL_COL_P_READS`+`POOL_TEMP_COL_P_READS` | **`ibm_db2.bufferpool.column.reads.physical`** (SHIPPED, metadata.csv:7) | count | get | `db`,`bufferpool` | EXISTS. Db2-native (BLU). |

### 1.2 Buffer-pool physical writes (page cleaners / dirty-page flush to disk) — **NEW, high value**

| pg/mysql analog | Db2 source: function + exact column | proposed `ibm_db2.<name>` | type | unit | tags | notes / caveats / version-gating |
|---|---|---|---|---|---|---|
| `mysql.innodb.pages_written`; `mysql.innodb.buffer_pool_pages_flushed`; `postgresql.bgwriter.buffers_clean`+`buffers_checkpoint`+`buffers_backend` (sum of all dirty-page writeback) | `MON_GET_BUFFERPOOL`/`MON_GET_DATABASE`: `POOL_DATA_WRITES` `[LIVE]` | **`ibm_db2.bufferpool.data.writes`** | count | write (page) | `db`,`bufferpool` | NEW. Total data-page writes to disk. mysql `pages_written` analog. |
| (same family, index) | `POOL_INDEX_WRITES` `[LIVE]` | **`ibm_db2.bufferpool.index.writes`** | count | write | `db`,`bufferpool` | NEW. |
| (XML) | `POOL_XDA_WRITES` `[LIVE]` | **`ibm_db2.bufferpool.xda.writes`** | count | write | `db`,`bufferpool` | NEW. Db2-native. |
| (columnar/BLU) | `POOL_COL_WRITES` `[DOC]` (present in 12.1 BP element set; live column-group lists `POOL_COL_*`) | **`ibm_db2.bufferpool.column.writes`** | count | write | `db`,`bufferpool` | NEW. Db2-native. Validate column presence on the live BP function. |
| `mysql.innodb.pages_written` / `mysql.innodb.buffer_pool_pages_flushed` (total) | sum of `POOL_DATA_WRITES`+`POOL_INDEX_WRITES`+`POOL_XDA_WRITES`+`POOL_COL_WRITES` | **`ibm_db2.bufferpool.writes`** (aggregate, mirrors existing `bufferpool.reads.*` aggregate pattern in `ibm_db2.py:348-377`) | count | write | `db`,(per-BP `bufferpool`) | NEW. Mirror the existing aggregate-of-four-classes summation pattern. The single most useful "how much is being flushed to disk" number. |

### 1.3 Async vs synchronous buffer-pool writes — **page-cleaner activity, Db2-native, NEW**

Db2 exposes the *portion* of writes done asynchronously by **page-cleaner EDUs**. `synchronous = total_writes − async_writes`. High sync writes = page cleaners not keeping up (the closest analog to mysql `innodb.buffer_pool_wait_free`).

| pg/mysql analog | Db2 source | proposed `ibm_db2.<name>` | type | unit | tags | notes |
|---|---|---|---|---|---|---|
| `postgresql.bgwriter.buffers_clean` (writes by bgwriter, the async cleaner) | `MON_GET_BUFFERPOOL`: `POOL_ASYNC_DATA_WRITES`, `POOL_ASYNC_INDEX_WRITES`, `POOL_ASYNC_XDA_WRITES`, `POOL_ASYNC_COL_WRITES` `[DOC]` (live group lists `POOL_QUEUED_ASYNC_*`/`POOL_FAILED_ASYNC_*`; the `POOL_ASYNC_*_WRITES` are the corresponding completed-write columns) | **`ibm_db2.bufferpool.{data,index,xda,column}.writes.async`** | count | write | `db`,`bufferpool` | NEW, Db2-native. = page-cleaner writes. |
| `postgresql.bgwriter.buffers_backend` (writes by a backend instead of bgwriter — sync) | derived: `POOL_<x>_WRITES − POOL_ASYNC_<x>_WRITES` | **`ibm_db2.bufferpool.{...}.writes.sync`** (derived) | count | write | `db`,`bufferpool` | NEW, Db2-native. backend/victim writes — high = cleaner pressure. |
| `mysql.innodb.buffer_pool_wait_free` (waits because no clean page available) | `MON_GET_BUFFERPOOL`: `POOL_NO_VICTIM_BUFFER` `[DOC]` | **`ibm_db2.bufferpool.no_victim_buffer`** | count | wait | `db`,`bufferpool` | NEW, Db2-native. Direct mysql `buffer_pool_wait_free` analog — agent had to search >1 BP buffer to find a victim. Strong cleaner-pressure signal. |
| `mysql.innodb.pages_created` | `MON_GET_BUFFERPOOL`: `POOL_DATA_LBP_PAGES_FOUND` already used for hit%; no pure "created" column — **no clean Db2 equivalent** | — | — | — | — | mysql `pages_created` (new pages) has no direct Db2 element. Flag as pg/mysql-only. |

### 1.4 Async vs synchronous buffer-pool reads — prefetcher activity (Db2-native, NEW)

| pg/mysql analog | Db2 source | proposed `ibm_db2.<name>` | type | unit | tags | notes |
|---|---|---|---|---|---|---|
| `mysql.innodb.buffer_pool_read_ahead` (pages read by read-ahead/prefetch thread) | `MON_GET_BUFFERPOOL`: `POOL_ASYNC_DATA_READS`, `POOL_ASYNC_INDEX_READS`, `POOL_ASYNC_XDA_READS`, `POOL_ASYNC_COL_READS` `[DOC]` (prefetcher EDU physical reads) | **`ibm_db2.bufferpool.{data,index,xda,column}.reads.async`** | count | get | `db`,`bufferpool` | NEW, Db2-native. = prefetcher reads. mysql `buffer_pool_read_ahead` analog. |
| (derived sync read = demand read) | `POOL_<x>_P_READS − POOL_ASYNC_<x>_READS` | **`ibm_db2.bufferpool.{...}.reads.sync`** (derived) | count | get | `db`,`bufferpool` | NEW. Synchronous (on-demand, latency-sensitive) physical reads. |
| `mysql.innodb.buffer_pool_read_ahead_evicted` (prefetched but evicted unused) | `MON_GET_BUFFERPOOL`: `UNREAD_PREFETCH_PAGES` `[DOC]` | **`ibm_db2.bufferpool.unread_prefetch_pages`** | count | page | `db`,`bufferpool` | NEW, Db2-native. Pages prefetched into BP but evicted before use = wasted prefetch I/O. Direct mysql `read_ahead_evicted` analog. |
| (no analog) | `MON_GET_BUFFERPOOL`/`MON_GET_DATABASE`: `PREFETCH_WAITS` `[LIVE]`, `PREFETCH_WAIT_TIME` `[LIVE]` | **`ibm_db2.bufferpool.prefetch.waits`** (count), **`ibm_db2.bufferpool.prefetch.wait_time`** (count, ms) | count | wait / millisecond | `db`,`bufferpool` | NEW, Db2-native. Time an agent waited for a prefetcher to finish I/O. Tuning signal for `NUM_IOSERVERS`. |
| `mysql.innodb.buffer_pool_read_ahead_rnd` (random read-aheads) | `MON_GET_BUFFERPOOL`: `VECTORED_IOS`, `PAGES_FROM_VECTORED_IOS`, `BLOCK_IOS`, `PAGES_FROM_BLOCK_IOS` `[DOC]` | **`ibm_db2.bufferpool.vectored_ios`**, **`...pages_from_vectored_ios`**, **`...block_ios`**, **`...pages_from_block_ios`** | count | operation / page | `db`,`bufferpool` | NEW, Db2-native. Prefetch I/O shape (sequential block prefetch vs scattered vectored). Lower priority. |

### 1.5 Direct (non-buffered) I/O — LOB/XML/utility disk I/O — **NEW, maps to "disk read/write" intent**

| pg/mysql analog | Db2 source | proposed `ibm_db2.<name>` | type | unit | tags | notes |
|---|---|---|---|---|---|---|
| `postgresql.disk_read` (broad "blocks read from disk"); `mysql.innodb.data_reads` (rate of data reads); `mysql.innodb.os_file_reads` | `MON_GET_DATABASE(-1)` / `MON_GET_BUFFERPOOL` / `MON_GET_TABLESPACE`: `DIRECT_READS` `[LIVE]` | **`ibm_db2.direct.reads`** | count | sector | `db` (DB-level); also per-`bufferpool`/`tablespace` | NEW, Db2-native + analog. Number of 512-byte sectors read directly (bypassing BP) — LOB/LONG/XML/utility. |
| (request-count granularity; no direct pg analog) | `DIRECT_READ_REQS` `[LIVE]` | **`ibm_db2.direct.read_reqs`** | count | request | `db` | NEW, Db2-native. Number of physical read *requests* (vs sectors). reqs vs sectors → avg I/O size. |
| `postgresql.disk_read` (write side: `mysql.innodb.data_writes`, `mysql.innodb.os_file_writes`) | `DIRECT_WRITES` `[LIVE]` | **`ibm_db2.direct.writes`** | count | sector | `db`, per-`bufferpool`/`tablespace` | NEW. Sectors written directly to disk. |
| (request count) | `DIRECT_WRITE_REQS` `[LIVE]` | **`ibm_db2.direct.write_reqs`** | count | request | `db` | NEW, Db2-native. |

### 1.6 I/O timing — read/write latency (Db2-native; analog to pg `track_io_timing`)

Db2 collects these **unconditionally** (no `track_io_timing` equivalent toggle needed — `[LIVE]` confirmed), which is a *fidelity win over postgres* (pg returns 0 unless `track_io_timing` is on).

| pg/mysql analog | Db2 source | proposed `ibm_db2.<name>` | type | unit | tags | notes |
|---|---|---|---|---|---|---|
| `postgresql.blk_read_time` (ms reading data blocks, track_io_timing); `postgresql.io.read_time` | `MON_GET_DATABASE(-1)` / `MON_GET_BUFFERPOOL` / `MON_GET_TABLESPACE`: `POOL_READ_TIME` `[LIVE]` (ms) | **`ibm_db2.bufferpool.read_time`** | count | millisecond | `db`, per-`bufferpool`/`tablespace` | NEW, Db2-native + pg analog. Total elapsed time of BP physical *reads*. Always populated. |
| `postgresql.blk_write_time`; `postgresql.io.write_time` | `POOL_WRITE_TIME` `[LIVE]` (ms) | **`ibm_db2.bufferpool.write_time`** | count | millisecond | `db`,`bufferpool`/`tablespace` | NEW, Db2-native + pg analog. Total elapsed time of BP physical *writes* (page cleaners). |
| (no pg analog — direct-IO timing) | `DIRECT_READ_TIME` `[LIVE]` (ms) | **`ibm_db2.direct.read_time`** | count | millisecond | `db` | NEW, Db2-native. |
| (no pg analog) | `DIRECT_WRITE_TIME` `[LIVE]` (ms) | **`ibm_db2.direct.write_time`** | count | millisecond | `db` | NEW, Db2-native. |
| `postgresql.io.fsync_time` (pg16+ DBM) | (no per-fsync timing element in Db2; folded into `POOL_WRITE_TIME`/log waits) | — | — | — | — | Flag: pg-only. Db2 has no separate fsync-time monitor element. |

### 1.7 Log disk I/O (in-scope: physical log read/write + log-disk waits)

| pg/mysql analog | Db2 source | proposed `ibm_db2.<name>` | type | unit | tags | notes |
|---|---|---|---|---|---|---|
| `postgresql.wal.write` (WAL writes to disk); `mysql.innodb.os_log_written` | `MON_GET_TRANSACTION_LOG(-1)`: `LOG_WRITES` (pages written by logger) | **`ibm_db2.log.writes`** (SHIPPED, metadata.csv:43) | count | write | `db` | EXISTS. pg `wal.write` analog. |
| (WAL read on recovery/replication) | `MON_GET_TRANSACTION_LOG(-1)`: `LOG_READS` | **`ibm_db2.log.reads`** (SHIPPED, metadata.csv:40) | count | read | `db` | EXISTS. |
| `postgresql.wal.sync_time` / `mysql.innodb.os_log_pending_fsyncs` (waiting on log disk) | `MON_GET_DATABASE(-1)` / `MON_GET_TRANSACTION_LOG`: `LOG_DISK_WAIT_TIME` `[LIVE]` (ms), `LOG_DISK_WAITS_TOTAL` `[LIVE]` (count) | **`ibm_db2.log.disk_wait_time`** (count, ms), **`ibm_db2.log.disk_waits`** (count) | count | millisecond / wait | `db` | NEW, Db2-native + pg `wal.sync_time` analog. Time agents spent waiting for log records to flush to disk = commit-latency driver. **High value.** |
| `mysql.innodb.log_waits` (log buffer too small, had to wait) | `MON_GET_DATABASE(-1)`: `NUM_LOG_BUFFER_FULL` `[LIVE]` | **`ibm_db2.log.buffer_full`** | count | wait | `db` | NEW, Db2-native + mysql `log_waits` analog. Times the log buffer filled and forced a flush → tune `LOGBUFSZ`. |
| `mysql.innodb.os_log_pending_writes` | (no direct pending-log-writes element) | — | — | — | — | Flag: mysql-only. |
| (raw log-records-written volume) | `MON_GET_TRANSACTION_LOG`: `LOG_WRITE_TIME` `[DOC]` (ms elapsed writing log), `NUM_LOG_WRITE_IO` `[DOC]`, `NUM_LOG_READ_IO` `[DOC]`, `LOG_WRITE_TIME`/`LOG_READ_TIME` | **`ibm_db2.log.write_time`**, **`ibm_db2.log.read_time`**, **`ibm_db2.log.write_io`**, **`ibm_db2.log.read_io`** | count | millisecond / operation | `db` | NEW, Db2-native. Disk-level log I/O time & op counts (distinct from `LOG_WRITES` page counts). Validate column names on live `MON_GET_TRANSACTION_LOG`. |

### 1.8 Table-space-level disk I/O + containers (per-tablespace, Db2-native; no pg/mysql analog at this granularity)

`MON_GET_TABLESPACE(NULL, -1)` carries the same `POOL_*_P_READS`, `POOL_*_WRITES`, `DIRECT_*`, `POOL_READ_TIME`, `POOL_WRITE_TIME` columns **per table space** — the existing check only pulls size columns. Per-TS I/O is the Db2 analog to pg per-relation block reads but at TS granularity.

| pg/mysql analog | Db2 source | proposed `ibm_db2.<name>` | type | unit | tags | notes |
|---|---|---|---|---|---|---|
| `postgresql.heap_blocks_read` (per relation) ≈ per-TS | `MON_GET_TABLESPACE`: `POOL_DATA_P_READS`+`POOL_INDEX_P_READS`+`POOL_XDA_P_READS`+`POOL_COL_P_READS` (+temp variants) | **`ibm_db2.tablespace.reads.physical`** | count | get | `db`,`tablespace` | NEW, Db2-native. Per-TS disk reads. Cardinality = #tablespaces (low). |
| `mysql.innodb.pages_written` (per TS) | `MON_GET_TABLESPACE`: `POOL_DATA_WRITES`+`POOL_INDEX_WRITES`+`POOL_XDA_WRITES`+`POOL_COL_WRITES` | **`ibm_db2.tablespace.writes.physical`** | count | write | `db`,`tablespace` | NEW. |
| `postgresql.blk_read_time` (per TS) | `MON_GET_TABLESPACE`: `POOL_READ_TIME`, `POOL_WRITE_TIME` | **`ibm_db2.tablespace.read_time`**, **`ibm_db2.tablespace.write_time`** | count | millisecond | `db`,`tablespace` | NEW. |
| (direct I/O per TS) | `MON_GET_TABLESPACE`: `DIRECT_READS`,`DIRECT_WRITES`,`DIRECT_READ_TIME`,`DIRECT_WRITE_TIME` | **`ibm_db2.tablespace.direct.{reads,writes,read_time,write_time}`** | count | sector/ms | `db`,`tablespace` | NEW, Db2-native. |
| (no pg analog — TS housekeeping I/O) | `MON_GET_TABLESPACE`: `FILES_CLOSED` `[DOC]` (used by sample custom query in `conf.yaml.example:109`) | **`ibm_db2.tablespace.files_closed`** | count | file | `db`,`tablespace` | NEW, Db2-native. Number of times a TS container file was closed (SMS/DMS file churn). |
| `postgresql.database_size` / per-table size (filesystem-level) | `MON_GET_CONTAINER(NULL, -1)`: `FS_USED_SIZE`, `FS_TOTAL_SIZE` (bytes) | **`ibm_db2.container.fs_used`**, **`ibm_db2.container.fs_total`** | gauge | byte | `db`,`tablespace`,`container` (`CONTAINER_NAME`), `member` | NEW, Db2-native. Filesystem free space per container = disk-full early-warning. Tag cardinality = #containers; OK. |
| (per-container physical I/O) | `MON_GET_CONTAINER`: `POOL_DATA_P_READS`/etc., `DIRECT_READS`/`DIRECT_WRITES`, `TOTAL_PAGES`, `USABLE_PAGES`, `USED_PAGES` | **`ibm_db2.container.reads.physical`**, **`ibm_db2.container.writes`**, etc. (optional, gated) | count | get/write | `db`,`tablespace`,`container` | NEW, Db2-native. **Gate behind a config option** (e.g. `collect_container_metrics`) — many containers in DMS → cardinality. Lower priority than TS-level. |

### 1.9 Temp / spill I/O (queries spilling to disk)

| pg/mysql analog | Db2 source | proposed `ibm_db2.<name>` | type | unit | tags | notes |
|---|---|---|---|---|---|---|
| `postgresql.temp_bytes` / `postgresql.temp_files`; `mysql.performance.created_tmp_disk_tables` (temp written to disk) | `MON_GET_DATABASE(-1)`: `POOL_TEMP_DATA_P_READS`+`POOL_TEMP_INDEX_P_READS`+`POOL_TEMP_XDA_P_READS`+`POOL_TEMP_COL_P_READS` `[LIVE]` (physical reads from temp TS = spill activity) | **`ibm_db2.bufferpool.temp.reads.physical`** | count | get | `db`,`bufferpool` | NEW, Db2-native. Physical I/O against temporary table spaces = sort/hash spill pressure. Closest temp-spill analog. (Today these temp columns are folded INTO the existing `reads.physical` totals; consider exposing the temp slice separately.) |
| `mysql.queries.sort_merge_passes` (sort spilled to disk); `mysql.innodb.buffer_pool_wait_free` | `MON_GET_DATABASE(-1)`: `SORT_OVERFLOWS` `[LIVE]` | **`ibm_db2.sort.overflows`** (NOTE: arguably belongs to a `sort/temp` category, but it is the disk-spill trigger) | count | overflow | `db` | NEW, Db2-native. Sorts that exceeded sort heap and spilled to a temp TS (disk). Cross-listed; map owner = sort category, but flag here as the spill-I/O driver. |

---

## 2. pg/mysql metrics in this category with **NO Db2 equivalent** (flag list)

| pg/mysql metric | why no Db2 analog | recommendation |
|---|---|---|
| `postgresql.bgwriter.checkpoints_timed` / `checkpoints_requested` / `buffers_checkpoint` | Db2 has no discrete "checkpoint" counter exposed via MON_GET; flushing is continuous via page cleaners + soft-checkpoint by LSN gap (`SOFTMAX`/`PAGE_AGE_TRGT_MCR`). | Closest proxy is `POOL_*_WRITES` (§1.2) + `LOG_DISK_WAIT_TIME`. Do NOT fabricate a checkpoint metric. |
| `postgresql.bgwriter.maxwritten_clean` | Db2 page cleaners are not driven by the same "max LRU scan" loop; no equivalent counter. | Skip. |
| `postgresql.bgwriter.buffers_backend_fsync` / `postgresql.io.fsyncs` / `io.fsync_time` | Db2 does not expose per-fsync counts or fsync time as monitor elements (fsync cost is inside `POOL_WRITE_TIME`/`LOG_DISK_WAIT_TIME`). | Skip; note as known gap. |
| `mysql.innodb.data_fsyncs` / `os_file_fsyncs` / `os_log_fsyncs` / `data_pending_fsyncs` | Same — no fsync-count element. | Skip. |
| `mysql.innodb.dblwr_pages_written` / `dblwr_writes` (doublewrite buffer) | Db2 has no doublewrite buffer (uses different torn-page protection). | N/A — architectural difference. |
| `mysql.innodb.data_pending_reads` / `data_pending_writes` / `pending_*_aio_*` / `os_log_pending_writes` | Db2 MON_GET does not expose instantaneous *pending* I/O queue depth (the `POOL_QUEUED_ASYNC_*`/`POOL_FAILED_ASYNC_*` columns are cumulative queue *counts*, not a live depth gauge). | `POOL_QUEUED_ASYNC_DATA_REQS` etc. are the nearest (cumulative); optional low-priority. No live "pending" gauge. |
| `mysql.innodb.pages_created` | No "pages created" element in Db2. | Skip. |
| `postgresql.wal.full_page_images` / `wal.buffers_full` / `wal_count` / `wal_size` | Db2 log architecture differs (no full-page-image WAL); `wal.buffers_full` ≈ `NUM_LOG_BUFFER_FULL` (mapped §1.7); log file count/size is config (`LOGPRIMARY`/`LOGSECOND`/`LOGFILSIZ`) not a MON metric. | `NUM_LOG_BUFFER_FULL` covered. Log sizing → config metadata (separate config category), not io-disk. |
| `postgresql.slru.*` | SLRU is a postgres-internal cache; no Db2 concept. | Skip. |
| `mysql.binlog.disk_use` / `binlog.cache_disk_use` | Db2 has no binlog; transaction log size is `TOTAL_LOG_USED`/`TOTAL_LOG_AVAILABLE` (already shipped as `ibm_db2.log.used`/`.available`, log category). | N/A. |

---

## 3. Db2-native io-disk metrics with NO pg/mysql analog worth adding (priority-ranked)

1. **`ibm_db2.log.disk_wait_time` / `ibm_db2.log.disk_waits`** (§1.7) — commit-latency driver; the single highest-value missing log-IO signal. (`LOG_DISK_WAIT_TIME`/`LOG_DISK_WAITS_TOTAL`, `[LIVE]`.)
2. **`ibm_db2.bufferpool.write_time` / `ibm_db2.bufferpool.read_time`** + **`ibm_db2.direct.{read,write}_time`** (§1.6) — Db2 always populates I/O timing (no `track_io_timing` toggle), a fidelity win over pg. (`[LIVE]`.)
3. **`ibm_db2.bufferpool.{data,index,xda,column}.writes`** + aggregate **`ibm_db2.bufferpool.writes`** (§1.2) — closes the glaring "we report reads but not writes" asymmetry. (`POOL_*_WRITES`, `[LIVE]`.)
4. **`ibm_db2.bufferpool.no_victim_buffer`** + **`ibm_db2.bufferpool.{...}.writes.sync`** (§1.3) — page-cleaner pressure (mysql `buffer_pool_wait_free` intent). (`POOL_NO_VICTIM_BUFFER` `[DOC]`.)
5. **`ibm_db2.direct.{reads,read_reqs,writes,write_reqs}`** (§1.5) — LOB/XML/utility disk I/O. (`[LIVE]`.)
6. **`ibm_db2.bufferpool.{...}.reads.async` / `.writes.async`** + **`unread_prefetch_pages`** + **`prefetch.waits`/`prefetch.wait_time`** (§1.3-1.4) — prefetcher/page-cleaner async breakdown. (Async columns `[DOC]`; prefetch wait `[LIVE]`.)
7. **`ibm_db2.tablespace.{reads.physical,writes.physical,read_time,write_time,direct.*,files_closed}`** (§1.8) — per-TS disk I/O, low cardinality.
8. **`ibm_db2.log.buffer_full`** (§1.7) — `LOGBUFSZ` tuning (mysql `log_waits` analog). (`[LIVE]`.)
9. **`ibm_db2.container.{fs_used,fs_total}`** (§1.8) — disk-full early warning per container.
10. **`ibm_db2.bufferpool.{vectored_ios,block_ios,...}`** (§1.4) — prefetch I/O shape; lowest priority.

---

## 4. Implementation notes for the plan author

- **Reuse the existing summation pattern.** `query_buffer_pool` (`ibm_db2.py:192-377`) already (a) loops `MON_GET_BUFFERPOOL` rows, (b) tags `bufferpool:<bp_name>`, (c) sums the four page classes (col/data/index/xda) into a DB-wide aggregate. The new writes/async/timing metrics drop straight into that loop — add the columns to `BUFFER_POOL_TABLE_COLUMNS` in `queries.py` and emit alongside the existing reads. **Same four-class aggregate roll-up** for `bufferpool.writes`.
- **Prefer DB-level rollup where cardinality matters.** For the headline DB-wide numbers (`direct.*`, `log.*`, total `read_time`/`write_time`) pull from `MON_GET_DATABASE(-1)` (single row) rather than summing BP rows — cheaper and authoritative. Per-BP/per-TS variants are the optional, tag-bearing additions.
- **Metric type discipline** (per `code-mysql-metrics.md` §10 and existing ibm_db2 convention): every cumulative MON_GET counter → `self.monotonic_count(...)`, declared `count` in `metadata.csv`. Computed ratios / point-in-time (`container.fs_used`) → `gauge`. **All `*_TIME` columns are cumulative ms counters → `monotonic_count`/`count`**, NOT gauges (mirror pg `blk_read_time,count,millisecond`).
- **Units in metadata.csv** (match pg/mysql conventions): page reads → `get` (existing ibm_db2 convention for BP reads) or `block`; writes → `write`; timing → `millisecond`; direct I/O sectors → `sector`; requests → `request`; waits → `wait`; filesystem → `byte`. Add a `metadata.csv` row per emitted metric (`integration=ibm_db2`, sensible `orientation`: writes/reads `0`, wait_time/no_victim_buffer/log_buffer_full `-1`, fs_used `-1`, fs_total `0`).
- **Version/edition gating:** target is 12.1 (live 12.1.4); all `POOL_*`/`DIRECT_*`/`LOG_DISK_*`/`PREFETCH_*` elements exist since 9.7/10.1, so **no version gate needed for 12.1**. `POOL_COL_*` and `POOL_*_GBP_*` are only meaningful for column-organized (BLU) tables and pureScale respectively — guard the column variants exactly like the existing `# no cov` pureScale GBP branches (`ibm_db2.py:233`, `270`, `307`): emit only when the source column is truthy. Validate `[DOC]`-flagged columns (`POOL_ASYNC_*_WRITES`, `POOL_NO_VICTIM_BUFFER`, `UNREAD_PREFETCH_PAGES`, `VECTORED_IOS`, `LOG_WRITE_TIME`/`NUM_LOG_WRITE_IO`, `MON_GET_CONTAINER.FS_*`) against the live container via `DESCRIBE SELECT ... FROM TABLE(MON_GET_BUFFERPOOL(NULL,-1))` before finalizing.
- **No monitor-switch dependency for these.** MON_GET I/O elements are always collected (unlike legacy snapshot switches); the `DFT_MON_BUFPOOL` switch the test harness sets (`code-ibm_db2-current.md:339`) affects legacy snapshot views, not `MON_GET_*`. Safe.
- **Member tag:** all queries use `-1`/`NULL` (aggregate across members). If a `member` dimension is later added (DPF/pureScale), `MON_GET_CONTAINER`/`MON_GET_TABLESPACE` expose a `MEMBER` column — tag it then.
