# Metric Mapping — BUFFERPOOL category (Db2 12.1 fidelity plan)

Raw implementation input mapping the **bufferpool** metric category (buffer pool reads/writes/hit-ratios for data/index/xda/col; prefetch; victim/page-cleaning; block & vectored I/O; pool read/write time; GBP / pureScale group buffer pool) to the Datadog `ibm_db2` integration, benchmarked against postgres and mysql fidelity.

Target Db2: **12.1** (live container **12.1.4**). Primary source: `MON_GET_BUFFERPOOL` table function (one row per buffer pool per member). All `MON_GET_BUFFERPOOL` columns are also exposed on `SYSIBMADM.MON_BP_UTILIZATION` / `SYSIBMADM.BP_HITRATIO` / `SYSIBMADM.BP_READ_IO` / `SYSIBMADM.BP_WRITE_IO` admin views (legacy snapshot views) and per-tablespace via `MON_GET_TABLESPACE`; we standardize on `MON_GET_BUFFERPOOL` (consistent with the existing check).

> NOTE ON RESEARCH INPUTS: Of the eight files named in the task prompt, only `code-mysql-metrics.md` and the three `metadata.csv` files existed at the time of writing. The catalog parts (`db2-monget-catalog-*.md`), `db2-sysibmadm-views.md`, `db2-live-monget.md`, `db2-live-sysibmadm.md`, and `code-postgres-metrics.md` are **not yet staged** in `/home/bits/dd/integrations-core/ibm_db2/dev-docs/db2-fidelity-plan/_research/`. I substituted: the existing-check audit `code-ibm_db2-current.md` (exact current bufferpool code + column list), `db2-live-pkgcache.md` §6d (live-container confirmation of the `POOL_*` BIGINT counter families available on 12.1.4), the integration source code directly (`ibm_db2.py`, `queries.py`), and IBM 12.1 monitor-element documentation (URLs cited inline). Flag for the implementer: re-reconcile against `db2-monget-catalog-*.md` / `db2-live-monget.md` once staged, especially exact column availability for `POOL_COL_WRITES`, `POOL_CACHING_TIER_*`, and the GBP `POOL_*_GBP_INVALID_PAGES` families.

---

## 0. Source-of-truth references

**Code (current integration):**
- Buffer pool collector: `/home/bits/dd/integrations-core/ibm_db2/datadog_checks/ibm_db2/ibm_db2.py:192-377` (`query_buffer_pool`).
- SQL + selected columns: `/home/bits/dd/integrations-core/ibm_db2/datadog_checks/ibm_db2/queries.py:43-79` (`BUFFER_POOL_TABLE_COLUMNS`, `BUFFER_POOL_TABLE`).
- Metric prefix helper `self.m(...)` → `ibm_db2.<name>`: `ibm_db2.py:633-635`.
- Existing catalog rows: `/home/bits/dd/integrations-core/ibm_db2/metadata.csv:5-29` (24 bufferpool rows today).
- Tag construction `bufferpool:<bp_name>`: `ibm_db2.py:197-198`. Global `db:<db>` tag: `ibm_db2.py:48`.

**Code (analog integrations):**
- MySQL InnoDB buffer pool catalog: `/home/bits/dd/integrations-core/mysql/metadata.csv:30-47` (the `mysql.innodb.buffer_pool_*` family) and MyISAM key cache `:130-134`.
- MySQL InnoDB var→metric map: `/home/bits/dd/integrations-core/mysql/datadog_checks/mysql/const.py` (`INNODB_VARS` 81-100, `OPTIONAL_INNODB_VARS` 151-237; buffer-pool intent from `SHOW ENGINE INNODB STATUS` text — anti-pattern, see `code-mysql-metrics.md` §4).
- Postgres buffer/cache catalog: `/home/bits/dd/integrations-core/postgres/metadata.csv` — `postgresql.buffer_hit` (:32), `postgresql.bgwriter.buffers_*` (:20-27), `postgresql.buffercache.*` (:33-37, pg_buffercache ext), per-relation `heap_blocks_hit/read` (:75-76), `index_blocks_hit/read` (:77-81), `toast_*` (:211-214), `postgresql.io.hits/evictions` (:89-94, pg_stat_io PG16+), `recovery_prefetch.*` (:127-135), `slru.blks_*` (:180-184), `queries.shared_blks_*` / `local_blks_*` / `temp_blks_*` (:115-125, DBM per-query).

**IBM docs (12.1 monitor elements / table function):**
- `MON_GET_BUFFERPOOL` table function (12.1): https://www.ibm.com/docs/en/db2/12.1?topic=functions-mon-get-bufferpool-get-buffer-pool-metrics
- Buffer pool hit-ratio formulas (used by existing code): https://www.ibm.com/support/knowledgecenter/SSEPGG_11.1.0/com.ibm.db2.luw.admin.mon.doc/doc/r0056871.html
- Prefetching into the buffer pool (12.1): https://www.ibm.com/docs/en/db2/12.1.x?topic=management-prefetching-data-into-buffer-pool
- IBM "Db2 Prefetching — Understanding, Configuring, Monitoring, Tuning": https://www.ibm.com/support/pages/db2-prefetching-understanding-configuring-monitoring-tuning
- Buffer pool I/O metric catalog reference (dsmtop, confirms element→metric mapping): https://ibm.github.io/db2-dsmtop-wiki/IO-Bufferpools/
- Async index reads element: https://www.ibm.com/docs/SSEPGG_9.7.0/com.ibm.db2.luw.admin.mon.doc/doc/r0001247.html
- Live-container confirmation of available `POOL_*` counters on 12.1.4: `/home/bits/dd/integrations-core/ibm_db2/dev-docs/db2-fidelity-plan/_research/db2-live-pkgcache.md:281-289`.

**Member arg convention:** all existing built-in queries pass `-1`/`NULL` to aggregate across members (`queries.py:79`). For pureScale / DPF per-member fidelity, switch to a non-`-1` member arg and add a `member:` tag (see §6).

---

## 1. The four page classes and the `temp` overlay (Db2-specific structure)

Db2's buffer-pool counters are factored along two axes the implementer must keep straight:

1. **Page class** — 4 of them, each a separate column family:
   - `data` — regular table data pages.
   - `index` — index pages.
   - `xda` — XML storage object (XDA) pages.
   - `col` — column-organized (BLU/columnar) table data pages. (Db2-native; **no** pg/mysql analog. Only nonzero on column-organized tables.)
2. **Container kind** — for reads, each page class has both a regular counter (`pool_<class>_<x>_reads`) and a **temp** counter (`pool_temp_<class>_<x>_reads`) for system temporary table spaces. The existing check **sums regular+temp** into one logical/physical read number per class (`ibm_db2.py:204-209,241-247,278-284,315-321`). Keep that convention for backward compatibility; optionally add separate `*.temp.*` series (see §5, NEW-T).

There is no `temp` overlay for **writes** (temp pages are written via `pool_data_writes` etc.; Db2 does not break out temp writes per class), nor for pages_found.

The existing aggregate (`bufferpool.reads.*`, `bufferpool.hit_percent`) is the **sum of all four classes** per buffer pool (`ibm_db2.py:348-363`).

---

## 2. EXISTING ibm_db2 bufferpool metrics (already shipped — keep, do not rename)

These 24 metrics already exist (`metadata.csv:5-29`) and are emitted by `query_buffer_pool`. Listed here so the implementer preserves names/types and so the table in §3/§5 only proposes *new* work. All are tagged `bufferpool:<bp_name>` + `db:<db>` + user tags. `<x>` ∈ {column, data, index, xda}.

| ibm_db2 metric | type (csv) | MON_GET_BUFFERPOOL source | formula | code |
|---|---|---|---|---|
| `ibm_db2.bufferpool.<x>.reads.physical` | count (monotonic_count) | `pool_<x>_p_reads` + `pool_temp_<x>_p_reads` | sum | `ibm_db2.py:204-205,241-242,278-279,315-316` |
| `ibm_db2.bufferpool.<x>.reads.logical` | count | `pool_<x>_l_reads` + `pool_temp_<x>_l_reads` | sum | `:209-210,246-247,283-284,320-321` |
| `ibm_db2.bufferpool.<x>.reads.total` | count | physical + logical (above) | sum | `:213-215,250-252,287-289,324-326` |
| `ibm_db2.bufferpool.<x>.hit_percent` | gauge | `pool_<x>_lbp_pages_found` − `pool_async_<x>_lbp_pages_found`, ÷ logical reads × 100 | ratio, 0 if logical=0 | `:219-225,256-262,293-299,330-336` |
| `ibm_db2.bufferpool.reads.physical` | count | Σ over 4 classes of physical | sum | `:349-350` |
| `ibm_db2.bufferpool.reads.logical` | count | Σ over 4 classes of logical | sum | `:352-353` |
| `ibm_db2.bufferpool.reads.total` | count | physical + logical | sum | `:355-356` |
| `ibm_db2.bufferpool.hit_percent` | gauge | Σ pages_found ÷ Σ logical × 100 | ratio | `:358-363` |
| `ibm_db2.bufferpool.group.<x>.hit_percent` | gauge | `pool_<x>_gbp_l_reads`, `pool_<x>_gbp_p_reads` | (gbp_l − gbp_p)/gbp_l×100, pureScale-only (`# no cov`) | `:229-235,266-272,303-309,340-346` |
| `ibm_db2.bufferpool.group.hit_percent` | gauge | Σ gbp pages_found ÷ Σ gbp logical × 100 | ratio, pureScale-only | `:366-377` |

> Note: `reads.*` use the unit `get` in metadata.csv (`metadata.csv:6` etc.) — a Db2-ism ("logical reads" == "buffer pool gets"). New read-count metrics in this category should reuse `unit_name=get` for consistency, even though `page` would also be defensible.
> Note (existing bug, out of scope but flag): `ibm_db2.bufferpool.xda.hit_percent` description in `metadata.csv:26` wrongly says "index page request" — copy/paste error; fix when touching the file.

---

## 3. NEW metrics with a direct pg/mysql analog (add for parity)

These fill the biggest gaps versus mysql/postgres: **writes**, **page-cleaning/victim**, **prefetch/async**, **pool I/O time**, and **buffer-pool sizing/utilization**. All from `MON_GET_BUFFERPOOL` unless noted, tagged `bufferpool:<bp_name>` (+ `db`, + optional `member`).

### 3.1 Buffer pool WRITES (parity: mysql `buffer_pool_pages_flushed`/`write_requests`, pg `bgwriter.buffers_*`)

`MON_GET_BUFFERPOOL` exposes writes per page class. **These columns are NOT currently selected** (`queries.py:44-78` omits all `*_writes`) — add them.

| pg/mysql analog | Db2 source column | proposed ibm_db2 metric | type | unit / per_unit | tags | notes |
|---|---|---|---|---|---|---|
| `mysql.innodb.buffer_pool_pages_flushed`; pg `bgwriter.buffers_clean` | `POOL_DATA_WRITES` | `ibm_db2.bufferpool.data.writes` | count (monotonic_count) | page | bufferpool | # of data pages physically written from BP to disk |
| (index writes) | `POOL_INDEX_WRITES` | `ibm_db2.bufferpool.index.writes` | count | page | bufferpool | |
| (xda writes) | `POOL_XDA_WRITES` | `ibm_db2.bufferpool.xda.writes` | count | page | bufferpool | XDA page writes |
| (columnar writes) | `POOL_COL_WRITES` | `ibm_db2.bufferpool.column.writes` | count | page | bufferpool | columnar; Db2-native. **Verify column exists in 12.1 MON_GET_BUFFERPOOL** (named in dsmtop wiki; confirm against `db2-monget-catalog-*.md`) |
| `mysql.innodb.buffer_pool_write_requests` (aggregate) | Σ of the 4 above | `ibm_db2.bufferpool.writes.total` | count | page | bufferpool | computed sum, mirrors how `reads.total` aggregates |

### 3.2 Pool read/write TIME (parity: pg `wal.write_time`, mysql has none; rounds out hit-ratio with latency)

| pg/mysql analog | Db2 source column | proposed ibm_db2 metric | type | unit | tags | notes |
|---|---|---|---|---|---|---|
| pg `io.*_time` family (loosely) | `POOL_READ_TIME` | `ibm_db2.bufferpool.read_time` | count (monotonic_count) | millisecond | bufferpool | total elapsed time spent reading data+index pages from disk into BP. Pairs with physical reads for avg read latency. **Not currently selected** |
| — | `POOL_WRITE_TIME` | `ibm_db2.bufferpool.write_time` | count | millisecond | bufferpool | total time writing data+index pages to disk. **Not currently selected** |

> Derived gauge option (mirrors existing `ibm_db2.lock.wait` avg pattern at `ibm_db2.py:165-169`): `read_time / reads.physical` → `ibm_db2.bufferpool.read_time.avg` (gauge, ms). Optional; prefer shipping raw counters and computing in-app.

### 3.3 PREFETCH / ASYNC I/O (parity: mysql `buffer_pool_read_ahead*`; pg `recovery_prefetch.*`)

mysql tracks read-ahead (`buffer_pool_read_ahead`, `_read_ahead_evicted`, `_read_ahead_rnd` — `mysql/metadata.csv:38-40`). Db2's analogs are the **async (prefetcher) reads** and **unread prefetch pages**.

| pg/mysql analog | Db2 source column | proposed ibm_db2 metric | type | unit | tags | notes |
|---|---|---|---|---|---|---|
| `mysql.innodb.buffer_pool_read_ahead` (data) | `POOL_ASYNC_DATA_READS` | `ibm_db2.bufferpool.data.reads.async` | count | page | bufferpool | physical reads done by prefetchers (async). Compare to `reads.physical` for prefetch effectiveness. **Not currently selected** |
| (index read-ahead) | `POOL_ASYNC_INDEX_READS` | `ibm_db2.bufferpool.index.reads.async` | count | page | bufferpool | https://www.ibm.com/docs/SSEPGG_9.7.0/com.ibm.db2.luw.admin.mon.doc/doc/r0001247.html |
| (xda read-ahead) | `POOL_ASYNC_XDA_READS` | `ibm_db2.bufferpool.xda.reads.async` | count | page | bufferpool | |
| (col read-ahead) | `POOL_ASYNC_COL_READS` | `ibm_db2.bufferpool.column.reads.async` | count | page | bufferpool | columnar; verify presence |
| `mysql.innodb.buffer_pool_read_ahead_evicted` | `UNREAD_PREFETCH_PAGES` | `ibm_db2.bufferpool.unread_prefetch_pages` | count | page | bufferpool | prefetched pages removed before being read = wasted prefetch I/O. orientation **-1**. Per-BP. **Not currently selected** |
| `mysql.innodb.data_pending_reads`(loose) | `POOL_ASYNC_DATA_READ_REQS` | `ibm_db2.bufferpool.data.read_reqs.async` | count | request | bufferpool | # of async read requests (vs pages). Optional; pair with NUMPAGEBLOCK tuning |
| (prefetch wait) | `PREFETCH_WAIT_TIME` | `ibm_db2.bufferpool.prefetch_wait_time` | count | millisecond | bufferpool | time agents waited for prefetchers. orientation -1. Present on MON_GET_BUFFERPOOL in 12.1 |
| (prefetch wait count) | `PREFETCH_WAITS` | `ibm_db2.bufferpool.prefetch_waits` | count | wait | bufferpool | # of times an agent waited on a prefetch |

> Async **write** ratio counterpart: `POOL_ASYNC_DATA_WRITES`, `POOL_ASYNC_INDEX_WRITES`, `POOL_ASYNC_XDA_WRITES`, `POOL_ASYNC_COL_WRITES` → optional `ibm_db2.bufferpool.<x>.writes.async` (count, page). These are the page-cleaner-written pages (vs synchronous victim writes). Add as a set with §3.4 victim metrics for a complete page-cleaning picture.

### 3.4 VICTIM / page-cleaning (parity: mysql `buffer_pool_wait_free`)

| pg/mysql analog | Db2 source column | proposed ibm_db2 metric | type | unit | tags | notes |
|---|---|---|---|---|---|---|
| `mysql.innodb.buffer_pool_wait_free` | `POOL_NO_VICTIM_BUFFER` | `ibm_db2.bufferpool.no_victim_buffer` | count | operation | bufferpool | # of times an agent could not find a victim (free/clean) buffer and had to do synchronous work. High = BP pressure / insufficient page cleaning. orientation -1. **Not currently selected** |

### 3.5 Buffer pool SIZE / configuration (parity: mysql `buffer_pool_pages_total`/`_free`/`_data`, pg `buffercache.*`)

mysql exposes BP page totals/free/data (`mysql/metadata.csv:33-37,43-45`). Db2 exposes current configured size and resize state.

| pg/mysql analog | Db2 source column | proposed ibm_db2 metric | type | unit | tags | notes |
|---|---|---|---|---|---|---|
| `mysql.innodb.buffer_pool_pages_total` | `BP_CUR_BUFFSZ` | `ibm_db2.bufferpool.pages.configured` | gauge | page | bufferpool | current size of this BP in pages. NB: page size varies per BP — to get bytes, join page size (see caveat). **Not currently selected** |
| (resize in flight) | `BP_PAGES_LEFT_TO_REMOVE` | `ibm_db2.bufferpool.pages.left_to_remove` | gauge | page | bufferpool | pages still to remove during an in-progress shrink; usually 0. Optional |
| (tablespace assoc.) | `BP_TBSP_USE_COUNT` | `ibm_db2.bufferpool.tablespaces` | gauge | tablespace | bufferpool | # table spaces mapped to this BP. Optional |

> **No direct Db2 BP analog** for mysql `buffer_pool_pages_free`, `buffer_pool_pages_dirty`, `buffer_pool_bytes_data` at the `MON_GET_BUFFERPOOL` grain — Db2 does not report current free/dirty page counts per pool through this function. Closest is database-level `MON_GET_DATABASE` (memory pool) / `MON_GET_MEMORY_POOL`/`MON_GET_MEMORY_SET` (covered by the *memory* category, not here). Flag as pg/mysql-only for the bufferpool category. See §7.

---

## 4. Block / Vectored I/O (Db2-native, partial mysql analog)

Db2 reports prefetch I/O efficiency via block vs vectored I/O — finer than mysql/pg. Worth adding for prefetch tuning dashboards.

| Db2 source column | proposed ibm_db2 metric | type | unit | tags | notes |
|---|---|---|---|---|---|
| `VECTORED_IOS` | `ibm_db2.bufferpool.vectored_ios` | count | operation | bufferpool | # of vectored I/O read requests by prefetchers |
| `PAGES_FROM_VECTORED_IOS` | `ibm_db2.bufferpool.pages_from_vectored_ios` | count | page | bufferpool | pages read via vectored I/O |
| `BLOCK_IOS` | `ibm_db2.bufferpool.block_ios` | count | operation | bufferpool | # of block I/O read requests (sequential prefetch into block area) |
| `PAGES_FROM_BLOCK_IOS` | `ibm_db2.bufferpool.pages_from_block_ios` | count | page | bufferpool | pages read via block I/O; pair with `unread_prefetch_pages` to tune NUMPAGEBLOCK |
| `FILES_CLOSED` | `ibm_db2.bufferpool.files_closed` | count | operation | bufferpool | times a container file was closed (descriptor pressure). Already used as the **conf.yaml.example custom-query sample** (`code-ibm_db2-current.md` §8 — `ibm_db2.tablespace.files_closed`); promote to a first-class BP metric |

Source confirmation of element names/semantics: https://ibm.github.io/db2-dsmtop-wiki/IO-Bufferpools/ ("Block IOs/s, Pages BlkIOs/s, Vectored IOs/s, Pages VctIOs/s, Victim Pages/s, Unread PrefPages/s, Files Closed/s").

---

## 5. Db2-native bufferpool metrics with NO pg/mysql analog (worth adding)

| category | Db2 source column(s) | proposed ibm_db2 metric | type | unit | tags | notes |
|---|---|---|---|---|---|---|
| Columnar (BLU) | `POOL_COL_L_READS`/`_P_READS`/`_LBP_PAGES_FOUND` | `ibm_db2.bufferpool.column.*` | (already shipped, see §2) | get / percent | bufferpool | the entire `column` class is Db2-native; pg/mysql have no column-organized BP |
| **NEW-T** temp split | `POOL_TEMP_<x>_L_READS`/`_P_READS` | `ibm_db2.bufferpool.<x>.temp.reads.logical`/`.physical` | count | get | bufferpool | optional: split the temp overlay the existing code currently folds into the regular read counters (§1). Lets you see system-temp BP pressure separately. **Behavior change risk:** do NOT subtract temp from existing metrics; add as *additional* series |
| Caching tier (multi-tier storage / Db2 Warehouse) | `POOL_DATA_GBP_INDEP_READS`… and `POOL_CACHING_TIER_*` family (`POOL_DATA_CACHING_TIER_L_READS`, `..._GBP_L_READS`, `POOL_CACHING_TIER_PAGE_WRITES`, etc.) | `ibm_db2.bufferpool.caching_tier.*` | count | get / page | bufferpool | only relevant on systems with a caching tier (SSD tier); all-zero otherwise. Confirmed present in 12.1 element families (`db2-pkgcache.md:287`). Gate behind a config flag; low priority |
| Page reclaim (pureScale) | `POOL_DATA_GBP_INVALID_PAGES`, `POOL_INDEX_GBP_INVALID_PAGES`, `POOL_XDA_GBP_INVALID_PAGES`, `POOL_COL_GBP_INVALID_PAGES` | `ibm_db2.bufferpool.group.<x>.invalid_pages` | count | page | bufferpool | pureScale GBP cross-invalidation pressure. pureScale-only; gate like existing `group.*` (§6) |
| Group async/independent reads (pureScale) | `POOL_ASYNC_DATA_GBP_L_READS`/`_P_READS`, `POOL_DATA_GBP_INDEP_PAGES_FOUND_IN_LBP` | `ibm_db2.bufferpool.group.<x>.reads.async` etc. | count | page | bufferpool | pureScale GBP detail; low priority |

---

## 6. pureScale / DPF member dimension (cross-cutting caveat)

- Existing code passes `-1`/`NULL` (`queries.py:79`) → **aggregates across all members**; existing `group.*` metrics are emitted but **untagged by member** (`code-ibm_db2-current.md` §14). On a single-node container (our 12.1.4) the GBP columns are all NULL/0, so `group.*` paths are `# no cov` (`ibm_db2.py:233,270,307,344,372`).
- For real pureScale/DPF fidelity: change the member arg to enumerate members (or pass each member id) and add a **`member:<n>`** tag to all bufferpool metrics. `MON_GET_BUFFERPOOL` returns a `MEMBER` column when not aggregating. This is a tag-cardinality decision — gate behind a config option (e.g. `collect_per_member`), mirroring mysql's per-object gating (`code-mysql-metrics.md` §2).
- All `group.*` / `*_gbp_*` / `*_invalid_pages` metrics are **version/edition-gated**: only meaningful in **pureScale**. Keep the existing "emit only if `gbp_l_reads` truthy" guard (`ibm_db2.py:233` etc.) for new GBP metrics too.

---

## 7. pg/mysql bufferpool metrics with NO Db2 (MON_GET_BUFFERPOOL) equivalent — flag, do not invent

| analog metric(s) | why no Db2 BP equivalent | nearest Db2 (other category) |
|---|---|---|
| `mysql.innodb.buffer_pool_pages_free`, `_pages_dirty`, `_bytes_dirty`, `_bytes_free`, `buffer_pool_utilization` | `MON_GET_BUFFERPOOL` does not report current free/dirty page counts | `MON_GET_MEMORY_POOL` / `MON_GET_MEMORY_SET` (memory category) report BP memory allocation, not free/dirty page counts. Dirty-page pressure is observable indirectly via `POOL_NO_VICTIM_BUFFER` (§3.4) and page-cleaner async writes (§3.3) |
| `mysql.innodb.buffer_pool_read_ahead_rnd` | Db2 has no "random read-ahead" concept | n/a (Db2 prefetch is sequential/list/readahead, not "random") |
| `mysql.myisam.key_*` (key cache) | Db2 has no separate index key cache; indexes use the buffer pool (`index` class) | already covered by `ibm_db2.bufferpool.index.*` |
| `postgresql.buffercache.*` (pg_buffercache: dirty/unused/used/pinning/usage_count per relation) | requires the pg_buffercache extension's per-buffer introspection; Db2 has no per-buffer relation map exposed via MON_GET | no direct analog; do not attempt |
| `postgresql.bgwriter.buffers_backend_fsync`, `maxwritten_clean`, `buffers_alloc` | postgres bgwriter internals | partial: page-cleaner activity via async writes (§3.3) / `no_victim_buffer` (§3.4); not a 1:1 mapping |
| `postgresql.recovery_prefetch.*` (WAL recovery prefetch, skip_fpw/skip_init/etc.) | postgres crash-recovery-specific WAL prefetch | n/a — Db2 redo/recovery prefetch is not exposed at BP grain via MON_GET_BUFFERPOOL |
| `postgresql.slru.blks_*` | postgres SLRU caches (commit/multixact) | n/a — Db2 has no SLRU subsystem |
| `postgresql.io.hits`/`evictions` (pg_stat_io, PG16+, per backend_type/context/object) | pg's unified per-context I/O view | partial: Db2 has per-object I/O via `MON_GET_TABLE`/`MON_GET_INDEX`/`MON_GET_CONTAINER` (object category), not at BP grain |
| `postgresql.queries.shared_blks_hit/read/written/dirtied`, `temp_blks_*`, `local_blks_*` (DBM per-query) | postgres DBM per-statement block accounting | **Db2 HAS the analog but in the statement/DBM category, not here:** `MON_GET_PKG_CACHE_STMT[_DETAILS]` exposes `POOL_DATA_L_READS`, `POOL_DATA_P_READS`, `POOL_INDEX_L_READS/P_READS`, `POOL_*_WRITES`, `DIRECT_READS/WRITES` per statement (`db2-live-pkgcache.md:282-288`). Map there, not in the bufferpool category |

---

## 8. Direct I/O (bypasses buffer pool) — boundary note

`DIRECT_READS`, `DIRECT_READ_REQS`, `DIRECT_WRITES`, `DIRECT_WRITE_REQS`, `DIRECT_READ_TIME`, `DIRECT_WRITE_TIME` are on `MON_GET_BUFFERPOOL` (and `MON_GET_DATABASE`/`MON_GET_TABLESPACE`) but are **non-buffered** I/O (LOBs/LONG VARCHAR, backup/restore, load). They belong to a generic **I/O** metric category, not bufferpool. The activity research already surfaces them at the activity/statement grain (`db2-live-activity.md:209,298,308,324`). Recommendation: emit `ibm_db2.bufferpool.direct.reads/writes[/_reqs/_time]` only if a dedicated I/O category does not own them; otherwise defer. Flag for the I/O-category mapper to claim.

---

## 9. SQL the implementer will run (proposed expanded SELECT)

Replace the column tuple in `queries.py:44-78` (`BUFFER_POOL_TABLE_COLUMNS`) with the existing 32 columns **plus** the new ones below (member arg stays `(NULL, -1)` until per-member is implemented):

```sql
SELECT
  bp_name,
  member,                                    -- add when per-member enabled
  -- existing read/pages_found columns (keep all 31 already selected) ...
  -- NEW writes:
  pool_data_writes, pool_index_writes, pool_xda_writes, pool_col_writes,
  -- NEW pool I/O time:
  pool_read_time, pool_write_time,
  -- NEW prefetch / async:
  pool_async_data_reads, pool_async_index_reads, pool_async_xda_reads, pool_async_col_reads,
  pool_async_data_read_reqs,
  unread_prefetch_pages, prefetch_wait_time, prefetch_waits,
  -- NEW async writes (page cleaners):
  pool_async_data_writes, pool_async_index_writes, pool_async_xda_writes, pool_async_col_writes,
  -- NEW victim / page cleaning:
  pool_no_victim_buffer,
  -- NEW block/vectored I/O:
  vectored_ios, pages_from_vectored_ios, block_ios, pages_from_block_ios, files_closed,
  -- NEW sizing:
  bp_cur_buffsz, bp_pages_left_to_remove, bp_tbsp_use_count
  -- pureScale GBP (gate): pool_*_gbp_invalid_pages, pool_async_*_gbp_*
FROM TABLE(MON_GET_BUFFERPOOL(NULL, -1))
```

All columns are BIGINT counters except `bp_name` (VARCHAR), `member` (SMALLINT), `bp_cur_buffsz`/`bp_pages_left_to_remove`/`bp_tbsp_use_count` (BIGINT, point-in-time → gauge). Column availability on 12.1.4 is confirmed for the `POOL_*` families in `db2-live-pkgcache.md:281-289`; verify the exact set against `db2-monget-catalog-*.md` once staged.

---

## 10. metadata.csv rows to add (ready to paste; `integration=ibm_db2`)

Format: `metric_name,metric_type,interval,unit_name,per_unit_name,description,orientation,integration,short_name,curated_metric`. Counters use csv type `count` (submitted via `monotonic_count`), point-in-time use `gauge`. `<x>` expands to column/data/index/xda.

```
ibm_db2.bufferpool.data.writes,count,,page,,The number of data pages physically written from the buffer pool to disk.,0,ibm_db2,,
ibm_db2.bufferpool.index.writes,count,,page,,The number of index pages physically written from the buffer pool to disk.,0,ibm_db2,,
ibm_db2.bufferpool.xda.writes,count,,page,,The number of XDA pages physically written from the buffer pool to disk.,0,ibm_db2,,
ibm_db2.bufferpool.column.writes,count,,page,,The number of column-organized data pages physically written from the buffer pool to disk.,0,ibm_db2,,
ibm_db2.bufferpool.writes.total,count,,page,,The total number of pages physically written from the buffer pool to disk.,0,ibm_db2,,
ibm_db2.bufferpool.read_time,count,,millisecond,,The total elapsed time spent reading data and index pages from disk into the buffer pool.,-1,ibm_db2,,
ibm_db2.bufferpool.write_time,count,,millisecond,,The total elapsed time spent writing data and index pages from the buffer pool to disk.,-1,ibm_db2,,
ibm_db2.bufferpool.data.reads.async,count,,page,,The number of data pages read asynchronously into the buffer pool by prefetchers.,0,ibm_db2,,
ibm_db2.bufferpool.index.reads.async,count,,page,,The number of index pages read asynchronously into the buffer pool by prefetchers.,0,ibm_db2,,
ibm_db2.bufferpool.xda.reads.async,count,,page,,The number of XDA pages read asynchronously into the buffer pool by prefetchers.,0,ibm_db2,,
ibm_db2.bufferpool.column.reads.async,count,,page,,The number of column-organized data pages read asynchronously into the buffer pool by prefetchers.,0,ibm_db2,,
ibm_db2.bufferpool.unread_prefetch_pages,count,,page,,The number of pages that were prefetched into the buffer pool but never read before being removed (wasted prefetch I/O).,-1,ibm_db2,,
ibm_db2.bufferpool.data.read_reqs.async,count,,request,,The number of asynchronous read requests issued by prefetchers for data pages.,0,ibm_db2,,
ibm_db2.bufferpool.prefetch_wait_time,count,,millisecond,,The time agents spent waiting for prefetchers to finish reading pages into the buffer pool.,-1,ibm_db2,,
ibm_db2.bufferpool.prefetch_waits,count,,wait,,The number of times an agent waited for a prefetcher to finish reading pages.,-1,ibm_db2,,
ibm_db2.bufferpool.data.writes.async,count,,page,,The number of data pages written asynchronously to disk by page cleaners.,0,ibm_db2,,
ibm_db2.bufferpool.index.writes.async,count,,page,,The number of index pages written asynchronously to disk by page cleaners.,0,ibm_db2,,
ibm_db2.bufferpool.xda.writes.async,count,,page,,The number of XDA pages written asynchronously to disk by page cleaners.,0,ibm_db2,,
ibm_db2.bufferpool.column.writes.async,count,,page,,The number of column-organized data pages written asynchronously to disk by page cleaners.,0,ibm_db2,,
ibm_db2.bufferpool.no_victim_buffer,count,,operation,,The number of times an agent could not find a usable victim buffer and had to perform synchronous work to free one.,-1,ibm_db2,,
ibm_db2.bufferpool.vectored_ios,count,,operation,,The number of vectored I/O read requests performed by prefetchers.,0,ibm_db2,,
ibm_db2.bufferpool.pages_from_vectored_ios,count,,page,,The total number of pages read into the buffer pool by vectored I/O.,0,ibm_db2,,
ibm_db2.bufferpool.block_ios,count,,operation,,The number of block I/O read requests performed by prefetchers.,0,ibm_db2,,
ibm_db2.bufferpool.pages_from_block_ios,count,,page,,The total number of pages read into the buffer pool by block I/O.,0,ibm_db2,,
ibm_db2.bufferpool.files_closed,count,,operation,,The number of times a database container file was closed.,0,ibm_db2,,
ibm_db2.bufferpool.pages.configured,gauge,,page,,The current size of the buffer pool in pages.,0,ibm_db2,,
ibm_db2.bufferpool.pages.left_to_remove,gauge,,page,,The number of pages still to be removed from the buffer pool during an in-progress resize.,0,ibm_db2,,
ibm_db2.bufferpool.tablespaces,gauge,,tablespace,,The number of table spaces mapped to this buffer pool.,0,ibm_db2,,
ibm_db2.bufferpool.group.column.invalid_pages,count,,page,,(pureScale) The number of column-organized pages invalidated in the group buffer pool.,-1,ibm_db2,,
ibm_db2.bufferpool.group.data.invalid_pages,count,,page,,(pureScale) The number of data pages invalidated in the group buffer pool.,-1,ibm_db2,,
ibm_db2.bufferpool.group.index.invalid_pages,count,,page,,(pureScale) The number of index pages invalidated in the group buffer pool.,-1,ibm_db2,,
ibm_db2.bufferpool.group.xda.invalid_pages,count,,page,,(pureScale) The number of XDA pages invalidated in the group buffer pool.,-1,ibm_db2,,
```

(Optional NEW-T temp-split rows and `caching_tier.*` rows omitted from the paste block — add only if those collectors are implemented.)

---

## 11. Implementation notes / caveats summary

1. **Type discipline** (per `code-mysql-metrics.md` §11, `code-ibm_db2-current.md` §4.6): lifetime `MON_GET` counters → `monotonic_count` (csv `count`); point-in-time (`bp_cur_buffsz`, `bp_pages_left_to_remove`, hit_percent) → `gauge`. Existing reads use csv unit `get`; new write/prefetch counters use `page`; times use `millisecond`.
2. **Backward compatibility:** do NOT change how existing `reads.*` fold regular+temp (§1). Add temp-split as *new* series only.
3. **Page-size for bytes:** `bp_cur_buffsz` is in pages; page size differs per buffer pool. To emit a byte gauge you must join the BP's page size (not on `MON_GET_BUFFERPOOL`; via `SYSCAT.BUFFERPOOLS.PAGESIZE` or `MON_GET_TABLESPACE.tbsp_page_size` for tablespaces in the pool). Prefer emitting `pages.configured` (page unit) and let dashboards multiply, mirroring how the existing `tablespace.size` does the page×page_size math in code (`ibm_db2.py:389+`).
4. **pureScale gating:** keep the `if <gbp>_reads_logical:` guard pattern (`ibm_db2.py:233` etc.) for all new GBP/invalid_pages metrics; they are NULL/0 on non-pureScale (our 12.1.4 container).
5. **Graceful degradation:** if a new column is absent on an older/edition-restricted server, the whole `SELECT` fails → `query_buffer_pool` is swallowed at WARNING (`ibm_db2.py:82-91`). Mitigation: 12.1 is the target and all columns above are 12.1-present, but if supporting <12.1, gate columns by version (mirror mysql `version_compatible`, `code-mysql-metrics.md` §2). Confirm exact column set against `db2-monget-catalog-*.md`/`db2-live-monget.md` when staged.
6. **Avg-latency derivations** (`read_time/reads.physical`, `write_time/data.writes`) follow the existing `lock.wait` average pattern (`ibm_db2.py:165-169`) — optional gauges; prefer shipping raw counters.
7. **Cardinality:** per-`bufferpool` tag is already low-cardinality (handful of pools). Adding `member:` multiplies by member count — gate behind config (§6).
8. **`files_closed` promotion:** it is currently the documented custom-query example (`conf.yaml.example`, `code-ibm_db2-current.md` §8) as `ibm_db2.tablespace.files_closed` from `MON_GET_TABLESPACE`. New first-class metric `ibm_db2.bufferpool.files_closed` from `MON_GET_BUFFERPOOL` does not collide (different prefix + source). Note the duplication in release notes.
