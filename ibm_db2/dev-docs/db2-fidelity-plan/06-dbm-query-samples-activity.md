# 06 — DBM Query Samples + Activity: the Db2 In-Flight Capture Collector

**Audience:** an engineer or AI agent who already understands Datadog DBM "query samples" and
"activity" for Postgres (`pg_stat_activity`) or MySQL (`activity.py` over `performance_schema.threads`),
but has little Db2 background. This doc designs the Db2 analog of the *in-flight / active-session*
capture end-to-end so you can implement it without re-deriving the framework.

**What "samples + activity" is, in two sentences:** every short interval, take one point-in-time
snapshot of the statements that are *currently executing* in the database (the `pg_stat_activity`
analog), obfuscate + sign each one so it links to the query-metrics rows from doc 05, and ship it.
The snapshot feeds two event streams off one query: an **activity** event (the whole active-session
list + connection counts → the DBM "Active Sessions"/ASH page) and **sample** events (per-statement
`fqt`/`plan` events → the "Query Samples" page).

**Where this fits in the plan:**
- [`03-reference-architecture.md`](03-reference-architecture.md) §1.3–§1.5 (framework pieces:
  `DBMAsyncJob`, `RateLimitingTTLCache`, payload contract) and §2.2–§2.3 (the samples/activity
  pipeline shapes). Read it first if you have not.
- [`05-dbm-query-metrics.md`](05-dbm-query-metrics.md) — the cumulative package-cache metrics
  collector. This doc's samples link to those metrics rows by **`query_signature`** (§3); doc 05
  emits the `fqt` event from the *metrics* path, this doc emits `fqt`/`plan`/`activity` from the
  *sampling* path. The two paths must compute `query_signature` identically.
- [`07-dbm-execution-plans.md`](07-dbm-execution-plans.md) — the `dbm_type:"plan"` content
  (running EXPLAIN, assembling the plan tree). This doc produces the **plan-event envelope and
  schedules the plan attempt per sampled statement**, but defers the actual EXPLAIN mechanics
  (section explain / EXPLAIN tables → JSON) to 07. The highest-risk feature.
- [`09-implementation-architecture.md`](09-implementation-architecture.md) — the concrete module
  layout, check wiring (`run_job_loop`/`cancel`), and per-job `ibm_db` connection isolation that
  this collector plugs into.
- [`12-risks-open-questions.md`](12-risks-open-questions.md) — the OLTP-blind-spot limitation
  (this doc §4), the obfuscator-dialect open question (shared with 05), and the WLM
  activity-event-monitor follow-on (§4.4).

> **Authoritative source for everything Db2-specific below:**
> [`_research/db2-live-activity.md`](_research/db2-live-activity.md) — empirical probe of
> `SYSIBMADM.MON_CURRENT_SQL`, `TABLE(MON_GET_ACTIVITY(NULL,-2))`, and
> `TABLE(MON_GET_UNIT_OF_WORK(NULL,-1))` on our live Db2 **12.1.4** container (2026-06-15),
> including the **fast-OLTP sub-interval blind-spot** negative result (§4.1). Claims I could not
> verify against that probe are tagged **(verify)**.

---

## 0. TL;DR for the implementer

1. **Primary source:** `SYSIBMADM.MON_CURRENT_SQL` — one row per *in-flight activity* (statement),
   with `STMT_TEXT`, identity (`APPLICATION_HANDLE`/`APPLICATION_ID`/`APPLICATION_NAME`/
   `SESSION_AUTH_ID`), wall-clock `ELAPSED_TIME_MSEC`, `ACTIVITY_STATE`/`ACTIVITY_TYPE`. This is the
   `pg_stat_activity` analog. It is a thin view over `MON_GET_ACTIVITY(NULL,-2)` joined to
   `MON_GET_CONNECTION` (`db2-live-activity.md` §5).
2. **When you need more columns** (stable `EXECUTABLE_ID` to link to package-cache metrics, accumulated
   wait time) than the view exposes (19 cols), query `TABLE(MON_GET_ACTIVITY(NULL,-2))` directly and
   join `MON_GET_CONNECTION` — i.e. reproduce the view but add `EXECUTABLE_ID`, `STMT_PKG_CACHE_ID`,
   `TOTAL_ACT_TIME`, `TOTAL_ACT_WAIT_TIME`, `LOCAL_START_TIME` (`db2-live-activity.md` §2).
3. **Transaction enrichment:** `TABLE(MON_GET_UNIT_OF_WORK(NULL,-1))` for transaction state
   (`WORKLOAD_OCCURRENCE_STATE`: `UOWEXEC`/`UOWWAIT`/`TRANSIENT`/`AUTONOMOUS_WORKLOAD`) and open-txn
   age — **it has no statement text** (`db2-live-activity.md` §9). Use it to flag
   idle-in-transaction sessions, never as the statement source.
4. **Obfuscate + sign client-side.** `STMT_TEXT` is the prepared form, carries a leading `/*dd...*/`
   comment and `?` markers; strip/parse the comment, obfuscate, compute `query_signature` exactly
   like doc 05 so samples link to metrics.
5. **Honest limitation:** sub-millisecond OLTP is *invisible* to point-in-time `MON_GET` sampling
   (§4.1, proven live). This is an ASH-style long/waiting-query signal, **not** a complete request
   log. The cumulative package cache (doc 05) is what captures every statement; the WLM activity
   event monitor (§4.4) is the future complement.
6. **One `DBMAsyncJob`** (`Db2StatementSamples`) runs both streams off one snapshot per loop, exactly
   like postgres. Default sample interval **1 s**, activity reported at most every **10 s**.
7. **Privilege:** the agent user needs `SYSMON` (or `DATAACCESS` / `EXECUTE` on the `MON_GET_*`
   routines) — §6.

---

## 1. Source of truth: the three live sources

### 1.1 Decision matrix (from the live probe)

Three sources at three granularities (`db2-live-activity.md` §1, §2). All return only
*currently-in-progress* work — a transient point-in-time snapshot, **not** cumulative history.

| Need | `MON_CURRENT_SQL` | `MON_GET_ACTIVITY` | `MON_GET_UNIT_OF_WORK` |
|---|---|---|---|
| In-flight statement text (`STMT_TEXT`) | **YES** | YES | **NO** |
| Stable stmt identity (`EXECUTABLE_ID`) — link to doc-05 metrics | no | **YES** | no |
| Application handle / id / name | YES | handle+`APPL_ID` | handle+`APPL_ID` |
| Session auth id (user) | **YES** | no¹ | YES |
| **Wall-clock elapsed of stmt** | **YES** (`ELAPSED_TIME_MSEC`) | no² | no² |
| Activity state / type | YES | YES | no |
| Transaction state | no | no | **YES** (`WORKLOAD_OCCURRENCE_STATE`) |
| Accumulated act time / waits | `TOTAL_CPU_TIME` only | **YES** (`TOTAL_ACT_TIME`, `TOTAL_ACT_WAIT_TIME`) | UOW totals |

¹ `MON_GET_ACTIVITY` has the handle; join `MON_GET_CONNECTION` for `SESSION_AUTH_ID`.
² Raw functions give accumulated/element times, not wall-clock since statement start;
`MON_CURRENT_SQL` computes wall-clock in the view (`db2-live-activity.md` §5).

**Mapping to the pg/mysql model** (`_research/code-postgres-dbm-samples.md` §13,
`_research/code-mysql-dbm.md` §3):

| Concept | Postgres | MySQL | **Db2** |
|---|---|---|---|
| Active-session list | `pg_stat_activity` | `performance_schema.threads` | `MON_CURRENT_SQL` (rows where `ACTIVITY_STATE='EXECUTING'`) |
| In-flight SQL text | `query` | `events_statements_current.sql_text` | `STMT_TEXT` |
| Session id | `pid` | `processlist_id`/`thread_id` | `APPLICATION_HANDLE` |
| User | `usename` | `processlist_user` | `SESSION_AUTH_ID` |
| App name | `application_name` | `processlist_user`/program | `APPLICATION_NAME` |
| Wall-clock duration | `clock_timestamp() - query_start` | `now - timer_start` | `ELAPSED_TIME_MSEC` (view-computed) |
| Wait dimension | `wait_event_type`/`wait_event` | `events_waits_current.event_name` | `ACTIVITY_STATE` + `TOTAL_ACT_WAIT_TIME` (no per-event wait name in this source — see §1.5) |
| Txn state | `state` (`idle in transaction`) | n/a | `WORKLOAD_OCCURRENCE_STATE` (`UOWWAIT` ≈ idle-in-txn) |
| Blocking | `pg_blocking_pids()` | `data_lock_waits` | `SYSIBMADM.MON_LOCKWAITS` (§1.6) |
| "now" from server | `clock_timestamp()` | `unix_timestamp()` | `CURRENT TIMESTAMP` |

### 1.2 Primary sample query — `MON_CURRENT_SQL`

Start here. This is the recommended primary collection query (`db2-live-activity.md` §2). It is the
Db2 analog of postgres's `PG_STAT_ACTIVITY_QUERY` (`_research/code-postgres-dbm-samples.md` §2.3).

```sql
SELECT
    CURRENT TIMESTAMP        AS now,          -- server "now"; compute durations against the server clock
    APPLICATION_HANDLE,                       -- BIGINT  : session id (the "pid")
    APPLICATION_ID,                           -- VARCHAR : globally-unique connection string
    APPLICATION_NAME,                         -- VARCHAR : 'run_orders', 'agent', 'db2bp', ...
    SESSION_AUTH_ID,                          -- VARCHAR : the user
    CLIENT_APPLNAME,                          -- VARCHAR : client-set app name (often '-')
    UOW_ID,                                   -- INTEGER : transaction id within the connection
    ACTIVITY_ID,                              -- INTEGER : activity id within the UOW
    COORD_MEMBER,                             -- SMALLINT
    ELAPSED_TIME_MSEC,                        -- INTEGER : *** wall-clock elapsed of the in-flight stmt ***
    ACTIVITY_STATE,                           -- VARCHAR : 'EXECUTING', 'IDLE', ...
    ACTIVITY_TYPE,                            -- VARCHAR : 'READ_DML','WRITE_DML','DDL','CALL','LOAD','OTHER'
    TOTAL_CPU_TIME,                           -- BIGINT  : MICROSECONDS (note: us, not ms)
    ROWS_READ,                                -- BIGINT
    ROWS_RETURNED,                            -- BIGINT
    QUERY_COST_ESTIMATE,                      -- BIGINT  : optimizer timerons
    DIRECT_READS,                             -- BIGINT
    DIRECT_WRITES,                            -- BIGINT
    STMT_TEXT                                 -- CLOB    : the in-flight statement (obfuscate client-side!)
FROM SYSIBMADM.MON_CURRENT_SQL
WHERE APPLICATION_HANDLE <> ?                 -- exclude the agent's own session (its handle, bound param)
  AND STMT_TEXT IS NOT NULL
ORDER BY ELAPSED_TIME_MSEC DESC               -- longest-running first (matches pg ORDER BY timer_wait)
```

Key points (each cross-checks a pg/mysql behavior):

- **`CURRENT TIMESTAMP AS now`** mirrors postgres's `clock_timestamp() as now` — compute all durations
  from the server clock, never the agent clock (`_research/code-postgres-dbm-samples.md` §2.3).
- **Exclude the agent's own session.** Postgres uses `pid != pg_backend_pid()`; mysql uses
  `processlist_id != CONNECTION_ID()`. The Db2 probe *always* shows its own query as a row
  (`db2-live-activity.md` §4) — bind the agent connection's `APPLICATION_HANDLE`. Get it once on the
  job's dedicated connection via `SELECT APPLICATION_HANDLE FROM TABLE(MON_GET_CONNECTION(NULL,-1))
  WHERE ... ` or `VALUES (MON_GET_APPLICATION_HANDLE())` **(verify the scalar helper exists in
  12.1)** — fall back to filtering `APPLICATION_NAME='agent'` *and* the handle.
- **The triple `(APPLICATION_HANDLE, UOW_ID, ACTIVITY_ID)`** uniquely identifies an in-flight
  activity within a database activation (`db2-live-activity.md` §3) — use it as the per-row dedup key.
- **Filter strategy — keep it permissive, filter in Python.** Postgres filters `state`/`query` in SQL;
  for Db2, `ACTIVITY_STATE='EXECUTING'` is the closest "is active" predicate (live, steady-state
  `EXECUTING` count ≈ 2, mostly the probe + ~1 — `db2-live-activity.md` §8). Whether you push
  `ACTIVITY_STATE='EXECUTING'` into the WHERE or filter in `_normalize_rows` depends on whether the
  activity stream also wants `IDLE` sessions (postgres's activity stream keeps non-idle + background;
  see §5.2). Recommended: select all rows, decide active-vs-idle in Python (§5.2).
- **Unit trap:** `TOTAL_CPU_TIME` is **microseconds**; `ELAPSED_TIME_MSEC` is **milliseconds**. Do
  *not* copy MySQL's picosecond math (`_research/code-mysql-dbm.md` §6.6); Db2 `MON_GET_*` timings are
  ms except CPU which is µs (`db2-live-activity.md` §3, §6).

### 1.3 Richer sample query — raw `MON_GET_ACTIVITY` (when you need `EXECUTABLE_ID`)

`MON_CURRENT_SQL` exposes only **19** of `MON_GET_ACTIVITY`'s **418** columns and crucially **omits
`EXECUTABLE_ID`** — the stable statement identity that links a sample to its package-cache metrics row
(doc 05 keys on `HEX(EXECUTABLE_ID)`). When you want that link or the accumulated wait time, query the
raw function and reproduce the view's join + wall-clock math yourself (`db2-live-activity.md` §2, §5):

```sql
WITH ACT AS (
    SELECT APPLICATION_HANDLE, UOW_ID, ACTIVITY_ID, MEMBER, COORD_MEMBER,
           ACTIVITY_STATE, ACTIVITY_TYPE, STMT_TEXT,
           EXECUTABLE_ID,                 -- <<< the link key to MON_GET_PKG_CACHE_STMT (doc 05)
           STMT_PKG_CACHE_ID,
           LOCAL_START_TIME,
           TOTAL_ACT_TIME,                -- ms  : accumulated (NOT wall-clock; 0 until metrics recorded)
           TOTAL_ACT_WAIT_TIME,           -- ms  : wait portion of act time  (wait signal)
           TOTAL_CPU_TIME,                -- us
           QUERY_COST_ESTIMATE, ROWS_READ, ROWS_RETURNED,
           EFFECTIVE_ISOLATION
    FROM TABLE(MON_GET_ACTIVITY(NULL, -2))           -- NULL = all handles; -2 = all members
)
SELECT CURRENT TIMESTAMP AS now,
       A.APPLICATION_HANDLE, C.APPLICATION_ID, C.APPLICATION_NAME, C.SESSION_AUTH_ID,
       C.CLIENT_APPLNAME,
       A.UOW_ID, A.ACTIVITY_ID, A.COORD_MEMBER,
       -- wall-clock elapsed, ms (the view's ELAPSED_TIME_MSEC formula, db2-live-activity.md §5):
       CAST( ( DAYS(CURRENT TIMESTAMP) - DAYS(A.LOCAL_START_TIME) ) * 86400000
           + ( MIDNIGHT_SECONDS(CURRENT TIMESTAMP) - MIDNIGHT_SECONDS(A.LOCAL_START_TIME) ) * 1000
           + ( MICROSECOND(CURRENT TIMESTAMP) - MICROSECOND(A.LOCAL_START_TIME) ) / 1000
           AS BIGINT)                                   AS elapsed_time_msec,   -- (verify arithmetic)
       A.ACTIVITY_STATE, A.ACTIVITY_TYPE,
       HEX(A.EXECUTABLE_ID)        AS executable_id,     -- hex-encode the FOR BIT DATA id (matches doc 05)
       A.STMT_PKG_CACHE_ID, A.TOTAL_ACT_TIME, A.TOTAL_ACT_WAIT_TIME, A.TOTAL_CPU_TIME,
       A.QUERY_COST_ESTIMATE, A.ROWS_READ, A.ROWS_RETURNED, A.EFFECTIVE_ISOLATION,
       A.STMT_TEXT
FROM ACT A
JOIN TABLE(MON_GET_CONNECTION(NULL, -2)) C
  ON C.APPLICATION_HANDLE = A.APPLICATION_HANDLE
 AND C.MEMBER             = A.COORD_MEMBER
WHERE A.MEMBER = A.COORD_MEMBER                          -- one row per activity on the coordinator
  AND A.APPLICATION_HANDLE <> ?                          -- exclude the agent's own handle
ORDER BY elapsed_time_msec DESC
```

Notes:
- The view double-evaluates `MON_GET_ACTIVITY(NULL,-2)` (CTE + join); evaluate it once and self-join,
  or — as above — scan once and add the columns you need (`db2-live-activity.md` §5 "Takeaways").
- `HEX(EXECUTABLE_ID)` matches doc 05's row identity so a sample can join to the cumulative metrics row.
- `LOCAL_START_TIME`-based wall-clock arithmetic: the exact view formula uses
  `JULIAN_DAY`/`HOUR`/`MINUTE`/`SECOND`/`MICROSECOND` deltas (`db2-live-activity.md` §5). The
  `DAYS`/`MIDNIGHT_SECONDS` form above is a simpler equivalent — **(verify)** against the container,
  or just collect `LOCAL_START_TIME` raw and compute `now - LOCAL_START_TIME` in Python.
- **Column introspection (do this).** Like postgres's `LIMIT 0` `cursor.description` probe
  (`_research/code-postgres-dbm-samples.md` §2.2), and like doc 05 §3.2, discover the available column
  set once (`DESCRIBE` or a `FETCH FIRST 0 ROWS ONLY` probe) and intersect with the desired set. The
  418-column set grows across fixpacks (`db2-live-activity.md` §11); do not hard-code.

**Which query to ship?** Start with `MON_CURRENT_SQL` (§1.2) — it is simpler, view-maintained, and
already has wall-clock elapsed + identity. Switch to the raw form (§1.3) only once doc 05 is wired and
you want the `EXECUTABLE_ID` sample→metrics linkage and `TOTAL_ACT_WAIT_TIME` wait signal. They are
mutually exclusive per loop; pick one. (Recommended end-state: the raw form, for the link key.)

### 1.4 Transaction enrichment — `MON_GET_UNIT_OF_WORK`

Optional second small query per loop to enrich each session's row (or just the active/long ones) with
transaction context. **No `STMT_TEXT`** (`db2-live-activity.md` §9):

```sql
SELECT APPLICATION_HANDLE, UOW_ID,
       WORKLOAD_OCCURRENCE_STATE,    -- UOWEXEC | UOWWAIT | TRANSIENT | AUTONOMOUS_WORKLOAD
       UOW_START_TIME,               -- transaction start (for open-txn age)
       TOTAL_RQST_TIME,              -- ms
       TOTAL_WAIT_TIME,              -- ms
       TOTAL_APP_COMMITS, TOTAL_APP_ROLLBACKS
FROM TABLE(MON_GET_UNIT_OF_WORK(NULL, -1))
WHERE APPLICATION_HANDLE <> ?
```

Join to the activity rows on `(APPLICATION_HANDLE, UOW_ID)`. `WORKLOAD_OCCURRENCE_STATE='UOWWAIT'`
(transaction open, between statements) is the Db2 analog of postgres `state='idle in transaction'` —
surface it so the activity stream can show idle-in-transaction sessions and open-transaction age (the
postgres collector specifically timestamps completed idle txns at `state_change`, see
`_research/code-postgres-dbm-samples.md` §8.1). `MON_GET_UNIT_OF_WORK` statement/exec lists are OFF by
default (`mon_uow_data=NONE`) but are **not needed** here (`db2-live-activity.md` §10).

### 1.5 Wait information (what Db2 gives you, and what it doesn't)

Db2's in-flight sources do **not** expose a per-activity wait *event name* the way
`pg_stat_activity.wait_event` or mysql `events_waits_current.event_name` do. What you have at sample
time:
- `ACTIVITY_STATE` — coarse: `EXECUTING` vs `IDLE`.
- `TOTAL_ACT_WAIT_TIME` (raw `MON_GET_ACTIVITY`, ms) — accumulated wait portion of activity time; a
  *magnitude*, not a *named* wait. Requires `mon_act_metrics >= BASE` (default; §6).
- For a true wait-event dimension you would mine the detailed `MON_GET_ACTIVITY` `_DETAILS` /
  request-metrics columns or `MON_GET_AGENT`/`WLM_GET_SERVICE_CLASS_AGENTS` (`_research/code-mysql-dbm.md`
  §3.1 lists the analogous Db2 functions). **(verify)** which wait columns are populated for in-flight
  activities — out of scope for first fidelity; ship `ACTIVITY_STATE` + `TOTAL_ACT_WAIT_TIME` and
  defer named waits.

So the Db2 activity stream is a **state + duration + concurrency** signal first, and a coarse wait
signal second. This is acceptable for v1 (postgres shipped without wait events originally too).

### 1.6 Blocking detection (optional, gated)

Postgres uses `pg_blocking_pids()` and mysql `performance_schema.data_lock_waits`, each gated behind a
config flag and only computed on the activity cadence (`_research/code-postgres-dbm-samples.md` §2.3,
`_research/code-mysql-dbm.md` §3.4). The Db2 analog is **`SYSIBMADM.MON_LOCKWAITS`** (or
`SNAPLOCKWAIT`) — one row per lock-wait edge with `HLD_APPLICATION_HANDLE` (blocker) and
`REQ_APPLICATION_HANDLE` (waiter) **(verify exact column names against 12.1)**. Join it to the
activity rows to annotate `blocking_app_handle` / `waiting_on`. Gate behind
`query_activity.collect_blocking_queries` (default `false`, mirroring mysql §3.9). Defer to a follow-up;
detail belongs with the locking map (`_research/map-locking-concurrency.md`).

---

## 2. The job: `Db2StatementSamples` (one `DBMAsyncJob`, two streams)

Mirror the postgres design exactly: **one** job produces both the plan/fqt sample events *and* the
activity event from a *single snapshot per loop* (`_research/code-postgres-dbm-samples.md` §1).
MySQL splits them into two jobs (`MySQLStatementSamples` + `MySQLActivity`,
`_research/code-mysql-dbm.md` §0); postgres unifies them. **Use the postgres unified model** for Db2 —
the snapshot is the expensive part and we want it taken once.

```python
class Db2StatementSamples(DBMAsyncJob):
    def __init__(self, check, config, connection_args):
        # collection interval: samples cadence drives the loop; if samples disabled,
        # fall back to the (slower) activity cadence  (pg statement_samples.py:148-164)
        collection_interval = config.query_samples.collection_interval        # default 1 s
        if not config.query_samples.enabled:
            collection_interval = config.query_activity.collection_interval   # default 10 s

        super().__init__(
            check,
            run_sync=config.query_samples.run_sync,                  # default False
            enabled=(config.query_samples.enabled or config.query_activity.enabled),
            min_collection_interval=config.min_collection_interval,
            dbms="db2",                                              # → dd.db2.async_job.* metrics
            rate_limit=1 / collection_interval,                      # ConstantRateLimiter pacing
            job_name="query-samples",
            shutdown_callback=self._close_db_conn,
            expected_db_exceptions=(ibm_db_dbi.DatabaseError,),      # (verify driver exc class)
        )
        self._config = config
        self._connection_args = connection_args
        self._db = None                                             # dedicated ibm_db connection

        # obfuscator options assembled once → JSON string (see §3); dbms hint 'db2' (verify)
        self._obfuscate_options = to_native_string(json.dumps(config.obfuscator_options))

        # activity gating: never report activity more often than samples (pg §1.1)
        self._activity_coll_enabled  = config.query_activity.enabled
        self._plan_coll_enabled      = config.query_samples.enabled
        self._activity_coll_interval = max(config.query_activity.collection_interval,
                                           collection_interval)
        self._activity_max_rows      = config.query_activity.payload_row_limit   # default 3500
        self._last_activity_report_time = 0

        # rate-limiting caches (sizes/TTLs in §4.2)
        self._explained_statements_ratelimiter = RateLimitingTTLCache(
            maxsize=config.query_samples.explained_queries_cache_maxsize,        # 5000
            ttl=60 * 60 / config.query_samples.explained_queries_per_hour_per_query)  # 60/hr → 60 s
        self._seen_samples_ratelimiter = RateLimitingTTLCache(
            maxsize=config.query_samples.seen_samples_cache_maxsize,             # 10000
            ttl=60 * 60 / config.query_samples.samples_per_hour_per_query)       # 15/hr → 240 s
        self._collection_strategy_cache = TTLCache(maxsize=1000, ttl=300)        # per-DB explain state
        self._agent_handle = None                                               # self-exclusion (§1.2)
```

### 2.1 Main loop — `run_job` → `_collect_statement_samples`

```python
def run_job(self):
    # strip dd.internal* tags; build comma-joined ddtags (samples) and list ddtags (activity)
    self.tags = [t for t in self._tags if not t.startswith('dd.internal')]
    self._collect_statement_samples()

@tracked_method(agent_check_getter=lambda self: self._check)
def _collect_statement_samples(self):
    # 1. decide whether THIS tick also emits an activity snapshot (cadence gate, computed FIRST so
    #    expensive enrichment — blocking, UOW join — is only done on activity ticks, pg §1.2)
    collect_activity = self._should_report_activity()

    # 2. ONE snapshot of the active-session source (§1.2 or §1.3)
    rows = self._get_active_statements()

    # 3. filter + obfuscate + sign each row (§3)
    rows = self._filter_and_normalize_rows(rows)

    # 4. sample/plan events (gated by query_samples.enabled)
    if self._plan_coll_enabled:
        submitted = 0
        for event in self._collect_sample_events(rows):
            self._check.database_monitoring_query_sample(
                json.dumps(event, default=default_json_event_encoding))
            submitted += 1
        self._check.count("dd.db2.collect_statement_samples.events_submitted.count",
                          submitted, tags=self.tags, raw=True)

    # 5. activity event (gated by cadence + query_activity.enabled)
    if collect_activity:
        connections = self._get_connection_counts()          # §5.3 aggregate query
        event = self._create_activity_event(rows, connections)
        self._check.database_monitoring_query_activity(
            json.dumps(event, default=default_json_event_encoding))
        self._last_activity_report_time = time.time()

def _should_report_activity(self):
    return (self._activity_coll_enabled
            and time.time() - self._last_activity_report_time >= self._activity_coll_interval)
```

This is structurally identical to postgres `_collect_statement_samples`
(`_research/code-postgres-dbm-samples.md` §1.2): activity decision first, one snapshot, normalize, then
fan out to the two streams. Each DB query first checks `self._cancel_event.is_set()` (the
`DBMAsyncJob` cancel contract, `_research/code-base-framework.md` §E.2).

---

## 3. Capture: statement text → obfuscate → `query_signature` (the link to doc 05)

The whole point of signing samples is that the backend can join a sample event to the query-metrics
time series and the FQT — all keyed by **`query_signature`**. So this step must be *byte-for-byte the
same obfuscation+signature pipeline as doc 05* (`_research/code-base-framework.md` §D,
`_research/code-dbm-payload-contract.md` §3.4).

`STMT_TEXT` here is the **prepared** form, identical to what the package cache stores
(`db2-live-activity.md` §6, §7): it carries the leading Datadog SQLCommenter tag and `?` parameter
markers, e.g.

```
/*dddbs='orders-app-bits',dde='local',ddps='orders-app-bits',ddprs='orders-db2'*/ UPDATE inventory_items SET quantity = ? WHERE sku = ?
```

### 3.1 Normalize each row

```python
def _filter_and_normalize_rows(self, rows):
    normalized = []
    for row in rows:
        stmt = row.get('STMT_TEXT')
        if not stmt:                                  # skip empty (pg: TRIM(query) != '')
            continue
        try:
            # replace_null_character=True: STMT_TEXT is CLOB; guard embedded nulls (base §D.1; doc 05 §2)
            result = obfuscate_sql_with_metadata(stmt, self._obfuscate_options,
                                                 replace_null_character=True)
        except Exception:
            self._check.count("dd.db2.statement_samples.error", 1,
                              tags=self.tags + ["error:sql-obfuscate"], raw=True)
            continue
        obfuscated = result['query']
        row['statement']       = obfuscated
        row['query_signature'] = compute_sql_signature(obfuscated)   # base utils/db/sql.py — DO NOT alter
        meta = result['metadata']
        row['dd_tables']   = meta.get('tables')
        row['dd_commands'] = meta.get('commands')
        row['dd_comments'] = meta.get('comments')                    # the /*dd...*/ trace tags land here
        row['query_truncated'] = self._truncation_state(stmt)        # §3.3
        normalized.append(row)
    return normalized
```

- `obfuscate_sql_with_metadata` → `datadog_agent.obfuscate_sql(query, options)`. The Go obfuscator
  strips literals, parses the leading `/*dd...*/` comment into `metadata['comments']` (the
  `dddbs`/`dde`/`ddps`/`ddprs` trace-correlation tags, used downstream for trace↔query linking), and
  normalizes the statement. **The same call in doc 05 must yield the same `query_signature`** — so
  share the obfuscator-options JSON construction with doc 05.
- `compute_sql_signature` = `mmh3.hash64(obfuscated_bytes, signed=False)[0]` as hex
  (`_research/code-base-framework.md` §D.3). **Must match the APM resource hash** — never change.
- `?` markers and literal-inlined seed/admin statements both occur; the Go obfuscator normalizes both
  (`db2-live-activity.md` §7).

### 3.2 The obfuscator dialect open question (shared with doc 05)

Set `obfuscator_options['dbms'] = 'db2'` (`_research/code-base-framework.md` §D.2,
`_research/code-dbm-payload-contract.md` §10). **(verify)** the Agent's Go `pkg/obfuscate` supports a
`'db2'` dialect; if not, fall back to the default/`'sql'` dialect. This is the *same* open question
doc 05 raises — resolve it once, in [`12-risks-open-questions.md`](12-risks-open-questions.md), and
both collectors inherit the answer. (It must be resolved consistently, or metrics and samples would
sign the same statement differently and fail to link.)

### 3.3 Truncation state

Db2 `STMT_TEXT` is `CLOB` declared up to ~2 MB in the package cache (`db2-live-activity.md` §7); it is
far less likely to truncate than postgres's `track_activity_query_size` (default 1024). Still emit the
contract field `query_truncated` ∈ `{"truncated","not_truncated","unknown"}`
(`_research/code-postgres-dbm-samples.md` §9). For v1: if the driver returns a `STMT_TEXT` at the CLOB
read cap, mark `truncated`; else `not_truncated`. **(verify)** the effective cap; see doc 05 §2 for the
parallel CLOB-read handling (`ibm_db` must read the full CLOB, not assume a short VARCHAR).

---

## 4. Sampling strategy, rate-limiting, and the honest limitation

### 4.1 The fast-OLTP blind spot (live-proven negative result — read this)

**This is the single most important caveat for the whole feature.** From the live probe
(`db2-live-activity.md` §8): the orders inventory statements are sub-millisecond, and **40–80
point-in-time samples of `MON_CURRENT_SQL`/`MON_GET_ACTIVITY` never caught a single one.** Only
deliberately slow statements (a triple self-cartesian join, or `CALL dbms_lock.sleep(N)`) were reliably
captured. Steady-state `EXECUTING` count was ~2 (mostly the probe itself).

Implications, baked into the design:
- `MON_GET` sampling is an **ASH-style long/waiting/blocked-query + concurrency signal**, *not* a
  complete request log. It systematically under-counts short statements.
- **The complete per-statement record is the cumulative package cache (doc 05)**, which counts *every*
  execution. Samples and metrics are complementary: metrics = "what ran and how much", samples = "what
  is slow/waiting *right now* and what does its plan look like". This is exactly the
  pg_stat_statements vs pg_stat_activity division of labor (`_research/code-postgres-dbm-samples.md`
  §13).
- Do **not** advertise the activity/samples stream as catching every query. Document the limitation in
  the conf example and [`12-risks-open-questions.md`](12-risks-open-questions.md).
- A 1 s interval (postgres default) is the right starting cadence — accept that sub-interval statements
  are invisible. Tightening the interval helps only marginally and costs CPU; it cannot catch a
  0.3 ms statement.

### 4.2 Rate-limiting (`RateLimitingTTLCache`)

Two mechanisms, exactly as postgres (`_research/code-postgres-dbm-samples.md` §5,
`_research/code-base-framework.md` §E.4):

1. **Loop limiter** — `ConstantRateLimiter(rate_limit=1/collection_interval)` inside `DBMAsyncJob`
   paces the whole loop to the collection interval (default 1 s). Built in; nothing to do beyond
   passing `rate_limit`.

2. **Per-key `RateLimitingTTLCache`** — `.acquire(key)` returns `True` at most once per `ttl` per key
   (and `False` when the cache is full), so "acquire == may proceed"
   (`_research/code-base-framework.md` §E.4):

| Cache | key | maxsize (default) | ttl | gate |
|---|---|---|---|---|
| `_explained_statements_ratelimiter` | `(schema, query_signature)` | `explained_queries_cache_maxsize`=**5000** | `3600/explained_queries_per_hour_per_query` = 3600/60 = **60 s** | how often we run EXPLAIN for the same query (doc 07) |
| `_seen_samples_ratelimiter` | `(query_signature, plan_signature)` | `seen_samples_cache_maxsize`=**10000** | `3600/samples_per_hour_per_query` = 3600/15 = **240 s** | how often we *emit* a plan/sample event for the same (query, plan) |

The plan/fqt event emission goes through `_seen_samples_ratelimiter`; the EXPLAIN call (doc 07) goes
through `_explained_statements_ratelimiter`. A plan event is emitted **even when EXPLAIN fails**, with
`collection_errors` populated, still rate-limited under key `(query_signature, None)`
(`_research/code-postgres-dbm-samples.md` §8.1).

### 4.3 Sample-event fan-out (`_collect_sample_events`)

```python
def _collect_sample_events(self, rows):
    for row in rows:
        if row.get('statement') is None:
            continue
        sig = row['query_signature']
        # FQT once per (schema, signature) per its own TTL (doc 05 also emits FQT from metrics path;
        # both share query_signature so the backend dedups). Emit here if not seen.
        if self._fqt_ratelimiter.acquire((row.get('SESSION_AUTH_ID'), sig)):
            yield self._to_fqt_event(row)

        # plan attempt: rate-limit the EXPLAIN, defer mechanics to doc 07
        if self._explained_statements_ratelimiter.acquire((row.get('current_schema'), sig)):
            plan, plan_sig, errors = self._explain_statement(row)     # → 07-dbm-execution-plans.md
            if self._seen_samples_ratelimiter.acquire((sig, plan_sig)):
                yield self._to_plan_event(row, plan, plan_sig, errors)
```

`_explain_statement` is **out of scope for this doc** — it is the body of
[`07-dbm-execution-plans.md`](07-dbm-execution-plans.md) (section explain via `EXPLAIN_FROM_SECTION`,
which reads the already-compiled plan and sidesteps the `?`/host-variable parameterized-query problem;
or EXPLAIN tables → JSON tree). This doc only schedules the attempt and shapes the event envelope
(§5.1). For v1 you may ship samples with `query_samples.enabled=true` but plans disabled / always
returning the `collection_errors` placeholder, then layer plans in P3.

### 4.4 The future complement — WLM activity event monitor

The blind spot (§4.1) is *inherent* to polling. The complete in-flight record would come from a
**WLM activity event monitor** (`CREATE EVENT MONITOR ... FOR ACTIVITIES`), which captures *every*
activity as it completes (including sub-millisecond ones) into an event-monitor table, with full timing
and the statement text. That is push-not-poll and would catch what sampling misses. It is **deferred**
(setup cost, write amplification, table management, and it changes the collection model from
poll-a-view to drain-a-table) — call it out in [`12-risks-open-questions.md`](12-risks-open-questions.md)
as the path to true per-statement-sample completeness. For first fidelity, ship `MON_GET` polling +
lean on the package cache (doc 05) for completeness. **(verify)** event-monitor availability/cost on the
community 12.1.4 image before committing.

---

## 5. Payload shapes (cite `_research/code-dbm-payload-contract.md`)

All payloads: `ddsource:"db2"`, `dbms:"db2"`, `timestamp` = epoch **milliseconds**
(`time.time()*1000`), serialized `json.dumps(event, default=default_json_event_encoding)`. **`ddtags`
is a comma-joined STRING in sample events but a LIST in the activity event** — do not unify them
(`_research/code-dbm-payload-contract.md` §4.1, §8 "ddtags quirk").

### 5.1 Sample / plan event (`dbm_type:"plan"`)

The canonical plan-event envelope (`_research/code-dbm-payload-contract.md` §4.1,
`_research/code-postgres-dbm-samples.md` §8.1). Plan `definition`/`signature` are filled by doc 07;
this doc emits the envelope even when EXPLAIN is deferred/failed (`collection_errors` carries the code).

```python
{
  "host":             self._check.reported_hostname,
  "database_instance": self._check.database_identifier,
  "dbm_type":         "plan",
  "ddagentversion":   datadog_agent.get_version(),
  "ddsource":         "db2",                                # <-- product source string
  "ddtags":           ",".join(self.tags),                 # COMMA-JOINED STRING
  "timestamp":        time.time() * 1000,                  # epoch ms
  "cloud_metadata":   self._check.cloud_metadata,
  "service":          self._config.service,
  "network": {"client": {"ip": None, "port": None, "hostname": row.get("CLIENT_APPLNAME")}},  # (verify client addr availability)
  "db": {
    "instance":        row.get("dbname"),                  # the connected database (TESTDB)
    "plan": {
      "definition":        obfuscated_plan,                # filled by doc 07; None for now
      "signature":         plan_signature,                 # compute_exec_plan_signature(...) — doc 07
      "collection_errors": collection_errors,              # [{"code":...,"message":...}] or None
    },
    "query_signature": row["query_signature"],             # links to doc 05 metrics + FQT
    "resource_hash":   row["query_signature"],             # = query_signature (pg convention)
    "application":     row.get("APPLICATION_NAME"),
    "user":            row.get("SESSION_AUTH_ID"),
    "statement":       row["statement"],                   # obfuscated SQL
    "metadata": {"tables": row["dd_tables"], "commands": row["dd_commands"], "comments": row["dd_comments"]},
    "query_truncated": row["query_truncated"],
  },
  "db2": {                                                 # engine-specific block (excludes keys lifted into db/network above)
    "application_handle": row["APPLICATION_HANDLE"],
    "application_id":     row.get("APPLICATION_ID"),
    "uow_id":             row.get("UOW_ID"),
    "activity_id":        row.get("ACTIVITY_ID"),
    "activity_state":     row.get("ACTIVITY_STATE"),
    "activity_type":      row.get("ACTIVITY_TYPE"),
    "elapsed_time_msec":  row.get("ELAPSED_TIME_MSEC"),    # the "duration"-equivalent
    "total_cpu_time_us":  row.get("TOTAL_CPU_TIME"),       # microseconds (label the unit!)
    "total_act_wait_time_ms": row.get("TOTAL_ACT_WAIT_TIME"),
    "rows_read":          row.get("ROWS_READ"),
    "rows_returned":      row.get("ROWS_RETURNED"),
    "query_cost_estimate": row.get("QUERY_COST_ESTIMATE"),
    "executable_id":      row.get("executable_id"),        # HEX — joins to doc-05 metrics row
    "now":                row.get("now"),
  },
}
```

The `db2` sub-object mirrors postgres's `postgres` block (the activity row minus keys that are surfaced
under the standard `db`/`network` keys, `_research/code-postgres-dbm-samples.md` §8.1).

### 5.2 Activity event (`dbm_type:"activity"`)

```python
{
  "host":               self._check.reported_hostname,
  "database_instance":  self._check.database_identifier,
  "ddagentversion":     datadog_agent.get_version(),
  "ddsource":           "db2",
  "dbm_type":           "activity",
  "collection_interval": self._activity_coll_interval,     # seconds
  "ddtags":             self.tags,                          # LIST (not comma-joined here)
  "timestamp":          time.time() * 1000,
  "cloud_metadata":     self._check.cloud_metadata,
  "service":            self._config.service,
  "db2_version":        self._check.dbms_version,           # mirror sqlserver_version (contract §5.4)
  "db2_activity":       active_sessions,                    # list of per-session dicts
  "db2_connections":    connection_counts,                  # list of count dicts (§5.3)
}
```

(`_research/code-dbm-payload-contract.md` §5.4 — the generalized Db2 contract: `db2_activity` +
`db2_connections` + `db2_version`.)

**Per-session row** = the normalized row with: null-valued keys stripped and the raw `STMT_TEXT` key
removed (keep obfuscated `statement`), `query_signature`/`dd_*`/`query_truncated` attached, and the
identity/timing/state columns from §1. A session counts as "active" if `ACTIVITY_STATE='EXECUTING'`
**or** its UOW is `WORKLOAD_OCCURRENCE_STATE='UOWWAIT'` and you want to surface idle-in-transaction
(decide in `_normalize_rows`, the postgres analog drops `state='idle'` client backends,
`_research/code-postgres-dbm-samples.md` §5.5). On obfuscation failure, set
`statement="ERROR: failed to obfuscate"` rather than dropping (matches mysql `_finalize_row`,
`_research/code-mysql-dbm.md` §3.7).

**Payload cap.** Pick one (both are contract-acceptable, `_research/code-dbm-payload-contract.md` §5.5):
- **Row limit** (postgres style): cap at `payload_row_limit` (default **3500**), sort by elapsed
  desc and keep the longest-running (we already `ORDER BY ELAPSED_TIME_MSEC DESC`).
- **Byte cap** (sqlserver/mysql style): stop appending once estimated size exceeds
  `MAX_PAYLOAD_BYTES = 19e6` (`_research/code-mysql-dbm.md` §3.7). Given Db2's tiny steady-state active
  set (~2 rows, §4.1), the row limit is more than sufficient — use it and warn if ever exceeded.

### 5.3 Connection-counts aggregate (`db2_connections`)

Run only on activity ticks (the postgres `PG_ACTIVE_CONNECTIONS_QUERY` analog,
`_research/code-postgres-dbm-samples.md` §2.6; mysql/mssql have the same idea):

```sql
SELECT APPLICATION_NAME, SESSION_AUTH_ID, WORKLOAD_OCCURRENCE_STATE AS state, COUNT(*) AS connections
FROM TABLE(MON_GET_UNIT_OF_WORK(NULL, -1)) U
JOIN TABLE(MON_GET_CONNECTION(NULL, -1)) C USING (APPLICATION_HANDLE)   -- (verify USING support; else ON)
WHERE APPLICATION_HANDLE <> ?
GROUP BY APPLICATION_NAME, SESSION_AUTH_ID, WORKLOAD_OCCURRENCE_STATE
```

Emits rows `{application_name, user, state, connections}` — the per-(app, user, state) connection
breakdown. `state` from `WORKLOAD_OCCURRENCE_STATE` gives the Db2 connection-state distribution
(executing / waiting-in-txn / transient). **(verify)** the cheapest connection source — `MON_GET_CONNECTION`
alone gives counts by app/user without UOW state if you don't need the state dimension.

### 5.4 FQT event (`dbm_type:"fqt"`)

Same envelope as doc 05's FQT (`_research/code-dbm-payload-contract.md` §4.2): obfuscated `statement`,
`query_signature`, `metadata`, rate-limited per `(instance/user, query_signature)`. Both the metrics
path (doc 05) and this samples path can emit FQT; because both key on the identical `query_signature`,
the backend dedups. To avoid double-work, **prefer emitting FQT from the metrics path (doc 05)** and
only emit it here for statements that appear in samples but were evicted from the package cache before
metrics saw them (rare). Cross-reference doc 05 §1.9-equivalent.

---

## 6. Privileges

The agent's DBM connection user needs to read the `MON_GET_*` family and the admin views
(`db2-live-activity.md` §10):

- **`SYSMON` authority** is the documented least-privilege minimum for the entire `MON_GET_*` family
  (`MON_GET_ACTIVITY`, `MON_GET_CONNECTION`, `MON_GET_UNIT_OF_WORK`) — recommend this for the agent.
  Alternatively `SYSCTRL`/`SYSMAINT`/`SYSADM`, or `DATAACCESS`, or `EXECUTE` on the specific routines.
- `SYSIBMADM.MON_CURRENT_SQL` / `MON_CURRENT_UOW` are admin views over those functions; `SYSMON` covers
  them. `EXECUTE` on the underlying functions + `SELECT` on the view also works.
- No special monitoring switch is needed for identity + `STMT_TEXT` + `ACTIVITY_STATE` +
  `ELAPSED_TIME_*`. The accumulated timing columns (`TOTAL_ACT_TIME`, `TOTAL_ACT_WAIT_TIME`) require
  `mon_act_metrics >= BASE` — **the default** on 12.1.4 (`db2-live-activity.md` §10). Gate
  timing-derived sample fields on `mon_act_metrics <> 'NONE'` and degrade gracefully (the
  `track_io_timing` analog described in doc 05 §7).
- Blocking detection (§1.6) via `SYSIBMADM.MON_LOCKWAITS` needs the same `SYSMON`-class authority.
- These are the **same** privileges doc 05 requires for `MON_GET_PKG_CACHE_STMT`, so one grant covers
  both DBM collectors. Document the `GRANT` in [`09-implementation-architecture.md`](09-implementation-architecture.md)
  alongside the connection setup.

---

## 7. Config knobs (`query_samples` + `query_activity` blocks)

Mirror the postgres/mysql defaults (`_research/code-postgres-dbm-samples.md` §10,
`_research/code-mysql-dbm.md` §2.10/§3.9, `_research/code-dbm-payload-contract.md` §10):

```yaml
# under each instance:
query_samples:
  enabled: true
  collection_interval: 1                       # seconds; the loop cadence
  run_sync: false
  samples_per_hour_per_query: 15               # _seen_samples_ratelimiter → ttl 240 s
  explained_queries_per_hour_per_query: 60     # _explained_statements_ratelimiter → ttl 60 s
  seen_samples_cache_maxsize: 10000
  explained_queries_cache_maxsize: 5000
  # explain_* knobs (explain_function/strategy, parameterized handling) live in 07-dbm-execution-plans

query_activity:
  enabled: true
  collection_interval: 10                      # seconds; activity reported at most this often
  payload_row_limit: 3500                      # §5.2 row cap
  collect_blocking_queries: false              # §1.6 MON_LOCKWAITS gate

# shared (already needed by doc 05):
obfuscator_options: { ... }                    # dbms hint 'db2' (§3.2, verify)
```

The activity loop never reports more often than the sample loop:
`_activity_coll_interval = max(query_activity.collection_interval, collection_interval)` (§2). When
`query_samples.enabled=false` but `query_activity.enabled=true`, the loop slows to the activity cadence
(§2 constructor). Document the §4.1 blind spot in the conf example next to these knobs.

---

## 8. Internal telemetry (self-monitoring)

Emit the postgres/mysql analogs (`raw=True`, tagged `self.tags`), namespaced `dd.db2.*`
(`_research/code-postgres-dbm-samples.md` §11, `_research/code-mysql-dbm.md` §2.9, §3.3):

- `dd.db2.collect_statement_samples.time` (histogram, ms)
- `dd.db2.collect_statement_samples.events_submitted.count` (count)
- `dd.db2.get_new_activity.time` / `.rows` (histogram)
- `dd.db2.collect_activity.payload_size` (histogram)
- `dd.db2.statement_samples.error` (count; `error:sql-obfuscate`, `error:explain-<code>`, …)
- `dd.db2.collect_statement_samples.seen_samples_cache.len` / `.explained_statements_cache.len` (gauge)
- plus the framework's `dd.db2.async_job.*` (missed/cancel/inactive_stop/error) from `DBMAsyncJob`
  (`_research/code-base-framework.md` §E.3).

These are debug/internal (not part of the backend contract, not in `metadata.csv` —
`_research/code-dbm-payload-contract.md` §11.2).

---

## 9. Implementation checklist

1. Add `Db2StatementSamples(DBMAsyncJob)` (§2); wire it in the check's `__init__` + `run_job_loop` +
   `cancel`, with its own dedicated `ibm_db` connection (`_research/code-base-framework.md` §J;
   detail in [`09-implementation-architecture.md`](09-implementation-architecture.md)).
2. Resolve the agent's own `APPLICATION_HANDLE` once on the job connection for self-exclusion (§1.2).
3. Ship the `MON_CURRENT_SQL` query (§1.2) first; runtime-introspect columns; intersect with desired.
4. Wire obfuscation+signature **sharing the exact options/path with doc 05** so signatures match (§3).
5. Resolve the `'db2'` obfuscator-dialect question with doc 05 in [`12`](12-risks-open-questions.md) (§3.2).
6. Emit the **activity** event (§5.2) + connection counts (§5.3) on the activity cadence.
7. Emit **fqt**/**plan** envelopes (§5.1, §5.4); leave plan `definition`/`signature` to doc 07; gate
   the EXPLAIN attempt behind `_explained_statements_ratelimiter` (§4.2-4.3).
8. Add `query_samples` + `query_activity` config blocks (§7); document the §4.1 OLTP blind spot.
9. Add `SYSMON` to the agent-user grant (§6) — same grant as doc 05.
10. Defer: named wait events (§1.5), blocking via `MON_LOCKWAITS` (§1.6), WLM activity event monitor
    (§4.4), full plan assembly ([`07`](07-dbm-execution-plans.md)).

---

## 10. Citations

- **Authoritative Db2 live findings:** [`_research/db2-live-activity.md`](_research/db2-live-activity.md)
  — §1–§2 (source decision matrix), §3 (`MON_CURRENT_SQL` 19 cols), §4 (in-flight elapsed proof),
  §5 (view = `MON_GET_ACTIVITY` ⋈ `MON_GET_CONNECTION`), §6 (`MON_GET_ACTIVITY` key cols, `EXECUTABLE_ID`),
  §7 (`STMT_TEXT` comment + `?` format), **§8 (fast-OLTP blind spot)**, §9 (`MON_GET_UNIT_OF_WORK`),
  §10 (monitoring cfg + privileges), §11 (12.1 doc links — re-cite vs 11.1 in current `queries.py`).
- **Framework / payloads:** [`_research/code-postgres-dbm-samples.md`](_research/code-postgres-dbm-samples.md)
  (§1–§5, §8–§13 — the unified samples+activity job we mirror),
  [`_research/code-mysql-dbm.md`](_research/code-mysql-dbm.md) (§2–§3 — split samples/activity jobs,
  rate-limit defaults, payload caps, §6.6 unit warning),
  [`_research/code-dbm-payload-contract.md`](_research/code-dbm-payload-contract.md)
  (§4–§5 plan/activity envelopes, §8 field reference, §10 config, §11 source strings),
  [`_research/code-base-framework.md`](_research/code-base-framework.md) (§D obfuscation/signatures,
  §E `DBMAsyncJob`/`RateLimitingTTLCache`, §F payload submitters, §I `DatabaseCheck`, §J sqlserver
  assembly, §K Db2 source map).
- **Sibling plan docs:** [`03-reference-architecture.md`](03-reference-architecture.md) §2.2–§2.3,
  [`05-dbm-query-metrics.md`](05-dbm-query-metrics.md) (FQT + `query_signature` linkage),
  [`07-dbm-execution-plans.md`](07-dbm-execution-plans.md) (`_explain_statement`/plan tree),
  [`09-implementation-architecture.md`](09-implementation-architecture.md) (check wiring, conn isolation,
  grants), [`12-risks-open-questions.md`](12-risks-open-questions.md) (OLTP blind spot, obfuscator
  dialect, WLM event monitor).
