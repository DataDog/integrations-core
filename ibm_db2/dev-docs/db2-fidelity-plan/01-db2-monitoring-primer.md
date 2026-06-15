# 01 — Db2 LUW Monitoring Primer (for a Postgres/MySQL Engineer)

**What this is.** The conceptual on-ramp for the rest of the plan. If you know the Datadog
`postgres` / `mysql` / `sqlserver` integrations — `pg_stat_statements`, `pg_stat_activity`,
`information_schema`, `EXPLAIN`, `DBMAsyncJob`, obfuscation/signatures — but have never touched IBM
Db2, this doc gives you the architecture and the **monitoring interfaces** you need to read every
other doc in the set without getting lost.

**Audience & style.** Written for a pg/mysql engineer. Every Db2 concept is introduced by analogy to
Postgres/MySQL where one exists, and the analogy's limits are called out. You do not need prior Db2
knowledge.

**Scope.** Db2 **LUW** (Linux/UNIX/Windows) only — the target platform. Our live ground-truth server
is **`DB2/LINUXX8664 12.1.4.0`**, Db2 **Community Edition** (`INSTALLED_PROD='DEC'`,
`LICENSE_TYPE='COMMUNITY'`), single-member, non-DPF, non-pureScale, non-HADR
(`_research/_raw/01-version-and-monget-functions.txt:4`,
`_research/db2-config-settings.md:236-254`). Db2 for **z/OS** is a completely different product with
a different monitoring surface and is **out of scope** (`_research/db2-editions-versions.md:281-293`).

**How to read the citations.** `_raw/NN-*.txt` and `_research/*.md` references point at
live-empirical captures from that 12.1.4 server (or research grounded in them). Facts I assert from
general Db2 LUW knowledge that were *not* directly confirmed live are tagged **(verify)**.

> **Sibling docs.** `00-README.md` (index/exec summary) → **this doc** →
> `02-current-integration-audit.md` (what the shipped check does today) → `10-implementation-phases.md`
> (the build order) → `99-review-and-gaps.md` (open issues). The deep per-interface detail lives in
> `_research/`: `db2-config-settings.md` (settings/version detection), `db2-editions-versions.md`
> (feature gating), `db2-live-pkgcache.md` (query metrics), `db2-live-activity.md` (samples/activity),
> `db2-monget-catalog-2.md` (per-object MON_GET catalog).

---

## 0. TL;DR — the ten things to internalize

1. **"Instance" in Db2 ≠ "instance" in Postgres.** A Db2 **instance** (`db2inst1`) is the engine
   process group; it contains **multiple databases**. You connect to **one database** (`TESTDB`) at a
   time, and most monitoring SQL is scoped to that one connected database. Closest analogy: a
   Postgres **cluster** (the `postmaster` + its data dir) holding multiple databases — except in Db2
   the layer that holds config and memory at the top is the *instance*, not the database.
2. **The modern monitoring API is the `MON_GET_*` table functions** — SQL table functions you
   `SELECT ... FROM TABLE(MON_GET_FOO(...))`. There are **64** of them on 12.1.4
   (`_raw/01-version-and-monget-functions.txt`). They are the Db2 analog of Postgres's
   `pg_stat_*` views + `pg_stat_statements`, and SQL Server's `sys.dm_*` DMVs.
3. **Counters are cumulative-since-database-activation and monotonic** — exactly like
   `pg_stat_statements`. You diff two snapshots and drop negatives (reset = cache eviction or DB
   reactivation) (`_research/db2-live-pkgcache.md:64-66, 388-391`).
4. **`MON_GET_PKG_CACHE_STMT` is the `pg_stat_statements` analog** (per-statement cumulative metrics,
   327 cols on 12.1.4) (`_research/db2-live-pkgcache.md:1, 51`).
5. **`MON_CURRENT_SQL` / `MON_GET_ACTIVITY` are the `pg_stat_activity` analog** (in-flight statements
   with text + wall-clock elapsed) (`_research/db2-live-activity.md:59-75`).
6. **Db2 does NOT normalize SQL text for you.** The cache stores statements *as prepared* — `?`
   markers if parameterized, raw literals if inlined. You must obfuscate + compute `query_signature`
   client-side, same as every other DBM integration (`_research/db2-live-pkgcache.md:62-63, 177-201`).
7. **`SYSIBMADM.*` administrative views are pre-aggregated, friendlier wrappers** over the table
   functions and over legacy snapshot data — **79** present (`_raw/03-sysibmadm-objects.txt`). Think
   of them as Db2's `information_schema` + convenience views. `MON_CURRENT_SQL` is literally a view
   over `MON_GET_ACTIVITY` + `MON_GET_CONNECTION` (`_research/db2-live-activity.md:289-336`).
8. **The system catalog is `SYSCAT.*` (views) over `SYSIBM.*` (base tables)** — the
   `information_schema` / `pg_catalog` analog. `SYSIBMADM.*` is the *monitoring/admin* schema; don't
   confuse it with `SYSCAT.*` (the *metadata* schema).
9. **Timing columns are gated by `mon_*_metrics` DB-config knobs**, not by version/edition. On our
   server they're at defaults (`mon_act_metrics=BASE`, etc.) which is sufficient; still introspect and
   degrade gracefully (`_raw/04-monitor-config.txt`, `_research/db2-live-pkgcache.md:73-75`).
10. **EXPLAIN works on Community Edition** and `EXPLAIN_OPERATOR` carries the full cost schema, so
    plan capture is viable (`_raw/05-explain-test.txt`).

---

## 1. Db2 LUW architecture (the mental model)

### 1.1 Instance vs database vs database partition

| Db2 LUW term | What it is | Closest pg/mysql analogy | Where config lives |
|---|---|---|---|
| **Instance** (`db2inst1`) | The engine: a set of OS processes + shared memory that owns **one or more databases**. Has its own owner OS user, its own listener port (`svcename`), its own config. | A Postgres **cluster** (`postmaster` + data dir) / a MySQL **server (`mysqld`)** — but the instance, not the DB, is the top config+memory layer. | **DBM CFG** (`db2 get dbm cfg` / `SYSIBMADM.DBMCFG`), instance-level (`_research/db2-config-settings.md:41-64`) |
| **Database** (`TESTDB`) | A self-contained collection of tablespaces, tables, indexes, logs, and its own catalog. You connect to exactly one at a time. Most `MON_GET_*` functions are database-scoped. | A Postgres/MySQL **database**. | **DB CFG** (`db2 get db cfg` / `SYSIBMADM.DBCFG`), per-database (`_research/db2-config-settings.md:86-114`) |
| **Database partition** (a.k.a. **member**) | A slice of a database in **DPF** (Database Partitioning Feature, MPP shared-nothing) or a **pureScale member** (shared-disk cluster). On a standalone server there is exactly **one** member, numbered `0`. | No direct pg/mysql analogy. Loosely: a Citus shard (DPF) or a Galera/RAC node (pureScale). | per-member rows in DBCFG/REG_VARIABLES |

**Why "member" matters for this integration even though we're single-member.** Almost every
`MON_GET_*` function takes a `member` argument and almost every monitoring row carries a `MEMBER`
column. Pass `-1` (current member) or `-2`/`NULL` (all members) — the existing check passes `-1`
everywhere (`/home/bits/dd/integrations-core/ibm_db2/datadog_checks/ibm_db2/queries.py`). On our
single-member server `MEMBER` is always `0`. On DPF/pureScale, a naive `SELECT *` returns **one row
per object per member**, so multi-member topologies multiply cardinality — you either aggregate
(`-2`) or carry `member` as a tag (`_research/db2-config-settings.md:100-114`,
`_research/db2-editions-versions.md:168-174`).

### 1.2 The storage stack: bufferpools, tablespaces, containers

Db2's storage hierarchy maps cleanly onto concepts you know, with one extra named layer:

- **Bufferpool** — the in-memory page cache. Direct analog of the Postgres **shared_buffers** / MySQL
  **InnoDB buffer pool**. A database can have several bufferpools of different page sizes. Hit ratio =
  logical reads served from memory (`POOL_*_L_READS`) vs physical reads from disk (`POOL_*_P_READS`)
  — this is the core efficiency metric and the shipped check already computes it
  (`02-current-integration-audit.md`; columns in `_raw/02-monget-key-columns.txt`).
- **Tablespace** — a logical storage layer that maps tables/indexes onto physical storage. A
  tablespace is bound to **one** bufferpool and **one** page size. Roughly a Postgres **tablespace**,
  but a first-class, always-present concept (every table lives in one). Read via
  `MON_GET_TABLESPACE` (`_raw/02-monget-key-columns.txt` L768).
- **Container** — the actual physical storage (a directory, file, or raw device) backing a
  tablespace. One tablespace → one or more containers. There is no Postgres analog; think "the files
  on disk under a tablespace." Read via `MON_GET_CONTAINER` (utilization / FS-level capacity).

So the chain is: **table → tablespace → container(s) → filesystem**, and **tablespace → bufferpool**
for caching. Page counts (`*_PAGES`) are point-in-time gauges; reads/writes are monotonic counters
(`_research/db2-monget-catalog-2.md:26-31`).

### 1.3 Transaction logs (active vs archive)

Db2 uses write-ahead logging like everyone else. Two modes/states matter:

- **Active logs** — the logs needed for crash recovery and in-flight transaction rollback (the
  always-present WAL). Analog of the Postgres **WAL** currently retained / MySQL **redo log**.
- **Archive logs** — once an active log fills and is no longer needed for recovery, it is **archived**
  (copied off) if the database is in `LOGARCHMETH1`-enabled (archive logging) mode, enabling
  roll-forward recovery and online backups. This is closest to **WAL archiving** in Postgres. The
  alternative is **circular logging** (logs reused in a ring; no point-in-time recovery) — analogous
  to a Postgres cluster with archiving off.

`MON_GET_TRANSACTION_LOG` (56 cols, `_research/db2-monget-catalog-2.md` provenance) exposes log space
used/available, log-write/read I/O, and `LOG_BUFFER_WAIT_TIME` / `LOG_DISK_WAIT_TIME`
(commit-latency signals). The shipped check already reads log utilization
(`02-current-integration-audit.md`).

### 1.4 The engine / agent model (where "sessions" live)

Db2 does **not** fork a process per connection (Postgres) nor use a fixed thread pool the way MySQL
does. Instead the engine uses **EDUs (Engine Dispatchable Units)** — threads — and a pool of
**agents**:

- A **coordinator agent** is assigned to each connection (the analog of a Postgres backend / MySQL
  connection thread). It does the work for that connection, or farms sub-work to **subagents** (on
  DPF/intra-parallel).
- Agents are pooled and reused. `MON_GET_INSTANCE` exposes the pool health:
  `AGENTS_REGISTERED`, `IDLE_AGENTS`, `NUM_COORD_AGENTS`, `AGENTS_CREATED_EMPTY_POOL`
  (pool-pressure signal) (`_research/db2-monget-catalog-2.md:146-184`).
- **Identity vocabulary you'll see everywhere:**
  - **`APPLICATION_HANDLE`** — the connection id within the current DB activation (the join key
    across `MON_GET_CONNECTION` / `MON_GET_ACTIVITY` / `MON_GET_UNIT_OF_WORK` / `MON_GET_AGENT`).
    Analog of a Postgres `pid` / MySQL `connection_id`.
  - **`APPLICATION_ID`** — a globally-unique connection string, e.g.
    `172.17.129.4.50932.260615021825` (`<ip>.<port>.<timestamp>`)
    (`_research/db2-live-activity.md:49-53`).
  - **`UOW_ID`** — Unit Of Work = **transaction** id within a connection.
  - **`ACTIVITY_ID`** — a single statement/activity within a UOW.
  - The triple **`(APPLICATION_HANDLE, UOW_ID, ACTIVITY_ID)`** uniquely identifies an in-flight
    statement (`_research/db2-live-activity.md:215-216`).

**Gotcha for sampling:** your own monitoring query *always* shows up as an in-flight activity in its
own snapshot — exclude your own `APPLICATION_HANDLE` / `APPLICATION_NAME`
(`_research/db2-live-activity.md:283-285`).

### 1.5 The memory model (heaps you'll see in metrics & config)

Db2 reserves OS memory in **memory sets** (top-level reservations) subdivided into **memory pools**
(individual heaps). The pools you care about, with their config knobs and analogies:

| Db2 memory pool | What it caches | pg/mysql analogy | Config knob |
|---|---|---|---|
| **Bufferpool** | data/index pages | shared_buffers / InnoDB BP | bufferpool size (or `database_memory` auto) |
| **Package cache** | compiled statement sections | `pg_stat_statements` shared mem / MySQL prepared-stmt cache | `pckcachesz` |
| **Sort heap** | per-sort/hash workspace | `work_mem` | `sortheap`, `sheapthres_shr` |
| **Lock list** | row/table lock structures | the lock table | `locklist`, `maxlocks` |
| **Catalog cache** | catalog metadata | catcache/relcache | `catalogcache_sz` |

`MON_GET_MEMORY_SET` (coarse, OS-committed) and `MON_GET_MEMORY_POOL` (per-heap `*_USED`/`*_USED_HWM`)
expose live usage as gauges (`_research/db2-monget-catalog-2.md:382-445`, columns marked **(verify)**
there — these two need a live `DESCRIBE` before coding). Pair the pool `*_USED` gauges with their
config limits from `SYSIBMADM.DBCFG` for "near limit" signals.

Many heaps are **self-tuning** under STMM (Self-Tuning Memory Manager); their config rows carry
`VALUE_FLAGS='AUTOMATIC'`, and the numeric `VALUE` is the *current computed* size
(`_research/db2-config-settings.md:117-123`).

### 1.6 Workload Manager (WLM): service classes & workloads

Db2 has a built-in **Workload Manager** that classifies and meters work along two orthogonal axes.
There is no clean Postgres analog; the closest is SQL Server **Resource Governor** (workload groups +
resource pools).

- **Service superclass → service subclass** — *how work is prioritized/resourced* (the resource
  axis). Read via `MON_GET_SERVICE_SUBCLASS` (376 cols) / `MON_GET_SERVICE_SUPERCLASS`.
- **Workload** — *who/what connected* (the logical-attribution axis: app name, user, address). Read
  via `MON_GET_WORKLOAD` (371 cols).

The two double-count the same underlying activity along different dimensions
(`_research/db2-monget-catalog-2.md:330-336`). **Crucial fact: default classes always exist** —
`SYSDEFAULTUSERCLASS` / `SYSDEFAULTSUBCLASS` and `SYSDEFAULTUSERWORKLOAD` (id 1) — so these functions
return useful "where is time going" roll-ups **even with no custom WLM configured**
(`_research/db2-monget-catalog-2.md:196-199, 329, 456-458`). They also expose the richest time/wait
decomposition in the whole API (request time → section time → wait components), making them strong
candidates for a workload-level "active sessions / time-spent" breakdown.

### 1.7 The system catalog: `SYSCAT.*` and `SYSIBM.*` (don't confuse with `SYSIBMADM.*`)

Three system schemas, three different jobs — keep them straight:

| Schema | Role | pg/mysql analogy | Used for (in this plan) |
|---|---|---|---|
| **`SYSIBM.*`** | The raw **base catalog tables** (and a few system views like `SYSIBM.SYSVERSIONS`). | `pg_catalog` base tables. | Low-level/version reads (`SYSIBM.SYSVERSIONS.versionnumber` packed int) (`_research/db2-config-settings.md:348-355`). |
| **`SYSCAT.*`** | Read-only **catalog views** over `SYSIBM` — the documented metadata API (tables, columns, indexes, routines, views). | `information_schema` / `pg_catalog` views. | **Schema metadata** collection (tables/columns/indexes), and labeling (`SYSCAT.INDEXES` to get index *names* that `MON_GET_INDEX` omits) (`_research/db2-monget-catalog-2.md:141-142`). |
| **`SYSIBMADM.*`** | **Administrative & monitoring views** — pre-aggregated wrappers over `MON_GET_*`, ENV/CFG table functions, and legacy snapshots. | A blend of `pg_stat_*` convenience views + admin functions. | Config (`DBCFG`/`DBMCFG`), version/edition (`ENV_*`), live SQL (`MON_CURRENT_SQL`), summaries (`MON_*_SUMMARY`). |

**The catch you'll hit immediately:** Db2 CLP treats double quotes as a **delimited identifier**, so
SQL string literals must be **single-quoted inside** a double-quoted CLP statement, or you get
`SQL0206N ... not valid in the context`. This bites every probe
(`_research/db2-live-pkgcache.md:33-37`, `_research/db2-live-activity.md:38-41`). The `ibm_db` driver
(parameterized queries) sidesteps it, but raw CLP probing does not.

---

## 2. The monitoring interfaces — what they are and when to use each

Db2 LUW has four distinct monitoring surfaces. The whole plan is built on these.

### 2.1 `MON_GET_*` table functions — the modern primary source (use these)

SQL **table functions** invoked as `SELECT ... FROM TABLE(MON_GET_FOO(args))`. They return
cumulative-since-activation counters (and some point-in-time gauges). **64 are present on 12.1.4**
(full list: `_raw/01-version-and-monget-functions.txt:11-74`). This is the source of truth for
metrics, query metrics, and samples. Properties:

- **Monotonic counters** → diff snapshots for rates (`_research/db2-live-pkgcache.md:64-66`).
- **Member argument** (`-1` current / `-2` all) on most functions (§1.1).
- **Column sets grow across fix packs** but layouts are stable. `MON_GET_PKG_CACHE_STMT` = **327** cols
  on 12.1.4; `MON_GET_ACTIVITY` = **418**; `MON_GET_DATABASE` = **515**; `MON_GET_CONNECTION` = **417**
  (`_research/db2-live-pkgcache.md:51`, `_research/db2-live-activity.md:84`,
  `_research/db2-monget-catalog-2.md:13-19`). **→ Always introspect columns at runtime** (a
  `WHERE 1=0` / `FETCH FIRST 0 ROWS ONLY` probe → intersect `cursor.description` with your desired set)
  rather than hard-coding by version (`_research/db2-live-pkgcache.md:383-387`,
  `_research/db2-editions-versions.md:228-243`). This is the same pattern as Postgres `statements.py`.
- **Unit inconsistency (critical):** within the *same* row, `TOTAL_CPU_TIME` is **microseconds** while
  `STMT_EXEC_TIME` / `TOTAL_ACT_TIME` / most `*_TIME` are **milliseconds**. Never mix without
  converting (`_research/db2-live-pkgcache.md:66-68, 354-364`).

The functions most load-bearing for this plan (catalog detail in `_research/db2-monget-catalog-2.md`):

| Function | Granularity | Plan use | Analog |
|---|---|---|---|
| `MON_GET_PKG_CACHE_STMT` | per cached statement (cumulative) | **query metrics** | `pg_stat_statements` |
| `MON_GET_ACTIVITY` / `MON_CURRENT_SQL` | per in-flight statement | **samples / activity** | `pg_stat_activity` + `pg_stat_get_activity` |
| `MON_GET_UNIT_OF_WORK` | per transaction (no stmt text) | transaction state / idle-in-txn | `pg_stat_activity` xact fields |
| `MON_GET_CONNECTION` | per connection | sample identity (auth id, app name) | `pg_stat_activity` identity |
| `MON_GET_DATABASE` / `MON_GET_INSTANCE` | DB / instance roll-up | **system metrics** | `pg_stat_database` / cluster stats |
| `MON_GET_BUFFERPOOL` / `MON_GET_TABLESPACE` / `MON_GET_CONTAINER` / `MON_GET_TRANSACTION_LOG` | per storage object | **system metrics** | `pg_statio_*` / `pg_stat_*` |
| `MON_GET_TABLE` / `MON_GET_INDEX` | per table / index | per-object metrics (hot tables/indexes) | `pg_stat_user_tables` / `pg_stat_user_indexes` |
| `MON_GET_SERVICE_SUBCLASS` / `MON_GET_WORKLOAD` | per WLM class / workload | workload time-spent breakdown | (no pg analog; ~SQL Server Resource Governor) |
| `MON_GET_MEMORY_SET` / `MON_GET_MEMORY_POOL` | per memory area | memory-pressure gauges | (no direct analog) |

### 2.2 `SYSIBMADM.*` administrative views — pre-aggregated convenience (use selectively)

**79 present** (`_raw/03-sysibmadm-objects.txt:9-86`). Three flavors live here:

1. **Modern `MON_*` views** wrapping the table functions: `MON_CURRENT_SQL`, `MON_CURRENT_UOW`,
   `MON_DB_SUMMARY`, `MON_PKG_CACHE_SUMMARY`, `MON_SERVICE_SUBCLASS_SUMMARY`, `MON_WORKLOAD_SUMMARY`,
   `MON_BP_UTILIZATION`, `MON_TBSP_UTILIZATION`, `MON_LOCKWAITS`, `MON_CONNECTION_SUMMARY`,
   `MON_TRANSACTION_LOG_UTILIZATION`. Use these when their pre-joined/pre-computed shape is exactly
   what you want — e.g. `MON_CURRENT_SQL` already joins activity+connection and computes wall-clock
   elapsed (`_research/db2-live-activity.md:289-336`).
2. **Config/env views**: `DBCFG`, `DBMCFG`, `REG_VARIABLES`, `ENV_INST_INFO`, `ENV_PROD_INFO`,
   `ENV_SYS_INFO`, `ENV_FEATURE_INFO` — the settings + version/edition surface
   (`_research/db2-config-settings.md` is the canonical reference).
3. **Legacy `SNAP*` snapshot views** (`SNAPDB`, `SNAPBP`, `SNAPDYN_SQL`, `SNAPHADR`, `SNAPFCM`, …) —
   deprecated wrappers over the old snapshot monitor. **Prefer the `MON_GET_*` functions**; the
   `SNAP*` views exist mainly for backward compatibility (`_research/db2-monget-catalog-2.md:466-471`).

**When to use a view vs the raw function:** views are convenient and sometimes do work for you
(joins, elapsed-time math), but they can double-evaluate the underlying function and expose fewer
columns. `MON_CURRENT_SQL` exposes only **19** of `MON_GET_ACTIVITY`'s 418 columns and lacks
`EXECUTABLE_ID` (the package-cache join key) — so when you need more, drop to the raw function and
reproduce the view's join yourself (`_research/db2-live-activity.md:84, 176-181, 289-336`).

### 2.3 Event monitors — push-style capture (mostly out of scope, one exception)

**Event monitors** asynchronously capture *events* (statement completions, deadlocks, locking,
activities, UOW completions) to a target (table, file, or pipe) as they happen — a push model versus
the pull model of `MON_GET_*`. The closest analogs are the MySQL **performance_schema** consumers or
SQL Server **Extended Events**.

For this plan they are **largely not needed** — the `MON_GET_*` pull model covers query metrics and
ASH-style sampling. The one place they matter:

- A **WLM activity event monitor** (and the lock/deadlock event monitors) is the only way to capture
  *every* completed statement including the **sub-interval-short OLTP** that point-in-time activity
  sampling systematically misses (proven live: 40–80 samples never caught the sub-millisecond orders
  statements) (`_research/db2-live-activity.md:96-102, 423-449`). The local-dev DB already has
  activity event-monitor tables present (`DB2INST1.ACTIVITY*_DD_ACTIVITIES`,
  `_research/db2-live-pkgcache.md:39-42`). Event monitors add setup/retention complexity and are a
  later-phase consideration; the cumulative package cache (§2.1) is what guarantees every statement is
  *counted* even if not *sampled*.

### 2.4 EXPLAIN — execution plans (proven working)

Db2's `EXPLAIN` populates a set of **EXPLAIN tables** (`EXPLAIN_STATEMENT`, `EXPLAIN_OPERATOR`,
`EXPLAIN_OBJECT`, …) with the chosen access plan; you then `SELECT` from them. Closest analog:
Postgres `EXPLAIN (FORMAT JSON)` / SQL Server showplan — except Db2 writes to tables rather than
returning a document, so plan capture is a two-step "EXPLAIN, then read the tables" flow.

**Confirmed working on the live Community server** (`_raw/05-explain-test.txt:9-13`): a test EXPLAIN
produced `RETURN` and `TBSCAN` operators, and `EXPLAIN_OPERATOR` carries the full cost schema —
`TOTAL_COST`, `IO_COST`, `CPU_COST`, `FIRST_ROW_COST`, `BUFFERS`, etc.
(`_raw/05-explain-test.txt:14-35`). Cost is in **timerons** (Db2's abstract optimizer cost unit; also
surfaced live as `QUERY_COST_ESTIMATE` on activities/cache rows). Plan capture is the highest-risk,
most-isolated DBM feature (it needs EXPLAIN tables to exist and the right privilege) and is
spike-gated in the phase plan — but it is **feasible** on the target.

### 2.5 Driver-level info (no SQL) — the existing fallback

The shipped check already pulls the version string straight from the `ibm_db` driver via
`ibm_db.get_db_info(conn, ibm_db.SQL_DBMS_VER)` (`raw MM.mm.uuuu`) and sets
`ibm_db.ATTR_CASE = ibm_db.CASE_LOWER` so dict rows come back **lowercase**
(`_research/db2-config-settings.md:374-378, 474-478`). Keep the driver call as a version fallback;
prefer SQL (`SYSIBM.SYSVERSIONS` / `ENV_INST_INFO`) for richness.

---

## 3. Monitor collection settings (`mon_*_metrics`) — what gates the timing columns

Whether the **timing/wait counters** in the table functions are *populated* depends on per-database
**monitor collection** knobs (DB CFG parameters), independent of version or edition. Reading them is
the Db2 analog of checking whether `track_io_timing` / `pg_stat_statements.track` are on in Postgres,
or which `performance_schema` consumers are enabled in MySQL.

**Live values on our 12.1.4 server** (`_raw/04-monitor-config.txt:9-22`):

| Setting | Live value | What it enables | Guard the agent should apply |
|---|---|---|---|
| `mon_req_metrics` | `BASE` | Request-level timing (`TOTAL_RQST_TIME`, wait components) in connection/service-class/workload functions | emit request-timing metrics only when `<> 'NONE'` |
| `mon_act_metrics` | `BASE` | **Activity timing** (`TOTAL_ACT_TIME`, `TOTAL_ACT_WAIT_TIME`, `COORD_STMT_EXEC_TIME`, `WLM_QUEUE_TIME_TOTAL`) in `MON_GET_ACTIVITY` & package cache | gate query-metric/sample timing fields on `<> 'NONE'` |
| `mon_obj_metrics` | `EXTENDED` | Object (table/index/bufferpool) page-level counters in `MON_GET_TABLE` / `MON_GET_INDEX` | gate per-object metrics on `<> 'NONE'` |
| `mon_uow_data` / `mon_uow_pkglist` / `mon_uow_execlist` | `NONE` / `OFF` / `OFF` | UOW statement & package lists | not needed for core features |
| `mon_lck_msg_lvl` / `mon_lockwait` / `mon_locktimeout` / `mon_deadlock` | `1` / `NONE` / `NONE` / `WITHOUT_HIST` | lock-event / deadlock detail capture | gate lock-wait detail features |
| `mon_lw_thresh` | `5000000` | lock-wait threshold (µs) before a lock-wait event is recorded | informational |

**Key point:** all values are at defaults, and **defaults are sufficient** for the timing columns
this plan needs (`BASE` activity/request metrics). The agent should still **read these at runtime**
(`SELECT name, value FROM SYSIBMADM.DBCFG WHERE name LIKE 'mon_%'`) and **degrade gracefully** if a
customer has set a level to `NONE` — emit the counters that are populated, skip the timing fields that
aren't (`_research/db2-editions-versions.md:257-277`, `_research/db2-live-pkgcache.md:368-377`).

---

## 4. Privileges — what the monitoring user needs

All of the SQL above runs over a **database connection** (these are SQL functions/views, not OS
commands). The monitoring user needs **one** data-access authority *or* targeted `EXECUTE` grants:

- **`SYSMON`** — the **least-privileged, monitoring-purpose** authority. It covers the entire
  `MON_GET_*` family **plus** the config/env views (`DBCFG`, `DBMCFG`, `ENV_*`, `REG_VARIABLES`). **This
  is the right recommendation for a read-only DBM user** (`_research/db2-config-settings.md:305-312`,
  `_research/db2-live-activity.md:508-510`).
- Broader alternatives that also work: `DBADM`, `SQLADM`, `DATAACCESS`, or
  `SYSADM`/`SYSCTRL`/`SYSMAINT`.
- Or grant **`EXECUTE` on the specific routines** the agent calls — e.g.
  `GRANT EXECUTE ON FUNCTION SYSPROC.MON_GET_PKG_CACHE_STMT TO USER datadog` (this exact grant was
  observed in the live package cache) (`_research/db2-live-pkgcache.md:406-409`). For settings,
  extend to `SYSPROC.DBM_GET_CFG`, `DB_GET_CFG`, `REG_LIST_VARIABLES`, `ENV_GET_*`
  (`_research/db2-config-settings.md:308-312`).
- **EXPLAIN** additionally needs the EXPLAIN tables to exist and the privilege to populate/read them.

**Notes & gotchas:**
- On our local-dev container the check connects as **`db2inst1`** (the instance owner), which has full
  authority — so probes "just work" there and don't exercise the least-privilege path
  (`_research/db2-config-settings.md:317-319`).
- The shipped README already documents granting `EXECUTE` on the MON_GET functions or one of
  `DATAACCESS`/`DBADM`/`SQLADM` (`/home/bits/dd/integrations-core/ibm_db2/README.md:58-106`); the plan
  should extend this to the new routines or just recommend `SYSMON`.
- The `_DETAILS` XML-variant functions (e.g. `MON_GET_PKG_CACHE_STMT_DETAILS`) exist but were **not
  callable** as `db2inst1` in probes (argument/grant issues) — they are **not required** for core
  features; treat their grants/signatures as needing separate verification
  (`_research/db2-live-pkgcache.md:401-409`, `_research/db2-editions-versions.md:375`).
- **Db2 on Cloud** (managed LUW) may withhold `SYSMON`/`DBADM` and block instance-scope reads — expect
  auth failures there, not missing functions (out of scope for now,
  `_research/db2-editions-versions.md:286`).

---

## 5. Editions & versions — how they gate features

**Target = Db2 LUW. Ours = 12.1.4.0, Community Edition (DEC).** Three independent gating axes; the
canonical detail is `_research/db2-editions-versions.md`, condensed here.

### 5.1 Version

Detect with the **packed integer** for easy comparisons:
`SELECT versionnumber FROM SYSIBM.SYSVERSIONS` → **`12010400`** (`= VV RR MM FF = 12.01.04.00`)
(`_research/db2-config-settings.md:348-355`). Human string: `ENV_INST_INFO.SERVICE_LEVEL` =
`DB2 v12.1.4.0` (`_research/db2-config-settings.md:229-239`). Packed values for gating:
11.1→`11010000`, 11.5→`11050000`, 12.1→`12010000` (`_research/db2-editions-versions.md:79-83`).

**The only version difference that matters for this plan is *additive columns*** (12.1 adds
`MODEL_PROVIDER_*` AI-inference waits, more caching-tier/columnar `POOL_COL_*`, extra `ENV_SYS_INFO`
columns). **No feature is removed 11.5→12.1.** Runtime column introspection (§2.1) handles all of it;
only use `versionnumber` to *label* a 12.1-only metric or skip a known-absent function
(`_research/db2-editions-versions.md:85-101`).

### 5.2 Edition

Detect with `SELECT installed_prod, license_type FROM SYSIBMADM.ENV_PROD_INFO WHERE
license_installed='Y'` → live `DEC` / `COMMUNITY` (`_research/db2-config-settings.md:252-259`). Edition
codes: `DEC` (Community), `WSE`/`AWSE` (Workgroup), `ESE`/`AESE` (Enterprise), `ADV`/`STD`/`*_AI`, etc.

**Edition gates capacity (cores/RAM) and whether cluster topologies can be *enabled* — it does NOT
remove any monitoring function/view on LUW.** Confirmed live: Community Edition exposes the **complete**
surface — all 64 MON_GET functions, all 79 SYSIBMADM views, EXPLAIN, package cache, activity, config
reads (`_research/db2-editions-versions.md:56-62, 200-224`). **→ Do not gate any DBM feature off
`LICENSE_TYPE='COMMUNITY'`.** Edition detection is useful only for tagging, explaining empty cluster
results, and a capacity advisory.

### 5.3 Topology (the real gate for cluster-only telemetry)

Cluster-only functions **exist on all editions but return rows only with the matching topology**:

- **pureScale** (shared-disk cluster): `MON_GET_CF`, `MON_GET_CF_CMD`, `MON_GET_CF_WAIT_TIME`,
  `MON_GET_GROUP_BUFFERPOOL`, the `POOL_*_GBP_*` columns. Detect via `SELECT count(*) FROM
  SYSIBMADM.DB2_CF` > 0. Empty on standalone.
- **DPF/MPP**: `MON_GET_FCM`, `MON_GET_FCM_CONNECTION_LIST`. Detect via `ENV_INST_INFO.NUM_DBPARTITIONS
  > 1`.
- **HADR** (replication/standby): `MON_GET_HADR` returns rows **only when an HADR pair is configured**;
  detect via `SELECT count(*) FROM TABLE(MON_GET_HADR(-1))` > 0
  (`_research/db2-editions-versions.md:186-191, 331-347`).

**The right pattern — data-gate, don't edition-branch:** call the function unconditionally and **skip
emission when the result set is empty or the cluster columns are 0/NULL**. The shipped check already
does exactly this for group-buffer-pool hit ratios (only computes when `pool_*_gbp_*` reads are
non-zero) (`_research/db2-editions-versions.md:43-50, 297-327`). On our standalone Community server all
CF/GBP/FCM/HADR telemetry is silently empty, and that is correct behavior.

### 5.4 Capability probe (do this once per connection)

The plan should run a **one-time capability probe** at connection setup and cache it: `versionnumber`
+ `service_level`; `installed_prod` + `license_type`; topology booleans (`is_purescale`, `is_dpf`,
`is_hadr`, `member_count`); and the `mon_*_metrics` levels (§3). Tag telemetry with `db2_version`,
`db2_edition`, and topology booleans (`_research/db2-editions-versions.md:382-389`).

---

## 6. The mapping table — Db2 monitoring surface → what the integration builds on it

This is the bridge from "Db2 surface" to "DBM feature" that the rest of the plan elaborates. Tracks
in the rightmost column are the `dbm-*` event-platform tracks (`00-README.md`).

| Db2 monitoring surface | Primary object(s) | DBM/metric feature built on it | Track / output | Analog |
|---|---|---|---|---|
| **System / DB / instance counters** | `MON_GET_DATABASE`, `MON_GET_INSTANCE`, `MON_GET_BUFFERPOOL`, `MON_GET_TABLESPACE`, `MON_GET_CONTAINER`, `MON_GET_TRANSACTION_LOG` | **Standard metrics** (buffer-pool I/O & timing, direct I/O, log space, tablespace/container utilization, agent/connection counts) | `ibm_db2.*` metrics (+ `dbm-metrics`) | `pg_stat_database`, `pg_statio_*` |
| **Per-object counters** | `MON_GET_TABLE`, `MON_GET_INDEX` | **Per-table / per-index metrics** (hot tables, scan ratios, index efficiency, B-tree maintenance) — cardinality-controlled (top-N) | `ibm_db2.*` metrics | `pg_stat_user_tables/indexes` |
| **WLM roll-ups** | `MON_GET_SERVICE_SUBCLASS`, `MON_GET_WORKLOAD` | **Workload time-spent / wait decomposition** (always populated via `SYSDEFAULT*`) | `ibm_db2.*` metrics | (SQL Server Resource Governor) |
| **Memory pools/sets** | `MON_GET_MEMORY_SET`, `MON_GET_MEMORY_POOL` | **Memory-pressure gauges** (package cache, lock list, sort heap usage vs limits) — *(verify columns via DESCRIBE)* | `ibm_db2.*` metrics | (no direct analog) |
| **Package cache (cumulative per-statement)** | `MON_GET_PKG_CACHE_STMT` (327 cols; key `EXECUTABLE_ID`) | **Query metrics** — diff snapshots, obfuscate, `query_signature`, divide by `NUM_EXEC_WITH_METRICS` | `dbm-metrics` | `pg_stat_statements` |
| **In-flight activity (point-in-time)** | `MON_CURRENT_SQL` / `MON_GET_ACTIVITY` (+ `MON_GET_CONNECTION` for identity) | **Query samples + active-session history** (ASH-style; misses sub-interval OLTP) | `dbm-samples` + `dbm-activity` | `pg_stat_activity` |
| **Transaction state** | `MON_GET_UNIT_OF_WORK` / `MON_CURRENT_UOW` | **Idle-in-transaction / long-open-txn** enrichment (no stmt text) | `dbm-activity` enrichment | `pg_stat_activity` xact fields |
| **Per-agent state** | `MON_GET_AGENT` *(verify columns)* | Optional **blocking/current-state** sampling | `dbm-activity` | (no direct analog) |
| **EXPLAIN tables** | `EXPLAIN_*` (`EXPLAIN_OPERATOR` cost schema; timerons) | **Execution plans** — EXPLAIN → read tables → JSON (highest-risk, spike-gated) | `dbm-samples` (`dbm_type:"plan"`) | `EXPLAIN (FORMAT JSON)` |
| **Config (instance + database)** | `SYSIBMADM.DBMCFG` ∪ `DBCFG` (+ `REG_VARIABLES`) | **Settings** metadata (incl. derived `pending_change`) | `dbm-metadata` (`kind:"db2_settings"`) | `pg_settings` / `mysql_variables` |
| **Catalog metadata** | `SYSCAT.TABLES`/`COLUMNS`/`INDEXES`/`ROUTINES` (+ `SYSCAT.INDEXES` to name indexes) | **Schema** metadata (tables/columns/indexes) | `dbm-metadata` | `information_schema` collection |
| **Version / edition / host** | `SYSIBM.SYSVERSIONS`, `ENV_INST_INFO`, `ENV_PROD_INFO`, `ENV_SYS_INFO`, `MON_GET_INSTANCE` | **`database_instance` registration** + `dbms_version` + edition/topology tags + capability probe | `database_instance` event / tags | server version + cloud metadata |
| **HADR / CF / GBP / FCM** | `MON_GET_HADR`, `MON_GET_CF*`, `MON_GET_GROUP_BUFFERPOOL`, `MON_GET_FCM*` | **Replication-lag / cluster metrics** — emit only when topology present (data-gate on non-empty) | `ibm_db2.*` / `dbm-health` | `pg_stat_replication` (HADR) |
| **Monitor collection knobs** | `SYSIBMADM.DBCFG` (`mon_*_metrics`) | **Capability/feature-gating input** — decide which timing fields to emit | (internal gating) | `track_io_timing` / `performance_schema` consumers |

**One-line takeaway:** the modern `MON_GET_*` table functions (pulled, diffed, obfuscated) carry the
overwhelming majority of the plan — query metrics, samples, system + per-object + WLM metrics — with
`SYSIBMADM` config/ENV views supplying settings + version/edition, `SYSCAT` supplying schemas, and
`EXPLAIN` supplying plans. On Community Edition 12.1.4 every one of these is available; the only gaps
are genuinely cluster-only (CF/GBP/FCM) or HADR telemetry that requires a topology the edition can't
run — and those are handled by tolerating empty result sets, not by branching on edition.
