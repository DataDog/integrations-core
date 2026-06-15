# Map: Locking & Concurrency — ibm_db2 fidelity plan

Maps the **locking / concurrency** metric category (locks held, locks waiting, lock-wait
time, deadlocks, lock timeouts, lock escalations, and live blocking/lock-wait detail) from
the postgres + mysql integrations onto Db2 12.1 monitoring sources, and proposes
`ibm_db2.*` metrics to reach parity.

Server under test: **DB2/LINUXX8664 12.1.4.0** (`_raw/01-version-and-monget-functions.txt:4`).

Sources read for this map:
- pg metrics arch: `/home/bits/dd/integrations-core/ibm_db2/dev-docs/db2-fidelity-plan/_research/code-postgres-metrics.md`
- mysql metrics arch: `.../_research/code-mysql-metrics.md`
- Db2 MON_GET catalog: `.../_research/db2-monget-catalog-2.md`
- live DESCRIBE dumps: `.../_research/_raw/02-monget-key-columns.txt`
- live function inventory: `.../_research/_raw/01-version-and-monget-functions.txt`
- live SYSIBMADM view inventory: `.../_research/_raw/03-sysibmadm-objects.txt`
- live monitor-switch config: `.../_research/_raw/04-monitor-config.txt`
- pg metric catalog: `/home/bits/dd/integrations-core/postgres/metadata.csv`
- mysql metric catalog: `/home/bits/dd/integrations-core/mysql/metadata.csv`
- ibm_db2 metric catalog: `/home/bits/dd/integrations-core/ibm_db2/metadata.csv`
- existing ibm_db2 code: `/home/bits/dd/integrations-core/ibm_db2/datadog_checks/ibm_db2/queries.py`,
  `.../ibm_db2.py`

NOTE: `db2-monget-catalog-1.md`, `db2-monget-catalog-3.md`, and `db2-sysibmadm-views.md`
named in the task prompt do **not exist** in `_research/`; equivalent content was sourced
from `db2-monget-catalog-2.md`, the raw DESCRIBE dump, and the SYSIBMADM inventory.

---

## 0. Executive summary

- Db2 has **first-class, dedicated** locking metrics. The integration already emits 7 lock
  metrics (`ibm_db2.lock.*`) from `MON_GET_DATABASE` — see `ibm_db2.py:152-173`. Db2 is
  actually **richer than postgres/mysql** here: it natively exposes lock-wait *time*,
  lock-timeout *count*, and lock-*escalation* counters that postgres/mysql do not have as
  built-in metrics.
- The biggest fidelity gaps vs. pg/mysql are **(a)** the current `lock.wait` is collected as
  an in-check-computed *average* (`lock_wait_time/lock_waits`) and **destroys** the raw
  cumulative counters (postgres/mysql keep raw counters); **(b)** no lock-escalation metric
  despite the column being available; **(c)** no per-connection / per-table / per-workload
  lock dimensioning; **(d)** no live blocking-tree (`MON_GET_LOCKS` / `MON_GET_APPL_LOCKWAIT`
  / `SYSIBMADM.MON_LOCKWAITS`) which is the analog of mysql's blocking detection and pg's
  `pg_locks` + idle-in-transaction lock age.
- All locking columns used below are **confirmed live** in the DESCRIBE dump:
  `MON_GET_DATABASE` (`_raw/02-monget-key-columns.txt:31-33,61,80-83,151-158`),
  `MON_GET_CONNECTION` (`:1071,1090-1098,1160-1165,1271-1273`),
  `MON_GET_TABLE` (`:1547-1556`), `MON_GET_SERVICE_SUBCLASS` (`:1713,1732-1735,1803-1808`),
  `MON_GET_WORKLOAD` (`:2097,2116-2119,2185-2190`).
- `MON_GET_LOCKS`, `MON_GET_APPL_LOCKWAIT`, `MON_GET_EXTENDED_LATCH_WAIT` are **confirmed
  present** as functions (`_raw/01...txt:16,28,38`) but their column lists are **NOT** in the
  DESCRIBE dump — column names below for those are "(general Db2 12.1 knowledge — verify with
  a live DESCRIBE before coding)". SYSIBMADM `MON_LOCKWAITS` / `LOCKWAITS` / `LOCKS_HELD`
  views are confirmed present (`_raw/03-sysibmadm-objects.txt:35,36,44`).

---

## 1. Conceptual analog table (pg/mysql concept → Db2 element)

| pg/mysql concept | pg metric | mysql metric | Db2 monitor element | Db2 source |
|---|---|---|---|---|
| Deadlocks (cumulative) | `postgresql.deadlocks` (rate), `postgresql.deadlocks.count` (count) | `mysql.innodb.deadlocks` (count) | `DEADLOCKS` | `MON_GET_DATABASE`/`_CONNECTION`/`_SERVICE_SUBCLASS`/`_WORKLOAD` |
| Locks currently held | (none built-in; `pg_locks` count via `relations`) | `mysql.innodb.lock_structs` (gauge, approx) | `NUM_LOCKS_HELD` | `MON_GET_DATABASE`, `MON_GET_CONNECTION` |
| Lock waiters (current) | `pg_locks` granted=false count | `mysql.innodb.row_lock_current_waits` | `NUM_LOCKS_WAITING` | `MON_GET_DATABASE`, `MON_GET_CONNECTION` |
| Lock-wait time (cumulative) | (none; only idle-tx age, DBM) | `mysql.innodb.row_lock_time` (gauge), `mysql.queries.lock_time` (count, DBM) | `LOCK_WAIT_TIME` (ms) | `MON_GET_DATABASE`/`_CONNECTION`/`_TABLE`/`_SERVICE_SUBCLASS`/`_WORKLOAD` |
| Lock-wait count (cumulative) | (none) | `mysql.innodb.row_lock_waits` (gauge) | `LOCK_WAITS` | same set as above |
| Lock timeouts | (none; `conflicts.lock` = standby cancels only) | (none) | `LOCK_TIMEOUTS` | `MON_GET_DATABASE`/`_CONNECTION`/`_SERVICE_SUBCLASS`/`_WORKLOAD` |
| Lock-list memory in use | (none) | `mysql.innodb.mem_lock_system` (gauge, from text) | `LOCK_LIST_IN_USE` (bytes) | `MON_GET_DATABASE` |
| Lock escalations | (none) | (none) | `LOCK_ESCALS` (+ `_MAXLOCKS`/`_LOCKLIST`/`_GLOBAL`) | `MON_GET_DATABASE`/`_CONNECTION`/`_SERVICE_SUBCLASS`/`_WORKLOAD` |
| Table-lock waits | (none) | `mysql.performance.table_locks_waited` / `_immediate` (gauge) | `LOCK_WAITS` / `LOCK_WAIT_TIME` per-table | `MON_GET_TABLE` |
| Live blocking / waiters detail | `pg_locks` join (relations `LOCK_METRICS`), `locks.idle_in_transaction_age` (DBM) | blocking via lock tables (DBM samples) | rows of `MON_GET_LOCKS`, `MON_GET_APPL_LOCKWAIT`, `SYSIBMADM.MON_LOCKWAITS` | dedicated lock functions/views |
| Lock-wait event time (wait-event family) | `postgresql.activity.wait_event` (count by event) | `mysql.performance.wait_event.*` (DBM) | `LOCK_WAIT_TIME`/`LOCK_WAITS` as a wait-time component of `TOTAL_WAIT_TIME` | `MON_GET_SERVICE_SUBCLASS` / `_WORKLOAD` |

Key fidelity observation: **Db2's native locking counters are a superset of pg+mysql.**
The opposite-direction gaps (pg/mysql metrics with no Db2 analog) are small and listed in §7.

---

## 2. MAIN MAPPING TABLE — instance/db-level locking (highest priority)

Source: `MON_GET_DATABASE(-1)` (already queried; `queries.py:21-40`). All columns below are
in the live DESCRIBE dump at `_raw/02-monget-key-columns.txt`. `-1` = current member; use
`-2` to fan out per member and tag `member` (pureScale/DPF) — current code uses `-1`.

Column units (Db2 convention, `db2-monget-catalog-2.md:26-31`): `*_TIME` = **milliseconds**,
counts are monotonic since DB activation, `LOCK_LIST_IN_USE` = **bytes**.

| pg/mysql analog | Db2 source: fn + exact column | proposed `ibm_db2.<name>` | type | unit | tags | notes / version-gating |
|---|---|---|---|---|---|---|
| `postgresql.deadlocks.count` / `mysql.innodb.deadlocks` | `MON_GET_DATABASE.DEADLOCKS` (`:61`) | `ibm_db2.lock.dead` *(EXISTING)* | monotonic_count | lock | `db`,`member` | already emitted `ibm_db2.py:152`. Keep. |
| `postgresql.deadlocks` (rate) | same `DEADLOCKS` | `ibm_db2.lock.deadlocks.rate` *(NEW, optional)* | rate | lock/s | `db`,`member` | rate convenience; pg ships both rate+count. Low priority — agent can rate a count. |
| (no pg/mysql counter) | `MON_GET_DATABASE.LOCK_TIMEOUTS` (`:81`) | `ibm_db2.lock.timeouts` *(EXISTING)* | monotonic_count | lock | `db`,`member` | already emitted `ibm_db2.py:155`. Keep. Db2-native, no pg/mysql analog. |
| `pg_locks` held count / `mysql.innodb.lock_structs` | `MON_GET_DATABASE.NUM_LOCKS_HELD` (`:31`) | `ibm_db2.lock.active` *(EXISTING)* | gauge | lock | `db`,`member` | already emitted `ibm_db2.py:158`. Keep. |
| `mysql.innodb.row_lock_current_waits` / `pg_locks granted=f` | `MON_GET_DATABASE.NUM_LOCKS_WAITING` (`:32`) | `ibm_db2.lock.waiting` *(EXISTING)* | gauge | lock | `db`,`member` | already emitted `ibm_db2.py:161`. Keep. (Agents/locks waiting.) |
| `mysql.innodb.row_lock_time` (avg flavor) | `MON_GET_DATABASE.LOCK_WAIT_TIME` / `LOCK_WAITS` (`:82-83`) | `ibm_db2.lock.wait` *(EXISTING — see fix)* | gauge | millisecond | `db`,`member` | currently computed in-check as `lock_wait_time/lock_waits` avg (`ibm_db2.py:165-169`). **FIX**: also emit the raw cumulative counters (next two rows) — the average alone is lossy and not delta-able. |
| `mysql.queries.lock_time` (cumulative) | `MON_GET_DATABASE.LOCK_WAIT_TIME` (`:82`) | `ibm_db2.lock.wait_time` *(NEW)* | monotonic_count | millisecond | `db`,`member` | raw cumulative lock-wait time. Closest analog to mysql's cumulative lock_time. **Add.** |
| `mysql.innodb.row_lock_waits` (cumulative) | `MON_GET_DATABASE.LOCK_WAITS` (`:83`) | `ibm_db2.lock.waits` *(NEW)* | monotonic_count | lock | `db`,`member` | raw cumulative count of lock waits. **Add.** Enables computing avg in DD instead of the check. |
| `mysql.innodb.mem_lock_system` | `MON_GET_DATABASE.LOCK_LIST_IN_USE` (`:33`) | `ibm_db2.lock.pages` *(EXISTING)* | gauge | page | `db`,`member` | already emitted as bytes/4096 → 4KiB pages (`ibm_db2.py:173`). Keep. Consider also raw bytes (`ibm_db2.lock.memory.used`, gauge, byte) for clarity. |
| (no pg/mysql analog) | `MON_GET_DATABASE.LOCK_ESCALS` (`:80`) | `ibm_db2.lock.escalations` *(NEW)* | monotonic_count | lock | `db`,`member` | lock escalations = row→table lock promotions; key Db2 health signal (LOCKLIST/MAXLOCKS pressure). **Add.** Db2-native. |
| (no analog) | `MON_GET_DATABASE.LOCK_ESCALS_MAXLOCKS` (`:154`) | `ibm_db2.lock.escalations.maxlocks` *(NEW, opt)* | monotonic_count | lock | `db`,`member` | escalations triggered by MAXLOCKS threshold. |
| (no analog) | `MON_GET_DATABASE.LOCK_ESCALS_LOCKLIST` (`:155`) | `ibm_db2.lock.escalations.locklist` *(NEW, opt)* | monotonic_count | lock | `db`,`member` | escalations triggered by LOCKLIST full. |
| (no analog) | `MON_GET_DATABASE.LOCK_ESCALS_GLOBAL` (`:156`) | `ibm_db2.lock.escalations.global` *(NEW, opt)* | monotonic_count | lock | `db`,`member` | pureScale global escalations; data-gate on non-zero (empty on single-node, see `db2-editions-versions.md:368-369` pattern). |
| (no analog) | `MON_GET_DATABASE.LOCK_WAITS_GLOBAL` (`:151`) | `ibm_db2.lock.waits.global` *(NEW, opt)* | monotonic_count | lock | `db`,`member` | pureScale CF lock waits; data-gate non-zero. |
| (no analog) | `MON_GET_DATABASE.LOCK_WAIT_TIME_GLOBAL` (`:152`) | `ibm_db2.lock.wait_time.global` *(NEW, opt)* | monotonic_count | millisecond | `db`,`member` | pureScale; data-gate non-zero. |
| (no analog) | `MON_GET_DATABASE.LOCK_TIMEOUTS_GLOBAL` (`:153`) | `ibm_db2.lock.timeouts.global` *(NEW, opt)* | monotonic_count | lock | `db`,`member` | pureScale; data-gate non-zero. |

Recommended **minimal parity additions** (priority order): `ibm_db2.lock.waits`,
`ibm_db2.lock.wait_time`, `ibm_db2.lock.escalations`. These three + keep-existing brings Db2
to "raw cumulative counters + escalations" which exceeds pg/mysql.

---

## 3. Per-CONNECTION lock attribution — `MON_GET_CONNECTION`

Source: `MON_GET_CONNECTION(NULL, -1)` — **not currently called for metrics** (the existing
check uses it nowhere for locks). Columns confirmed live: `DEADLOCKS` (`:1071`),
`LOCK_ESCALS` (`:1090`), `LOCK_TIMEOUTS` (`:1091`), `LOCK_WAIT_TIME` (`:1092`),
`LOCK_WAITS` (`:1093`), `NUM_LOCKS_HELD` (`:1098`), the `*_GLOBAL` family (`:1160-1165`),
plus per-connection config/state `LOCK_TIMEOUT_VAL` (`:1271`), `CURRENT_ISOLATION` (`:1272`),
`NUM_LOCKS_WAITING` (`:1273`). Identity columns: `APPLICATION_HANDLE` (`:1032`),
`APPLICATION_NAME` (`:1033`), `SESSION_AUTH_ID` (`:1045`), `CLIENT_WRKSTNNAME` (`:1036`).

This is the analog of mysql's `QUERY_USER_CONNECTIONS` (per user/host) and pg's per-pid
`pg_locks`. **High cardinality** — gate behind a config flag and top-N, mirroring mysql
`extra_status_metrics` / index `limit` pattern (`code-mysql-metrics.md:171,264`).

| pg/mysql analog | Db2 source: column | proposed `ibm_db2.<name>` | type | unit | tags | notes |
|---|---|---|---|---|---|---|
| `mysql.performance.user_connections` (per user) | `MON_GET_CONNECTION` row count | `ibm_db2.connection.locks_held` *(NEW)* | gauge | lock | `application_name`,`session_auth_id`,`member` | per-conn `NUM_LOCKS_HELD` (`:1098`). |
| `mysql.innodb.row_lock_current_waits` (attributed) | `NUM_LOCKS_WAITING` (`:1273`) | `ibm_db2.connection.locks_waiting` *(NEW)* | gauge | lock | `application_name`,`session_auth_id`,`member` | who is waiting now. |
| `mysql.queries.lock_time` (per session) | `LOCK_WAIT_TIME` (`:1092`) | `ibm_db2.connection.lock_wait_time` *(NEW)* | monotonic_count | millisecond | `application_name`,`session_auth_id`,`member` | cumulative per-conn. |
| (none) | `LOCK_WAITS` (`:1093`) | `ibm_db2.connection.lock_waits` *(NEW)* | monotonic_count | lock | `application_name`,`session_auth_id`,`member` | |
| `mysql.innodb.deadlocks` (attributed) | `DEADLOCKS` (`:1071`) | `ibm_db2.connection.deadlocks` *(NEW)* | monotonic_count | lock | `application_name`,`session_auth_id`,`member` | |
| (none) | `LOCK_TIMEOUTS` (`:1091`) | `ibm_db2.connection.lock_timeouts` *(NEW)* | monotonic_count | lock | `application_name`,`session_auth_id`,`member` | |
| (none) | `LOCK_ESCALS` (`:1090`) | `ibm_db2.connection.lock_escalations` *(NEW)* | monotonic_count | lock | `application_name`,`session_auth_id`,`member` | |

`LOCK_TIMEOUT_VAL` (`:1271`, ms; -1=infinite) and `CURRENT_ISOLATION` (`:1272`, CHAR(2):
`CS`/`RS`/`RR`/`UR`) are good **tags or service-config metrics**, not counters. Consider
`CURRENT_ISOLATION` as a tag on per-connection lock metrics to show isolation-level impact.

Cardinality control: aggregate to top-N connections by `LOCK_WAIT_TIME` (or by
`NUM_LOCKS_WAITING` for "current blocking"), `FETCH FIRST n ROWS ONLY`. Default OFF; enable
via a `collect_connection_lock_metrics` config flag (mirrors pg `dbm`/`relations` gating
discipline, `code-postgres-metrics.md:415-434`).

---

## 4. Per-TABLE lock contention — `MON_GET_TABLE`

Source: `MON_GET_TABLE(NULL, NULL, -1)` — **not currently called**. This is the direct
analog of mysql `table_locks_waited`, but per-table instead of server-wide. Confirmed live
lock columns: `LOCK_WAIT_TIME` (`:1547`), `LOCK_WAIT_TIME_GLOBAL` (`:1548`),
`LOCK_WAITS` (`:1549`), `LOCK_WAITS_GLOBAL` (`:1550`), `LOCK_ESCALS` (`:1551`),
`LOCK_ESCALS_GLOBAL` (`:1552`), plus `DATA_SHARING_REMOTE_LOCKWAIT_COUNT/_TIME`
(`:1555-1556`, pureScale). Identity: `TABSCHEMA`, `TABNAME`, `MEMBER`
(`db2-monget-catalog-2.md:62-64`). Populated under live `mon_obj_metrics=EXTENDED`
(`_raw/04-monitor-config.txt:16`, sufficient — see `db2-monget-catalog-2.md:42-44`).

| pg/mysql analog | Db2 source: column | proposed `ibm_db2.<name>` | type | unit | tags | notes |
|---|---|---|---|---|---|---|
| `mysql.performance.table_locks_waited` (per-table) | `MON_GET_TABLE.LOCK_WAITS` (`:1549`) | `ibm_db2.table.lock_waits` *(NEW)* | monotonic_count | lock | `tabschema`,`tabname`,`member` | hot/contended tables. |
| (none, per-table wait time) | `MON_GET_TABLE.LOCK_WAIT_TIME` (`:1547`) | `ibm_db2.table.lock_wait_time` *(NEW)* | monotonic_count | millisecond | `tabschema`,`tabname`,`member` | |
| (none) | `MON_GET_TABLE.LOCK_ESCALS` (`:1551`) | `ibm_db2.table.lock_escalations` *(NEW)* | monotonic_count | lock | `tabschema`,`tabname`,`member` | which table triggers escalations. |

Cardinality control: identical to per-table metrics elsewhere — top-N by `LOCK_WAIT_TIME`,
schema allowlist/denylist (exclude `SYS*`), `FETCH FIRST n ROWS ONLY`, gated by a config
flag like pg's `relations` (`code-postgres-metrics.md:351-385`). Default OFF.

---

## 5. WLM workload/service-class lock attribution — `MON_GET_WORKLOAD` / `MON_GET_SERVICE_SUBCLASS`

These aggregate the same lock counters by WLM **workload definition** (who connected) or
**service subclass** (priority). Default classes always exist so rows return without custom
WLM (`db2-monget-catalog-2.md:196-198,457`). This is the closest Db2 analog to a wait-event
breakdown: `LOCK_WAIT_TIME` is one component of `TOTAL_WAIT_TIME`
(`db2-monget-catalog-2.md:230-233`).

Confirmed live: `MON_GET_SERVICE_SUBCLASS` `DEADLOCKS` (`:1713`), `LOCK_ESCALS` (`:1732`),
`LOCK_TIMEOUTS` (`:1733`), `LOCK_WAIT_TIME` (`:1734`), `LOCK_WAITS` (`:1735`), `*_GLOBAL`
+ `LOCK_ESCALS_MAXLOCKS/_LOCKLIST` (`:1803-1808`). `MON_GET_WORKLOAD` mirror at
`:2097,2116-2119,2185-2190`.

| pg/mysql analog | Db2 source: column | proposed `ibm_db2.<name>` | type | unit | tags | notes |
|---|---|---|---|---|---|---|
| `mysql.performance.wait_event.time` (lock component) | `MON_GET_WORKLOAD.LOCK_WAIT_TIME` (`:2118`) | `ibm_db2.workload.lock_wait_time` *(NEW)* | monotonic_count | millisecond | `workload_name`,`member` | lock-wait time by logical workload (app attribution). |
| `mysql.performance.wait_event.count` | `MON_GET_WORKLOAD.LOCK_WAITS` (`:2119`) | `ibm_db2.workload.lock_waits` *(NEW)* | monotonic_count | lock | `workload_name`,`member` | |
| (none) | `MON_GET_WORKLOAD.DEADLOCKS` (`:2097`) | `ibm_db2.workload.deadlocks` *(NEW, opt)* | monotonic_count | lock | `workload_name`,`member` | |
| (none) | `MON_GET_SERVICE_SUBCLASS.LOCK_WAIT_TIME` (`:1734`) | `ibm_db2.service_subclass.lock_wait_time` *(NEW, opt)* | monotonic_count | millisecond | `service_superclass_name`,`service_subclass_name`,`member` | lock time by WLM priority tier. |

Prefer **WORKLOAD** over SERVICE_SUBCLASS for app-level attribution unless WLM priority
tiers are configured (`db2-monget-catalog-2.md:333-336`). Cardinality is low (handful of
default classes/workloads) → safe to collect unconditionally, but still recommend a config
flag for consistency. These double-count the instance-level §2 counters along a dimension.

---

## 6. LIVE blocking / lock-wait detail (the activity/sample analog) — `MON_GET_LOCKS`, `MON_GET_APPL_LOCKWAIT`, `SYSIBMADM.MON_LOCKWAITS`

This is the analog of pg's per-relation `LOCK_METRICS` (`pg_locks`,
`code-postgres-metrics.md:371-372`), pg's DBM `locks.idle_in_transaction_age`
(`code-postgres-metrics.md:345-349`), and mysql's blocking detection via lock tables
(`code-mysql-dbm.md:301`). It answers "who is blocking whom right now". All three sources
are confirmed present: `MON_GET_LOCKS` + `MON_GET_APPL_LOCKWAIT` functions
(`_raw/01...txt:38,16`); `SYSIBMADM.MON_LOCKWAITS`, `LOCKWAITS`, `LOCKS_HELD` views
(`_raw/03-sysibmadm-objects.txt:44,36,35`).

**Column lists for `MON_GET_LOCKS` / `MON_GET_APPL_LOCKWAIT` are NOT in the DESCRIBE dump**
— the following are general Db2 12.1 knowledge — **capture a live
`DESCRIBE SELECT * FROM TABLE(MON_GET_LOCKS(NULL,-1))` and
`DESCRIBE SELECT * FROM TABLE(MON_GET_APPL_LOCKWAIT(NULL,-1))` before coding.**

### 6a. `MON_GET_LOCKS(NULL, -1)` — one row per held/requested lock (general Db2 12.1 — verify)
Useful columns (verify): `LOCK_NAME`, `LOCK_OBJECT_TYPE` (TABLE/ROW/etc.),
`LOCK_MODE` (S/X/IX/IS/U/Z/...), `LOCK_STATUS` (GRNT/CONV/WAIT), `LOCK_CURRENT_MODE`,
`LOCK_ESCALATION` (Y/N), `LOCK_COUNT`, `TBSP_ID`, `TAB_FILE_ID`, `APPLICATION_HANDLE`,
`MEMBER`.

| pg analog (`relations` LOCK_METRICS) | Db2 source | proposed `ibm_db2.<name>` | type | unit | tags | notes |
|---|---|---|---|---|---|---|
| `postgresql.locks` (count by lock_mode/lock_type/granted) | `COUNT(*)` over `MON_GET_LOCKS` grouped | `ibm_db2.lock.count` *(NEW)* | gauge | lock | `lock_object_type`,`lock_mode`,`lock_status`,`member` | mirrors pg `postgresql.locks` tagging (`lock_mode`,`lock_type`,`granted`). |

### 6b. `MON_GET_APPL_LOCKWAIT(NULL, -1)` / `SYSIBMADM.MON_LOCKWAITS` — one row per lock WAIT (blocking edge)
This is the blocking-edge view: requester + holder + waited object + wait age. Columns
(general Db2 12.1 — verify; `SYSIBMADM.MON_LOCKWAITS` is documented and stable):
`REQ_APPLICATION_HANDLE`, `HLD_APPLICATION_HANDLE`, `REQ_AGENT_TID`, `HLD_AGENT_TID`,
`LOCK_NAME`, `LOCK_OBJECT_TYPE`, `LOCK_MODE`, `LOCK_MODE_REQUESTED`,
`LOCK_WAIT_START_TIME` / `LOCK_WAIT_ELAPSED_TIME`, `TABSCHEMA`, `TABNAME`,
`REQ_APPLICATION_NAME`, `HLD_APPLICATION_NAME`, `MEMBER`.

| pg/mysql analog | Db2 source | proposed `ibm_db2.<name>` | type | unit | tags | notes |
|---|---|---|---|---|---|---|
| `postgresql.locks` granted=false / `mysql` blocking count | `COUNT(*)` over `MON_GET_APPL_LOCKWAIT` | `ibm_db2.lock.waits.current` *(NEW)* | gauge | lock | `lock_object_type`,`lock_mode`,`member` | current count of in-flight lock waits (waiters). |
| `postgresql.locks.idle_in_transaction_age` (DBM, max age) | `MAX(LOCK_WAIT_ELAPSED_TIME)` | `ibm_db2.lock.wait.max_age` *(NEW)* | gauge | second | `member`(,`tabschema`,`tabname` if low-card) | longest current lock wait — "stuck blocker" signal. |

**Beyond metrics:** the rich per-edge rows (requester→holder, object, statement) are the
natural feed for a **DBM "lock-wait / blocking" sample event** (analogous to pg DBM samples
+ blocking, `code-postgres-dbm-samples.md`). Out of scope for this metrics map, but flag:
`MON_GET_APPL_LOCKWAIT`/`MON_LOCKWAITS` is the source. See `db2-live-activity.md` references
(`code-base-framework.md:331,423`, `code-sqlserver-dbm-template.md:348-349`).

### 6c. Gating for live lock detail (IMPORTANT)
Per-object lock detail richness is gated by DB cfg monitor switches
(`_raw/04-monitor-config.txt`): live values are `mon_lockwait=NONE` (`:13`),
`mon_locktimeout=NONE` (`:12`), `mon_deadlock=WITHOUT_HIST` (`:10`), `mon_lck_msg_lvl=1`
(`:11`), `mon_lw_thresh=5000000` (`:14`). `MON_GET_LOCKS` / `MON_GET_APPL_LOCKWAIT` point-in
-time snapshots work regardless of these switches (they read live lock-manager state), but
**lock-wait/timeout/deadlock event-monitor history** needs the switches ON. Recommendation:
collect snapshot counts via the functions unconditionally (cheap), and only attempt the
event-history detail when switches are enabled (`db2-editions-versions.md:367` gate note).
Wrap in try/except so a missing function or privilege degrades gracefully (pg pattern,
`code-postgres-metrics.md:108-112`; mysql pattern, `code-mysql-metrics.md:265`).

---

## 7. pg/mysql metrics with NO clean Db2 equivalent (flagged)

| pg/mysql metric | why no Db2 analog | closest Db2 substitute (if any) |
|---|---|---|
| `postgresql.conflicts.lock` / `.deadlock` / `.snapshot` / `.bufferpin` / `.tablespace` (`metadata.csv`) | These are **standby recovery-conflict** cancels (replica replaying WAL kills local queries). Db2 HADR standby is read-replica-only differently; no per-conflict-type counter. | HADR replay state via `MON_GET_HADR` (`map-hadr-replication.md`); not a lock-conflict-type breakdown. |
| `mysql.innodb.s_lock_*` / `x_lock_*` / `mutex_spin_*` (semaphore spin metrics) | InnoDB-internal mutex/rwlock spin counters from `SHOW ENGINE INNODB STATUS` text. Db2 has no public spin-wait equivalent at this granularity. | `MON_GET_EXTENDED_LATCH_WAIT` (confirmed present, `_raw/01...txt:28`): `TOTAL_EXTENDED_LATCH_WAIT_TIME` / `TOTAL_EXTENDED_LATCH_WAITS` (in `MON_GET_SERVICE_SUBCLASS`, `db2-monget-catalog-2.md:237,240`) is the nearest "internal contention" signal — different semantics. |
| `mysql.performance.table_locks_immediate` (granted-without-wait count) | Db2 doesn't expose a "lock granted immediately" counter; only waits are counted. | Derive: total lock requests − `LOCK_WAITS` is not directly available; treat as no analog. |
| `mysql.innodb.locked_tables` / `locked_transactions` (gauge from text) | InnoDB-internal snapshot counts. | `MON_GET_LOCKS` row counts grouped by `LOCK_OBJECT_TYPE='TABLE'` (§6a) approximate this. |
| `postgresql.create_index.lockers_done` / `lockers_total` | pg CREATE INDEX progress lockers. Db2 index-build progress is not exposed with locker counts. | `MON_GET_UTILITY` (no locker breakdown). |

Db2 metrics with **NO pg/mysql analog** worth adding (Db2-native value-adds): lock
**timeouts** (`ibm_db2.lock.timeouts`, already shipped), lock **escalations** family
(`ibm_db2.lock.escalations*`, §2), pureScale **global** lock counters (`*.global`, §2),
per-connection **isolation level** (`CURRENT_ISOLATION` tag, §3), per-connection
**lock-timeout setting** (`LOCK_TIMEOUT_VAL`), and `LOCK_WAIT_ELAPSED_TIME` max-age (§6b).

---

## 8. Config / capacity context (denominators for lock metrics)

Lock-pressure metrics are most useful paired with their configured limits, read from
`SYSIBMADM.DBCFG` by `NAME` (lowercase param names, confirmed view present
`_raw/03-sysibmadm-objects.txt:24`; access pattern `db2-config-settings.md:94`). These are
the analogs of mysql's `VARIABLES_VARS` capacity gauges (`max_connections`, etc.):

| DB cfg param | meaning | proposed `ibm_db2.<name>` (optional capacity gauge) | type/unit | notes (general Db2 12.1 — verify) |
|---|---|---|---|---|
| `locklist` | total lock-list memory (4KiB pages, or AUTOMATIC) | `ibm_db2.lock.list.configured` | gauge / page | pair with `LOCK_LIST_IN_USE`/`ibm_db2.lock.pages` to compute % used. |
| `maxlocks` | % of lock list one app may use before escalation | `ibm_db2.lock.maxlocks_percent` | gauge / percent | escalation threshold; pair with `LOCK_ESCALS`. |
| `locktimeout` | lock wait timeout (seconds; -1=infinite) | `ibm_db2.lock.timeout_value` | gauge / second | pair with `LOCK_TIMEOUTS`. |
| `dlchktime` | deadlock detector interval (ms) | `ibm_db2.lock.deadlock_check_interval` | gauge / millisecond | context for `DEADLOCKS`. |

These four mirror the postgres "max_connections" denominator pattern
(`code-postgres-metrics.md:214-227`). Low priority; emit once per run (cache via a
`GlobalVariables`-style fetch, `code-mysql-metrics.md:221-229`).

---

## 9. Implementation notes (for the building agent)

1. **Use Paradigm B (declarative QueryExecutor `columns` dicts)** for all new lock queries —
   each is one `SELECT ... FROM TABLE(MON_GET_*(...))` with metric/tag columns
   (`code-mysql-metrics.md:262`, `code-postgres-metrics.md:46-68,459`). The existing ibm_db2
   check hand-rolls cursors (`ibm_db2.py:152-173`); new work should adopt the framework style.
2. **Fix the lossy `lock.wait` average**: keep `ibm_db2.lock.wait` (avg, backward compat) but
   **add raw `ibm_db2.lock.waits` (count) + `ibm_db2.lock.wait_time` (count, ms)** so the
   counters are delta-able in the backend (every other integration ships raw cumulatives).
   Code site: `ibm_db2.py:165-169`.
3. **metric_type discipline** (`code-mysql-metrics.md:267`): cumulative Db2 counters
   (`DEADLOCKS`, `LOCK_WAITS`, `LOCK_WAIT_TIME`, `LOCK_TIMEOUTS`, `LOCK_ESCALS`) →
   `monotonic_count` (CSV `count`). Point-in-time (`NUM_LOCKS_HELD`, `NUM_LOCKS_WAITING`,
   `LOCK_LIST_IN_USE`, snapshot `COUNT(*)` from `MON_GET_LOCKS`/`_APPL_LOCKWAIT`, max-age) →
   `gauge`.
4. **Units**: all Db2 `*_TIME` lock columns are **milliseconds** (`db2-monget-catalog-2.md:26`)
   → `unit_name=millisecond`. `LOCK_LIST_IN_USE` is **bytes** (existing code divides by 4096
   to report 4KiB pages → `unit_name=page`). Counts → `unit_name=lock`.
5. **Tags**: base `db`, `member` on all (member from `-2` fan-out if pureScale/DPF — current
   code passes `-1`, single-member, so `member` is constant; keep dimension for forward-compat,
   `code-postgres-metrics.md:408-411`). Per-conn: `application_name`, `session_auth_id`,
   optional `current_isolation`. Per-table: `tabschema`, `tabname`. Per-workload:
   `workload_name`. Lock snapshot: `lock_object_type`, `lock_mode`, `lock_status`.
6. **Cardinality**: per-connection/per-table/per-lock are unbounded → gate behind config flags
   (e.g. `collect_connection_lock_metrics`, `collect_table_lock_metrics`, default OFF) with
   top-N `FETCH FIRST n ROWS ONLY`, mirroring pg `relations`/`dbm` and mysql index `limit`
   gating (`code-postgres-metrics.md:415-434`, `code-mysql-metrics.md:171`).
7. **Graceful degradation**: wrap each lock query so a missing function (`MON_GET_LOCKS` etc.)
   or insufficient authority (needs SYSMON/DBADM, `code-mysql-metrics.md:265`) logs a warning
   and skips, rather than failing the whole check (`code-postgres-metrics.md:108-112`).
8. **Every new metric needs an `ibm_db2/metadata.csv` row** with `integration=ibm_db2`,
   correct `metric_type` (catalog vocab: `gauge`/`count`/`rate`), `unit_name`/`per_unit_name`,
   `orientation` (lock waits/timeouts/deadlocks/escalations = `-1`; held = `0`), and a
   description naming the enabling config flag + tags (`code-postgres-metrics.md:441-453`).
9. **Live-DESCRIBE before coding** the §6 functions: `MON_GET_LOCKS`,
   `MON_GET_APPL_LOCKWAIT`, `MON_GET_EXTENDED_LATCH_WAIT` column lists are knowledge-based
   here, not from the dump.

---

## 10. Proposed metadata.csv rows (ready to paste; verify units/descriptions)

```
ibm_db2.lock.waits,count,,lock,,The total number of times that a request for a lock resulted in a wait.,-1,ibm_db2,,
ibm_db2.lock.wait_time,count,,millisecond,,The total elapsed time spent waiting for locks.,-1,ibm_db2,,
ibm_db2.lock.escalations,count,,lock,,The total number of times that locks were escalated from row to table level.,-1,ibm_db2,,
ibm_db2.lock.escalations.maxlocks,count,,lock,,Lock escalations triggered because an application reached its MAXLOCKS limit.,-1,ibm_db2,,
ibm_db2.lock.escalations.locklist,count,,lock,,Lock escalations triggered because the lock list became full.,-1,ibm_db2,,
ibm_db2.lock.escalations.global,count,,lock,,"Global (pureScale) lock escalations. Tagged with member.",-1,ibm_db2,,
ibm_db2.lock.waits.global,count,,lock,,"Global (pureScale) lock waits. Tagged with member.",-1,ibm_db2,,
ibm_db2.lock.wait_time.global,count,,millisecond,,"Global (pureScale) lock-wait time. Tagged with member.",-1,ibm_db2,,
ibm_db2.lock.timeouts.global,count,,lock,,"Global (pureScale) lock timeouts. Tagged with member.",-1,ibm_db2,,
ibm_db2.lock.count,gauge,,lock,,"Number of locks currently held/requested, from MON_GET_LOCKS. Tagged with lock_object_type, lock_mode, lock_status.",0,ibm_db2,,
ibm_db2.lock.waits.current,gauge,,lock,,"Number of lock waits currently in flight, from MON_GET_APPL_LOCKWAIT. Tagged with lock_object_type, lock_mode.",-1,ibm_db2,,
ibm_db2.lock.wait.max_age,gauge,,second,,The age of the longest-running current lock wait.,-1,ibm_db2,,
ibm_db2.connection.locks_held,gauge,,lock,,"Locks held per connection. Enabled with collect_connection_lock_metrics. Tagged with application_name, session_auth_id.",0,ibm_db2,,
ibm_db2.connection.locks_waiting,gauge,,lock,,"Locks being waited on per connection. Tagged with application_name, session_auth_id.",-1,ibm_db2,,
ibm_db2.connection.lock_wait_time,count,,millisecond,,"Cumulative lock-wait time per connection. Tagged with application_name, session_auth_id.",-1,ibm_db2,,
ibm_db2.connection.lock_waits,count,,lock,,"Cumulative lock waits per connection. Tagged with application_name, session_auth_id.",-1,ibm_db2,,
ibm_db2.connection.deadlocks,count,,lock,,"Deadlocks attributed to a connection. Tagged with application_name, session_auth_id.",-1,ibm_db2,,
ibm_db2.connection.lock_timeouts,count,,lock,,"Lock timeouts attributed to a connection. Tagged with application_name, session_auth_id.",-1,ibm_db2,,
ibm_db2.connection.lock_escalations,count,,lock,,"Lock escalations attributed to a connection. Tagged with application_name, session_auth_id.",-1,ibm_db2,,
ibm_db2.table.lock_waits,count,,lock,,"Lock waits per table. Enabled with collect_table_lock_metrics. Tagged with tabschema, tabname.",-1,ibm_db2,,
ibm_db2.table.lock_wait_time,count,,millisecond,,"Cumulative lock-wait time per table. Tagged with tabschema, tabname.",-1,ibm_db2,,
ibm_db2.table.lock_escalations,count,,lock,,"Lock escalations per table. Tagged with tabschema, tabname.",-1,ibm_db2,,
ibm_db2.workload.lock_wait_time,count,,millisecond,,"Cumulative lock-wait time per WLM workload. Tagged with workload_name.",-1,ibm_db2,,
ibm_db2.workload.lock_waits,count,,lock,,"Cumulative lock waits per WLM workload. Tagged with workload_name.",-1,ibm_db2,,
ibm_db2.workload.deadlocks,count,,lock,,"Deadlocks per WLM workload. Tagged with workload_name.",-1,ibm_db2,,
```

(Existing rows `ibm_db2.lock.active`, `ibm_db2.lock.dead`, `ibm_db2.lock.pages`,
`ibm_db2.lock.timeouts`, `ibm_db2.lock.wait`, `ibm_db2.lock.waiting` already in
`/home/bits/dd/integrations-core/ibm_db2/metadata.csv` — keep.)
