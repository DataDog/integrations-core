# 99 — Completeness Review & Gaps (Adversarial Critique of the COMPLETE doc set)

**What this is.** A fresh, adversarial completeness review of the **now-complete** Db2 fidelity plan
in `/home/bits/dd/integrations-core/ibm_db2/dev-docs/db2-fidelity-plan/`. The numbered doc set
`00`–`12` all **exist** now (the previous version of this file reviewed a 3-doc skeleton; that review
is obsolete and is fully superseded here). This pass read every numbered doc end-to-end and
re-grounded the load-bearing claims against the `_research/_raw/*.txt` live captures and the actual
`datadog_checks_base` / reference-integration source.

**Verdict.** The plan is **implementation-ready in substance** — the architecture (subclass
`DatabaseCheck`, one `DBMAsyncJob` per feature, reuse the base delta/obfuscation/signature helpers,
per-job `ibm_db` connection isolation) is correct and well-templated on SQL Server, and the four DBM
feature docs (05–08) are each independently buildable. The remaining problems are **not** conceptual;
they are (a) a small set of **cross-doc contradictions** that will produce wrong code if the
implementer reads the wrong doc first, (b) a body of **`(verify)`/`[DOC]` facts** that the plan
correctly flags but that still gate real phases, and (c) **P0 live checks** that must run on a Db2
server before any SELECT is written. Most fixes are one line.

**How to read the priorities.** **P0** = blocks or actively misleads the implementer / will ship
wrong product-visible behavior. **P1** = causes rework or silently-wrong output. **P2** =
fidelity/quality gap, safe to defer.

---

## TOP 5 GAPS (the headline — relay these)

1. **`execution_indicators` is contradicted across docs — `num_exec_with_metrics` (correct) vs
   `num_executions` (wrong) — and the wrong value sits in the two docs the implementer codes from.**
   Docs 05 (§1.4, §3.3, §10), the README (risk #5), the contract, and doc 11 (§0) all correctly
   mandate `execution_indicators=['num_exec_with_metrics']` (IBM's recommended divisor; live-grounded
   in `_research/db2-live-pkgcache.md` §1 item 8). **But doc 09 §3.1 (`_collect_and_diff`) and doc 10
   P1 task list both write `execution_indicators=['num_executions']`** — and 09/10 are exactly the
   "what code to write / what order" docs. An implementer copying 09's `statements.py` skeleton ships
   the wrong indicator. **Fix: `num_exec_with_metrics` everywhere; correct 09 §3.1 and 10 P1.** (P0)

2. **`database_instance_collection_interval` default is given three different ways; the real base
   default is 300s.** Verified in source: `postgres/.../config_models/defaults.py:59` **and**
   `sqlserver/.../config_models/defaults.py:43` both `return 300`. Doc 11 (§0, §2.1) and README risk #6
   correctly say **300**. But **doc 03 §2.5 says 1800**, **doc 08 §3.4/§4.5 say 1800**, and **doc 09
   §4.1 says "default 1800 (verify; pick a value)"**. Three docs will generate a `defaults.py` that
   re-emits the registration event 6× too slowly. **Fix: pin 300 in 03/08/09.** (P0)

3. **A large slice of P0 metrics and the entire `MON_GET_CONTAINER` surface is `[DOC]` (never
   live-DESCRIBE'd), yet specified as if confirmed — and a single missing column silently kills the
   whole collector.** `MON_GET_CONTAINER` is **not** in the `_raw/02` DESCRIBE dump (confirmed: it is
   present in the *function list* `_raw/01:25` but never column-probed), so every `FS_USED_SIZE`/
   `FS_TOTAL_SIZE`/`container.*` metric in docs 04 §1.5/§1.9 is unverified. Same for `POOL_COL_WRITES`,
   `POOL_ASYNC_*_WRITES`, `POOL_NO_VICTIM_BUFFER`, `UNREAD_PREFETCH_PAGES`, `VECTORED_IOS`,
   `LOG_WRITE_TIME`/`NUM_LOG_WRITE_IO`, `MON_GET_MEMORY_SET.*`. Doc 04 §6.2 rule 5 and the README risk
   #3 both flag this, and doc 11 §6.2 gives the exact `DESCRIBE` commands — **good** — but because a
   non-existent column makes the whole widened SELECT fail (swallowed at WARNING → the collector goes
   silently dark), the live-DESCRIBE step is a **hard P0 gate**, not a footnote. **Fix: keep it as the
   first gating P0 task (P0a in doc 04 §7), and the implementer must run it before P0/P1 SELECTs.**
   (P0)

4. **`EXPLAIN_FROM_SECTION` (Path B — the *recommended* plan path) was never run live; only Path A
   was.** `_research/_raw/05-explain-test.txt` proves `EXPLAIN PLAN FOR` works and gives the
   `EXPLAIN_OPERATOR` schema + 8-column join key — but it ran as `DB2INST1` (instance owner). Doc 07
   honestly recommends Path B (it sidesteps the `?`-marker problem) while admitting (§0, §1.3, §7
   item 1) that the procedure signature, the `'M'` source arg, the OUT params, and **whether a
   non-owner `datadog` user can even call it** are all unproven. If Path B is blocked, the design
   falls back to Path A and inherits the full parameter-marker problem on the common (parameterized
   OLTP) case — the single biggest *feature* risk. Doc 07 §7 / doc 12 OQ-7 correctly gate the whole
   P3 feature behind a spike with default-disabled config. **No fix needed beyond honoring the gate;
   relay it as the dominant P3 unknown.** (P0 for P3 only)

5. **The obfuscator `dbms:'db2'` dialect is unverifiable from this repo and gates every
   `query_signature` (P1/P2/P3).** Confirmed independently: there is no obfuscator dialect table under
   `datadog_checks_base/.../utils/db/` — the list lives in the Agent's Go `pkg/obfuscate`, not in
   `integrations-core`. Docs 05 §3.2, 06 §3.2, 09 §4.2, 10 (global dep + P1 task 0), 12 OQ-5 all flag
   it consistently and prescribe the fallback (generic SQL on an unknown dialect). This is correctly
   tracked now (doc 12 exists). The residual risk: if the obfuscator *errors* (rather than silently
   falling back) on an unknown `dbms`, P1 breaks. **Fix: spike against the Agent binary in P1 task 0
   before coding `statements.py`; the decision propagates to 05/06/07 identically (they must compute
   the signature the same way or metrics/samples/plans fail to link).** (P0/P1)

---

## Per-document confidence table (01–12)

Confidence = how safely the implementer can build straight from this doc without re-deriving or
being misled. "Issues" lists the specific defects this review found (see the GAPS/FIXES list for IDs).

| Doc | Confidence | Grounding | Issues found |
|---|---|---|---|
| **01 — monitoring primer** | **High** | Live-grounded (`_raw/01`,`04`,`05`; editions/config research). | Conceptual only; `MON_GET_MEMORY_SET/POOL` columns marked `(verify)` (correct). No defects. |
| **02 — current audit** | **High** | Reads shipped 4.3.0 source + `code-ibm_db2-current.md`. | Solid baseline. Minor: still lists itself as one of only-3-docs in places it cross-refs `00`; cosmetic. |
| **03 — reference architecture** | **High (1 default bug)** | Verified vs base source. | **F2** (1800s should be 300s, §2.5). §2 cadence table says query-metrics "10s pg/mysql, 60s mssql" then §5.2 says "query_metrics 60" — pick one default and state it once (F7). |
| **04 — metrics fidelity** | **High (gated on live-DESCRIBE)** | Maps are `[LIVE]`/`[DOC]`-honest. | **F3** (`[DOC]`/`MON_GET_CONTAINER` gate). Internally consistent; the tiering + cardinality discipline is strong. `unit_name` allow-list caveats correctly flagged. |
| **05 — query metrics** | **Very High** | `db2-live-pkgcache.md` + base source, line-cited. | The strongest feature doc. `num_exec_with_metrics` correct here. No defects beyond shared obfuscator OQ (F5). |
| **06 — samples/activity** | **High** | `db2-live-activity.md`; OLTP blind spot live-proven. | `MON_GET_APPLICATION_HANDLE` is marked "(verify the scalar helper exists)" but it **is present in `_raw/01:14`** — can be promoted to verified (F8). FQT double-emit (05 vs 06) resolved sensibly (prefer 05). |
| **07 — execution plans** | **Medium (by design)** | Path A live-proven; Path B + JSON-shape unproven. | **F4** (Path B unproven) + plan-JSON shape (OQ-10) are inherent, correctly gated. Highest-variance doc; honest about it. |
| **08 — schemas/settings** | **High (1 default bug)** | `db2-config-settings.md` (DBMCFG/DBCFG live), `SYSCAT.*` cols `(verify)`. | **F2** (1800s, §3.4/§4.5). `SYSCAT.*` column lists `(verify)` — correct, must DESCRIBE in P4. |
| **09 — implementation arch** | **High (1 real bug)** | SQL Server mirror, verified file:line. | **F1** (`num_executions` in §3.1 — wrong) + **F2** (1800s §4.1). Otherwise the most directly-codeable doc; `connection.py`/`config.py`/check skeletons are sound. `util.py`-vs-`utils.py` naming is muddled (F9). |
| **10 — phases** | **High (1 real bug + numbering)** | Dependency-aware, cross-refs intact. | **F1** (`num_executions` in P1 tasks). **F6** phase-numbering mismatch: doc 10 uses **P0–P5**; docs 04/09/11 and the README's roadmap table mix P0–P5 with a P1-based scheme; the same word "P1" means "standard metrics" in doc 09 §7 but "DBM scaffold" in doc 10. Real source of confusion. |
| **11 — testing** | **Very High** | Runnable; correctly overrides stale research-doc strings in its §0. | Best operational doc. Correctly pins `db2` + `num_exec_with_metrics` + 300s in §0 as the authority. Concrete, per-phase, copy-pasteable. Minor: assumes the §0 corrections propagate — they don't yet (F1/F2). |
| **12 — risks/open Qs** | **Very High** | Consolidates all unknowns; OQ-1..12 numbered. | The single best "what's still unknown" home. Correctly carries OQ-5 (obfuscator), OQ-7 (Path B), OQ-9 (notes 09 missing — now stale since 09 exists: minor F10). |

---

## GAPS / FIXES (prioritized, with IDs)

### P0 — blocking / will ship wrong behavior

- **F1 — `num_executions` → `num_exec_with_metrics`.** Doc 09 §3.1 and doc 10 P1 use the wrong
  execution indicator. Every other doc is correct. These are the code-skeleton docs, so this is the
  highest-impact one-line fix. (gap #1)
- **F2 — `database_instance_collection_interval` 1800 → 300.** Real base default is 300
  (`postgres`/`sqlserver` `defaults.py`). Fix docs 03 §2.5, 08 §3.4/§4.5, 09 §4.1. Docs 11/README
  already say 300. (gap #2)
- **F3 — Live-DESCRIBE every `[DOC]` column before any SELECT.** `MON_GET_CONTAINER`,
  `MON_GET_MEMORY_SET`, and the buffer-pool/log write/async/victim/prefetch columns are doc-sourced
  only. A missing column silently dark-fails the whole collector. Honor doc 04 §7 P0a / doc 11 §6.2 as
  a hard gate. (gap #3)
- **F5 — Obfuscator `dbms:'db2'` spike (P1 task 0).** Not answerable from this repo (confirmed: no
  dialect table in `datadog_checks_base`). Run against the Agent before coding `statements.py`. (gap
  #5)
- **F4 — `EXPLAIN_FROM_SECTION` spike (P3 gate).** Path B unproven; if blocked, fall back to Path A's
  marker problem or defer P3. Keep plans default-disabled until the spike passes. (gap #4)

### P1 — rework / silently-wrong if unfixed

- **F6 — Reconcile phase numbering across docs.** Doc 10 is P0–P5 (P0 = metric breadth on the
  existing pattern; P1 = DBM scaffold + query metrics). Doc 09 §7 calls metric breadth "P1" and the
  DBM scaffold "P2". The README roadmap table uses yet another P0–P5 mapping and even admits "10's
  P0→P4 punch-list numbering differs slightly." **Pick one canonical phase scheme (recommend doc 10's
  P0–P5) and make 09/04/02 reference it by the same labels.** Until then, an implementer can mis-order
  the scaffold vs the metric work.
- **F7 — Pin one query-metrics default interval.** Doc 03 §2 says "10s pg/mysql, 60s mssql" and §5.2
  says "query_metrics 60"; doc 05 §5.2 says default **10**; doc 09 §4.1 table says **60**. The
  collector's `rate_limit = 1/interval` depends on this. **Recommend 60s** (matches sqlserver, the
  structural template, and is gentler on the package cache) — state it once and make 05 match.
- **F8 — Promote `MON_GET_APPLICATION_HANDLE` from `(verify)` to confirmed.** Doc 06 §1.2 hedges
  whether the scalar self-exclusion helper exists; `_raw/01:14` lists it present on 12.1.4. The
  `VALUES(MON_GET_APPLICATION_HANDLE())` self-exclusion path is therefore available (still verify the
  exact call form, but it is not a "may not exist" risk).
- **F11 — Lock-wait / blocking detail is gated OFF by the live monitor config, not just "optional."**
  `_raw/04` shows `mon_lockwait=NONE`, `mon_locktimeout=NONE`, `mon_deadlock=WITHOUT_HIST`. Docs 04
  §1.7, 06 §1.6 treat `MON_GET_LOCKS`/`MON_GET_APPL_LOCKWAIT`/`MON_LOCKWAITS` blocking features as
  "optional, gated by a config flag" but do **not** prominently say the *server-side* monitor switches
  must also be non-NONE for the lock-event detail to populate. Note this: blocking detection needs
  both the agent config flag **and** `mon_lockwait <> NONE` on the DB. (Cross-ref doc 12 §2.3, which
  does say it — propagate to 04/06.)

### P2 — fidelity / quality, safe to defer

- **F9 — `util.py` vs `utils.py` naming.** Doc 09 §1 proposes a *new* `util.py` alongside the existing
  `utils.py` then says "recommended — extend `utils.py` directly." Pick one (extend `utils.py`); the
  two-file split invites import confusion.
- **F10 — Doc 12 OQ-9 is stale.** It says `09-implementation-architecture.md` "does not exist in the
  plan directory yet" — it now does. Drop OQ-9 or rewrite it as "ensure 09 stays in sync with the
  threading contract."
- **F12 — `files_closed` triple-home still unresolved in the live docs.** Doc 04 §5.4 flags it
  (bufferpool vs tablespace vs the `conf.yaml.example` custom-query example) and recommends
  `ibm_db2.bufferpool.files_closed`, but the source `files_closed` is `[DOC]` (F3) — confirm it exists
  on `MON_GET_BUFFERPOOL` before committing to that home.
- **F13 — Pg/mysql fidelity areas the plan deliberately omits (acknowledge, don't necessarily build).**
  Adversarially checked against postgres/mysql parity: the plan has **no** analog for (a) pg's
  `pg_stat_io` per-backend-type breakdown / mysql `performance_schema` wait-event *names* — doc 06 §1.5
  honestly says Db2 gives no per-activity wait-event name and defers it; (b) **named wait events** in
  samples (deferred, doc 06 §1.5); (c) **deadlock capture** (skipped, doc 09 §3.4 — Db2 deadlock detail
  is in event monitors / `db2diag.log`, and `mon_deadlock=WITHOUT_HIST` live); (d) **stored-procedure /
  routine metrics** (`MON_GET_ROUTINE*` exist in `_raw/01` but are unmapped — a real pg/mysql-adjacent
  gap left on the table); (e) the **WLM activity event monitor** path that would close the fast-OLTP
  blind spot (doc 06 §4.4, deferred). These are all *consciously* deferred and documented — listing
  them so the parity claim ("~320 metrics exceeds pg/mysql in count") is understood to be count-parity,
  not feature-for-feature wait/deadlock parity.

---

## (1) Is every proposed metric/feature backed by a real proven source?

**Mostly yes, and the docs are honest about the exceptions.** The `[LIVE]`/`[DOC]` and `(verify)`
discipline in docs 04/05/06/08 is the strongest part of the plan. The split:

- **Proven live (high confidence):** query metrics (`MON_GET_PKG_CACHE_STMT`, 327 cols, stable
  `HEX(EXECUTABLE_ID)`, µs/ms unit split, CLOB text, `/*dd*/` comment — `db2-live-pkgcache.md`,
  `_raw/01`); activity (`MON_CURRENT_SQL`/`MON_GET_ACTIVITY` + the fast-OLTP blind-spot negative result
  — `db2-live-activity.md`); settings (DBMCFG/DBCFG row counts — `db2-config-settings.md`); monitor
  switches (`_raw/04`); EXPLAIN *Path A* + `EXPLAIN_OPERATOR` cost schema (`_raw/05`); the function
  inventory and `MON_GET_APPLICATION_HANDLE` presence (`_raw/01`); editions/version gating.
- **`[DOC]` / `(verify)` (must be confirmed live first):** all `MON_GET_CONTAINER.*` (never probed),
  `MON_GET_MEMORY_SET.*`, the buffer-pool write/async/victim/prefetch columns, `LOG_WRITE_TIME`/
  `NUM_LOG_WRITE_IO`, the entire HADR/CF/GBP/FCM column surface (standalone server returns 0 rows —
  *structurally* untestable here), `SYSCAT.*` schema column lists, `MON_GET_LOCKS`/`APPL_LOCKWAIT`
  columns, `EXPLAIN_FROM_SECTION` (Path B), and the plan-JSON shape the backend accepts.

So: features are sourced, but **a non-trivial fraction of the column-level detail is doc-sourced and
gated on a live DESCRIBE / spike** — which is exactly what the verify-live-first checklist below
captures. No feature is *fabricated*; the risk is silent SELECT failure on a missing `[DOC]` column.

## (2) Pg/mysql fidelity areas still missing

Covered well: throughput/commits/rollbacks, rows I/U/D, buffer-pool reads+writes+timing, direct I/O,
sort/hash, locks, log latency, per-table/index, WLM, memory pools, HADR, settings, schemas, query
metrics, samples/activity, FQT, instance registration. Genuinely **missing or deferred** (see F13):
named wait events, deadlock capture, routine/stored-proc metrics (`MON_GET_ROUTINE*` unmapped),
pg_stat_io-style backend breakdown, and the event-monitor path for sub-ms OLTP completeness. The
"exceeds pg/mysql metric count" claim (doc 04 §3.2) is true for *count* but should be read as
count-parity, not wait/deadlock feature-parity.

## (3) DBM payload-contract consistency across 05/06/07/08

**Consistent and correct.** Spot-checked the load-bearing fields:

- **`ddsource`/`dbms`/vendor-row-key = `"db2"`** — uniform across 05 (§4), 06 (§5), 07 (§3.4), 08
  (§2.4/§3.4), 03 (§3), 09 (§2.2). Doc 11 §0 explicitly nails this as the authority and notes the lone
  remaining offender is `_research/code-testing-harness.md` (still says `ibm_db2` in places) — a
  research doc, not a numbered doc, so the numbered set is now internally clean. The README key-risk #2
  and doc 12 §8.1 both pin `"db2"` and correctly note `DatabaseCheck.dbms` defaults to
  `self.__class__.__name__.lower()` → `"ibmdb2check"` (verified at `db.py:38`), so it **must** be set
  explicitly.
- **`ddtags` shape: comma-joined STRING on samples/plan/fqt, LIST on activity** — stated identically in
  03 §3.5, 05/06 §5, 07 §3.4, and 12 §8.3. Consistent.
- **`timestamp` = epoch milliseconds (`time.time()*1000`)** — uniform across all four feature docs and
  the contract. Consistent.
- **`metadata.dbm = true` on the `database_instance` event** — uniform (03 §2.5, 08 §3.4, 09 §2.5).
- **Units (µs vs ms):** `TOTAL_CPU_TIME` = microseconds, other `*_TIME` = milliseconds — flagged
  identically and prominently in 05 §1.3, 06 §1.2, the maps, and 12 §3 item 4. Consistent and
  live-grounded. The only residual is per-element unit `(verify)` tags in doc 04 (correct caution).

The single contract-level *default* inconsistency is **F2** (the 1800/300 split), which is an envelope
field (`collection_interval` on the registration event), not a routing string.

## (4) Are the testing steps (doc 11) concrete, runnable, and do they cover every feature?

**Yes — doc 11 is the strongest operational doc.** It gives runnable `ddev`/`docker compose` commands,
the exact `get_event_platform_events("dbm-*")` assertion pattern (correctly noting there is no
`assert_event_platform_event` helper), the `dbm_instance` fixture with `run_sync:True` +
near-zero-interval + `stop_orphaned_threads` thread hygiene, the 12.1.4 compose with `privileged`/`ipc:
host`/`start_period:480s`, the `--skip-env` fast path, and per-phase P0–P5 checklists. Coverage:
P0 metric breadth (§4 + `assert_metrics_using_metadata` + HADR-zero-row §4.4), dbm-metrics (§5.2),
FQT/plan (§5.3), dbm-activity (§5.4), dbm-metadata + `database_instance` (§5.5), obfuscation mocking
(§5.7). **Every feature has a matching test section.** Gaps: it inherits **F1** (its §0 says
`num_exec_with_metrics` but the docs it tests, 09/10, say `num_executions` — the test would then
contradict the implementation) and **F2** (its §2.1 example asserts `…() -> 300`, correct, but 03/08/09
generate 1800). Both are upstream-doc bugs, not doc-11 bugs. Doc 11 is the de-facto tie-breaker and
says so.

## (5) Cross-doc inconsistencies / contradictions (consolidated)

| # | Inconsistency | Docs in conflict | Resolution |
|---|---|---|---|
| 1 | `execution_indicators` value | 05/11/README (`num_exec_with_metrics`) vs **09/10** (`num_executions`) | `num_exec_with_metrics` (F1) |
| 2 | `database_instance_collection_interval` default | 11/README (300) vs **03/08/09** (1800) | 300 — verified in pg/mssql `defaults.py` (F2) |
| 3 | query-metrics default interval | 05 (10s) vs **03/09** (60s) | 60s, sqlserver-aligned (F7) |
| 4 | phase numbering / what "P1" means | 10 (P0–P5) vs **09** (P1=metrics, P2=scaffold) vs README mix | adopt 10's P0–P5 (F6) |
| 5 | `ddsource`=`"db2"` vs `"ibm_db2"` | numbered docs all `"db2"`; only `_research/code-testing-harness.md` dissents | `"db2"` (already resolved in numbered set; purge from research doc) |
| 6 | `MON_GET_APPLICATION_HANDLE` existence | 06 hedges `(verify)` | present per `_raw/01` (F8) |
| 7 | doc 12 OQ-9 ("09 doesn't exist") | stale — 09 exists | drop/rewrite OQ-9 (F10) |

Unit consistency (µs/ms) and the `ddtags` string-vs-list quirk are **not** in conflict anywhere — they
are stated uniformly. That is a credit to the doc set.

---

## VERIFY-LIVE-FIRST checklist (the P0 gating checks an implementer must run on a Db2 server)

Run all of these on the live 12.1.4 container (`make -C .../dbm/local-dev exec/db2`, then `db2 connect
to testdb`) **before** writing the corresponding SELECT/collector. None can be answered from this repo.

1. **Obfuscator dialect (OQ-5, F5) — gates P1/P2/P3 signatures.** Against the **Agent** (`pkg/obfuscate`,
   *not* this repo): does `obfuscate_sql(query, {'dbms':'db2'})` accept `db2`, silently fall back, or
   error? Decide the fallback dialect. Settle once; 05/06/07 inherit it.
2. **`[DOC]` columns exist (F3) — gates P0/P1 SELECTs.** `DESCRIBE SELECT * FROM TABLE(...)` for
   `MON_GET_BUFFERPOOL`, `MON_GET_TRANSACTION_LOG`, **`MON_GET_CONTAINER`** (never probed),
   **`MON_GET_MEMORY_SET`**, `MON_GET_DATABASE` — reconcile every `[DOC]` column (`POOL_COL_WRITES`,
   `POOL_ASYNC_*_WRITES`, `POOL_NO_VICTIM_BUFFER`, `UNREAD_PREFETCH_PAGES`, `VECTORED_IOS`,
   `LOG_WRITE_TIME`, `NUM_LOG_WRITE_IO`, all `FS_*`). Drop or version-gate any absent column.
3. **`EXPLAIN_FROM_SECTION` Path B (OQ-7, F4) — gates the entire P3 plan feature.** As a **non-owner
   `datadog`** user against a live `EXECUTABLE_ID`: confirm the procedure signature, the `'M'` source
   arg, the OUT params, and that it is callable under `SYSMON`. If it fails → Path A + marker problem,
   or defer P3.
4. **Plan-JSON shape (OQ-10) — gates P3 usefulness.** Round-trip the synthesized Db2 operator-tree JSON
   through a real Agent's `obfuscate_sql_exec_plan` + the DBM UI renderer; confirm a non-Postgres
   source's key names render.
5. **Least-privilege grant set (OQ-4).** Re-run the P1/P2/P4 `MON_GET_*` + config/env routine calls as
   a non-owner `datadog` user (all research ran as `DB2INST1` owner). Confirm `SYSMON` suffices, or
   enumerate `EXECUTE` grants.
6. **`ibm_db` threading + CLOB + handle lifecycle (OQ-8).** Confirm `ibm_db.connect` from a
   `ThreadPoolExecutor` worker is permitted by the pinned `ibm_db==3.2.6`; that `fetch_assoc`
   materializes `STMT_TEXT` CLOB (not a locator); and decide `ibm_db` low-level vs `ibm_db_dbi` (the
   latter likely forced by `callproc` OUT params for Path B). Establish per-job connection isolation.
7. **`SET CURRENT ISOLATION = UR`** via `ibm_db.exec_immediate` — syntax/effect (doc 09 §2.3 `(verify)`).
8. **12.1.4 CI image swap (README risk #7).** Nobody has run the existing suite against
   `icr.io/db2_community/db2:12.1.4.0`; `common.py` constants + `DbManager.initialize` need changes the
   plan does not fully enumerate. Prove the suite green on 12.1.4 — itself a P0 deliverable.
9. **`SYSCAT.*` schema columns (doc 08 §1.3-§1.6 `(verify)`).** `DESCRIBE` `SYSCAT.SCHEMATA/TABLES/
   COLUMNS/INDEXES/INDEXCOLUSE/REFERENCES/KEYCOLUSE` on 12.1.4; promote to `[LIVE]` for P4.
10. **Cluster/HADR (OQ-3) — cannot be done on this server.** All HADR/CF/GBP/FCM columns are unverified
    because the test box is standalone Community. Decide: ship empty-tolerant + unvalidated, stand up a
    pureScale/HADR bed, or defer.
11. **Db2 `max_query_duration` mechanism (doc 08 §4.4 `(verify)`).** Confirm the `ibm_db` connection
    `QueryTimeout` attribute (not `SET CURRENT QUERY OPTIMIZATION`) for the schema-collection timeout.
12. **Minimum supported version floor (OQ-2).** Only 12.1.4 is proven; 11.5 behavior is inferred. Pin
    the floor and decide whether to test an 11.5 instance before claiming support.

---

## Recommended fix order

1. **One-line doc fixes first (F1, F2, F7, F8, F10):** correct `num_executions`→`num_exec_with_metrics`
   in 09/10; pin 300 in 03/08/09; pin one query-metrics interval (60) in 05/09; promote
   `MON_GET_APPLICATION_HANDLE`; retire OQ-9. ~30 minutes, removes every product-visible contradiction.
2. **Reconcile phase numbering (F6):** make 09/04/02 use doc 10's P0–P5 labels.
3. **Then execute the verify-live-first checklist** — items 1 (obfuscator), 2 (`[DOC]`/CONTAINER
   DESCRIBE), 8 (12.1.4 CI) are the P0 gates that unblock P0/P1; item 3 (Path B) and 4 (plan JSON) gate
   P3 only and can run later.
4. **Build in doc-10 order** (P0 metrics → P1 scaffold+query-metrics → P2 samples/activity ∥ P4
   schemas/settings → P3 plans last, spike-gated), honoring 12's OQ gates.
