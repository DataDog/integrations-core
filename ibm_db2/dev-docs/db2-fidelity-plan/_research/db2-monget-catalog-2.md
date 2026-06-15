# Db2 MON_GET_* Catalog 2 — Workload / Service Class / Agent / Memory / Table / Index / Instance

Scope: detailed catalog of 8 requested table functions plus the closely-related
`MON_GET_SERVICE_SUBCLASS`/`MON_GET_WORKLOAD` shared column family. Intended as raw
input for a fidelity-plan agent. Db2 server under test: **DB2/LINUXX8664 12.1.4.0**
(`/home/bits/dd/integrations-core/ibm_db2/dev-docs/db2-fidelity-plan/_research/_raw/01-version-and-monget-functions.txt`).

## Provenance / how to read this doc

- "DESCRIBE dump" = `DESCRIBE SELECT * FROM TABLE(<fn>(...))` output captured live and
  stored in `_raw/02-monget-key-columns.txt`. Column names, SQL types, and type-lengths
  below are transcribed verbatim from that file (with the start line cited).
- The DESCRIBE dump contains 11 functions in this order:
  `MON_GET_DATABASE`(515 cols, L16), `MON_GET_BUFFERPOOL`(221, L538),
  `MON_GET_TABLESPACE`(253, L768), `MON_GET_CONNECTION`(417, L1030),
  `MON_GET_TRANSACTION_LOG`(56, L1456), **`MON_GET_TABLE`(91, L1521)**,
  **`MON_GET_INDEX`(35, L1621)**, `MON_GET_HADR`(10, L1665),
  **`MON_GET_SERVICE_SUBCLASS`(376, L1684)**, **`MON_GET_WORKLOAD`(371, L2069)**,
  **`MON_GET_INSTANCE`(24, L2447)**.
- `MON_GET_AGENT`, `MON_GET_MEMORY_POOL`, `MON_GET_MEMORY_SET` are **NOT** in the DESCRIBE
  dump. Their columns below are from general Db2 12.1 knowledge and are explicitly marked
  "(general Db2 12.1 knowledge — verify)". All three functions ARE confirmed present on the
  server (listed in `_raw/01-version-and-monget-functions.txt`, lines 13/39/40).
- SQL type codes seen: `493 BIGINT`(8), `497 INTEGER`(4), `501 SMALLINT`(2),
  `449 VARCHAR`(n), `453 CHARACTER`(1), `393 TIMESTAMP`(26), `481 DOUBLE`(8).
- Units convention for Db2 monitor elements (general Db2 knowledge): all `*_TIME`
  counters are **milliseconds**; `*_VOLUME` are **bytes**; `POOL_*`/`*_L_READS`/`*_P_READS`
  /`*_PAGES` are **pages** (count); read/write/sort/lock/commit/etc. are monotonic
  **counts** since database activation (or since last `WLM` reset for WLM objects).
  Recommended Datadog metric type for monotonic counters = `monotonic_count` (or `rate`);
  for point-in-time gauges (e.g. `*_CUR_SIZE`, `AGENTS_REGISTERED`) = `gauge`.
- The current integration does NOT call any of these 8 functions per-object; it aggregates
  only to instance/db/bufferpool/tablespace/log
  (`/home/bits/dd/integrations-core/ibm_db2/dev-docs/db2-fidelity-plan/_research/code-ibm_db2-current.md`
  lines 359, 366). Integration code lives at
  `/home/bits/dd/integrations-core/ibm_db2/datadog_checks/ibm_db2/queries.py` and
  `.../ibm_db2.py`.

Live monitor-switch settings that gate whether these counters are populated
(`_raw/04-monitor-config.txt`): `mon_req_metrics=BASE`, `mon_act_metrics=BASE`,
`mon_obj_metrics=EXTENDED`, `mon_uow_data=NONE`. BASE request metrics are sufficient to
populate the request-time / wait-time families in `MON_GET_SERVICE_SUBCLASS` and
`MON_GET_WORKLOAD`; `mon_obj_metrics=EXTENDED` populates the object (`MON_GET_TABLE`/
`MON_GET_INDEX`) data/index page counters.

---

## 1. MON_GET_TABLE — per-table activity & I/O

DESCRIBE dump: `_raw/02-monget-key-columns.txt` L1521-1613 (91 columns).

Purpose: per-table (and per-data-partition, per-member) physical and logical access
metrics — row counts, scans, page footprint, lock waits at table granularity, bufferpool
logical/physical reads broken out by object type (data/index/xda/col). The canonical
source for "hot tables", scan-heavy tables, lock-contended tables.

Signature (general Db2 12.1 knowledge — verify): `MON_GET_TABLE(tabschema, tabname, member)`;
pass NULLs / `-2` for member to get all. Returns one row per (table, data partition, member).

Identity / dimension columns:
| Column | Type | Notes |
|---|---|---|
| TABSCHEMA | VARCHAR(128) | schema |
| TABNAME | VARCHAR(128) | table name |
| MEMBER | SMALLINT | DB member/partition |
| TAB_TYPE | VARCHAR(14) | USER_TABLE / etc. |
| TAB_FILE_ID | BIGINT | |
| DATA_PARTITION_ID | INTEGER | |
| TBSP_ID / INDEX_TBSP_ID / LONG_TBSP_ID | BIGINT | tablespace ids |
| DBPARTITIONNUM | SMALLINT | |
| TAB_ORGANIZATION | CHARACTER(1) | row ('R') vs column ('C') organized |
| TENANT_ID | BIGINT | |
| DATA_SHARING_STATE | VARCHAR(19) | pureScale |

Key metric columns (all BIGINT counts unless noted):
- Row activity: `ROWS_READ`, `ROWS_INSERTED`, `ROWS_UPDATED`, `ROWS_DELETED`,
  `NO_CHANGE_UPDATES`, `TABLE_SCANS`, `OVERFLOW_ACCESSES`, `OVERFLOW_CREATES`, `PAGE_REORGS`.
- Stats/RTS: `STATS_ROWS_MODIFIED`, `RTS_ROWS_MODIFIED`, `NUM_PAGE_DICT_BUILT`,
  `NUM_COLUMNS_REFERENCED`, `SECTION_EXEC_WITH_COL_REFERENCES`.
- Size (pages, point-in-time gauge): `DATA_OBJECT_L_PAGES`, `LOB_OBJECT_L_PAGES`,
  `LONG_OBJECT_L_PAGES`, `INDEX_OBJECT_L_PAGES`, `XDA_OBJECT_L_PAGES`, `COL_OBJECT_L_PAGES`.
- Lock contention at table scope: `LOCK_WAIT_TIME` (ms), `LOCK_WAITS`,
  `LOCK_WAIT_TIME_GLOBAL`, `LOCK_WAITS_GLOBAL`, `LOCK_ESCALS`, `LOCK_ESCALS_GLOBAL`.
- Direct I/O: `DIRECT_READS`, `DIRECT_READ_REQS`, `DIRECT_WRITES`, `DIRECT_WRITE_REQS`.
- Bufferpool reads by object (data): `OBJECT_DATA_L_READS`, `OBJECT_DATA_P_READS`,
  `OBJECT_DATA_GBP_L_READS`, `OBJECT_DATA_GBP_P_READS`, `OBJECT_DATA_GBP_INVALID_PAGES`,
  `OBJECT_DATA_LBP_PAGES_FOUND`, `OBJECT_DATA_GBP_INDEP_PAGES_FOUND_IN_LBP`.
- Same pattern for XDA (`OBJECT_XDA_*`) and column-organized (`OBJECT_COL_*`).
- Caching-tier (NVMe/SSD buffer tier) variants: `OBJECT_DATA_CACHING_TIER_L_READS`,
  `OBJECT_DATA_CACHING_TIER_PAGES_FOUND`, `OBJECT_DATA_CACHING_TIER_GBP_INVALID_PAGES`,
  `OBJECT_DATA_CACHING_TIER_GBP_INDEP_PAGES_FOUND` (and `OBJECT_XDA_CACHING_TIER_*`,
  `OBJECT_COL_CACHING_TIER_*`), plus generic
  `CACHING_TIER_DIRECT_READS`/`_READ_TIME`/`_READ_REQS`, `CACHING_TIER_PAGE_READ_TIME`.
- External table I/O: `EXT_TABLE_RECV_WAIT_TIME`, `EXT_TABLE_RECVS_TOTAL`,
  `EXT_TABLE_RECV_VOLUME`, `EXT_TABLE_READ_VOLUME`, `EXT_TABLE_SEND_WAIT_TIME`,
  `EXT_TABLE_SENDS_TOTAL`, `EXT_TABLE_SEND_VOLUME`, `EXT_TABLE_WRITE_VOLUME`.

Suggested metric mapping (counts -> `monotonic_count`, `*_PAGES` -> `gauge`, `*_TIME` ->
`monotonic_count` ms). Tag by `tabschema`, `tabname`, `member`, `tab_organization`.

---

## 2. MON_GET_INDEX — per-index activity

DESCRIBE dump: `_raw/02-monget-key-columns.txt` L1621-1657 (35 columns).

Purpose: per-index access and structural-maintenance metrics — scans, key updates,
node splits, pseudo-delete/cleanup activity, index bufferpool reads. Source for index
efficiency, index-only scan ratio, and B-tree fragmentation/maintenance signals.

Signature (general Db2 12.1 knowledge — verify): `MON_GET_INDEX(tabschema, tabname, member)`.
Returns one row per (index = TABSCHEMA+TABNAME+IID, data partition, member).

Identity / structure columns:
| Column | Type | Notes |
|---|---|---|
| TABSCHEMA | VARCHAR(128) | |
| TABNAME | VARCHAR(128) | |
| IID | SMALLINT | index id (unique within table) |
| MEMBER | SMALLINT | |
| DATA_PARTITION_ID | INTEGER | |
| NLEAF | BIGINT | # leaf pages (gauge) |
| NLEVELS | SMALLINT | B-tree depth (gauge) |
| TENANT_ID | BIGINT | |

Key metric columns (BIGINT counts):
- Access: `INDEX_SCANS`, `INDEX_ONLY_SCANS`, `INDEX_JUMP_SCANS`.
- Mutation: `KEY_UPDATES`, `INCLUDE_COL_UPDATES`.
- Cleanup / dead space: `PSEUDO_DELETES`, `DEL_KEYS_CLEANED`, `PSEUDO_EMPTY_PAGES`,
  `EMPTY_PAGES_REUSED`, `EMPTY_PAGES_DELETED`, `PAGES_MERGED`, `PAGE_ALLOCATIONS`.
- Splits (fragmentation/cost): `ROOT_NODE_SPLITS`, `INT_NODE_SPLITS`,
  `BOUNDARY_LEAF_NODE_SPLITS`, `NONBOUNDARY_LEAF_NODE_SPLITS`.
- Bufferpool index reads: `OBJECT_INDEX_L_READS`, `OBJECT_INDEX_P_READS`,
  `OBJECT_INDEX_GBP_L_READS`, `OBJECT_INDEX_GBP_P_READS`,
  `OBJECT_INDEX_GBP_INVALID_PAGES`, `OBJECT_INDEX_LBP_PAGES_FOUND`,
  `OBJECT_INDEX_GBP_INDEP_PAGES_FOUND_IN_LBP`.
- Caching tier: `OBJECT_INDEX_CACHING_TIER_L_READS`,
  `OBJECT_INDEX_CACHING_TIER_PAGES_FOUND`, `OBJECT_INDEX_CACHING_TIER_GBP_INVALID_PAGES`,
  `OBJECT_INDEX_CACHING_TIER_GBP_INDEP_PAGES_FOUND`.

Tag by `tabschema`, `tabname`, `iid`, `member`. Note: `MON_GET_INDEX` does not return the
index *name*; join to `SYSCAT.INDEXES` on (TABSCHEMA,TABNAME,IID) to label it.

---

## 3. MON_GET_INSTANCE — instance-level agents & gateway

DESCRIBE dump: `_raw/02-monget-key-columns.txt` L2447-2474 (24 columns).

Purpose: single-row, instance-wide status: agent pool health, coordinator agent counts,
local connections, DRDA gateway connections, and product/version identification. This is
the cheapest "is the instance healthy / agent saturation" probe and the authoritative
in-band version string.

Signature (general Db2 12.1 knowledge — verify): `MON_GET_INSTANCE(member)`; `-1`/`-2` for
current/all members. Returns one row per member.

All columns (verbatim):
| Column | Type | Meaning / metric guidance |
|---|---|---|
| MEMBER | SMALLINT | dimension |
| DB2_STATUS | VARCHAR(12) | ACTIVE/QUIESCE_PEND/QUIESCED (service-check candidate) |
| DB2START_TIME | TIMESTAMP(26) | instance start; derive uptime |
| TIMEZONEOFFSET | INTEGER | |
| TIMEZONEID | VARCHAR(255) | |
| CON_LOCAL_DBASES | BIGINT | # local databases with active connections (gauge) |
| TOTAL_CONNECTIONS | BIGINT | connections to instance (gauge) |
| AGENTS_REGISTERED | BIGINT | agents registered (gauge) |
| AGENTS_REGISTERED_TOP | BIGINT | high-water (gauge) |
| IDLE_AGENTS | BIGINT | agents in pool idle (gauge) |
| AGENTS_FROM_POOL | BIGINT | agents assigned from pool (monotonic_count) |
| AGENTS_CREATED_EMPTY_POOL | BIGINT | agents created because pool empty (monotonic_count) — pool-pressure signal |
| NUM_COORD_AGENTS | BIGINT | coordinator agents (gauge) |
| COORD_AGENTS_TOP | BIGINT | high-water (gauge) |
| AGENTS_STOLEN | BIGINT | agents reassigned (monotonic_count) |
| GW_TOTAL_CONS | BIGINT | gateway connections total (monotonic_count) |
| GW_CUR_CONS | BIGINT | current gateway connections (gauge) |
| GW_CONS_WAIT_HOST | BIGINT | gateway conns waiting on host (gauge) |
| GW_CONS_WAIT_CLIENT | BIGINT | gateway conns waiting on client (gauge) |
| NUM_GW_CONN_SWITCHES | BIGINT | (monotonic_count) |
| PRODUCT_NAME | VARCHAR(32) | e.g. "DB2 v12.1.4.0" |
| SERVICE_LEVEL | VARCHAR(64) | fixpack/service level string |
| SERVER_PLATFORM | VARCHAR(32) | e.g. LINUXX8664 |
| NETWORK_INTERFACE_BOUND | VARCHAR(255) | |

---

## 4. MON_GET_SERVICE_SUBCLASS — WLM service-class workload metrics

DESCRIBE dump: `_raw/02-monget-key-columns.txt` L1684-2061 (376 columns).

Purpose: comprehensive WLM service-subclass roll-up of essentially every request/activity
monitor element — time-spent breakdown, wait-time breakdown, sort/hash/compile activity,
SQL statement mix, bufferpool reads, FCM/IPC/TCPIP communications, and (uniquely) WLM
admission/parallelism gauges. This is the richest aggregate for "where is time going" at
a workload-class granularity. Default classes always exist (`SYSDEFAULTSUBCLASS` under
`SYSDEFAULTUSERCLASS` / `SYSDEFAULTSYSTEMCLASS` / `SYSDEFAULTMAINTENANCECLASS`), so it
returns useful data even with no custom WLM config.

Signature (general Db2 12.1 knowledge — verify):
`MON_GET_SERVICE_SUBCLASS(service_superclass_name, service_subclass_name, member)`; NULLs
for all. One row per (superclass, subclass, member).

Identity columns:
| Column | Type |
|---|---|
| SERVICE_SUPERCLASS_NAME | VARCHAR(128) |
| SERVICE_SUBCLASS_NAME | VARCHAR(128) |
| SERVICE_CLASS_ID | INTEGER |
| MEMBER | SMALLINT |

Key metric families (all BIGINT counts; `*_TIME` in ms; DOUBLE for utilization gauges):

Request / activity throughput:
- `ACT_COMPLETED_TOTAL`, `ACT_ABORTED_TOTAL`, `ACT_REJECTED_TOTAL`,
  `APP_ACT_COMPLETED_TOTAL`, `APP_ACT_ABORTED_TOTAL`, `APP_ACT_REJECTED_TOTAL`,
  `ACT_RQSTS_TOTAL`, `RQSTS_COMPLETED_TOTAL`, `APP_RQSTS_COMPLETED_TOTAL`,
  `TOTAL_APP_RQST_TIME`, `TOTAL_RQST_TIME`.

Time-spent decomposition (the core "tier breakdown"):
- `TOTAL_CPU_TIME` (microseconds — general Db2 note, this element is in us not ms; verify),
  `TOTAL_WAIT_TIME`, `TOTAL_RQST_TIME`, `TOTAL_SECTION_TIME`, `TOTAL_SECTION_PROC_TIME`,
  `TOTAL_ACT_TIME`, `TOTAL_ACT_WAIT_TIME`, `TOTAL_ROUTINE_TIME`,
  `TOTAL_ROUTINE_USER_CODE_TIME`, `TOTAL_ROUTINE_USER_CODE_PROC_TIME`,
  `TOTAL_COMPILE_TIME`/`_PROC_TIME`, `TOTAL_IMPLICIT_COMPILE_TIME`/`_PROC_TIME`,
  `TOTAL_COMMIT_TIME`/`_PROC_TIME`, `TOTAL_ROLLBACK_TIME`/`_PROC_TIME`,
  `TOTAL_SECTION_SORT_TIME`/`_PROC_TIME`, `TOTAL_COL_TIME`/`_PROC_TIME`,
  `TOTAL_DISP_RUN_QUEUE_TIME`, `WLM_QUEUE_TIME_TOTAL`.

Wait-time components (sum approximately to `TOTAL_WAIT_TIME`):
- `POOL_READ_TIME`, `POOL_WRITE_TIME`, `DIRECT_READ_TIME`, `DIRECT_WRITE_TIME`,
  `LOCK_WAIT_TIME`, `LOG_DISK_WAIT_TIME`, `LOG_BUFFER_WAIT_TIME`, `AGENT_WAIT_TIME`,
  `CLIENT_IDLE_WAIT_TIME`, `FCM_RECV_WAIT_TIME`, `FCM_SEND_WAIT_TIME`,
  `IPC_RECV_WAIT_TIME`, `IPC_SEND_WAIT_TIME`, `TCPIP_RECV_WAIT_TIME`,
  `TCPIP_SEND_WAIT_TIME`, `PREFETCH_WAIT_TIME`, `EVMON_WAIT_TIME`,
  `RECLAIM_WAIT_TIME`, `SPACEMAPPAGE_RECLAIM_WAIT_TIME`, `CF_WAIT_TIME`,
  `TOTAL_EXTENDED_LATCH_WAIT_TIME`, `COMM_EXIT_WAIT_TIME`, `FED_WAIT_TIME`.
- Paired counts: `AGENT_WAITS_TOTAL`, `LOCK_WAITS`, `LOG_DISK_WAITS_TOTAL`,
  `NUM_LOG_BUFFER_FULL`, `PREFETCH_WAITS`, `EVMON_WAITS_TOTAL`,
  `TOTAL_EXTENDED_LATCH_WAITS`, `CF_WAITS`, `COMM_EXIT_WAITS`, `FED_WAITS_TOTAL`.

Bufferpool / I/O (pages, counts):
- `POOL_DATA_L_READS`, `POOL_INDEX_L_READS`, `POOL_XDA_L_READS`, `POOL_COL_L_READS`,
  `POOL_TEMP_DATA_L_READS`, `POOL_TEMP_INDEX_L_READS`, `POOL_TEMP_XDA_L_READS`,
  `POOL_TEMP_COL_L_READS`; physical `*_P_READS` siblings; writes
  `POOL_DATA_WRITES`/`POOL_INDEX_WRITES`/`POOL_XDA_WRITES`/`POOL_COL_WRITES`;
  GBP/LBP variants `POOL_DATA_GBP_L_READS`, `POOL_DATA_GBP_P_READS`,
  `POOL_DATA_LBP_PAGES_FOUND`, `POOL_DATA_GBP_INVALID_PAGES`,
  `POOL_DATA_GBP_INDEP_PAGES_FOUND_IN_LBP` (and INDEX/XDA/COL siblings);
  full caching-tier matrix `POOL_*_CACHING_TIER_L_READS`/`_PAGES_FOUND`/
  `_PAGE_WRITES`/`_PAGE_UPDATES`/`_GBP_INVALID_PAGES`/`_GBP_INDEP_PAGES_FOUND` plus
  `POOL_CACHING_TIER_PAGE_READ_TIME`/`_WRITE_TIME`.
- Direct I/O: `DIRECT_READS`, `DIRECT_READ_REQS`, `DIRECT_WRITES`, `DIRECT_WRITE_REQS`.

Sort / hash / OLAP:
- `TOTAL_SORTS`, `TOTAL_SECTION_SORTS`, `SORT_OVERFLOWS`, `POST_THRESHOLD_SORTS`,
  `POST_SHRTHRESHOLD_SORTS`, `SORT_HEAP_ALLOCATED`, `SORT_SHRHEAP_ALLOCATED`,
  `ACTIVE_SORTS`, `ACTIVE_SORT_CONSUMERS`, `TOTAL_HASH_JOINS`, `TOTAL_HASH_LOOPS`,
  `HASH_JOIN_OVERFLOWS`, `HASH_JOIN_SMALL_OVERFLOWS`, `POST_THRESHOLD_HASH_JOINS`,
  `POST_SHRTHRESHOLD_HASH_JOINS`, `TOTAL_HASH_GRPBYS`, `HASH_GRPBY_OVERFLOWS`,
  `POST_THRESHOLD_HASH_GRPBYS`, `TOTAL_OLAP_FUNCS`, `OLAP_FUNC_OVERFLOWS`,
  `POST_THRESHOLD_OLAP_FUNCS`, `ACTIVE_HASH_JOINS`, `ACTIVE_HASH_GRPBYS`,
  `ACTIVE_OLAP_FUNCS`.

SQL statement mix (counts):
- `DYNAMIC_SQL_STMTS`, `STATIC_SQL_STMTS`, `FAILED_SQL_STMTS`, `SELECT_SQL_STMTS`,
  `UID_SQL_STMTS`, `DDL_SQL_STMTS`, `MERGE_SQL_STMTS`, `XQUERY_STMTS`, `CALL_SQL_STMTS`,
  `IMPLICIT_REBINDS`, `BINDS_PRECOMPILES`, `ROWS_MODIFIED`, `ROWS_READ`, `ROWS_RETURNED`,
  `ROWS_INSERTED`/`ROWS_UPDATED`/`ROWS_DELETED` and internal `INT_ROWS_*`.

Caches / locks / commits:
- `PKG_CACHE_INSERTS`, `PKG_CACHE_LOOKUPS`, `CAT_CACHE_INSERTS`, `CAT_CACHE_LOOKUPS`,
  `DEADLOCKS`, `LOCK_ESCALS`, `LOCK_TIMEOUTS`, `LOCK_WAITS_GLOBAL`,
  `LOCK_WAIT_TIME_GLOBAL`, `LOCK_TIMEOUTS_GLOBAL`, `LOCK_ESCALS_MAXLOCKS`,
  `LOCK_ESCALS_LOCKLIST`, `LOCK_ESCALS_GLOBAL`, `THRESH_VIOLATIONS`,
  `NUM_LW_THRESH_EXCEEDED`, `TOTAL_APP_COMMITS`, `INT_COMMITS`, `TOTAL_APP_ROLLBACKS`,
  `INT_ROLLBACKS`.

Communications volume (bytes): `FCM_RECV_VOLUME`/`FCM_SEND_VOLUME`,
`IPC_RECV_VOLUME`/`IPC_SEND_VOLUME`, `TCPIP_RECV_VOLUME`/`TCPIP_SEND_VOLUME`,
`IDA_*_VOLUME`, plus `*_SENDS_TOTAL`/`*_RECVS_TOTAL` counts and FCM message/TQ subfamilies
(`FCM_MESSAGE_*`, `FCM_TQ_*`).

Utility activity: `TOTAL_RUNSTATS`/`_TIME`/`_PROC_TIME`, `TOTAL_REORGS`/`_TIME`,
`TOTAL_LOADS`/`_TIME`, `TOTAL_BACKUPS`/`_TIME`, `TOTAL_INDEXES_BUILT`/`_TIME`.

WLM admission & parallelism (notable — DOUBLE gauges unique to this family vs WORKLOAD):
- `AGENT_LOAD_TRGT_UTILIZATION` (DOUBLE), `SORT_SHRHEAP_UTILIZATION` (DOUBLE),
  `AGENT_LOAD_TRGT_DEMAND` (DOUBLE), `SORT_SHRHEAP_DEMAND` (DOUBLE),
  `EFF_PARALLELISM`, `ACTUAL_PARALLELISM`, `ADM_OVERFLOWS`, `ADM_BYPASS_ACT_TOTAL`,
  `WLM_QUEUE_ASSIGNMENTS_TOTAL`, priority counts
  `LOW_PRIORITY_ACT_TOTAL`/`MEDIUM_PRIORITY_ACT_TOTAL`/`HIGH_PRIORITY_ACT_TOTAL`/
  `CRITICAL_PRIORITY_ACT_TOTAL`.

TLS/connect (12.1): `TOTAL_TLS_SENDS`/`_TIME`/`_PROC_TIME`, `TOTAL_TLS_RECVS`/...,
`TOTAL_TLS_CONNECTS`/..., `TOTAL_CONNECT_REQUESTS`/`_TIME`,
`TOTAL_CONNECT_AUTHENTICATIONS`/`_TIME`. AI model integration (12.1):
`MODEL_PROVIDER_WAIT_TIME`, `MODEL_PROVIDER_WAITS_TOTAL`.

Tag by `service_superclass_name`, `service_subclass_name`, `member`. Counters reset on WLM
service-class statistics reset.

---

## 5. MON_GET_WORKLOAD — WLM workload-definition metrics

DESCRIBE dump: `_raw/02-monget-key-columns.txt` L2069-2446 (371 columns).

Purpose: identical metric element set to `MON_GET_SERVICE_SUBCLASS` but aggregated by WLM
**workload definition** (who/what connected) rather than service class (how it was
prioritized). Diff vs SUBCLASS (verified by comparing the two dump sections):
- Identity columns differ: WORKLOAD has `WORKLOAD_NAME` VARCHAR(128) + `WORKLOAD_ID`
  INTEGER + `MEMBER` (instead of `SERVICE_SUPERCLASS_NAME`/`SERVICE_SUBCLASS_NAME`/
  `SERVICE_CLASS_ID`).
- 371 vs 376 columns: WORKLOAD omits the ~5 service-class-only admission gauges
  (`AGENT_LOAD_TRGT_UTILIZATION`, `SORT_SHRHEAP_UTILIZATION`, `AGENT_LOAD_TRGT_DEMAND`,
  `SORT_SHRHEAP_DEMAND`, and one related). All other metric families listed under
  §4 are present (request/activity throughput, time decomposition, wait-time components,
  bufferpool/IO, sort/hash, SQL mix, caches, locks, commits, comms, utilities, TLS, etc.).

Confirmed present in WORKLOAD (workload-centric throughput/UOW — verified from L2069-2446):
`ACT_COMPLETED_TOTAL`, `ACT_ABORTED_TOTAL`, `ACT_REJECTED_TOTAL`,
`APP_ACT_COMPLETED_TOTAL`, `APP_ACT_ABORTED_TOTAL`, `APP_ACT_REJECTED_TOTAL`,
`RQSTS_COMPLETED_TOTAL`, `APP_RQSTS_COMPLETED_TOTAL`, `TOTAL_APP_RQST_TIME`,
`TOTAL_APP_SECTION_EXECUTIONS`, `TOTAL_APP_COMMITS`, `INT_COMMITS`,
`TOTAL_APP_ROLLBACKS`, `INT_ROLLBACKS`, `TOTAL_COMMIT_TIME`/`_PROC_TIME`,
`TOTAL_ROLLBACK_TIME`/`_PROC_TIME`.

Signature (general Db2 12.1 knowledge — verify): `MON_GET_WORKLOAD(workload_name, member)`.
Default workload `SYSDEFAULTUSERWORKLOAD` (id 1) always exists. Tag by `workload_name`,
`workload_id`, `member`.

Plan note: SUBCLASS and WORKLOAD double-count the same underlying activity along two
different axes — collect both only if WLM-class vs workload-definition dimensions are both
wanted; otherwise WORKLOAD alone gives "per logical workload" and is usually the more
intuitive dimension for app-level attribution.

---

## 6. MON_GET_AGENT — per-agent / per-EDU runtime state

**NOT in DESCRIBE dump.** Function confirmed present (`_raw/01...txt` L13). Columns below
are general Db2 12.1 knowledge — verify against a live `DESCRIBE SELECT * FROM
TABLE(MON_GET_AGENT('','',CAST(NULL AS BIGINT),-2))`.

Purpose: one row per active agent / EDU (engine dispatchable unit) — the "what is each
worker thread doing right now" view. Used for blocking-tree / current-activity analysis,
agent-state distribution, and mapping agents to application handles. Complements
`MON_GET_INSTANCE` (aggregate agent counts) with per-agent detail.

Signature (general Db2 12.1 knowledge — verify):
`MON_GET_AGENT(service_superclass_name, service_subclass_name, application_handle, member)`.

Key columns (general Db2 12.1 knowledge — verify):
| Column | Type | Notes |
|---|---|---|
| APPLICATION_HANDLE | BIGINT | join key to MON_GET_CONNECTION/UNIT_OF_WORK |
| APPLICATION_NAME | VARCHAR | |
| APPLICATION_ID | VARCHAR | |
| AGENT_TID | BIGINT | EDU/thread id |
| AGENT_PID | BIGINT | |
| AGENT_TYPE | VARCHAR | COORDINATOR / SUBAGENT / etc. |
| AGENT_STATE | VARCHAR | ASSOCIATED / ACTIVE / IDLE |
| EVENT_STATE | VARCHAR | EXECUTING / IDLE / WAITING |
| EVENT_TYPE | VARCHAR | what the agent is doing |
| EVENT_OBJECT | VARCHAR | object the event is on (e.g. REQUEST, WAIT, LOCK) |
| EVENT_OBJECT_NAME | VARCHAR | |
| REQUEST_TYPE | VARCHAR | current request kind |
| WORKLOAD_NAME / WORKLOAD_ID | VARCHAR/INTEGER | WLM workload |
| SERVICE_SUPERCLASS_NAME / SERVICE_SUBCLASS_NAME | VARCHAR | WLM class |
| ENTRY_TIME / LAST_ACTIVITY_TIME / EVENT_BEGIN_TIME | TIMESTAMP | for age/duration |
| UOW_ID / ACTIVITY_ID | INTEGER | |
| EXECUTABLE_ID | VARBINARY | join key to MON_GET_PKG_CACHE_STMT (statement text) |
| MEMBER | SMALLINT | |

This is primarily a "current state" snapshot (gauges / categorical), not monotonic
counters. Useful for activity-sampling-style collection: count agents by
`event_state`/`event_object`, identify long-running EVENT_BEGIN_TIME.

---

## 7. MON_GET_MEMORY_SET — memory set allocation (OS-committed)

**NOT in DESCRIBE dump.** Function confirmed present (`_raw/01...txt` L40). Columns below
are general Db2 12.1 knowledge — verify against live `DESCRIBE`.

Purpose: per memory **set** (the top-level OS memory reservation Db2 makes) committed and
allocated sizes. One row per (host, db, memory_set_type, member). The coarse layer above
`MON_GET_MEMORY_POOL`. Source for "how much memory has Db2 reserved from the OS, per area".

Signature (general Db2 12.1 knowledge — verify):
`MON_GET_MEMORY_SET(memory_set_type, db_name, member)`.

Key columns (general Db2 12.1 knowledge — verify):
| Column | Type | Notes |
|---|---|---|
| MEMORY_SET_TYPE | VARCHAR | DATABASE / INSTANCE / APPLICATION / BUFFERPOOL / FCM / FMP / PRIVATE / DBMS |
| HOST_NAME | VARCHAR | |
| DB_NAME | VARCHAR | |
| MEMBER | SMALLINT | |
| MEMORY_SET_ID | INTEGER | |
| MEMORY_SET_USED | BIGINT | KB currently used in set (gauge) |
| MEMORY_SET_COMMITTED | BIGINT | KB committed from OS (gauge) |
| MEMORY_SET_USED_HWM | BIGINT | high-water KB (gauge) |
| ADDITIONAL_COMMITTED | BIGINT | KB (gauge) |
| MEMORY_SET_SIZE | BIGINT | configured size KB (gauge) |
| EDU_ID / BP_ID | BIGINT | for bufferpool/EDU sets |

Units: KB (general Db2 convention for memory monitor elements — verify). All point-in-time
gauges. Tag by `memory_set_type`, `db_name`, `member`. The `DATABASE` and `INSTANCE` set
types are the highest-value gauges for capacity tracking.

---

## 8. MON_GET_MEMORY_POOL — memory pool allocation (within sets)

**NOT in DESCRIBE dump.** Function confirmed present (`_raw/01...txt` L39). Columns below
are general Db2 12.1 knowledge — verify against live `DESCRIBE`.

Purpose: per memory **pool** detail within each memory set (e.g. buffer pool heap, lock
list, package cache, sort heap, utility heap, catalog cache, application heap). The
granular memory-attribution view. Source for "which heap is growing / near its limit".

Signature (general Db2 12.1 knowledge — verify):
`MON_GET_MEMORY_POOL(memory_set_type, db_name, member)`.

Key columns (general Db2 12.1 knowledge — verify):
| Column | Type | Notes |
|---|---|---|
| MEMORY_SET_TYPE | VARCHAR | parent set type |
| MEMORY_POOL_TYPE | VARCHAR | e.g. BP, LOCKMGR, PACKAGE_CACHE, CAT_CACHE, SORTHEAP, SHARED_SORTHEAP, UTILITY, APPL_CONTROL, DATABASE, APP_GROUP, XMLCACHE |
| HOST_NAME | VARCHAR | |
| DB_NAME | VARCHAR | |
| MEMBER | SMALLINT | |
| APPLICATION_HANDLE | BIGINT | for per-app pools (nullable) |
| MEMORY_POOL_ID | INTEGER | |
| MEMORY_POOL_USED | BIGINT | KB used now (gauge) |
| MEMORY_POOL_USED_HWM | BIGINT | high-water KB (gauge) |
| EDU_ID | BIGINT | |
| BP_ID | BIGINT | bufferpool id when pool is a BP |

Units: KB (general Db2 convention — verify). Gauges. Tag by `memory_pool_type`,
`memory_set_type`, `db_name`, `member`. The package-cache, lock-list, and sort-heap pool
`*_USED`/`*_USED_HWM` are the highest-signal memory-pressure metrics; pair with config
limits (`PCKCACHESZ`, `LOCKLIST`, `SHEAPTHRES_SHR`) from `db2-config-settings.md`.

---

## Cross-cutting notes for the plan

- **Identity-only vs counter functions**: TABLE/INDEX/SERVICE_SUBCLASS/WORKLOAD are
  monotonic-counter (delta-able) sources -> emit as `monotonic_count`/`rate` with object
  tags. INSTANCE/MEMORY_SET/MEMORY_POOL/AGENT are mostly point-in-time gauges/state.
- **Cardinality**: per-table and per-index emit one series per object per member —
  cardinality control (top-N by activity, schema filtering) will be needed; the integration
  currently emits none of these (`code-ibm_db2-current.md` L366).
- **WLM defaults always populated**: SUBCLASS/WORKLOAD return rows even without custom WLM,
  via `SYSDEFAULT*` classes/workload, so these are safe to query unconditionally.
- **Version/identity**: `MON_GET_INSTANCE.SERVICE_LEVEL` / `PRODUCT_NAME` /
  `SERVER_PLATFORM` give the authoritative in-band version (matches the
  `DB2/LINUXX8664 12.1.4.0` banner in the raw dumps) — good for a `version` tag / metadata.
- **Three functions need a live DESCRIBE before coding**: AGENT, MEMORY_SET, MEMORY_POOL
  column lists here are knowledge-based; capture
  `DESCRIBE SELECT * FROM TABLE(MON_GET_MEMORY_SET(...))` etc. to lock exact names/types
  before mapping metrics.
- Related SYSIBMADM aggregate views exist as alternatives/cross-checks
  (`_raw/03-sysibmadm-objects.txt`): `MON_DB_SUMMARY` (L43),
  `MON_SERVICE_SUBCLASS_SUMMARY` (L46), `MON_WORKLOAD_SUMMARY` (L49); legacy snapshot
  admin views `SNAPAGENT`/`SNAPAGENT_MEMORY_POOL`/`SNAPDB_MEMORY_POOL`/
  `SNAPDBM_MEMORY_POOL` (L55,56,64,65) overlap AGENT/MEMORY data but are deprecated — prefer
  the MON_GET_* functions.
