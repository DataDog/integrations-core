# 10 — Implementation Phases

> **Audience.** An engineer (and an implementing AI agent) who knows the Datadog Postgres / MySQL /
> SQL Server integrations well but knows **little about Db2**. This document sequences the work in
> [`04-metrics-fidelity-plan.md`](04-metrics-fidelity-plan.md) through
> [`09-implementation-architecture.md`](09-implementation-architecture.md) into an ordered,
> dependency-aware execution plan. Every phase states **scope, dependencies, concrete tasks,
> acceptance criteria, and a rough effort estimate**. Read the sibling docs first; this is the
> "what to do, in what order" handoff, not the "what each thing is" reference.
>
> **Where this fits.** [`00-README.md`](00-README.md) is the index;
> [`02-current-integration-audit.md`](02-current-integration-audit.md) is the baseline;
> [`03-reference-architecture.md`](03-reference-architecture.md) and
> [`09-implementation-architecture.md`](09-implementation-architecture.md) describe the target shape;
> [`11-testing-and-validation.md`](11-testing-and-validation.md) is the testing companion (each phase
> cross-references it); [`12-risks-open-questions.md`](12-risks-open-questions.md) tracks the
> unknowns that gate several phases.

---

## 0. Orientation: what we are building and why this order

The current `ibm_db2` integration is a **metrics-only** `AgentCheck`: one persistent `ibm_db`
connection, five synchronous `MON_GET_*` queries, 49 metrics, no DBM features at all (full audit in
[`02-current-integration-audit.md`](02-current-integration-audit.md); raw findings in
`_research/code-ibm_db2-current.md`). The target is a **DBM-grade** integration matching the
Postgres/MySQL/SQL Server bar: query metrics, query samples + activity, execution plans, schemas +
settings — each on its own `DBMAsyncJob` background schedule, plus a much wider metric surface.

**Db2 concepts you need up front** (so the phase scopes make sense):

- **`MON_GET_*` table functions** are Db2's in-memory monitoring interface — the analog of Postgres
  `pg_stat_*` views. You call them like `SELECT ... FROM TABLE(MON_GET_DATABASE(-1))`. The trailing
  `-1`/`NULL` argument is the **member** arg; `-1`/`NULL` aggregates across all members (Db2's term
  for nodes in a multi-node DPF/pureScale cluster). All five existing queries pass `-1`
  (`queries.py:79` etc.).
- **`MON_GET_PKG_CACHE_STMT`** is the **package cache** statement-metrics function — Db2's
  `pg_stat_statements`. 327 columns on 12.1.4; cumulative-since-activation counters keyed by a stable
  `EXECUTABLE_ID` (`_research/db2-live-pkgcache.md` §1, §6).
- **`MON_CURRENT_SQL` / `MON_GET_ACTIVITY`** are the live "what's running right now" sources — Db2's
  `pg_stat_activity` / `sys.dm_exec_requests` (`_research/db2-live-activity.md` §2).
- **`SYSIBMADM.DBCFG` / `DBMCFG`** are the database and instance config views — Db2's `pg_settings`
  (`_research/db2-config-settings.md` §1-2).
- **`SYSCAT.*`** are the catalog views (tables/columns/indexes) — for schema collection.
- **Db2 does NOT normalize SQL** in the package cache: literals and `?` markers are stored verbatim,
  one cache entry per literal variant (`_research/db2-live-pkgcache.md` §5). The agent must obfuscate
  client-side, exactly as for the other engines.

**Sequencing principle.** Value lands early, risk is isolated:

| Phase | Theme | Value | Risk |
|---|---|---|---|
| **P0** | Metrics-foundation expansion (no DBM scaffold) | High, immediate | Low — same code shape as today |
| **P1** | DBM scaffold + query metrics | High — the headline DBM feature | Medium — new `DBMAsyncJob`/connection layer |
| **P2** | Samples + activity | High | Medium |
| **P3** | Execution plans | Medium | **High — isolated on purpose** (see §P3) |
| **P4** | Schemas + settings | Medium | Low-Medium |
| **P5** | Dashboards, docs, packaging, CI hardening | Polish/GA | Low |

P0 ships pure metrics with the *existing* hand-rolled pattern, so it needs none of the DBM
machinery and de-risks the rest (it forces the 12.1 container into CI and proves the new columns
exist). P1 builds the `DatabaseCheck` + `DBMAsyncJob` + per-job connection scaffold once; P2–P4 reuse
it. **P3 (plans) is deliberately last among the data features** because it is the only one with no
clean Db2 source (no inline JSON plan column — plans must be assembled from EXPLAIN tables;
`_research/code-base-framework.md` §F.4, `_research/code-dbm-payload-contract.md` §4). Isolating it
means P1/P2/P4 can ship and provide value even if P3 slips or proves infeasible.

**Global dependency:** the **obfuscator dialect** question (does the Agent Go obfuscator support a
`'db2'` `dbms` hint, or do we fall back to generic SQL?) blocks P1/P2/P3 signature computation. It is
the #1 open question — resolve it in P1's first task and track in
[`12-risks-open-questions.md`](12-risks-open-questions.md).

---

## P0 — Metrics-foundation expansion

**Goal:** dramatically widen the plain-metric surface using the *existing* synchronous-query pattern,
and stand up Db2 **12.1** in CI. No DBM scaffolding. This is the safest, highest-ratio value: it ships
the new metric categories the mapping docs identified (writes, I/O timing, sort/hash, HADR) without
touching the architecture.

### Scope

Add new `MON_GET_*`-backed metrics in these categories (all detailed in the `_research/map-*.md`
files and [`04-metrics-fidelity-plan.md`](04-metrics-fidelity-plan.md)):

1. **Buffer-pool writes / prefetch / I/O timing** — `_research/map-bufferpool.md` §3-4, §10.
2. **Disk I/O** — direct reads/writes, pool read/write time, log-disk waits, per-tablespace I/O,
   container filesystem space — `_research/map-io-disk.md` §1, §3.
3. **Sorting & hashing** — the entire `ibm_db2.sort.*` / `ibm_db2.hash.*` namespace (currently
   **zero** such metrics) — `_research/map-sorting-hashing.md` §3.
4. **HADR / replication** (new `query_hadr` collector) — `ibm_db2.hadr.*` — `_research/map-hadr-replication.md` §4, §7.

### Dependencies

- None on other phases. **Hard external dependency:** a Db2 **12.1.4** test container in CI (today
  CI only runs `taskana/db2:11.1`; `_research/code-ibm_db2-current.md` §12,
  `_research/code-testing-harness.md` §6.1). Switch/add `icr.io/db2_community/db2:12.1.4.0` and a
  `12.1` hatch matrix entry **first** — every new column must be validated against 12.1, and several
  (`POOL_COL_WRITES`, `POOL_ASYNC_*_WRITES`, `POOL_NO_VICTIM_BUFFER`, `MON_GET_CONTAINER.FS_*`) are
  flagged `[DOC]` (doc-sourced, not yet live-verified) in the maps.

### Concrete tasks

1. **CI: add Db2 12.1.** In `ibm_db2/hatch.toml` add `version = ["11.1", "12.1"]` to
   `[[envs.default.matrix]]`; map `12.1`→image tag `12.1.4.0` via an `[envs.default.overrides]
   matrix.version.env-vars` block; point `tests/docker/docker-compose.yaml` at
   `icr.io/db2_community/db2:${DB2_VERSION}` with `privileged: true`, `ipc: host`, `LICENSE=accept`,
   `DB2INSTANCE=db2inst1`, `DB2INST1_PASSWORD=...`, `DBNAME=...`, and a long healthcheck
   `start_period` (the IBM image first-boot takes minutes — mirror
   `local-dev/db2/docker-compose.yaml`). See [`11-testing-and-validation.md`](11-testing-and-validation.md)
   and `_research/code-testing-harness.md` §2.1, §6, §8.
2. **Validate columns live.** Before writing each SELECT, run
   `DESCRIBE SELECT * FROM TABLE(MON_GET_BUFFERPOOL(NULL,-1))` (and the database/tablespace/container/log
   variants) against the 12.1.4 container and confirm every `[DOC]`-flagged column exists. Drop or
   version-gate any that do not. (`_research/map-io-disk.md` §4 closing note.)
3. **Extend `queries.py` column tuples.** Add the new columns to `BUFFER_POOL_TABLE_COLUMNS`
   (writes, `pool_read_time`/`pool_write_time`, async reads/writes, `unread_prefetch_pages`,
   `prefetch_wait*`, `pool_no_victim_buffer`, vectored/block I/O, `files_closed`, `bp_cur_buffsz`),
   pull the disk-I/O columns from `MON_GET_DATABASE(-1)` (`direct_*`, `log_disk_wait*`,
   `num_log_buffer_full`), pull sort/hash columns from `MON_GET_DATABASE(-1)`, and add per-tablespace
   I/O + a new `MON_GET_CONTAINER(NULL,-1)` query for filesystem space. Exact SELECT lists:
   `_research/map-bufferpool.md` §9, `_research/map-sorting-hashing.md` §2.1, `_research/map-hadr-replication.md` §7.2.
4. **Emit the metrics** in the existing `query_*` methods (`ibm_db2.py`), following the established
   conventions: cumulative `MON_GET` counters → `self.monotonic_count(...)` (catalogued `count` in
   `metadata.csv`); point-in-time / HWM / ratios → `self.gauge(...)`; reuse the four-class
   buffer-pool aggregate roll-up pattern at `ibm_db2.py:348-377` for `bufferpool.writes`. Keep the
   `if <gbp>_reads_logical:` guard for pureScale-only GBP/`invalid_pages` metrics
   (`_research/map-bufferpool.md` §6, §11). **Do not change** how existing `reads.*` fold regular+temp
   reads — add temp splits only as *new* series (backward-compat; `_research/map-bufferpool.md` §1, §11.2).
5. **Add `query_hadr`** as a new method in `self._query_methods` with 0-row handling: on a non-HADR DB
   (`HADR database role = STANDARD`) `MON_GET_HADR(-1)` returns **0 rows** — treat as "not configured",
   emit nothing (or only `ibm_db2.hadr.role{role:standard}=1`), never error. Compute derived
   `replay_lag` from `(current_time - standby_replay_log_time)` using the existing `backup.latest`
   timestamp-delta pattern (`ibm_db2.py:176-181`). Add an `ibm_db2.hadr.status` service check.
   Full design: `_research/map-hadr-replication.md` §4, §7.
6. **Catalog every new metric** in `metadata.csv` (header
   `metric_name,metric_type,interval,unit_name,per_unit_name,description,orientation,integration,short_name,curated_metric`;
   `metric_type` ∈ `{count,gauge,rate}`; orientation ∈ `{0,1,-1}`; units from the allow-list —
   `get` for BP reads, `page`/`write` for writes, `millisecond` for times, `sector` for direct I/O,
   `byte` for FS). Ready-to-paste rows in `_research/map-bufferpool.md` §10. Note: `sort` is **not** a
   valid `unit_name` — verify each unit against `VALID_UNIT_NAMES` before use
   (`_research/code-integration-scaffolding.md` §2.2).
7. **Privileges.** Add `GRANT EXECUTE ON FUNCTION SYSPROC.MON_GET_HADR` (and `MON_GET_CONTAINER`) to
   the README least-privilege grant list, or recommend `SYSMON` which covers all `MON_GET_*`
   (`_research/map-hadr-replication.md` §7.4, `_research/db2-config-settings.md` §5).
8. **Tests.** Add every new metric name to `tests/metrics.py` (`assert_all_metrics_covered()` fails
   otherwise — `_research/code-testing-harness.md` §3.2) and adopt
   `aggregator.assert_metrics_using_metadata(...)` to catch type/metadata drift.

### Acceptance criteria

- CI runs against Db2 **12.1.4** (and ideally keeps 11.1 green via version-gated columns).
- New buffer-pool/IO/sort/hash metrics appear, correctly typed, tagged `db:<db>` (+ `bufferpool:`/
  `tablespace:`/`container:` where applicable), and are in `metadata.csv`.
- `query_hadr` emits nothing on the (default) STANDARD database and does not error;
  `assert_metrics_using_metadata` and `assert_all_metrics_covered` pass.
- No regression to the existing 49 metrics or the tablespace-state event.

### Effort

**~1–1.5 weeks.** Mechanical and well-specified by the maps; the long pole is the CI image swap and
live column re-validation, not the emission code.

---

## P1 — DBM scaffold + query metrics

**Goal:** convert the check to the DBM architecture **once**, then ship the first DBM feature:
per-statement query metrics from the package cache. This is the highest-value DBM phase and the
foundation P2–P4 build on.

### Scope

1. **Architecture conversion (one-time, shared):**
   - `IbmDb2Check(AgentCheck)` → `IbmDb2Check(DatabaseCheck)` with `__NAMESPACE__ = "ibm_db2"`;
     implement the identity properties (`reported_hostname`, `resolved_hostname`,
     `database_identifier`, `database_hostname`, `dbms` → `"db2"`, `dbms_version`, `tags` via a
     `TagManager`, `cloud_metadata`). (`_research/code-dbm-payload-contract.md` §2, §12;
     `_research/code-sqlserver-dbm-template.md` §3.1.)
   - A **per-job connection-isolation layer**: `ibm_db` has no thread-safe shared cursor, so each
     `DBMAsyncJob` opens its own `ibm_db.connect` (namespaced by a `key_prefix` like SQL Server's
     `"dbm-"`, `"dbm-activity-"`, …). Open DBM connections with `SET CURRENT ISOLATION = UR`
     (uncommitted read) so monitoring never takes locks. (`_research/code-sqlserver-dbm-template.md`
     §4.) `ibm_db.fetch_assoc` already returns lowercase-keyed dict rows (`ATTR_CASE=CASE_LOWER`,
     `ibm_db2.py:567`), so no `DictCursor` shim is needed.
   - The **`database_instance` registration event** (`kind: "database_instance"`, `metadata.dbm =
     config.dbm`) emitted every run, debounced by `database_instance_collection_interval`. **This is
     the single payload that registers the host as a DBM instance** — without it the host never
     appears in the DBM UI. (`_research/code-dbm-payload-contract.md` §6.1.)
   - **Config surface:** add a `dbm: false` master switch plus per-collector blocks
     (`query_metrics`, `query_activity`, `collect_settings`, `collect_schemas`, `obfuscator_options`,
     `collect_raw_query_statement`, `reported_hostname`, `exclude_hostname`, `database_identifier`,
     cloud blocks) to `assets/configuration/spec.yaml` (the source of truth), then **regenerate**
     `config_models/*` and `conf.yaml.example` via `ddev validate config --sync` (never hand-edit the
     generated files). (`_research/code-sqlserver-dbm-template.md` §2, §8.3;
     `_research/code-integration-scaffolding.md`.)
   - Wire `run_job_loop(tags)` for each job in `check()` behind `if config.dbm_enabled`, and a
     `cancel()` that tears down every job. (`_research/code-sqlserver-dbm-template.md` §3.3-3.4.)
2. **Query-metrics collector** `statements.py` — `Db2StatementMetrics(DBMAsyncJob)`:
   - Source: `TABLE(MON_GET_PKG_CACHE_STMT(NULL, NULL, NULL, -1))`.
   - **Introspect columns at runtime** (327 on 12.1.4, fewer on older fixpacks) via a
     `WHERE 1=0` / `FETCH FIRST 0 ROWS ONLY` probe; intersect with the desired set. Do not hard-code.
     (`_research/db2-live-pkgcache.md` §9.1.)
   - Pull identity + counters broadly; fetch `STMT_TEXT` (a CLOB up to 2 MB) bounded
     (e.g. first 4–16 KB) and set a truncation flag via `LENGTH(STMT_TEXT)` vs the cap — Db2 appends
     no `...` marker. For large caches use the two-step pattern (fetch `EXECUTABLE_ID` cheaply, then
     `STMT_TEXT` per top-N id). (`_research/db2-live-pkgcache.md` §7, §9.6.)
   - **Obfuscate + signature client-side:** strip the leading `/*dd...*/` APM comment, call
     `obfuscate_sql_with_metadata(text, obfuscator_options, replace_null_character=True)`, compute
     `compute_sql_signature(obfuscated)`. (`_research/code-base-framework.md` §D;
     `_research/db2-live-pkgcache.md` §1.5, §9.3.)
   - **Delta engine:** `StatementMetrics.compute_derivative_rows(rows, metric_cols, key=...,
     execution_indicators=['num_exec_with_metrics'])`. Snapshot/diff key = `HEX(EXECUTABLE_ID)` + `MEMBER` +
     db name; final merge/emit key = `query_signature` (re-aggregate churned `EXECUTABLE_ID`s and
     literal variants). Drop rows whose any diffed counter went negative (cache eviction / reactivation
     reset). (`_research/code-base-framework.md` §C; `_research/db2-live-pkgcache.md` §4, §9.2-9.3.)
   - **Unit normalization:** `TOTAL_CPU_TIME` is **microseconds**; `STMT_EXEC_TIME`/`TOTAL_ACT_TIME`/
     `PREP_TIME` are **milliseconds** — convert before mixing. Averages divide by
     `NUM_EXEC_WITH_METRICS` (not `NUM_EXECUTIONS`), guarding 0. (`_research/db2-live-pkgcache.md`
     §1.7-1.8.)
   - **Payload:** `dbm-metrics` track, wrapper keys `host`/`timestamp`(ms)/`min_collection_interval`/
     `tags`(dd.internal + db: stripped)/`cloud_metadata`/`ddagentversion`/`service`/`db2_version`,
     and a **`db2_rows`** array. Chunk to stay under `batch_max_content_size`. Emit **FQT** events
     (`dbm_type: "fqt"`) per new `(query_signature, db)`, rate-limited. (`_research/code-dbm-payload-contract.md`
     §3, §4.2, §12.2.) Gate timing-derived columns on `mon_act_metrics <> 'NONE'`
     (`_research/db2-live-pkgcache.md` §8).

### Dependencies

- **P0** is not strictly required but should land first (the 12.1 CI container is shared).
- **Obfuscator dialect** decision (P1 task 0) gates signatures — blocks P2/P3 too.

### Concrete tasks

0. **Resolve the obfuscator dialect.** Verify whether the Agent `pkg/obfuscate` Go obfuscator
   accepts `dbms: 'db2'`; if not, fall back to a generic SQL dialect. Document the decision in
   [`12-risks-open-questions.md`](12-risks-open-questions.md). (`_research/code-base-framework.md` §D.2;
   `_research/code-dbm-payload-contract.md` §10.)
1. Implement the `DatabaseCheck` conversion + identity props + `TagManager` (`_research/code-dbm-payload-contract.md` §2).
2. Implement the per-`key_prefix` `ibm_db` connection layer + `UR` isolation
   (`_research/code-sqlserver-dbm-template.md` §4.6).
3. Add the spec blocks; regenerate config models + example.
4. Implement `_send_database_instance_metadata` (`metadata.dbm` = config.dbm).
5. Implement `Db2StatementMetrics(DBMAsyncJob)` end-to-end per the scope above.
6. Add `db2_version` payload helper (`payload_db2_version`) sourced from `ENV_INST_INFO.SERVICE_LEVEL`
   (`DB2 v12.1.4.0`) or the existing driver parse (`utils.py:27-28`); cache it in a `static_info`
   TTLCache analog. (`_research/db2-config-settings.md` §6; `_research/code-sqlserver-dbm-template.md` §3.6.)
7. **Tests:** `test_statements.py` asserting on `get_event_platform_events("dbm-metrics")` — `db2_rows`
   present, `query_signature` matches `compute_sql_signature`, counters numeric, `host`/`ddagentversion`/
   `min_collection_interval`/`tags` correct; FQT events on `dbm-samples`. Use a `dbm_instance` fixture
   (`dbm:True`, `run_sync:True`, tiny interval) and reset `DBMAsyncJob.executor` between tests.
   (`_research/code-testing-harness.md` §4.1-4.2, §4.5-4.6.)
8. **Privileges/setup:** grant `EXECUTE ON FUNCTION SYSPROC.MON_GET_PKG_CACHE_STMT`; document. The
   `_DETAILS` variant was not callable as a non-owner in the live probe and is **not** required
   (`_research/db2-live-pkgcache.md` §9.7).

### Acceptance criteria

- With `dbm: true`, the host registers as a DBM instance (a `database_instance` event with
  `metadata.dbm == true` lands on `dbm-metadata`).
- `dbm-metrics` payloads contain `db2_rows` with correct deltas, obfuscated `query` text, and stable
  `query_signature`s that survive `EXECUTABLE_ID` churn; FQT events emitted and rate-limited.
- `mon_act_metrics = NONE` degrades gracefully (no timing-derived columns, no crash).
- All async jobs are cancelled on check teardown (no leaked threads in tests).

### Effort

**~2.5–3.5 weeks.** Most of the cost is the one-time scaffold (connection isolation, identity,
spec/config, registration event); the collector itself is well-templated by SQL Server/Postgres.

---

## P2 — Query samples + activity

**Goal:** "what is running right now" — active-session snapshots (ASH-style) and connection counts,
linked to query signatures.

### Scope

`activity.py` — `Db2Activity(DBMAsyncJob)`:

- **Primary source:** `SYSIBMADM.MON_CURRENT_SQL` (a view over `MON_GET_ACTIVITY(NULL,-2)` JOIN
  `MON_GET_CONNECTION(NULL,-2)`). It already computes a true wall-clock `ELAPSED_TIME_MSEC` (=
  `CURRENT TIMESTAMP - LOCAL_START_TIME`) that the raw functions do not expose. Where you need
  `EXECUTABLE_ID` (to link to package-cache metrics) or accumulated wait time, sample
  `MON_GET_ACTIVITY` directly and join `MON_GET_CONNECTION`. (`_research/db2-live-activity.md` §2, §3, §5.)
- **Exclude the agent's own session** (it always appears in its own snapshot — filter by
  `APPLICATION_HANDLE`/`APPLICATION_NAME`). (`_research/db2-live-activity.md` §4.)
- **Obfuscate + signature** each row's `STMT_TEXT` (same comment-strip + obfuscator as P1).
- **Enrich with transaction state** from `MON_GET_UNIT_OF_WORK` / `MON_CURRENT_UOW`
  (`WORKLOAD_OCCURRENCE_STATE`: `UOWEXEC`/`UOWWAIT`/`AUTONOMOUS_WORKLOAD`) for idle-in-transaction
  detection — these have **no** `STMT_TEXT`, so use them only to enrich, not as the statement source.
  (`_research/db2-live-activity.md` §9.)
- **Connection counts** from `MON_GET_CONNECTION` (grouped by user/status/app) →
  `db2_connections`.
- **Payload:** `dbm-activity` track, `dbm_type: "activity"`, top-level
  `host`/`database_instance`/`ddsource:"db2"`/`collection_interval`/`ddtags`(**list**, not
  comma-joined)/`timestamp`(ms)/`cloud_metadata`/`service`/`db2_version`, plus `db2_activity` (active
  sessions) and `db2_connections`. Default interval **10s** (sample loop can be faster, e.g. 1s).
  Cap by row count or `MAX_PAYLOAD_BYTES`. (`_research/code-dbm-payload-contract.md` §5;
  `_research/code-sqlserver-dbm-template.md` §5.2.)

### Dependencies

- **P1** (scaffold, connection layer, obfuscator, identity, signatures).

### Concrete tasks

1. Implement `Db2Activity(DBMAsyncJob)` with `MON_CURRENT_SQL` as primary, self-exclusion, obfuscation,
   UOW enrichment, connection counts, and the activity payload.
2. Map activity-row fields to the cross-DBMS schema (drop null keys, add `query_truncated`,
   obfuscated `statement`, `query_signature`, wait/blocking/identity columns).
   (`_research/code-dbm-payload-contract.md` §5.5.)
3. **Blocking/lock-wait** (optional within P2, can defer): surface blockers via
   `SYSIBMADM.MON_LOCKWAITS` to populate blocking-session linkage.
4. Gate activity timing fields on `mon_act_metrics <> 'NONE'` (`_research/db2-live-activity.md` §10).
5. **Tests:** `test_activity.py` — `get_event_platform_events("dbm-activity")`, `dbm_type=="activity"`,
   `ddsource=="db2"`, `db2_activity` rows with `query_signature`/obfuscated `sql_text`, `ddtags` is a
   list. Generate catchable in-flight activity with `CALL dbms_lock.sleep(N)` or a self-cartesian join
   (orders OLTP is sub-ms and is systematically missed by sampling — expected, document it).
   (`_research/db2-live-activity.md` §8, §13; `_research/code-testing-harness.md` §4.3.)

### Acceptance criteria

- `dbm-activity` payloads contain `db2_activity` + `db2_connections`; long-running statements appear
  with correct `ELAPSED_TIME_MSEC` and `query_signature`; the agent's own session is excluded.
- Sub-millisecond OLTP being absent from samples is documented as expected (cumulative metrics from
  P1 are the complete per-statement source).

### Effort

**~2–2.5 weeks.**

---

## P3 — Execution plans (ISOLATED, highest risk)

**Goal:** obfuscated execution-plan samples (`dbm_type: "plan"`), the deepest DBM feature.

> **Why this is isolated and last among data features.** Postgres gets a JSON plan from
> `EXPLAIN (FORMAT JSON)`; SQL Server reads a cached XML plan. **Db2 has neither** — there is no
> inline plan column on `MON_GET_PKG_CACHE_STMT`. Db2 plans live in **EXPLAIN tables**
> (`EXPLAIN_STATEMENT`, `EXPLAIN_OPERATOR`, `EXPLAIN_STREAM`, `EXPLAIN_OBJECT`) populated via
> `EXPLAIN PLAN FOR <sql>` / `CURRENT EXPLAIN MODE` / `db2exfmt`, and the plan **tree must be
> assembled from those tables and serialized to JSON** before `compute_exec_plan_signature`. This is
> the highest-complexity, highest-uncertainty work in the whole plan
> (`_research/code-base-framework.md` §F.4; `_research/code-dbm-payload-contract.md` §4, §12). Keeping
> it as a separate, late, independently-shippable phase means P1/P2/P4 deliver value regardless of how
> P3 lands. Full design and the open questions live in
> [`07-dbm-execution-plans.md`](07-dbm-execution-plans.md) and
> [`12-risks-open-questions.md`](12-risks-open-questions.md).

### Scope

- A **spike first** (see tasks) to settle the plan-acquisition mechanism before committing to a full
  collector. Candidate mechanisms, in rough order of preference:
  1. `EXPLAIN PLAN FOR <obfuscated-or-reconstructed sql>` into per-session EXPLAIN tables, then
     assemble the operator tree from the EXPLAIN tables → JSON. Requires EXPLAIN tables to exist
     (`SYSPROC.SYSINSTALLOBJECTS('EXPLAIN', ...)`), write access to them, and a strategy for
     parameter markers (`?`) — Db2's analog of Postgres's `explain_parameterized_queries` generic-plan
     workaround (`_research/code-postgres-dbm-samples.md` §1.1).
  2. `db2exfmt`/`db2expln` text output (harder to normalize; lower fidelity).
- Plan event on `dbm-samples`, `dbm_type: "plan"`, `db.plan.definition` (obfuscated JSON),
  `db.plan.signature` = `compute_exec_plan_signature(normalized_plan)`, `collection_errors`,
  `query_signature`, obfuscated `statement`. Rate-limit per `(query_signature, plan_signature)`.
  (`_research/code-dbm-payload-contract.md` §4.1.) Optional `rqp` (raw plan) when
  `collect_raw_query_statement.enabled`.

### Dependencies

- **P1** (signatures, obfuscation, scaffold) and **P2** (the sampling loop that drives plan capture
  for active statements — Postgres/SQL Server emit plans from the samples job). Folding the plan
  collector into the P2 `activity.py` job is the natural structure.

### Concrete tasks

1. **Spike (timeboxed, ~1 week):** on the 12.1.4 container, prove end-to-end that an obfuscated
   statement from the package cache can be EXPLAINed and its tree assembled into JSON. Decide: EXPLAIN
   tables vs `db2exfmt`; how to handle `?` markers; least-privilege grants; per-session EXPLAIN-table
   isolation. **Gate the rest of P3 on the spike result** — if infeasible at acceptable cost,
   document and defer (P1/P2/P4 still ship).
2. Implement plan assembly: query the EXPLAIN tables, build the operator tree, serialize to JSON,
   normalize, sign.
3. Implement the plan event + per-`(query_signature, plan_signature)` rate limiting + `collection_errors`.
4. Parameter-marker handling (generic-plan equivalent).
5. **Tests:** plan events on `dbm-samples` with non-null `db.plan.definition` parseable as JSON, a
   `db.plan.signature`, and the error path emitting `dd.ibm_db2.*` telemetry.
   (`_research/code-testing-harness.md` §4.2.)

### Acceptance criteria

- Plan samples emitted for sampled statements with valid obfuscated JSON plans and stable plan
  signatures; rate-limited; graceful `collection_errors` when a plan can't be obtained.
- **OR** a documented decision (with evidence from the spike) to defer, in
  [`12-risks-open-questions.md`](12-risks-open-questions.md).

### Effort

**~3–5 weeks (high variance).** The spike outcome dominates; this is the phase most likely to slip,
which is exactly why it is isolated.

---

## P4 — Schemas + settings

**Goal:** database settings (config) and schema/table/index metadata in the DBM `dbm-metadata` track.

### Scope

1. **Settings** — `metadata.py` `Db2Metadata(DBMAsyncJob)`:
   - Emit `kind: "db2_settings"` whose `metadata` array is the **union of `SYSIBMADM.DBMCFG` (instance)
     + `SYSIBMADM.DBCFG` (database, `WHERE member=0`)**, each row tagged `config_scope: "dbm"|"db"`
     plus a derived `pending_change = value != deferred_value` (Db2's analog of Postgres
     `pending_restart`). Single UNION query in `_research/db2-config-settings.md` §8.2.
   - Be **schema-agnostic over rows** (do not hard-code a parameter list; 113 DBMCFG + 194 DBCFG rows
     on 12.1.4, and the set grows per fixpack). (`_research/db2-config-settings.md` §7.)
   - Optional `kind: "db2_registry_variables"` from `SYSIBMADM.REG_VARIABLES` (note: startup-time
     snapshot, document the skew vs `db2set -all`). (`_research/db2-config-settings.md` §3.4, §8.3.)
   - Support an `ignored_settings_patterns` list (SQL `LIKE`/`NOT LIKE`); offer pattern-based
     redaction for topology-leaking params (`%keystore%`, `%group%`). No plaintext secrets exist in
     these views. Default interval **600s**. (`_research/db2-config-settings.md` §9.)
2. **Schemas** — `schemas.py` `Db2SchemaCollector(SchemaCollector)`:
   - Subclass the shared `SchemaCollector` and override only `kind` (→ `"db2_databases"`),
     `_get_databases`, `_get_cursor`, `_get_next`, `_map_row`. The base handles chunking
     (`payload_chunk_size`, default 10k) and the envelope. (`_research/code-base-framework.md` §G;
     `_research/code-dbm-payload-contract.md` §6.3.)
   - Sources: `SYSCAT.SCHEMATA`, `SYSCAT.TABLES`, `SYSCAT.COLUMNS`, `SYSCAT.INDEXES` +
     `SYSCAT.INDEXCOLUSE`, `SYSCAT.REFERENCES` + `SYSCAT.KEYCOLUSE`. Default interval **3600s**.
   - Invoked by the metadata `DBMAsyncJob` on its own interval (not itself a job), gated by
     `collect_schemas.enabled`. (`_research/code-sqlserver-dbm-template.md` §5.3-5.4.)

### Dependencies

- **P1** (scaffold, identity, `dbm-metadata` submitter, version helper).

### Concrete tasks

1. Implement `Db2Metadata(DBMAsyncJob)` settings event (DBMCFG ∪ DBCFG, `pending_change`,
   `ignored_settings_patterns`).
2. Implement `Db2SchemaCollector(SchemaCollector)` over `SYSCAT.*` with the four overrides + `kind`.
3. Add `collect_settings` / `collect_schemas` config blocks to the spec; regenerate models/example.
4. Fold version/edition/host facts into `dbms_version` (and optionally a `db2_env_info` kind) from
   `ENV_INST_INFO`/`ENV_PROD_INFO`/`ENV_SYS_INFO`. (`_research/db2-config-settings.md` §4, §6.)
5. **Privileges:** extend the grant list to the config/env routines (`DBM_GET_CFG`, `DB_GET_CFG`,
   `REG_LIST_VARIABLES`, `ENV_GET_*`) or recommend `SYSMON`. (`_research/db2-config-settings.md` §5.)
6. **Tests:** `test_metadata.py` / `test_schemas.py` via `get_event_platform_events("dbm-metadata")`
   asserting the `db2_settings` rows (incl. `config_scope`, `pending_change`) and the `db2_databases`
   schema chunks (`collection_payloads_count` on the last). (`_research/code-testing-harness.md` §4.4.)

### Acceptance criteria

- `dbm-metadata` carries a `db2_settings` event (DBMCFG ∪ DBCFG, correctly scoped/flagged) and, when
  enabled, chunked `db2_databases` schema payloads with the completion count.
- Settings collection is schema-agnostic (no hard-coded parameter list); pending changes surfaced.

### Effort

**~2–2.5 weeks** (settings ~0.5 week; schemas ~1.5 weeks reusing the base collector).

---

## P5 — Dashboards, docs, packaging, CI hardening (GA polish)

**Goal:** make the expanded integration usable and shippable.

### Scope

1. **Dashboard(s):** extend `assets/dashboards/overview.json` with the new metric categories
   (writes, I/O timing, sort/hash, HADR) and add DBM-oriented views; consider a dedicated HADR
   dashboard. (Current dashboard inventory: `_research/code-ibm_db2-current.md` §11.)
2. **Service checks / manifest:** register `ibm_db2.hadr.status` in `assets/service_checks.json`;
   optionally move `manifest.json` `owner` to `database-monitoring` and add DBM classifier tags
   (note: there is **no** `"dbm": true` manifest flag — DBM is driven by the runtime
   `database_instance` event; `_research/code-dbm-payload-contract.md` §11).
3. **Docs:** README setup updates — least-privilege grants (consolidate on `SYSMON`), `dbm: true`
   enablement, per-collector config blocks, and the `ibm_db` driver/packaging story (the driver is a
   compiled C extension not bundled with the Agent; air-gapped install is multi-step —
   `_research/code-ibm_db2-current.md` §14). Refresh the 11.1 KnowledgeCenter doc links to 12.1.
4. **CI hardening:** add `base-package-features = ["deps","db","json"]` to `hatch.toml` (required once
   DBM framework is used), the `--skip-env` fast-dev path, `dbm_instance` fixtures, and thread hygiene
   across the test suite. (`_research/code-testing-harness.md` §6, §8.)
5. **Driver packaging follow-up:** evaluate bundling/`E2E_METADATA` automation for `ibm_db` so DBM
   installs are not manual (tracked as a risk in [`12-risks-open-questions.md`](12-risks-open-questions.md)).

### Dependencies

- Everything it documents/visualizes — so it runs **last**, but the dashboard/doc work for each
  category can be drafted incrementally as P0–P4 land.

### Concrete tasks

1. Dashboard widgets for P0 metric categories + DBM enablement notes.
2. `service_checks.json` + manifest classifier updates.
3. README rewrite (privileges, `dbm` enablement, config reference, driver install, 12.1 links).
4. `hatch.toml` `base-package-features`; `--skip-env`; ensure `assert_metrics_using_metadata` runs in CI.
5. CHANGELOG entries (towncrier `changelog.d/`) for every shipped phase.

### Acceptance criteria

- Dashboards render the new metrics; README documents enablement + least-privilege grants + driver
  install; CI is green on 12.1 with DBM tests; manifest/service-checks updated.

### Effort

**~1.5–2 weeks** (parallelizable with earlier phases for the per-category drafting).

---

## Cross-phase dependency graph (quick reference)

```
                 ┌──────────────────────────────────────────────┐
   P0 metrics ───┤ shares the 12.1 CI container with everything  │
   (independent) └──────────────────────────────────────────────┘
                                   │
                                   ▼
   P1 DBM scaffold + query metrics  ── (resolves obfuscator dialect; builds connection layer,
        │                               identity, registration event — reused by all below)
        ├──────────────► P2 samples + activity
        │                      │
        │                      ▼
        │                P3 execution plans  ◄── ISOLATED / last / spike-gated (high risk)
        │
        └──────────────► P4 schemas + settings   (independent of P2/P3)

   P5 dashboards/docs/packaging  ◄── consumes all; drafted incrementally, finalized last
```

**Value-vs-risk landing order:** P0 (low risk, high value) → P1 (the DBM unlock) → P2 → P4 (both
moderate, independent) → P3 (isolated, may slip) → P5 (polish). P4 can run in parallel with P2/P3
since it only depends on the P1 scaffold.

## Rough total

| Phase | Estimate |
|---|---|
| P0 | 1–1.5 wk |
| P1 | 2.5–3.5 wk |
| P2 | 2–2.5 wk |
| P3 | 3–5 wk (high variance) |
| P4 | 2–2.5 wk |
| P5 | 1.5–2 wk |
| **Total** | **~12–17 weeks** (one engineer; P4 ∥ P2/P3 and P5 drafting overlap can compress this) |

See [`11-testing-and-validation.md`](11-testing-and-validation.md) for the per-phase test strategy and
[`12-risks-open-questions.md`](12-risks-open-questions.md) for the blockers (obfuscator dialect, plan
acquisition, `ibm_db` packaging) that gate P1/P3.
