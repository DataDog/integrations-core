# Metric Category Map: `wlm-workload` (WLM service-class / workload metrics)

Maps the Db2 Workload Manager metric family — `MON_GET_SERVICE_SUBCLASS` (WLM service
subclass roll-up) and `MON_GET_WORKLOAD` (WLM workload-definition roll-up) — onto proposed
`ibm_db2.*` metrics, for the postgres/mysql-fidelity plan.

## Sources

- Column lists verbatim from the live `DESCRIBE` dump
  `/home/bits/dd/integrations-core/ibm_db2/dev-docs/db2-fidelity-plan/_research/_raw/02-monget-key-columns.txt`:
  - **`MON_GET_SERVICE_SUBCLASS`** — L1684-2061 (376 cols). Identity:
    `SERVICE_SUPERCLASS_NAME` VARCHAR(128), `SERVICE_SUBCLASS_NAME` VARCHAR(128),
    `SERVICE_CLASS_ID` INTEGER, `MEMBER` SMALLINT.
  - **`MON_GET_WORKLOAD`** — L2069+ (371 cols). Identity:
    `WORKLOAD_NAME` VARCHAR(128), `WORKLOAD_ID` INTEGER, `MEMBER` SMALLINT.
- Server under test: **DB2/LINUXX8664 12.1.4.0**.
- Catalog narrative: `.../db2-monget-catalog-2.md` §4 (SUBCLASS) and §5 (WORKLOAD).
- pg/mysql analog search: `postgres/metadata.csv`, `mysql/metadata.csv` (greped for
  cpu/activity/wait/statement-mix metrics).

## Why this category is Db2-native (no real pg/mysql analog)

WLM (Workload Manager) is a Db2-specific construct: every request/activity is classified
into a **service class** (superclass + subclass — how Db2 prioritizes/throttles it) and a
**workload** (workload definition — who/what connected). Neither Postgres nor MySQL has a
comparable in-engine workload-classification + per-class accounting layer, so almost every
column here has **NO pg/mysql analog**. The few near-analogs are coarse, server-wide, and
NOT per-class:

- mysql `mysql.performance.cpu_time` / `user_time` / `kernel_time` — whole-`mysqld`
  process CPU **percent** via psutil, not per-workload SQL CPU. Db2 `TOTAL_CPU_TIME` is
  far richer (per service-class / per-workload, monotonic microseconds).
- mysql `mysql.performance.com_select` / `com_insert` / `com_update` / `com_delete` /
  `questions` / `queries` — server-wide statement **rates** (from `SHOW GLOBAL STATUS`),
  not attributable to a workload class. Db2's `SELECT_SQL_STMTS` / `UID_SQL_STMTS` /
  `DDL_SQL_STMTS` / `DYNAMIC_SQL_STMTS` etc. are the same intent **broken out per WLM
  class** — strictly higher fidelity.
- mysql `mysql.performance.wait_event.*` (DBM-only) / postgres `postgresql.activity.wait_event` —
  point-in-time wait sampling, not a cumulative per-class wait-time decomposition. Db2's
  `TOTAL_WAIT_TIME` + components (`LOCK_WAIT_TIME`, `POOL_READ_TIME`, `LOG_DISK_WAIT_TIME`,
  …) give a cumulative tier breakdown per class — closest in spirit but structurally
  different.
- postgres `postgresql.active_queries` / `waiting_queries` (collect_activity_metrics) —
  point-in-time gauges, not per-class throughput counters. Db2 `ACT_COMPLETED_TOTAL` /
  `ACT_ABORTED_TOTAL` are cumulative per-class.

Conclusion: treat this whole category as **Db2-native, additive fidelity** — there are no
pg/mysql metric names to mirror; emit new `ibm_db2.wlm.*` metrics.

## Always-populated (no custom WLM config needed)

Default WLM objects always exist, so both functions return rows out of the box:

- Service classes: `SYSDEFAULTUSERCLASS` / `SYSDEFAULTSYSTEMCLASS` /
  `SYSDEFAULTMAINTENANCECLASS`, each with `SYSDEFAULTSUBCLASS` (plus
  `SYSDEFAULTSYSCLASS`'s internal subclasses).
- Workload: `SYSDEFAULTUSERWORKLOAD` (id 1) and `SYSDEFAULTADMWORKLOAD`.

So the collector can call both unconditionally and get the entire instance's activity
attributed to the default classes/workload even where the DBA never defined custom WLM.
With custom WLM defined, the same metrics fan out per user-defined class/workload — same
metric names, more tag values.

## Units / type conventions (Db2 monitor elements)

- All `*_TIME` counters are **milliseconds**, monotonic → `monotonic_count` (CSV `count`),
  `unit_name=millisecond`. **Exception: `TOTAL_CPU_TIME` is microseconds** (Db2 ships this
  one element in µs) → `unit_name=microsecond`. Verify on the live box before coding.
- `*_VOLUME` are **bytes** → `count`, `byte`.
- `POOL_*_READS`/`*_WRITES` are **pages** → `count`, `page`.
- Throughput/activity/statement/lock/sort counts are monotonic **counts** since DB
  activation or last WLM stats reset → `monotonic_count`.
- The four SUBCLASS-only `DOUBLE` utilization/demand columns are point-in-time → `gauge`.
- `ACTIVE_*` (active sorts/hash-joins/olap consumers) are point-in-time → `gauge`.

## Tagging (all rows in this category)

Plus base tags (`db`, `database_hostname`, `database_instance`, version tag):

- From `MON_GET_SERVICE_SUBCLASS`: `service_superclass` (SERVICE_SUPERCLASS_NAME),
  `service_subclass` (SERVICE_SUBCLASS_NAME), `service_class_id` (SERVICE_CLASS_ID),
  `member` (MEMBER).
- From `MON_GET_WORKLOAD`: `workload_name` (WORKLOAD_NAME), `workload_id` (WORKLOAD_ID),
  `member` (MEMBER).

Cardinality is naturally low (a handful of default classes/workloads × members); custom
WLM adds a bounded set of DBA-defined names. No top-N limit needed unless a site defines
very many classes.

## Double-counting note

SUBCLASS and WORKLOAD aggregate the **same** underlying activity along two axes (priority
class vs workload definition). Emitting both double-counts the totals. Recommended default:
collect **`MON_GET_WORKLOAD`** (intuitive per-logical-workload attribution) and gate
`MON_GET_SERVICE_SUBCLASS` behind a config flag (e.g. `collect_wlm_service_class_metrics`)
for sites that use custom service classes / need the priority-class axis and the
SUBCLASS-only admission/parallelism gauges. The metric names below use a function-neutral
`ibm_db2.wlm.*` namespace; the distinguishing dimension is the tag set
(`service_*` vs `workload_*`), so the same metric name carries data from whichever
function(s) are enabled.

---

## Mapping table

Legend: type/unit per the conventions above. "Source fn" = which function exposes the
column (BOTH = present in both `MON_GET_SERVICE_SUBCLASS` and `MON_GET_WORKLOAD`;
SUBCLASS-only columns are noted). Tags column lists the tag set in addition to base tags.

### Tier 1 — high-value Db2-native (collect by default)

| pg/mysql analog | Db2 source: fn + column | Proposed `ibm_db2.<name>` | Type | Unit | Tags | Notes / version-gating |
|---|---|---|---|---|---|---|
| none (cf. mysql cpu_time, coarse) | BOTH `TOTAL_CPU_TIME` | `wlm.total_cpu_time` | monotonic_count | microsecond | svc/wl + member | **µs not ms** — verify live. Headline "CPU per workload-class" metric. |
| none | BOTH `ACT_COMPLETED_TOTAL` | `wlm.activities.completed` | monotonic_count | activity | svc/wl + member | Coord activities that completed. Core throughput. |
| none | BOTH `ACT_ABORTED_TOTAL` | `wlm.activities.aborted` | monotonic_count | activity | svc/wl + member | Failures/cancellations per class. orientation -1. |
| none | BOTH `ACT_REJECTED_TOTAL` | `wlm.activities.rejected` | monotonic_count | activity | svc/wl + member | WLM admission rejections. orientation -1. |
| none | BOTH `APP_ACT_COMPLETED_TOTAL` | `wlm.app_activities.completed` | monotonic_count | activity | svc/wl + member | Application (coordinator) activities completed. |
| none | BOTH `APP_ACT_ABORTED_TOTAL` | `wlm.app_activities.aborted` | monotonic_count | activity | svc/wl + member | orientation -1. |
| none | BOTH `APP_ACT_REJECTED_TOTAL` | `wlm.app_activities.rejected` | monotonic_count | activity | svc/wl + member | orientation -1. |
| none | BOTH `ACT_RQSTS_TOTAL` | `wlm.activity_requests` | monotonic_count | request | svc/wl + member | (SUBCLASS) request count for activities. |
| none | BOTH `RQSTS_COMPLETED_TOTAL` | `wlm.requests.completed` | monotonic_count | request | svc/wl + member | Total requests completed. |
| none | BOTH `APP_RQSTS_COMPLETED_TOTAL` | `wlm.app_requests.completed` | monotonic_count | request | svc/wl + member | Coordinator requests completed. |
| ~mysql wait_event.time (diff) | BOTH `TOTAL_WAIT_TIME` | `wlm.total_wait_time` | monotonic_count | millisecond | svc/wl + member | Sum of wait components below. orientation -1. |
| none | BOTH `TOTAL_RQST_TIME` | `wlm.total_request_time` | monotonic_count | millisecond | svc/wl + member | Total time servicing requests. |
| none | BOTH `TOTAL_APP_RQST_TIME` | `wlm.total_app_request_time` | monotonic_count | millisecond | svc/wl + member | App-perceived request time. |
| none | BOTH `WLM_QUEUE_TIME_TOTAL` | `wlm.queue_time` | monotonic_count | millisecond | svc/wl + member | **WLM admission queue time** — key WLM throttling signal. orientation -1. |
| none | BOTH `WLM_QUEUE_ASSIGNMENTS_TOTAL` | `wlm.queue_assignments` | monotonic_count | assignment | svc/wl + member | # times work was queued by a WLM threshold. |
| none | BOTH `TOTAL_ACT_TIME` | `wlm.total_activity_time` | monotonic_count | millisecond | svc/wl + member | |
| none | BOTH `TOTAL_ACT_WAIT_TIME` | `wlm.total_activity_wait_time` | monotonic_count | millisecond | svc/wl + member | orientation -1. |
| none | BOTH `TOTAL_SECTION_TIME` | `wlm.total_section_time` | monotonic_count | millisecond | svc/wl + member | Section (execution) time. |
| none | BOTH `TOTAL_SECTION_PROC_TIME` | `wlm.total_section_proc_time` | monotonic_count | millisecond | svc/wl + member | Section processing (non-wait) time. |
| ~mysql com_* / questions (server-wide) | BOTH `TOTAL_APP_COMMITS` | `wlm.commits` | monotonic_count | transaction | svc/wl + member | Per-class commit throughput. |
| ~mysql com_* (server-wide) | BOTH `TOTAL_APP_ROLLBACKS` | `wlm.rollbacks` | monotonic_count | transaction | svc/wl + member | orientation -1. |
| none | BOTH `INT_COMMITS` | `wlm.internal_commits` | monotonic_count | transaction | svc/wl + member | |
| none | BOTH `INT_ROLLBACKS` | `wlm.internal_rollbacks` | monotonic_count | transaction | svc/wl + member | |

### Tier 1 — wait-time decomposition (per WLM class; sum ≈ TOTAL_WAIT_TIME)

| pg/mysql analog | Db2 source: fn + column | Proposed `ibm_db2.<name>` | Type | Unit | Tags | Notes |
|---|---|---|---|---|---|---|
| none (cf. pg activity.wait_event, diff) | BOTH `LOCK_WAIT_TIME` | `wlm.lock_wait_time` | monotonic_count | millisecond | svc/wl + member | orientation -1. |
| none | BOTH `LOCK_WAITS` | `wlm.lock_waits` | monotonic_count | wait | svc/wl + member | |
| none | BOTH `POOL_READ_TIME` | `wlm.pool_read_time` | monotonic_count | millisecond | svc/wl + member | Bufferpool physical read wait. |
| none | BOTH `POOL_WRITE_TIME` | `wlm.pool_write_time` | monotonic_count | millisecond | svc/wl + member | |
| none | BOTH `DIRECT_READ_TIME` | `wlm.direct_read_time` | monotonic_count | millisecond | svc/wl + member | |
| none | BOTH `DIRECT_WRITE_TIME` | `wlm.direct_write_time` | monotonic_count | millisecond | svc/wl + member | |
| none | BOTH `LOG_DISK_WAIT_TIME` | `wlm.log_disk_wait_time` | monotonic_count | millisecond | svc/wl + member | orientation -1. |
| none | BOTH `LOG_BUFFER_WAIT_TIME` | `wlm.log_buffer_wait_time` | monotonic_count | millisecond | svc/wl + member | |
| none | BOTH `AGENT_WAIT_TIME` | `wlm.agent_wait_time` | monotonic_count | millisecond | svc/wl + member | Wait for an agent (pool pressure). orientation -1. |
| none | BOTH `AGENT_WAITS_TOTAL` | `wlm.agent_waits` | monotonic_count | wait | svc/wl + member | |
| none | BOTH `CLIENT_IDLE_WAIT_TIME` | `wlm.client_idle_wait_time` | monotonic_count | millisecond | svc/wl + member | Time blocked on client (think time). |
| none | BOTH `PREFETCH_WAIT_TIME` | `wlm.prefetch_wait_time` | monotonic_count | millisecond | svc/wl + member | |
| none | BOTH `TOTAL_EXTENDED_LATCH_WAIT_TIME` | `wlm.extended_latch_wait_time` | monotonic_count | millisecond | svc/wl + member | Latch contention. orientation -1. |
| none | BOTH `TOTAL_EXTENDED_LATCH_WAITS` | `wlm.extended_latch_waits` | monotonic_count | wait | svc/wl + member | |
| none | BOTH `FCM_RECV_WAIT_TIME` / `FCM_SEND_WAIT_TIME` | `wlm.fcm_recv_wait_time` / `wlm.fcm_send_wait_time` | monotonic_count | millisecond | svc/wl + member | MPP/pureScale only (FCM). |
| none | BOTH `TCPIP_RECV_WAIT_TIME` / `TCPIP_SEND_WAIT_TIME` | `wlm.tcpip_recv_wait_time` / `wlm.tcpip_send_wait_time` | monotonic_count | millisecond | svc/wl + member | |
| none | BOTH `IPC_RECV_WAIT_TIME` / `IPC_SEND_WAIT_TIME` | `wlm.ipc_recv_wait_time` / `wlm.ipc_send_wait_time` | monotonic_count | millisecond | svc/wl + member | Local (shared-memory) client comms. |
| none | BOTH `CF_WAIT_TIME` / `CF_WAITS` | `wlm.cf_wait_time` / `wlm.cf_waits` | monotonic_count | millisecond / wait | svc/wl + member | **pureScale only** — gate on CF presence (0 elsewhere). |
| none | BOTH `RECLAIM_WAIT_TIME` | `wlm.reclaim_wait_time` | monotonic_count | millisecond | svc/wl + member | pureScale page reclaim. |

### Tier 2 — statement mix, sort/hash, locks, rows (good fidelity, default-on)

| pg/mysql analog | Db2 source: fn + column | Proposed `ibm_db2.<name>` | Type | Unit | Tags | Notes |
|---|---|---|---|---|---|---|
| mysql com_select (server-wide) | BOTH `SELECT_SQL_STMTS` | `wlm.statements.select` | monotonic_count | query | svc/wl + member | Per-class statement mix (vs mysql's server-wide com_*). |
| mysql com_insert/update/delete | BOTH `UID_SQL_STMTS` | `wlm.statements.uid` | monotonic_count | query | svc/wl + member | Update+Insert+Delete combined (Db2 groups them). |
| none | BOTH `DDL_SQL_STMTS` | `wlm.statements.ddl` | monotonic_count | query | svc/wl + member | |
| none | BOTH `MERGE_SQL_STMTS` | `wlm.statements.merge` | monotonic_count | query | svc/wl + member | |
| none | BOTH `CALL_SQL_STMTS` | `wlm.statements.call` | monotonic_count | query | svc/wl + member | |
| none | BOTH `DYNAMIC_SQL_STMTS` | `wlm.statements.dynamic` | monotonic_count | query | svc/wl + member | |
| none | BOTH `STATIC_SQL_STMTS` | `wlm.statements.static` | monotonic_count | query | svc/wl + member | |
| mysql slow/aborted (loose) | BOTH `FAILED_SQL_STMTS` | `wlm.statements.failed` | monotonic_count | query | svc/wl + member | orientation -1. |
| pg rows_returned | BOTH `ROWS_RETURNED` | `wlm.rows_returned` | monotonic_count | row | svc/wl + member | Per-class analog of existing `ibm_db2.row.returned.total`. |
| pg rows_fetched / mysql rows_examined | BOTH `ROWS_READ` | `wlm.rows_read` | monotonic_count | row | svc/wl + member | Per-class analog of `ibm_db2.row.reads.total`. |
| pg rows_inserted/updated/deleted | BOTH `ROWS_MODIFIED` | `wlm.rows_modified` | monotonic_count | row | svc/wl + member | Per-class analog of `ibm_db2.row.modified.total`. |
| (detail) | BOTH `ROWS_INSERTED` / `ROWS_UPDATED` / `ROWS_DELETED` | `wlm.rows_inserted` / `wlm.rows_updated` / `wlm.rows_deleted` | monotonic_count | row | svc/wl + member | Optional breakout. |
| mysql sort_* (DBM, loose) | BOTH `TOTAL_SORTS` | `wlm.sorts.total` | monotonic_count | sort | svc/wl + member | |
| mysql created_tmp_disk_tables (loose) | BOTH `SORT_OVERFLOWS` | `wlm.sorts.overflows` | monotonic_count | sort | svc/wl + member | Spilled sorts. orientation -1. |
| none | BOTH `POST_THRESHOLD_SORTS` | `wlm.sorts.post_threshold` | monotonic_count | sort | svc/wl + member | Sorts past sortheap threshold. |
| none | BOTH `POST_SHRTHRESHOLD_SORTS` | `wlm.sorts.post_shrthreshold` | monotonic_count | sort | svc/wl + member | |
| none | BOTH `TOTAL_HASH_JOINS` | `wlm.hash_joins.total` | monotonic_count | operation | svc/wl + member | |
| none | BOTH `HASH_JOIN_OVERFLOWS` | `wlm.hash_joins.overflows` | monotonic_count | operation | svc/wl + member | orientation -1. |
| none | BOTH `TOTAL_HASH_GRPBYS` | `wlm.hash_grpbys.total` | monotonic_count | operation | svc/wl + member | |
| none | BOTH `HASH_GRPBY_OVERFLOWS` | `wlm.hash_grpbys.overflows` | monotonic_count | operation | svc/wl + member | orientation -1. |
| none | BOTH `TOTAL_OLAP_FUNCS` | `wlm.olap_funcs.total` | monotonic_count | operation | svc/wl + member | |
| none | BOTH `OLAP_FUNC_OVERFLOWS` | `wlm.olap_funcs.overflows` | monotonic_count | operation | svc/wl + member | orientation -1. |
| none | BOTH `ACTIVE_SORTS` | `wlm.active_sorts` | gauge | sort | svc/wl + member | Point-in-time. |
| none | BOTH `ACTIVE_HASH_JOINS` | `wlm.active_hash_joins` | gauge | operation | svc/wl + member | Point-in-time. |
| none | BOTH `ACTIVE_OLAP_FUNCS` | `wlm.active_olap_funcs` | gauge | operation | svc/wl + member | Point-in-time. |
| none | BOTH `SORT_HEAP_ALLOCATED` | `wlm.sort_heap_allocated` | gauge | page | svc/wl + member | |
| none | BOTH `SORT_SHRHEAP_ALLOCATED` | `wlm.sort_shrheap_allocated` | gauge | page | svc/wl + member | |
| pg deadlocks / mysql innodb.deadlocks | BOTH `DEADLOCKS` | `wlm.deadlocks` | monotonic_count | lock | svc/wl + member | Per-class analog of `ibm_db2.lock.dead`. orientation -1. |
| pg/mysql lock timeouts (loose) | BOTH `LOCK_TIMEOUTS` | `wlm.lock_timeouts` | monotonic_count | lock | svc/wl + member | orientation -1. |
| none | BOTH `LOCK_ESCALS` | `wlm.lock_escalations` | monotonic_count | lock | svc/wl + member | orientation -1. |
| none | BOTH `THRESH_VIOLATIONS` | `wlm.threshold_violations` | monotonic_count | violation | svc/wl + member | WLM threshold breaches. orientation -1. |
| none | BOTH `NUM_LW_THRESH_EXCEEDED` | `wlm.lock_wait_thresh_exceeded` | monotonic_count | violation | svc/wl + member | |
| none | BOTH `PKG_CACHE_INSERTS` / `PKG_CACHE_LOOKUPS` | `wlm.pkg_cache.inserts` / `wlm.pkg_cache.lookups` | monotonic_count | get | svc/wl + member | Package-cache hit-ratio source. |
| none | BOTH `CAT_CACHE_INSERTS` / `CAT_CACHE_LOOKUPS` | `wlm.cat_cache.inserts` / `wlm.cat_cache.lookups` | monotonic_count | get | svc/wl + member | Catalog-cache hit-ratio source. |

### Tier 2 — bufferpool / IO per WLM class (optional, mirrors existing bufferpool family)

These duplicate `ibm_db2.bufferpool.*` but attributed per WLM class. Recommend gating behind
the same flag as SUBCLASS collection to control volume.

| pg/mysql analog | Db2 source: fn + column | Proposed `ibm_db2.<name>` | Type | Unit | Tags | Notes |
|---|---|---|---|---|---|---|
| pg blks_hit (loose) | BOTH `POOL_DATA_L_READS` | `wlm.bufferpool.data.reads.logical` | monotonic_count | page | svc/wl + member | |
| pg blks_read (loose) | BOTH `POOL_DATA_P_READS` | `wlm.bufferpool.data.reads.physical` | monotonic_count | page | svc/wl + member | |
| none | BOTH `POOL_INDEX_L_READS` / `POOL_INDEX_P_READS` | `wlm.bufferpool.index.reads.logical` / `.physical` | monotonic_count | page | svc/wl + member | |
| none | BOTH `POOL_COL_L_READS` / `POOL_COL_P_READS` | `wlm.bufferpool.column.reads.logical` / `.physical` | monotonic_count | page | svc/wl + member | Column-organized (BLU). |
| none | BOTH `POOL_DATA_WRITES` / `POOL_INDEX_WRITES` | `wlm.bufferpool.data.writes` / `wlm.bufferpool.index.writes` | monotonic_count | page | svc/wl + member | |
| mysql innodb.data_reads (loose) | BOTH `DIRECT_READS` / `DIRECT_WRITES` | `wlm.direct_reads` / `wlm.direct_writes` | monotonic_count | page | svc/wl + member | Bypass-bufferpool I/O (LOBs etc.). |

### Tier 3 — WLM admission & parallelism (SUBCLASS-ONLY — the 5 columns WORKLOAD omits)

These exist **only** in `MON_GET_SERVICE_SUBCLASS` (per catalog §5: WORKLOAD has 371 cols
vs SUBCLASS's 376, omitting these). They are the strongest reason to also collect SUBCLASS.

| pg/mysql analog | Db2 source: fn + column | Proposed `ibm_db2.<name>` | Type | Unit | Tags | Notes |
|---|---|---|---|---|---|---|
| none | SUBCLASS-only `AGENT_LOAD_TRGT_UTILIZATION` | `wlm.agent_load_target_utilization` | gauge | percent | svc + member | DOUBLE. WLM agent-load-target utilization. |
| none | SUBCLASS-only `AGENT_LOAD_TRGT_DEMAND` | `wlm.agent_load_target_demand` | gauge | percent | svc + member | DOUBLE. |
| none | SUBCLASS-only `SORT_SHRHEAP_UTILIZATION` | `wlm.sort_shrheap_utilization` | gauge | percent | svc + member | DOUBLE. Shared sort heap pressure. |
| none | SUBCLASS-only `SORT_SHRHEAP_DEMAND` | `wlm.sort_shrheap_demand` | gauge | percent | svc + member | DOUBLE. |
| none | BOTH `EFF_PARALLELISM` | `wlm.effective_parallelism` | gauge | thread | svc/wl + member | Effective intra-query parallelism. |
| none | BOTH `ACTUAL_PARALLELISM` | `wlm.actual_parallelism` | gauge | thread | svc/wl + member | |
| none | BOTH `ADM_OVERFLOWS` | `wlm.admission_overflows` | monotonic_count | overflow | svc/wl + member | WLM admission-control overflow. orientation -1. |
| none | BOTH `ADM_BYPASS_ACT_TOTAL` | `wlm.admission_bypassed` | monotonic_count | activity | svc/wl + member | Activities that bypassed admission. |
| none | BOTH `LOW_PRIORITY_ACT_TOTAL` | `wlm.activities.low_priority` | monotonic_count | activity | svc/wl + member | CPU-priority distribution. |
| none | BOTH `MEDIUM_PRIORITY_ACT_TOTAL` | `wlm.activities.medium_priority` | monotonic_count | activity | svc/wl + member | |
| none | BOTH `HIGH_PRIORITY_ACT_TOTAL` | `wlm.activities.high_priority` | monotonic_count | activity | svc/wl + member | |
| none | BOTH `CRITICAL_PRIORITY_ACT_TOTAL` | `wlm.activities.critical_priority` | monotonic_count | activity | svc/wl + member | |

### Tier 3 — utility / routine / compile time (lower priority, optional)

| pg/mysql analog | Db2 source: fn + column | Proposed `ibm_db2.<name>` | Type | Unit | Tags | Notes |
|---|---|---|---|---|---|---|
| none | BOTH `TOTAL_ROUTINE_TIME` | `wlm.routine_time` | monotonic_count | millisecond | svc/wl + member | Stored-proc/UDF time. |
| none | BOTH `TOTAL_ROUTINE_INVOCATIONS` | `wlm.routine_invocations` | monotonic_count | invocation | svc/wl + member | |
| none | BOTH `TOTAL_ROUTINE_USER_CODE_TIME` | `wlm.routine_user_code_time` | monotonic_count | millisecond | svc/wl + member | |
| none | BOTH `TOTAL_COMPILE_TIME` | `wlm.compile_time` | monotonic_count | millisecond | svc/wl + member | Explicit compile/prepare time. |
| none | BOTH `TOTAL_COMPILATIONS` | `wlm.compilations` | monotonic_count | compilation | svc/wl + member | |
| none | BOTH `TOTAL_IMPLICIT_COMPILE_TIME` | `wlm.implicit_compile_time` | monotonic_count | millisecond | svc/wl + member | Implicit recompiles. |
| none | BOTH `TOTAL_COMMIT_TIME` | `wlm.commit_time` | monotonic_count | millisecond | svc/wl + member | |
| none | BOTH `TOTAL_ROLLBACK_TIME` | `wlm.rollback_time` | monotonic_count | millisecond | svc/wl + member | |
| none | BOTH `TOTAL_RUNSTATS` / `TOTAL_RUNSTATS_TIME` | `wlm.runstats` / `wlm.runstats_time` | monotonic_count | operation / millisecond | svc/wl + member | Maintenance class signal. |
| none | BOTH `TOTAL_REORGS` / `TOTAL_REORG_TIME` | `wlm.reorgs` / `wlm.reorg_time` | monotonic_count | operation / millisecond | svc/wl + member | |
| none | BOTH `TOTAL_LOADS` / `TOTAL_LOAD_TIME` | `wlm.loads` / `wlm.load_time` | monotonic_count | operation / millisecond | svc/wl + member | |
| none | BOTH `TOTAL_BACKUPS` / `TOTAL_BACKUP_TIME` | `wlm.backups` / `wlm.backup_time` | monotonic_count | operation / millisecond | svc/wl + member | |
| none | BOTH `TOTAL_DISP_RUN_QUEUE_TIME` | `wlm.dispatcher_run_queue_time` | monotonic_count | millisecond | svc/wl + member | CPU-dispatcher queueing (WLM CPU shares). orientation -1. |

### Skip / low-value here (covered better elsewhere or niche)

- Full caching-tier matrix (`POOL_*_CACHING_TIER_*`, ~40 cols) — NVMe-tier-specific; skip
  unless the deployment uses a caching tier.
- FCM/TQ message subfamilies (`FCM_MESSAGE_*`, `FCM_TQ_*`), `IDA_*`, external-table
  (`EXT_TABLE_*`) — MPP/federation/Netezza-specific; gate behind those features.
- TLS/connect timing (`TOTAL_TLS_*`, `TOTAL_CONNECT_*`) — better as a connection-category
  metric than per-WLM-class.
- AI model provider (`MODEL_PROVIDER_WAIT_TIME` / `_WAITS_TOTAL`) — 12.1 AI feature; niche.
- Audit/diaglog (`AUDIT_*`, `DIAGLOG_*`) — security/ops, not workload performance.
- pureScale-only GBP/LBP page columns (`POOL_*_GBP_*`, `POOL_*_LBP_*`) — emit only on
  pureScale.

---

## Implementation notes for the plan

1. **Two queries, one metric namespace.** Both functions use the new declarative
   `QueryExecutor` `columns` dict style (mirror `mysql/index_metrics.py`). `MON_GET_WORKLOAD`
   default-on; `MON_GET_SERVICE_SUBCLASS` behind `collect_wlm_service_class_metrics`
   (default off) to avoid double-counting and to pick up the 5 SUBCLASS-only admission
   gauges. Same `ibm_db2.wlm.*` names; distinguished by `service_*` vs `workload_*` tags.
2. **Signatures** (verify on the live box):
   `MON_GET_SERVICE_SUBCLASS(NULL, NULL, -2)`,
   `MON_GET_WORKLOAD(NULL, -2)` (`-2` = all members). Returns one row per
   class/workload × member.
3. **Always returns data** via `SYSDEFAULT*` — safe to query unconditionally; no WLM
   licensing/config prerequisite for the default-class rows.
4. **Graceful degradation:** wrap each query; on missing function / insufficient authority
   (SYSMON/DBADM) log and skip, per the postgres `UndefinedFunction` and mysql PROCESS-grant
   patterns.
5. **`TOTAL_CPU_TIME` unit:** ship as microseconds but verify against the live server before
   finalizing the metadata.csv `unit_name`.
6. **metadata.csv:** every emitted `ibm_db2.wlm.*` metric needs a row
   (`integration=ibm_db2`, correct `metric_type`/`unit_name`, orientation, description noting
   the enabling flag and `service_superclass`/`service_subclass`/`workload_name`/`member`
   tags). Current file has 49 metrics; this category adds ~70-90 rows depending on tier scope.
7. **member tag** only varies on MPP/pureScale; on a single-member instance it is constant
   (e.g. `member:0`) — still emit for consistency with other Db2 categories.
