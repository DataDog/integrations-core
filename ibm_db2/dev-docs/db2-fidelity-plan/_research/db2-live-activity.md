# Db2 12.1.4 Live Activity / Active-Session Probe — `MON_CURRENT_SQL`, `MON_GET_ACTIVITY`, `MON_GET_UNIT_OF_WORK`

Raw empirical research input for the Db2 **activity-sampling** (a.k.a. Active Session History /
"samples") implementation plan. This is the **currently-executing-statement source of truth** —
the Db2 analog of Postgres `pg_stat_activity` / SQL Server `sys.dm_exec_requests` +
`dm_exec_sql_text`. All output below was captured **live, on 2026-06-15**, from the running
local-dev container while the orders inventory workload was actively executing.

> Scope note: this doc covers the **live / in-flight activity** sources only. The cumulative
> statement-metrics source (`MON_GET_PKG_CACHE_STMT`, the `pg_stat_statements` analog) is
> covered in the sibling doc `db2-live-pkgcache.md` — read that for query-metrics.
> This doc is raw input for an implementation plan handed to another agent — favor completeness
> over brevity. Do NOT hard-code column sets from this doc; introspect at runtime. Confirm units
> per-column against IBM docs (cited in §11) — they are inconsistent across columns.

---

## 0. Environment / how this was captured

- Container: `db2-primary`, image `icr.io/db2_community/db2:12.1.4.0`, status `Up 2 days (healthy)`.
  - Sibling containers running concurrently: `orders-app-db2-bits` (workload generator,
    image `db2-orders-app-db2`) and `datadog-agent-db2-bits` (`dbm-local-db2-agent:7.78.0`).
- Product level (`db2level`): `DB2 v12.1.4.0`, code release `SQL12014`, level identifier
  `02050110`, Fix Pack `0`, 64-bit, installed at `/opt/ibm/db2/V12.1`.
- Database: `TESTDB`. Auth ID: `DB2INST1`. The local `db2inst1` OS user needs **no password**.
- Invocation pattern used for every probe (cwd is reset between calls; always uses `su -`):

  ```bash
  docker exec db2-primary su - db2inst1 -c \
    "db2 connect to testdb > /dev/null; db2 -x \"<SQL>\"; db2 connect reset > /dev/null"
  ```

  For multi-statement / looping probes I wrote a small shell script, `docker cp`'d it into the
  container, and ran it via `docker exec db2-primary su - db2inst1 -c "bash /tmp/<file>.sh"`.

  **Quoting gotcha (live-confirmed):** Db2 CLP treats `"..."` as a **delimited identifier**, so a
  string literal like `'SYSIBMADM'` must be single-quoted *inside* an outer double-quoted CLP
  statement. Wrapping a literal in double quotes yields
  `SQL0206N "..." is not valid in the context where it is used. SQLSTATE=42703`. The `-x` flag
  suppresses the column header/footer so rows can be parsed.

  **Loop gotcha (live-confirmed):** running many *separate* `db2 -x` calls inside a single
  `su - -c "for ...; do db2 -x ...; done"` intermittently drops the connection
  (`SQL1024N A database connection does not exist. SQLSTATE=08003`), especially under
  concurrency / when other detached `db2 connect reset` processes run. For reliable rapid
  sampling, prefer either (a) one `docker exec` per sample, or (b) a single CLP session via
  `db2 -tf script.sql`. Don't trust an in-shell `for`-loop of `db2 -x` for tight sampling.

- Workload identity (from `MON_GET_CONNECTION`): the orders app connects as
  `APPLICATION_NAME = 'run_orders'`, `SESSION_AUTH_ID = 'DB2INST1'`, over TCP, with
  `APPLICATION_ID` like `172.17.129.4.50932.260615021825` (`<ip>.<port>.<timestamp>`). The
  Datadog agent connects as `APPLICATION_NAME = 'agent'` (handle 427). Interactive CLP probes
  show as `APPLICATION_NAME = 'db2bp'` with `APPLICATION_ID` like `*LOCAL.db2inst1.260615022112`.

---

## 1. TL;DR (the load-bearing facts)

1. **There are three distinct live sources, at three different granularities:**
   - `SYSIBMADM.MON_CURRENT_SQL` — **per in-flight activity** (statement). Has `STMT_TEXT`. **Best
     source for currently-executing statement text + identity.**
   - `TABLE(MON_GET_ACTIVITY(NULL, -2))` — **per in-flight activity** (statement). Also has
     `STMT_TEXT`. This is the underlying primitive; `MON_CURRENT_SQL` is a thin view over it.
   - `TABLE(MON_GET_UNIT_OF_WORK(NULL, -1))` — **per transaction (UOW)**. **No `STMT_TEXT`.** Gives
     transaction-level state + timing, not statement text.

2. **`MON_CURRENT_SQL` is the recommended primary source for "what is running right now".**
   Live-verified its view definition (§5): it is
   `MON_GET_ACTIVITY(NULL,-2)` JOIN `MON_GET_CONNECTION(NULL,-2)`, and its `STMT_TEXT` column comes
   **directly from `MON_GET_ACTIVITY`**. It adds the connection identity (`APPLICATION_NAME`,
   `SESSION_AUTH_ID`, `CLIENT_APPLNAME`, `APPLICATION_ID`) and a **true wall-clock elapsed time**
   the raw function does not expose.

3. **`MON_CURRENT_SQL.ELAPSED_TIME_MSEC` / `ELAPSED_TIME_SEC` = wall-clock elapsed of the
   in-flight statement** (`CURRENT TIMESTAMP - LOCAL_START_TIME`), computed in the view (§5).
   Live-verified advancing 9899 ms → 14330 ms across a 3 s gap on a `CALL dbms_lock.sleep(15)`
   (§4). This is the single most useful "how long has this been running" signal and the raw
   `MON_GET_ACTIVITY` function does **not** provide it directly.

4. **`MON_GET_ACTIVITY` exposes `STMT_TEXT`, `EXECUTABLE_ID`, and `STMT_PKG_CACHE_ID` directly** —
   no `_DETAILS` / XML-parsing variant needed (live-confirmed via `DESCRIBE`, §6). This means you
   can join an in-flight activity to its package-cache metrics row by `EXECUTABLE_ID`.

5. **`MON_GET_ACTIVITY` has 418 columns** in 12.1.4 (live `DESCRIBE`). `MON_CURRENT_SQL` exposes
   **19** of them (§3). Both return only **currently-in-progress** activities — a transient,
   point-in-time snapshot, NOT cumulative history.

6. **`STMT_TEXT` here is the prepared text, identical in form to the package cache.** For the
   orders app it carries the leading Datadog SQL-comment tag
   `/*dddbs='orders-app-bits',dde='local',ddps='orders-app-bits',ddprs='orders-db2'*/` and
   `?` parameter markers (live sample §7). The agent must obfuscate / strip the comment / compute
   `query_signature` client-side, exactly as for the package cache.

7. **Fast OLTP is invisible to sampling.** The orders inventory statements
   (`select count(*) from inventory_items`, `UPDATE ... WHERE sku = ?`, etc.) execute in
   sub-millisecond time and were **never** caught by 40–80 point-in-time samples of
   `MON_CURRENT_SQL` / `MON_GET_ACTIVITY` (§8). Only deliberately slow statements (a triple
   cartesian join, or `CALL dbms_lock.sleep(N)`) were reliably captured. **Implication:**
   activity sampling alone will under-count short statements; it is an ASH-style *wait/long-query*
   signal, not a complete request log. The cumulative package cache (sibling doc) is what captures
   every statement.

8. **`MON_GET_UNIT_OF_WORK` has NO `STMT_TEXT`** (live-confirmed via `DESCRIBE` grep, §6). Use it
   for transaction state (`WORKLOAD_OCCURRENCE_STATE`), commit/rollback counts, and request-time —
   not for "what statement is running". `MON_CURRENT_UOW` (its view companion) likewise has no
   statement text (§9).

9. **Member argument semantics:** `MON_GET_ACTIVITY(application_handle, member)` — pass
   `member = -1` for "current member" or `-2` for "all members" (`MON_CURRENT_SQL` uses `-2`).
   First arg `NULL` = all application handles; pass a specific handle to scope to one connection.

10. **Monitoring config is adequate by default for live activity.** `mon_act_metrics = BASE`
    (live `DBCFG`, §10). Identity + `STMT_TEXT` + state + elapsed do not require any non-default
    setting. Activity *timing* counters (`TOTAL_ACT_TIME`, etc.) require `mon_act_metrics >= BASE`
    (satisfied). `MON_GET_UNIT_OF_WORK` statement/package lists are OFF
    (`mon_uow_data=NONE`, `mon_uow_pkglist=OFF`, `mon_uow_execlist=OFF`) — not needed for this
    source.

11. **The current `ibm_db2` integration collects NO live activity.** A grep over
    `/home/bits/dd/integrations-core/ibm_db2/datadog_checks/` for
    `mon_current_sql|mon_get_activity|mon_get_unit_of_work|mon_current_uow|activity|samples`
    returns nothing in code (§12). This is greenfield for the DBM samples feature.

---

## 2. Decision: which source for currently-executing statement text + identity?

**Winner: `SYSIBMADM.MON_CURRENT_SQL`** — and, where you need columns it does not expose, fall
back to the raw `TABLE(MON_GET_ACTIVITY(NULL, -2))` it is built on.

| Need | MON_CURRENT_SQL | MON_GET_ACTIVITY | MON_GET_UNIT_OF_WORK |
|---|---|---|---|
| In-flight statement text (`STMT_TEXT`) | YES | YES | **NO** |
| Stable statement identity (`EXECUTABLE_ID`) | no | **YES** | no |
| Pkg-cache join id (`STMT_PKG_CACHE_ID`) | no | **YES** | no |
| Application handle | YES | YES | YES |
| Application id (conn string) | YES | YES (`APPL_ID`) | YES (`APPL_ID`) |
| Application name | YES | no (handle only) | no (handle only) |
| Session auth id (user) | YES | no¹ | YES |
| Client app name | YES | YES | YES |
| **Wall-clock elapsed of stmt** | **YES** (`ELAPSED_TIME_*`) | no² | no² |
| Activity state (EXECUTING/IDLE/…) | YES | YES | no |
| Activity type (READ_DML/CALL/…) | YES | YES | no |
| Transaction state | no | no | **YES** (`WORKLOAD_OCCURRENCE_STATE`) |
| Accumulated activity time | `TOTAL_CPU_TIME` only | **YES** (`TOTAL_ACT_TIME`, waits) | UOW totals only |
| Query cost estimate | YES | YES | no |
| Rows read / returned | YES | YES | YES (UOW totals) |

¹ `MON_GET_ACTIVITY` has the handle; join to `MON_GET_CONNECTION` for `SESSION_AUTH_ID`.
² Raw functions give accumulated/element times relative to db activation, not wall-clock since
statement start; `MON_CURRENT_SQL` computes wall-clock in the view (§5).

**Recommended collection query (start here):**

```sql
SELECT
    APPLICATION_HANDLE,         -- BIGINT  : connection id within this db activation
    APPLICATION_ID,             -- VARCHAR : globally-unique connection string
    APPLICATION_NAME,           -- VARCHAR : 'run_orders', 'agent', 'db2bp', ...
    SESSION_AUTH_ID,            -- VARCHAR : the user
    CLIENT_APPLNAME,            -- VARCHAR : client-set app name (often '-')
    UOW_ID,                     -- INTEGER : transaction id within the connection
    ACTIVITY_ID,                -- INTEGER : activity id within the UOW
    ELAPSED_TIME_MSEC,          -- INTEGER : *** wall-clock elapsed of the in-flight stmt ***
    ACTIVITY_STATE,             -- VARCHAR : 'EXECUTING', 'IDLE', ...
    ACTIVITY_TYPE,              -- VARCHAR : 'READ_DML', 'WRITE_DML', 'DDL', 'CALL', 'OTHER', ...
    TOTAL_CPU_TIME,             -- BIGINT  : microseconds (note: us, not ms)
    ROWS_READ,                  -- BIGINT
    ROWS_RETURNED,              -- BIGINT
    QUERY_COST_ESTIMATE,        -- BIGINT  : optimizer timerons
    STMT_TEXT                   -- CLOB    : the in-flight statement (obfuscate client-side!)
FROM SYSIBMADM.MON_CURRENT_SQL
WHERE ACTIVITY_STATE = 'EXECUTING'
  AND APPLICATION_HANDLE <> APPLICATION_HANDLE_OF_THE_AGENT_SESSION   -- exclude self
```

If you also need `EXECUTABLE_ID` (to join to package-cache metrics) and accumulated wait/act time,
sample `TABLE(MON_GET_ACTIVITY(NULL, -2))` directly and join `MON_GET_CONNECTION(NULL, -2)` for
the connection identity — i.e. reproduce the `MON_CURRENT_SQL` view but add `EXECUTABLE_ID`,
`STMT_PKG_CACHE_ID`, `TOTAL_ACT_TIME`, `TOTAL_ACT_WAIT_TIME`, `LOCAL_START_TIME`,
`COORD_STMT_EXEC_TIME`, `WLM_QUEUE_TIME_TOTAL`, `EFFECTIVE_ISOLATION`.

---

## 3. `SYSIBMADM.MON_CURRENT_SQL` — full column list (live)

Captured via:
```bash
db2 -x "select colname from syscat.columns where tabschema='SYSIBMADM' and tabname='MON_CURRENT_SQL' order by colno"
```
All **19** columns, in order:

| # | Column | Type (from view, §5) | Notes |
|---|---|---|---|
| 1 | `COORD_MEMBER` | SMALLINT | coordinating member |
| 2 | `APPLICATION_HANDLE` | BIGINT | connection id |
| 3 | `APPLICATION_NAME` | VARCHAR | from `MON_GET_CONNECTION` |
| 4 | `SESSION_AUTH_ID` | VARCHAR | the user |
| 5 | `CLIENT_APPLNAME` | VARCHAR | client-supplied; often `-` |
| 6 | `ELAPSED_TIME_SEC` | derived INTEGER | wall-clock seconds since `LOCAL_START_TIME` |
| 7 | `ELAPSED_TIME_MSEC` | derived INTEGER | wall-clock **milliseconds** since stmt start |
| 8 | `ACTIVITY_STATE` | VARCHAR(32) | `EXECUTING`, `IDLE`, ... |
| 9 | `ACTIVITY_TYPE` | VARCHAR(32) | `READ_DML`, `WRITE_DML`, `DDL`, `CALL`, `LOAD`, `OTHER` |
| 10 | `TOTAL_CPU_TIME` | BIGINT | **microseconds** |
| 11 | `ROWS_READ` | BIGINT | |
| 12 | `ROWS_RETURNED` | BIGINT | |
| 13 | `QUERY_COST_ESTIMATE` | BIGINT | optimizer cost (timerons) |
| 14 | `DIRECT_READS` | BIGINT | |
| 15 | `DIRECT_WRITES` | BIGINT | |
| 16 | `APPLICATION_ID` | VARCHAR | connection string id |
| 17 | `UOW_ID` | INTEGER | transaction id |
| 18 | `ACTIVITY_ID` | INTEGER | activity id within UOW |
| 19 | `STMT_TEXT` | CLOB | the in-flight statement text |

The triple `(APPLICATION_HANDLE, UOW_ID, ACTIVITY_ID)` uniquely identifies an in-flight activity
within a database activation.

---

## 4. PROOF: catching an in-flight statement + live elapsed time

Launched a 15-second sleep in a detached CLP session:
```bash
# /tmp/sleep15.sh, run with: docker exec -d db2-primary su - db2inst1 -c "bash /tmp/sleep15.sh"
db2 connect to testdb; db2 -x "call dbms_lock.sleep(15)"; db2 connect reset
```
Then took two snapshots 3 s apart of all three sources (`/tmp/catch3.sh`):

**Snapshot A**
```
===== MON_CURRENT_SQL (sleep handle) =====
 19706  *LOCAL.db2inst1.260615022112  uow=1 aid=1  esec=10  ems=9899   EXECUTING CALL  authid=DB2INST1  stmt="CALL dbms_lock.sleep(?)"
===== MON_GET_ACTIVITY (sleep handle) =====
 19706  uow=1 aid=1  EXECUTING  total_act_time=0  total_cpu_time=0  local_start_time=2026-06-15-02.20.59.301076  stmt="CALL dbms_lock.sleep(?)"
===== MON_GET_UNIT_OF_WORK (sleep handle) =====
 19706  uow=1  AUTONOMOUS_W(ORKLOAD)  total_rqst_time=0  uow_start_time=2026-06-15-02.20.59.299843
```

**Snapshot B (≈3 s later)**
```
===== MON_CURRENT_SQL (sleep handle) =====
 19706  *LOCAL.db2inst1.260615022112  uow=1 aid=1  esec=14  ems=14330  EXECUTING CALL  authid=DB2INST1  stmt="CALL dbms_lock.sleep(?)"
===== MON_GET_ACTIVITY (sleep handle) =====
 19706  uow=1 aid=1  EXECUTING  total_act_time=11009  total_cpu_time=2111  local_start_time=2026-06-15-02.20.59.301076  stmt="CALL dbms_lock.sleep(?)"
===== MON_GET_UNIT_OF_WORK (sleep handle) =====
 19706  uow=1  AUTONOMOUS_W(ORKLOAD)  total_rqst_time=11010  uow_start_time=2026-06-15-02.20.59.299843
```

**What this proves:**
- `MON_CURRENT_SQL.ELAPSED_TIME_MSEC` is **wall-clock elapsed** and advances live
  (9899 → 14330 ms = ~4.4 s real gap incl. probe latency). This is the canonical "how long has
  this statement been running" value.
- `MON_GET_ACTIVITY.TOTAL_ACT_TIME` is **accumulated activity time**, not wall-clock: it was `0`
  in Snap A and `11009` ms in Snap B. It lags / differs from wall-clock and is `0` until the
  request-metrics machinery records it. Do not use it as elapsed-since-start; use
  `MON_CURRENT_SQL.ELAPSED_TIME_MSEC` or compute `CURRENT TIMESTAMP - LOCAL_START_TIME` yourself.
- `MON_GET_UNIT_OF_WORK` shows the **transaction** state (`AUTONOMOUS_WORKLOAD` here, because
  `dbms_lock.sleep` runs in an autonomous routine) and `TOTAL_RQST_TIME` advancing — but **no
  statement text at all**.
- Statement text is the **prepared** form: `CALL dbms_lock.sleep(?)` (parameter marker `?`, not
  the literal `15`).

A second proof using a concurrent multi-statement capture (`/tmp/catch.sh`, while a
`dbms_lock.sleep(8)` ran) caught **multiple in-flight rows simultaneously**, including the
internal helper agent of the sleep routine:
```
===== MON_CURRENT_SQL while slow query runs =====
 19684 db2artn  ms=7899 EXECUTING OTHER  "SET :HV00009 :HI00009 = DBMS_PIPE.RECEIVE_MESSAGE('used fo..."
 19684 db2artn  ms=7903 EXECUTING CALL   "-"
 19683 db2bp    ms=7904 EXECUTING CALL   "CALL dbms_lock.sleep(?)"
 19688 db2bp    ms=0    EXECUTING READ_DML "select application_handle ..."   <- the probe itself
===== MON_GET_ACTIVITY while slow query runs =====
 19683 uow=1 aid=1 EXECUTING CALL     "CALL dbms_lock.sleep(?)"
 19684 uow=1 aid=2 EXECUTING OTHER    "SET :HV00009 :HI00009 = DBMS_PIPE.RECEIVE_MESSAGE('us..."
 19684 uow=1 aid=1 EXECUTING CALL     "-"
 19688 uow=2 aid=1 EXECUTING READ_DML "select application_handle, uow_id, activity_id ..."
===== MON_GET_UNIT_OF_WORK while slow query runs (active only) =====
 19684 uow=1 UOWEXEC
 19683 uow=1 AUTONOMOUS_W(ORKLOAD)
 19688 uow=3 UOWEXEC
 19685 uow=1 TRANSIENT
```
Note: the probe query **always appears as a row** in its own snapshot (handle 19688 above) — the
agent must exclude its own `APPLICATION_HANDLE` (or filter on `APPLICATION_NAME`/`APPLICATION_ID`)
when collecting.

---

## 5. PROOF: `MON_CURRENT_SQL` is a view over `MON_GET_ACTIVITY` + `MON_GET_CONNECTION`

Captured via `select text from syscat.views where viewschema='SYSIBMADM' and viewname='MON_CURRENT_SQL'`.
Reconstructed (abbreviated, exact structure):

```sql
CREATE OR REPLACE VIEW SYSIBMADM.MON_CURRENT_SQL
 (COORD_MEMBER, APPLICATION_HANDLE, APPLICATION_NAME, SESSION_AUTH_ID, CLIENT_APPLNAME,
  ELAPSED_TIME_SEC, ELAPSED_TIME_MSEC, ACTIVITY_STATE, ACTIVITY_TYPE, TOTAL_CPU_TIME,
  ROWS_READ, ROWS_RETURNED, QUERY_COST_ESTIMATE, DIRECT_READS, DIRECT_WRITES,
  APPLICATION_ID, UOW_ID, ACTIVITY_ID, STMT_TEXT)
AS
WITH WLM_METRICS AS (
  SELECT APPLICATION_HANDLE, UOW_ID, ACTIVITY_ID,
         MIN(COORD_MEMBER)    AS COORD_MEMBER,
         SUM(TOTAL_CPU_TIME)  AS TOTAL_CPU_TIME,
         SUM(ROWS_READ)       AS ROWS_READ,
         SUM(ROWS_RETURNED)   AS ROWS_RETURNED,
         SUM(DIRECT_READS)    AS DIRECT_READS,
         SUM(DIRECT_WRITES)   AS DIRECT_WRITES
  FROM TABLE(MON_GET_ACTIVITY(NULL, -2))           -- <<< primitive #1: per-member activities
  GROUP BY APPLICATION_HANDLE, UOW_ID, ACTIVITY_ID
)
SELECT M.COORD_MEMBER, W.APPLICATION_HANDLE, C.APPLICATION_NAME, C.SESSION_AUTH_ID,
       C.CLIENT_APPLNAME,
       /* ELAPSED_TIME_SEC = CURRENT TIMESTAMP - W.LOCAL_START_TIME, in whole seconds */
       (((JULIAN_DAY(CURRENT TIMESTAMP)-JULIAN_DAY(W.LOCAL_START_TIME))*24
         + (HOUR(CURRENT TIMESTAMP)-HOUR(W.LOCAL_START_TIME)))*60
         + (MINUTE(CURRENT TIMESTAMP)-MINUTE(W.LOCAL_START_TIME)))*60
         + (SECOND(CURRENT TIMESTAMP)-SECOND(W.LOCAL_START_TIME))  AS ELAPSED_TIME_SEC,
       /* ELAPSED_TIME_MSEC = same delta incl. MICROSECOND, /1000, as INTEGER */
       CAST(( ... seconds*1000000 + (MICROSECOND(CURRENT TIMESTAMP)-MICROSECOND(W.LOCAL_START_TIME)) )/1000
            AS INTEGER)  AS ELAPSED_TIME_MSEC,
       W.ACTIVITY_STATE, W.ACTIVITY_TYPE,
       M.TOTAL_CPU_TIME, M.ROWS_READ, M.ROWS_RETURNED,
       W.QUERY_COST_ESTIMATE, M.DIRECT_READS, M.DIRECT_WRITES,
       C.APPLICATION_ID, M.UOW_ID, M.ACTIVITY_ID,
       W.STMT_TEXT                                  -- <<< STMT_TEXT comes from MON_GET_ACTIVITY
FROM WLM_METRICS AS M
JOIN TABLE(MON_GET_ACTIVITY(NULL, -2))   AS W
  ON W.APPLICATION_HANDLE = M.APPLICATION_HANDLE
 AND W.MEMBER             = M.COORD_MEMBER
 AND W.UOW_ID             = M.UOW_ID
 AND W.ACTIVITY_ID        = M.ACTIVITY_ID
JOIN TABLE(MON_GET_CONNECTION(NULL, -2)) AS C       -- <<< primitive #2: connection identity
  ON C.APPLICATION_HANDLE = M.APPLICATION_HANDLE
 AND C.MEMBER             = M.COORD_MEMBER;
```

**Takeaways for the implementation:**
- `ELAPSED_TIME_MSEC` = `CURRENT TIMESTAMP - LOCAL_START_TIME` computed at query time. You can
  reproduce this exactly against the raw function if you collect from `MON_GET_ACTIVITY` directly
  and want more columns.
- `TOTAL_CPU_TIME` / `ROWS_*` / `DIRECT_*` are **summed across members** (this is a CTE `SUM`),
  which matters only on multi-member (DPF) instances; on a single member it is a pass-through.
- The view double-evaluates `MON_GET_ACTIVITY(NULL,-2)` (once in the CTE, once in the join). If
  you build your own collector, evaluate it once and self-join, or just add the columns you need
  to a single scan.
- `MEMBER` filter `-2` = all members. On the single-member community container `COORD_MEMBER` /
  `MEMBER` are `0`.

---

## 6. `MON_GET_ACTIVITY` — shape and key columns (live `DESCRIBE`)

```bash
db2 -x "describe select * from table(mon_get_activity(null,-1))"
# -> "Number of columns: 418"
```

**Confirmed-present identity / text / timing columns** (grep of the `DESCRIBE`):

| Column | Type | Meaning / unit | Notes |
|---|---|---|---|
| `APPLICATION_HANDLE` | BIGINT | connection id | |
| `APPL_ID` | VARCHAR(128) | connection string id | same as `MON_CURRENT_SQL.APPLICATION_ID` |
| `UOW_ID` | INTEGER | transaction id | |
| `ACTIVITY_ID` | INTEGER | activity id within UOW | |
| `PARENT_UOW_ID` / `PARENT_ACTIVITY_ID` | INTEGER | parent activity (nested/routine) | |
| `NESTING_LEVEL` / `INVOCATION_ID` | INTEGER | for nested activities | |
| `ACTIVITY_STATE` | VARCHAR(32) | `EXECUTING`, `IDLE`, ... | |
| `ACTIVITY_TYPE` | VARCHAR(32) | `READ_DML`, `WRITE_DML`, `DDL`, `CALL`, `LOAD`, `OTHER` | live-seen: `READ_DML`, `CALL`, `OTHER` |
| `LOCAL_START_TIME` | TIMESTAMP | when this activity started (local) | use for wall-clock elapsed |
| `ENTRY_TIME` | TIMESTAMP | when activity entered the system | |
| `EXECUTABLE_ID` | VARCHAR(32) FOR BIT DATA | **stable statement identity** | join key to `MON_GET_PKG_CACHE_STMT` |
| `STMT_PKG_CACHE_ID` | BIGINT | package-cache id | |
| `STMT_TEXT` | CLOB | the in-flight statement | obfuscate client-side |
| `TOTAL_ACT_TIME` | BIGINT | **milliseconds** | accumulated, NOT wall-clock (§4); 0 until metrics recorded |
| `TOTAL_ACT_WAIT_TIME` | BIGINT | **milliseconds** | wait portion of act time |
| `TOTAL_CPU_TIME` | BIGINT | **microseconds** | (unit differs from the *_TIME ms columns!) |
| `COORD_STMT_EXEC_TIME` | BIGINT | **milliseconds** | coordinator exec time |
| `WLM_QUEUE_TIME_TOTAL` | BIGINT | **milliseconds** | time queued by WLM thresholds |
| `QUERY_COST_ESTIMATE` | BIGINT | timerons | optimizer cost |
| `ROWS_READ` / `ROWS_RETURNED` | BIGINT | counts | |
| `EFFECTIVE_ISOLATION` | CHAR(2) | `UR`/`CS`/`RS`/`RR` | isolation in effect |
| `EFFECTIVE_LOCK_TIMEOUT` | BIGINT | lock timeout in effect | |
| `EFFECTIVE_QUERY_DEGREE` | BIGINT | intra-parallel degree | |
| `SECTION_NUMBER` / `STMTNO` | BIGINT/INTEGER | section identity | |
| `PACKAGE_SCHEMA` / `PACKAGE_NAME` / `PACKAGE_VERSION_ID` | VARCHAR | package identity | |
| `CLIENT_APPLNAME` / `CLIENT_USERID` / `CLIENT_WRKSTNNAME` / `CLIENT_ACCTNG` | VARCHAR(255) | client info | |
| `SERVICE_CLASS_ID` | INTEGER | WLM service class | |
| many `*_THRESHOLD_ID/_VALUE/_VIOLATED` | INTEGER/BIGINT/SMALLINT | WLM threshold tracking | for WLM-aware alerting |

`SESSION_AUTH_ID` is **NOT** in `MON_GET_ACTIVITY` — get it from `MON_GET_CONNECTION` (join on
`APPLICATION_HANDLE`) or just use `MON_CURRENT_SQL` which already does the join.

**Signature for the function:** `MON_GET_ACTIVITY(application_handle BIGINT, member INTEGER)`.
- `application_handle = NULL` → all connections; or a specific handle.
- `member = -1` → current member; `-2` → all members (DPF); a member number for one member.

---

## 7. PROOF: orders-app `STMT_TEXT` format (Datadog comment + parameter markers)

`STMT_TEXT` returned by the live sources is the **prepared** text, byte-for-byte the same as what
the package cache stores. Sampled from the package cache (the in-flight text matches this form):
```
/*dddbs='orders-app-bits',dde='local',ddps='orders-app-bits',ddprs='orders-db2'*/ UPDATE inventory_items SET quantity = ? WHERE sku = ?
/*dddbs='orders-app-bits',dde='local',ddps='orders-app-bits',ddprs='orders-db2'*/ select count(*) from inventory_items
/*dddbs='orders-app-bits',ddps='orders-app-bits'*/ SELECT sku FROM inventory_items ORDER BY RAND() FETCH FIRST 50 ROWS ONLY
```

**Implications for the samples pipeline:**
- The leading `/*dd...*/` comment must be parsed for DBM trace-correlation tags
  (`dddbs`/`dde`/`ddps`/`ddprs`) AND stripped/handled before computing the `query_signature`,
  exactly as in the existing Postgres/MySQL/SQL Server samples integrations.
- Parameter markers (`?`) are present for parameterized prepares; literal-inlined statements keep
  their literals (e.g. the seed/admin queries). Client-side obfuscation is still required to
  normalize literals and to collapse variants — Db2 does not normalize for you.
- `STMT_TEXT` is a `CLOB` (declared up to 2 MB in the package cache; same column source). The
  agent's Db2 driver (ibm_db / ibm_db_dbi) must read the CLOB fully; do not assume a small VARCHAR.

---

## 8. PROOF: fast OLTP is missed by sampling (negative result, important)

The orders inventory statements are sub-millisecond. Repeated point-in-time sampling never caught
them:

- 30× / 40× / 80× loops over `MON_CURRENT_SQL WHERE application_name='run_orders'` → **empty**
  (no rows; only `SQL1024N` connection-drop noise from the in-shell loop, see §0 loop gotcha).
- 5 back-to-back snapshots of `MON_CURRENT_SQL` (all rows) → only the **probe's own** query
  appeared each time:
  ```
  --- snap 1..5 ---
   19649 db2bp ms=0 EXECUTING "select application_handle, substr(application_name,1,12 ..."
  ```
- 40 external `docker exec` samples of `MON_GET_ACTIVITY` (excluding the probe) caught only a
  **leftover slow cartesian** I had launched, never an orders OLTP statement:
  ```
  19697 READ_DML "select count(*) from inventory_items a, inventory_items b, inventory_items c where ..."
  ```
- Steady-state count of `EXECUTING` activities was typically **2** (the probe + ~1 other),
  confirming there is almost never a long-running orders statement in flight.

**Implication for the plan:** sampling `MON_CURRENT_SQL` is an ASH-style signal that surfaces
*long / waiting / blocked* statements and current concurrency — it will **systematically miss
short statements**. Pair it with the cumulative `MON_GET_PKG_CACHE_STMT` source (sibling doc) for
complete per-statement metrics. For "active sessions" counting, use the snapshot row count; for
"top slow queries right now", use `ELAPSED_TIME_MSEC` ordering. Sample interval should be tuned
(e.g. 1 s like other DBM ASH collectors) accepting that sub-interval statements are invisible.

---

## 9. `MON_GET_UNIT_OF_WORK` and `SYSIBMADM.MON_CURRENT_UOW` (transaction-level)

`TABLE(MON_GET_UNIT_OF_WORK(application_handle, member))` — per-transaction, **no statement text**.
Confirmed-present key columns (live `DESCRIBE` grep):

| Column | Type | Meaning / unit |
|---|---|---|
| `APPLICATION_HANDLE` | BIGINT | connection id |
| `UOW_ID` | INTEGER | transaction id |
| `WORKLOAD_OCCURRENCE_STATE` | VARCHAR | transaction state (values below) |
| `UOW_START_TIME` / `UOW_STOP_TIME` | TIMESTAMP | transaction start/stop |
| `TOTAL_APP_COMMITS` / `TOTAL_APP_ROLLBACKS` | BIGINT | counts |
| `TOTAL_ROLLBACK_TIME` | BIGINT | ms |
| `TOTAL_RQST_TIME` | BIGINT | ms (advances live, §4) |
| `TOTAL_WAIT_TIME` | BIGINT | ms |
| `TOTAL_CPU_TIME` | BIGINT | microseconds |
| `TOTAL_ACT_TIME` | BIGINT | ms |
| `APP_RQSTS_COMPLETED_TOTAL` | BIGINT | requests completed |
| `ROWS_READ` / `ROWS_RETURNED` | BIGINT | UOW totals |
| `CLIENT_APPLNAME` / `SESSION_AUTH_ID` | VARCHAR | identity |

**`WORKLOAD_OCCURRENCE_STATE` values observed live:** `UOWEXEC` (executing), `UOWWAIT`
(transaction open, between statements — i.e. app is idle-in-transaction-ish / waiting on client),
`TRANSIENT` (transitioning), `AUTONOMOUS_WORKLOAD` (running an autonomous routine). Steady-state
orders connections sat in `UOWWAIT` between requests.

`SYSIBMADM.MON_CURRENT_UOW` view columns (live):
`COORD_MEMBER, UOW_ID, APPLICATION_HANDLE, APPLICATION_NAME, SESSION_AUTH_ID, CLIENT_APPLNAME,
ELAPSED_TIME_SEC, ELAPSED_TIME_MSEC, WORKLOAD_OCCURRENCE_STATE, TOTAL_CPU_TIME,
TOTAL_ROWS_MODIFIED, TOTAL_ROWS_READ, TOTAL_ROWS_RETURNED` — again **no `STMT_TEXT`**. Useful for
"how long has this transaction been open" and detecting long-open / idle-in-transaction sessions,
NOT for statement text.

**Use `MON_GET_UNIT_OF_WORK` / `MON_CURRENT_UOW` to enrich an activity sample** with transaction
state and open-transaction age, not as the primary statement source.

---

## 10. Monitoring configuration (live `DBCFG`)

```bash
db2 -x "select substr(name,1,22), substr(value,1,12) from sysibmadm.dbcfg
        where name in ('mon_act_metrics','mon_req_metrics','mon_uow_data','mon_uow_execlist','mon_uow_pkglist')"
```
```
mon_req_metrics   BASE
mon_act_metrics   BASE      <- enables activity timing columns (TOTAL_ACT_TIME, waits). Sufficient.
mon_uow_data      NONE      <- UOW statement/exec lists disabled (not needed for this source)
mon_uow_pkglist   OFF
mon_uow_execlist  OFF
```
- Identity + `STMT_TEXT` + `ACTIVITY_STATE` + `ELAPSED_TIME_*` need **no special config**.
- Activity timing columns (`TOTAL_ACT_TIME`, `TOTAL_ACT_WAIT_TIME`, `COORD_STMT_EXEC_TIME`,
  `WLM_QUEUE_TIME_TOTAL`) require `mon_act_metrics >= BASE` (satisfied by default). The agent
  should gate timing-derived sample fields on `mon_act_metrics <> 'NONE'` and degrade gracefully.
- `MON_GET_ACTIVITY` requires the caller to hold `SYSMON`/`SYSCTRL`/`SYSMAINT`/`SYSADM` or
  `DATAACCESS` / `EXECUTE` on the routine — `DB2INST1` has it here; for a least-privilege agent
  user, `SYSMON` authority is the documented minimum for the `MON_GET_*` family.

---

## 11. IBM documentation citations (Db2 12.1)

- `MON_GET_ACTIVITY` table function (12.1):
  https://www.ibm.com/docs/en/db2/12.1?topic=mtf-mon-get-activity-table-function
- `MON_GET_UNIT_OF_WORK` table function (12.1):
  https://www.ibm.com/docs/en/db2/12.1?topic=mtf-mon-get-unit-work-table-function
- `MON_CURRENT_SQL` administrative view (12.1):
  https://www.ibm.com/docs/en/db2/12.1?topic=views-mon-current-sql-administrative-view
- `MON_CURRENT_UOW` administrative view (12.1):
  https://www.ibm.com/docs/en/db2/12.1?topic=views-mon-current-uow-administrative-view
- `MON_GET_CONNECTION` table function (12.1):
  https://www.ibm.com/docs/en/db2/12.1?topic=mtf-mon-get-connection-table-function
- Monitor element reference (units/semantics per element, e.g. `total_act_time`, `total_cpu_time`,
  `activity_state`, `activity_type`, `workload_occurrence_state`):
  https://www.ibm.com/docs/en/db2/12.1?topic=monitoring-monitor-elements
- SYSMON authority (least-privilege for MON_GET_*):
  https://www.ibm.com/docs/en/db2/12.1?topic=authorities-sysmon-authority
> Note: live `db2level` is `12.1.4.0`; the older `queries.py` links in the current integration
> point at 11.1 KC URLs (`SSEPGG_11.1.0`). Re-cite against 12.1 docs above; semantics for these
> table functions are stable 11.5→12.1 but column *sets* grow — introspect at runtime.

---

## 12. Current integration state (code references)

- `/home/bits/dd/integrations-core/ibm_db2/datadog_checks/ibm_db2/queries.py` — defines only
  cumulative/system metric queries (`MON_GET_INSTANCE`, `MON_GET_DATABASE`, `MON_GET_BUFFERPOOL`,
  `MON_GET_TABLESPACE`, `MON_GET_TRANSACTION_LOG`). **No** `MON_CURRENT_SQL` / `MON_GET_ACTIVITY` /
  `MON_GET_UNIT_OF_WORK` / activity sampling.
- `/home/bits/dd/integrations-core/ibm_db2/datadog_checks/ibm_db2/ibm_db2.py` — main check; a grep
  for `mon_current_sql|mon_get_activity|mon_get_unit_of_work|mon_current_uow|activity|samples`
  returns nothing. No DBM samples / ASH path exists yet.
- Conclusion: the live-activity / DBM "samples" feature is **greenfield** for `ibm_db2`. Model the
  collector on the existing DBM samples integrations (Postgres `pg_stat_activity`,
  SQL Server `dm_exec_requests`), mapping their fields to §2's `MON_CURRENT_SQL` columns, and join
  to the package-cache metrics (sibling doc) via `EXECUTABLE_ID` for query-signature linkage.

---

## 13. Workload reference (so the next agent knows what generates the activity)

Source: `/home/bits/go/src/github.com/DataDog/dbm/orders/workloads/inventoryworkload.go`. The Db2
path runs (all sub-millisecond OLTP, hence invisible to sampling, §8):
- `select * from inventory_items where sku = 'item1'` (`goodQuery`, literal-inlined)
- `select count(*) from inventory_items` (`countQuery`)
- `SELECT sku FROM inventory_items ORDER BY RAND() FETCH FIRST 50 ROWS ONLY` (shipment pick)
- A transaction: `SELECT quantity FROM inventory_items WHERE sku = ?` →
  `UPDATE inventory_items SET quantity = ? WHERE sku = ?` →
  `INSERT INTO shipments (sku, quantity) VALUES (?, ?)` → `COMMIT`
- Driver: Go `database/sql` via ibm-db Db2 driver; statements carry the DBM
  `/*dddbs=...*/` comment (§7).

To deliberately generate catchable in-flight activity for testing the collector, use either
`CALL dbms_lock.sleep(N)` (autonomous routine; shows as `ACTIVITY_TYPE=CALL`,
`WORKLOAD_OCCURRENCE_STATE=AUTONOMOUS_WORKLOAD`) or a self-cartesian
`select count(*) from inventory_items a, inventory_items b, inventory_items c where ...`
(shows as `ACTIVITY_TYPE=READ_DML`, `WORKLOAD_OCCURRENCE_STATE=UOWEXEC`).
Cancel a runaway with `db2 force application (<handle>)` (verified working;
`WLM_CANCEL_ACTIVITY` is not installed in this community image).
