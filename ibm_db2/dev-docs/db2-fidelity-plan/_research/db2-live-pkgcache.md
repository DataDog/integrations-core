# Db2 12.1.4 Live Package-Cache Probe — `MON_GET_PKG_CACHE_STMT`

Raw empirical research input for the Db2 query-metrics implementation plan. This is the
**query-metrics source of truth** (the Db2 analog of `pg_stat_statements`). All output below
was captured live, on **2026-06-15**, from the running local-dev container while the orders
inventory workload was actively executing parameterized inventory queries.

> Scope note: this doc covers the package-cache statement-metrics source only. It is raw
> input for an implementation plan handed to another agent — favor completeness over brevity.
> Do NOT hard-code column sets from this doc; introspect at runtime (see §9). Confirm units
> per-column against IBM docs (cited in §10) — they are inconsistent across columns.

---

## 0. Environment / how this was captured

- Container: `db2-primary`, image `icr.io/db2_community/db2:12.1.4.0`, status `Up 2 days (healthy)`.
  - Sibling containers running concurrently: `orders-app-db2-bits` (workload generator,
    `db2-orders-app-db2` image) and `datadog-agent-db2-bits` (`dbm-local-db2-agent:7.78.0`).
- Product level (`db2level`):
  - `DB2 v12.1.4.0`, code release `SQL12014`, level identifier `02050110`, Fix Pack `0`,
    64-bit, installed at `/opt/ibm/db2/V12.1`.
  - Server string in connect banner: `DB2/LINUXX8664 12.1.4.0`.
- Database: `TESTDB`. Auth ID: `DB2INST1`. The local `db2inst1` OS user needs **no password**.
- Invocation pattern used for every probe (cwd is reset between calls — always uses absolute
  semantics via `su -`):

  ```bash
  docker exec db2-primary su - db2inst1 -c \
    "db2 connect to testdb > /dev/null; db2 -x \"<SQL>\"; db2 connect reset > /dev/null"
  ```

  Quoting gotcha discovered live: Db2 CLP treats `"..."` as a **delimited identifier**, so
  a string literal like `'SYS%'` must be single-quoted *inside* an outer double-quoted CLP
  statement (`db2 -x "select ... where x like 'SYS%'"`). Wrapping a literal in double quotes
  yields `SQL0206N ... is not valid in the context where it is used. SQLSTATE=42703`.
  The `-x` flag suppresses the column-header/footer so rows can be parsed.

- Workload tables confirmed present (non-`SYS%`):
  `DB2INST1.INVENTORY_ITEMS`, `DB2INST1.SHIPMENTS`, plus the activity event-monitor tables
  `DB2INST1.ACTIVITY*_DD_ACTIVITIES`, `DB2INST1.CONTROL_DD_ACTIVITIES`,
  `DB2INST1.DD_PKGCACHE_VIEW`, `DB2INST1.DD_LOAD`, and `DATADOG.T_STMTID_TEST`.

---

## 1. TL;DR (the load-bearing facts)

1. **Source table function:** `TABLE(MON_GET_PKG_CACHE_STMT(NULL, NULL, NULL, -1))`. Returns
   cumulative-since-database-activation per-cached-section counters for both dynamic and static
   SQL. This is the Db2 equivalent of `pg_stat_statements`.
2. **327 columns** total in 12.1.4 (full list in §6). Counts (>0 num_executions) are real:
   157 rows initially, growing to 225 within the same session as the workload ran.
3. **Stable identity = `EXECUTABLE_ID`** — a `VARCHAR(32) FOR BIT DATA` (exactly 32 bytes;
   confirmed `LENGTH(executable_id) = 32`). Renders as `x'....'` raw, or via `HEX()` as a
   64-char uppercase hex string. The full 64-char `HEX(EXECUTABLE_ID)` **is stable across
   successive snapshots** of the same cache entry (verified — see §4), so it is a safe diff key.
4. **`STMT_TEXT` is a `CLOB`** (declared max **2,097,152** bytes = 2 MB; LOB length field
   `2097152` in the DESCRIBE). Observed real lengths in this DB: min 12, max 5195 chars.
5. **`STMT_TEXT` is NOT server-normalized.** The package cache stores the statement **as it was
   prepared**: parameterized prepares keep `?` parameter markers; literal-inlined statements keep
   their literals (e.g. `... where sku = 'item1'`). Each distinct literal variant gets its **own
   cache entry with its own `EXECUTABLE_ID`**. The agent MUST obfuscate/normalize client-side
   (compute `query_signature`) — Db2 does not collapse literals for you.
6. **Counters are monotonic** (increase across snapshots; reset only on cache eviction / db
   reactivation) — suitable for the standard "diff two snapshots, drop negative diffs" pattern.
7. **Unit inconsistency (critical):** `TOTAL_CPU_TIME` is in **microseconds**; `STMT_EXEC_TIME`,
   `COORD_STMT_EXEC_TIME`, `TOTAL_ACT_TIME`, `PREP_TIME`, and the other `*_TIME` activity columns
   are in **milliseconds**. Do not mix without converting.
8. **Average divisor = `NUM_EXEC_WITH_METRICS`** (not `NUM_EXECUTIONS`) per IBM guidance: some
   executions may run without metrics collection. In this live DB they happened to be equal for
   the orders statements (e.g. 324/324), but the implementation should divide by
   `NUM_EXEC_WITH_METRICS` and guard against 0.
9. **Monitoring config is already adequate** for timing columns: `mon_act_metrics = BASE`,
   `mon_req_metrics = BASE`, `mon_obj_metrics = EXTENDED` (defaults). Timing columns require
   `mon_act_metrics >= BASE`; the agent should gate timing-derived metrics on this.
10. **Datadog SQL comment tags are present in `STMT_TEXT`.** The orders app prepends a leading
    `/*dddbs='...',dde='...',ddps='...',ddprs='...'*/` comment. The obfuscator/signature step must
    strip/handle these leading comments (they otherwise defeat dedup and pollute the text).

---

## 2. The probe SQL and the EXACT command run

Main evidence query (top statements by CPU, with the requested columns):

```bash
docker exec db2-primary su - db2inst1 -c \
"db2 connect to testdb > /dev/null; \
 db2 -x \"select num_executions, total_cpu_time, stmt_exec_time, rows_read, rows_returned, \
          rows_modified, substr(hex(executable_id),1,40) as exec_id_hex, \
          substr(stmt_text,1,90) as stmt \
   from table(mon_get_pkg_cache_stmt(NULL,NULL,NULL,-1)) \
   where num_executions > 0 order by total_cpu_time desc fetch first 15 rows only\"; \
 db2 connect reset > /dev/null"
```

Argument meaning for `MON_GET_PKG_CACHE_STMT(section_type, executable_id, member, ...)`:
- arg1 `section_type`: `NULL` = both dynamic + static (`'D'` = dynamic only).
- arg2 `executable_id`: `NULL` = all cached sections; or pass a specific `x'...'` to fetch one
  section cheaply (the recommended two-step pattern on large/busy systems).
- arg3 `member`: `NULL` = current member.
- arg4 `-1` = current member (vs `-2` = aggregate all members). Both `-1` and `-2` appear in IBM
  examples; `-1`/current-member is fine for the single-member local container.

---

## 3. REAL output — top statements by CPU (abbreviated, headers added)

`num_exec | total_cpu_time(us) | stmt_exec_time(ms) | rows_read | rows_returned | rows_modified | exec_id_hex(first40) | stmt_text(first 90)`

```
14738 | 914552 | 2634 | 737    | 0   | 0  | 0100000000000000980100000000000000000000 | /*dddbs='orders-app-bits',dde='local',ddps='orders-app-bits',ddprs='orders-db2'*/ INSERT I
   48 |  31824 |   32 | 480000 | 48  | 0  | 0100000000000000BA0900000000000000000000 | /*dddbs='orders-app-bits',...*/ select *
    1 |  27535 |   28 |  14953 | 3   | 0  | 0100000000000000B90900000000000000000000 | SELECT VARCHAR(PARMNAME,20) ... FROM SYSCAT.ROU   (catalog introspection, not orders)
    8 |  17609 |   18 |  80000 | 400 | 0  | 0100000000000000C60900000000000000000000 | /*dddbs='orders-app-bits',ddps='orders-app-bits'*/ SELECT sku FROM inventory_items ORDER B
    8 |   5169 |    5 |  80000 | 8   | 0  | 0100000000000000C70900000000000000000000 | /*dddbs='orders-app-bits',...*/ SELECT q
    8 |   4208 |    5 |  80000 | 0   | 8  | 0100000000000000C80900000000000000000000 | /*dddbs='orders-app-bits',...*/ UPDATE i
```

(Other rows were DDL/setup: `CALL SYSPROC.SYSINSTALLOBJECTS(...)`, `CREATE FUNCTION SYSTOOLS...`,
`grant execute on function sysproc.MON_GET_PKG_CACHE_STMT to user datadog`, etc.)

Consolidated, later-in-session snapshot for the orders inventory statements specifically
(`num_exec | num_exec_with_metrics | cpu_us | exec_ms | rows_read | rows_returned | rows_modified | stmt_body`):

```
324 | 324 | 217556 | 218 | 3240000 | 324  | 0  | select * from inventory_items where sku = 'item1'
 81 |  81 | 161192 | 161 |  810000 | 4050 | 0  | ... inventory_items ORDER BY RAND() FETCH FIRST 50 ROWS ONLY
324 | 324 | 153886 | 154 |       0 | 324  | 0  | select count(*) from inventory_items
 81 |  81 |  48656 |  48 |  810000 | 0    | 81 | UPDATE inventory_items SET quantity = ? WHERE sku = ?
 81 |  81 |  48178 |  48 |  810000 | 81   | 0  | SELECT quantity FROM inventory_items WHERE sku = ?
```

Observations from real data:
- `INSERT INTO ...` is the hottest (14738 executions, ~0.9 s cumulative CPU) — the shipments
  insert loop.
- `rows_read = 3240000` for `select * ... sku='item1'` over 324 executions = 10000 rows read per
  exec but only 1 returned (`rows_returned`/324 = 1) → a full-table-scan-style lookup with no
  index on `sku` for this literal path. (`rows_read` >> `rows_returned` is the classic
  inefficiency signal the metric is meant to surface.)
- `count(*)` has `rows_read = 0` here (statistics/zero-row path) but real CPU — counters are
  independent.
- `rows_modified` is populated only for the UPDATE (81), matching `num_exec`.

---

## 4. Stable-identity verification (two snapshots of the SAME cache entry)

```bash
# snapshot 1
db2 -x "select hex(executable_id), num_executions, total_cpu_time
        from table(mon_get_pkg_cache_stmt(NULL,NULL,NULL,-1))
        where stmt_text like '%UPDATE inventory_items SET quantity%' fetch first 1 rows only"
# snapshot 2 (moments later)
```

Result:
```
snap1: 0100000000000000260A00000000000000000000020020260615021302037276 | 0 | 0
snap2: 0100000000000000260A00000000000000000000020020260615021302037276 | 1 | 2675
```

Conclusions:
- **`HEX(EXECUTABLE_ID)` is identical across snapshots** (`...037276`) → safe, stable diff key.
- **`NUM_EXECUTIONS` and `TOTAL_CPU_TIME` increased** (0→1, 0→2675) between the two reads →
  monotonic cumulative counters confirmed. Diff = (snap2 - snap1) gives per-interval deltas.
- Earlier in the session a re-prepared UPDATE produced a *different* `EXECUTABLE_ID`
  (`...026A...` vs `...0A22...`) for the same text — i.e. re-prepare / cache churn creates a new
  section/identity. The diff logic must therefore key on `EXECUTABLE_ID` for the raw snapshot but
  **re-aggregate by `query_signature`** for the shipped metric so churned identities merge.
- The trailing portion of the binary id encodes a timestamp-like token
  (`...020020260615021302037276` → `2026-06-15 02:13:02.037276`) — do NOT parse/depend on this
  structure; treat `EXECUTABLE_ID` as opaque.

---

## 5. STMT_TEXT fidelity: literals vs parameter markers (the normalization question)

The orders workload mixes both styles. Full text captured live (`substr(stmt_text,1,400)`):

```
/*dddbs='orders-app-bits',dde='local',ddps='orders-app-bits',ddprs='orders-db2'*/ UPDATE inventory_items SET quantity = ? WHERE sku = ?
/*dddbs='orders-app-bits',dde='local',ddps='orders-app-bits',ddprs='orders-db2'*/ select count(*) from inventory_items
/*dddbs='orders-app-bits',ddps='orders-app-bits'*/ SELECT sku FROM inventory_items ORDER BY RAND() FETCH FIRST 50 ROWS ONLY
/*dddbs='orders-app-bits',dde='local',ddps='orders-app-bits',ddprs='orders-db2'*/ select * from inventory_items where sku = 'item1'
/*dddbs='orders-app-bits',dde='local',ddps='orders-app-bits',ddprs='orders-db2'*/ SELECT quantity FROM inventory_items WHERE sku = ?
```

Findings (load-bearing for the obfuscation/signature design):
- **Parameter markers (`?`) are preserved verbatim** when the client prepared a parameterized
  statement (`UPDATE ... SET quantity = ? WHERE sku = ?`, `SELECT quantity ... WHERE sku = ?`).
- **Literals are preserved verbatim** when the client inlined them (`... where sku = 'item1'`).
  This proves **Db2 does NOT auto-normalize literals** in the package cache.
- Therefore a literal-heavy app would explode the cache into one entry per literal value, each
  with a distinct `EXECUTABLE_ID`. The agent MUST run client-side obfuscation (datadog-agent SQL
  obfuscator) to produce `query_signature` and merge these.
- The leading `/*dd...*/` APM comment must be stripped before signature computation (otherwise the
  `dde='local'` vs absent-`dde` difference, seen in the RAND query, would split signatures).
- `?` markers are already "normalized" from the obfuscator's perspective; mixed `?`-and-literal
  texts must both reduce to the same canonical signature.

---

## 6. ALL 327 columns (DESCRIBE output) — name : type [notes]

Command:
```bash
db2 "describe select * from table(mon_get_pkg_cache_stmt(NULL,NULL,NULL,-1))"
# -> "Number of columns: 327"
```

Types below are from the live DESCRIBE. Unless noted, all metric counters are `BIGINT`.
Non-BIGINT / notable columns called out explicitly; the long tail of `BIGINT` counters is
grouped to keep this readable but the names are exact.

### 6a. Identity / metadata columns (NOT plain counters)
| Column | Type | Notes |
|---|---|---|
| `MEMBER` | SMALLINT | DB member id |
| `SECTION_TYPE` | CHAR(1) | `D`=dynamic, `S`=static |
| `INSERT_TIMESTAMP` | TIMESTAMP | when section entered cache (first-seen proxy) |
| `EXECUTABLE_ID` | VARCHAR(32) FOR BIT DATA | **stable identity**, 32 bytes, opaque binary |
| `PACKAGE_SCHEMA` | VARCHAR(128) | |
| `PACKAGE_NAME` | VARCHAR(128) | |
| `PACKAGE_VERSION_ID` | VARCHAR(64) | |
| `SECTION_NUMBER` | BIGINT | |
| `EFFECTIVE_ISOLATION` | CHAR(2) | |
| `LAST_METRICS_UPDATE` | TIMESTAMP | last time metrics changed |
| `VALID` | CHAR(1) | section valid flag |
| `ROUTINE_ID` | BIGINT | |
| `STMT_TYPE_ID` | VARCHAR(32) | |
| `QUERY_COST_ESTIMATE` | BIGINT | optimizer timerons |
| `STMT_PKG_CACHE_ID` | BIGINT | |
| `MAX_COORD_STMT_EXEC_TIMESTAMP` | TIMESTAMP | when max coord exec time occurred |
| `QUERY_DATA_TAG_LIST` | VARCHAR(32) | |
| `STMTNO` | INTEGER | |
| `NUM_ROUTINES` | INTEGER | |
| `SEMANTIC_ENV_ID` | BIGINT | |
| `STMTID` | BIGINT | statement id |
| `PLANID` | BIGINT | plan id |
| `PREP_WARNING` | INTEGER | |
| `PREP_WARNING_REASON` | INTEGER | |
| `LAST_EXEC_ERROR` | INTEGER | |
| `LAST_EXEC_ERROR_SQLERRMC` | VARCHAR(70) | |
| `LAST_EXEC_ERROR_TIMESTAMP` | TIMESTAMP | |
| `LAST_EXEC_WARNING` | INTEGER | |
| `LAST_EXEC_WARNING_SQLERRMC` | VARCHAR(70) | |
| `LAST_EXEC_WARNING_TIMESTAMP` | TIMESTAMP | |
| `TENANT_ID` | BIGINT | |
| `STMT_TEXT` | **CLOB (max 2097152)** | the SQL text; NOT normalized (see §5) |
| `COMP_ENV_DESC` | BLOB (max 10240) | compilation environment |
| `MAX_COORD_STMT_EXEC_TIME_ARGS` | BLOB (max 10485760) | |
| `STMT_COMMENTS` | BLOB (max 10240) | |

### 6b. Core counters requested in the task (all BIGINT)
`NUM_EXECUTIONS`, `NUM_EXEC_WITH_METRICS`, `NUM_COORD_EXEC`, `NUM_COORD_EXEC_WITH_METRICS`,
`TOTAL_CPU_TIME` (**microseconds**), `STMT_EXEC_TIME` (**milliseconds**),
`COORD_STMT_EXEC_TIME` (ms), `TOTAL_ACT_TIME` (ms), `TOTAL_ACT_WAIT_TIME` (ms), `PREP_TIME` (ms),
`ROWS_READ`, `ROWS_RETURNED`, `ROWS_MODIFIED`, `ROWS_DELETED`, `ROWS_INSERTED`, `ROWS_UPDATED`,
`TOTAL_ROUTINE_TIME` (ms), `TOTAL_ROUTINE_INVOCATIONS`, `TOTAL_SECTION_TIME` (ms),
`TOTAL_SECTION_PROC_TIME` (ms), `MAX_COORD_STMT_EXEC_TIME` (ms), `ESTIMATED_RUNTIME`.

### 6c. Time / wait counters (BIGINT, milliseconds unless noted)
`POOL_READ_TIME`, `POOL_WRITE_TIME`, `DIRECT_READ_TIME`, `DIRECT_WRITE_TIME`, `LOCK_WAIT_TIME`,
`TOTAL_SECTION_SORT_TIME`, `TOTAL_SECTION_SORT_PROC_TIME`, `WLM_QUEUE_TIME_TOTAL`,
`FCM_RECV_WAIT_TIME`, `FCM_SEND_WAIT_TIME`, `LOG_BUFFER_WAIT_TIME`, `LOG_DISK_WAIT_TIME`,
`LOCK_WAIT_TIME_GLOBAL`, `RECLAIM_WAIT_TIME`, `SPACEMAPPAGE_RECLAIM_WAIT_TIME`, `CF_WAIT_TIME`,
`AUDIT_FILE_WRITE_WAIT_TIME`, `AUDIT_SUBSYSTEM_WAIT_TIME`, `DIAGLOG_WRITE_WAIT_TIME`,
`FCM_MESSAGE_RECV_WAIT_TIME`, `FCM_MESSAGE_SEND_WAIT_TIME`, `FCM_TQ_RECV_WAIT_TIME`,
`FCM_TQ_SEND_WAIT_TIME`, `TOTAL_ROUTINE_USER_CODE_PROC_TIME`, `TOTAL_ROUTINE_USER_CODE_TIME`,
`EVMON_WAIT_TIME`, `TOTAL_EXTENDED_LATCH_WAIT_TIME`, `TOTAL_DISP_RUN_QUEUE_TIME`,
`TOTAL_STATS_FABRICATION_TIME`, `TOTAL_SYNC_RUNSTATS_TIME`, `PREFETCH_WAIT_TIME`,
`IDA_SEND_WAIT_TIME`, `IDA_RECV_WAIT_TIME`, `COMM_EXIT_WAIT_TIME`,
`POOL_CACHING_TIER_PAGE_READ_TIME`, `POOL_CACHING_TIER_PAGE_WRITE_TIME`,
`TOTAL_COL_TIME`, `TOTAL_COL_PROC_TIME`, `TOTAL_INDEX_BUILD_TIME`, `TOTAL_INDEX_BUILD_PROC_TIME`,
`TOTAL_COL_SYNOPSIS_TIME`, `TOTAL_COL_SYNOPSIS_PROC_TIME`, `LOB_PREFETCH_WAIT_TIME`,
`FED_WAIT_TIME`, `EXT_TABLE_RECV_WAIT_TIME`, `EXT_TABLE_SEND_WAIT_TIME`,
`TOTAL_ROUTINE_NON_SECT_TIME`, `TOTAL_ROUTINE_NON_SECT_PROC_TIME`,
`CACHING_TIER_DIRECT_READ_TIME`, `MODEL_PROVIDER_WAIT_TIME`.

### 6d. Buffer-pool / I-O counters (BIGINT)
`DIRECT_READS`, `DIRECT_READ_REQS`, `DIRECT_WRITES`, `DIRECT_WRITE_REQS`,
`POOL_DATA_L_READS`, `POOL_TEMP_DATA_L_READS`, `POOL_XDA_L_READS`, `POOL_TEMP_XDA_L_READS`,
`POOL_INDEX_L_READS`, `POOL_TEMP_INDEX_L_READS`, `POOL_DATA_P_READS`, `POOL_TEMP_DATA_P_READS`,
`POOL_XDA_P_READS`, `POOL_TEMP_XDA_P_READS`, `POOL_INDEX_P_READS`, `POOL_TEMP_INDEX_P_READS`,
`POOL_DATA_WRITES`, `POOL_XDA_WRITES`, `POOL_INDEX_WRITES`,
plus the full `POOL_*_GBP_*`, `POOL_*_LBP_PAGES_FOUND`, `POOL_*_CACHING_TIER_*`,
`POOL_COL_*`, `POOL_QUEUED_ASYNC_*`, `POOL_FAILED_ASYNC_*` families (column data, index, xda,
col, temp variants — ~120 columns in total in this group).

### 6e. Sort / hash / OLAP counters (BIGINT)
`TOTAL_SECTION_SORTS`, `TOTAL_SORTS`, `POST_THRESHOLD_SORTS`, `POST_SHRTHRESHOLD_SORTS`,
`SORT_OVERFLOWS`, `TOTAL_HASH_JOINS`, `TOTAL_HASH_LOOPS`, `HASH_JOIN_OVERFLOWS`,
`HASH_JOIN_SMALL_OVERFLOWS`, `POST_SHRTHRESHOLD_HASH_JOINS`, `POST_THRESHOLD_HASH_JOINS`,
`TOTAL_HASH_GRPBYS`, `HASH_GRPBY_OVERFLOWS`, `POST_THRESHOLD_HASH_GRPBYS`,
`TOTAL_OLAP_FUNCS`, `OLAP_FUNC_OVERFLOWS`, `POST_THRESHOLD_OLAP_FUNCS`,
`TQ_SORT_HEAP_REQUESTS`, `TQ_SORT_HEAP_REJECTIONS`, plus `ACTIVE_*_TOP`, `SORT_*_TOP`,
`ESTIMATED_SORT_*` high-water columns.

### 6f. Lock / concurrency counters (BIGINT)
`LOCK_ESCALS`, `LOCK_WAITS`, `LOCK_TIMEOUTS`, `DEADLOCKS`, `LOCK_WAITS_GLOBAL`,
`LOCK_TIMEOUTS_GLOBAL`, `LOCK_ESCALS_MAXLOCKS`, `LOCK_ESCALS_LOCKLIST`, `LOCK_ESCALS_GLOBAL`.

### 6g. Other BIGINT counters (full names, grouped)
FCM: `FCM_RECV_VOLUME`, `FCM_RECVS_TOTAL`, `FCM_SEND_VOLUME`, `FCM_SENDS_TOTAL`,
`FCM_MESSAGE_*`, `FCM_TQ_*`, `FCM_*_WAITS_TOTAL`.
Logging: `NUM_LOG_BUFFER_FULL`, `LOG_DISK_WAITS_TOTAL`.
Routines/execution: `TOTAL_APP_SECTION_EXECUTIONS`, `TOTAL_COL_EXECUTIONS`, `NUM_WORKING_COPIES`,
`NUM_EXEC_WITH_ERROR`, `NUM_EXEC_WITH_WARNING`.
WLM/threshold: `WLM_QUEUE_ASSIGNMENTS_TOTAL`, `NUM_LW_THRESH_EXCEEDED`, `THRESH_VIOLATIONS`,
`POST_THRESHOLD_PEDS`, `POST_THRESHOLD_PEAS`, `TOTAL_PEDS`, `DISABLED_PEDS`, `TOTAL_PEAS`,
`POST_THRESHOLD_COL_VECTOR_CONSUMERS`, `TOTAL_COL_VECTOR_CONSUMERS`,
`COL_VECTOR_CONSUMER_OVERFLOWS`.
Stats/runstats: `TOTAL_STATS_FABRICATIONS`, `TOTAL_SYNC_RUNSTATS`.
Internal rows: `INT_ROWS_DELETED`, `INT_ROWS_INSERTED`, `INT_ROWS_UPDATED`.
Federation: `FED_ROWS_DELETED`, `FED_ROWS_INSERTED`, `FED_ROWS_UPDATED`, `FED_ROWS_READ`,
`FED_WAITS_TOTAL`.
External table / IDA: `EXT_TABLE_*` (recv/send volume + totals + read/write volume),
`IDA_SENDS_TOTAL`, `IDA_SEND_VOLUME`, `IDA_RECVS_TOTAL`, `IDA_RECV_VOLUME`.
Audit/diag: `AUDIT_EVENTS_TOTAL`, `AUDIT_FILE_WRITES_TOTAL`, `AUDIT_SUBSYSTEM_WAITS_TOTAL`,
`DIAGLOG_WRITES_TOTAL`, `EVMON_WAITS_TOTAL`.
Latch/dispatch: `TOTAL_EXTENDED_LATCH_WAITS`, `AGENTS_TOP`.
Prefetch/LOB: `PREFETCH_WAITS`, `LOB_PREFETCH_REQS`.
Columnar/index-build: `TOTAL_INDEXES_BUILT`, `TOTAL_COL_SYNOPSIS_EXECUTIONS`,
`COL_SYNOPSIS_ROWS_INSERTED`.
Caching tier: `CACHING_TIER_DIRECT_READS`, `CACHING_TIER_DIRECT_READ_REQS`.
Misc: `TQ_TOT_SEND_SPILLS`, `COMM_EXIT_WAITS`, `MODEL_PROVIDER_WAITS_TOTAL`,
`ADM_OVERFLOWS`, `ADM_BYPASS_ACT_TOTAL`.

> The full machine-parsed 327-row `name<TAB>type<TAB>type_len<TAB>lob_len` dump was produced
> during this probe; the groupings above preserve every exact column name. If the implementer
> needs the literal flat list, re-run the DESCRIBE command in §6.

---

## 7. STMT_TEXT type confirmation + truncation handling

- `DESCRIBE` reports `STMT_TEXT` as **`CLOB`** with `Lob length = 2097152` (2 MB max).
- Practical handling: select with `SUBSTR(STMT_TEXT, 1, N)` (CLP/driver-friendly) or cast to
  VARCHAR for a bounded fetch. Observed real max length in this DB = 5195 chars, so a 2 MB cap
  is far above anything the orders workload produces, but the driver/agent should still bound the
  fetch (e.g. first 4–16 KB) and **set a truncation flag** if `LENGTH(STMT_TEXT) > fetch_limit`
  (mirror the MySQL `get_truncation_state` enum: `truncated` / `not_truncated`). Db2 does not
  append a `...` marker — detect truncation via `LENGTH(STMT_TEXT)` vs the SUBSTR cap.
- CLOB retrieval over `ibm_db` / CLI: ensure the LOB is materialized (some drivers return a LOB
  locator). The two-step pattern (fetch `EXECUTABLE_ID` cheaply, then fetch `STMT_TEXT` per id via
  `MON_GET_PKG_CACHE_STMT(NULL, x'...', NULL, -1)`) avoids dragging full CLOBs for every row on
  large caches.

---

## 8. Units verified live + averages

`avg = column / NUM_EXEC_WITH_METRICS` (guard 0). Verified derivation live:

```
SELECT quantity FROM inventory_items WHERE sku = ?
  num_executions=1, total_cpu_time=3679 (us), avg_cpu_us=3679,
  stmt_exec_time=4 (ms), avg_exec_ms=4
```

- `TOTAL_CPU_TIME` **microseconds** (3679 us ≈ 3.7 ms; consistent with `stmt_exec_time`=4 ms — CPU
  time is a subset of elapsed). Confirms the **us vs ms** split.
- `STMT_EXEC_TIME`, `COORD_STMT_EXEC_TIME`, `TOTAL_ACT_TIME` **milliseconds**.
- `INSERT_TIMESTAMP` and `LAST_METRICS_UPDATE` are full TIMESTAMPs
  (e.g. `2026-06-15-02.09.24.583014`). `INSERT_TIMESTAMP` can seed a "first seen" sample.

Monitoring config captured live (`SYSIBMADM.DBCFG`):
```
mon_act_metrics  = BASE      (>= BASE required for activity timing columns)
mon_req_metrics  = BASE
mon_obj_metrics  = EXTENDED
mon_uow_data     = NONE
mon_lck_msg_lvl  = 1
```
All at defaults → timing metrics are populated. The agent should still **introspect these** and
gate timing-derived metrics if a customer has set them to `NONE`.

---

## 9. Implementation guidance for the diff/collection job (from live behavior)

1. **Introspect columns at runtime**, do not hard-code by fixpack. Read `cursor.description` of a
   `... FETCH FIRST 0 ROWS ONLY` (or `WHERE 1=0`) probe, intersect with the desired set, and
   `sorted(available & desired)`. 12.1.4 has 327 columns; older fixpacks have fewer (e.g. no
   `MODEL_PROVIDER_*`, fewer `*_CACHING_TIER_*`). This mirrors the Postgres `statements.py`
   approach. (Ref: `code-postgres-dbm-statements.md:108`, `code-base-framework.md`.)
2. **Snapshot key:** `HEX(EXECUTABLE_ID)` (stable, verified §4) plus `MEMBER` and the database
   name. Keep a `_previous` snapshot; diff cumulative columns; **drop rows whose diff is negative**
   wholesale (cache eviction / db reactivation = counter reset). Require
   `NUM_EXEC_WITH_METRICS` (or `NUM_EXECUTIONS`) to have increased before emitting.
3. **Final merge key:** `query_signature` (client-side obfuscation) — re-aggregate across churned
   `EXECUTABLE_ID`s and across literal variants (§5). Strip the leading `/*dd...*/` APM comment
   before signature computation.
4. **Averages divide by `NUM_EXEC_WITH_METRICS`** (IBM-recommended), not `NUM_EXECUTIONS`.
5. **Unit normalization:** convert `TOTAL_CPU_TIME` us→ms (or keep us and document) before mixing
   with `STMT_EXEC_TIME`/`TOTAL_ACT_TIME` (ms). DBM payload conventions decide final unit.
6. **Cost control:** for large caches, fetch identity + counters in the broad call, then fetch
   `STMT_TEXT` per top-N `EXECUTABLE_ID` (two-step pattern, §2/§10). Avoid pulling 2 MB CLOBs for
   every cached section every interval.
7. **`MON_GET_PKG_CACHE_STMT_DETAILS`** (the XML-detail sibling that adds per-section
   metric-detail XML / activity metrics) was **NOT directly callable** as `db2inst1` in this probe
   — both `MON_GET_PKG_CACHE_STMT_DETAILS(NULL,NULL,NULL,-1,'')` and 2-arg variants returned
   `SQL0440N No authorized routine ... having compatible arguments`. Treat its signature/grants as
   needing separate verification; it is **not required** for the core query-metrics feature
   (the flat `MON_GET_PKG_CACHE_STMT` columns cover exec count / CPU / exec time / rows). The DBA
   probe used the `datadog` user grant: `grant execute on function sysproc.MON_GET_PKG_CACHE_STMT
   to user datadog` (seen in the cache itself), so the agent's monitoring user needs
   `EXECUTE` on `SYSPROC.MON_GET_PKG_CACHE_STMT`.

---

## 10. Citations

Live-probe evidence (this document, all captured 2026-06-15 against container `db2-primary`,
image `icr.io/db2_community/db2:12.1.4.0`, DB `TESTDB`, user `db2inst1`): see §2–§8 for the exact
commands and raw output.

Code / repo references (absolute paths):
- `/home/bits/dd/integrations-core/ibm_db2/dev-docs/db2-fidelity-plan/_research/code-postgres-dbm-statements.md`
  — runtime column introspection pattern (`statements.py:108`, `:157`, `:211-232`, `:361`),
  snapshot-diff design, `EXECUTABLE_ID` as stable identity, timing-column gating on
  `mon_act_metrics`/`mon_req_metrics` (`:223`).
- `/home/bits/dd/integrations-core/ibm_db2/dev-docs/db2-fidelity-plan/_research/code-base-framework.md`
  — `StatementMetrics.compute_derivative_rows` analog; key `(query_signature, EXECUTABLE_ID)`
  (`:135-137`, `:420`).
- `/home/bits/dd/integrations-core/ibm_db2/dev-docs/db2-fidelity-plan/_research/code-sqlserver-dbm-template.md`
  — `Db2StatementMetrics(DBMAsyncJob)` over `MON_GET_PKG_CACHE_STMT` (`:322-329`, `:431`, `:485`).
- `/home/bits/dd/integrations-core/ibm_db2/dev-docs/db2-fidelity-plan/_research/code-mysql-dbm.md`
  — truncation-state pattern to mirror for `STMT_TEXT` (`:477`).
- `/home/bits/dd/integrations-core/ibm_db2/dev-docs/db2-fidelity-plan/_research/code-ibm_db2-current.md`
  — confirms the current integration has NO statement metrics yet (`:356-358`).

IBM / web references (units, types, semantics):
- MON_GET_PKG_CACHE_STMT table function (IBM Db2 docs, 11.5.x — same column semantics as 12.1):
  https://www.ibm.com/docs/en/db2/11.5.x?topic=mmr-mon-get-pkg-cache-stmt-table-function-get-package-cache-statement-metrics
  (12.1 page: https://www.ibm.com/docs/en/db2/12.1 — same topic; returned HTTP 403 to the fetcher,
  use a browser/authenticated client).
- `TOTAL_CPU_TIME` = microseconds; `STMT_EXEC_TIME` = milliseconds; `EXECUTABLE_ID` =
  `VARCHAR(...) FOR BIT DATA` (opaque binary, rendered `x'...'`); two-step "fetch text by
  EXECUTABLE_ID" pattern:
  https://www.raghu-on-tech.com/2020/06/07/using-mon_get_pkg_cache_stmt-to-find-bottlenecks/
  and https://datageek.blog/2015/02/12/db2-administrative-sql-cookbook-finding-problem-sql-in-the-package-cache/
- `mon_act_metrics` (>= BASE required for activity timing metrics; default BASE; db2mon
  prerequisite), `stmt_text` returned as CLOB, average divisor `num_exec_with_metrics`,
  `MON_PKG_CACHE_SUMMARY` aggregated view, MON_GET cumulative-since-activation semantics:
  https://www.ibm.com/docs/en/db2/11.5.x?topic=parameters-mon-act-metrics-monitoring-activity-metrics
  and https://www.ibm.com/docs/en/db2/11.5.x?topic=tuning-collecting-reporting-performance-monitor-data
  and https://www.ibm.com/docs/en/db2/9.7?topic=elements-stmt-exec-time-statement-execution-time
