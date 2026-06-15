# Metric Category Mapping: `tablespace-storage` (Db2 12.1 fidelity)

Raw research input for the Db2 high-fidelity metric implementation plan. **Category scope:**
table-space **size / used / usable / free / total / high-water / utilization / state**,
**automatic-storage / auto-resize** sizing, **containers** (count + per-container filesystem
capacity & utilization), and the related **MON_TBSP_UTILIZATION** / **CONTAINER_UTILIZATION**
admin views. Source functions in scope: **`MON_GET_TABLESPACE`**, **`MON_GET_CONTAINER`**,
and the SYSIBMADM views **`MON_TBSP_UTILIZATION`** / **`TBSP_UTILIZATION`** /
**`CONTAINER_UTILIZATION`** / **`MON_BP_UTILIZATION`** (size-side only).

> **Scope boundary:** the *I/O* columns that ride on the same `MON_GET_TABLESPACE` /
> `MON_GET_CONTAINER` rows (`POOL_*_P_READS`, `POOL_*_WRITES`, `DIRECT_*`, `POOL_READ_TIME`,
> `PREFETCH_*`, container `FS_*` *I/O*, etc.) are owned by the **io-disk** category and are
> mapped in `/home/bits/dd/integrations-core/ibm_db2/dev-docs/db2-fidelity-plan/_research/map-io-disk.md`.
> This doc owns the **capacity / sizing / state** columns only. Where a column is plausibly
> claimed by both (e.g. container `FS_USED_SIZE`/`FS_TOTAL_SIZE`), it is noted as a cross-listed
> overlap with io-disk so the plan author dedupes.

Target Db2 version **12.1** (live container **12.1.4.0**, `DB2/LINUXX8664 12.1.4.0`).

## Sources consulted
- Existing ibm_db2 catalog: `/home/bits/dd/integrations-core/ibm_db2/metadata.csv` (50 lines incl. header)
- Existing ibm_db2 SQL: `/home/bits/dd/integrations-core/ibm_db2/datadog_checks/ibm_db2/queries.py` (`TABLE_SPACE_TABLE_COLUMNS` L83-91)
- Existing ibm_db2 emission: `/home/bits/dd/integrations-core/ibm_db2/datadog_checks/ibm_db2/ibm_db2.py` (`query_table_space` L379-412, `track_table_space_state_changes` L536-552)
- Tablespace-state service-check / status map: `/home/bits/dd/integrations-core/ibm_db2/datadog_checks/ibm_db2/utils.py` (`DB_STATUS_MAP` L13-24)
- **LIVE** `MON_GET_TABLESPACE` 253-column DESCRIBE dump: `/home/bits/dd/integrations-core/ibm_db2/dev-docs/db2-fidelity-plan/_research/_raw/02-monget-key-columns.txt` L766-1023 (size/state columns L822-942)
- SYSIBMADM views present on live server: `/home/bits/dd/integrations-core/ibm_db2/dev-docs/db2-fidelity-plan/_research/_raw/03-sysibmadm-objects.txt` (`MON_TBSP_UTILIZATION` L47, `CONTAINER_UTILIZATION` L19, `TBSP_UTILIZATION` L85, `MON_BP_UTILIZATION` L39)
- MON_GET function inventory (live): `/home/bits/dd/integrations-core/ibm_db2/dev-docs/db2-fidelity-plan/_research/_raw/01-version-and-monget-functions.txt` (`MON_GET_TABLESPACE` L61, `MON_GET_CONTAINER` L25, `MON_GET_TABLESPACE_RANGE` L63, `MON_GET_TABLESPACE_QUIESCER` L62, `MON_GET_EXTENT_MOVEMENT_STATUS` L29, `MON_GET_REBALANCE_STATUS` L45)
- pg metric catalog: `/home/bits/dd/integrations-core/postgres/metadata.csv`
- mysql metric catalog: `/home/bits/dd/integrations-core/mysql/metadata.csv`
- pg/mysql collection architecture: `code-postgres-metrics.md`, `code-mysql-metrics.md` (same `_research/` dir)
- Catalog cross-ref: `db2-monget-catalog-2.md` (units convention §"Provenance", monitor-switch gating)

**Provenance flags:** `[LIVE]` = column name confirmed in the 12.1.4 `MON_GET_TABLESPACE`
DESCRIBE dump (with the exact source line cited). `[DOC]` = from IBM 12.1 docs / general Db2
12.1 knowledge — **verify** against the live container with `DESCRIBE SELECT * FROM
TABLE(MON_GET_CONTAINER(NULL,-1))` before coding. `MON_GET_CONTAINER`, `MON_TBSP_UTILIZATION`,
and `CONTAINER_UTILIZATION` column lists are **not** in the captured DESCRIBE dump (the dump
holds only the 11 functions enumerated in `db2-monget-catalog-2.md` §"Provenance"), so all of
their columns are `[DOC]`.

---

## 0. Db2 storage model in one paragraph (so the mapping makes sense)

A Db2 database is divided into **table spaces** (`MON_GET_TABLESPACE`), each backed by one or
more **containers** (files/devices/automatic-storage paths — `MON_GET_CONTAINER`). Sizing is
expressed in **pages**, where the page size is per-table-space (`TBSP_PAGE_SIZE`, typically
4096/8192/16384/32768 bytes). To get **bytes** you must multiply a `*_PAGES` column by
`TBSP_PAGE_SIZE` — exactly what the existing check does (`ibm_db2.py:391-405`). The page
hierarchy for a table space is:

- **`TBSP_TOTAL_PAGES`** — total pages across all containers (the gross allocation, incl.
  overhead pages not available to data).
- **`TBSP_USABLE_PAGES`** — total minus container/extent overhead = pages actually available
  to store data.
- **`TBSP_USED_PAGES`** — usable pages currently holding data.
- **`TBSP_FREE_PAGES`** — usable pages not yet used (`USABLE − USED`, for DMS/auto-storage;
  may be -1/NULL for SMS where free space is filesystem-bounded). `[LIVE]` L824.
- **`TBSP_PAGE_TOP`** — high-water-mark page (the highest page ever used; drives whether the
  TS can shrink). `[LIVE]` L828.
- **`TBSP_PENDING_FREE_PAGES`** — pages freed but pending reuse (reclaimable). `[LIVE]` L827.
- **`TBSP_MAX_SIZE` / `TBSP_INITIAL_SIZE` / `TBSP_INCREASE_SIZE`** — auto-resize policy
  (max cap, seed size, growth increment). `[LIVE]` L908/907/909.

**Utilization** = `USED / USABLE * 100` (the existing `tablespace.utilized` formula,
`ibm_db2.py:407-410`). A *capacity-cap* utilization (how close to `TBSP_MAX_SIZE`) is a
distinct, higher-value signal for auto-resize table spaces (used pages vs the configured max).

`MON_GET_TABLESPACE` is **always populated** regardless of monitor switches (it is an object
function, and `mon_obj_metrics=EXTENDED` on the live box, `_raw/04-monitor-config.txt`); the
size/state columns specifically have no switch dependency. One row per (table space, member).
The existing check queries `MON_GET_TABLESPACE(NULL, -1)` (all TS, current/aggregate member).

---

## 1. EXISTING ibm_db2 tablespace-storage metrics (baseline — do not duplicate)

From `metadata.csv:47-50` + `ibm_db2.py:379-412`. All `gauge`, tagged `db` (instance tags) +
`tablespace:<TBSP_NAME>`.

| metric | source column(s) | computation | unit | orient. | notes |
|---|---|---|---|---|---|
| `ibm_db2.tablespace.size` | `TBSP_TOTAL_PAGES` × `TBSP_PAGE_SIZE` | bytes | byte | 0 | `[LIVE]` L826/775. "total size". |
| `ibm_db2.tablespace.usable` | `TBSP_USABLE_PAGES` × `TBSP_PAGE_SIZE` | bytes | byte | 1 | `[LIVE]` L825. |
| `ibm_db2.tablespace.used` | `TBSP_USED_PAGES` × `TBSP_PAGE_SIZE` | bytes | byte | -1 | `[LIVE]` L823. |
| `ibm_db2.tablespace.utilized` | `USED/USABLE*100` | percent | percent | -1 | guards div-by-zero (`ibm_db2.py:407`). |
| *(event, not a metric)* `ibm_db2.tablespace_state_change` | `TBSP_STATE` | event on change | — | — | `track_table_space_state_changes` L536-552; emits a Datadog **event** when a TS's `TBSP_STATE` string changes. No service check, no gauge. |

**Gaps in the baseline (this category):** no `free`, no `high-water`, no auto-resize/max-size,
no page-size gauge, no container count, no per-container filesystem capacity, **no
service-check or numeric gauge for TS state** (only a free-form event), no reclaimable/pending
space, no rebalance/extent-movement progress. Sections 2-5 fill these.

---

## 2. MAPPING TABLE — pg/mysql analog → Db2 source → proposed ibm_db2 metric

Legend for **type**: `gauge` = point-in-time (all sizing/state here are gauges — page counts
and bytes are current values, not lifetime counters). `count` = monotonic_count (none in this
category; sizing is never cumulative). Metric prefix is `ibm_db2.` (auto-applied). Bytes are
always `pages × TBSP_PAGE_SIZE`.

### 2.1 Table-space size family (capacity)

| pg/mysql analog | Db2 source: fn + exact column | proposed `ibm_db2.<name>` | type | unit | tags | notes / version-gating |
|---|---|---|---|---|---|---|
| `postgresql.database_size` (per-db disk); mysql `info.schema.size` (per-schema) — closest "allocated storage" analogs (none is per-tablespace) | `MON_GET_TABLESPACE`: `TBSP_TOTAL_PAGES` × `TBSP_PAGE_SIZE` | **`ibm_db2.tablespace.size`** (SHIPPED, metadata.csv:47) | gauge | byte | `db`,`tablespace` | EXISTS. `[LIVE]` L826. |
| (no direct pg/mysql analog) | `TBSP_USABLE_PAGES` × `TBSP_PAGE_SIZE` | **`ibm_db2.tablespace.usable`** (SHIPPED, metadata.csv:48) | gauge | byte | `db`,`tablespace` | EXISTS. `[LIVE]` L825. |
| `postgresql.relation_size`/`table_size` (used space, per-relation) | `TBSP_USED_PAGES` × `TBSP_PAGE_SIZE` | **`ibm_db2.tablespace.used`** (SHIPPED, metadata.csv:49) | gauge | byte | `db`,`tablespace` | EXISTS. `[LIVE]` L823. |
| (no analog — pg/mysql expose free space only as derived) | `TBSP_FREE_PAGES` × `TBSP_PAGE_SIZE` | **`ibm_db2.tablespace.free`** | gauge | byte | `db`,`tablespace` | **NEW.** `[LIVE]` L824. Note: `TBSP_FREE_PAGES` can be `-1`/NULL for SMS table spaces (free space is filesystem-bounded, not preallocated) — **emit only when ≥ 0** (mirror the existing `available == -1` guard in `query_transaction_log`, `ibm_db2.py:430`). Pairs with `.usable`/`.used` for an explicit free-space alarm rather than forcing dashboards to subtract. |
| (no analog) | `TBSP_PAGE_TOP` × `TBSP_PAGE_SIZE` | **`ibm_db2.tablespace.high_water_mark`** | gauge | byte | `db`,`tablespace` | **NEW.** `[LIVE]` L828. Highest page ever used — the floor a table space can shrink to. Gap between `high_water_mark` and `used` = reclaimable-via-reorg space; gap between `size` and `high_water_mark` = shrinkable space. High-value capacity-planning signal with no pg/mysql equivalent. |
| (no analog) | `TBSP_PENDING_FREE_PAGES` × `TBSP_PAGE_SIZE` | **`ibm_db2.tablespace.pending_free`** | gauge | byte | `db`,`tablespace` | **NEW.** `[LIVE]` L827. Pages freed but pending reuse (reclaimable space in reclaimable-storage TS). Pairs with `RECLAIMABLE_SPACE_ENABLED` (L830). Lower priority. |
| (no analog — Db2 page size is per-TS config) | `TBSP_PAGE_SIZE` | **`ibm_db2.tablespace.page_size`** | gauge | byte | `db`,`tablespace` | **NEW (optional).** `[LIVE]` L775. Mostly a label/context value; arguably better as a `page_size:` *tag* than a metric to avoid a near-constant series. Recommend tag, not metric. |

### 2.2 Auto-resize / automatic-storage sizing (Db2-native capacity caps)

These let you alert on "approaching the configured ceiling" — far more actionable than raw
utilization for auto-growing table spaces. No pg/mysql analog (pg/mysql do not expose a
per-storage-object growth cap).

| pg/mysql analog | Db2 source | proposed `ibm_db2.<name>` | type | unit | tags | notes |
|---|---|---|---|---|---|---|
| (no analog) | `MON_GET_TABLESPACE`: `TBSP_MAX_SIZE` (bytes; `-1` = unlimited) | **`ibm_db2.tablespace.max_size`** | gauge | byte | `db`,`tablespace` | **NEW.** `[LIVE]` L908. **Already in bytes** (NOT pages — do not multiply by page size). Emit only when `> 0` (`-1` = no cap). |
| (no analog) | `TBSP_INITIAL_SIZE` (bytes) | **`ibm_db2.tablespace.initial_size`** | gauge | byte | `db`,`tablespace` | **NEW (optional).** `[LIVE]` L907. Seed size for auto-resize. Bytes already. Low priority. |
| (no analog) | `TBSP_INCREASE_SIZE` (bytes) and/or `TBSP_INCREASE_SIZE_PERCENT` | **`ibm_db2.tablespace.increase_size`** | gauge | byte / percent | `db`,`tablespace` | **NEW (optional).** `[LIVE]` L909/910. Growth increment. Low priority. |
| (no analog) — **derived, HIGH value** | `TBSP_USED_PAGES × TBSP_PAGE_SIZE / TBSP_MAX_SIZE * 100` (only when `TBSP_AUTO_RESIZE_ENABLED=1 AND TBSP_MAX_SIZE > 0`) | **`ibm_db2.tablespace.max_utilized`** | gauge | percent | `db`,`tablespace` | **NEW, derived.** Uses `TBSP_AUTO_RESIZE_ENABLED` `[LIVE]` L783 + `TBSP_MAX_SIZE` `[LIVE]` L908. "How close to the configured max" — the *actionable* fullness number for auto-resize TS (the existing `.utilized` measures fullness vs currently-allocated usable space, which auto-grows and so masks the real ceiling). Skip / emit NaN-guard when not auto-resize or max is unlimited. |
| (no analog) | `TBSP_LAST_RESIZE_FAILED` (0/1) | **`ibm_db2.tablespace.last_resize_failed`** | gauge | (boolean) | `db`,`tablespace` | **NEW (optional).** `[LIVE]` L912. `1` = the most recent auto-resize attempt failed (often = out of storage). Strong disk-full early-warning. Consider also a service-check. Orientation -1. |

### 2.3 Utilization (point-in-time fullness)

| pg/mysql analog | Db2 source | proposed `ibm_db2.<name>` | type | unit | tags | notes |
|---|---|---|---|---|---|---|
| (closest: no pg/mysql per-tablespace util; conceptually like a disk-fullness %) | derived `TBSP_USED_PAGES / TBSP_USABLE_PAGES * 100` | **`ibm_db2.tablespace.utilized`** (SHIPPED, metadata.csv:50) | gauge | percent | `db`,`tablespace` | EXISTS. Guards `usable == 0` → 0. |
| (no analog) | SYSIBMADM `MON_TBSP_UTILIZATION.TBSP_UTILIZATION_PERCENT` (server-computed) | *(use as cross-check, not a 2nd metric)* | — | percent | — | `[DOC]` `_raw/03...txt` L47. The admin view pre-computes the same %; prefer the in-house `MON_GET_TABLESPACE` derivation to avoid a 2nd query. Documented only as a validation source. |

### 2.4 Table-space STATE (availability) — upgrade from event to service-check + gauge

The shipped check turns `TBSP_STATE` only into a free-form **event on change**
(`track_table_space_state_changes`, `ibm_db2.py:536`). There is **no metric and no service
check**, so you cannot alert on "table space OFFLINE/in-LOAD-pending right now" — only on a
transition that the agent happened to observe. This is the biggest fidelity gap in the
category. `TBSP_STATE` is a `VARCHAR(256)` bit-mask label string (e.g. `NORMAL`,
`OFFLINE,NOT_ACCESSIBLE`, `BACKUP_PENDING`, `LOAD_PENDING`, `RESTORE_PENDING`,
`ROLLFORWARD_PENDING`, `STORAGE_MUST_DEFINE`, etc.).

| pg/mysql analog | Db2 source | proposed `ibm_db2.<name>` | type | unit | tags | notes |
|---|---|---|---|---|---|---|
| (no metric analog; pg `conflicts.tablespace` is the only pg metric naming a tablespace, semantics differ — see §3) | `MON_GET_TABLESPACE`: `TBSP_STATE` `[LIVE]` L822 | **service check `ibm_db2.tablespace.status`** (NEW) | service_check | — | `db`,`tablespace`,`tablespace_state:<state>` | **NEW.** Map `NORMAL` → OK; pending/quiesced states → WARNING; `OFFLINE`/`NOT_ACCESSIBLE`/`*_PENDING` (restore/rollforward) → CRITICAL. Mirror the existing `DB_STATUS_MAP`/`status_to_service_check` pattern (`utils.py:13-24`) with a new `TABLE_SPACE_STATE_MAP`. Keep the existing change-event too. |
| (optional numeric companion) | `TBSP_STATE` truthiness | **`ibm_db2.tablespace.online`** | gauge | (boolean) | `db`,`tablespace` | **NEW (optional).** `1` when state == `NORMAL`, else `0`. A monitorable numeric for dashboards/SLOs that prefer a gauge over a service check. Orientation 1. |

### 2.5 Container count + per-container filesystem capacity

A table space's real disk-full risk is at the **container / filesystem** level (auto-storage
paths share a filesystem; a full FS blocks every TS on it). pg/mysql have no per-container
concept; the closest pg analog is `database_size` against the host filesystem.

| pg/mysql analog | Db2 source | proposed `ibm_db2.<name>` | type | unit | tags | notes |
|---|---|---|---|---|---|---|
| (no analog) | `MON_GET_TABLESPACE`: `TBSP_NUM_CONTAINERS` | **`ibm_db2.tablespace.containers`** | gauge | container | `db`,`tablespace` | **NEW.** `[LIVE]` L906. Cheap (rides the existing TS query — just add the column). # of containers per TS. |
| `postgresql.database_size` (filesystem-level disk usage) | `MON_GET_CONTAINER(NULL,-1)`: `FS_USED_SIZE` (bytes) | **`ibm_db2.container.fs_used`** | gauge | byte | `db`,`tablespace`,`container`,`member` | **NEW.** `[DOC]` (CONTAINER not in dump — verify). **Cross-listed with io-disk §1.8** — coordinate ownership; capacity dashboards want it here. |
| (no analog) | `MON_GET_CONTAINER`: `FS_TOTAL_SIZE` (bytes) | **`ibm_db2.container.fs_total`** | gauge | byte | `db`,`tablespace`,`container`,`member` | **NEW.** `[DOC]`. Total filesystem size hosting the container. `fs_used/fs_total` = filesystem fullness = the true disk-full early warning. |
| (no analog) | `MON_GET_CONTAINER`: `TOTAL_PAGES` × page_size | **`ibm_db2.container.total`** | gauge | byte | `db`,`tablespace`,`container`,`member` | **NEW (optional).** `[DOC]`. Container allocation. |
| `postgresql.relation_size` (used, per-object) | `MON_GET_CONTAINER`: `USED_PAGES`, `USABLE_PAGES` × page_size | **`ibm_db2.container.used`**, **`ibm_db2.container.usable`** | gauge | byte | `db`,`tablespace`,`container`,`member` | **NEW (optional).** `[DOC]`. Per-container used/usable. |
| (no analog) | `MON_GET_CONTAINER`: `ACCESSIBLE` (0/1) | **service check `ibm_db2.container.status`** or gauge `ibm_db2.container.accessible` | service_check / gauge | — | `db`,`tablespace`,`container` | **NEW (optional).** `[DOC]`. `0` = container offline/inaccessible (disk failure). High value, low cardinality. |

> **Cardinality / gating for §2.5 containers:** `MON_GET_CONTAINER` returns one row per
> (container, member). DMS/auto-storage table spaces can have many containers. **Gate the
> per-container metrics behind a config option** (proposed `collect_container_metrics`,
> default off) exactly as io-disk recommends. `tablespace.containers` (the count) is on the
> cheap TS row and can ship unconditionally. Container tags: `container:<CONTAINER_NAME>`,
> `container_type:<DISK|FILE|PATH>` (`[DOC]`).

### 2.6 Storage groups (automatic-storage grouping) — Db2-native, optional

| pg/mysql analog | Db2 source | proposed `ibm_db2.<name>` | type | unit | tags | notes |
|---|---|---|---|---|---|---|
| (no analog) | `MON_GET_TABLESPACE`: `STORAGE_GROUP_NAME`, `STORAGE_GROUP_ID` | *(tag only)* `storage_group:<name>` | — | — | `db`,`tablespace`,`storage_group` | `[LIVE]` L862/863. **Add as a tag** on the existing TS size metrics (not a metric) so capacity can be rolled up per storage group. Cheap, high value for auto-storage. |
| (no analog) | `MON_GET_TABLESPACE`: `TBSP_USING_AUTO_STORAGE` (0/1), `AUTO_STORAGE_HYBRID` | *(tag)* `auto_storage:true|false` | — | — | `db`,`tablespace` | `[LIVE]` L782/831. Optional descriptive tag. |
| (no analog) | `MON_GET_TABLESPACE`: `TBSP_TYPE` (DMS/SMS), `TBSP_CONTENT_TYPE` (ANY/LARGE/USRTEMP/SYSTEMP) | *(tags)* `tablespace_type:`, `tablespace_content_type:` | — | — | `db`,`tablespace` | `[LIVE]` L773/774. **Add as tags** — lets you exclude SMS/temp TS from free-space alarms (where `TBSP_FREE_PAGES` is meaningless) and segment regular vs temp. High value for dashboard hygiene. |

### 2.7 Rebalance / extent-movement progress (automatic-storage maintenance) — Db2-native

When a storage path is added/dropped or `ALTER TABLESPACE ... REBALANCE` runs, Db2 moves
extents in the background. No pg/mysql analog. Separate functions, not on the TS row.

| pg/mysql analog | Db2 source | proposed `ibm_db2.<name>` | type | unit | tags | notes |
|---|---|---|---|---|---|---|
| `postgresql.vacuum.heap_blks_*` (progress %, conceptual only) | `MON_GET_REBALANCE_STATUS(NULL,-2)` (`_raw/01...txt` L45): `EXTENTS_REMAINING`, `EXTENTS_PROCESSED`, `START_TIME` | **`ibm_db2.tablespace.rebalance.extents_remaining`**, **`...extents_processed`** | gauge | extent | `db`,`tablespace`,`member` | **NEW (optional).** `[DOC]`. Returns rows only while a rebalance is active. % complete = processed/(processed+remaining). Lower priority. |
| (conceptual progress) | `MON_GET_EXTENT_MOVEMENT_STATUS(NULL,-2)` (`_raw/01...txt` L29): `EXTENTS_MOVED`, `EXTENTS_LEFT`, `CURRENT_EXTENT`, `NUM_EXTENTS_MOVED` | **`ibm_db2.tablespace.extent_movement.moved`**, **`...left`** | gauge | extent | `db`,`tablespace`,`member` | **NEW (optional).** `[DOC]`. Active only during `ALTER ... REDUCE`/extent movement. Lowest priority. |

---

## 3. pg/mysql metrics in this category with NO Db2 equivalent (flag list)

| pg/mysql metric | semantics | why no Db2 analog / recommendation |
|---|---|---|
| `postgresql.conflicts.tablespace` (count) | queries canceled on a standby because a temp tablespace was dropped during recovery | **NOT a sizing metric** — it is a *replication-conflict* counter that merely names "tablespace". Db2 has no equivalent (HADR conflict accounting differs). Maps, if anywhere, to the HADR category, not tablespace-storage. Flag pg-only. |
| `postgresql.database_size` (per-DB bytes) | total disk used by a database | Db2's nearest is **sum of `TBSP_USED_PAGES × TBSP_PAGE_SIZE` across all TS** or `SYSPROC.ADMIN_GET_DBSIZE_INFO()` (`DATABASE_SIZE`/`DATABASE_CAPACITY`). Not a per-tablespace metric — belongs to a future `database.size` rollup. Note as a derivable gap; consider `ibm_db2.database.size` (sum) + `ibm_db2.database.capacity` from `ADMIN_GET_DBSIZE_INFO()` `[DOC]`. |
| `postgresql.relation_size` / `table_size` / `total_size` / `index_size` / `toast_size` / `individual_index_size` | **per-table / per-index** disk space (enabled with `relations`) | Db2 equivalent is **per-table**, not per-tablespace: `MON_GET_TABLE` `DATA_OBJECT_L_PAGES`/`INDEX_OBJECT_L_PAGES`/`LOB_OBJECT_L_PAGES`/`COL_OBJECT_L_PAGES`/`XDA_OBJECT_L_PAGES` × page size, or `SYSPROC.ADMIN_GET_TAB_INFO()`. **Out of scope for tablespace-storage** — owned by a future per-table category (see `db2-monget-catalog-2.md` §1, `MON_GET_TABLE`). Flag: handled elsewhere, not here. |
| `mysql.info.schema.size` / `mysql.info.table.data_size` / `index_size` | per-schema / per-table size (MiB) | Same as above — Db2 per-table sizing via `MON_GET_TABLE` / `ADMIN_GET_TAB_INFO`, not per-tablespace. Out of scope here. |
| `mysql.index.size` | per-index size | `MON_GET_TABLE.INDEX_OBJECT_L_PAGES` or `SYSCAT.INDEXES` — per-index category, not tablespace. |
| `postgresql.toast_size` | TOAST (out-of-line large value) storage | Db2 stores LOBs/LONG in the LONG table space; nearest is `MON_GET_TABLE.LOB_OBJECT_L_PAGES`/`LONG_OBJECT_L_PAGES`. Per-table, not per-TS. Flag. |

**Net:** the only pg/mysql metric that *names* "tablespace" (`conflicts.tablespace`) is not a
sizing metric and has no Db2 analog. All real pg/mysql *size* metrics are **per-database** or
**per-relation**, whereas Db2's native sizing granularity is **per-table-space** and
**per-container**. The category is therefore largely **Db2-native**: fidelity here means
exposing Db2's richer per-TS/per-container capacity model, not chasing pg/mysql parity.

---

## 4. Db2-native tablespace-storage metrics with NO pg/mysql analog, ranked by value

1. **`ibm_db2.tablespace.status` (service check) + `ibm_db2.tablespace.online` (gauge)** (§2.4)
   — close the biggest gap: today TS state is only a transient event. `TBSP_STATE` `[LIVE]`.
2. **`ibm_db2.tablespace.max_utilized` (derived %)** + **`ibm_db2.tablespace.max_size`** (§2.2)
   — the *actionable* fullness for auto-resize table spaces (vs the ceiling, not vs the
   auto-growing usable size). `TBSP_MAX_SIZE`/`TBSP_AUTO_RESIZE_ENABLED` `[LIVE]`.
3. **`ibm_db2.container.fs_used` / `ibm_db2.container.fs_total`** (§2.5) — true disk-full early
   warning at the filesystem hosting auto-storage paths. `MON_GET_CONTAINER.FS_*` `[DOC]`,
   cross-listed with io-disk. Gate behind `collect_container_metrics`.
4. **`ibm_db2.tablespace.free`** (§2.1) — explicit free bytes (with SMS `-1` guard).
   `TBSP_FREE_PAGES` `[LIVE]`.
5. **`ibm_db2.tablespace.high_water_mark`** (§2.1) — shrinkable-space / reorg-benefit signal.
   `TBSP_PAGE_TOP` `[LIVE]`.
6. **`ibm_db2.tablespace.containers`** (count) + **`storage_group`/`tablespace_type`/
   `tablespace_content_type` tags** (§2.5/§2.6) — cheap context that rides the existing query;
   enables per-storage-group rollups and excluding temp/SMS TS from alarms. `[LIVE]`.
7. **`ibm_db2.tablespace.last_resize_failed`** (§2.2) — explicit "auto-grow failed" alarm.
   `TBSP_LAST_RESIZE_FAILED` `[LIVE]`.
8. **`ibm_db2.tablespace.pending_free`** (§2.1) + **container `accessible`/`used`/`usable`/
   `total`** (§2.5) — reclaimable space + per-container detail. Lower priority, gated.
9. **`ibm_db2.tablespace.rebalance.*` / `.extent_movement.*`** (§2.7) — auto-storage
   maintenance progress; only active during rebalance. Lowest priority.

---

## 5. Implementation notes for the plan author

- **Extend the existing query, don't add a new one for the cheap columns.** Add to
  `TABLE_SPACE_TABLE_COLUMNS` (`queries.py:83-90`): `tbsp_free_pages`, `tbsp_page_top`,
  `tbsp_pending_free_pages`, `tbsp_num_containers`, `tbsp_max_size`, `tbsp_initial_size`,
  `tbsp_auto_resize_enabled`, `tbsp_last_resize_failed`, `tbsp_type`, `tbsp_content_type`,
  `storage_group_name`, `tbsp_using_auto_storage`. All ride the single existing
  `MON_GET_TABLESPACE(NULL,-1)` row — near-zero added cost. Emit them in the existing
  `query_table_space` loop (`ibm_db2.py:382-412`) alongside the current size gauges.
- **Bytes vs pages discipline (critical):** `TBSP_*_PAGES` columns are **pages** → multiply by
  `TBSP_PAGE_SIZE` (the existing pattern, `ibm_db2.py:391/396/401`). But `TBSP_MAX_SIZE`,
  `TBSP_INITIAL_SIZE`, `TBSP_INCREASE_SIZE` are **already bytes** — do NOT multiply. Mixing
  these up is the easiest bug here.
- **Guard sentinel values:** `TBSP_FREE_PAGES` and `TBSP_MAX_SIZE` are `-1` for SMS /
  unlimited respectively (mirror the `available == -1` guard in `query_transaction_log`,
  `ibm_db2.py:430`). For `tablespace.utilized`/`max_utilized`, keep the `usable == 0` /
  `max <= 0` div-by-zero guards.
- **State → service check:** add a `TABLE_SPACE_STATE_MAP` to `utils.py` mirroring
  `DB_STATUS_MAP` (L13-24) and a `status_to_service_check`-style helper; register a new
  `ibm_db2.tablespace.status` service check (TS state is a comma-joined bit-mask string — match
  on substring/`NORMAL`-exact). Keep the existing change-event (`track_table_space_state_changes`).
  Add a `tablespace_state:<TBSP_STATE>` tag to the size metrics for filtering.
- **Containers behind a flag:** new query `SELECT ... FROM TABLE(MON_GET_CONTAINER(NULL,-1))`
  gated by `collect_container_metrics` (default off). **Run a live `DESCRIBE SELECT * FROM
  TABLE(MON_GET_CONTAINER(NULL,-1))` first** — its columns are not in the captured dump
  (`[DOC]`): confirm `CONTAINER_NAME`, `CONTAINER_TYPE`, `FS_USED_SIZE`, `FS_TOTAL_SIZE`,
  `TOTAL_PAGES`, `USABLE_PAGES`, `USED_PAGES`, `ACCESSIBLE`, `MEMBER` before mapping.
  Coordinate with io-disk §1.8 to avoid double-defining `container.fs_used`/`fs_total`.
- **Metric type discipline:** everything in this category is point-in-time → `self.gauge(...)`,
  declared `gauge` in `metadata.csv`. (No `monotonic_count` — sizing is never cumulative. This
  contrasts with io-disk, where the same functions' `POOL_*`/`DIRECT_*` columns ARE counters.)
- **Units in metadata.csv** (match existing rows 47-50): all byte sizes → `byte`; utilization
  → `percent`; container count → `container` (mirror `connection`/`lock` unit convention);
  page_size → `byte`; extents → `extent`; booleans → leave `unit_name` blank. Orientation:
  `used`/`utilized`/`max_utilized`/`fs_used`/`last_resize_failed`/`pending_free` = `-1`;
  `usable`/`free`/`online` = `1`; `size`/`total`/`high_water_mark`/`containers`/`page_size`/
  `max_size` = `0`. `integration=ibm_db2`.
- **Tags:** base instance tags + `tablespace:<TBSP_NAME>` (already applied). Add
  `tablespace_type`, `tablespace_content_type`, `storage_group`, `tablespace_state` (size
  metrics); `container`, `container_type`, `member` (container metrics). `member` only matters
  for DPF/pureScale — the existing check aggregates with `-1`; add `member` only if/when a
  member dimension is introduced (note `MON_GET_TABLESPACE` exposes `MEMBER` `[LIVE]` L772 and
  `MON_GET_CONTAINER` exposes `MEMBER` `[DOC]`).
- **No version/edition gate needed for 12.1:** all `TBSP_*` size/state/auto-resize columns
  exist since 9.7/10.1 and are present in the live 12.1.4 dump. `STORAGE_GROUP_*` requires
  multi-temperature storage (10.1+) — present here. `CACHING_TIER*` columns are storage-tier
  (LSA) specific and out of scope for capacity. pureScale-only GBP/caching columns are not in
  this category.
- **Validation set before shipping** (run live `DESCRIBE`): all `MON_GET_CONTAINER`,
  `MON_GET_REBALANCE_STATUS`, `MON_GET_EXTENT_MOVEMENT_STATUS`, and `MON_TBSP_UTILIZATION`
  columns (`[DOC]`). All `MON_GET_TABLESPACE` columns cited here are `[LIVE]` (no re-verify
  needed) with exact source lines in `_raw/02-monget-key-columns.txt`.
