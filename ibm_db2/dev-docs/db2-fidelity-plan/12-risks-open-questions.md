# 12 — Risks, Caveats & Open Questions

**Audience:** the engineer/agent implementing the Db2 fidelity plan, plus reviewers. This doc
consolidates every load-bearing **risk**, **caveat**, and **decision-needed** surfaced by the
research (`_research/db2-*.md`, `_research/map-*.md`, `_research/_raw/*`) and the sibling plan docs.
It does **not** re-derive mappings — it collects the landmines and the unknowns so they are not
rediscovered mid-implementation. Each section cross-references the sibling doc where the risk is
most actionable.

> **How to read this:** §1–§8 are organized risks (gating, privilege, query-metrics, samples,
> plans, driver/threading, cardinality, packaging). §9 is the numbered **OPEN QUESTIONS** list — the
> human decisions that must be made before or during implementation. Claims that could not be
> confirmed against the live `DB2/LINUXX8664 12.1.4.0` container are tagged **(verify)**.

> **Provenance of the "live" facts below:** all empirical claims trace to the single live ground-truth
> server — container `db2-primary`, image `icr.io/db2_community/db2:12.1.4.0`, DB `TESTDB`, auth ID
> `DB2INST1` (instance owner), **single-member, non-DPF, non-pureScale, non-HADR, Db2 Community
> Edition** (`DEC`/`COMMUNITY`). That single environment is itself a meta-risk: **every "◐ empty"
> and every non-instance-owner privilege claim is unproven** because the test server has neither a
> cluster topology nor a least-privilege monitoring user. See §1, §2.

---

## 1. Db2 version / edition / topology gating

Most relevant sibling: [`_research/db2-editions-versions.md`](_research/db2-editions-versions.md)
(the feature-availability matrix), [`_research/db2-config-settings.md`](_research/db2-config-settings.md) §6
(detection SQL), [`03-reference-architecture.md`](03-reference-architecture.md) (where the capability
probe lives).

### 1.1 Scope decision — **Db2 LUW only** (explicit, must be guarded)

This integration targets **Db2 LUW (Linux/UNIX/Windows)**. Explicitly **out of scope**, and why:

| Platform | Out-of-scope reason | Risk if a customer points the check at it |
|---|---|---|
| **Db2 for z/OS** | **Completely different monitoring surface** — no `MON_GET_*` LUW table functions, different `SYSIBM` catalog, no `SYSIBMADM.DBCFG/DBMCFG`, IFCID/trace-based, different version scheme (Db2 13 for z/OS). | Nearly every SQL path in the plan fails. Would need a separate integration. |
| **Db2 on Cloud** (managed LUW) | Same engine, but **restricted privileges** — a tenant may lack `SYSMON`/`DBADM`; instance-scope reads / `db2set` may be blocked. **(verify)** | Auth failures on instance-scope functions, not missing functions. Partially supportable later. |
| **Db2 Warehouse / IIAS** | LUW-derived but **column-organized (BLU) by default**, OLAP/MPP — `POOL_COL_*`/`TOTAL_COL_*`/synopsis metrics dominate; DPF normal. **(verify)** | Same API family, different metric emphasis; would mis-prioritize metrics. |

**Required guard:** a one-time platform/topology detection at connection setup (§1.4) that at minimum
records LUW-ness implicitly (all SQL assumes it) and tags telemetry with version/edition/topology so
a wrong target is diagnosable. There is **no positive "is this LUW?" probe specified** — the design
assumes LUW and would simply error on z/OS. **Open question OQ-1.**

### 1.2 11.5 vs 12.1 — additive columns only, but a real floor question

- **No 11.5→12.1 difference removes a feature** for this integration. All differences are *additive
  columns* (e.g. `MODEL_PROVIDER_WAIT_TIME`/`MODEL_PROVIDER_WAITS_TOTAL`, expanded
  `POOL_*_CACHING_TIER_*`, `POOL_COL_*`, columnar/synopsis families) plus `ENV_SYS_INFO` gaining
  `OS_FULL_VERSION`/`OS_KERNEL_VERSION`/`OS_ARCH_TYPE`. The live `MON_GET_PKG_CACHE_STMT` has **327
  cols**, `MON_GET_ACTIVITY` **418 cols** on 12.1.4; 11.5 has fewer of both.
- **The mitigation is runtime column introspection, not version branching** (probe
  `... WHERE 1=0` / `FETCH FIRST 0 ROWS ONLY`, intersect `cursor.description` with the desired set).
  Use `versionnumber` (packed int `12010400` from `SYSIBM.SYSVERSIONS`) only to *label* a 12.1-only
  metric or to skip a known-absent function.
- **Caveat:** the existing check's IBM doc URLs point at **11.1** (`SSEPGG_11.1.0`). Semantics are
  stable 11.5→12.1 but the docs the integration cites are two majors stale (re-cite against 12.1).
- **Floor decision needed:** what is the **minimum supported Db2 version**? The research only proves
  12.1.4; 11.5 behavior is inferred. **(verify on an 11.5 instance.) Open question OQ-2.**

### 1.3 Community Edition — capacity-limited, NOT feature-limited

- The live server is **Community Edition (`DEC`/`COMMUNITY`)** and exposes the **complete** monitoring
  surface: all 64 `MON_GET_*` functions, all 79 `SYSIBMADM` views, package cache, activity, EXPLAIN,
  config reads. **Community gets the full DBM feature set.**
- **Do NOT gate any feature off `LICENSE_TYPE='COMMUNITY'`.** Edition gates only (a) **capacity**
  (~4 cores / 16 GB **(verify)**) and (b) whether pureScale/DPF can be enabled at all (Community
  cannot run them → CF/GBP/FCM telemetry is empty, a *topology* gap, not an edition gap).
- Edition detection is useful only for **tagging** (`db2_edition:community`) and explaining empty
  cluster results.

### 1.4 pureScale-only (CF/GBP/FCM) and HADR-only — present-but-empty, never feature-branch

Most relevant: [`_research/map-fcm-purescale.md`](_research/map-fcm-purescale.md),
[`_research/map-hadr-replication.md`](_research/map-hadr-replication.md), and the existing
GBP-skip precedent in the live code.

- `MON_GET_CF`, `MON_GET_CF_CMD`, `MON_GET_CF_WAIT_TIME`, `MON_GET_GROUP_BUFFERPOOL`, `MON_GET_FCM`,
  `MON_GET_FCM_CONNECTION_LIST` **exist on all LUW editions** but return **0 rows** without the
  pureScale/DPF topology. `MON_GET_HADR(-1)` and `SYSIBMADM.SNAPHADR` return rows **only** when HADR
  is configured.
- **Correct pattern (already in the code):** call the function unconditionally and **skip emission on
  empty/zero results** — mirror the existing GBP-ratio data-gate
  (`ibm_db2.py:232-235,269-272,306-309,343-346,365-377`), which gates on the *value* (non-zero
  `*_gbp_*` reads), never on edition. Those branches are marked `# no cov` — i.e. **never exercised on
  the single-member test env**, so the cluster path is structurally untested.
- **Optional:** a one-time topology probe (CF rows > 0 → pureScale; `num_dbpartitions > 1` → DPF;
  `MON_GET_HADR` rows > 0 → HADR) can *suppress the calls entirely* to avoid per-interval overhead.
- **Risk:** **none of CF/GBP/FCM/HADR is verified live** — all column lists for HADR/CF/GBP/FCM are
  "(general Db2 12.1 knowledge — verify)" because the standalone server returns 0 rows. These metrics
  cannot be validated without a pureScale/HADR test bed. **Open question OQ-3.**

### 1.5 The unifying gate: a one-time capability probe

The plan's recommended guard (cache for the connection lifetime, tag telemetry):
`versionnumber` (packed) + `service_level`; `installed_prod` + `license_type`; `is_purescale`,
`is_dpf`, `is_hadr`, `member_count`; and the `mon_*_metrics` levels (§2.3). **Prefer runtime
introspection + empty-result tolerance over hard branching.**

---

## 2. Privilege & monitoring-overhead risks

Most relevant: [`_research/db2-config-settings.md`](_research/db2-config-settings.md) §5,
[`03-reference-architecture.md`](03-reference-architecture.md) (privilege matrix),
[`07-dbm-execution-plans.md`](07-dbm-execution-plans.md) §6 (plan grants).

### 2.1 SYSMON vs DBADM and the EXECUTE grants

- **`SYSMON` is the least-privilege recommendation** — it covers the `MON_GET_*` family + config/ENV
  views. Alternatives: `DBADM`/`SQLADM`/`DATAACCESS`/`SYSADM`/`SYSCTRL`/`SYSMAINT`.
- The existing README grants `EXECUTE` on the five system `MON_GET_*` functions or one of
  `DATAACCESS`/`DBADM`/`SQLADM`. **DBM extends the routine set** — add `EXECUTE` on
  `MON_GET_PKG_CACHE_STMT`, `MON_GET_ACTIVITY`, `MON_GET_CONNECTION`, `MON_GET_UNIT_OF_WORK`,
  `MON_GET_TABLE`, `MON_GET_INDEX`, `MON_GET_WORKLOAD`, `MON_GET_SERVICE_SUBCLASS`,
  `MON_GET_MEMORY_POOL/SET`, the config/env routines (`DBM_GET_CFG`, `DB_GET_CFG`,
  `REG_LIST_VARIABLES`, `ENV_GET_*`), and (for plans) `EXPLAIN_FROM_SECTION` + `SYSINSTALLOBJECTS`.
  `SYSMON` is simpler than enumerating these.
- **Big caveat — everything was tested as `DB2INST1` (the instance owner).** No grant claim is
  verified for a least-privilege `datadog` user. In particular `EXPLAIN_FROM_SECTION` and
  `SYSINSTALLOBJECTS` for a non-owner are **(verify)** (§5, OQ-7). The package cache itself shows a
  `grant execute on function sysproc.MON_GET_PKG_CACHE_STMT to user datadog` — evidence the intended
  user is `datadog`, but its full grant set is unconfirmed. **Open question OQ-4.**

### 2.2 `MON_GET_PKG_CACHE_STMT_DETAILS` not callable

`MON_GET_PKG_CACHE_STMT_DETAILS` is *present* (`_raw/01:43`) but was **NOT callable** as `db2inst1`
(`SQL0440N No authorized routine ... having compatible arguments`). Treat all `*_DETAILS` XML
variants as needing separate signature/grant verification — they are **not required** for core
features (flat `MON_GET_PKG_CACHE_STMT` covers exec count / CPU / exec time / rows).

### 2.3 `mon_*_metrics` collection settings gate WHICH DATA EXISTS

This is **orthogonal to version/edition** and must be checked at runtime via `SYSIBMADM.DBCFG`.
Live values (defaults, all adequate):

| Setting | Live | Gates | Guard |
|---|---|---|---|
| `mon_act_metrics` | `BASE` | Activity timing cols (`TOTAL_ACT_TIME`, waits, `COORD_STMT_EXEC_TIME`, `WLM_QUEUE_TIME_TOTAL`) in `MON_GET_ACTIVITY`/pkg cache | emit timing-derived metrics only when `<> 'NONE'` |
| `mon_req_metrics` | `BASE` | Request-level timing (`MON_GET_SERVICE_SUBCLASS`/`WORKLOAD`) | same |
| `mon_obj_metrics` | `EXTENDED` | Object metrics: `MON_GET_TABLE` row/scan counters need `<> NONE`; `MON_GET_TABLE`/`MON_GET_INDEX` bufferpool-read object columns need `EXTENDED` | gate per-table/index metrics; emit 0 / skip on `NONE` |
| `mon_uow_data` / `mon_uow_pkglist` / `mon_uow_execlist` | `NONE`/`OFF`/`OFF` | UOW statement & package lists | not needed for core features |
| `mon_rtn_execlist` | `OFF` | `MON_GET_ROUTINE_EXEC_LIST` | gate routine-exec-list feature |
| `mon_lockwait` / `mon_locktimeout` / `mon_deadlock` / `mon_lck_msg_lvl` | `NONE`/`NONE`/`WITHOUT_HIST`/`1` | lock-event monitor detail | gate lock-wait detail features |

**Risk:** a customer who set any `mon_*_metrics` to `NONE` gets silent zeros, not errors. Every
timing-derived metric must degrade gracefully and ideally surface the collection level so a UI can
explain the gap. (See [`05-dbm-query-metrics.md`](05-dbm-query-metrics.md) §5,
[`06-dbm-query-samples-activity.md`](06-dbm-query-samples-activity.md), and the per-table gating in
[`_research/map-tables-indexes.md`](_research/map-tables-indexes.md) §E.4.)

### 2.4 Collection cost — the overhead the customer pays

- **`MON_GET_TABLE` / `MON_GET_INDEX`** fan out to one row per object per member (per data partition).
  On a wide schema this is expensive to call *and* to ship — see §7. Top-N + schema filtering are
  mandatory.
- **Plans WRITE to explain tables on every explain** (§5) — a real, persisted operational cost that
  Postgres `EXPLAIN` does not have.
- **No event monitors are required** by the core design (activity is sampled via `MON_GET_ACTIVITY`,
  not an activity event monitor). The live DB *does* have leftover `ACTIVITY*_DD_ACTIVITIES` /
  `CONTROL_DD_ACTIVITIES` event-monitor tables from prior experimentation — **the plan does not depend
  on them**; if any future feature adds an event monitor, its write/storage overhead becomes a new
  cost to manage. **(verify the plan never silently relies on a pre-existing event monitor.)**

---

## 3. Query-metrics risks (`MON_GET_PKG_CACHE_STMT`)

Most relevant: [`05-dbm-query-metrics.md`](05-dbm-query-metrics.md),
[`_research/db2-live-pkgcache.md`](_research/db2-live-pkgcache.md).

1. **Package-cache eviction = counter resets.** Counters are cumulative-since-activation and reset on
   cache eviction or DB reactivation. The diff job must **drop rows whose diff is negative** wholesale
   and require `NUM_EXEC_WITH_METRICS` (or `NUM_EXECUTIONS`) to have increased before emitting. The
   first interval after churn under-reports.
2. **`EXECUTABLE_ID` churn vs `query_signature`.** `HEX(EXECUTABLE_ID)` is stable across snapshots of
   the *same* cache entry (verified) and is the safe **diff key**, but a re-prepare produces a **new**
   `EXECUTABLE_ID` for the same text, and **each literal variant gets its own entry**. So the final
   **merge/aggregation key must be `query_signature`** (client-side obfuscation), re-aggregating across
   churned ids and literal variants. Keying the metric on raw id alone would fragment one logical query.
3. **`NUM_EXEC_WITH_METRICS` vs `NUM_EXECUTIONS`.** IBM guidance: average divisor is
   **`NUM_EXEC_WITH_METRICS`** (some executions run without metrics). They happened to be equal live
   (e.g. 324/324) but the implementation must divide by `NUM_EXEC_WITH_METRICS` and **guard against 0**.
4. **Unit inconsistency (critical).** `TOTAL_CPU_TIME` is **microseconds**; `STMT_EXEC_TIME`,
   `COORD_STMT_EXEC_TIME`, `TOTAL_ACT_TIME`, `PREP_TIME` and the other `*_TIME` columns are
   **milliseconds**. Do not mix without converting. (Db2 monitor-element units are inconsistent
   column-to-column across the board — confirm each against IBM docs.)
5. **`STMT_TEXT` is a CLOB (up to 2 MB), NOT server-normalized.** Db2 stores the statement *as
   prepared*: `?` markers kept for parameterized prepares, literals kept inline otherwise. Obfuscation
   pitfalls:
   - The leading Datadog `/*dddbs=...,dde=...,ddps=...,ddprs=...*/` APM comment **must be stripped
     before computing `query_signature`** — otherwise `dde='local'`-vs-absent differences split
     signatures (seen live on the RAND query).
   - Client-side obfuscation is mandatory (Db2 does not collapse literals); mixed `?`-and-literal
     texts must reduce to the same signature.
   - **CLOB handling:** the driver may return a LOB *locator*; the agent must materialize the text.
     Bound the fetch (e.g. 4–16 KB) and **set a truncation flag** by comparing `LENGTH(STMT_TEXT)` to
     the fetch cap — Db2 appends no `...` marker. Prefer the two-step pattern (fetch ids + counters
     broadly, then fetch `STMT_TEXT` per top-N id) to avoid dragging 2 MB CLOBs every interval (§6.3).

---

## 4. Samples / activity risk (`MON_CURRENT_SQL` / `MON_GET_ACTIVITY`)

Most relevant: [`06-dbm-query-samples-activity.md`](06-dbm-query-samples-activity.md),
[`_research/db2-live-activity.md`](_research/db2-live-activity.md).

1. **The live-proven sub-interval OLTP blind spot (the defining caveat).** `MON_CURRENT_SQL` /
   `MON_GET_ACTIVITY` return only **currently-in-progress** activities — a point-in-time snapshot, not
   cumulative history. **Sub-millisecond OLTP is systematically invisible:** 40–80 point-in-time
   samples **never** caught the orders inventory statements; only deliberately slow statements
   (cartesian join, `dbms_lock.sleep`) were reliably captured. **Implication:** activity sampling is an
   **ASH-style long-query / wait signal**, NOT a complete request log. It must be paired with the
   cumulative package cache (§3) for per-statement completeness, and the feature's docs must state this
   limitation. Sample interval ~1s, accepting sub-interval invisibility.
2. **The probe sees itself.** The collecting query always appears as a row in its own snapshot — the
   agent must **exclude its own `APPLICATION_HANDLE`** (or filter by `APPLICATION_NAME`/`APPLICATION_ID`).
3. **Elapsed vs accumulated time.** Use `MON_CURRENT_SQL.ELAPSED_TIME_MSEC` (true wall-clock since
   `LOCAL_START_TIME`, computed in the view) for "how long has this run." `MON_GET_ACTIVITY.TOTAL_ACT_TIME`
   is **accumulated** and `0` until metrics machinery records it — do **not** use it as elapsed-since-start.
4. **`MON_GET_UNIT_OF_WORK` / `MON_CURRENT_UOW` have NO `STMT_TEXT`.** Use them for transaction state
   (`WORKLOAD_OCCURRENCE_STATE`) and open-transaction age (idle-in-transaction detection), never as the
   statement source.
5. **Same CLOB / obfuscation / APM-comment-stripping caveats as §3.5** apply to the in-flight
   `STMT_TEXT` (it is byte-for-byte the prepared form).
6. **CLP loop fragility (test-harness caveat, not production):** rapid in-shell `for`-loops of
   `db2 -x` intermittently drop the connection (`SQL1024N`). Relevant to writing live tests, not the
   agent (which holds a persistent handle) — see [`11-testing-and-validation.md`](11-testing-and-validation.md).

---

## 5. Execution-plan risks (the highest-variance DBM piece)

Most relevant: [`07-dbm-execution-plans.md`](07-dbm-execution-plans.md),
[`_research/_raw/05-explain-test.txt`](_research/_raw/05-explain-test.txt).

1. **`EXPLAIN_FROM_SECTION` (Path B, the *recommended* path) is UNPROVEN.** Only `EXPLAIN PLAN FOR`
   (Path A) was actually run live. The exact procedure signature, its source-type arg (`'M'`), its OUT
   params, and **whether a non-owner `datadog` user can call it** are all **(verify)**. **If Path B is
   unavailable/unprivileged, the design falls back to Path A and inherits the full parameter-marker
   problem** — the single biggest fidelity risk. This is a **gating spike** before plans commit.
2. **Explain tables are WRITTEN to on every explain** (unlike read-only Postgres `EXPLAIN`). Each
   explain inserts an `EXPLAIN_STATEMENT` + N `EXPLAIN_OPERATOR` + M `EXPLAIN_STREAM` … row-set.
   Mitigations: a **dedicated agent explain schema** (never write to `SYSTOOLS`), **delete-after-read**
   by the 8-column join key, and the rate-limiter as a write-throttle. **Write contention under a busy
   agent loop was not load-tested. (verify under load.)**
3. **Bootstrap idempotency.** Explain tables already exist on the live server (in `SYSTOOLS`);
   `SYSINSTALLOBJECTS('EXPLAIN','C',...)` then raises `SQL0601N ... SQLSTATE=42710` — **treat 42710 as
   success**. Probe-then-create, cache per-schema in a `TTLCache`, never drop/recreate.
4. **Parameter markers (Path A only).** Cached text keeps `?`; `EXPLAIN PLAN FOR ... ? ...` may raise
   `SQL0418N` or produce a degenerate plan. Mitigations (verify the exact 12.1.4 incantation):
   `SET CURRENT EXPLAIN MODE` + `REOPT ONCE`, or substitute typed representative values (`NULL`
   short-circuits predicates and skews plans). **Path B eliminates this entirely**, which is why it is
   preferred.
5. **Plan-JSON shape for a non-Postgres source is unverified.** Db2 has no native JSON EXPLAIN — the
   tree must be **synthesized** from `EXPLAIN_OPERATOR` (nodes) + `EXPLAIN_STREAM` (edges) into a
   Postgres-compatible nested-node document. Whether `datadog_agent.obfuscate_sql_exec_plan` and the UI
   renderer accept the synthesized key names is **the biggest plan-shape open question** — needs a
   round-trip test against a real agent.
6. **Tree assembly is non-trivial.** The 2-node `RETURN <- TBSCAN` live example understates reality:
   `SOURCE_ID`/`TARGET_ID` < 0 denote base objects on a stream, multi-input joins, subquery/`SORT`
   materialization, columnar plans all need iterative validation.
7. **Plans are optimizer ESTIMATES, not actuals.** Db2 EXPLAIN (like pg `EXPLAIN` without `ANALYZE`)
   gives estimated cardinalities/costs only — no actual-rows/actual-time. Do not claim actuals; cost
   numbers arrive as `DOUBLE` (`+1.21895591735840E+002`) → coerce with `float()`.
8. **Path B fidelity depends on the section still being cached** at explain time; an `EXECUTABLE_ID`
   evicted between the metrics read and the explain → a `section_not_found` error. **Ship plans behind
   their own config gate, default disabled, until the §1/§5 spike confirms procedure + privileges.**

---

## 6. `ibm_db` driver / threading constraints

Most relevant: [`_research/code-ibm_db2-current.md`](_research/code-ibm_db2-current.md) §2,
[`_research/code-integration-scaffolding.md`](_research/code-integration-scaffolding.md),
[`09-implementation-architecture.md`](09-implementation-architecture.md) (the wiring doc, referenced
throughout but **not yet present** in the plan dir — its absence is itself OQ-9).

1. **DBM collectors run as `DBMAsyncJob` threads — each needs its OWN `ibm_db` connection.** The
   current check holds a **single persistent `self._conn`** (one handle per check instance, no pooling,
   no per-query connections, reconnect-on-error in `iter_rows`). DBM statements/samples/plans run on
   independent schedules in background threads; **the main check's handle must never be shared across
   threads.** Each job (`dbms="db2"`, distinct `job_name`) opens and owns its own `ibm_db.connect`
   handle and closes it in `shutdown_callback`. (The thread-safety of a *single* `ibm_db` handle across
   threads is not established here — **assume not thread-safe; isolate per job. (verify)**)
2. **CLOB handling (`STMT_TEXT`).** `ibm_db` may return a LOB locator rather than the materialized
   string; the agent must read the full CLOB and bound it (§3.5, §4.5). Confirm `fetch_assoc`/
   `fetch_tuple` materialize the CLOB for `MON_GET_PKG_CACHE_STMT.STMT_TEXT` / `MON_GET_ACTIVITY.STMT_TEXT`.
3. **Statement-handle / "no cursor" model.** The existing code uses `ibm_db.exec_immediate(conn, sql)`
   returning a statement handle, then iterates with `ibm_db.fetch_assoc` (dict, lowercase keys via
   `ibm_db.ATTR_CASE = ibm_db.CASE_LOWER`) or `ibm_db.fetch_tuple`. There is **no DB-API cursor object**
   in the current pattern (it is the `ibm_db` low-level API, not `ibm_db_dbi`). New collectors must
   decide: reuse `exec_immediate`/`fetch_assoc`, or adopt `ibm_db_dbi` (DB-API 2.0 cursor) for
   `callproc` (needed for `EXPLAIN_FROM_SECTION` OUT params) and parameter binding. **This API choice
   is unsettled. Open question OQ-8.** Note `callproc` with OUT params (Path B) is awkward in the raw
   `ibm_db` API and may force `ibm_db_dbi`.
4. **Driver not bundled.** `ibm_db` is a C-extension (`ibm-db==3.2.6`), **not shipped with the Agent**
   — the operator must `pip install` it into the embedded env (Windows additionally needs
   `os.add_dll_directory` for `clidriver/bin`). DBM features inherit this install/packaging burden.
5. **Result keys are lowercase** everywhere (`ATTR_CASE=CASE_LOWER`) — all new column references must
   match lowercase.

---

## 7. Metric-cardinality risks

Most relevant: [`_research/map-tables-indexes.md`](_research/map-tables-indexes.md) (the worst
offender), [`_research/map-connections-applications.md`](_research/map-connections-applications.md),
[`_research/map-tablespace-storage.md`](_research/map-tablespace-storage.md),
[`_research/db2-monget-catalog-2.md`](_research/db2-monget-catalog-2.md) (WLM fan-out).

**Cardinality is the defining risk of the new per-object metrics** — every one is *one time series per
object per member*. The current integration emits **zero** per-object metrics (DB/instance/bufferpool/
tablespace/log only), so all of this is new fan-out:

| Source | Fan-out | Mandatory controls |
|---|---|---|
| `MON_GET_TABLE` | per table × data-partition × member | `collect_table_metrics` (default **OFF**) + `table_metrics_limit` (~300) + `ORDER BY ROWS_READ DESC FETCH FIRST n` + system-schema exclude |
| `MON_GET_INDEX` | per index × partition × member (no `INDNAME` — must join `SYSCAT.INDEXES`) | `collect_index_metrics` (default **OFF**) + `index_metrics_limit` (~1000) + top-N + schema filter |
| `MON_GET_CONNECTION` | per connection (unbounded on busy servers) | aggregate or cap; per-connection series can explode |
| `MON_GET_CONTAINER` / tablespace | per container/tablespace × member | usually bounded, but cap defensively |
| `MON_GET_SERVICE_SUBCLASS` + `MON_GET_WORKLOAD` | **double-count** the same activity on two axes | collect both only if both dimensions wanted; WORKLOAD alone is usually the intuitive one |
| Per-member (`-2`) fan-out | multiplies **every** per-object series by member count on DPF/pureScale | member is a tag dimension — be aware it multiplies cardinality |

System schemas to exclude by default: `SYSCAT, SYSIBM, SYSSTAT, SYSPUBLIC, SYSTOOLS, NULLID,
SYSIBMADM, SYSIBMINTERNAL, SYSIBMTS`. Lifetime counters → `monotonic_count`; structural sizes →
`gauge`; `*_TIME` → `monotonic_count` (ms). **Decide the default-ON vs default-OFF posture per
collector. Open question OQ-6.**

---

## 8. Integration-packaging questions

Most relevant: [`00-README.md`](00-README.md) "Key risks", `99-review-and-gaps.md`,
[`_research/code-dbm-payload-contract.md`](_research/code-dbm-payload-contract.md),
[`_research/code-base-framework.md`](_research/code-base-framework.md).

1. **The `"db2"` vs `"ibm_db2"` split (product-visible, must be pinned).** There are **two distinct
   strings that must NOT be conflated**:
   - **Metric prefix + integration identity = `ibm_db2.`** (all 49 existing metrics, `metadata.csv`
     `integration=ibm_db2`, manifest `prefix:"ibm_db2."`). New metrics keep this prefix.
   - **DBM source / dbms string = `"db2"`** — `ddsource:"db2"`, `dbms:"db2"`, and the vendor row-key.
     The payload contract and both DBM plan docs say `"db2"`; the backend keys DBM routing off this
     string. **`code-testing-harness.md` still says `"ibm_db2"` — a direct contradiction.**
     **Resolution: `"db2"`** for all DBM payloads (purge `ibm_db2` from the testing doc). Crucially,
     `DatabaseCheck.dbms` defaults to the lowercased class name (`"ibmdb2check"`), so it **must be
     explicitly set to `"db2"`** in code regardless. Pin this in one place. **Open question OQ-5.**
2. **Obfuscator dialect support for Db2 (P1 blocker, not answerable from this repo).** Does the Agent
   Go obfuscator (`pkg/obfuscate`) accept `obfuscate_options['dbms']='db2'`, or must Db2 fall back to
   the generic SQL dialect? The dialect drives `query_signature` quality. **Must be verified against
   the Agent source/binary, not this repo.** If `'db2'` is unsupported, generic SQL is the fallback
   (acceptable but lower fidelity). **Open question OQ-5 (same spike).**
3. **`ddtags` shape differs by track:** comma-joined **string** on the samples/plan track; a **list**
   on the activity track. Match per payload type exactly (payload-contract §4.1/§5).

---

## 9. OPEN QUESTIONS — decisions a human must make (numbered)

These require a decision or a live spike **before/while implementing**. Ordered roughly by how much
they block.

1. **OQ-1 — Platform-target guard.** Is "assume LUW, error on z/OS" acceptable, or do we add an
   explicit LUW-positive probe and a clear "unsupported platform" service-check message? Decide how
   Db2-on-Cloud (restricted privileges) and Db2 Warehouse (columnar emphasis) are handled or refused.
   (§1.1)
2. **OQ-2 — Minimum supported Db2 version.** Pin the floor (11.5? 11.1? 12.1-only?). Only 12.1.4 is
   live-proven; 11.5 column/behavior differences are inferred. Decide whether to test against an 11.5
   instance before claiming support. (§1.2)
3. **OQ-3 — Cluster/HADR validation.** CF/GBP/FCM and HADR metrics are entirely unverified (test
   server is standalone Community). Do we (a) ship them empty-tolerant and unvalidated, (b) stand up a
   pureScale/HADR test bed, or (c) defer cluster telemetry to a later phase? (§1.4)
4. **OQ-4 — Least-privilege monitoring user.** Confirm the full grant set for a non-owner `datadog`
   user (vs the `DB2INST1` instance owner used in all research). Recommend `SYSMON` vs an explicit
   `EXECUTE` list, and verify each `MON_GET_*`/config/env routine is callable under it. (§2.1)
5. **OQ-5 — Pin `ddsource`/`dbms`=`"db2"` AND verify obfuscator dialect.** One-place pin of the DBM
   string to `"db2"` (set `DatabaseCheck.dbms` explicitly; purge `ibm_db2` from the testing doc), and a
   spike against the Agent `pkg/obfuscate` to confirm a `'db2'` dialect exists (else generic). (§8.1, §8.2)
6. **OQ-6 — Default-ON vs default-OFF posture for per-object metrics**, and the limit/filter defaults
   (`table_metrics_limit`, `index_metrics_limit`, schema include/exclude). Drives cardinality cost.
   (§7)
7. **OQ-7 — `EXPLAIN_FROM_SECTION` (Path B) spike (gates the whole plan feature).** Run it as a
   non-owner against a live `EXECUTABLE_ID`; confirm procedure signature, source arg (`'M'`), OUT
   params, and grants. If Path B fails/unprivileged, accept Path A + the parameter-marker problem, or
   defer plans. (§5.1)
8. **OQ-8 — `ibm_db` low-level API vs `ibm_db_dbi` (DB-API 2.0).** Decide whether new collectors reuse
   `exec_immediate`/`fetch_assoc` or adopt `ibm_db_dbi` cursors — likely forced by `callproc` with OUT
   params for `EXPLAIN_FROM_SECTION` and by clean parameter binding. Establish/confirm per-job
   connection isolation (assume the handle is not thread-safe). (§6.1, §6.3)
9. **OQ-9 — The missing architecture doc (`09-implementation-architecture.md`).** It is referenced by
   05/06/07 for `DBMAsyncJob` wiring, per-job `ibm_db` connection isolation, `run_job_loop`/`cancel`,
   module layout, and config-model surface — but **does not exist in the plan directory yet**. It must
   be written (or its content folded elsewhere) before implementation, since the threading/connection
   contract (§6) lives there.
10. **OQ-10 — Plan-JSON shape acceptance.** Round-trip the synthesized Db2 plan document through a real
    agent's `obfuscate_sql_exec_plan` + the DBM UI renderer to confirm the synthesized key names render
    correctly for a non-Postgres source. (§5.5)
11. **OQ-11 — Statement-text truncation policy.** Pin the `STMT_TEXT` fetch cap (e.g. 4–16 KB) and the
    truncation-flag semantics (`LENGTH(STMT_TEXT)` vs cap), shared by metrics (§3.5) and samples (§4.5).
12. **OQ-12 — Settings security posture.** Decide the default `ignored_settings_patterns` for the
    `db2_settings` payload — `sysadm_group`/`sysmon_group`/`keystore_*`/`ssl_*` etc. leak topology
    (not secrets; Db2 cfg stores no plaintext passwords), so pattern-based exclusion is a conservative
    default to agree on. ([`_research/db2-config-settings.md`](_research/db2-config-settings.md) §9)

---

## 10. Cross-reference index (where each risk is actionable)

| Risk area | Primary plan doc | Primary research doc(s) |
|---|---|---|
| Version/edition/topology gating (§1) | [`03-reference-architecture.md`](03-reference-architecture.md) | [`_research/db2-editions-versions.md`](_research/db2-editions-versions.md), [`_research/db2-config-settings.md`](_research/db2-config-settings.md) |
| Privilege + overhead (§2) | [`03-reference-architecture.md`](03-reference-architecture.md) | [`_research/db2-config-settings.md`](_research/db2-config-settings.md) §5, `_raw/04-monitor-config.txt` |
| Query metrics (§3) | [`05-dbm-query-metrics.md`](05-dbm-query-metrics.md) | [`_research/db2-live-pkgcache.md`](_research/db2-live-pkgcache.md) |
| Samples/activity (§4) | [`06-dbm-query-samples-activity.md`](06-dbm-query-samples-activity.md) | [`_research/db2-live-activity.md`](_research/db2-live-activity.md) |
| Execution plans (§5) | [`07-dbm-execution-plans.md`](07-dbm-execution-plans.md) | `_raw/05-explain-test.txt`, [`_research/db2-live-pkgcache.md`](_research/db2-live-pkgcache.md) §3-5 |
| Driver/threading (§6) | `09-implementation-architecture.md` (**TBD, OQ-9**) | [`_research/code-ibm_db2-current.md`](_research/code-ibm_db2-current.md) §2 |
| Cardinality (§7) | [`04-metrics-fidelity-plan.md`](04-metrics-fidelity-plan.md) | [`_research/map-tables-indexes.md`](_research/map-tables-indexes.md), [`_research/db2-monget-catalog-2.md`](_research/db2-monget-catalog-2.md) |
| Packaging / strings / obfuscator (§8) | [`00-README.md`](00-README.md), `99-review-and-gaps.md` | [`_research/code-dbm-payload-contract.md`](_research/code-dbm-payload-contract.md), [`_research/code-base-framework.md`](_research/code-base-framework.md) |
| Testing of all the above | [`11-testing-and-validation.md`](11-testing-and-validation.md) | [`_research/code-testing-harness.md`](_research/code-testing-harness.md) |
