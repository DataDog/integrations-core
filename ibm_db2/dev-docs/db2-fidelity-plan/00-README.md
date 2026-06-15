# 00 — Db2 Fidelity Plan: Index & Executive Summary

**What this is.** The navigational entry point and executive summary for the **now-complete** plan to
bring the Datadog `ibm_db2` integration up to postgres/mysql-class **metric breadth** and **full
Database Monitoring (DBM)**. The full doc set — `01`–`12` plus the `99` completeness review — exists
and is implementation-ready in substance (per [`99`](99-review-and-gaps.md)). This README is a map,
not a re-explanation: read it to orient, then go to the numbered doc for the work in front of you.

**Audience.** An engineer (or implementing AI agent) who knows the Datadog `postgres` / `mysql` /
`sqlserver` integrations well — `pg_stat_statements`, `DBMAsyncJob`, the `dbm-*` event-platform
tracks, obfuscation/signatures — but knows little about IBM Db2. Every Db2 concept is explained inline
in the docs below; start with [`01`](01-db2-monitoring-primer.md) if Db2 is unfamiliar.

---

## 1. Goal

Bring `ibm_db2` from its shipped baseline of **49 standard metrics and zero DBM** up to
**postgres(244)/mysql(254)-class metric fidelity** — a target of **~320 metrics** (the doc `04`
T0+T1 baseline, which exceeds pg/mysql in count and matches them on coverage of buffer-pool
writes/IO-timing, direct I/O, container FS, sort/hash, locks, log latency, per-table/index, WLM,
memory pools, and HADR) — **plus** the complete DBM feature set delivered on the five event-platform
tracks: **query metrics** (`MON_GET_PKG_CACHE_STMT` → `dbm-metrics`), **query samples + activity**
(`MON_CURRENT_SQL` / `MON_GET_ACTIVITY` → `dbm-samples` + `dbm-activity`), **execution plans** (EXPLAIN
tables → JSON → `dbm-samples`), and **schemas + settings** (`SYSCAT.*` + `DBMCFG`∪`DBCFG` →
`dbm-metadata`), with the `database_instance` registration event that makes the host appear in the DBM
UI. The decisive gap closed here is not metric count — it is the **total absence of DBM** today.

## 2. Current → Target snapshot

| Dimension | Today (`ibm_db2` 4.3.0) | Target |
|---|---|---|
| Check base class | `AgentCheck` (synchronous, one persistent `ibm_db` connection) | `DatabaseCheck` + per-job `DBMAsyncJob` connection layer (`dbms="db2"`, `__NAMESPACE__="ibm_db2"`) |
| Standard metrics | **49** (~20% of pg's 244 / mysql's 254) | **~320** (T0+T1): writes/prefetch/IO-timing, direct I/O, container FS, sort/hash, locks, log latency, per-table/index/WLM/memory, HADR |
| Query metrics (`pg_stat_statements` analog) | **none** | `MON_GET_PKG_CACHE_STMT` → `dbm-metrics` (`db2_rows`), client-side obfuscation + `query_signature` |
| Query samples / activity (`pg_stat_activity` analog) | **none** | `MON_CURRENT_SQL` / `MON_GET_ACTIVITY` → `dbm-activity` + `dbm-samples` |
| Execution plans | **none** | EXPLAIN-tables → JSON → `dbm-samples` (`dbm_type:"plan"`) — highest-risk, isolated, spike-gated |
| Settings / schemas | **none** | `DBMCFG`∪`DBCFG` + `SYSCAT.*` → `dbm-metadata` |
| DBM instance registration | **none** (host never appears in DBM UI) | `database_instance` event, `metadata.dbm=true` — the single must-have payload |
| CI Db2 version | **11.1 only** (`taskana/db2`) | add **12.1.4** (`icr.io/db2_community/db2`); live ground-truth container is 12.1.4 |

A grep over `datadog_checks/ibm_db2/` for
`mon_get_pkg_cache_stmt|mon_current_sql|dbm|obfuscate|query_signature|DBMAsyncJob` returns nothing
today — Half 2 (the DBM half) is entirely net-new.

---

## 3. Doc index

Grouped by theme. Read top-to-bottom within a group.

### Foundations — *understand Db2 and the current check before building*

- **[`01-db2-monitoring-primer.md`](01-db2-monitoring-primer.md)** — The conceptual on-ramp. Db2 LUW
  architecture (instance≠database, members, storage stack, agents/EDUs, memory pools, WLM, catalogs)
  and its four monitoring interfaces (`MON_GET_*` table functions, `SYSIBMADM.*` views, event
  monitors, EXPLAIN) — each by analogy to pg/mysql. Read first if Db2 is unfamiliar.
- **[`02-current-integration-audit.md`](02-current-integration-audit.md)** — The "before" picture and
  punch list: a file-by-file inventory of the shipped 4.3.0 check, the exhaustive catalog of all **49
  metrics** with their `MON_GET_*` SQL, the category-by-category gap vs pg(244)/mysql(254), and the
  total absence of DBM. Read to know what exists and what's missing.
- **[`03-reference-architecture.md`](03-reference-architecture.md)** — The blueprint: how a
  pg/mysql/sqlserver-grade DBM integration is assembled from `datadog_checks_base` (the two-half
  split, `DatabaseCheck`, per-feature `DBMAsyncJob` collectors, the `dbm-*` payload contracts). SQL
  Server is the template (DBM bolted onto a metrics-only check — exactly Db2's situation).

### Metrics — *standard-metric breadth (Half 1)*

- **[`04-metrics-fidelity-plan.md`](04-metrics-fidelity-plan.md)** — The standard-metric expansion
  from 49 → ~320. Consumes the 14 `_research/map-*.md` tables into a tiered (T0/T1/T2/T3) metric
  catalog, the concrete `queries.py` changes, `metadata.csv` additions + target count, tag/cardinality
  controls, and keep/rename/deprecate calls for the existing 49. Standard metrics only; query metrics
  live in `05`.

### DBM features — *the headline (Half 2), one collector per doc*

- **[`05-dbm-query-metrics.md`](05-dbm-query-metrics.md)** — `Db2StatementMetrics(DBMAsyncJob)` over
  `MON_GET_PKG_CACHE_STMT`: the diff engine, client-side obfuscation/signature, unit normalization
  (µs vs ms), `db2_rows` payload, and FQT events. The strongest, most live-grounded feature doc.
- **[`06-dbm-query-samples-activity.md`](06-dbm-query-samples-activity.md)** —
  `Db2Activity(DBMAsyncJob)` over `MON_CURRENT_SQL` / `MON_GET_ACTIVITY`: point-in-time active-session
  capture → `dbm-activity` + `dbm-samples`, self-exclusion, UOW enrichment, connection counts, and
  the live-proven **sub-millisecond OLTP blind spot** (ASH-style, not a complete request log).
- **[`07-dbm-execution-plans.md`](07-dbm-execution-plans.md)** — The Db2 plan collector. **Highest
  risk:** Db2 has no inline JSON EXPLAIN, so the plan tree must be assembled from EXPLAIN tables to
  JSON. Path A (`EXPLAIN PLAN FOR`) is live-proven; Path B (`EXPLAIN_FROM_SECTION`, the recommended
  path that sidesteps `?`-markers) is unproven and spike-gated. Isolated and independently deferrable.
- **[`08-dbm-schemas-and-settings.md`](08-dbm-schemas-and-settings.md)** — `Db2Metadata(DBMAsyncJob)`
  settings (`DBMCFG`∪`DBCFG` + `REG_VARIABLES`, with derived `pending_change`) and
  `Db2SchemaCollector(SchemaCollector)` over `SYSCAT.*`, both on `dbm-metadata`. Independent of P2/P3.

### Build — *what code to write, in what order, and how to test it*

- **[`09-implementation-architecture.md`](09-implementation-architecture.md)** — The concrete module
  layout, class skeletons, `IbmDb2Check` wiring, config surface (`spec.yaml` → regenerated models),
  manifest/metadata changes, and file-by-file change list. Mirrors the SQL Server modules. The most
  directly-codeable doc.
- **[`10-implementation-phases.md`](10-implementation-phases.md)** — The ordered execution plan:
  phases **P0–P5**, each with scope, dependencies, concrete tasks, acceptance criteria, and effort
  (~12–17 weeks, one engineer), plus the cross-phase dependency graph. The canonical phase scheme.
- **[`11-testing-and-validation.md`](11-testing-and-validation.md)** — The testing companion: runnable
  `ddev`/`docker compose` commands, the `get_event_platform_events("dbm-*")` assertion pattern, the
  `dbm_instance` fixture + thread hygiene, the 12.1.4 CI container, and per-phase P0–P5 checklists.
  **The de-facto tie-breaker** — its §0 pins the contract decisions (`db2`, `num_exec_with_metrics`,
  300s) and overrides any contradicting research note.

### Risk — *what's still unknown; read before coding*

- **[`12-risks-open-questions.md`](12-risks-open-questions.md)** — Every load-bearing risk, caveat,
  and decision-needed: gating/privilege/query-metrics/samples/plans/driver-threading/cardinality/
  packaging risks (§1–§8) plus the numbered **OQ-1..12** open questions a human must resolve. The
  single best "what's still unknown" home.
- **[`99-review-and-gaps.md`](99-review-and-gaps.md)** — The adversarial **completeness review** of
  the full set: the TOP-5 gaps, a per-document confidence table, prioritized fixes (F1..F13), the
  cross-doc contradiction list, and the **verify-live-first checklist**. Read before implementing.

> Deep line-cited detail lives in **`_research/`** (28 `.md` studies + `_raw/` live captures): the
> `db2-live-*` probes (pkgcache/activity/config), the `map-*` per-category metric maps, and the
> `code-*` framework/template studies. The numbered docs condense these; drop to `_research/` for
> exact `MON_GET_*` columns and ready-to-paste `metadata.csv` rows.

---

## 4. Phased roadmap at a glance

The canonical scheme is doc [`10`](10-implementation-phases.md)'s **P0–P5**.

| Phase | Scope | Key deliverable | Value / Risk | Effort |
|---|---|---|---|---|
| **P0** | Metric-breadth expansion (writes, IO-timing, direct I/O, container FS, sort/hash, HADR) on the *existing* synchronous pattern; stand up Db2 **12.1.4** in CI. | ~320 standard metrics; 12.1.4 green CI; no DBM machinery. | High / Low | ~1–1.5 wk |
| **P1** | **DBM scaffold (once)** + query metrics: convert to `DatabaseCheck`, per-job connection layer, `database_instance` registration, then `Db2StatementMetrics`. | DBM unlock: host registers; `dbm-metrics` `db2_rows` + FQT. | High / Medium | ~2.5–3.5 wk |
| **P2** | Query samples + activity over `MON_CURRENT_SQL` / `MON_GET_ACTIVITY`. | `dbm-activity` + `dbm-samples`; connection counts. | High / Medium | ~2–2.5 wk |
| **P3** | **Execution plans (isolated, spike-gated, highest risk)** — assembled from EXPLAIN tables to JSON. | `dbm_type:"plan"` events **or** a documented deferral. | Medium / **High** | ~3–5 wk (high variance) |
| **P4** | Schemas (`SYSCAT.*`) + settings (`DBMCFG`∪`DBCFG`) on `dbm-metadata`. Independent of P2/P3. | `db2_settings` + chunked `db2_databases`. | Medium / Low-Med | ~2–2.5 wk |
| **P5** | Dashboards, docs, packaging, CI hardening (GA polish). | Dashboards, README, `service_checks`, driver-install story. | Polish / Low | ~1.5–2 wk |

**Landing order:** P0 → **P1 (the DBM unlock)** → P2 ∥ P4 → P3 (may slip) → P5. P0 shares the 12.1.4
CI container with everything; P1 builds the scaffold P2–P4 reuse; P3 is deliberately last and
independently deferrable (P1/P2/P4 still ship value if it slips). Total **~12–17 weeks** (one engineer;
P4 ∥ P2/P3 and P5 drafting overlap can compress this). *Caveat (`99` F6): doc `09` §7 uses a
P1=metrics / P2=scaffold scheme — treat doc `10`'s P0–P5 as canonical.*

---

## 5. Key risks & verify-live-first (read before coding)

The top P0 gates from [`12`](12-risks-open-questions.md) and [`99`](99-review-and-gaps.md). **None can
be answered from this repo** — run each on a live Db2 12.1.4 server (or the Agent binary) *before*
writing the corresponding collector.

1. **Live-`DESCRIBE` every `[DOC]`-flagged column before any SELECT** (`99` F3, `12` §2.3). A large
   slice of P0 — all `MON_GET_CONTAINER.FS_*` (never probed), `MON_GET_MEMORY_SET.*`, and the
   buffer-pool write/async/victim/prefetch + `LOG_WRITE_TIME`/`NUM_LOG_WRITE_IO` columns — is
   doc-sourced, not live-verified. **A single missing column makes the whole widened SELECT fail
   silently (WARNING-swallowed → the collector goes dark).** This is a hard P0 gate, not a footnote.
2. **Obfuscator `dbms:'db2'` dialect spike** (`12` OQ-5, `99` F5) — gates *all* `query_signature`
   (P1/P2/P3). The dialect list lives in the Agent's Go `pkg/obfuscate`, **not** in
   `integrations-core`. Verify whether the obfuscator accepts `'db2'`, silently falls back, or errors,
   against the Agent **before** coding `statements.py`; settle once so 05/06/07 sign identically.
3. **`EXPLAIN_FROM_SECTION` (Path B) spike** (`12` OQ-7, `99` F4) — gates the entire P3 plan feature.
   Only Path A was run live, as the instance owner. Confirm the procedure signature, the `'M'` source
   arg, the OUT params, and that a non-owner `datadog` user can call it under `SYSMON`. If blocked →
   Path A + the `?`-marker problem, or defer P3. Keep plans default-disabled until the spike passes.
4. **The `"db2"` vs `"ibm_db2"` split is product-visible** (`12` §8.1, `99` gap #5). Two distinct
   strings that must NOT be conflated: the **metric prefix / integration name / hatch env / `ddev`
   target stay `ibm_db2`**, but the **DBM source / dbms / vendor-row-key = `"db2"`** (`ddsource:"db2"`,
   `dbms:"db2"`, `db2_rows`/`db2_activity`/`db2_connections`) — the backend routes DBM off this string.
   `DatabaseCheck.dbms` defaults to the lowercased class name (`"ibmdb2check"`), so it **must** be set
   to `"db2"` explicitly. (Resolved across the numbered set; only `_research/code-testing-harness.md`
   still dissents — trust `"db2"`.)
5. **`execution_indicators=['num_exec_with_metrics']`** (`99` F1), NOT `num_executions` — IBM's
   recommended divisor. Docs 09 §3.1 and 10 P1 (the code-skeleton docs) still say `num_executions`;
   every other doc is correct. Use `num_exec_with_metrics` everywhere, guarding 0.
6. **`database_instance_collection_interval` default = 300s** (`99` F2), not 1800 — verified in
   pg/sqlserver `defaults.py`. Pin 300 (docs 03/08/09 mis-state 1800).
7. **12.1.4 CI image swap is asserted, not proven** (`99` checklist #8). Nobody has run the existing
   suite against `icr.io/db2_community/db2:12.1.4.0`; `common.py` constants + `DbManager.initialize`
   (monitoring user + grants) need changes the plan doesn't fully enumerate. Gates all phases' CI.

Further gates in `99`'s verify-live-first list: least-privilege grant set for a non-owner `datadog`
user (all research ran as `DB2INST1` owner; OQ-4); `ibm_db` threading + CLOB-materialization + low-level
vs `ibm_db_dbi` (OQ-8); plan-JSON shape round-trip (OQ-10); `SYSCAT.*` column DESCRIBEs (P4);
cluster/HADR validation (structurally impossible on the standalone test box; OQ-3); minimum supported
version floor (only 12.1.4 proven; OQ-2). The `ibm_db` driver is a C-extension **not bundled** with the
Agent — air-gapped DBM install is a multi-step GA blocker (`12` §6.4).

---

## 6. Start here (reading path for the implementing agent)

1. **Read [`99`](99-review-and-gaps.md) TOP-5 + the verify-live-first checklist + the cross-doc
   contradiction table.** Know the one-line doc bugs (F1 `num_exec_with_metrics`, F2 `300s`, F7
   interval, F6 phase numbering) and the live gates before you trust any single doc.
2. **If Db2 is unfamiliar, read [`01`](01-db2-monitoring-primer.md).** Then read
   [`02`](02-current-integration-audit.md) for the shipped 49 metrics and the gap.
3. **Resolve the two P0/P1 blockers first:** pin the `dbms`/`ddsource` string to `"db2"` in one place,
   and spike the obfuscator dialect against the Agent (`12` OQ-5).
4. **Read [`03`](03-reference-architecture.md) (the blueprint) and
   [`10`](10-implementation-phases.md) §0 + the dependency graph**, then execute **P0**: swap CI to
   Db2 12.1.4 and **live-`DESCRIBE` every `[DOC]` column** before writing any SELECT (`99` F3 / `12`
   §2.3). P0 ships value with no DBM machinery and de-risks the rest.
5. **For P1+ build detail, pair the feature doc with [`09`](09-implementation-architecture.md):**
   [`05`](05-dbm-query-metrics.md) (query metrics) → [`06`](06-dbm-query-samples-activity.md)
   (samples/activity) ∥ [`08`](08-dbm-schemas-and-settings.md) (schemas/settings) →
   [`07`](07-dbm-execution-plans.md) (plans, spike-gated last). Test each against
   [`11`](11-testing-and-validation.md), honoring [`12`](12-risks-open-questions.md)'s OQ gates.

> When the docs say "the check", they mean the single class `IbmDb2Check` in
> `/home/bits/dd/integrations-core/ibm_db2/datadog_checks/ibm_db2/ibm_db2.py`. Result-dict keys come
> back **lowercase** (`ATTR_CASE=CASE_LOWER`) — keep all new keys lowercase.
