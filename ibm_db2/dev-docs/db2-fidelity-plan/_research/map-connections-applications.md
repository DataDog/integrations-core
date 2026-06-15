# Mapping — Connections / Applications / Sessions / Agents (Db2 fidelity plan)

Scope: bring the `ibm_db2` integration to postgres/mysql fidelity for the **connections-applications**
metric category — connection counts, application/session counts, per-connection throughput, agent-pool
health, and connection-level wait/time decomposition. This file is raw input for an implementation plan
handed to another agent. Favor completeness; every claim is sourced.

Primary Db2 sources for this category (all confirmed present on the live target
`DB2/LINUXX8664 12.1.4.0`, `_raw/01-version-and-monget-functions.txt`):
- `MON_GET_CONNECTION(application_handle, member)` — **per-connection** throughput/wait detail (417 cols;
  `_raw/02-monget-key-columns.txt` L1030-1448). The per-connection analog of MySQL
  `performance_schema.threads` / pg `pg_stat_activity`.
- `MON_GET_DATABASE(member)` — **instance/db aggregate** connection & agent counts
  (`_raw/02-monget-key-columns.txt` L16+; key cols L22-34).
- `MON_GET_INSTANCE(member)` — **instance-wide** agent-pool + gateway counts (24 cols; catalog-2 §3;
  `_raw/02-monget-key-columns.txt` L2447-2474).
- `SYSIBMADM.MON_CONNECTION_SUMMARY` — pre-built per-connection summary view (`_raw/03-sysibmadm-objects.txt`
  L40). Convenience view over `MON_GET_CONNECTION`.
- `SYSIBMADM.MON_DB_SUMMARY` (L43), `SYSIBMADM.APPLICATIONS` (L13), `SYSIBMADM.APPL_PERFORMANCE` (L14),
  `SYSIBMADM.SNAPAPPL_INFO` / `SNAPAPPL` (L57/58) — legacy/alternate aggregates.

> **Code refs.** Current integration: connection metrics are submitted from
> `/home/bits/dd/integrations-core/ibm_db2/datadog_checks/ibm_db2/ibm_db2.py` lines **131, 140, 143, 146,
> 149** using SQL from `/home/bits/dd/integrations-core/ibm_db2/datadog_checks/ibm_db2/queries.py`
> (`INSTANCE_TABLE` L16-17, `DATABASE_TABLE` L20-40). Postgres analogs:
> `/home/bits/dd/integrations-core/postgres/datadog_checks/postgres/util.py` `CONNECTION_METRICS`
> (L849), `CONNECTION_METRICS_BY_DB` (L826), `DBM_MIGRATED_METRICS` (L414), `NEWER_14_METRICS` (L443),
> `QUERY_PG_WAIT_EVENT_METRICS` (L809). MySQL analogs:
> `/home/bits/dd/integrations-core/mysql/datadog_checks/mysql/const.py` `STATUS_VARS` (Threads_/Connections_/
> Aborted_, L18-68), `VARIABLES_VARS` (max_connections, L71-79); `queries.py` `QUERY_USER_CONNECTIONS`
> (L220-243).

Units convention (catalog-2 provenance, general Db2 monitor-element knowledge): `*_TIME` counters are
**milliseconds**; `*_VOLUME` are **bytes**; monotonic since database activation (or connection start for
per-connection). `metric_type` discipline: monotonic lifetime counters → `monotonic_count` (catalog CSV
`count`); point-in-time → `gauge`. CSV `metric_type` vocabulary = `gauge`/`count`/`rate` (Agent
`monotonic_count` surfaces as `count`).

---

## A. What the integration already emits in this category (baseline)

| Existing metric | Db2 source column | type | unit | ibm_db2.py |
|---|---|---|---|---|
| `ibm_db2.connection.active` | `MON_GET_INSTANCE.TOTAL_CONNECTIONS` | gauge | connection | L131 |
| `ibm_db2.application.active` | `MON_GET_DATABASE.APPLS_CUR_CONS` | gauge | connection | L140 |
| `ibm_db2.application.executing` | `MON_GET_DATABASE.APPLS_IN_DB2` | gauge | connection | L143 |
| `ibm_db2.connection.max` | `MON_GET_DATABASE.CONNECTIONS_TOP` | gauge | connection | L146 |
| `ibm_db2.connection.total` | `MON_GET_DATABASE.TOTAL_CONS` | count (monotonic) | connection | L149 |

metadata.csv rows: L30-32 (`connection.active/max/total`), L2-3 (`application.active/executing`).
All carry only the static instance `self._tags` — **no `member` tag, no per-connection dimension**. This
is the entire current footprint; everything below is net-new fidelity.

> **NOTE/semantics gotcha:** `connection.active` is sourced from `MON_GET_INSTANCE.TOTAL_CONNECTIONS`
> (instance-wide, all DBs) while `application.active` is `APPLS_CUR_CONS` (this DB). For a single-DB target
> they roughly agree; on a multi-DB instance they diverge. The plan should make this explicit and consider
> renaming/clarifying. `ibm_db2.application.active` (=`APPLS_CUR_CONS`) is the truest "connections to THIS
> database" analog of `postgresql.connections` / `mysql.performance.threads_connected`.

---

## B. MAPPING TABLE — pg/mysql analog → Db2 source → proposed ibm_db2 metric

Legend for type: `g`=gauge, `c`=count(monotonic_count), `r`=rate. Tags column lists tags **beyond** the
base instance tags (`database_hostname`, `database_instance`, configured `tags`). `member` should be added
to every `MON_GET_*` metric (these functions take a member arg; `-1`=current, `-2`=all) — listed once here
to avoid repetition: **all rows below carry `member`** unless they come from `SYSIBMADM` aggregate views
that already roll up across members.

### B.1 Connection / application counts (instance + per-database aggregate)

| pg/mysql analog | Db2 source (fn + column) | proposed ibm_db2.<name> | type | unit | tags | notes / version-gating |
|---|---|---|---|---|---|---|
| `postgresql.connections` (gauge) / `mysql.performance.threads_connected` (gauge) | `MON_GET_DATABASE.APPLS_CUR_CONS` | `ibm_db2.application.active` *(exists)* | g | connection | — | Already emitted (ibm_db2.py:140). Truest "connections to this DB". metadata L2. |
| `postgresql.connections` "active/in-flight" subset | `MON_GET_DATABASE.APPLS_IN_DB2` | `ibm_db2.application.executing` *(exists)* | g | connection | — | Apps with a request currently being processed by the DB manager (ibm_db2.py:143). metadata L3. |
| `mysql.net.max_connections` (high-water, gauge) | `MON_GET_DATABASE.CONNECTIONS_TOP` | `ibm_db2.connection.max` *(exists)* | g | connection | — | High-water since activation (ibm_db2.py:146). metadata L31. |
| `mysql.net.connections` (rate of new conns) | `MON_GET_DATABASE.TOTAL_CONS` | `ibm_db2.connection.total` *(exists)* | c | connection | — | Lifetime coordinator-agent connections; delta→rate gives new-conn/s (ibm_db2.py:149). metadata L32. |
| (no direct pg/mysql analog — secondary/MPP conns) | `MON_GET_DATABASE.TOTAL_SEC_CONS` | `ibm_db2.connection.secondary.total` | c | connection | — | **NEW.** Subagent connections to other members (MPP/pureScale). DESCRIBE L24 (col `TOTAL_SEC_CONS`). Db2-native; gate to MPP/pureScale (≈0 on single-member). |
| `postgresql.max_connections` (gauge) | DB cfg `MAX_CONNECTIONS` (or `MAXAPPLS`) via `SYSIBMADM.DBCFG` / `MON_GET_*` not available — read cfg | `ibm_db2.connection.max_configured` | g | connection | — | **NEW.** `SELECT value FROM SYSIBMADM.DBCFG WHERE name='max_connections'` (or `maxappls`). `SYSIBMADM.DBCFG` confirmed present (`_raw/03` L24). Enables a usage-% metric (see B.2). (general Db2 12.1 — verify cfg name.) |
| `mysql.net.max_connections_available` | DBM cfg `MAX_CONNECTIONS` / `MAX_COORDAGENTS` via `SYSIBMADM.DBMCFG` | `ibm_db2.connection.coordagents_max` | g | connection | — | **NEW.** `SYSIBMADM.DBMCFG` present (`_raw/03` L25). Instance-level coordinator-agent ceiling. (general — verify.) |
| (instance-wide total, all DBs) | `MON_GET_INSTANCE.TOTAL_CONNECTIONS` | `ibm_db2.connection.active` *(exists)* | g | connection | — | Already emitted (ibm_db2.py:131). Keep but document it is instance-wide, not per-DB. metadata L30. |
| (instance-wide # local DBs with conns) | `MON_GET_INSTANCE.CON_LOCAL_DBASES` | `ibm_db2.instance.local_databases` | g | database | — | **NEW.** Db2-native (DESCRIBE L2456). # local DBs currently connected. |

### B.2 Connection-pool saturation (derived — pg/mysql parity)

| pg/mysql analog | Db2 source | proposed ibm_db2.<name> | type | unit | tags | notes |
|---|---|---|---|---|---|---|
| `postgresql.percent_usage_connections` (fraction) / `postgresql.percent_database_usage_connections` | derived: `APPLS_CUR_CONS / max_connections(cfg)` | `ibm_db2.connection.percent_used` | g | fraction | — | **NEW (derived).** Compute in check: `MON_GET_DATABASE.APPLS_CUR_CONS` ÷ DBCFG `max_connections`. Mirror pg's `pct_connections` (util.py:826/849). High-value SLO metric. |
| (mysql Max_used vs available) | derived: `CONNECTIONS_TOP / max_connections(cfg)` | `ibm_db2.connection.percent_used_peak` | g | fraction | — | **NEW (derived).** Peak utilization. Optional. |

### B.3 Agent pool health (Db2-native; weak pg/mysql analog = thread cache)

`MON_GET_INSTANCE` (instance-wide; DESCRIBE L2447-2474, catalog-2 §3) and `MON_GET_DATABASE`
(per-DB; DESCRIBE L27-30) expose agent-pool counters. Closest pg/mysql analog is MySQL's thread-cache
(`mysql.performance.threads_cached`/`threads_created`/`thread_cache_size`) — conceptually "worker reuse".

| pg/mysql analog | Db2 source (fn + column) | proposed ibm_db2.<name> | type | unit | tags | notes / gating |
|---|---|---|---|---|---|---|
| `mysql.performance.threads_running` (loosely) | `MON_GET_INSTANCE.NUM_COORD_AGENTS` | `ibm_db2.agent.coord` | g | agent | — | **NEW.** Coordinator agents now (DESCRIBE L2463). |
| (high-water) | `MON_GET_INSTANCE.COORD_AGENTS_TOP` | `ibm_db2.agent.coord.max` | g | agent | — | **NEW.** DESCRIBE L2464. |
| (registered agents) | `MON_GET_INSTANCE.AGENTS_REGISTERED` | `ibm_db2.agent.registered` | g | agent | — | **NEW.** DESCRIBE L2458. |
| (high-water) | `MON_GET_INSTANCE.AGENTS_REGISTERED_TOP` | `ibm_db2.agent.registered.max` | g | agent | — | **NEW.** DESCRIBE L2459. |
| `mysql.performance.threads_cached` | `MON_GET_INSTANCE.IDLE_AGENTS` | `ibm_db2.agent.idle` | g | agent | — | **NEW.** Idle agents in pool (DESCRIBE L2460). |
| `mysql.performance.threads_created` ↑ pressure | `MON_GET_INSTANCE.AGENTS_CREATED_EMPTY_POOL` | `ibm_db2.agent.created_empty_pool` | c | agent | — | **NEW.** Agents created because pool empty = pool-pressure (DESCRIBE L2462). Highest-signal agent metric. |
| (pool reuse) | `MON_GET_INSTANCE.AGENTS_FROM_POOL` | `ibm_db2.agent.from_pool` | c | agent | — | **NEW.** DESCRIBE L2461. Pair with above for hit ratio. |
| (agents stolen) | `MON_GET_INSTANCE.AGENTS_STOLEN` | `ibm_db2.agent.stolen` | c | agent | — | **NEW.** DESCRIBE L2465. |
| — | `MON_GET_DATABASE.NUM_ASSOC_AGENTS` | `ibm_db2.agent.associated` | g | agent | — | **NEW.** Per-DB associated agents (DESCRIBE L27). |
| — | `MON_GET_DATABASE.AGENTS_TOP` | `ibm_db2.agent.associated.max` | g | agent | — | **NEW.** DESCRIBE L28. |
| — | `MON_GET_DATABASE.NUM_COORD_AGENTS` | (alias of agent.coord per-DB) | g | agent | — | Optional; DESCRIBE L29. Prefer instance-level to avoid double-count. |
| — | `MON_GET_DATABASE.NUM_POOLED_AGENTS` | `ibm_db2.agent.pooled` | g | agent | — | **NEW.** Db2-native (MON_GET_DATABASE col, DESCRIBE L406). |

### B.4 DRDA gateway connections (Db2-native; no pg/mysql analog)

From `MON_GET_INSTANCE` (catalog-2 §3, DESCRIBE L2466-2470). Relevant only when the instance acts as a
DRDA application server/gateway (federation). Gate behind a config flag; ~0 otherwise.

| Db2 source | proposed ibm_db2.<name> | type | unit | notes |
|---|---|---|---|---|
| `GW_TOTAL_CONS` | `ibm_db2.gateway.connection.total` | c | connection | NEW. DESCRIBE L2466. |
| `GW_CUR_CONS` | `ibm_db2.gateway.connection.active` | g | connection | NEW. |
| `GW_CONS_WAIT_HOST` | `ibm_db2.gateway.connection.waiting_host` | g | connection | NEW. Conns waiting on remote host. |
| `GW_CONS_WAIT_CLIENT` | `ibm_db2.gateway.connection.waiting_client` | g | connection | NEW. |
| `NUM_GW_CONN_SWITCHES` | `ibm_db2.gateway.connection.switches` | c | connection | NEW. |

### B.5 Per-connection throughput & wait decomposition — `MON_GET_CONNECTION` (the core net-new fidelity)

`MON_GET_CONNECTION(NULL, -2)` returns **one row per active connection per member** (DESCRIBE L1030-1448,
417 cols). This is the per-session detail layer that pg's DBM `postgresql.connections_by_process`
(metadata L52) and MySQL's `mysql.performance.user_connections` (`QUERY_USER_CONNECTIONS`, queries.py:220)
provide. **Cardinality control required** (top-N by activity, or aggregate by identity dims) — analogous
to MySQL grouping `performance_schema.threads` by user/host/db/state.

**Identity / tag columns** (DESCRIBE L1032-1047): `APPLICATION_HANDLE` (BIGINT, the connection id),
`APPLICATION_NAME`, `APPLICATION_ID`, `MEMBER`, `COORD_MEMBER`, `SESSION_AUTH_ID` (the connected user —
best `user` tag), `SYSTEM_AUTH_ID`, `CLIENT_HOSTNAME` (L1187), `CLIENT_IPADDR` (L1318),
`CLIENT_PORT_NUMBER` (L1188), `CLIENT_WRKSTNNAME`, `CLIENT_USERID`, `CLIENT_APPLNAME` (the app-supplied
name — best `app` tag), `CLIENT_PRDID`, `CLIENT_PLATFORM`, `CLIENT_PROTOCOL`, `WORKLOAD_OCCURRENCE_STATE`
(L1326 — the per-connection "state" string, analog of pg `state` / mysql `processlist_state`),
`CONNECTION_START_TIME` (L1047 — derive connection age), `IS_SYSTEM_APPL` (L1270 — filter system apps).

**Recommended approach (two tiers, mirror pg/mysql):**

- **Tier 1 — aggregate (low cardinality, always-on):** `GROUP BY` identity dims and emit COUNT(*) +
  SUM(throughput). This is the direct analog of `QUERY_USER_CONNECTIONS`
  (`SELECT ... COUNT(*) ... GROUP BY processlist_user/host/db/state`).
- **Tier 2 — per-connection top-N (config-gated, like mysql `index_config`/pg `relations`):** order by an
  activity column (`ROWS_READ` or `TOTAL_RQST_TIME`) `FETCH FIRST n ROWS ONLY`, tag by
  `application_handle` + identity. Gate behind a config flag (e.g. `collect_connection_metrics` /
  `connection_metrics_limit`).

| pg/mysql analog | Db2 source `MON_GET_CONNECTION.<col>` | proposed ibm_db2.<name> | type | unit | tags | notes |
|---|---|---|---|---|---|---|
| `mysql.performance.user_connections` (gauge, grouped by user/host/state) | `COUNT(*)` over rows | `ibm_db2.connection.count` | g | connection | `session_auth_id`(user), `client_applname`(app), `client_hostname`, `workload_occurrence_state`(state), `member` | **NEW (Tier 1).** Direct analog of mysql user_connections (queries.py:220) & pg connections_by_process (metadata L52). DESCRIBE identity cols above. |
| `postgresql.transactions.idle_in_transaction` (gauge) | `COUNT(*) WHERE WORKLOAD_OCCURRENCE_STATE='UOWWAIT'`/idle states | `ibm_db2.connection.idle_in_transaction` | g | connection | `member` | **NEW (derived).** Map pg idle-in-tx via `WORKLOAD_OCCURRENCE_STATE`. Also usable: `APPL_IDLE_TIME` (L1436) / `UOW_CLIENT_IDLE_WAIT_TIME` (L1274). Verify state-string values live. |
| `postgresql.rows_returned` (rate, per-db) — but per-connection | `ROWS_RETURNED` (L1102) | `ibm_db2.connection.rows_returned` | c | row | identity tags, `member` | NEW. Per-connection rows returned to app. |
| `postgresql.rows_fetched`/`rows_read` (rate) | `ROWS_READ` (L1101) | `ibm_db2.connection.rows_read` | c | row | identity, `member` | NEW. Rows read to satisfy queries (scan pressure). Good top-N order key. |
| `postgresql.rows_inserted` | `ROWS_INSERTED` (L1276) | `ibm_db2.connection.rows_inserted` | c | row | identity, `member` | NEW. |
| `postgresql.rows_updated` | `ROWS_UPDATED` (L1277) | `ibm_db2.connection.rows_updated` | c | row | identity, `member` | NEW. |
| `postgresql.rows_deleted` | `ROWS_DELETED` (L1275) | `ibm_db2.connection.rows_deleted` | c | row | identity, `member` | NEW. |
| (rows modified total) | `ROWS_MODIFIED` (L1100) | `ibm_db2.connection.rows_modified` | c | row | identity, `member` | NEW. ins+upd+del. |
| `postgresql.commits` (rate) | `TOTAL_APP_COMMITS` (L1139) | `ibm_db2.connection.commits` | c | transaction | identity, `member` | NEW. Per-connection commits; rate via delta. |
| `postgresql.rollbacks` (rate) | `TOTAL_APP_ROLLBACKS` (L1143) | `ibm_db2.connection.rollbacks` | c | transaction | identity, `member` | NEW. |
| (internal commits/rollbacks) | `INT_COMMITS` (L1140) / `INT_ROLLBACKS` (L1144) | `ibm_db2.connection.commits.internal` / `.rollbacks.internal` | c | transaction | identity | NEW (optional). |
| `mysql.performance.com_select` etc. (statement mix) | `SELECT_SQL_STMTS`(L1288), `UID_SQL_STMTS`(L1289), `DDL_SQL_STMTS`(L1290), `DYNAMIC_SQL_STMTS`(L1285), `STATIC_SQL_STMTS`(L1286), `FAILED_SQL_STMTS`(L1287), `CALL_SQL_STMTS`(L1298), `MERGE_SQL_STMTS`(L1291) | `ibm_db2.connection.stmts.{select,uid,ddl,dynamic,static,failed,call,merge}` | c | query | identity, `member` | NEW. Per-connection SQL mix; analog of mysql `Com_*`. Pick a subset to bound count. |
| `postgresql.deadlocks` (per-conn) | `DEADLOCKS` (L1071) | `ibm_db2.connection.deadlocks` | c | lock | identity | NEW. |
| `mysql.innodb.row_lock_time` (loosely) | `LOCK_WAIT_TIME` (L1092) / `LOCK_WAITS` (L1093) | `ibm_db2.connection.lock_wait_time` / `.lock_waits` | c | millisecond / lock | identity | NEW. Per-connection lock contention. |
| `postgresql.activity.xact_start_age` (loosely) | derive from `UOW_START_TIME` (L1320) | `ibm_db2.connection.uow_age` | g | second | identity | NEW (derived). Age of current transaction. |
| (idle conn age) | `APPL_IDLE_TIME` (L1436) | `ibm_db2.connection.idle_time` | g | second | identity | NEW. Seconds since last request — find abandoned conns. |
| `mysql.net.bytes_sent`/`bytes_received` (per-conn) | `TCPIP_SEND_VOLUME`(L1104)/`TCPIP_RECV_VOLUME`(L1103) | `ibm_db2.connection.tcpip.send_volume` / `.recv_volume` | c | byte | identity | NEW. Network volume per connection. |

**Time decomposition per connection** (ms; the "where is time going" tier, richer than pg/mysql at
session scope — Db2-native advantage):

| Db2 source `MON_GET_CONNECTION.<col>` | proposed ibm_db2.<name> | type | unit | notes |
|---|---|---|---|---|
| `TOTAL_RQST_TIME` (L1110) | `ibm_db2.connection.total_rqst_time` | c | millisecond | Total request time. Good top-N order key. |
| `TOTAL_APP_RQST_TIME` (L1109) | `ibm_db2.connection.total_app_rqst_time` | c | millisecond | Time the app spent in requests. |
| `TOTAL_CPU_TIME` (L1113) | `ibm_db2.connection.total_cpu_time` | c | microsecond | NOTE: CPU time element is **microseconds**, not ms (catalog-2 §4 caveat — verify). |
| `TOTAL_WAIT_TIME` (L1114) | `ibm_db2.connection.total_wait_time` | c | millisecond | Sum of wait components below. |
| `POOL_READ_TIME`(L1068)/`POOL_WRITE_TIME`(L1069) | `ibm_db2.connection.pool_read_time`/`.pool_write_time` | c | millisecond | BP I/O wait. |
| `LOCK_WAIT_TIME` (L1092) | (see above) | c | millisecond | |
| `LOG_DISK_WAIT_TIME`(L1096)/`LOG_BUFFER_WAIT_TIME`(L1094) | `ibm_db2.connection.log_disk_wait_time`/`.log_buffer_wait_time` | c | millisecond | Log wait. |
| `CLIENT_IDLE_WAIT_TIME` (L1070) | `ibm_db2.connection.client_idle_wait_time` | c | millisecond | Time waiting on the client (network/think time). |
| `TOTAL_SECTION_SORT_TIME` (L1116) / `TOTAL_SORTS` (L1119) | `ibm_db2.connection.sort_time`/`.sorts` | c | millisecond / sort | Per-conn sort cost (cross-ref map-sorting-hashing.md). |
| `AGENT_WAIT_TIME` (L1051) / `AGENT_WAITS_TOTAL` (L1052) | `ibm_db2.connection.agent_wait_time`/`.agent_waits` | c | millisecond / wait | Waited for an agent (pool exhaustion at conn scope). |

> Submission style: use the **declarative QueryExecutor `columns` dict** (Paradigm B; mysql
> `index_metrics.py`/`queries.py`, pg new-style dicts in `util.py`). Each metric column `type` =
> `gauge`/`monotonic_count`; identity columns `type:'tag'` (or `tag_not_null` for nullable like
> `client_hostname`). One `FETCH FIRST {limit} ROWS ONLY` query for Tier 2; one `GROUP BY` query for Tier 1.

### B.6 SYSIBMADM convenience views (alternatives / cross-checks)

| pg/mysql analog | Db2 view (`_raw/03-sysibmadm-objects.txt`) | proposed use | notes |
|---|---|---|---|
| `mysql.performance.user_connections` | `SYSIBMADM.MON_CONNECTION_SUMMARY` (L40) | alt source for Tier-1 per-conn rollup | Pre-joined summary over `MON_GET_CONNECTION`: per-connection `ROWS_READ`, `TOTAL_CPU_TIME`, `ACT_*`, `RQSTS_COMPLETED_TOTAL`, `TOTAL_APP_COMMITS`, etc. Columns are a curated subset — prefer raw `MON_GET_CONNECTION` for control, but this view is lower-effort. (general Db2 12.1 — verify exact columns via DESCRIBE.) |
| db-level throughput aggregate | `SYSIBMADM.MON_DB_SUMMARY` (L43) | cross-check db aggregates | One-row db summary (commits, rollbacks, rows, avg times). |
| `mysql.performance.user_connections` (legacy) | `SYSIBMADM.APPLICATIONS` (L13) / `SNAPAPPL_INFO` (L57) | legacy per-app identity | Has `AGENT_ID`/`APPL_STATUS`/`APPL_NAME`/`AUTHID`. Deprecated snapshot family — prefer `MON_GET_CONNECTION`. |
| per-app perf | `SYSIBMADM.APPL_PERFORMANCE` (L14) | legacy per-app rows-read/selected ratio | Deprecated; informational. |

---

## C. Db2-native metrics worth adding with NO pg/mysql analog

(High-value, category-relevant, not represented in postgres/mysql metadata.)

1. **Agent-pool pressure** — `MON_GET_INSTANCE.AGENTS_CREATED_EMPTY_POOL` → `ibm_db2.agent.created_empty_pool`
   (count). Single best "connection concurrency is exceeding agent pool" signal. No pg/mysql equivalent
   (they don't expose a server-managed agent pool). DESCRIBE L2462.
2. **Agent pool hit ratio** (derived from `AGENTS_FROM_POOL` vs `AGENTS_CREATED_EMPTY_POOL`) →
   `ibm_db2.agent.pool_hit_percent` (gauge). Db2-native operational metric.
3. **DRDA gateway connection family** (B.4) — relevant only as DRDA AS/federation server; no pg/mysql
   analog.
4. **Secondary/subagent connections** — `MON_GET_DATABASE.TOTAL_SEC_CONS` → `ibm_db2.connection.secondary.total`.
   MPP/pureScale only; no analog.
5. **Local databases connected** — `MON_GET_INSTANCE.CON_LOCAL_DBASES` → `ibm_db2.instance.local_databases`.
6. **WLM/admission at connection scope** — `MON_GET_CONNECTION.WLM_QUEUE_TIME_TOTAL` (L1111),
   `WLM_QUEUE_ASSIGNMENTS_TOTAL` (L1112) → `ibm_db2.connection.wlm_queue_time`/`.wlm_queue_assignments`.
   Db2 WLM has no pg/mysql parallel. (Aggregate WLM lives in `MON_GET_SERVICE_SUBCLASS`/`MON_GET_WORKLOAD`,
   see catalog-2 §4-5 — separate map.)
7. **Connection security/TLS** — `MON_GET_CONNECTION.CONNECT_SEC_TYPE` (L1417), `CONNECT_CIPHER_SPEC`
   (L1418), `TOTAL_TLS_CONNECTS` (L1446). Could surface a tag/gauge for TLS-vs-plaintext connection mix.
   Db2-native (12.1).
8. **Connection reusability** — `MON_GET_CONNECTION.CONNECTION_REUSABILITY_STATUS` (L1396),
   `REUSABILITY_STATUS_REASON` (L1397). 12.1 connection-pooling feature; no analog.
9. **Routine/section time per connection** — `TOTAL_ROUTINE_TIME` (L1135), `TOTAL_SECTION_TIME` (L1129).
10. **Agent association high-water per UOW** — `ASSOCIATED_AGENTS_TOP` (L1325) — intra-parallel fan-out.

---

## D. pg/mysql connection metrics with NO Db2 equivalent (flag as gaps)

| pg/mysql metric | why no Db2 equivalent |
|---|---|
| `postgresql.sessions.session_time` / `.active_time` / `.idle_in_transaction_time` (PG14+ `pg_stat_database`) | Db2 has no per-DB cumulative session-time counters in `MON_GET_DATABASE`. Closest is per-connection `TOTAL_RQST_TIME`/`APPL_IDLE_TIME` from `MON_GET_CONNECTION` (B.5), but it is per-connection and resets when the connection ends — not a stable per-DB lifetime counter. Could be approximated by SUM over connections but loses ended sessions. **Gap (partial).** |
| `postgresql.sessions.count` / `.abandoned` / `.fatal` / `.killed` (PG14+ session outcome counters) | No Db2 monitor element tracks session termination *cause* (lost client vs fatal vs operator kill). `MON_GET_DATABASE.TOTAL_CONS` counts connections but not outcomes. **Gap.** |
| `mysql.net.aborted_clients` / `mysql.net.aborted_connects` | Db2 does not expose aborted-connection counters analogous to MySQL's. `TOTAL_CONNECT_AUTHENTICATIONS` (L1257, per-connection) exists but no instance-level "failed/aborted connects" counter. `MON_GET_CONNECTION.FAILED_SQL_STMTS` is statement-level, not connect-level. **Gap.** Possible proxy: `db2diag.log` parsing (out of scope). |
| `mysql.performance.threads_created` (exact) / `thread_cache_size` | Db2's agent model differs; `AGENTS_CREATED_EMPTY_POOL` (B.3) is the nearest intent but not a thread-cache size. **Partial (mapped by intent).** |
| `postgresql.activity.backend_xid_age` / `backend_xmin_age` (xid wraparound horizon per backend) | Db2 has no transaction-ID-wraparound concept (MVCC differs); no per-connection xid horizon. **No Db2 equivalent (architectural).** |
| `postgresql.activity.wait_event` count by `wait_event` (pg per-event histogram) | Db2 exposes wait *time* components per connection (POOL/LOG/LOCK/AGENT wait times, B.5) but NOT a discrete `wait_event`-name COUNT histogram at connection scope. Wait-event-style detail lives in `MON_GET_ACTIVITY`/`MON_GET_AGENT.EVENT_STATE` (activity sampling — see db2-live-activity.md). **Different shape; cover via activity map, not metrics.** |
| `postgresql.connections_by_process` exact `(state, application, user, db)` breakdown (DBM) | Achievable via `MON_GET_CONNECTION` Tier-1 group-by (B.5 `ibm_db2.connection.count`), but `state` semantics differ (Db2 `WORKLOAD_OCCURRENCE_STATE` strings ≠ pg `state` enum). **Mappable with caveats.** |

---

## E. Tagging model (this category)

- Base instance tags (all metrics): configured `tags`, `database_hostname`, `database_instance`. Mirror
  pg `add_core_tags` (postgres.py:258) / `tags_without_db`.
- `member` on every `MON_GET_*`-sourced metric (instance/db/connection). `-1`=current member,
  `-2`=all members. Single-member box → `member:0`.
- Per-connection (B.5) tag set, mapping to pg/mysql conventions:
  - `db` ← target database (the integration connects to one DB; static tag).
  - `user` ← `SESSION_AUTH_ID` (analog of pg `user`/mysql `processlist_user`).
  - `app` ← `CLIENT_APPLNAME` (analog of pg `application_name`/mysql client), fallback `APPLICATION_NAME`.
  - `client_hostname` ← `CLIENT_HOSTNAME` (`tag_not_null`).
  - `state` ← `WORKLOAD_OCCURRENCE_STATE` (analog of pg `state`/mysql `processlist_state`).
  - `application_handle` ← only on Tier-2 per-connection top-N (high cardinality; gate it).
- Consider an `is_system_appl`-based filter (DESCRIBE L1270) to exclude Db2 system connections from
  user-facing counts (mirror pg excluding `postgres`/`{dd__user}`, mysql excluding the monitor user).

---

## F. Implementation notes / version & authority gating

- **Authority:** `MON_GET_*` table functions require `DATAACCESS` or `SQLADM`/`WLMADM` or
  `EXECUTE`-on-function; the existing check connects as `DB2INST1` (full). Wrap each new query in graceful
  degradation (mirror pg `_run_query_scope` catching `ProgrammingError`/`FeatureNotSupported`,
  postgres.py:804-825; mysql warns and returns `{}` on missing authority). Missing function/authority →
  log warning + skip, don't fail the check.
- **Monitor switches** (`_raw/04-monitor-config.txt`): `mon_req_metrics=BASE` and `mon_act_metrics=BASE`
  are sufficient to populate the request-time/activity counters used in B.5 (request-time, wait-time,
  rows). No EXTENDED switch needed for connection-level throughput. Counts that depend on object metrics
  are not in this category.
- **Cardinality:** Tier-2 per-connection metrics must be gated behind a config flag with a top-N limit
  (mirror mysql `index_config.limit`=1000 / pg `max_relations`=300). Default Tier-1 aggregate (group-by
  identity) is bounded and safe always-on. `FETCH FIRST {n} ROWS ONLY` is Db2's `LIMIT`.
- **Submission paradigm:** use declarative QueryExecutor `columns` dicts (Paradigm B). The existing
  ibm_db2 check hand-rolls cursors (`iter_rows`); the plan should migrate connection metrics to the base
  `QueryManager`/`QueryExecutor` for tag/type handling parity with pg/mysql.
- **Counter resets:** `MON_GET_CONNECTION` counters reset when the connection ends (handle is reused).
  `MON_GET_DATABASE`/`MON_GET_INSTANCE` counters reset on database deactivation / instance restart.
  `monotonic_count` handles resets (drops negative deltas). For per-connection top-N, the
  `application_handle` series will churn — acceptable for top-N/gated collection but document it.
- **Every new metric needs a metadata.csv row** in `/home/bits/dd/integrations-core/ibm_db2/metadata.csv`
  with `integration=ibm_db2`, correct `metric_type` (`gauge`/`count`), `unit_name`
  (`connection`/`agent`/`row`/`transaction`/`millisecond`/`byte`/`fraction`/`second`/`query`/`lock`),
  `orientation`, and a description naming the gating config flag and tags. Current file has 49 metrics
  (L2-50); this category adds ~25-40 depending on tiers chosen.

---

## G. Source index (absolute paths)

- Db2 column truth (DESCRIBE dumps): `/home/bits/dd/integrations-core/ibm_db2/dev-docs/db2-fidelity-plan/_research/_raw/02-monget-key-columns.txt`
  — `MON_GET_CONNECTION` L1030-1448, `MON_GET_DATABASE` L16+ (conn cols L22-34), `MON_GET_INSTANCE`
  L2447-2474.
- Function availability: `.../_research/_raw/01-version-and-monget-functions.txt`.
- SYSIBMADM views: `.../_research/_raw/03-sysibmadm-objects.txt` (MON_CONNECTION_SUMMARY L40,
  MON_DB_SUMMARY L43, APPLICATIONS L13, APPL_PERFORMANCE L14).
- Monitor switches: `.../_research/_raw/04-monitor-config.txt`.
- Catalog notes: `.../_research/db2-monget-catalog-2.md` (MON_GET_INSTANCE §3, AGENT §6).
- Live activity / connection identity: `.../_research/db2-live-activity.md`.
- Current integration code: `/home/bits/dd/integrations-core/ibm_db2/datadog_checks/ibm_db2/ibm_db2.py`
  (L127-149), `.../queries.py` (L16-40), `/home/bits/dd/integrations-core/ibm_db2/metadata.csv` (L2-3,30-32).
- Postgres analogs: `/home/bits/dd/integrations-core/postgres/datadog_checks/postgres/util.py`
  (CONNECTION_METRICS L849, CONNECTION_METRICS_BY_DB L826, DBM_MIGRATED_METRICS L414, NEWER_14_METRICS
  L443), `.../postgres/metadata.csv` (L51-52,65,106-108,173-179).
- MySQL analogs: `/home/bits/dd/integrations-core/mysql/datadog_checks/mysql/const.py` (STATUS_VARS,
  VARIABLES_VARS), `.../mysql/queries.py` (QUERY_USER_CONNECTIONS L220-243),
  `/home/bits/dd/integrations-core/mysql/metadata.csv` (L137-141,210-216).

> **Note:** the prompt referenced `db2-monget-catalog-1.md`, `db2-monget-catalog-3.md`, and
> `db2-sysibmadm-views.md`; these files do not exist in `_research/` (only `db2-monget-catalog-2.md` and
> the raw `03-sysibmadm-objects.txt`). All Db2 claims here are sourced from the live raw DESCRIBE dumps and
> the existing catalog-2, with general-knowledge items explicitly flagged.
