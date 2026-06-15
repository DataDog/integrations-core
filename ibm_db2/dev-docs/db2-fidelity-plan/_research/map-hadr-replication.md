# Metric Category Map — HADR / Replication (Db2 12.1)

Raw research input for the Db2 high-fidelity metric-collection implementation plan. **Category scope:** HADR (High Availability Disaster Recovery) state, log gap, log send/receive rate, congestion, replay lag, takeover, peer window, heartbeat, spool/recv-buffer congestion. Target Db2 version **12.1** (live container **12.1.4**, image `icr.io/db2_community/db2:12.1.4.0`, container `db2-primary`, db `TESTDB`).

This file is the mapping deliverable for ONE category. It is exhaustive on purpose — favor completeness over brevity. All code findings cite absolute paths; IBM doc URLs are cited per element.

---

## 0. TL;DR / orientation

- **The existing `ibm_db2` integration emits ZERO metrics in this category.** `metadata.csv` (`/home/bits/dd/integrations-core/ibm_db2/metadata.csv`, 49 metrics) has no `ibm_db2.hadr.*` / `ibm_db2.replication.*` rows. The check never calls `MON_GET_HADR` or `SYSIBMADM.SNAPHADR`. Gap explicitly called out in `code-ibm_db2-current.md:372-373`.
- **So there is NO existing `ibm_db2.*` naming to follow in this category** — we get to define the namespace. Proposal: **`ibm_db2.hadr.*`** (mirrors IBM's own "HADR" terminology and matches the dashboard/health language). Do NOT name it `ibm_db2.replication.*` — Db2's feature is literally called HADR, and "replication" in Db2-land also means SQL Replication / Q Replication (a different product). Using `hadr.*` avoids ambiguity.
- **Primary source: `MON_GET_HADR(-1)`** — the modern, supported 12.1 table function. 57 columns (full schema captured live below, §2). One row per (log stream × standby) pair. On a primary with N standbys you get N rows; on a standby you get 1 row.
- **Secondary/legacy source: `SYSIBMADM.SNAPHADR`** — older snapshot admin view, 23 columns (§3). Superset of nothing MON_GET_HADR lacks; **prefer MON_GET_HADR**. SNAPHADR is documented-deprecated-in-spirit (snapshot monitor) but still present in 12.1.4 (verified live). Only use as a fallback if `MON_GET_HADR` is somehow unavailable; not recommended.
- **CRITICAL gating fact:** on a non-HADR database (`HADR database role = STANDARD`), `MON_GET_HADR(-1)` returns **0 rows** (verified live: `SELECT count(*) FROM TABLE(MON_GET_HADR(-1))` → `0`). The collector must treat "0 rows" as "HADR not configured" and emit nothing (or a single `ibm_db2.hadr.role` state metric = standard), NOT error. This is the dominant deployment case (most Db2 installs are not HADR).
- All MON_GET column names come back **lowercase** through the check's driver (`ibm_db.ATTR_CASE = ibm_db.CASE_LOWER`, `ibm_db2.py:567`). Use lowercase keys in code.

---

## 1. How pg/mysql model this category (the fidelity bar)

### postgres (`/home/bits/dd/integrations-core/postgres/metadata.csv`, query defs `/home/bits/dd/integrations-core/postgres/datadog_checks/postgres/util.py`)
Postgres splits replication into several query blocks (util.py line refs):
- `REPLICATION_METRICS_10` / `_9_1` / `_9_2` (`util.py:646-681`): `postgresql.replication_delay` (gauge, sec), `postgresql.replication_delay_bytes` (gauge, byte) — **standby-side lag** (how far behind this replica is). Gated on `pg_is_in_recovery()`.
- `QUERY_PG_REPLICATION_STATS_METRICS` (`util.py:684-726`, pg10+): from `pg_stat_replication` (primary-side, one row per connected standby). LSN byte deltas: `replication.sent_lsn_delay`, `.write_lsn_delay`, `.flush_lsn_delay`, `.replay_lsn_delay` (all gauge/byte); time lags `replication.wal_write_lag`, `.wal_flush_lag`, `.wal_replay_lag` (gauge/sec); `replication.backend_xmin_age`. Tags: `wal_app_name`, `wal_state`, `wal_sync_state`, `wal_client_addr`, `slot_name`, `slot_type`.
- `QUERY_PG_STAT_WAL_RECEIVER` (`util.py:729-750`): standby receiver health — `wal_receiver.connected` (gauge), `.received_timeline`, `.last_msg_send_age`, `.last_msg_receipt_age`, `.latest_end_age`. Tag `status`.
- `QUERY_PG_REPLICATION_SLOTS` (`util.py:752-778`) + `_STATS` (pg14+): slot retention bytes + spill/stream counters.
- Archiver (`COMMON_ARCHIVER_METRICS`, `util.py:612-614`): `archiver.archived_count`, `.failed_count` (count).

### mysql (`/home/bits/dd/integrations-core/mysql/metadata.csv:242-255`)
- `mysql.replication.seconds_behind_source` / `seconds_behind_master` (gauge, sec) — the headline lag.
- `mysql.replication.replicas_connected` (gauge).
- Group-replication block `mysql.replication.group.*` (transactions applied/checked/proposed/rollback/queued/validating, conflicts_detected, member_status) — Galera/GR; **no Db2 analog** (Db2 HADR is log-shipping, not multi-primary certification).
- Service checks: `mysql.replication.replica_running`, `mysql.replication.group.status`.

### The fidelity-bar mapping (intent → Db2 column)
| pg/mysql intent | Db2 12.1 equivalent |
|---|---|
| "how far behind is the standby" (time) | `MON_GET_HADR.STANDBY_REPLAY_DELAY` is a *config* delay, NOT lag; real time-lag is derived from `PRIMARY_LOG_TIME - STANDBY_REPLAY_LOG_TIME` (no single column). Closest single columns: `HADR_LOG_GAP` (bytes), `STANDBY_RECV_REPLAY_GAP` (bytes). |
| "how far behind" (bytes) | `HADR_LOG_GAP` (avg primary→standby gap, bytes); `STANDBY_RECV_REPLAY_GAP` (recv→replay gap on standby, bytes) |
| "is the replica connected" | `HADR_CONNECT_STATUS` (CONNECTED / DISCONNECTED / CONGESTED) |
| "replica running" service check | `HADR_STATE` (PEER / REMOTE_CATCHUP / DISCONNECTED_PEER / ...) + `HADR_CONNECT_STATUS` |
| "replicas connected" count | row count of `MON_GET_HADR` on primary (one row per standby) |
| LSN delays (sent/write/flush/replay) | `PRIMARY_LOG_POS`, `STANDBY_LOG_POS`, `STANDBY_REPLAY_LOG_POS` byte positions; deltas between them |
| send/recv throughput rate | **no direct rate column**; derive rate from monotonic `PRIMARY_LOG_POS`/`STANDBY_LOG_POS` deltas, or use `LOG_HADR_WAITS_TOTAL`/`LOG_HADR_WAIT_TIME` for congestion |
| pg slots retention | no analog (Db2 uses `HADR_SPOOL_LIMIT` + `STANDBY_SPOOL_PERCENT`) |

---

## 2. PRIMARY SOURCE — `MON_GET_HADR(-1)` — full 57-column schema (live 12.1.4)

`SELECT * FROM TABLE(MON_GET_HADR(-1))`. The `-1` (or `NULL`) member arg = aggregate across all members. Verified live via `DESCRIBE SELECT * FROM TABLE(MON_GET_HADR(-1))` on `db2-primary`/`TESTDB`. IBM doc: `MON_GET_HADR` table function — https://www.ibm.com/docs/en/db2/12.1?topic=functions-mon-get-hadr-returns-high-availability-disaster (12.1 KC). Monitor elements: https://www.ibm.com/docs/en/db2/12.1?topic=elements-monitor

Columns (exact name, SQL type, semantics):

| # | Column | Type | Semantics (monitor element) |
|---|---|---|---|
| 1 | `HADR_ROLE` | VARCHAR(13) | PRIMARY / STANDARD / STANDBY. The role of *this* member. |
| 2 | `REPLAY_TYPE` | VARCHAR(9) | PHYSICAL (always, in current Db2). |
| 3 | `HADR_SYNCMODE` | VARCHAR(10) | SYNC / NEARSYNC / ASYNC / SUPERASYNC. |
| 4 | `STANDBY_ID` | SMALLINT | 1..3 identifying which standby this row describes (multi-standby). 0 on standby's own row. |
| 5 | `LOG_STREAM_ID` | INTEGER | Log stream (member) id. |
| 6 | `HADR_STATE` | VARCHAR(23) | DISCONNECTED / LOCAL_CATCHUP / REMOTE_CATCHUP_PENDING / REMOTE_CATCHUP / PEER / DISCONNECTED_PEER. **The headline state.** |
| 7 | `HADR_FLAGS` | VARCHAR(512) | Space-separated flags, e.g. `STANDBY_RECV_BLOCKED`, `ASSISTED_REMOTE_CATCHUP`. |
| 8 | `PRIMARY_MEMBER_HOST` | VARCHAR(255) | Hostname of primary member. |
| 9 | `PRIMARY_INSTANCE` | VARCHAR(128) | Instance name of primary. |
| 10 | `PRIMARY_MEMBER` | SMALLINT | Member number of primary. |
| 11 | `STANDBY_MEMBER_HOST` | VARCHAR(255) | Hostname of the standby this row describes. |
| 12 | `STANDBY_INSTANCE` | VARCHAR(128) | Instance name of standby. |
| 13 | `STANDBY_MEMBER` | SMALLINT | Member number of standby. |
| 14 | `HADR_CONNECT_STATUS` | VARCHAR(12) | CONNECTED / DISCONNECTED / CONGESTED. **Congestion lives here.** |
| 15 | `HADR_CONNECT_STATUS_TIME` | TIMESTAMP | When connect status last changed. |
| 16 | `HEARTBEAT_INTERVAL` | BIGINT | Heartbeat interval (seconds). |
| 17 | `HADR_TIMEOUT` | BIGINT | HADR_TIMEOUT cfg (seconds). |
| 18 | `TIME_SINCE_LAST_RECV` | BIGINT | Seconds since last message received from partner. **Liveness/lag proxy.** |
| 19 | `PEER_WAIT_LIMIT` | BIGINT | Seconds primary will block in peer before breaking. |
| 20 | `LOG_HADR_WAIT_CUR` | BIGINT | Seconds the current log write has been waiting on HADR. **Congestion (current).** |
| 21 | `LOG_HADR_WAIT_TIME` | BIGINT | Total time (ms) log writers waited on HADR. **Congestion (cumulative).** |
| 22 | `LOG_HADR_WAITS_TOTAL` | BIGINT | Total count of HADR log waits. **Congestion (cumulative count).** |
| 23 | `SOCK_SEND_BUF_REQUESTED` | BIGINT | Requested TCP send buffer bytes (0 = OS default). |
| 24 | `SOCK_SEND_BUF_ACTUAL` | BIGINT | Actual TCP send buffer bytes. |
| 25 | `SOCK_RECV_BUF_REQUESTED` | BIGINT | Requested TCP recv buffer bytes. |
| 26 | `SOCK_RECV_BUF_ACTUAL` | BIGINT | Actual TCP recv buffer bytes. |
| 27 | `PRIMARY_LOG_FILE` | VARCHAR(12) | Current log file on primary, e.g. `S0000123.LOG`. |
| 28 | `PRIMARY_LOG_PAGE` | BIGINT | Page within file. |
| 29 | `PRIMARY_LOG_POS` | BIGINT | **Byte LSN position on primary.** Monotonic; basis for send rate. |
| 30 | `PRIMARY_LOG_TIME` | TIMESTAMP | Timestamp of primary log position. |
| 31 | `STANDBY_LOG_FILE` | VARCHAR(12) | Current received log file on standby. |
| 32 | `STANDBY_LOG_PAGE` | BIGINT | Page. |
| 33 | `STANDBY_LOG_POS` | BIGINT | **Byte LSN received on standby.** Basis for recv rate. |
| 34 | `STANDBY_LOG_TIME` | TIMESTAMP | Timestamp of received position. |
| 35 | `HADR_LOG_GAP` | BIGINT | **Running-average gap (bytes) between primary & standby log positions.** Headline "behind by" byte metric. |
| 36 | `STANDBY_REPLAY_LOG_FILE` | VARCHAR(12) | Log file currently being replayed on standby. |
| 37 | `STANDBY_REPLAY_LOG_PAGE` | BIGINT | Page. |
| 38 | `STANDBY_REPLAY_LOG_POS` | BIGINT | **Byte LSN replayed on standby.** |
| 39 | `STANDBY_REPLAY_LOG_TIME` | TIMESTAMP | Timestamp of replay position. (Used with `PRIMARY_LOG_TIME` to derive *time* lag.) |
| 40 | `STANDBY_RECV_REPLAY_GAP` | BIGINT | **Bytes received but not yet replayed (recv pos − replay pos).** Replay backlog. |
| 41 | `STANDBY_REPLAY_DELAY` | BIGINT | Configured replay delay (seconds) — NOT lag, it's `HADR_REPLAY_DELAY` cfg. |
| 42 | `STANDBY_RECV_BUF_SIZE` | BIGINT | Standby receive buffer size (pages). |
| 43 | `STANDBY_RECV_BUF_PERCENT` | DOUBLE | **% of recv buffer full.** Congestion indicator. |
| 44 | `STANDBY_SPOOL_LIMIT` | BIGINT | Spool limit (4KB pages); -1=unlimited via AUTOMATIC, 0=off. |
| 45 | `STANDBY_SPOOL_PERCENT` | DOUBLE | **% of spool used.** Congestion indicator. NULL when spool limit 0. |
| 46 | `PEER_WINDOW` | BIGINT | Peer window duration (seconds). |
| 47 | `PEER_WINDOW_END` | TIMESTAMP | When current peer window expires. |
| 48 | `TAKEOVER_APP_REMAINING_PRIMARY` | BIGINT | Apps remaining to force on primary during takeover. |
| 49 | `TAKEOVER_APP_REMAINING_STANDBY` | BIGINT | Apps remaining on standby during takeover. |
| 50 | `READS_ON_STANDBY_ENABLED` | CHAR(1) | Y/N — Reads on Standby feature. |
| 51 | `STANDBY_REPLAY_ONLY_WINDOW_ACTIVE` | CHAR(1) | Y/N — RoS replay-only window active (blocks reader connections). |
| 52 | `STANDBY_REPLAY_ONLY_WINDOW_START` | TIMESTAMP | Start of replay-only window. |
| 53 | `STANDBY_REPLAY_ONLY_WINDOW_TRAN_COUNT` | BIGINT | Tx count in replay-only window. |
| 54 | `HEARTBEAT_MISSED` | INTEGER | **Heartbeats missed in current interval.** |
| 55 | `HEARTBEAT_EXPECTED` | INTEGER | **Heartbeats expected in current interval.** (missed/expected = health ratio.) |
| 56 | `STANDBY_ERROR_TIME` | TIMESTAMP | Time of last standby replay error (NULL if none). |
| 57 | `HADR_LAST_TAKEOVER_TIME` | TIMESTAMP | Timestamp of last takeover. |

Notes:
- On the **standby** member, `HADR_GET` returns 1 row describing itself vs the primary. On the **primary**, it returns one row per standby (multi-standby → up to 3 rows). In a multi-member (DPF/pureScale) topology `-1` aggregates per log stream — expect one row per (log stream × standby).
- `MON_GET_HADR` requires **DATAACCESS** or **DBADM** or **SQLADM** or **EXECUTE on the function** (same authority model as the other `MON_GET_*` functions the check already uses — see `code-ibm_db2-current.md:345-347`). Add `EXECUTE ON FUNCTION SYSPROC.MON_GET_HADR` to the read-only monitoring user grant list.

---

## 3. SECONDARY/LEGACY SOURCE — `SYSIBMADM.SNAPHADR` — 23-column schema (live 12.1.4)

`SELECT * FROM SYSIBMADM.SNAPHADR`. Verified live via `DESCRIBE`. IBM doc: https://www.ibm.com/docs/en/db2/12.1?topic=views-snaphadr-hadr-snapshot-administrative-view (snapshot admin view). **Prefer MON_GET_HADR**; SNAPHADR is a thinner, snapshot-monitor-based view kept for compatibility.

| Column | Type | Notes (vs MON_GET_HADR) |
|---|---|---|
| `SNAPSHOT_TIMESTAMP` | TIMESTAMP | snapshot time |
| `DB_NAME` | VARCHAR(128) | database name (MON_GET_HADR has no DB_NAME) |
| `HADR_ROLE` | VARCHAR(10) | = MON_GET_HADR.HADR_ROLE |
| `HADR_STATE` | VARCHAR(14) | = HADR_STATE |
| `HADR_SYNCMODE` | VARCHAR(10) | = HADR_SYNCMODE |
| `HADR_CONNECT_STATUS` | VARCHAR(12) | = HADR_CONNECT_STATUS |
| `HADR_CONNECT_TIME` | TIMESTAMP | ≈ HADR_CONNECT_STATUS_TIME |
| `HADR_HEARTBEAT` | INTEGER | # of missed heartbeats (≈ HEARTBEAT_MISSED) |
| `HADR_LOCAL_HOST` | VARCHAR(255) | local host |
| `HADR_LOCAL_SERVICE` | VARCHAR(40) | local TCP service |
| `HADR_REMOTE_HOST` | VARCHAR(255) | remote host |
| `HADR_REMOTE_SERVICE` | VARCHAR(40) | remote TCP service |
| `HADR_REMOTE_INSTANCE` | VARCHAR(128) | remote instance |
| `HADR_TIMEOUT` | BIGINT | = HADR_TIMEOUT |
| `HADR_PRIMARY_LOG_FILE` | VARCHAR(255) | ≈ PRIMARY_LOG_FILE |
| `HADR_PRIMARY_LOG_PAGE` | BIGINT | ≈ PRIMARY_LOG_PAGE |
| `HADR_PRIMARY_LOG_LSN` | BIGINT | ≈ PRIMARY_LOG_POS |
| `HADR_STANDBY_LOG_FILE` | VARCHAR(255) | ≈ STANDBY_LOG_FILE |
| `HADR_STANDBY_LOG_PAGE` | BIGINT | ≈ STANDBY_LOG_PAGE |
| `HADR_STANDBY_LOG_LSN` | BIGINT | ≈ STANDBY_LOG_POS |
| `HADR_LOG_GAP` | BIGINT | = HADR_LOG_GAP |
| `DBPARTITIONNUM` | SMALLINT | partition |
| `MEMBER` | SMALLINT | member |

SNAPHADR lacks: replay position, recv/replay gap, congestion wait counters (`LOG_HADR_WAIT*`), spool/recv-buffer %, peer window, takeover-remaining, RoS, heartbeat expected. **=> Do not build the metric set on SNAPHADR; it is insufficient for fidelity. Use MON_GET_HADR.**

---

## 4. MAPPING TABLE — proposed `ibm_db2.hadr.*` metrics

All from `MON_GET_HADR(-1)` unless noted. **Tags** (applied to every row's metrics): `db:<db>` (already global, `ibm_db2.py:48`); proposed new: `hadr_role:<HADR_ROLE>`, `standby_id:<STANDBY_ID>`, `log_stream:<LOG_STREAM_ID>`, `standby_host:<STANDBY_MEMBER_HOST>` (only on primary, to disambiguate multiple standbys), `member:<MEMBER>` (for MPP/pureScale). Keep cardinality low — `standby_host`/`standby_id` cardinality = number of standbys (≤3).

CSV `metric_type` vocabulary: `gauge` (point-in-time / DOUBLE %), `count` (submit as `monotonic_count` for lifetime cumulative counters). Db2 has no "rate" lifetime column here — send-rate must be derived agent-side OR exposed as the underlying `count`/`gauge` and rated in-app (`.as_rate()`).

### 4a. State / role / connectivity (gauge state-mapped)

| pg/mysql analog | Db2 source column (MON_GET_HADR) | proposed metric | type | unit | tags | notes / caveats |
|---|---|---|---|---|---|---|
| `mysql.replication.replica_running` (svc check); pg `wal_receiver.connected` | `HADR_STATE` → mapped int | `ibm_db2.hadr.state` | gauge | — | hadr_role, standby_id, log_stream | Map string→int and also emit string as a tag `hadr_state:<v>` so it's filterable. Suggested map: PEER=0(healthy), REMOTE_CATCHUP=1, REMOTE_CATCHUP_PENDING=2, LOCAL_CATCHUP=3, DISCONNECTED_PEER=4, DISCONNECTED=5. Better pattern (pg `wal_receiver`): emit `ibm_db2.hadr.state{hadr_state:peer}=1`. Recommend the pg style (value always 1, state as tag) for dashboards. |
| pg `wal_receiver.connected{status:...}` | `HADR_CONNECT_STATUS` | `ibm_db2.hadr.connected` | gauge | — | hadr_role, standby_id, connect_status:<v> | 1 always, tag `connect_status:connected\|disconnected\|congested`. **Congestion surfaces here.** Alert on `connect_status:congested`. |
| (role) | `HADR_ROLE` | `ibm_db2.hadr.role` | gauge | — | role:<primary\|standby\|standard> | Emit 1 with role tag. This is the ONE metric you may emit even when MON_GET_HADR has 0 rows (then read role from DB CFG `HADR database role` = STANDARD) so you always know "is HADR on". |
| (sync mode) | `HADR_SYNCMODE` | `ibm_db2.hadr.syncmode` | gauge | — | syncmode:<sync\|nearsync\|async\|superasync> | Emit 1 with syncmode tag. Config visibility. |
| `mysql.replication.replicas_connected`; pg (# rows in pg_stat_replication) | row count of `MON_GET_HADR` where HADR_ROLE=PRIMARY | `ibm_db2.hadr.standby.count` | gauge | — | (db only) | COUNT of standby rows on the primary. 0 when not primary / not configured. |

### 4b. Log gap / lag (the headline "how far behind")

| pg/mysql analog | Db2 source column | proposed metric | type | unit | tags | notes |
|---|---|---|---|---|---|---|
| `postgresql.replication_delay_bytes`; `mysql.replication.seconds_behind_source` (bytes-analog) | `HADR_LOG_GAP` | `ibm_db2.hadr.log_gap` | gauge | byte | hadr_role, standby_id, log_stream | **Headline lag metric.** Running average gap (primary pos − standby received pos), bytes. orientation -1. |
| `postgresql.replication.replay_lsn_delay` (bytes) | `STANDBY_RECV_REPLAY_GAP` | `ibm_db2.hadr.recv_replay_gap` | gauge | byte | hadr_role, standby_id | Bytes received but not yet replayed (replay backlog). orientation -1. |
| `postgresql.replication.sent_lsn_delay` (derive) | `PRIMARY_LOG_POS` − `STANDBY_LOG_POS` (agent-computed) | `ibm_db2.hadr.send_recv_gap` | gauge | byte | hadr_role, standby_id | Optional derived; `HADR_LOG_GAP` already covers this as a smoothed value. Include only if you want instantaneous (not running-avg). |
| `postgresql.replication.wal_replay_lag` (sec); `mysql.replication.seconds_behind_source` | derive: `PRIMARY_LOG_TIME` − `STANDBY_REPLAY_LOG_TIME` (epoch seconds) | `ibm_db2.hadr.replay_lag` | gauge | second | hadr_role, standby_id | **Time lag.** No single column; compute `(PRIMARY_LOG_TIME - STANDBY_REPLAY_LOG_TIME).total_seconds()`. Mirrors the check's existing `backup.latest` timestamp-delta pattern (`ibm_db2.py:176-181`). Clamp ≥0. orientation -1. |
| `postgresql.wal_receiver.last_msg_receipt_age` | `TIME_SINCE_LAST_RECV` | `ibm_db2.hadr.time_since_last_recv` | gauge | second | hadr_role, standby_id | Liveness; rises when partner silent. orientation -1. |

Log-position raw values (optional, for advanced LSN dashboards / agent-side rate via `.as_rate()`):

| Db2 column | proposed metric | type | unit | notes |
|---|---|---|---|---|
| `PRIMARY_LOG_POS` | `ibm_db2.hadr.primary_log_pos` | gauge | byte | Monotonic-ish LSN. Emit as gauge (it can jump on log archive). For "send rate" use `.as_rate()` in-app. |
| `STANDBY_LOG_POS` | `ibm_db2.hadr.standby_log_pos` | gauge | byte | Received LSN. `.as_rate()` = recv rate. |
| `STANDBY_REPLAY_LOG_POS` | `ibm_db2.hadr.standby_replay_log_pos` | gauge | byte | Replayed LSN. `.as_rate()` = replay rate. |
| `PRIMARY_LOG_PAGE` / `STANDBY_LOG_PAGE` / `STANDBY_REPLAY_LOG_PAGE` | (skip) | — | — | Redundant with POS; skip unless requested. |

> **Send/recv "rate" caveat (category explicitly asks for send/recv rate):** Db2's `MON_GET_HADR` exposes **positions, not rates**. There is NO `*_BYTES_SENT_PER_SEC` column. Two valid implementations: (a) emit `primary_log_pos`/`standby_log_pos` as gauges and let Datadog `.as_rate()` derive bytes/sec on the dashboard (simplest, recommended); or (b) keep prior-run positions in the check (like mysql's qcache delta pattern, `code-mysql-metrics.md:103`) and submit `ibm_db2.hadr.log_send_rate` / `.log_recv_rate` as gauge bytes/sec. Recommend (a) — no state to manage and matches pg's LSN-delta philosophy.

### 4c. Congestion (HADR-only — no pg/mysql analog)

This is the "congestion (HADR-only)" sub-item explicitly named in the category. No postgres/mysql equivalent exists; these are Db2-native and worth adding.

| Db2 source column | proposed metric | type | unit | tags | notes |
|---|---|---|---|---|---|
| `LOG_HADR_WAITS_TOTAL` | `ibm_db2.hadr.log_wait.count` | count | — | hadr_role, standby_id | Cumulative count of log writes that waited on HADR. monotonic_count. Rising fast = congestion. |
| `LOG_HADR_WAIT_TIME` | `ibm_db2.hadr.log_wait.time` | count | millisecond | hadr_role, standby_id | Cumulative ms log writers waited on HADR. monotonic_count. (avg wait = `.time / .count` in-app, mirrors `lock.wait` pattern.) |
| `LOG_HADR_WAIT_CUR` | `ibm_db2.hadr.log_wait.current` | gauge | second | hadr_role, standby_id | Seconds the *current* log write has been blocked on HADR. Spikes during congestion. orientation -1. |
| `STANDBY_RECV_BUF_PERCENT` | `ibm_db2.hadr.standby_recv_buf_percent` | gauge | percent | hadr_role, standby_id | DOUBLE 0-100. High = standby can't drain recv buffer fast enough. orientation -1. |
| `STANDBY_SPOOL_PERCENT` | `ibm_db2.hadr.standby_spool_percent` | gauge | percent | hadr_role, standby_id | DOUBLE; NULL when spool off (skip metric if NULL). High = spooling to disk. orientation -1. |
| `STANDBY_RECV_BUF_SIZE` | `ibm_db2.hadr.standby_recv_buf_size` | gauge | page | hadr_role, standby_id | Recv buffer size (pages). Context for the percent. |
| `STANDBY_SPOOL_LIMIT` | `ibm_db2.hadr.standby_spool_limit` | gauge | page | hadr_role, standby_id | Spool limit (4KB pages); -1=unlimited. Context for percent. |
| `SOCK_SEND_BUF_ACTUAL` | `ibm_db2.hadr.sock_send_buf` | gauge | byte | hadr_role, standby_id | TCP send buffer (actual). Tuning visibility. Low priority. |
| `SOCK_RECV_BUF_ACTUAL` | `ibm_db2.hadr.sock_recv_buf` | gauge | byte | hadr_role, standby_id | TCP recv buffer (actual). Low priority. |

> `HADR_FLAGS` (VARCHAR) can include `STANDBY_RECV_BLOCKED` — consider emitting `ibm_db2.hadr.recv_blocked` (gauge 0/1) by string-matching the flag, as a clean congestion boolean. Low priority / optional.

### 4d. Heartbeat / health

| Db2 source column | proposed metric | type | unit | tags | notes |
|---|---|---|---|---|---|
| `HEARTBEAT_MISSED` | `ibm_db2.hadr.heartbeat.missed` | gauge | — | hadr_role, standby_id | Heartbeats missed this interval. orientation -1. |
| `HEARTBEAT_EXPECTED` | `ibm_db2.hadr.heartbeat.expected` | gauge | — | hadr_role, standby_id | Heartbeats expected this interval. (missed/expected ratio → alert.) |
| `HEARTBEAT_INTERVAL` | `ibm_db2.hadr.heartbeat.interval` | gauge | second | hadr_role, standby_id | Config visibility. Low priority. |
| `HADR_TIMEOUT` | `ibm_db2.hadr.timeout` | gauge | second | hadr_role, standby_id | Config visibility. Low priority. |

### 4e. Peer window / takeover

| Db2 source column | proposed metric | type | unit | tags | notes |
|---|---|---|---|---|---|
| `PEER_WINDOW` | `ibm_db2.hadr.peer_window` | gauge | second | hadr_role, standby_id | Peer window duration (config). |
| `PEER_WINDOW_END` − now | `ibm_db2.hadr.peer_window_remaining` | gauge | second | hadr_role, standby_id | Derived: `(PEER_WINDOW_END - current timestamp).total_seconds()`, clamp ≥0. Time until safety window closes. Optional. |
| `TAKEOVER_APP_REMAINING_PRIMARY` | `ibm_db2.hadr.takeover_app_remaining.primary` | gauge | — | hadr_role, standby_id | Apps to force during takeover (0 except during takeover). Optional. |
| `TAKEOVER_APP_REMAINING_STANDBY` | `ibm_db2.hadr.takeover_app_remaining.standby` | gauge | — | hadr_role, standby_id | Optional. |
| `STANDBY_REPLAY_ONLY_WINDOW_TRAN_COUNT` | `ibm_db2.hadr.replay_only_window.tran_count` | gauge | transaction | hadr_role, standby_id | Reads-on-Standby: tx in replay-only window (blocks readers). Optional. |

### 4f. Recommended minimal vs full set
- **Minimal (ship first):** `hadr.role`, `hadr.state` (state-as-tag style), `hadr.connected` (connect_status-as-tag), `hadr.standby.count`, `hadr.log_gap`, `hadr.recv_replay_gap`, `hadr.replay_lag`, `hadr.time_since_last_recv`, `hadr.log_wait.count`, `hadr.log_wait.time`, `hadr.standby_recv_buf_percent`, `hadr.standby_spool_percent`, `hadr.heartbeat.missed`. (13 metrics — directly maps to pg/mysql intent + Db2 congestion.)
- **Full:** add log positions, sock buffers, heartbeat interval/timeout, peer window, takeover remaining, RoS — ~28 metrics total.

---

## 5. pg/mysql metrics with NO Db2 (HADR) equivalent — flag these

| pg/mysql metric | Why no Db2 HADR analog |
|---|---|
| `postgresql.replication_slot.*` (xmin_age, restart/confirmed_flush delay, spill/stream counters) | Db2 HADR has no "replication slot" concept (no logical decoding consumers). Closest is spool (`STANDBY_SPOOL_*`), already mapped. **No mapping for slots.** |
| `postgresql.subscription.*` (logical subscriptions) | Db2 HADR is physical log shipping, not logical pub/sub. The Db2 product for logical is **SQL Replication / Q Replication** (separate product, `IBMSNAP_*` tables) — out of scope for this integration. **No mapping.** |
| `postgresql.recovery_prefetch.*` | pg WAL-replay prefetcher internals; Db2 replay has no equivalent exposed counter. **No mapping.** |
| `postgresql.archiver.archived_count` / `.failed_count` | WAL archiving to a file archive. Db2 log archiving exists (`LOGARCHMETH1`) but is exposed via `MON_GET_TRANSACTION_LOG` / db cfg, NOT HADR. Belongs in a "transaction log / archiving" category, not HADR. **No HADR mapping** (note for the log-category map). |
| `postgresql.wal.*` (bytes/records/fpi/buffers_full/write_time...) | WAL generation stats. Db2 analog is `MON_GET_TRANSACTION_LOG` (LOG_WRITES, LOG_WRITE_TIME, NUM_LOG_DATA_FOUND_IN_BUFFER, CUR_COMMIT_DISK_LOG_READS — all confirmed present live, §6) — belongs in the **transaction-log** category, not HADR. **No HADR mapping.** |
| `postgresql.wal_age` / `wal_count` / `wal_size` | On-disk WAL file inventory; Db2 equivalent is log-path filesystem, not HADR. **No HADR mapping.** |
| `mysql.replication.group.*` (Galera/Group Replication: transactions_applied/checked/proposed/rollback/validating, conflicts_detected, member_status) | Db2 HADR is single-primary log shipping, NOT multi-primary certification-based replication. No conflict detection, no group consensus. **No mapping.** (Db2 pureScale ≠ this either — pureScale is shared-disk, not log replication.) |
| `mysql.replication.seconds_behind_master/source` (single sec value) | Partially mapped via derived `ibm_db2.hadr.replay_lag` (computed from log timestamps) — not a native single column. Flag: our lag is *derived*, pg/mysql expose it directly. |

---

## 6. Db2-native HADR-adjacent metrics worth adding (already mapped above, summarized)
These have NO pg/mysql analog but are valuable:
- **Congestion suite** (§4c): `log_wait.count/time/current`, `standby_recv_buf_percent`, `standby_spool_percent`. Db2's congestion model (synchronous log-write blocking on the standby) is unique and is the #1 HADR ops concern — no pg/mysql equivalent.
- **Heartbeat missed/expected** (§4d): finer-grained than pg's `last_msg_receipt_age`.
- **Peer window** (§4e): Db2-specific safety-window concept for guaranteed-zero-data-loss.
- **Takeover-remaining** (§4e): failover progress, Db2-specific.
- **Reads-on-Standby replay-only window** (§4e): Db2-specific feature interaction.

Transaction-log throughput columns that pair with HADR (live-confirmed present in `MON_GET_TRANSACTION_LOG(-1)` on 12.1.4: `CUR_COMMIT_DISK_LOG_READS`, `LOG_WRITE_TIME`, `LOG_READ_TIME`, `NUM_LOG_DATA_FOUND_IN_BUFFER`, `LOG_WRITES`, `LOG_READS`) belong to the **transaction-log** category map, not here, but the HADR replay-lag story is incomplete without them — cross-reference in the implementation plan.

---

## 7. Implementation notes (for the coding agent)

1. **New collector method** `query_hadr` mirroring the existing `query_*` pattern in `/home/bits/dd/integrations-core/ibm_db2/datadog_checks/ibm_db2/ibm_db2.py` (the five existing methods, `ibm_db2.py:67-74`). Add to `self._query_methods`. Add SQL constant to `/home/bits/dd/integrations-core/ibm_db2/datadog_checks/ibm_db2/queries.py` following the column-tuple convention there.
2. **SQL:** `SELECT hadr_role, replay_type, hadr_syncmode, standby_id, log_stream_id, hadr_state, hadr_flags, standby_member_host, hadr_connect_status, time_since_last_recv, log_hadr_wait_cur, log_hadr_wait_time, log_hadr_waits_total, sock_send_buf_actual, sock_recv_buf_actual, primary_log_pos, primary_log_time, standby_log_pos, standby_replay_log_pos, standby_replay_log_time, hadr_log_gap, standby_recv_replay_gap, standby_recv_buf_size, standby_recv_buf_percent, standby_spool_limit, standby_spool_percent, peer_window, peer_window_end, takeover_app_remaining_primary, takeover_app_remaining_standby, standby_replay_only_window_tran_count, heartbeat_interval, hadr_timeout, heartbeat_missed, heartbeat_expected, member, current timestamp AS current_time FROM TABLE(MON_GET_HADR(-1))`. (Include `current timestamp AS current_time` for the replay_lag/peer_window_remaining derivations, exactly as `query_database` does for backup age — `ibm_db2.py` SQL in `queries.py:20-40`.)
3. **0-row handling:** if the cursor yields no rows, read `HADR database role` from DB CFG (or `MON_GET_HADR` returning empty) → emit only `ibm_db2.hadr.role{role:standard}=1` (or nothing). Never error. Wrap in the same try/except-and-warn the orchestrator already provides (`ibm_db2.py:82-90`).
4. **Authority:** add `GRANT EXECUTE ON FUNCTION SYSPROC.MON_GET_HADR TO <user>` to README setup (`/home/bits/dd/integrations-core/ibm_db2/README.md:58-106`). Degrade gracefully on SQL0551N (no authority) — log warning, skip (the orchestrator already swallows per-method exceptions).
5. **Timestamp deltas:** `MON_GET_HADR` timestamps come back as Python `datetime` via `ibm_db.fetch_assoc` (same as `last_backup` today, `ibm_db2.py:176-181`). Compute `(current_time - standby_replay_log_time).total_seconds()` for `replay_lag`. Guard NULLs (standby-only fields are NULL/blank on a primary's self row and vice-versa).
6. **Service check (recommended, pg/mysql parity):** add `ibm_db2.hadr.status` service check derived from `HADR_STATE`+`HADR_CONNECT_STATUS`: OK when `PEER`/`CONNECTED`, WARNING on `REMOTE_CATCHUP*`/`CONGESTED`, CRITICAL on `DISCONNECTED`/`DISCONNECTED_PEER`. Mirrors `mysql.replication.replica_running` and `ibm_db2.status` existing pattern (`utils.py:13-24`). Register in `assets/service_checks.json`.
7. **metadata.csv:** add one row per emitted metric to `/home/bits/dd/integrations-core/ibm_db2/metadata.csv`, `integration=ibm_db2`, units per §4, orientation -1 for gap/lag/wait/missed metrics, 0 for positions/counts/config.
8. **Tag cardinality:** `standby_id`/`standby_host` ≤ 3; `log_stream`/`member` = member count (DPF/pureScale). All bounded — safe. Do NOT tag by `hadr_state`/`connect_status` value on the gauge metrics (use state-as-value or state-as-tag-on-a-status-metric, not both on every metric) to avoid metric churn when state flaps.

---

## 8. Source citations
- Live schema (authoritative for 12.1.4): `DESCRIBE SELECT * FROM TABLE(MON_GET_HADR(-1))` and `DESCRIBE SELECT * FROM SYSIBMADM.SNAPHADR` run on container `db2-primary` (`icr.io/db2_community/db2:12.1.4.0`), db `TESTDB`, 2026-06-15. `SELECT count(*) FROM TABLE(MON_GET_HADR(-1))` = 0 (role STANDARD, HADR not configured).
- Existing integration code: `/home/bits/dd/integrations-core/ibm_db2/datadog_checks/ibm_db2/ibm_db2.py`, `/home/bits/dd/integrations-core/ibm_db2/datadog_checks/ibm_db2/queries.py`, `/home/bits/dd/integrations-core/ibm_db2/datadog_checks/ibm_db2/utils.py`, `/home/bits/dd/integrations-core/ibm_db2/metadata.csv`.
- Gap audit: `/home/bits/dd/integrations-core/ibm_db2/dev-docs/db2-fidelity-plan/_research/code-ibm_db2-current.md:366,372-373`.
- postgres replication: `/home/bits/dd/integrations-core/postgres/datadog_checks/postgres/util.py:646-799`, `/home/bits/dd/integrations-core/postgres/metadata.csv:141-162,240-245`.
- mysql replication: `/home/bits/dd/integrations-core/mysql/metadata.csv:242-255`; collection refs `/home/bits/dd/integrations-core/ibm_db2/dev-docs/db2-fidelity-plan/_research/code-mysql-metrics.md:100-101`.
- IBM docs: `MON_GET_HADR` table function (12.1 KC) https://www.ibm.com/docs/en/db2/12.1?topic=functions-mon-get-hadr-returns-high-availability-disaster ; `SNAPHADR` admin view https://www.ibm.com/docs/en/db2/12.1?topic=views-snaphadr-hadr-snapshot-administrative-view ; HADR monitor elements / `HADR_STATE`/`HADR_CONNECT_STATUS` value lists https://www.ibm.com/docs/en/db2/12.1?topic=elements-monitor .

> NOTE TO ORCHESTRATOR: several research files named in the kickoff prompt (`code-postgres-metrics.md`, `db2-monget-catalog-1..3.md`, `db2-sysibmadm-views.md`, `db2-live-monget.md`, `db2-live-sysibmadm.md`) **do not exist** in `_research/` as of this run — only `code-ibm_db2-current.md`, `code-mysql-metrics.md`, the `code-*` framework files, and `db2-live-{activity,pkgcache}.md` / `db2-config-settings.md` are present. I substituted by reading the existing files plus the three `metadata.csv` files and by querying the live `db2-primary` 12.1.4 container directly for exact MON_GET_HADR / SNAPHADR schemas. The schemas above are therefore live-verified, not transcribed from a catalog file.
