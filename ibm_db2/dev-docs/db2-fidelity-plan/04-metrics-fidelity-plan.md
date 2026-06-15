# 04 — Metrics Fidelity Plan (standard-metric expansion to pg/mysql parity)

**What this is.** The comprehensive plan to expand the `ibm_db2` integration's **standard metric**
surface from today's **49 metrics** to postgres-grade (**244**) / mysql-grade (**254**) fidelity. It
consumes the 14 per-category mapping tables in `_research/map-*.md` and turns them into: (1) a
consolidated metric catalog organized by category; (2) the concrete `queries.py` query-definition
changes (one block per `MON_GET_*` function / `SYSIBMADM` view); (3) the `metadata.csv` additions and a
target metric count; (4) the new tag dimensions and per-object opt-in / cardinality controls; (5) the
keep/rename/deprecate decisions for the existing 49; and (6) collection-overhead guidance.

**Scope boundary.** This doc is **standard metrics only** — the `dbm-metrics` query-metrics payload
(`MON_GET_PKG_CACHE_STMT`, the `pg_stat_statements` analog) is owned by
[`05-dbm-query-metrics.md`](05-dbm-query-metrics.md); samples/activity/plans/metadata are owned by the
(not-yet-written) `06`–`09` and live in `_research/db2-live-{activity,pkgcache}.md`. Where a Db2
function carries per-statement columns of the same family (e.g. sort/hash on
`MON_GET_PKG_CACHE_STMT`), this doc notes the overlap and routes it to `05`.

**Audience.** An engineer (or implementing AI agent) who knows the Datadog `postgres` / `mysql`
integrations well — `pg_stat_database`, `SHOW GLOBAL STATUS`, `QueryExecutor`/`QueryManager`, per-relation
`relations` gating — but **little about Db2**. Db2-specific concepts are explained inline; uncertain
facts are flagged `(verify)`.

**Cross-references (sibling docs).**
- [`01-db2-monitoring-primer.md`](01-db2-monitoring-primer.md) — the `MON_GET_*` table-function model,
  monitor switches, units convention, authority model. Read first if Db2 is unfamiliar.
- [`02-current-integration-audit.md`](02-current-integration-audit.md) — the shipped 49-metric baseline
  and the per-category gap vs pg(244)/mysql(254).
- [`03-reference-architecture.md`](03-reference-architecture.md) — the target check architecture
  (`DatabaseCheck`, `QueryExecutor`/`QueryManager`, per-job connection layer, base tags). This doc's
  query blocks assume that architecture.
- [`05-dbm-query-metrics.md`](05-dbm-query-metrics.md) — per-statement metrics (the `pg_stat_statements`
  analog); the sort/hash/IO **per-query** families live there, not here.
- [`10-implementation-phases.md`](10-implementation-phases.md) — sequencing; this doc's work is
  **Phase P0** (metric breadth on the existing synchronous pattern) plus the metric portions of later
  phases (per-table/index in P-tail).
- [`11-testing-and-validation.md`](11-testing-and-validation.md) — how to assert these metrics
  (`tests/metrics.py` `STANDARD` list, `assert_all_metrics_covered`) and the 12.1.4 CI container.
- Risks/open questions: doc `12` is **not yet written**; the `00-README.md` "Key risks" section is the
  stand-in (esp. risk #3: every `[DOC]`-flagged column below must be live-`DESCRIBE`'d on 12.1.4 before
  shipping — this is a **gating P0 prerequisite**, not a footnote).

---

## 0. Executive summary

### 0.1 The decision: how far to push standard-metric breadth

The 14 maps surface **~430 candidate `ibm_db2.*` metric names** across 14 categories. Shipping all of
them is neither necessary for "pg/mysql fidelity" nor wise (cardinality, overhead, catalog bloat).
The plan tiers them:

| Tier | What | Approx. new metrics | Default | Gating |
|---|---|---|---|---|
| **T0 — core breadth** | Columns that ride functions the check **already calls** (`MON_GET_DATABASE`, `MON_GET_BUFFERPOOL`, `MON_GET_TABLESPACE`, `MON_GET_TRANSACTION_LOG`, `MON_GET_INSTANCE`): commits/rollbacks, rows I/U/D, bufferpool writes/async/timing, direct I/O, log timing/buffer, lock counters+escalations, tablespace free/HWM/max, agent pool, uptime. | **~150** | **on** | none (12.1 columns always present) |
| **T1 — new low-cardinality functions** | New always-safe `MON_GET_*` calls: sort/hash (`MON_GET_DATABASE`), memory pools (`MON_GET_MEMORY_POOL`/`_SET`), WLM workload (`MON_GET_WORKLOAD`), HADR (`MON_GET_HADR`). Low/bounded cardinality. | **~120** (of which WLM ~70 is mostly tag-fan-out on a handful of names) | **on** (HADR/WLM emit only when configured) | data-gated (0-row → skip) |
| **T2 — per-object fan-out** | High-cardinality per-`(schema,table)` / per-`(schema,table,index)` / per-container / per-connection / per-WLM-service-subclass. | **~60** metric names (× object count series) | **off** | config flag + top-N cap + schema filter |
| **T3 — clustered-only** | pureScale / DPF: FCM, CF, GBP-structure, `*_global` lock counters. | **~50** | **off** | pureScale/DPF probe + config flag |

**Recommended target:** ship **T0 + T1** as the parity baseline (≈ **270 new metrics** → **~320 total**,
which **exceeds** pg's 244 and mysql's 254 in count and matches/exceeds them in coverage of every
shared concept). Ship **T2/T3 behind config flags** for sites that want per-object / clustered depth.
The count target is a means, not the end — §1's per-category tables mark each metric's tier so the
implementer can land T0 first (Phase P0) and add T1/T2/T3 incrementally.

### 0.2 The five load-bearing rules (apply to every new metric)

1. **Type discipline** (matches the existing check and every analog integration): a lifetime,
   monotonically-increasing `MON_GET` BIGINT counter → submit `monotonic_count` → declare `count` in
   `metadata.csv`. A point-in-time value / high-water (`*_TOP`, `*_HWM`) / computed ratio → `gauge`.
   **Never** submit `rate` from the agent for these — keep them counters so the backend/dashboards
   choose (postgres convention; `code-postgres-metrics.md`). Db2 has essentially no native rate column.
2. **Units convention** (Db2 monitor-element knowledge, `01-db2-monitoring-primer.md`; `(verify)` per
   element): `*_TIME` = **milliseconds** (one exception: `TOTAL_CPU_TIME` and the CF `*_MICRO`
   columns are **microseconds** `(verify)`); `*_VOLUME` = **bytes**; `POOL_*`/`*_PAGES`/`NLEAF` =
   **pages**; memory pools/sets = **bytes** `(verify byte-vs-KiB once live)`. Existing bufferpool reads
   use `unit_name=get` (a Db2-ism for "logical reads == buffer-pool gets") — **reuse `get`** for new
   bufferpool read-family metrics for consistency.
3. **Tagging** (mirror pg/mysql `add_core_tags`): every metric carries base tags `db:<db>` (already
   auto-added, `ibm_db2.py:48`), the new `database_hostname` / `database_instance` (added by the
   `DatabaseCheck` migration, `03`), and `member` on every `MON_GET_*`-sourced metric (the function's
   member arg; `-1`=current, `-2`=all). On a single-member box `member` is constant (`member:0`) — emit
   anyway for forward-compat. Per-object tags (`bufferpool`, `tablespace`, `schema`, `table`, …) are
   added per §4.
4. **Graceful degradation** (mirror pg `_run_query_scope` / mysql warn-and-return): wrap **each** query
   so a missing `MON_GET_*` function, NULL column on a restricted edition, or insufficient authority
   logs a WARNING and skips that collector — never aborts the run. The existing orchestrator already
   swallows per-method exceptions (`ibm_db2.py:82-91`); preserve that for every new query.
5. **One metadata.csv row per emitted metric** (`integration=ibm_db2`; format in §3.1), with the right
   `metric_type`/`unit_name`/`orientation` and a description naming the source column and any gating
   config flag. Every metric the check can emit MUST have a row or `ddev validate metadata` fails.

### 0.3 Highest-value adds (if you ship nothing else)

Ranked by signal-per-effort, all T0 (ride an already-called function):
1. **Transaction throughput** — `transaction.commits` / `.rollbacks` (+ internal) from
   `MON_GET_DATABASE` (`map-rows-throughput.md`). The single biggest, clearest gap vs both pg and mysql.
2. **Rows I/U/D split** — `row.inserted/updated/deleted.total` (`map-rows-throughput.md`).
3. **Bufferpool writes + I/O timing** — `bufferpool.{data,index,xda,column}.writes`,
   `bufferpool.read_time/write_time` (`map-bufferpool.md`, `map-io-disk.md`). Closes the glaring
   "we report reads but not writes" asymmetry; Db2 always populates I/O timing (a fidelity win over pg's
   `track_io_timing`-gated zeros).
4. **Log commit-latency** — `log.disk_wait_time`, `log.buffer_full`, `log.to_redo_for_recovery`
   (`map-transaction-logs.md`, `map-io-disk.md`).
5. **Lock raw counters + escalations** — `lock.waits`, `lock.wait_time`, `lock.escalations`
   (`map-locking-concurrency.md`) — and **fix** the lossy in-check `lock.wait` average (§5.2).
6. **Uptime + agent pool** — `uptime`, `agent.*` from `MON_GET_INSTANCE`
   (`map-instance-database-summary.md`, `map-connections-applications.md`).

---

## 1. Consolidated metric catalog (by category)

Conventions for the tables below:
- **Tier** = T0/T1/T2/T3 per §0.1.
- **Type** = Datadog submit fn → metadata.csv `metric_type`: `count` (= `monotonic_count`), `gauge`,
  (no `rate`).
- **Source** = `MON_GET_*` function (or `SYSIBMADM` view) **+ exact column**. `[DOC]` = column from IBM
  docs / general knowledge, **not** confirmed in the live 12.1.4 DESCRIBE dump — **must be
  live-`DESCRIBE`'d before shipping** (`00-README.md` risk #3). `[LIVE]` = confirmed present.
- **Tags** beyond the base set (`db`, `database_hostname`, `database_instance`, `member`).
- **Existing** metrics are marked `(EXISTS)`; §5 covers keep/rename/deprecate.

Per-category detail (including pg/mysql-only gaps and Db2-native extras) lives in each
`_research/map-<category>.md`; this section is the consolidated, tiered, ship-list view.

### 1.1 Instance / database summary — `MON_GET_INSTANCE`, `MON_GET_DATABASE`, `SYSIBMADM.ENV_*`
(`map-instance-database-summary.md`)

| Tier | Proposed `ibm_db2.*` | Type | Unit | Source column | Tags | Notes |
|---|---|---|---|---|---|---|
| T0 | `uptime` | gauge | second | `MON_GET_INSTANCE.DB2START_TIME` [LIVE] vs `CURRENT TIMESTAMP` | — | pg `uptime` analog. Compute in Python like `backup.latest`. **Top add.** |
| T0 | `running` | gauge | — | derived: 1 on successful instance probe | — | pg `running` analog. Emit 1 only on success. |
| T0 | `instance.status` | gauge | — | `MON_GET_INSTANCE.DB2_STATUS` [LIVE] → int | `db2_status:<v>` | instance liveness (0=ACTIVE…). |
| T0 | `database.status` | gauge | — | `MON_GET_DATABASE.DB_STATUS` [LIVE] → int | `db_status:<v>`,`db_activation_state:<v>` | numeric companion to existing `ibm_db2.status` SC. |
| T0 | `databases.active` | gauge | item | `MON_GET_INSTANCE.CON_LOCAL_DBASES` [LIVE] | — | partial `postgresql.db.count` analog. |
| T0 | `database.uptime` | gauge | second | `MON_GET_DATABASE.DB_CONN_TIME` [LIVE] vs now | — | activation uptime; optional. |
| T0 | `backup.latest` `(EXISTS)` | gauge | second | `MON_GET_DATABASE.LAST_BACKUP` | — | keep. |
| T0 | `agent.registered` / `.registered.max` | gauge | agent | `MON_GET_INSTANCE.AGENTS_REGISTERED` / `_TOP` [LIVE] | — | agent-pool saturation. |
| T0 | `agent.idle` | gauge | agent | `MON_GET_INSTANCE.IDLE_AGENTS` [LIVE] | — | ≈ mysql `threads_cached`. |
| T0 | `agent.coord` / `.coord.max` | gauge | agent | `NUM_COORD_AGENTS` / `COORD_AGENTS_TOP` [LIVE] | — | ≈ mysql `threads_running`. |
| T0 | `agent.from_pool` | count | agent | `MON_GET_INSTANCE.AGENTS_FROM_POOL` [LIVE] | — | pool-reuse. |
| T0 | `agent.created_empty_pool` | count | agent | `AGENTS_CREATED_EMPTY_POOL` [LIVE] | — | **highest-signal agent metric** (≈ mysql `threads_created`). orient -1. |
| T0 | `agent.stolen` | count | agent | `AGENTS_STOLEN` [LIVE] | — | optional. |
| T1 | `gateway.connection.{total,active,waiting_host,waiting_client,switches}` | count/gauge | connection | `GW_*` [LIVE] | — | DRDA gateway; emit only when `GW_TOTAL_CONS>0` or config flag. |
| T1 | `summary.bufferpool.hit_percent`, `summary.rows_read_per_returned`, `summary.pkg_cache.hit_percent`, `summary.cat_cache.hit_percent`, `summary.sort_overflow_percent` | gauge | percent/row | `SYSIBMADM.MON_DB_SUMMARY` `(verify cols)` OR computed from `MON_GET_DATABASE` | — | prefer computing from `MON_GET_DATABASE` cols already fetched (no extra round-trip). |

**Identity → tags/metadata, NOT metrics** (`map-instance-database-summary.md` §1C): surface
`db2_version` (`MON_GET_INSTANCE.SERVICE_LEVEL` [LIVE] / `ENV_INST_INFO.SERVICE_LEVEL`), `db2_edition`
(`ENV_PROD_INFO.INSTALLED_PROD`), `db2_license` (`LICENSE_TYPE`), optional `db2_product`/`db2_platform`
as **low-cardinality instance tags** + `set_metadata('version', …)` (mirror pg `postgresql_version:`).
Never emit version/edition as a metric value. Use `SYSIBM.SYSVERSIONS.VERSIONNUMBER` (packed `12010400`)
for internal capability gating only.

### 1.2 Connections / applications / agents — `MON_GET_DATABASE`, `MON_GET_INSTANCE`, `MON_GET_CONNECTION`
(`map-connections-applications.md`)

| Tier | Proposed `ibm_db2.*` | Type | Unit | Source column | Tags | Notes |
|---|---|---|---|---|---|---|
| T0 | `connection.active` `(EXISTS)` | gauge | connection | `MON_GET_INSTANCE.TOTAL_CONNECTIONS` | — | keep; document it is **instance-wide** (all DBs). |
| T0 | `application.active` `(EXISTS)` | gauge | connection | `MON_GET_DATABASE.APPLS_CUR_CONS` | — | truest "connections to THIS db". keep. |
| T0 | `application.executing` `(EXISTS)` | gauge | connection | `APPLS_IN_DB2` | — | keep. |
| T0 | `connection.max` `(EXISTS)` | gauge | connection | `CONNECTIONS_TOP` | — | keep. |
| T0 | `connection.total` `(EXISTS)` | count | connection | `TOTAL_CONS` | — | keep. |
| T0 | `connection.secondary.total` | count | connection | `MON_GET_DATABASE.TOTAL_SEC_CONS` [LIVE] | — | MPP/pureScale subagent conns; ~0 single-member. |
| T0 | `agent.associated` / `.associated.max` | gauge | agent | `MON_GET_DATABASE.NUM_ASSOC_AGENTS` / `AGENTS_TOP` [LIVE] | — | per-DB. |
| T0 | `agent.pooled` | gauge | agent | `MON_GET_DATABASE.NUM_POOLED_AGENTS` [DOC] | — | per-DB pooled agents. |
| T1 | `connection.max_configured` | gauge | connection | `SYSIBMADM.DBCFG` `max_connections`/`maxappls` `(verify)` | — | enables `connection.percent_used`. cache per run. |
| T1 | `connection.percent_used` / `.percent_used_peak` | gauge | fraction | derived (`APPLS_CUR_CONS`/cfg) | — | pg `percent_usage_connections` analog. |
| T1 | `instance.local_databases` | gauge | database | `MON_GET_INSTANCE.CON_LOCAL_DBASES` [LIVE] | — | (dedupe with `databases.active` §1.1 — pick one name). |
| **T2** | `connection.count` | gauge | connection | `COUNT(*)` over `MON_GET_CONNECTION` GROUP BY identity | `session_auth_id`(user),`client_applname`(app),`client_hostname`,`workload_occurrence_state`(state) | **Tier-1 aggregate** (mysql `user_connections` / pg `connections_by_process` analog). Always-safe (bounded by identity-dim cardinality). |
| **T2** | `connection.{rows_read,rows_returned,rows_inserted,rows_updated,rows_deleted,commits,rollbacks,...}` + time decomposition (`total_rqst_time`,`total_cpu_time`,`lock_wait_time`,`pool_read_time`,`log_disk_wait_time`,`client_idle_wait_time`,`tcpip_{send,recv}_volume`,...) | count | row/ms/byte | `MON_GET_CONNECTION.*` [LIVE, L1030-1448] | identity tags + `application_handle` | **Tier-2 per-connection top-N** (`FETCH FIRST n`). Gate `collect_connection_metrics`. High churn (handle reuse); `monotonic_count` handles resets. Overlaps DBM activity — consider deferring to `06`. |

> Note (`map-connections-applications.md` §A): `connection.active` (instance-wide
> `MON_GET_INSTANCE.TOTAL_CONNECTIONS`) and `application.active` (this-DB `APPLS_CUR_CONS`) diverge on a
> multi-DB instance — document the distinction; do not rename (back-compat).

### 1.3 Rows / throughput — `MON_GET_DATABASE` (`map-rows-throughput.md`)

All ride the **already-called** `MON_GET_DATABASE(-1)` — add columns to one existing SELECT, no new
round-trip. Every column confirmed [LIVE] on 12.1.4.

| Tier | Proposed `ibm_db2.*` | Type | Unit | Source column | Notes |
|---|---|---|---|---|---|
| T0 | `transaction.commits` | count | transaction | `TOTAL_APP_COMMITS` | pg `xact_commit` / mysql `Com_commit`. **P0 must-have.** orient 0. |
| T0 | `transaction.rollbacks` | count | transaction | `TOTAL_APP_ROLLBACKS` | pg `xact_rollback`. orient -1. |
| T0 | `transaction.commits.internal` | count | transaction | `INT_COMMITS` | Db2-native. |
| T0 | `transaction.rollbacks.internal` | count | transaction | `INT_ROLLBACKS` | instability signal. orient -1. |
| T0 | `row.modified.total` `(EXISTS)` | count | row | `ROWS_MODIFIED` | keep. |
| T0 | `row.reads.total` `(EXISTS)` | count | row | `ROWS_READ` | keep (true pg `tup_returned`/`rows_fetched` analog — see semantic note). |
| T0 | `row.returned.total` `(EXISTS)` | count | row | `ROWS_RETURNED` | keep. |
| T0 | `row.inserted.total` | count | row | `ROWS_INSERTED` | pg `tup_inserted` / mysql `rows_inserted`. **P0 must-have.** |
| T0 | `row.updated.total` | count | row | `ROWS_UPDATED` | |
| T0 | `row.deleted.total` | count | row | `ROWS_DELETED` | |
| T1 | `row.{inserted,updated,deleted}.internal` | count | row | `INT_ROWS_*` | cascading RI / MQT / triggers. optional. |
| T0 | `activity.completed` | count | operation | `ACT_COMPLETED_TOTAL` | primary "work done" counter. |
| T0 | `activity.aborted` / `.rejected` | count | operation | `ACT_ABORTED_TOTAL` / `ACT_REJECTED_TOTAL` | orient -1. |
| T0 | `request.completed` | count | request | `RQSTS_COMPLETED_TOTAL` | |
| T0 | `section.executions` | count | operation | `TOTAL_APP_SECTION_EXECUTIONS` | ≈ pg `calls`-style throughput. |
| T1 | `sql.{select,uid,ddl,dynamic,static,failed,merge,call}_statements` | count | statement | `SELECT_SQL_STMTS`,`UID_SQL_STMTS`,`DDL_SQL_STMTS`,`DYNAMIC_SQL_STMTS`,`STATIC_SQL_STMTS`,`FAILED_SQL_STMTS`,`MERGE_SQL_STMTS`,`CALL_SQL_STMTS` | SQL statement mix (≈ mysql `Com_*`). Gate `collect_statement_mix_metrics` (default off) or ship a subset. `failed` orient -1. |

> **Semantic note to carry into dashboards** (`map-rows-throughput.md` §7): map
> `postgresql.rows_returned` → `ibm_db2.row.reads.total` (both are "rows read by scans"), and treat
> `ibm_db2.row.returned.total` (rows delivered to client) as a more-useful Db2-native metric with no
> exact pg twin.

### 1.4 Buffer pool — `MON_GET_BUFFERPOOL` (`map-bufferpool.md`)

Rides the **already-called** `MON_GET_BUFFERPOOL(NULL,-1)` (one row per pool). Tag `bufferpool:<bp_name>`
already applied. The existing 25 read/hit metrics are kept (§5). `<x>` ∈ {data, index, xda, column}.

| Tier | Proposed `ibm_db2.*` | Type | Unit | Source column | Notes |
|---|---|---|---|---|---|
| T0 | `bufferpool.<x>.writes` | count | page | `POOL_DATA_WRITES`,`POOL_INDEX_WRITES`,`POOL_XDA_WRITES`,`POOL_COL_WRITES` ([LIVE] except `POOL_COL_WRITES` [DOC]) | pages flushed to disk. **closes reads-but-no-writes gap.** |
| T0 | `bufferpool.writes.total` | count | page | Σ of the 4 above | mirrors existing `reads.total` aggregate. |
| T0 | `bufferpool.read_time` / `.write_time` | count | millisecond | `POOL_READ_TIME` / `POOL_WRITE_TIME` [LIVE] | pg `io.*_time` analog; always populated (fidelity win). |
| T0 | `bufferpool.<x>.reads.async` | count | page/get | `POOL_ASYNC_{DATA,INDEX,XDA,COL}_READS` [DOC] | prefetcher reads (mysql `read_ahead` analog). |
| T1 | `bufferpool.<x>.writes.async` | count | page | `POOL_ASYNC_{...}_WRITES` [DOC] | page-cleaner writes (pg `bgwriter.buffers_clean`). |
| T0 | `bufferpool.unread_prefetch_pages` | count | page | `UNREAD_PREFETCH_PAGES` [DOC] | wasted prefetch (mysql `read_ahead_evicted`). orient -1. |
| T0 | `bufferpool.no_victim_buffer` | count | operation | `POOL_NO_VICTIM_BUFFER` [DOC] | cleaner pressure (mysql `buffer_pool_wait_free`). orient -1. |
| T1 | `bufferpool.prefetch_wait_time` / `.prefetch_waits` | count | ms/wait | `PREFETCH_WAIT_TIME` [LIVE] / `PREFETCH_WAITS` [LIVE] | `NUM_IOSERVERS` tuning. orient -1. |
| T1 | `bufferpool.{vectored_ios,pages_from_vectored_ios,block_ios,pages_from_block_ios}` | count | operation/page | `VECTORED_IOS`,`PAGES_FROM_VECTORED_IOS`,`BLOCK_IOS`,`PAGES_FROM_BLOCK_IOS` [DOC] | prefetch I/O shape. low priority. |
| T1 | `bufferpool.files_closed` | count | operation | `FILES_CLOSED` [DOC] | descriptor pressure. **NB triple-home** with tablespace + custom-query example — pick one source (§5.4). |
| T1 | `bufferpool.pages.configured` | gauge | page | `BP_CUR_BUFFSZ` [DOC] | mysql `buffer_pool_pages_total` analog. page-size varies per BP → emit pages, not bytes. |
| T1 | `bufferpool.pages.left_to_remove` / `bufferpool.tablespaces` | gauge | page/tablespace | `BP_PAGES_LEFT_TO_REMOVE`,`BP_TBSP_USE_COUNT` [DOC] | resize/assoc context. optional. |
| **T3** | `bufferpool.group.<x>.invalid_pages` | count | page | `POOL_{...}_GBP_INVALID_PAGES` [DOC] | pureScale GBP cross-invalidation. gate like existing `group.*`. |

> **Direct I/O** (`DIRECT_READS/WRITES/READ_REQS/WRITE_REQS/READ_TIME/WRITE_TIME`) rides
> `MON_GET_BUFFERPOOL`/`MON_GET_DATABASE`/`MON_GET_TABLESPACE` but is **non-buffered** I/O — owned by the
> io-disk category §1.6 below (emit at DB scope from `MON_GET_DATABASE`). Do not double-define.
> **Temp split** (`POOL_TEMP_*` separated from the existing folded reads) is an optional NEW set — add
> as *additional* series; do NOT change how existing `reads.*` fold regular+temp (§5.3).

### 1.5 I/O / disk — `MON_GET_DATABASE`, `MON_GET_TABLESPACE`, `MON_GET_CONTAINER` (`map-io-disk.md`)

Headline DB-wide numbers come from the already-called `MON_GET_DATABASE(-1)` (single row, authoritative,
cheap). Per-tablespace rides the already-called `MON_GET_TABLESPACE`. Per-container is a new gated query.

| Tier | Proposed `ibm_db2.*` | Type | Unit | Source (function.column) | Tags | Notes |
|---|---|---|---|---|---|---|
| T0 | `direct.reads` / `.writes` | count | sector | `MON_GET_DATABASE.DIRECT_READS` / `DIRECT_WRITES` [LIVE] | — | LOB/XML/utility disk I/O (mysql `data_reads`/`os_file_reads` analog). |
| T0 | `direct.read_reqs` / `.write_reqs` | count | request | `DIRECT_READ_REQS` / `DIRECT_WRITE_REQS` [LIVE] | — | reqs vs sectors → avg I/O size. |
| T0 | `direct.read_time` / `.write_time` | count | millisecond | `DIRECT_READ_TIME` / `DIRECT_WRITE_TIME` [LIVE] | — | Db2-native; no pg analog. |
| **T2** | `tablespace.reads.physical` / `.writes.physical` | count | get/page | `MON_GET_TABLESPACE` Σ `POOL_*_P_READS` / `POOL_*_WRITES` | `tablespace` | per-TS disk I/O. low cardinality (#TS). gate `collect_tablespace_io_metrics` or fold into existing TS query. |
| **T2** | `tablespace.read_time` / `.write_time` / `tablespace.direct.*` | count | ms/sector | `MON_GET_TABLESPACE.POOL_READ_TIME`/`WRITE_TIME`/`DIRECT_*` | `tablespace` | per-TS. |
| **T2** | `container.fs_used` / `.fs_total` | gauge | byte | `MON_GET_CONTAINER.FS_USED_SIZE` / `FS_TOTAL_SIZE` [DOC] | `tablespace`,`container` | **disk-full early warning.** gate `collect_container_metrics`. cross-listed with §1.9 — own here. |
| **T2** | `container.{total,used,usable}` ; `container.reads.physical`/`.writes` | gauge/count | byte/get | `MON_GET_CONTAINER.*` [DOC] | `tablespace`,`container` | optional, gated. **live-DESCRIBE `MON_GET_CONTAINER` first (never probed).** |

(Buffer-pool reads/writes/timing already covered in §1.4; the io-disk map reconciles the existing
`bufferpool.*.reads.physical` as the pg `disk_read` analog — no new metric there.)

### 1.6 Transaction logs — `MON_GET_TRANSACTION_LOG` (`map-transaction-logs.md`)

Rides the already-called `MON_GET_TRANSACTION_LOG(-1)`; widen its 4-column SELECT. All 56 columns [LIVE].

| Tier | Proposed `ibm_db2.*` | Type | Unit | Source column | Notes |
|---|---|---|---|---|---|
| T0 | `log.used` / `.available` / `.utilized` `(EXISTS)` | gauge | block/percent | `TOTAL_LOG_USED`/`TOTAL_LOG_AVAILABLE` | keep (4 KiB blocks). **Fix infinite-log `-1`** (§5.5). |
| T0 | `log.reads` / `.writes` `(EXISTS)` | count | read/write | `LOG_READS`/`LOG_WRITES` | keep. |
| T0 | `log.space.used` / `.available` | gauge | byte | `TOTAL_LOG_USED`/`TOTAL_LOG_AVAILABLE` | **new byte-native** siblings (don't perpetuate the 4 KiB-block unit). |
| T0 | `log.space.used.max` / `log.secondary.used.max` | gauge | byte | `TOT_LOG_USED_TOP` / `SEC_LOG_USED_TOP` | capacity-planning HWMs. |
| T0 | `log.secondary.allocated` | gauge | file | `SEC_LOGS_ALLOCATED` | >0 = undersized `LOGPRIMARY`. |
| T0 | `log.disk_wait_time` / `log.disk_waits` | count | ms/wait | `LOG_DISK_WAIT_TIME` [LIVE] / `LOG_DISK_WAITS_TOTAL` [LIVE] | **commit-latency driver** (pg `wal.sync_time`). top add. orient -1. |
| T0 | `log.buffer_full` | count | event | `NUM_LOG_BUFFER_FULL` [LIVE] | mysql `log_waits` + pg `wal.buffers_full`. `LOGBUFSZ` tuning. orient -1. |
| T0 | `log.to_redo_for_recovery` | gauge | byte | `LOG_TO_REDO_FOR_RECOVERY` [LIVE] | crash-recovery RTO (mysql `checkpoint_age`). orient -1. |
| T1 | `log.write_time` / `.read_time` | count | millisecond | `LOG_WRITE_TIME` [DOC] / `LOG_READ_TIME` [LIVE] | avg log latency. |
| T1 | `log.write_io` / `.read_io` / `.partial_page_io` | count | operation | `NUM_LOG_WRITE_IO`/`NUM_LOG_READ_IO`/`NUM_LOG_PART_PAGE_IO` [DOC] | pages-per-IO efficiency. |
| T1 | `log.held_by_dirty_pages` | gauge | byte | `LOG_HELD_BY_DIRTY_PAGES` [LIVE] | page-cleaner/truncation health. |
| T1 | `log.cur_commit.reads.{total,disk,buffer}` | count | read | `CUR_COMMIT_*_LOG_READS` [LIVE] | currently-committed overhead. Db2-native. |
| T1 | `log.data_found_in_buffer` | count | hit | `NUM_LOG_DATA_FOUND_IN_BUFFER` [LIVE] | log-buffer hit ratio. |
| T1 | `log.files.reusable` | gauge | file | `NUM_LOGS_AVAIL_FOR_RENAME` [LIVE] | recycling headroom. |
| T1 | `log.indoubt_transactions` | gauge | transaction | `NUM_INDOUBT_TRANS` [LIVE] | 2PC operator-attention; SC candidate. |
| T1 | `log.archive.method{1,2}.status` / `.next_log` ; `log.archive.current_log` | gauge | — | `ARCHIVE_METHOD{1,2}_STATUS`,`METHOD{1,2}_NEXT_LOG_TO_ARCHIVE`,`CURRENT_ARCHIVE_LOG` [LIVE] | pg `archiver` analog; method tag. SC candidate. |
| T1 | LSN/position gauges `log.{lsn.current,lso.current,lsn.oldest_tx,active.{first,last,current},chain_id}` | gauge | — | `CURRENT_LSN`,`CURRENT_LSO`,`OLDEST_TX_LSN`,`FIRST/LAST/CURRENT_ACTIVE_LOG`,`LOG_CHAIN_ID` [LIVE] | dashboards/derived rates. low priority. |
| **T1-gated** | `log.extraction.*` (CDC) | count/gauge | byte/ms | `LOG_EXTRACTION_*` [LIVE] | only if log extraction in use; gate `collect_log_extraction_metrics`. |

> Cross-category: `LOG_HADR_WAIT_TIME`/`LOG_HADR_WAITS_TOTAL` live **only** in
> `MON_GET_TRANSACTION_LOG` but are HADR signals — collect here, name them under HADR
> (`hadr.log_wait.time`/`.count`, §1.12) to keep the namespace coherent.

### 1.7 Locking / concurrency — `MON_GET_DATABASE` (+ per-conn/table/workload, +live blocking)
(`map-locking-concurrency.md`)

Db2 is **richer than pg/mysql** here. DB-level rides the already-called `MON_GET_DATABASE(-1)`.

| Tier | Proposed `ibm_db2.*` | Type | Unit | Source column | Tags | Notes |
|---|---|---|---|---|---|---|
| T0 | `lock.dead` `(EXISTS)` | count | lock | `DEADLOCKS` | — | keep. |
| T0 | `lock.timeouts` `(EXISTS)` | count | lock | `LOCK_TIMEOUTS` | — | keep. |
| T0 | `lock.active` / `.waiting` `(EXISTS)` | gauge | lock | `NUM_LOCKS_HELD` / `NUM_LOCKS_WAITING` | — | keep. |
| T0 | `lock.wait` `(EXISTS)` | gauge | millisecond | `LOCK_WAIT_TIME/LOCK_WAITS` avg | — | keep for back-compat but **also add raw counters** ↓ (§5.2 fix). |
| T0 | `lock.pages` `(EXISTS)` | gauge | page | `LOCK_LIST_IN_USE/4096` | — | keep. |
| T0 | `lock.waits` | count | lock | `LOCK_WAITS` [LIVE] | — | **raw cumulative** (mysql `row_lock_waits`). orient -1. |
| T0 | `lock.wait_time` | count | millisecond | `LOCK_WAIT_TIME` [LIVE] | — | **raw cumulative** (mysql `lock_time`). orient -1. |
| T0 | `lock.escalations` | count | lock | `LOCK_ESCALS` [LIVE] | — | row→table promotion; Db2-native; LOCKLIST/MAXLOCKS pressure. orient -1. |
| T1 | `lock.escalations.{maxlocks,locklist}` | count | lock | `LOCK_ESCALS_MAXLOCKS`/`_LOCKLIST` [LIVE] | — | escalation cause. orient -1. |
| **T3** | `lock.{waits,wait_time,escalations,timeouts}.global` | count | lock/ms | `LOCK_*_GLOBAL` [LIVE] | — | pureScale CF lock; data-gate non-zero. |
| **T2** | `connection.{locks_held,locks_waiting,lock_wait_time,lock_waits,deadlocks,lock_timeouts,lock_escalations}` | gauge/count | lock/ms | `MON_GET_CONNECTION.*` [LIVE] | `application_name`,`session_auth_id`,`current_isolation` | gate `collect_connection_lock_metrics`; top-N by `LOCK_WAIT_TIME`. |
| **T2** | `table.{lock_waits,lock_wait_time,lock_escalations}` | count | lock/ms | `MON_GET_TABLE.*` [LIVE] | `schema`,`table` | gate `collect_table_lock_metrics`; finer than mysql `table_locks_waited`. |
| **T2** | `lock.count` | gauge | lock | `COUNT(*)` over `MON_GET_LOCKS(NULL,-1)` [function LIVE, cols DOC] | `lock_object_type`,`lock_mode`,`lock_status` | live blocking snapshot (pg `postgresql.locks` analog). live-DESCRIBE first. |
| **T2** | `lock.waits.current` / `lock.wait.max_age` | gauge | lock/second | `COUNT(*)`/`MAX(LOCK_WAIT_ELAPSED_TIME)` over `MON_GET_APPL_LOCKWAIT` [DOC] | — | current waiters + "stuck blocker" age (pg `idle_in_transaction_age`). |

> `MON_GET_LOCKS`/`MON_GET_APPL_LOCKWAIT` rich per-edge rows are the natural feed for a DBM
> **lock-wait/blocking sample event** — route detail to the activity workstream (`06`/`db2-live-activity`),
> keep only the count/age gauges here. Config-capacity denominators (`locklist`, `maxlocks`,
> `locktimeout`, `dlchktime` from `SYSIBMADM.DBCFG`) are optional T1 gauges.

### 1.8 Sorting / hashing — `MON_GET_DATABASE` (`map-sorting-hashing.md`)

**Entirely new category** (zero today). Rides the already-called `MON_GET_DATABASE(-1)`. New
`ibm_db2.sort.*` / `ibm_db2.hash.*` namespace. All counts confirmed [LIVE] (populated on the community
image). Counts → `count`; `ACTIVE_*`/`*_TOP`/heap → `gauge`.

| Tier | Proposed `ibm_db2.*` | Type | Unit | Source column | Notes |
|---|---|---|---|---|---|
| T1 | `sort.total` | count | sort | `TOTAL_SORTS` | core sort count. |
| T1 | `sort.overflows` | count | sort | `SORT_OVERFLOWS` | **key spill signal** (mysql `sort_merge_passes`/pg `temp_files`). orient -1. |
| T1 | `sort.post_threshold` / `.post_shrthreshold` | count | sort | `POST_THRESHOLD_SORTS` / `POST_SHRTHRESHOLD_SORTS` | `sheapthres(_shr)` pressure — #1 sort-heap tuning signal. orient -1. |
| T1 | `sort.section.total` | count | sort | `TOTAL_SECTION_SORTS` | |
| T1 | `sort.section.time` / `.proc_time` | count | millisecond | `TOTAL_SECTION_SORT_TIME` / `_PROC_TIME` | gate on `mon_act_metrics<>'NONE'` (live=BASE, ok). |
| T1 | `sort.tq_heap_requests` / `.tq_heap_rejections` | count | request | `TQ_SORT_HEAP_REQUESTS` / `_REJECTIONS` | DPF/parallel; ~0 single-member. orient -1 (rejections). |
| T1 | `sort.active` / `.active.max` ; `sort.consumers.active` / `.active.max` | gauge | sort/consumer | `ACTIVE_SORTS`/`_TOP`,`ACTIVE_SORT_CONSUMERS`/`_TOP` | point-in-time + HWM. |
| T1 | `sort.heap.allocated` / `.allocated.max` ; `sort.shrheap.allocated` / `.allocated.max` | gauge | page | `SORT_HEAP_ALLOCATED`/`SORT_HEAP_TOP`,`SORT_SHRHEAP_ALLOCATED`/`SORT_SHRHEAP_TOP` | 4 KB pages. work_mem pressure analog. |
| T1 | `sort.consumer.heap.max` / `.shrheap.max` | gauge | page | `SORT_CONSUMER_HEAP_TOP` / `SORT_CONSUMER_SHRHEAP_TOP` | largest single consumer. |
| T1 | `sort.heap.configured` / `sort.shrheap.threshold` | gauge | page | `SYSIBMADM.DBCFG` `sortheap` / `sheapthres_shr` | capacity denominators (AUTOMATIC-managed → read fresh). cache per run. |
| T1 | `sort.shrheap.utilized` | gauge | percent | derived `SORT_SHRHEAP_ALLOCATED/sheapthres_shr*100` | mirrors `tablespace.utilized`. orient -1. |
| T1 | `sort.section.proc_time_percent` | gauge | percent | `SYSIBMADM.MON_DB_SUMMARY.SECTION_SORT_PROC_TIME_PERCENT` | ready-made ratio; optional. |
| T1 | `hash.joins.total` / `.loops.total` | count | join/loop | `TOTAL_HASH_JOINS` / `TOTAL_HASH_LOOPS` | Db2 counts hash joins; pg/mysql cannot. `loops` orient -1. |
| T1 | `hash.joins.{overflows,small_overflows,post_threshold,post_shrthreshold}` | count | overflow/join | `HASH_JOIN_OVERFLOWS`,`HASH_JOIN_SMALL_OVERFLOWS`,`POST_THRESHOLD_HASH_JOINS`,`POST_SHRTHRESHOLD_HASH_JOINS` | spill/threshold pressure. orient -1. |
| T1 | `hash.grpbys.{total,overflows,post_threshold}` | count | operation/overflow | `TOTAL_HASH_GRPBYS`,`HASH_GRPBY_OVERFLOWS`,`POST_THRESHOLD_HASH_GRPBYS` | |
| T1 | `hash.joins.active` / `.active.max` ; `hash.grpbys.active` / `.active.max` | gauge | join/operation | `ACTIVE_HASH_JOINS`/`_TOP`,`ACTIVE_HASH_GRPBYS`/`_TOP` | point-in-time + HWM. |

(Per-statement sort/hash from `MON_GET_PKG_CACHE_STMT` → DBM query-metrics, `05`. Per-workload sort/hash
→ §1.11 WLM.)

### 1.9 Tablespace storage — `MON_GET_TABLESPACE`, `MON_GET_CONTAINER` (`map-tablespace-storage.md`)

Cheap columns ride the already-called `MON_GET_TABLESPACE(NULL,-1)`. All sizing is `gauge` (never
cumulative). `TBSP_*_PAGES × TBSP_PAGE_SIZE` = bytes; `TBSP_MAX_SIZE`/`INITIAL_SIZE`/`INCREASE_SIZE` are
**already bytes** (do NOT multiply — easiest bug here).

| Tier | Proposed `ibm_db2.*` | Type | Unit | Source | Notes |
|---|---|---|---|---|---|
| T0 | `tablespace.size` / `.usable` / `.used` / `.utilized` `(EXISTS)` | gauge | byte/percent | `TBSP_TOTAL/USABLE/USED_PAGES × PAGE_SIZE`; used/usable*100 | keep. |
| T0 | `tablespace.free` | gauge | byte | `TBSP_FREE_PAGES × PAGE_SIZE` [LIVE] | **emit only when ≥0** (SMS = -1). |
| T0 | `tablespace.high_water_mark` | gauge | byte | `TBSP_PAGE_TOP × PAGE_SIZE` [LIVE] | shrinkable/reorg-benefit signal. |
| T1 | `tablespace.pending_free` | gauge | byte | `TBSP_PENDING_FREE_PAGES × PAGE_SIZE` [LIVE] | reclaimable. low priority. |
| T0 | `tablespace.max_size` | gauge | byte | `TBSP_MAX_SIZE` [LIVE] (bytes!) | emit only when >0 (-1 = unlimited). |
| T0 | `tablespace.max_utilized` | gauge | percent | derived `USED_PAGES×PAGE_SIZE/TBSP_MAX_SIZE*100` when `AUTO_RESIZE_ENABLED & MAX_SIZE>0` | **actionable fullness vs ceiling** for auto-resize TS. orient -1. |
| T1 | `tablespace.initial_size` / `.increase_size` | gauge | byte | `TBSP_INITIAL_SIZE`/`TBSP_INCREASE_SIZE` [LIVE] (bytes!) | optional. |
| T1 | `tablespace.last_resize_failed` | gauge | (bool) | `TBSP_LAST_RESIZE_FAILED` [LIVE] | disk-full early warning. SC candidate. orient -1. |
| T0 | `tablespace.containers` | gauge | container | `TBSP_NUM_CONTAINERS` [LIVE] | cheap; rides existing row. |
| T1 | `tablespace.online` | gauge | (bool) | `TBSP_STATE`==NORMAL | numeric companion to the new TS-state SC. orient 1. |
| **T2** | `container.fs_used` / `.fs_total` (+ `.total`/`.used`/`.usable`/`.accessible`) | gauge | byte | `MON_GET_CONTAINER.*` [DOC] | gate `collect_container_metrics`. **own with io-disk §1.5 — define once.** |
| **T2** | `tablespace.rebalance.{extents_remaining,extents_processed}` ; `.extent_movement.{moved,left}` | gauge | extent | `MON_GET_REBALANCE_STATUS` / `MON_GET_EXTENT_MOVEMENT_STATUS` [DOC] | active only during rebalance. lowest priority. |

**Tags, not metrics** (`map-tablespace-storage.md` §2.6): add `tablespace_type` (`TBSP_TYPE` DMS/SMS),
`tablespace_content_type` (ANY/LARGE/USRTEMP/SYSTEMP), `storage_group` (`STORAGE_GROUP_NAME`),
`tablespace_state` (`TBSP_STATE`) to the TS size metrics — lets dashboards exclude SMS/temp TS from
free-space alarms and roll up per storage group. **Service check** `ibm_db2.tablespace.status` from
`TBSP_STATE` (NORMAL→OK, *_PENDING→WARN, OFFLINE/NOT_ACCESSIBLE→CRIT) is the biggest gap-closer here
(today TS state is only a transient event) — mirror `DB_STATUS_MAP` with a new `TABLE_SPACE_STATE_MAP`
in `utils.py`; keep the existing change-event.

### 1.10 Tables & indexes — `MON_GET_TABLE`, `MON_GET_INDEX`, `SYSCAT.*` (`map-tables-indexes.md`)

**Cardinality is the defining constraint** — one series per object per member. Gate behind config +
top-N cap (`ORDER BY <activity> DESC FETCH FIRST {limit} ROWS ONLY`) + schema include/exclude, exactly
like pg `relations`/`max_relations` and mysql `index_metrics` `INDEX_LIMIT=1000`. **Common tags:** `db`,
`schema` (`TABSCHEMA`), `table` (`TABNAME`), `index` (`INDNAME` via `SYSCAT.INDEXES` join on
`(TABSCHEMA,TABNAME,IID)` — `MON_GET_INDEX` has no name, falls back to `iid:<n>`), `member`. Default
exclude `SYSCAT,SYSIBM,SYSSTAT,SYSPUBLIC,SYSTOOLS,NULLID,SYSIBMADM,SYSIBMINTERNAL,SYSIBMTS`.

| Tier | Proposed `ibm_db2.*` | Type | Unit | Source | Gate |
|---|---|---|---|---|---|
| **T1** | `table.count` | gauge | table | `SELECT TABSCHEMA,COUNT(*) FROM SYSCAT.TABLES WHERE TYPE IN ('T','S') GROUP BY TABSCHEMA` | `collect_table_count` **default on** (cheap; pg `table.count` parity). tags `db`,`schema`. |
| **T2** | `table.scans` ; `table.rows_{read,inserted,updated,deleted}` | count | scan/row | `MON_GET_TABLE.TABLE_SCANS`,`ROWS_READ`,`ROWS_INSERTED/UPDATED/DELETED` [LIVE] | `collect_table_metrics` + `table_metrics_limit` (~300). pg `seq_scans`/`rows_*` analog. |
| **T2** | `table.{overflow_accesses,overflow_creates,page_reorgs,no_change_updates}` | count | access/row/reorg/update | `MON_GET_TABLE.*` [LIVE] | **Db2-native fragmentation/REORG-need signals** (no pg/mysql analog). orient -1 on overflow/reorg. |
| **T2** | `table.{stats,rts}_rows_modified` | count | row | `STATS_ROWS_MODIFIED`/`RTS_ROWS_MODIFIED` [LIVE] | RUNSTATS staleness. optional. |
| **T2** | `table.{data,index,lob,long,xda,col}_object_pages` | gauge | page | `MON_GET_TABLE.*_OBJECT_L_PAGES` [LIVE] | per-table footprint (× PAGESIZE = bytes). |
| **T2** | `table.data.reads.{logical,physical}` (+xda/col variants) | count | page | `MON_GET_TABLE.OBJECT_DATA_{L,P}_READS` [LIVE] | requires `mon_obj_metrics=EXTENDED` (live=ok). |
| **T2** | `table.{direct_reads,direct_writes}` | count | page | `MON_GET_TABLE.DIRECT_*` [LIVE] | optional; overlaps io-disk. |
| **T2** | `index.scans` ; `index.only_scans` ; `index.jump_scans` | count | scan | `MON_GET_INDEX.INDEX_SCANS`,`INDEX_ONLY_SCANS`,`INDEX_JUMP_SCANS` [LIVE] | `collect_index_metrics` + `index_metrics_limit` (~1000). pg `index_scans`/mysql `index.reads`. |
| **T2** | `index.key_updates` / `.include_col_updates` | count | operation | `KEY_UPDATES`/`INCLUDE_COL_UPDATES` [LIVE] | mysql `index.updates`. |
| **T2** | `index.pseudo_deletes` / `.del_keys_cleaned` | count | key | `PSEUDO_DELETES`/`DEL_KEYS_CLEANED` [LIVE] | dead-key accumulation/cleanup-lag. Db2-native. |
| **T2** | `index.leaf_pages` / `.levels` | gauge | page/level | `NLEAF` / `NLEVELS` [LIVE] | size proxy (×PAGESIZE) + B-tree depth. |
| **T2** | `index.{root,int,boundary_leaf,nonboundary_leaf}_node_splits` ; `index.{page_allocations,pseudo_empty_pages,empty_pages_reused,empty_pages_deleted,pages_merged}` | count | split/page | `MON_GET_INDEX.*` [LIVE] | B-tree health / fragmentation. lower priority. |
| **T2** | `index.reads.{logical,physical}` | count | page | `OBJECT_INDEX_{L,P}_READS` [LIVE] | per-index BP reads (pg `index_blocks_read/hit`). EXTENDED. |
| **T2** | `table.{cardinality,npages,fpages}` ; `table.{data,index,lob}_size` | gauge | row/page/byte | `SYSCAT.TABLES.CARD/NPAGES/FPAGES` ; `SYSIBMADM.ADMINTABINFO` (KB→byte) | catalog estimates / exact size (ADMINTABINFO is **expensive** → separate flag/interval). |

> Phasing (`map-tables-indexes.md` §E.8): P1 = `table.count` (cheap, default on); P1 = core
> `MON_GET_TABLE` row activity + Db2-native fragmentation (gated `collect_table_metrics`); P2 = core
> `MON_GET_INDEX` (gated `collect_index_metrics`); P3 = sizes via `ADMINTABINFO` + long-tail split
> columns. Overlap: DB-aggregate row counters (`ibm_db2.row.*` §1.3) and per-table (`ibm_db2.table.*`)
> are complementary, not duplicate.

### 1.11 WLM workload / service-class — `MON_GET_WORKLOAD`, `MON_GET_SERVICE_SUBCLASS`
(`map-wlm-workload.md`)

**Db2-native** (no real pg/mysql analog). Default `SYSDEFAULT*` objects always return rows → safe to
query unconditionally; low cardinality (a handful of names × members). **One metric namespace
`ibm_db2.wlm.*`**; the distinguishing dimension is the tag set. Tags: `workload_name` (from WORKLOAD) OR
`service_superclass`+`service_subclass`+`service_class_id` (from SUBCLASS), + `member`. **Double-count
caveat:** SUBCLASS and WORKLOAD aggregate the same activity along two axes → collect **WORKLOAD by
default**, gate SUBCLASS behind `collect_wlm_service_class_metrics` (off). `TOTAL_CPU_TIME` is
**microseconds** `(verify)`; other `*_TIME` are ms.

| Tier | Proposed `ibm_db2.wlm.*` | Type | Unit | Source column (BOTH unless noted) | Notes |
|---|---|---|---|---|---|
| T1 | `total_cpu_time` | count | microsecond | `TOTAL_CPU_TIME` | headline CPU-per-class. **µs (verify).** |
| T1 | `activities.{completed,aborted,rejected}` ; `app_activities.{completed,aborted,rejected}` | count | activity | `ACT_*_TOTAL`,`APP_ACT_*_TOTAL` | core throughput. aborted/rejected orient -1. |
| T1 | `requests.completed` ; `app_requests.completed` ; `activity_requests` | count | request | `RQSTS_COMPLETED_TOTAL`,`APP_RQSTS_COMPLETED_TOTAL`,`ACT_RQSTS_TOTAL` | |
| T1 | `total_{wait,request,app_request,activity,activity_wait,section,section_proc}_time` | count | millisecond | `TOTAL_*_TIME` | request-time decomposition. waits orient -1. |
| T1 | `queue_time` / `queue_assignments` | count | ms/assignment | `WLM_QUEUE_TIME_TOTAL` / `WLM_QUEUE_ASSIGNMENTS_TOTAL` | **WLM throttling signal.** orient -1. |
| T1 | `commits` / `rollbacks` / `internal_commits` / `internal_rollbacks` | count | transaction | `TOTAL_APP_COMMITS`,`TOTAL_APP_ROLLBACKS`,`INT_COMMITS`,`INT_ROLLBACKS` | per-class. |
| T1 | wait decomposition: `{lock_wait_time,lock_waits,pool_read_time,pool_write_time,direct_read_time,direct_write_time,log_disk_wait_time,log_buffer_wait_time,agent_wait_time,agent_waits,client_idle_wait_time,prefetch_wait_time,extended_latch_wait_time,extended_latch_waits,tcpip_{recv,send}_wait_time,ipc_{recv,send}_wait_time}` | count | ms/wait | `*_WAIT_TIME`,`*_WAITS*` | per-class wait tiers; sum ≈ `total_wait_time`. |
| T1 | `statements.{select,uid,ddl,merge,call,dynamic,static,failed}` | count | query | `*_SQL_STMTS` | per-class statement mix. `failed` orient -1. |
| T1 | `rows_{returned,read,modified,inserted,updated,deleted}` | count | row | `ROWS_*` | per-class row activity. |
| T1 | `sorts.{total,overflows,post_threshold,post_shrthreshold}` ; `hash_joins.{total,overflows}` ; `hash_grpbys.{total,overflows}` ; `olap_funcs.{total,overflows}` ; `active_{sorts,hash_joins,olap_funcs}` ; `sort_{heap,shrheap}_allocated` | count/gauge | sort/operation/page | sort/hash family | per-class sort/hash. overflows orient -1. |
| T1 | `deadlocks` / `lock_timeouts` / `lock_escalations` ; `threshold_violations` / `lock_wait_thresh_exceeded` | count | lock/violation | `DEADLOCKS`,`LOCK_TIMEOUTS`,`LOCK_ESCALS`,`THRESH_VIOLATIONS`,`NUM_LW_THRESH_EXCEEDED` | orient -1. |
| T1 | `pkg_cache.{inserts,lookups}` / `cat_cache.{inserts,lookups}` | count | get | `PKG_CACHE_*`,`CAT_CACHE_*` | cache hit-ratio sources. |
| **SUBCLASS-only** | `agent_load_target_{utilization,demand}` ; `sort_shrheap_{utilization,demand}` | gauge | percent | DOUBLE, SUBCLASS-only | the 5 cols WORKLOAD omits — strongest reason to enable SUBCLASS. |
| T1 | `{effective,actual}_parallelism` ; `admission_overflows` / `admission_bypassed` ; `activities.{low,medium,high,critical}_priority` | gauge/count | thread/overflow/activity | parallelism/admission family | WLM admission & CPU-priority. |
| **T2-gated** | `wlm.bufferpool.*` / `wlm.direct_{reads,writes}` ; routine/compile/utility time (`routine_time`,`compile_time`,`runstats`,`reorgs`,`loads`,`backups`,…) | count | page/ms/operation | per-class BP/IO + utility | gate behind SUBCLASS flag / lower priority. |

Skip (`map-wlm-workload.md` "Skip"): caching-tier matrix, FCM/TQ subfamilies (→ §1.13), TLS/connect
timing (→ connections), AI model-provider, audit/diaglog, pureScale GBP/LBP (→ §1.13).

### 1.12 HADR / replication — `MON_GET_HADR` (`map-hadr-replication.md`)

**New category** (zero today). New `ibm_db2.hadr.*` namespace (NOT `replication.*` — Db2's feature is
literally HADR; "replication" means a different product). **Critical gating:** on a non-HADR DB
(`STANDARD` role), `MON_GET_HADR(-1)` returns **0 rows** — treat as "HADR not configured", emit only
`hadr.role{role:standard}=1` (or nothing), never error. Tags: `hadr_role`, `standby_id` (≤3),
`log_stream`, `standby_host` (on primary), `member`. State metrics use the **pg `wal_receiver` style**
(value always 1, state as a tag) to avoid metric churn when state flaps.

| Tier | Proposed `ibm_db2.hadr.*` | Type | Unit | Source column | Notes |
|---|---|---|---|---|---|
| T1 | `role` | gauge | — | `HADR_ROLE` (or DB CFG when 0 rows) | emit even when not configured. |
| T1 | `state` / `connected` / `syncmode` | gauge | — | `HADR_STATE`/`HADR_CONNECT_STATUS`/`HADR_SYNCMODE` | value 1 + state-as-tag. **congestion surfaces in `connect_status:congested`.** |
| T1 | `standby.count` | gauge | — | row count where role=PRIMARY | mysql `replicas_connected` analog. |
| T1 | `log_gap` | gauge | byte | `HADR_LOG_GAP` | **headline "behind by"** (pg `replication_delay_bytes`). orient -1. |
| T1 | `recv_replay_gap` | gauge | byte | `STANDBY_RECV_REPLAY_GAP` | replay backlog. orient -1. |
| T1 | `replay_lag` | gauge | second | derived `PRIMARY_LOG_TIME − STANDBY_REPLAY_LOG_TIME` | **time lag** (mysql `seconds_behind_source`). clamp ≥0. orient -1. |
| T1 | `time_since_last_recv` | gauge | second | `TIME_SINCE_LAST_RECV` | liveness. orient -1. |
| T1 | `log_wait.count` / `.time` / `.current` | count/gauge | wait/ms/second | `LOG_HADR_WAITS_TOTAL`/`LOG_HADR_WAIT_TIME` (from `MON_GET_TRANSACTION_LOG`, see §1.6) / `LOG_HADR_WAIT_CUR` | **congestion** (Db2-native). |
| T1 | `standby_recv_buf_percent` / `standby_spool_percent` | gauge | percent | `STANDBY_RECV_BUF_PERCENT`/`STANDBY_SPOOL_PERCENT` | congestion. spool NULL when off → skip. orient -1. |
| T1 | `heartbeat.missed` / `.expected` | gauge | — | `HEARTBEAT_MISSED`/`HEARTBEAT_EXPECTED` | health ratio. missed orient -1. |
| T1 (full) | `primary_log_pos`/`standby_log_pos`/`standby_replay_log_pos` ; `sock_{send,recv}_buf` ; `heartbeat.{interval,timeout}` ; `peer_window`/`.peer_window_remaining` ; `takeover_app_remaining.{primary,standby}` ; `replay_only_window.tran_count` | gauge | byte/second/— | `MON_GET_HADR.*` | LSN positions (`.as_rate()` for send/recv rate), config visibility, takeover progress. |

Service check `ibm_db2.hadr.status` from `HADR_STATE`+`HADR_CONNECT_STATUS` (PEER/CONNECTED→OK,
REMOTE_CATCHUP*/CONGESTED→WARN, DISCONNECTED*→CRIT). Authority: add
`EXECUTE ON FUNCTION SYSPROC.MON_GET_HADR`.

### 1.13 FCM / pureScale (T3 — clustered only) — `MON_GET_FCM`, `MON_GET_CF*`, `MON_GET_GROUP_BUFFERPOOL`
(`map-fcm-purescale.md`)

**Gate the entire category** behind a cached pureScale/DPF probe (member count >1, `MON_GET_CF` rows,
`SYSIBMADM.DB2_MEMBER.MEMBER_TYPE`). On the single-node target all functions exist but return 0/NULL —
`# no cov` in unit tests (like existing `group.*`). FCM-channel metrics on DPF **or** pureScale; CF/GBP
on pureScale only. The headline FCM volume/wait counters are **[LIVE-confirmed]** (embedded in
`MON_GET_DATABASE`/`_CONNECTION`/`_SERVICE_SUBCLASS`/`_WORKLOAD`); the dedicated-function columns are
`[DOC]` and need live-DESCRIBE.

| Tier | Proposed `ibm_db2.*` | Type | Unit | Source | Notes |
|---|---|---|---|---|---|
| T3 | `cf.wait_time` / `cf.waits` | count | ms/wait | `MON_GET_DATABASE.CF_WAIT_TIME`/`CF_WAITS` [LIVE] | **single best pureScale KPI.** cheap (DB row). |
| T3 | `reclaim.wait_time` / `.spacemap_wait_time` | count | ms | `RECLAIM_WAIT_TIME`/`SPACEMAPPAGE_RECLAIM_WAIT_TIME` [LIVE] | shared-disk space contention. |
| T3 | `fcm.{send,recv}_volume` / `.sends` / `.recvs` / `.{send,recv}_wait_time` / `.{send,recv}_waits` (+ `.message.*` / `.tq.*` subchannels) | count | byte/message/ms/wait | embedded `FCM_*` [LIVE] / `MON_GET_FCM` [DOC] | TQ subchannel = parallel-query shuffle cost. |
| T3 | `fcm.buffers.{free,free_low_water,total}` / `fcm.channels.{...}` / `.utilized` | gauge | buffer/channel/percent | `MON_GET_FCM` [DOC] | resource exhaustion early warning. gate `collect_fcm_metrics`. |
| T3 | `cf.{state,count,gbp.size,lock.size,sca.size,memory.current,memory.target,host.memory_{total,free}}` | gauge | —/page/byte | `MON_GET_CF` / `ENV_CF_SYS_RESOURCES` [DOC] | CF structure resources. gate `collect_cf_metrics`. |
| T3 | `cf.cmd.{requests,time,avg_time,wait_time}` | count/gauge | request/microsecond | `MON_GET_CF_CMD` / `MON_GET_CF_WAIT_TIME` [DOC] | per-command latency. **µs (verify).** tag `cf_cmd_name`. |
| T3 | `gbp.{full,castouts,cross_invalidations}` | count | event/page | `MON_GET_GROUP_BUFFERPOOL` [DOC] | castout/cross-invalidation. **don't double-map** the per-BP `group.*.invalid_pages` (§1.4). |

### 1.14 Memory — `MON_GET_MEMORY_POOL`, `MON_GET_MEMORY_SET` (`map-memory.md`)

**New category** (zero today). All **gauges** (point-in-time, never counters). The two pool columns give
full heap fidelity via **tagging** (`memory_pool`, `memory_set`) rather than one metric name per heap —
the mysql per-tag-dict pattern. **Cardinality:** `WHERE APPLICATION_HANDLE IS NULL` for default
collection (don't tag by `application_handle`/`edu_id` — explodes cardinality). `MON_GET_MEMORY_POOL` is
[LIVE-confirmed] (10 cols); `MON_GET_MEMORY_SET` is `[DOC]` — **live-DESCRIBE first**, and confirm the
**byte-vs-KiB** unit before shipping.

| Tier | Proposed `ibm_db2.memory.*` | Type | Unit | Source column | Tags | Notes |
|---|---|---|---|---|---|---|
| T1 | `pool.used` | gauge | byte `(verify)` | `MON_GET_MEMORY_POOL.MEMORY_POOL_USED` | `memory_pool`,`memory_set` | core per-heap memory. tag values: `BP`,`LOCKMGR`,`PACKAGE_CACHE`,`CAT_CACHE`,`SORTHEAP`,`SHARED_SORTHEAP`,`UTILITY`,… |
| T1 | `pool.used_hwm` | gauge | byte `(verify)` | `MEMORY_POOL_USED_HWM` | `memory_pool`,`memory_set` | per-heap peak — best near-limit signal; no pg/mysql analog. |
| T1 | `set.{committed,used,used_hwm,size,additional_committed}` | gauge | byte `(verify)` | `MON_GET_MEMORY_SET.*` [DOC] | `memory_set` | OS-committed per area (`DATABASE`,`DBMS`,`APPLICATION`,`BUFFERPOOL`,`FCM`,`FMP`,`PRIVATE`). **verify cols+unit.** |

---

## 2. queries.py changes (QueryManager / QueryExecutor definitions)

### 2.1 Migration posture

The shipped check hand-rolls cursors via `ibm_db.exec_immediate` + `iter_rows`
(`code-ibm_db2-current.md` §1-2); SQL lives as column-tuple constants in `queries.py`. The target
architecture (`03-reference-architecture.md`) is the **declarative `QueryExecutor`/`QueryManager`
`columns`-dict style** (Paradigm B, `code-mysql-metrics.md` §0; `code-postgres-metrics.md` §1B) — one
dict per `MON_GET_*` function, each column either a metric (`type: gauge|monotonic_count`) or a tag
(`type: tag` / `tag_not_null`). Every map file recommends Paradigm B for new work.

**Two valid landing paths:**
- **Path A (fastest P0, lowest risk):** keep the existing hand-rolled `query_*` methods and just
  **widen the column tuples** in `queries.py` + add submit lines. Zero architectural change. Best for
  the T0 columns that ride the 5 already-called functions (rows/throughput, bufferpool writes/timing,
  log, locks, tablespace, instance). This is literally "add columns to existing SELECTs."
- **Path B (target, required for new functions):** define new `QueryExecutor` dicts for the **new**
  functions (`MON_GET_WORKLOAD`, `MON_GET_MEMORY_POOL/SET`, `MON_GET_HADR`, `MON_GET_TABLE/INDEX`,
  `MON_GET_CONTAINER`, FCM/CF). These need tag-fan-out, top-N, and per-row tagging the hand-rolled path
  does poorly. Adopt Path B here and migrate the existing 5 opportunistically.

Recommendation: **Path A for the existing-5 widening (T0), Path B for every new function (T1/T2/T3).**
Do not block T0 breadth on the full migration.

### 2.2 Existing query widening (Path A — `queries.py` column tuples)

**`DATABASE_TABLE_COLUMNS`** (`queries.py:21-39`) — add (all [LIVE]):
```
total_app_commits, int_commits, total_app_rollbacks, int_rollbacks,
rows_inserted, rows_updated, rows_deleted,                       -- + optional int_rows_*
act_completed_total, act_aborted_total, act_rejected_total,
rqsts_completed_total, total_app_section_executions,
lock_waits, lock_wait_time, lock_escals,                         -- raw lock counters + escalations
lock_escals_maxlocks, lock_escals_locklist,
direct_reads, direct_writes, direct_read_reqs, direct_write_reqs, direct_read_time, direct_write_time,
log_disk_wait_time, log_disk_waits_total, num_log_buffer_full,
db_status, db_activation_state, db_conn_time,                    -- status/uptime (db_status already selected)
-- sort/hash (new sort/hash category, §1.8):
total_sorts, sort_overflows, post_threshold_sorts, post_shrthreshold_sorts,
total_section_sorts, total_section_sort_time, total_section_sort_proc_time,
active_sorts, active_sorts_top, active_sort_consumers, active_sort_consumers_top,
sort_heap_allocated, sort_heap_top, sort_shrheap_allocated, sort_shrheap_top,
sort_consumer_heap_top, sort_consumer_shrheap_top,
total_hash_joins, total_hash_loops, hash_join_overflows, hash_join_small_overflows,
post_threshold_hash_joins, post_shrthreshold_hash_joins,
total_hash_grpbys, hash_grpby_overflows, post_threshold_hash_grpbys,
active_hash_joins, active_hash_joins_top, active_hash_grpbys, active_hash_grpbys_top
-- optional statement-mix (gate): select_sql_stmts, uid_sql_stmts, ddl_sql_stmts, dynamic_sql_stmts,
--   static_sql_stmts, failed_sql_stmts, merge_sql_stmts, call_sql_stmts
```
(`MON_GET_DATABASE` becomes the workhorse: rows/throughput + locks + direct I/O + log waits + sort/hash
all ride one already-issued SELECT — no new round-trip.)

**`INSTANCE_TABLE_COLUMNS`** (`queries.py:16`) — replace `('total_connections',)` with:
```
total_connections, con_local_dbases, db2_status, db2start_time,
agents_registered, agents_registered_top, idle_agents, agents_from_pool,
agents_created_empty_pool, num_coord_agents, coord_agents_top, agents_stolen,
gw_cur_cons, gw_total_cons, gw_cons_wait_host, gw_cons_wait_client, num_gw_conn_switches,
product_name, service_level, server_platform,
'current timestamp AS current_time'   -- for uptime diff (like backup.latest)
```

**`BUFFER_POOL_TABLE_COLUMNS`** (`queries.py:44-78`) — add (writes/async/timing/victim/prefetch/sizing):
```
pool_data_writes, pool_index_writes, pool_xda_writes, pool_col_writes,        -- [DOC] pool_col_writes
pool_read_time, pool_write_time,
pool_async_data_reads, pool_async_index_reads, pool_async_xda_reads, pool_async_col_reads,
pool_async_data_writes, pool_async_index_writes, pool_async_xda_writes, pool_async_col_writes,
unread_prefetch_pages, prefetch_wait_time, prefetch_waits, pool_no_victim_buffer,
vectored_ios, pages_from_vectored_ios, block_ios, pages_from_block_ios, files_closed,
bp_cur_buffsz, bp_pages_left_to_remove, bp_tbsp_use_count
-- pureScale (gate): pool_*_gbp_invalid_pages
```

**`TABLE_SPACE_TABLE_COLUMNS`** (`queries.py:83-90`) — add:
```
tbsp_free_pages, tbsp_page_top, tbsp_pending_free_pages, tbsp_num_containers,
tbsp_max_size, tbsp_initial_size, tbsp_increase_size, tbsp_auto_resize_enabled,
tbsp_last_resize_failed, tbsp_type, tbsp_content_type, storage_group_name, tbsp_using_auto_storage
-- (+ per-TS I/O if collect_tablespace_io_metrics: pool_*_p_reads, pool_*_writes, pool_read_time,
--   pool_write_time, direct_*, files_closed)
```

**`TRANSACTION_LOG_TABLE_COLUMNS`** (`queries.py:95`) — replace the 4-col tuple with the full set:
```
log_reads, log_writes, total_log_available, total_log_used,
tot_log_used_top, sec_log_used_top, sec_logs_allocated, num_logs_avail_for_rename,
num_log_write_io, num_log_read_io, num_log_part_page_io, log_write_time, log_read_time,
num_log_buffer_full, num_log_data_found_in_buffer,
cur_commit_total_log_reads, cur_commit_disk_log_reads, cur_commit_log_buff_log_reads,
log_to_redo_for_recovery, log_held_by_dirty_pages, num_indoubt_trans,
archive_method1_status, archive_method2_status, method1_next_log_to_archive,
method2_next_log_to_archive, current_archive_log,
current_lsn, current_lso, oldest_tx_lsn, first_active_log, last_active_log, current_active_log, log_chain_id,
log_hadr_wait_time, log_hadr_waits_total   -- emitted as hadr.log_wait.* (§1.12)
```

> `[DOC]` columns above (`pool_col_writes`, `pool_async_*_writes`, `unread_prefetch_pages`,
> `pool_no_victim_buffer`, `vectored_ios`, `block_ios`, `bp_cur_buffsz`, `num_log_write_io`,
> `log_write_time`, …) **must be live-`DESCRIBE`'d on 12.1.4 before being added** — a missing column
> makes the whole SELECT fail (swallowed at WARNING → the entire collector silently goes dark). This is
> `00-README.md` risk #3, a gating P0 prerequisite.

### 2.3 New query blocks (Path B — `QueryExecutor` `columns` dicts)

Each new function is one declarative dict. Sketch (postgres/mysql `columns`-dict shape; metric prefix
`ibm_db2.` applied by the framework `__NAMESPACE__`):

```python
# Rows/throughput, bufferpool writes, etc. are folded into the widened existing SELECTs (§2.2).
# The blocks below are the NEW functions.

QUERY_WORKLOAD = {  # T1 default-on; SUBCLASS variant gated
    'name': 'mon_get_workload',
    'query': "SELECT workload_name, member, total_cpu_time, act_completed_total, "
             "act_aborted_total, act_rejected_total, total_wait_time, wlm_queue_time_total, "
             "total_app_commits, total_app_rollbacks, lock_wait_time, lock_waits, rows_read, "
             "rows_returned, rows_modified, total_sorts, sort_overflows "
             "FROM TABLE(MON_GET_WORKLOAD(NULL, -2))",
    'columns': [
        {'name': 'workload_name', 'type': 'tag'},
        {'name': 'member', 'type': 'tag'},
        {'name': 'wlm.total_cpu_time', 'type': 'monotonic_count'},       # us (verify)
        {'name': 'wlm.activities.completed', 'type': 'monotonic_count'},
        {'name': 'wlm.activities.aborted', 'type': 'monotonic_count'},
        {'name': 'wlm.activities.rejected', 'type': 'monotonic_count'},
        {'name': 'wlm.total_wait_time', 'type': 'monotonic_count'},
        {'name': 'wlm.queue_time', 'type': 'monotonic_count'},
        {'name': 'wlm.commits', 'type': 'monotonic_count'},
        {'name': 'wlm.rollbacks', 'type': 'monotonic_count'},
        {'name': 'wlm.lock_wait_time', 'type': 'monotonic_count'},
        {'name': 'wlm.lock_waits', 'type': 'monotonic_count'},
        {'name': 'wlm.rows_read', 'type': 'monotonic_count'},
        {'name': 'wlm.rows_returned', 'type': 'monotonic_count'},
        {'name': 'wlm.rows_modified', 'type': 'monotonic_count'},
        {'name': 'wlm.sorts.total', 'type': 'monotonic_count'},
        {'name': 'wlm.sorts.overflows', 'type': 'monotonic_count'},
    ],
}

QUERY_MEMORY_POOL = {  # T1 default-on; all gauges
    'name': 'mon_get_memory_pool',
    'query': "SELECT member, db_name, memory_set_type, memory_pool_type, "
             "memory_pool_used, memory_pool_used_hwm "
             "FROM TABLE(MON_GET_MEMORY_POOL(NULL, NULL, -2)) WHERE application_handle IS NULL",
    'columns': [
        {'name': 'member', 'type': 'tag'},
        {'name': 'db', 'type': 'tag'},                          # from db_name
        {'name': 'memory_set', 'type': 'tag'},                  # from memory_set_type
        {'name': 'memory_pool', 'type': 'tag'},                 # from memory_pool_type
        {'name': 'memory.pool.used', 'type': 'gauge'},          # byte (verify)
        {'name': 'memory.pool.used_hwm', 'type': 'gauge'},
    ],
}

QUERY_HADR = {  # T1; 0 rows when role=STANDARD -> emit nothing (or hadr.role only)
    'name': 'mon_get_hadr',
    'query': "SELECT hadr_role, standby_id, log_stream_id, hadr_state, hadr_connect_status, "
             "hadr_syncmode, hadr_log_gap, standby_recv_replay_gap, time_since_last_recv, "
             "log_hadr_wait_cur, standby_recv_buf_percent, standby_spool_percent, "
             "heartbeat_missed, heartbeat_expected, primary_log_time, standby_replay_log_time, "
             "member, current timestamp AS current_time FROM TABLE(MON_GET_HADR(-1))",
    # state/connected emitted value=1 + tag; replay_lag derived in a wrapper from the timestamps.
    'columns': [ ... ],  # see map-hadr-replication.md §7 for the full SELECT + state-as-tag handling
}

QUERY_TABLE_METRICS = {  # T2 gated collect_table_metrics; top-N + schema filter
    'name': 'mon_get_table',
    'query': "SELECT tabschema, tabname, member, table_scans, rows_read, rows_inserted, "
             "rows_updated, rows_deleted, overflow_accesses, overflow_creates, page_reorgs, "
             "data_object_l_pages, index_object_l_pages "
             "FROM TABLE(MON_GET_TABLE(NULL, NULL, -2)) "
             "WHERE tabschema NOT IN ('SYSCAT','SYSIBM','SYSSTAT','SYSPUBLIC','SYSTOOLS','NULLID',"
             "'SYSIBMADM','SYSIBMINTERNAL','SYSIBMTS') "
             "ORDER BY rows_read DESC FETCH FIRST {table_metrics_limit} ROWS ONLY",
    'columns': [
        {'name': 'schema', 'type': 'tag'}, {'name': 'table', 'type': 'tag'},
        {'name': 'member', 'type': 'tag'},
        {'name': 'table.scans', 'type': 'monotonic_count'},
        {'name': 'table.rows_read', 'type': 'monotonic_count'},
        {'name': 'table.rows_inserted', 'type': 'monotonic_count'},
        {'name': 'table.rows_updated', 'type': 'monotonic_count'},
        {'name': 'table.rows_deleted', 'type': 'monotonic_count'},
        {'name': 'table.overflow_accesses', 'type': 'monotonic_count'},
        {'name': 'table.overflow_creates', 'type': 'monotonic_count'},
        {'name': 'table.page_reorgs', 'type': 'monotonic_count'},
        {'name': 'table.data_object_pages', 'type': 'gauge'},
        {'name': 'table.index_object_pages', 'type': 'gauge'},
    ],
}
# Analogous blocks: QUERY_INDEX_METRICS (MON_GET_INDEX + SYSCAT.INDEXES join for INDNAME),
# QUERY_TABLE_COUNT (SYSCAT.TABLES, default-on), QUERY_CONTAINER (MON_GET_CONTAINER, gated),
# QUERY_SERVICE_SUBCLASS (gated), and the T3 FCM/CF/GBP blocks (pureScale-probe gated).
```

Wire-up: register these in the new-query-executor list (the `_new_query_executor` / `dynamic_queries`
equivalent the `DatabaseCheck` migration introduces, `03`); the `{table_metrics_limit}` /
`{index_metrics_limit}` placeholders are `.format(...)`-substituted from config (like pg
`max_relations`, mysql `INDEX_LIMIT`). Derived metrics that need Python (`uptime`, `replay_lag`,
`connection.percent_used`, `sort.shrheap.utilized`, `tablespace.max_utilized`) follow the existing
`backup.latest` timestamp-delta / `tablespace.utilized` ratio patterns (`ibm_db2.py:176-181,407-410`) —
keep them as small post-fetch computations.

### 2.4 Config-cached settings query

Capacity denominators (`max_connections`/`maxappls`, `max_coordagents`, `sortheap`,
`sheapthres_shr`, `sheapthres`, `locklist`, `maxlocks`, `locktimeout`, `dlchktime`) come from
`SYSIBMADM.DBCFG` / `DBMCFG`, not `MON_GET`. Fetch **once per run and cache** (mirror mysql
`GlobalVariables`, `code-mysql-metrics.md` §8) — they rarely change and some are AUTOMATIC (STMM-moving)
so read fresh each run, not once per process. Used both for derived `*.percent_used`/`*.utilized` gauges
and optional `*.configured`/`*.threshold` context gauges.

---

## 3. metadata.csv additions

### 3.1 Format & naming conventions

Header (existing): `metric_name,metric_type,interval,unit_name,per_unit_name,description,orientation,integration,short_name,curated_metric`

- `metric_type`: `count` (monotonic counters), `gauge`, `rate` (unused). `interval` blank.
- `unit_name` vocabulary used here: `connection`, `agent`, `transaction`, `row`, `operation`,
  `request`, `statement`, `lock`, `millisecond`, `microsecond`, `second`, `byte`, `page`, `get`,
  `sector`, `block`, `file`, `wait`, `event`, `percent`, `fraction`, `tablespace`, `container`,
  `extent`, `sort`, `join`, `overflow`, `consumer`, `level`, `split`, `key`, `database`, `item`,
  `message`, `buffer`, `channel`, `node`, `violation`, `assignment`, `thread`, `invocation`,
  `compilation`. (`activity`/`scan`/`access`/`reorg`/`update` are not standard DD units — use
  `operation`/`scan` per existing acceptance, falling back to `operation` where no exact unit fits.
  `ddev validate metadata` is the authority.)
- `per_unit_name`: blank for all of these (no `/s` rates from the agent).
- `description`: name the **source `MON_GET_*` column**, the tags, and any gating config flag — mirror
  pg's "Enabled with `relations`." convention. Quote descriptions containing commas.
- `orientation`: `0` (neutral throughput/size), `1` (higher is better — usable/free/hit ratios),
  `-1` (lower is better — waits/timeouts/deadlocks/escalations/overflows/aborts/rejects/failures/lag/
  utilization/used). Each §1 table notes the non-zero orientations.
- `integration=ibm_db2`. `short_name`/`curated_metric` blank (set `curated_metric` only if a metric
  belongs on the curated default dashboard set — leave to dashboard work).

Ready-to-paste row blocks already exist per category in each `_research/map-*.md` (§10/§9 of those
files); the implementer pastes the rows for the tiers being shipped. Example (rows-throughput core,
`map-rows-throughput.md` §9):
```
ibm_db2.transaction.commits,count,,transaction,,The number of application-requested transaction commits (TOTAL_APP_COMMITS). Tagged with db.,0,ibm_db2,,
ibm_db2.transaction.rollbacks,count,,transaction,,The number of application-requested transaction rollbacks (TOTAL_APP_ROLLBACKS). Tagged with db.,-1,ibm_db2,,
ibm_db2.row.inserted.total,count,,row,,The total number of rows inserted (ROWS_INSERTED). Tagged with db.,0,ibm_db2,,
ibm_db2.row.updated.total,count,,row,,The total number of rows updated (ROWS_UPDATED). Tagged with db.,0,ibm_db2,,
ibm_db2.row.deleted.total,count,,row,,The total number of rows deleted (ROWS_DELETED). Tagged with db.,0,ibm_db2,,
```

### 3.2 Target metric count

| | count |
|---|---|
| Existing (keep) | 49 |
| T0 adds (rides 5 already-called fns) | ~150 |
| T1 adds (sort/hash, memory, WLM, HADR, log/bufferpool tail) | ~120 |
| **Subtotal T0+T1 (recommended ship)** | **~320** |
| T2 adds (per-table/index/connection/container/subclass — gated) | ~60 names |
| T3 adds (FCM/CF/GBP/global locks — gated) | ~50 |
| **Total catalog (all tiers declared)** | **~430** |

The **~320** T0+T1 baseline already **exceeds** pg(244)/mysql(254) in count and matches/exceeds them on
every shared concept. **Important:** every metric the check *can emit* (including gated T2/T3) needs a
`metadata.csv` row even if off by default — declare them all; gate **emission**, not **declaration**.
Test coverage (`tests/metrics.py` `STANDARD`, §`11`) asserts the default-on set; gated metrics are
asserted in dedicated tests with the flag enabled.

### 3.3 Catalog fixes to fold in (from existing 49)

- Fix `ibm_db2.bufferpool.xda.hit_percent` description (`metadata.csv:26`) — copy-paste says "index page
  request"; should say "XML storage object (XDA) page request" (`00-README.md` smaller-reconciliations).
- Optionally fix `ibm_db2.lock.pages` orientation: currently `0`; lock-list memory pressure is
  arguably `-1` — leave as-is for back-compat unless dashboards depend on it.

---

## 4. New tag dimensions & cardinality controls

### 4.1 The tag taxonomy

| Tag | Source | Cardinality | Applied to | Gating |
|---|---|---|---|---|
| `db` `(EXISTS)` | config / `DB_NAME` | 1 | everything | always |
| `database_hostname`, `database_instance` (NEW) | resolved host / instance id (`DatabaseCheck`) | 1 | everything | always (base-tag migration, `03`) |
| `member` (NEW) | `MON_GET_*.MEMBER` (`-2` arg) | = #members (1 on single-node) | every `MON_GET_*` metric | always (constant on single-member) |
| `bufferpool` `(EXISTS)` | `BP_NAME` | low (handful) | bufferpool.* | always |
| `tablespace` `(EXISTS)` | `TBSP_NAME` | low (handful) | tablespace.* | always |
| `tablespace_type`, `tablespace_content_type`, `storage_group`, `tablespace_state` (NEW) | `MON_GET_TABLESPACE` | low | tablespace.* (size) | always (cheap) |
| `memory_set`, `memory_pool` (NEW) | `MON_GET_MEMORY_*` | low (~7 sets, ~12 pools) | memory.* | always |
| `workload_name` (NEW) | `MON_GET_WORKLOAD` | low (default ~2 + custom) | wlm.* | default on |
| `service_superclass`, `service_subclass`, `service_class_id` (NEW) | `MON_GET_SERVICE_SUBCLASS` | low | wlm.* | `collect_wlm_service_class_metrics` |
| `db2_version`, `db2_edition`, `db2_license`, `db2_product`, `db2_platform` (NEW, instance tags) | `ENV_*` / `MON_GET_INSTANCE` | 1 | instance-scope | always (cached per run) |
| `hadr_role`, `standby_id`, `log_stream`, `standby_host` (NEW) | `MON_GET_HADR` | ≤3 standbys | hadr.* | HADR configured |
| `schema`, `table` (NEW) | `MON_GET_TABLE` | **HIGH** (#tables) | table.* | `collect_table_metrics` + top-N + schema filter |
| `index` (NEW) | `SYSCAT.INDEXES` join | **HIGH** (#indexes) | index.* | `collect_index_metrics` + top-N + schema filter |
| `container`, `container_type` (NEW) | `MON_GET_CONTAINER` | medium (#containers) | container.* | `collect_container_metrics` |
| `session_auth_id`(user), `client_applname`(app), `client_hostname`, `workload_occurrence_state`(state), `application_handle`, `current_isolation` (NEW) | `MON_GET_CONNECTION` | **HIGH** (per connection) | connection.* (Tier-2) | `collect_connection_metrics` + top-N |
| `cf_id`, `host_name`, `cf_cmd_name`, `remote_member` (NEW) | `MON_GET_CF*` / FCM | low (pureScale) | cf.*/fcm.* | pureScale probe + flags |
| `memory_pool` value `application_handle` / `edu_id` | `MON_GET_MEMORY_POOL` | **HIGH** | (excluded by default) | never tag by default (`WHERE … IS NULL`) |

### 4.2 Cardinality control rules (mandatory for high-cardinality categories)

For per-table, per-index, per-container, per-connection (and per-WLM-subclass if a site defines many
classes), apply the **same discipline as pg `relations` / mysql `index_metrics`**:

1. **Config gate, default OFF** (except `collect_table_count`, default ON — it's a cheap catalog query).
   Proposed flags: `collect_table_metrics`, `collect_index_metrics`, `collect_container_metrics`,
   `collect_connection_metrics`, `collect_table_lock_metrics`, `collect_connection_lock_metrics`,
   `collect_wlm_service_class_metrics`, `collect_fcm_metrics`, `collect_cf_metrics`,
   `collect_statement_mix_metrics`, `collect_log_extraction_metrics`. Add to `spec.yaml` /
   `config_models`.
2. **Per-collector `*_limit`** (top-N): `table_metrics_limit` (~300, pg `max_relations`),
   `index_metrics_limit` (~1000, mysql `INDEX_LIMIT`), `connection_metrics_limit`. Enforce with
   `ORDER BY <activity_col> DESC FETCH FIRST {limit} ROWS ONLY` (Db2's `LIMIT`) so the most-active
   objects survive the cap.
3. **Schema include/exclude** (regex via the shared `datadog_checks.base` filters) — default-exclude the
   9 system schemas. Mirror pg's relation autodiscovery filters.
4. **`member` fan-out** (`-2`) only when the topology warrants it (DPF/pureScale); otherwise `-1` keeps
   `member` constant and cardinality flat. Tier-2/T3 fan-out multiplies by member count — document it.
5. **Connection Tier-1 vs Tier-2:** the aggregate `connection.count` (GROUP BY identity) is bounded and
   safe always-on; only the **per-connection** series (`application_handle` tag) need the flag+cap.
   `monotonic_count` tolerates the handle-reuse churn (drops negative deltas) but document it.

### 4.3 Per-object opt-in summary (the pg/mysql parity pattern)

The map files converge on this contract (`map-tables-indexes.md` §E, `map-locking-concurrency.md` §9,
`map-connections-applications.md` §F): **aggregate/instance/db/bufferpool/tablespace/log/sort/hash/
memory/WLM-workload/HADR = always-on, bounded**; **per-table / per-index / per-container /
per-connection / per-WLM-subclass / clustered = opt-in, capped, filtered**. This matches pg (core
`pg_stat_database` always on; `relations`/`functions` opt-in) and mysql (`SHOW GLOBAL STATUS` always on;
per-schema/per-index/`extra_*` opt-in) exactly.

---

## 5. Existing 49 metrics — keep / rename / deprecate

**Verdict: keep all 49 as-is (names + types).** None should be renamed or deprecated — they are all
correctly-sourced and on the right grain; renaming breaks dashboards/monitors with no upside. The work
is **additive**. Specific notes:

### 5.1 Keep unchanged
All 25 bufferpool, 4 tablespace, 5 log, 6 lock, 3 row, 3 connection, 2 application, 1 backup metrics
keep their current names, types, and units. Existing bufferpool reads keep `unit_name=get`; new
read-family metrics reuse `get` for consistency. (The `00-README.md`/`02` reconciliation: the bufferpool
count is **25**, not 24 as `map-bufferpool.md` states — 24 per-pool + the aggregate family.)

### 5.2 `ibm_db2.lock.wait` — keep, but add raw counters (the one real fidelity bug)
`lock.wait` is collected as an **in-check-computed average** (`lock_wait_time/lock_waits`,
`ibm_db2.py:165-169`), which **destroys** the raw cumulative counters — they can't be delta'd/re-rated
in the backend (every other integration ships raw cumulatives). **Fix:** keep `lock.wait` (gauge avg)
for back-compat, and **add** `ibm_db2.lock.waits` (count) + `ibm_db2.lock.wait_time` (count, ms) raw
counters (§1.7). Migration note: the average can then be computed in-app as `wait_time/waits`; dashboards
should migrate to the raw counters over time (don't remove `lock.wait`).

### 5.3 Bufferpool reads regular+temp folding — preserve
The existing `bufferpool.<x>.reads.{physical,logical}` **sum regular + temp** reads
(`ibm_db2.py:204-209,…`). **Do NOT change this** (back-compat). The optional temp-split (§1.4) adds
`*.temp.*` as **new additional** series; it must not subtract from the existing folded metrics.

### 5.4 `files_closed` — resolve the triple-home before adding
`files_closed` appears three ways: as the documented **custom-query example**
(`conf.yaml.example` → `ibm_db2.tablespace.files_closed`), proposed as a bufferpool metric (§1.4), and as
a tablespace metric (§1.5/io-disk). **Pick one source** to avoid confusion: recommend
`ibm_db2.bufferpool.files_closed` from `MON_GET_BUFFERPOOL` (first-class, distinct prefix). The
custom-query example does not collide (different prefix); note the relationship in release notes.

### 5.5 `log.utilized` / `log.available` infinite-log handling — fix while touching the file
When `TOTAL_LOG_AVAILABLE == -1` (infinite logging, `LOGSECOND=-1`), the check submits
`log.available = 0` and `log.utilized = 0` (`ibm_db2.py:428-435`), conflating "infinite" with "none".
**Fix:** skip those two metrics (or emit a documented sentinel) under infinite logging — don't emit a
misleading 0. Keep the metric names. The new byte-native `log.space.*` siblings (§1.6) should apply the
same guard.

### 5.6 `connection.active` semantics — document, don't rename
`connection.active` is instance-wide (`MON_GET_INSTANCE.TOTAL_CONNECTIONS`) while `application.active`
is this-DB (`APPLS_CUR_CONS`); they diverge on multi-DB instances. Clarify in the metadata description;
do **not** rename.

---

## 6. Collection overhead guidance

### 6.1 Cost model

- **The five existing functions are near-free to widen.** `MON_GET_DATABASE`/`_INSTANCE` return one row;
  `_TRANSACTION_LOG` one row per member; `_BUFFERPOOL`/`_TABLESPACE` one row per object (handful). Adding
  columns to these SELECTs adds **zero round-trips** and negligible engine cost — T0's ~150 metrics ride
  queries the check already issues. This is why T0 is "high value / low risk" (`00-README.md` P0).
- **New low-cardinality functions (T1)** add a handful of round-trips: `MON_GET_WORKLOAD` (~2 rows),
  `MON_GET_MEMORY_POOL/SET` (~12/~7 rows), `MON_GET_HADR` (0–3 rows), sort/hash (rides
  `MON_GET_DATABASE`). Each is one cheap query. Total T1 overhead is small.
- **Per-object fan-out (T2)** is where cost lives: `MON_GET_TABLE`/`MON_GET_INDEX` scan all objects.
  Mitigations: top-N cap (`FETCH FIRST`), schema filter, and a **longer collection interval** for the
  expensive ones. `MON_GET_PAGE_ACCESS_INFO`-style and `ADMINTABINFO` (exact sizes) are notably
  heavier → separate flag + interval (e.g. 300s like mysql `index_metrics` `collection_interval`).
- **T3 (clustered)** is gated off on non-clustered instances by the pureScale/DPF probe — zero cost
  there.

### 6.2 Practical guidance

1. **Default collection interval** stays at 15s (`min_collection_interval`) for T0+T1 — they are cheap.
   Put T2 per-table/index and `ADMINTABINFO` on a **separate, longer interval** (the `QueryExecutor`
   `collection_interval` per-dict, like mysql `index_metrics.py:79`).
2. **Authority:** all new `MON_GET_*` functions need the same authority class the check already uses
   (`DATAACCESS`/`SQLADM`/`DBADM` or `EXECUTE` on each function). Add `EXECUTE ON FUNCTION` grants for the
   new functions (`MON_GET_WORKLOAD`, `MON_GET_MEMORY_POOL`, `MON_GET_MEMORY_SET`, `MON_GET_HADR`,
   `MON_GET_TABLE`, `MON_GET_INDEX`, `MON_GET_CONTAINER`, `MON_GET_SERVICE_SUBCLASS`, FCM/CF) to the
   README setup. Missing authority → graceful skip (§0.2 rule 4), not a failed run.
3. **Monitor switches:** T0/T1 counters populate under the default/live switches
   (`mon_req_metrics=BASE`, `mon_act_metrics=BASE`, `mon_obj_metrics=EXTENDED`). Per-table/index object
   bufferpool-read columns (`OBJECT_*_READS`) and `MON_GET_INDEX` access counters require
   `mon_obj_metrics=EXTENDED` (live = EXTENDED, ok); if a site sets it `NONE` those columns return
   0/NULL — emit 0 / skip, don't error. Sort-timing columns need `mon_act_metrics<>'NONE'`.
4. **Connection churn:** the persistent single connection (`code-ibm_db2-current.md` §2) is fine for
   metrics; per-job connections come with the DBM migration (`03`) and don't affect this metrics path.
5. **Live-DESCRIBE the `[DOC]` columns first** (gating prerequisite): widening a SELECT with a
   non-existent column fails the whole query and the collector silently goes dark (swallowed at
   WARNING). Run `DESCRIBE SELECT * FROM TABLE(MON_GET_BUFFERPOOL(NULL,-1))`,
   `…MON_GET_TRANSACTION_LOG(-1)`, `…MON_GET_CONTAINER(NULL,-1)`, `…MON_GET_MEMORY_SET(...)`, and the
   FCM/CF functions on 12.1.4 and reconcile the `[DOC]` columns before shipping (`00-README.md` risk #3).

---

## 7. Phasing (metric-breadth slice of `10-implementation-phases.md`)

| Phase | Metric scope | Tiers | Effort |
|---|---|---|---|
| **P0a** | Live-DESCRIBE all `[DOC]` columns on 12.1.4; stand up 12.1.4 CI. **Gating prerequisite.** | — | ~0.5 wk |
| **P0b** | Widen the 5 existing SELECTs: rows/throughput, bufferpool writes/async/timing, direct I/O, log timing/buffer/redo, lock raw+escalations, tablespace free/HWM/max + state SC, instance uptime/agents. Fix lock.wait/infinite-log/files_closed/xda-description. | T0 | ~1–1.5 wk |
| **P0c** | New low-cardinality functions: sort/hash (rides `MON_GET_DATABASE`), memory pools/sets, WLM workload, HADR. | T1 | ~1–1.5 wk |
| **P-tail** | Gated per-object: `table.count` (on), `collect_table_metrics`/`collect_index_metrics`, container FS, per-connection, WLM subclass. | T2 | folds into P1/later |
| **P-cluster** | pureScale/DPF probe + FCM/CF/GBP behind flags. | T3 | deferred / on-demand |

T0+T1 (P0) delivers the parity baseline on the **existing synchronous pattern** with no DBM machinery —
the highest value at the lowest risk, exactly as `00-README.md`/`10` sequence it. T2/T3 layer on behind
config flags without touching the default-on surface.

---

## 8. Source index

- 14 category maps: `_research/map-{bufferpool,io-disk,transaction-logs,locking-concurrency,
  rows-throughput,sorting-hashing,tablespace-storage,tables-indexes,connections-applications,
  instance-database-summary,memory,wlm-workload,hadr-replication,fcm-purescale}.md` (each carries the
  full per-category mapping table, pg/mysql-only gaps, Db2-native extras, ready-to-paste `metadata.csv`
  rows, and implementation notes).
- Current check audit: `_research/code-ibm_db2-current.md`. Live column oracle:
  `_research/_raw/02-monget-key-columns.txt` (11 functions DESCRIBE'd; `MON_GET_CONTAINER`/`_AGENT`/
  `MEMORY_SET`/FCM/CF **not** in it → `[DOC]`). Function inventory:
  `_research/_raw/01-version-and-monget-functions.txt`. Monitor switches:
  `_research/_raw/04-monitor-config.txt`.
- pg/mysql collection refs: `_research/code-postgres-metrics.md`, `_research/code-mysql-metrics.md`.
- Code to change: `/home/bits/dd/integrations-core/ibm_db2/datadog_checks/ibm_db2/queries.py`,
  `.../ibm_db2.py`, `.../utils.py` (status maps), `.../config_models/*` + `assets/configuration/spec.yaml`
  (new flags), `/home/bits/dd/integrations-core/ibm_db2/metadata.csv`,
  `.../assets/service_checks.json` (new TS/HADR SCs).
- Sibling docs: `01-db2-monitoring-primer.md`, `02-current-integration-audit.md`,
  `03-reference-architecture.md`, `05-dbm-query-metrics.md`, `10-implementation-phases.md`,
  `11-testing-and-validation.md`. (`09-implementation-architecture.md` and `12-risks-open-questions.md`
  are referenced but not yet written — use `00-README.md`'s "Key risks" as the `12` stand-in.)
