# Metric-Category Map — TABLES & INDEXES (per-table / per-index)

Scope of THIS category: per-table activity & footprint (rows read/written, table scans,
overflow accesses/creates, page reorgs, data/index page footprint, table-scope lock waits)
and per-index activity & structure (index scans / index-only scans, key updates, leaf-page
count, B-tree depth, node splits, pseudo-delete / cleanup, index bufferpool reads). Db2
sources are `MON_GET_TABLE` and `MON_GET_INDEX` (the per-object monitoring table functions),
with `SYSCAT.TABLES` / `SYSCAT.INDEXES` for catalog inventory (table count) and labels
(index name). This is the Db2 analog of Postgres' `relations` per-relation metrics
(`pg_stat_user_tables`, `pg_stat_user_indexes`, `pg_class`, `pg_statio_user_tables`) and
MySQL's per-table / per-index metrics (`information_schema`, `performance_schema`,
`mysql.innodb_index_stats`).

**Cardinality is the defining constraint of this category.** Every metric here is one time
series *per object per member*. Postgres and MySQL gate the equivalents behind config
(`relations` / `index_config.enabled`) and cap with `LIMIT` / `max_relations`. Db2 must do
the same: a config gate + top-N cap (`FETCH FIRST n ROWS ONLY` / `ORDER BY <activity> DESC`)
+ schema include/exclude filtering. The existing `ibm_db2` integration emits **zero**
per-table / per-index metrics today (it aggregates only to instance/db/bufferpool/tablespace/log;
`code-ibm_db2-current.md:359,366`).

## Sources read / provenance

- Postgres metric collection: `/home/bits/dd/integrations-core/postgres/datadog_checks/postgres/relationsmanager.py`,
  `.../postgres/util.py`, `/home/bits/dd/integrations-core/postgres/metadata.csv`
  (rows 68–216 are the relation/table/index/toast family).
- MySQL metric collection: `/home/bits/dd/integrations-core/mysql/datadog_checks/mysql/index_metrics.py`,
  `.../mysql/queries.py`, `/home/bits/dd/integrations-core/mysql/metadata.csv` (rows 20–28 index/table).
- Db2 `MON_GET_TABLE` columns: live `DESCRIBE` dump
  `/home/bits/dd/integrations-core/ibm_db2/dev-docs/db2-fidelity-plan/_research/_raw/02-monget-key-columns.txt:1521-1613`
  (91 columns) — every column name/type below transcribed verbatim with line cite.
- Db2 `MON_GET_INDEX` columns: same raw file `:1621-1657` (35 columns).
- Function availability: `_raw/01-version-and-monget-functions.txt` (live `DB2 v12.1.4.0`):
  `MON_GET_TABLE` (L60), `MON_GET_INDEX` (L34), `MON_GET_TABLE_USAGE_LIST` (L64),
  `MON_GET_INDEX_USAGE_LIST` (L35), `MON_GET_PAGE_ACCESS_INFO` (L41) all confirmed present.
- SYSIBMADM views: `_raw/03-sysibmadm-objects.txt` — `ADMINTABINFO` (L10), `ADMINTABCOMPRESSINFO` (L9),
  `SNAPTAB` (L77), `SNAPTAB_REORG` (L78) present.
- Monitor-switch gating: `_raw/04-monitor-config.txt` — `mon_obj_metrics=EXTENDED` (populates
  the object data/index page counters), `mon_act_metrics=BASE`, `mon_req_metrics=BASE`.
- Catalog inventory column names: `code-postgres-dbm-metadata-schemas.md:525-535`
  (`SYSCAT.TABLES`: `TABSCHEMA,TABNAME,TYPE,CARD,NPAGES,FPAGES`; `SYSCAT.INDEXES`:
  `INDSCHEMA,INDNAME,TABSCHEMA,TABNAME,IID,UNIQUERULE,...`).
- Naming conventions / overlap: `map-rows-throughput.md` owns the DB-aggregate row counters
  (`ibm_db2.row.*` from `MON_GET_DATABASE`); THIS doc owns the per-table/per-index fan-out
  (`ibm_db2.table.*`, `ibm_db2.index.*`). They are complementary, not duplicate.

**Monitor-switch caveat (load-bearing):** `MON_GET_TABLE` row activity counters
(`ROWS_READ`, `TABLE_SCANS`, etc.) require `mon_obj_metrics` ≠ `NONE`; the bufferpool-read
object columns (`OBJECT_DATA_*_READS`, `OBJECT_INDEX_*_READS`) and `MON_GET_INDEX` access
counters require `mon_obj_metrics=EXTENDED` (live setting is `EXTENDED`,
`_raw/04-monitor-config.txt:15`). If a site sets `mon_obj_metrics=NONE` these columns return
0/NULL — gate gracefully and document.

**Unit conventions (general Db2 12.1 knowledge — verify):** `*_TIME` counters are
**milliseconds**; `*_VOLUME` are **bytes**; `*_L_PAGES` / `*_P_READS` / `*_L_READS` / `NLEAF`
are **pages** (count); row/scan/split/update counters are monotonic **counts** since database
activation (per member). Recommended types: lifetime monotonic counters → `monotonic_count`
(CSV `count`); point-in-time structural sizes (`NLEAF`, `NLEVELS`, `*_L_PAGES`) → `gauge`.

---

## A. MAPPING TABLE — TABLES (`MON_GET_TABLE`)

Source object for all rows: `MON_GET_TABLE(tabschema, tabname, member)`; pass
`NULL,NULL,-2` for all tables/all members (general Db2 12.1 knowledge — verify signature).
One row per (table, data partition, member). Common tags for **every** row below:
`db`, `schema` (=`TABSCHEMA`), `table` (=`TABNAME`), `member` (=`MEMBER`); optionally
`tab_organization` (`TAB_ORGANIZATION` 'R' row / 'C' column) and `data_partition_id`.
Proposed config gate: `collect_table_metrics` (default OFF) + `table_metrics_limit`
(default ~300, mirroring Postgres `max_relations`) + schema include/exclude.

| pg/mysql analog metric | Db2 source (fn + exact column) | proposed `ibm_db2.<name>` | type | unit | tags | notes / version-gating |
|---|---|---|---|---|---|---|
| `pg seq_scans` (`postgresql.seq_scans`, relations); `pg index_rel_scans` partial | `MON_GET_TABLE.TABLE_SCANS` (`02-monget-key-columns.txt:1532`) | `ibm_db2.table.scans` | count | scan | db,schema,table,member | Closest analog to seq scans. Postgres separates seq vs index scans; Db2 `TABLE_SCANS` counts table (relation) scans. orientation 0. |
| `pg seq_rows_read` (`postgresql.seq_rows_read`); `mysql.info.table.rows.read` (`mysql.info.table.rows.read`) | `MON_GET_TABLE.ROWS_READ` (`:1533`) | `ibm_db2.table.rows_read` | count | row | db,schema,table,member | Per-table breakdown of the DB-level `ibm_db2.row.reads.total`. High-signal for hot-table detection. orientation 0. |
| `pg rows_inserted` (`postgresql.rows_inserted`, relations); `mysql.innodb.rows_inserted` | `MON_GET_TABLE.ROWS_INSERTED` (`:1534`) | `ibm_db2.table.rows_inserted` | count | row | db,schema,table,member | Per-table; complements DB-level `ibm_db2.row.inserted.total` (map-rows-throughput). orientation 0. |
| `pg rows_updated` (`postgresql.rows_updated`, relations); `mysql.innodb.rows_updated` | `MON_GET_TABLE.ROWS_UPDATED` (`:1535`) | `ibm_db2.table.rows_updated` | count | row | db,schema,table,member | orientation 0. |
| `pg rows_deleted` (`postgresql.rows_deleted`, relations); `mysql.innodb.rows_deleted` | `MON_GET_TABLE.ROWS_DELETED` (`:1536`) | `ibm_db2.table.rows_deleted` | count | row | db,schema,table,member | orientation 0. |
| `mysql.info.table.rows.changed` (Percona userstat) | derived: `ROWS_INSERTED+ROWS_UPDATED+ROWS_DELETED` (or emit separately) | (n/a — prefer 3 separate metrics) | — | — | — | Do NOT pre-sum; emit the 3 above and let dashboards aggregate (matches Postgres). |
| — (Db2-native; loosely `pg n_tup_upd` vs HOT) | `MON_GET_TABLE.NO_CHANGE_UPDATES` (`:1546`) | `ibm_db2.table.no_change_updates` | count | update | db,schema,table,member | NEW Db2-native: updates where no column value actually changed (write-amplification signal). Optional. orientation 0. |
| — (Db2-native; row-overflow, no pg/mysql analog) | `MON_GET_TABLE.OVERFLOW_ACCESSES` (`:1537`) | `ibm_db2.table.overflow_accesses` | count | access | db,schema,table,member | NEW. Reads of overflowed (relocated) rows; high values ⇒ REORG needed. orientation -1. No Postgres/MySQL equivalent. |
| — (Db2-native) | `MON_GET_TABLE.OVERFLOW_CREATES` (`:1538`) | `ibm_db2.table.overflow_creates` | count | row | db,schema,table,member | NEW. Rows that became overflow records (update made row too big for its page). orientation -1. |
| — (Db2-native; loosely `pg autovacuum` intent) | `MON_GET_TABLE.PAGE_REORGS` (`:1539`) | `ibm_db2.table.page_reorgs` | count | reorg | db,schema,table,member | NEW. Online page reorganizations triggered by inserts/updates. Fragmentation signal. orientation -1. |
| — (Db2-native; RUNSTATS staleness) | `MON_GET_TABLE.STATS_ROWS_MODIFIED` (`:1576`) | `ibm_db2.table.stats_rows_modified` | count | row | db,schema,table,member | NEW. Rows modified since last RUNSTATS (proxy for "stats getting stale"). Optional. orientation 0. |
| — (Db2-native; RTS) | `MON_GET_TABLE.RTS_ROWS_MODIFIED` (`:1577`) | `ibm_db2.table.rts_rows_modified` | count | row | db,schema,table,member | NEW. Rows modified since last real-time-stats sample. Optional. orientation 0. |
| `pg relation.pages` / `relation_size`; `mysql.info.table.data_size` | `MON_GET_TABLE.DATA_OBJECT_L_PAGES` (`:1540`) | `ibm_db2.table.data_object_pages` | gauge | page | db,schema,table,member | Data-object logical page footprint. Multiply by tablespace PAGESIZE for bytes (see §C size note). orientation 0. |
| `pg index_size` (per-table sum) | `MON_GET_TABLE.INDEX_OBJECT_L_PAGES` (`:1543`) | `ibm_db2.table.index_object_pages` | gauge | page | db,schema,table,member | Index-object page footprint for the table's indexes (aggregate). orientation 0. |
| `pg toast_size` (loosely; LOB footprint) | `MON_GET_TABLE.LOB_OBJECT_L_PAGES` (`:1541`) | `ibm_db2.table.lob_object_pages` | gauge | page | db,schema,table,member | NEW. LOB storage object pages (nearest to Postgres TOAST size). orientation 0. |
| — | `MON_GET_TABLE.LONG_OBJECT_L_PAGES` (`:1542`) | `ibm_db2.table.long_object_pages` | gauge | page | db,schema,table,member | NEW. LONG VARCHAR/VARGRAPHIC storage. Optional. orientation 0. |
| — | `MON_GET_TABLE.XDA_OBJECT_L_PAGES` (`:1544`) | `ibm_db2.table.xda_object_pages` | gauge | page | db,schema,table,member | NEW. XML storage object pages. Optional. orientation 0. |
| — (column-organized; Db2-native) | `MON_GET_TABLE.COL_OBJECT_L_PAGES` (`:1578`) | `ibm_db2.table.col_object_pages` | gauge | page | db,schema,table,member | NEW. Column-organized (BLU) data pages. Only meaningful when `TAB_ORGANIZATION='C'`. Optional. orientation 0. |
| — (no analog; table-scope locks) | `MON_GET_TABLE.LOCK_WAIT_TIME` (`:1547`) | `ibm_db2.table.lock_wait_time` | count | millisecond | db,schema,table,member | NEW. Cumulative lock-wait time attributed to this table. Pairs with `lock_waits`. orientation -1. (Postgres locks are not per-relation-rolled-up the same way; MySQL `table_locks_waited` is server-wide.) |
| `mysql.performance.table_locks_waited` (server-wide; Db2 is per-table) | `MON_GET_TABLE.LOCK_WAITS` (`:1549`) | `ibm_db2.table.lock_waits` | count | lock | db,schema,table,member | NEW. Lock waits on this table. orientation -1. Better granularity than MySQL's global counter. |
| — (Db2-native lock escalation) | `MON_GET_TABLE.LOCK_ESCALS` (`:1551`) | `ibm_db2.table.lock_escals` | count | lock | db,schema,table,member | NEW. Row→table lock escalations on this table. orientation -1. Optional. |
| `pg heap_blocks_read`/`heap_blocks_hit` intent | `MON_GET_TABLE.OBJECT_DATA_L_READS` (`:1561`) / `OBJECT_DATA_P_READS` (`:1562`) | `ibm_db2.table.data.reads.logical` / `ibm_db2.table.data.reads.physical` | count | page | db,schema,table,member | Per-table bufferpool data-page reads. Logical−physical ≈ buffer hits (Postgres heap_blocks_hit analog). Requires `mon_obj_metrics=EXTENDED`. orientation 0. |
| `pg index_blocks_read` (per-table aggregate) | (NOTE: per-table index reads live in `MON_GET_INDEX`, not `MON_GET_TABLE`) | — | — | — | — | `MON_GET_TABLE` has no `OBJECT_INDEX_*` columns; see §B `OBJECT_INDEX_*_READS`. Flagged to avoid mis-mapping. |
| — (XDA bufferpool reads) | `MON_GET_TABLE.OBJECT_XDA_L_READS` (`:1568`) / `OBJECT_XDA_P_READS` (`:1569`) | `ibm_db2.table.xda.reads.logical` / `.physical` | count | page | db,schema,table,member | NEW. Optional (XML workloads only). orientation 0. |
| — (column-organized bufferpool reads) | `MON_GET_TABLE.OBJECT_COL_L_READS` (`:1580`) / `OBJECT_COL_P_READS` (`:1581`) | `ibm_db2.table.col.reads.logical` / `.physical` | count | page | db,schema,table,member | NEW. BLU/column-organized only. Optional. orientation 0. |
| `pg.io.reads` (per-relation direct I/O intent) | `MON_GET_TABLE.DIRECT_READS` (`:1559`) / `DIRECT_WRITES` (`:1557`) | `ibm_db2.table.direct_reads` / `ibm_db2.table.direct_writes` | count | page | db,schema,table,member | NEW. Direct (non-bufferpool) I/O for LOB/LONG access. Optional; overlaps `map-io-disk`. orientation 0. |

### Db2-native TABLE metrics worth adding (no pg/mysql analog) — summary
- `OVERFLOW_ACCESSES` / `OVERFLOW_CREATES` / `PAGE_REORGS` — fragmentation / REORG-need
  signals unique to Db2's slotted-page + overflow-record model. **Highest-value Db2-native
  additions** (Postgres surfaces this only indirectly via bloat; MySQL not at all).
- `NO_CHANGE_UPDATES` — write-amplification / no-op update detection.
- `STATS_ROWS_MODIFIED` / `RTS_ROWS_MODIFIED` — RUNSTATS / real-time-stats staleness.
- `LOCK_WAIT_TIME` / `LOCK_WAITS` / `LOCK_ESCALS` at table granularity — finer than
  MySQL's server-wide `table_locks_waited` and absent from Postgres core relation metrics.
- Column-organized (`*_COL_*`) and caching-tier (`*_CACHING_TIER_*`, `:1589-1613`) families —
  Db2 12.1 BLU / NVMe-tier specific; collect only when relevant (gate on `TAB_ORGANIZATION='C'`
  / caching-tier configured). Likely defer.

---

## B. MAPPING TABLE — INDEXES (`MON_GET_INDEX`)

Source object: `MON_GET_INDEX(tabschema, tabname, member)`; `NULL,NULL,-2` for all
(general Db2 12.1 knowledge — verify signature). One row per (index = TABSCHEMA+TABNAME+IID,
data partition, member). **`MON_GET_INDEX` returns no index NAME** — only `IID`
(`:1625`). To produce an `index` tag, join `SYSCAT.INDEXES` on
`(TABSCHEMA, TABNAME, IID)` → `INDNAME`, `INDSCHEMA` (`db2-monget-catalog-2.md:142`,
`code-postgres-dbm-metadata-schemas.md:531`). Recommended: cache the
`(TABSCHEMA,TABNAME,IID)→INDNAME` map once per run (like a small catalog lookup) and resolve
in Python, OR LEFT JOIN in the SQL. Common tags for every row: `db`, `schema`
(=`TABSCHEMA`), `table` (=`TABNAME`), `index` (=`INDNAME` via join; fall back to
`iid:<IID>`), `member`. Config gate: `collect_index_metrics` (default OFF) + `index_metrics_limit`
(default ~1000, mirroring MySQL `index_metrics.py:80 INDEX_LIMIT=1000`) + schema filter.

| pg/mysql analog metric | Db2 source (fn + exact column) | proposed `ibm_db2.<name>` | type | unit | tags | notes / version-gating |
|---|---|---|---|---|---|---|
| `pg index_scans` (`postgresql.index_scans`, per-index); `mysql.index.reads` (`mysql.index.reads`) | `MON_GET_INDEX.INDEX_SCANS` (`02-monget-key-columns.txt:1630`) | `ibm_db2.index.scans` | count | scan | db,schema,table,index,member | Primary index-usage metric. Requires `mon_obj_metrics=EXTENDED`. orientation 0. Maps to both pg `index_scans` and mysql `index.reads`. |
| `pg index_rows_read` (`postgresql.index_rows_read`) loosely; index-only-scan ratio | `MON_GET_INDEX.INDEX_ONLY_SCANS` (`:1631`) | `ibm_db2.index.only_scans` | count | scan | db,schema,table,index,member | NEW Db2-native. Index-only scans (covering-index efficiency). Ratio to `INDEX_SCANS` = covering-index hit ratio. orientation 1. |
| — (Db2-native) | `MON_GET_INDEX.INDEX_JUMP_SCANS` (`:1652`) | `ibm_db2.index.jump_scans` | count | scan | db,schema,table,index,member | NEW. Jump scans (skip-scan optimization). Optional. orientation 0. |
| `mysql.index.updates` (`mysql.index.updates`); `pg` n/a (no per-index update counter) | `MON_GET_INDEX.KEY_UPDATES` (`:1632`) | `ibm_db2.index.key_updates` | count | operation | db,schema,table,index,member | Per-index key updates — closest to `mysql.index.updates`. orientation 0. |
| — (Db2-native; INCLUDE columns) | `MON_GET_INDEX.INCLUDE_COL_UPDATES` (`:1633`) | `ibm_db2.index.include_col_updates` | count | operation | db,schema,table,index,member | NEW. Updates to INCLUDE columns of a unique index. Optional. orientation 0. |
| `mysql.index.deletes` (`mysql.index.deletes`) loosely; `pg` n/a | `MON_GET_INDEX.PSEUDO_DELETES` (`:1634`) | `ibm_db2.index.pseudo_deletes` | count | key | db,schema,table,index,member | NEW. Keys pseudo-deleted (logically removed, not yet physically cleaned). Dead-key accumulation. orientation -1. Nearest to mysql `index.deletes` but semantically richer. |
| — (Db2-native; cleanup) | `MON_GET_INDEX.DEL_KEYS_CLEANED` (`:1635`) | `ibm_db2.index.del_keys_cleaned` | count | key | db,schema,table,index,member | NEW. Pseudo-deleted keys physically cleaned up. Pair with `pseudo_deletes` for cleanup-lag. orientation 0. |
| `pg relation.pages` (index analog); `mysql.index.size` (page form) | `MON_GET_INDEX.NLEAF` (`:1628`) | `ibm_db2.index.leaf_pages` | gauge | page | db,schema,table,index,member | NEW. # leaf pages — the per-index size proxy (multiply by tablespace PAGESIZE for bytes). Closest to `mysql.index.size`. orientation 0. |
| — (Db2-native B-tree depth; no analog) | `MON_GET_INDEX.NLEVELS` (`:1629`) | `ibm_db2.index.levels` | gauge | level | db,schema,table,index,member | NEW. B-tree height. Growth indicates index getting deep/inefficient. orientation -1 (lower is better, within reason). |
| — (Db2-native fragmentation) | `MON_GET_INDEX.ROOT_NODE_SPLITS` (`:1636`) | `ibm_db2.index.root_node_splits` | count | split | db,schema,table,index,member | NEW. Root-node splits (expensive). orientation -1. Optional. |
| — | `MON_GET_INDEX.INT_NODE_SPLITS` (`:1637`) | `ibm_db2.index.int_node_splits` | count | split | db,schema,table,index,member | NEW. Intermediate-node splits. orientation -1. Optional. |
| — | `MON_GET_INDEX.BOUNDARY_LEAF_NODE_SPLITS` (`:1638`) | `ibm_db2.index.boundary_leaf_splits` | count | split | db,schema,table,index,member | NEW. Boundary leaf splits (typically append patterns). orientation 0. Optional. |
| — | `MON_GET_INDEX.NONBOUNDARY_LEAF_NODE_SPLITS` (`:1639`) | `ibm_db2.index.nonboundary_leaf_splits` | count | split | db,schema,table,index,member | NEW. Non-boundary leaf splits (random-insert fragmentation). orientation -1. Optional. |
| — (Db2-native page allocation) | `MON_GET_INDEX.PAGE_ALLOCATIONS` (`:1640`) | `ibm_db2.index.page_allocations` | count | page | db,schema,table,index,member | NEW. New index pages allocated. orientation 0. Optional. |
| — (Db2-native dead-space) | `MON_GET_INDEX.PSEUDO_EMPTY_PAGES` (`:1641`) | `ibm_db2.index.pseudo_empty_pages` | count | page | db,schema,table,index,member | NEW. Pages with only pseudo-deleted keys (reclaimable). orientation -1. Optional. |
| — | `MON_GET_INDEX.EMPTY_PAGES_REUSED` (`:1642`) | `ibm_db2.index.empty_pages_reused` | count | page | db,schema,table,index,member | NEW. orientation 1. Optional. |
| — | `MON_GET_INDEX.EMPTY_PAGES_DELETED` (`:1643`) | `ibm_db2.index.empty_pages_deleted` | count | page | db,schema,table,index,member | NEW. orientation 0. Optional. |
| — | `MON_GET_INDEX.PAGES_MERGED` (`:1644`) | `ibm_db2.index.pages_merged` | count | page | db,schema,table,index,member | NEW. Leaf-page merges (cleanup). orientation 0. Optional. |
| `pg index.index_blocks_read` (`postgresql.index.index_blocks_read`) / `index.index_blocks_hit` | `MON_GET_INDEX.OBJECT_INDEX_L_READS` (`:1645`) / `OBJECT_INDEX_P_READS` (`:1646`) | `ibm_db2.index.reads.logical` / `ibm_db2.index.reads.physical` | count | page | db,schema,table,index,member | Per-index bufferpool reads. Logical−physical ≈ index buffer hits (pg `index.index_blocks_hit` analog). Requires `mon_obj_metrics=EXTENDED`. orientation 0. **This is the per-index `OBJECT_INDEX_*` that `MON_GET_TABLE` lacks** (see §A note). |

### Db2-native INDEX metrics worth adding (no pg/mysql analog) — summary
- `INDEX_ONLY_SCANS` (covering-index efficiency ratio vs `INDEX_SCANS`) — strong signal,
  no direct pg/mysql counter.
- `PSEUDO_DELETES` / `DEL_KEYS_CLEANED` — dead-key accumulation & cleanup lag (Db2 MVCC-free
  index maintenance model; Postgres handles this via VACUUM, MySQL via purge — neither
  exposes an equivalent per-index counter).
- `NLEVELS` (B-tree depth) and the `*_NODE_SPLITS` family — B-tree health/fragmentation
  signals unique to Db2's exposed index internals.
- `NLEAF` doubles as the per-index size proxy (page count → bytes via PAGESIZE).

---

## C. TABLE COUNT & TABLE/INDEX SIZE (catalog inventory)

These map to Postgres `postgresql.table.count` (`COUNT_METRICS`, `pg_class`,
`collect_count_metrics` default True, `code-postgres-metrics.md:319-323`) and the
size metrics (`mysql.info.table.data_size` / `.index_size`, `postgresql.table_size` /
`index_size` / `total_size`). Db2 has two routes; pick by cost/freshness:

| pg/mysql analog | Db2 source + exact column | proposed `ibm_db2.<name>` | type | unit | tags | notes |
|---|---|---|---|---|---|---|
| `postgresql.table.count` (`pg_class relkind IN ('r','p')` grouped by schema) | `SELECT TABSCHEMA, COUNT(*) FROM SYSCAT.TABLES WHERE TYPE IN ('T','S') GROUP BY TABSCHEMA` (`SYSCAT.TABLES.TYPE`, `code-postgres-dbm-metadata-schemas.md:525-527`) | `ibm_db2.table.count` | gauge | table | db,schema | Cheap catalog query. Filter system schemas (`SYSCAT,SYSIBM,SYSSTAT,SYSPUBLIC,SYSTOOLS,NULLID,SYSIBMADM,...`, `code-postgres-dbm-metadata-schemas.md:522-524`). `TYPE='T'` table, `'S'` MQT. Gate `collect_table_count` default ON (matches pg). orientation 0. |
| `postgresql.relation.tuples` / `pg live_rows`; `mysql` est. rows | `SYSCAT.TABLES.CARD` (RUNSTATS estimate; `map-rows-throughput.md:279`, `code-postgres-dbm-metadata-schemas.md:525`) | `ibm_db2.table.cardinality` | gauge | row | db,schema,table | NEW (optional). Estimated live-row count; `-1` if never RUNSTATS'd (drop those). Catalog estimate, not exact. orientation 0. |
| `postgresql.relation.pages` (planner estimate) | `SYSCAT.TABLES.NPAGES` / `FPAGES` (`code-postgres-dbm-metadata-schemas.md:525`) | `ibm_db2.table.npages` / `ibm_db2.table.fpages` | gauge | page | db,schema,table | NEW (optional). `NPAGES`=pages with rows, `FPAGES`=total file pages. Catalog estimate. orientation 0. |
| `mysql.info.table.data_size`; `postgresql.table_size` (exact, bytes) | `SYSIBMADM.ADMINTABINFO` (`DATA_OBJECT_P_SIZE`,`INDEX_OBJECT_P_SIZE`,`LOB_OBJECT_P_SIZE`, in KB; `_raw/03-sysibmadm-objects.txt:10`) | `ibm_db2.table.data_size` / `ibm_db2.table.index_size` / `ibm_db2.table.lob_size` | gauge | byte | db,schema,table | NEW (optional, **expensive**). `ADMINTABINFO` is heavier than `SYSCAT.TABLES`; gate behind a separate flag/longer interval. Sizes are in KB → ×1024 for byte unit (general Db2 12.1 knowledge — verify). orientation 0. |

Alternative (no extra catalog query): derive per-table size from `MON_GET_TABLE.*_L_PAGES`
× tablespace PAGESIZE (need PAGESIZE per `TBSP_ID`, joinable from `MON_GET_TABLESPACE` or
`SYSCAT.TABLESPACES`). This keeps everything inside the monitoring functions but requires a
PAGESIZE lookup. The `map-tablespace-storage.md:202` note explicitly routes per-index/per-table
size to THIS category rather than the tablespace category.

---

## D. pg/mysql metrics in this category with NO Db2 equivalent (flag)

| pg/mysql metric | why no Db2 analog | best-effort substitute |
|---|---|---|
| `postgresql.live_rows` / `postgresql.dead_rows` (relations) | Db2 has no MVCC dead-tuple bookkeeping; its locking model overwrites in place. No per-table dead-row counter. | `live_rows` ≈ `SYSCAT.TABLES.CARD` (catalog estimate, §C). No `dead_rows` equivalent — omit. |
| `postgresql.rows_hot_updated` (relations) | HOT (heap-only-tuple) is a Postgres MVCC optimization; Db2 has no HOT concept. | `NO_CHANGE_UPDATES` (`MON_GET_TABLE`, `:1546`) is loosely related (no-op updates) but semantically different — document, don't equate. |
| `postgresql.toast.*` family (toast.live_rows, toast.dead_rows, toast.index_scans, toast.rows_*, toast.vacuumed, toast.last_*_age — `metadata.csv:201-210`) | Db2 has no TOAST mechanism (`code-postgres-dbm-metadata-schemas.md:538`). LOBs are inline/separate objects but not a per-row TOAST table with its own stats. | No equivalent. `LOB_OBJECT_L_PAGES` gives LOB *footprint* only (§A). Omit the rest. |
| `postgresql.toast_blocks_read/hit`, `toast_index_blocks_read/hit` (`metadata.csv:211-214`) | No TOAST. | Omit. |
| `postgresql.{vacuumed,autovacuumed,analyzed,autoanalyzed}` + `last_*_age` (per-relation, `QUERY_PG_CLASS`) | Db2 has no autovacuum daemon. The analog is REORG/RUNSTATS, which is utility-level not per-relation-stat. | REORG/RUNSTATS activity is at WLM/utility level (`MON_GET_SERVICE_SUBCLASS.TOTAL_REORGS`/`TOTAL_RUNSTATS`, `db2-monget-catalog-2.md:284`) — belongs to a utilities map, not per-table here. `STATS_TIME` (`SYSCAT.TABLES`) gives a RUNSTATS age if wanted. |
| `postgresql.relation.all_visible` / `relation.xmin` (`metadata.csv:136,139`) | Postgres visibility-map / MVCC xmin — no Db2 analog (no visibility map, no transaction-id-per-row). | Omit. |
| `mysql.performance.table_open_cache` / `table_cache_hits` / `table_cache_misses` (`metadata.csv:204,205,210`) | MySQL table-descriptor cache; Db2 uses the catalog cache (`CAT_CACHE_*`), which is instance/db-level not per-table. | `CAT_CACHE_LOOKUPS`/`CAT_CACHE_INSERTS` (`MON_GET_DATABASE`/`MON_GET_SERVICE_SUBCLASS`) — belongs to a caches map, not per-table. |
| `mysql.performance.table_locks_immediate` / `table_locks_waited` (`metadata.csv:206-209`, server-wide) | Db2 doesn't expose a server-wide immediate-vs-waited table-lock split; it has per-table `LOCK_WAITS`/`LOCK_WAIT_TIME` (richer, §A) and DB-level lock counters. | Use per-table `ibm_db2.table.lock_waits` (§A) for "waited"; no "immediate" counter exists. |
| `postgresql.bgwriter.*` / index-bloat / table-bloat (`collect_bloat_metrics`) | Db2 fragmentation is surfaced via OVERFLOW_*/PAGE_REORGS/pseudo-empty pages (§A/§B) and REORGCHK, not a bloat-estimate SQL. | Use the Db2-native overflow/reorg/pseudo-delete metrics (§A/§B) as the fragmentation signal instead of a bloat estimate. |

---

## E. Implementation notes for the plan (concrete)

1. **Use Paradigm B (declarative QueryExecutor `columns` dicts)** — matches MySQL
   `index_metrics.py` exactly and the new Postgres style. Each of `MON_GET_TABLE` /
   `MON_GET_INDEX` becomes one query dict with `columns: [{name,type:tag|count|gauge}, ...]`
   and a `collection_interval` (default 300s, like `index_metrics.py:79`).
2. **Cardinality control is mandatory** (this is the whole risk of this category):
   - Config gates: `collect_table_metrics` (OFF), `collect_index_metrics` (OFF),
     `collect_table_count` (ON, cheap catalog), with per-collector `*_limit` (table ~300,
     index ~1000) and schema include/exclude (regex via shared `filters.py`).
   - Top-N: `ORDER BY ROWS_READ DESC FETCH FIRST {limit} ROWS ONLY` (tables) /
     `ORDER BY INDEX_SCANS DESC FETCH FIRST {limit} ROWS ONLY` (indexes) so the most-active
     objects are kept under the cap (mirrors MySQL `LIMIT {INDEX_LIMIT}` and Postgres
     `LIMIT max_relations`).
   - Default exclude system schemas (`SYSCAT,SYSIBM,SYSSTAT,SYSPUBLIC,SYSTOOLS,NULLID,
     SYSIBMADM,SYSIBMINTERNAL,SYSIBMTS`, per `code-postgres-dbm-metadata-schemas.md:522-524`).
3. **Index-name resolution**: `MON_GET_INDEX` lacks `INDNAME`. Either LEFT JOIN
   `SYSCAT.INDEXES` on `(TABSCHEMA,TABNAME,IID)` in the SQL, or cache the mapping once per run.
   Without it, the only index identifier is `iid:<n>` (acceptable fallback). Tag key `index`.
4. **Monitor-switch gating / graceful degradation**: row/scan counters need
   `mon_obj_metrics ≠ NONE`; object bufferpool-read counters need `mon_obj_metrics=EXTENDED`
   (live: EXTENDED). If a site has it OFF these columns are 0 — don't error, just emit 0 /
   skip. Wrap each collector to catch SQL0204 (object not found) / authority errors
   (SYSMON/DBADM) and continue, mirroring Postgres' `UndefinedFunction`/`ProgrammingError`
   handling (`code-postgres-metrics.md:108-112`) and MySQL's graceful-degradation pattern.
5. **Type discipline**: lifetime counters (`*_SCANS`, `ROWS_*`, `*_SPLITS`, `KEY_UPDATES`,
   `*_READS`, `OVERFLOW_*`, `PSEUDO_*`) → `monotonic_count` (CSV `count`); structural
   point-in-time (`NLEAF`, `NLEVELS`, `*_L_PAGES`, `CARD`, `NPAGES`, sizes) → `gauge`;
   `*_TIME` → `monotonic_count`, unit `millisecond`.
6. **metadata.csv**: every emitted metric needs a row in
   `/home/bits/dd/integrations-core/ibm_db2/metadata.csv` with `integration=ibm_db2`, the
   units above, orientation (per table), and a description naming the enabling config flag and
   tags (e.g. "Enabled with `collect_table_metrics`. ... tagged with db, schema, table, member.").
   Mirror the Postgres convention "Enabled with `relations`." (`postgres/metadata.csv:68` etc.).
7. **Tagging**: base tags `db`, `database_hostname`, `database_instance`, version tag, plus
   per-object `schema`/`table`/`index`/`member` (and optional `tab_organization`,
   `data_partition_id`). `member` matters for DPF/pureScale fan-out (`-2` = all members).
8. **Recommended phasing** (by value/cost):
   - **P1**: `ibm_db2.table.count` (§C, cheap, default ON) — direct `postgresql.table.count` parity.
   - **P1**: core `MON_GET_TABLE` row activity (`scans, rows_read, rows_inserted/updated/deleted`,
     `OVERFLOW_*`, `PAGE_REORGS`) — gated `collect_table_metrics`. The fidelity win + Db2-native
     fragmentation signals.
   - **P2**: core `MON_GET_INDEX` (`scans, only_scans, key_updates, pseudo_deletes,
     del_keys_cleaned, leaf_pages, levels, reads.logical/physical`) — gated `collect_index_metrics`.
   - **P3**: table/index size via `ADMINTABINFO` (expensive; separate flag/interval), and the
     long-tail Db2-native columns (splits, pseudo-empty pages, XDA/COL/caching-tier families).
