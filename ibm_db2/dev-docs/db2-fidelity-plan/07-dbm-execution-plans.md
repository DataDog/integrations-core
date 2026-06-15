# 07 — DBM Execution Plans: the Db2 Plan Collector

**Audience:** an engineer or AI agent who understands Datadog DBM "explain plans" for Postgres
(`EXPLAIN (FORMAT JSON)` shipped as `dbm_type:"plan"` sample events), but has little Db2 background.
This doc designs the Db2 analog. It is the **highest-risk** DBM piece (plan P3 in
[`10-implementation-phases.md`](10-implementation-phases.md)) because Db2 has **no inline JSON
EXPLAIN** — a plan must be assembled out of relational "explain tables" into the DBM plan-JSON
contract. The good news: the core mechanic is **proven to work** on our live server (see the raw
capture below), so this doc starts from "EXPLAIN works" rather than from nothing.

**What "execution plans" is, in one sentence:** for a sampled / cached statement, obtain Db2's
optimizer access plan (the operator tree with costs), serialize it to the same plan-JSON shape
Postgres ships, obfuscate it, sign it, and emit one `dbm_type:"plan"` event per
`(query_signature, plan_signature)` — rate-limited so we collect each plan at most once per window.

**Where this fits in the plan:**
- [`05-dbm-query-metrics.md`](05-dbm-query-metrics.md) — the statement-metrics collector. It produces
  the `query_signature` and the `EXECUTABLE_ID` this collector keys plans on, and emits the **FQT**
  event; this doc emits the **plan** event for the same statements.
- [`06-dbm-query-samples-activity.md`](06-dbm-query-samples-activity.md) — the samples/activity collector. It owns the
  active-session snapshot and the `query_truncated` / network / `db.*` envelope fields a plan event
  reuses; whether plans are collected from the **live sample** path or the **package-cache** path is
  decided here (§1) and coordinated with 06.
- [`09-implementation-architecture.md`](09-implementation-architecture.md) — module layout, check
  wiring (`run_job_loop` / `cancel`), and the per-job `ibm_db` connection isolation this collector
  plugs into.
- [`11-testing-and-validation.md`](11-testing-and-validation.md) — how to test explain-table
  bootstrapping, tree assembly, and the plan-JSON shape against the live 12.1.4 container.
- [`12-risks-open-questions.md`](12-risks-open-questions.md) — the load-bearing open questions
  (`EXPLAIN_FROM_SECTION` privileges, `?`-marker reopt, explain-table isolation) surfaced here.

> **Authoritative source for the Db2 behavior below:** the live EXPLAIN test on our Db2 **12.1.4**
> container (2026-06-15), captured raw in
> [`_research/_raw/05-explain-test.txt`](_research/_raw/05-explain-test.txt), plus
> [`_research/db2-live-pkgcache.md`](_research/db2-live-pkgcache.md) for `EXECUTABLE_ID`. The
> Postgres pattern this mirrors is
> [`_research/code-postgres-dbm-samples.md`](_research/code-postgres-dbm-samples.md); the payload
> envelope is [`_research/code-dbm-payload-contract.md`](_research/code-dbm-payload-contract.md) §4.
> Claims I could not verify against the live test are tagged **(verify)**.

---

## 0. What the live EXPLAIN test already proved

This is the empirical floor the design rests on — every claim below is from
[`_research/_raw/05-explain-test.txt`](_research/_raw/05-explain-test.txt), run on
`DB2/LINUXX8664 12.1.4.0`, DB `TESTDB`, auth ID `DB2INST1`:

1. **The explain tables already exist** on our server, in schema `SYSTOOLS`, created by
   `SYSPROC.SYSINSTALLOBJECTS('EXPLAIN', ...)`. We did **not** have to create them — they were already
   present (a prior `CALL SYSPROC.SYSINSTALLOBJECTS('EXPLAIN','C',NULL,NULL)` and the resulting
   `CREATE FUNCTION SYSTOOLS...` / explain-table DDL show up in the package cache,
   [`_research/db2-live-pkgcache.md`](_research/db2-live-pkgcache.md) §3). So in our environment the
   bootstrap is a no-op; the design must still **handle both states** (§2).
2. **`EXPLAIN PLAN FOR <text>` succeeded.** A real statement was explained without executing it.
3. **A real operator tree with costs was produced.** Reading `EXPLAIN_OPERATOR` returned:

   ```
   OPERATOR_ID  OPERATOR_TYPE  TOTAL_COST                  IO_COST
       1        RETURN         +1.21895591735840E+002      +1.36000000000000E+002
       2        TBSCAN         +1.21895591735840E+002      +1.36000000000000E+002
   ```

   i.e. a two-node `RETURN <- TBSCAN` plan, each row an operator with a `TOTAL_COST` (timerons) and an
   `IO_COST`. This is the raw material a plan tree is built from.
4. **The `EXPLAIN_OPERATOR` column schema is known** (the `DESCRIBE` is captured in the raw file): the
   load-bearing columns are `OPERATOR_ID`, `OPERATOR_TYPE`, `TOTAL_COST`, `IO_COST`, `CPU_COST`,
   `FIRST_ROW_COST`, `RE_TOTAL_COST`, `BUFFERS`, plus the join key columns `EXPLAIN_REQUESTER`,
   `EXPLAIN_TIME`, `SOURCE_NAME`, `SOURCE_SCHEMA`, `SOURCE_VERSION`, `EXPLAIN_LEVEL`, `STMTNO`,
   `SECTNO`. Those eight join-key columns are the **composite key** that ties together every explain
   table for one explained statement (§3.1).

What the test did **not** prove (carried as open, §7): `EXPLAIN_FROM_SECTION` privileges for a
non-instance-owner monitoring user; `?`-marker reopt behavior; explain-table write contention under a
busy agent loop; the full `EXPLAIN_STREAM` edge/`EXPLAIN_PREDICATE` content shape. Treat those as
**(verify)** spike items.

---

## 1. The two capture paths (and which to use)

Postgres has exactly one path: call a `SECURITY DEFINER` function that runs
`EXPLAIN (FORMAT JSON) <statement>` on the **raw** statement text (with literals) and returns JSON
([`_research/code-postgres-dbm-samples.md`](_research/code-postgres-dbm-samples.md) §4.3). Db2 offers
**two** fundamentally different paths, and choosing between them is the central design decision.

### 1.1 Path A — `EXPLAIN PLAN FOR <text>` (re-compile from statement text)

```sql
EXPLAIN PLAN FOR <statement text>;        -- populates the explain tables; does NOT run the statement
```

- **What it is.** Hand Db2 the SQL **text**, it re-compiles the statement under the *current* session
  environment, and writes the resulting access plan into the explain tables. This is the **direct
  analog of Postgres `EXPLAIN`** — and it is the path the live test exercised (§0).
- **Needs:** (a) the statement text, and (b) the explain tables present and writable (§2).
- **The problem it inherits:** because it re-compiles from text, it has the **parameterized-query
  problem** — a cached statement's text contains `?` markers (`UPDATE inventory_items SET quantity = ?
  WHERE sku = ?`, verified in [`_research/db2-live-pkgcache.md`](_research/db2-live-pkgcache.md) §5).
  `EXPLAIN PLAN FOR ... ? ...` may fail to type the markers or may produce a different plan than the
  one that actually ran (§4). It is also a fresh compile under the agent's session, so isolation
  level, special registers, `CURRENT SCHEMA`, and statistics drift can yield a plan that differs from
  production's compiled section.

### 1.2 Path B — `EXPLAIN_FROM_SECTION` (explain the already-compiled section)

```sql
-- Explain the section identified by its package-cache EXECUTABLE_ID, into the explain tables:
CALL SYSPROC.EXPLAIN_FROM_SECTION(
        :executable_id,    -- VARCHAR(32) FOR BIT DATA, the SAME id key from MON_GET_PKG_CACHE_STMT
        'M',               -- source: 'M' = in-memory package cache (vs 'P' package, 'C' catalog) (verify)
        NULL, NULL,        -- section/stmt qualifiers (NULL for pkg-cache lookup) (verify)
        :explain_schema,   -- schema holding the explain tables (e.g. the monitoring user)
        ?, ?, ?, ?, ? );   -- OUT: explain_requester, explain_time, source_name, source_schema, source_version
```

- **What it is.** Db2 takes the **already-compiled section** out of the package cache (or a package, or
  the catalog) by its `EXECUTABLE_ID` and writes its **actual** access plan into the explain tables —
  **without re-compiling and without re-running** the statement. (`db2exfmt` / the `db2 explain`
  tooling wraps this same `EXPLAIN_FROM_*` family.)
- **Needs:** the `EXECUTABLE_ID` (which [`05-dbm-query-metrics.md`](05-dbm-query-metrics.md) already
  reads from `MON_GET_PKG_CACHE_STMT` as the stable diff key) and the explain tables present/writable.
  It does **not** need the statement text to plan.
- **Why it is better for our use case:**
  - **No parameterized-query problem.** The compiled section already baked in its access plan when the
    app prepared it; `EXPLAIN_FROM_SECTION` just reads that plan. `?` markers, host variables, and
    reopt are all already resolved — §4 mostly evaporates. This is the same advantage Postgres' section
    /`force_generic_plan` workaround chases, but Db2 gives it to us for free.
  - **It is the plan that actually ran**, not a fresh compile under the agent's (possibly different)
    session environment. Fidelity is strictly higher.
  - **It keys on the identity we already have.** `EXECUTABLE_ID` is the same stable
    `VARCHAR(32) FOR BIT DATA` the metrics collector diffs on
    ([`_research/db2-live-pkgcache.md`](_research/db2-live-pkgcache.md) §3/§4) — so plan collection
    composes cleanly with metrics collection: metrics gives us the hot statements + their ids, this
    collector explains the interesting ones.

### 1.3 Recommendation

**Use Path B (`EXPLAIN_FROM_SECTION` from the package cache) as the primary path; keep Path A
(`EXPLAIN PLAN FOR`) as a fallback.** Rationale, ranked:

1. **Path B sidesteps the parameterized-query problem entirely** (the single hardest part of the
   Postgres explain story, [`_research/code-postgres-dbm-samples.md`](_research/code-postgres-dbm-samples.md)
   §7). For an OLTP app that prepares parameterized statements (exactly our orders workload), Path A
   would fail or mis-plan most of the interesting queries.
2. **Path B yields the real plan**, matching the metrics we already ship for that `EXECUTABLE_ID`.
3. **Path B composes with metrics** — same id, same loop cadence, "explain the hot ones."

Path A is retained only as a fallback when (a) we have statement text but **no `EXECUTABLE_ID`** (e.g.
a live sample of a statement that has since left the cache), or (b) `EXPLAIN_FROM_SECTION` is
unavailable / unprivileged on a given instance. When Path A is used on parameterized text, apply the
§4 representative-value strategy.

> **Both paths write to the same explain tables and read back with the same code (§3).** Only the
> *populate* step differs. So the assembly/serialization half of this collector is path-agnostic.

> **Caveat carried from the live test (§0):** `EXPLAIN_FROM_SECTION` privileges for a non-instance
> owner were **not** verified — the test ran as `DB2INST1`. The §6 grant list and a spike to confirm
> `datadog` can call it are a P3 prerequisite **(verify)**.

---

## 2. Explain-table bootstrapping

Db2 will not write a plan unless the explain tables exist in the target schema. There are ~15 tables
in the set; the four this collector reads are `EXPLAIN_STATEMENT`, `EXPLAIN_OPERATOR`,
`EXPLAIN_STREAM`, `EXPLAIN_PREDICATE` (plus `EXPLAIN_INSTANCE`/`EXPLAIN_OBJECT` exist and are
join-reachable). They are created by the stored procedure:

```sql
CALL SYSPROC.SYSINSTALLOBJECTS('EXPLAIN', 'C', NULL, CAST(:explain_schema AS VARCHAR(128)));
--                              ^object    ^'C'=create   ^tablespace(NULL=default)  ^schema
```

- **On our server they already exist** in `SYSTOOLS` (§0.1) — the call above will then raise
  **`SQL0601N ... already exists, SQLSTATE=42710`**. **Treat 42710 as success / idempotent** — catch
  it and continue, exactly the way Postgres treats "explain function already present" as a no-op. Do
  **not** drop/recreate.
- **Bootstrap policy (do it once, lazily, cached per schema):** on first plan attempt for an instance,
  probe for the tables (`SELECT 1 FROM <schema>.EXPLAIN_OPERATOR FETCH FIRST 0 ROWS ONLY`); if missing
  (`SQL0204N ... undefined name`), call `SYSINSTALLOBJECTS('EXPLAIN','C',NULL,:schema)`, swallow
  42710, and cache the result in a per-instance `TTLCache` (mirror Postgres'
  `_collection_strategy_cache`, [`_research/code-postgres-dbm-samples.md`](_research/code-postgres-dbm-samples.md)
  §4.2/§5 — `maxsize=1000, ttl=300`) so a broken/unprivileged instance is re-probed at most every 5
  minutes, not every loop.
- **Which schema?** Use a **dedicated, agent-owned explain schema** (e.g. the monitoring user's own
  schema, or an explicit `DATADOG` schema) so the agent's plan writes never collide with a customer's
  own explain runs in `SYSTOOLS`. `EXPLAIN_FROM_SECTION` and `EXPLAIN PLAN FOR` both write to the
  tables in `CURRENT SCHEMA` / the explicitly named schema. Make the schema a config knob
  (`query_samples.explain_schema` **(verify)**), defaulting to the monitoring user's schema.

```python
def _ensure_explain_tables(self, cursor, schema):
    if self._explain_setup_cache.get(schema):           # TTLCache(maxsize=1000, ttl=300)
        return self._explain_setup_cache[schema]         # cached (None=ok, or an error code)
    try:
        cursor.execute(f"SELECT 1 FROM {schema}.EXPLAIN_OPERATOR FETCH FIRST 0 ROWS ONLY")
        state = None                                      # tables present
    except ibm_db.Error as e:
        if _is_undefined_name(e):                         # SQL0204N
            try:
                cursor.callproc('SYSPROC.SYSINSTALLOBJECTS', ('EXPLAIN', 'C', None, schema))
                state = None
            except ibm_db.Error as e2:
                state = None if _is_already_exists(e2) else DBExplainError.failed_function  # 42710 -> ok
        else:
            state = DBExplainError.connection_error       # or insufficient_privilege, etc.
    self._explain_setup_cache[schema] = state
    return state
```

### The schema to read back

All explain tables share the **composite join key** the live `EXPLAIN_OPERATOR` `DESCRIBE` exposed
(§0.4): `(EXPLAIN_REQUESTER, EXPLAIN_TIME, SOURCE_NAME, SOURCE_SCHEMA, SOURCE_VERSION, EXPLAIN_LEVEL,
STMTNO, SECTNO)`. Every populate step (Path A or B) produces one new row-set under a fresh
`EXPLAIN_TIME`; read back the row-set you just wrote by capturing that key (Path B returns it as OUT
params; Path A: take `MAX(EXPLAIN_TIME)` for the requester).

| Table | What it holds | Key columns this collector uses |
|---|---|---|
| `EXPLAIN_STATEMENT` | one row per explained statement: the statement text, `TOTAL_COST` (overall), `STATEMENT_TEXT`, `EXPLAIN_LEVEL` (`'P'`=chosen plan) | join key + `TOTAL_COST`, `STATEMENT_TEXT`, `QUERYNO`, `QUERY_DEGREE` |
| `EXPLAIN_OPERATOR` | **one row per plan operator (node)** — the tree's vertices | join key + `OPERATOR_ID`, `OPERATOR_TYPE`, `TOTAL_COST`, `IO_COST`, `CPU_COST`, `FIRST_ROW_COST`, `BUFFERS`, `TOTAL_CARDINALITY` (verify name) |
| `EXPLAIN_STREAM` | **the edges** — data streams between operators and base objects; carries cardinalities | join key + `STREAM_ID`, `SOURCE_ID`, `TARGET_ID`, `OBJECT_SCHEMA`, `OBJECT_NAME`, `STREAM_COUNT` (estimated rows on the edge) |
| `EXPLAIN_PREDICATE` | per-operator predicates (the `WHERE`/join conditions applied at each node) | join key + `OPERATOR_ID`, `PREDICATE_ID`, `PREDICATE_TEXT`, `HOW_APPLIED` |
| `EXPLAIN_OBJECT` | base objects (tables/indexes) referenced, with their stats | join key + `OBJECT_SCHEMA`, `OBJECT_NAME`, `OBJECT_TYPE` (optional enrichment) |

`OPERATOR_TYPE` values seen / expected: `RETURN`, `TBSCAN` (table scan, seen live), `IXSCAN` (index
scan), `FETCH`, `NLJOIN`/`HSJOIN`/`MSJOIN` (joins), `SORT`, `GRPBY`, `FILTER`, `INSERT`/`UPDATE`/
`DELETE`. (verify the full enum against the target fixpack — do not hard-code it; pass `OPERATOR_TYPE`
through as a string.)

---

## 3. Reading the tables and serializing to the DBM plan-JSON contract

`EXPLAIN_OPERATOR` gives the **nodes**; `EXPLAIN_STREAM` gives the **edges** (`SOURCE_ID` →
`TARGET_ID`). Assembling the tree means: build a node per operator, then wire each stream whose
`SOURCE_ID`/`TARGET_ID` are both operators as a parent→child edge; streams that touch a base object
(`OBJECT_NAME` set) annotate the leaf node with its table/index and estimated `STREAM_COUNT` rows.

### 3.1 Read-back query (one explained statement)

```sql
-- Operators (nodes):
SELECT OPERATOR_ID, OPERATOR_TYPE, TOTAL_COST, IO_COST, CPU_COST,
       FIRST_ROW_COST, BUFFERS
FROM   <schema>.EXPLAIN_OPERATOR
WHERE  EXPLAIN_REQUESTER = ? AND EXPLAIN_TIME = ? AND SOURCE_NAME = ?
  AND  SOURCE_SCHEMA = ?     AND SOURCE_VERSION = ? AND EXPLAIN_LEVEL = ?
  AND  STMTNO = ?            AND SECTNO = ?
ORDER BY OPERATOR_ID;

-- Streams (edges + base-object touches):
SELECT STREAM_ID, SOURCE_ID, TARGET_ID, OBJECT_SCHEMA, OBJECT_NAME, STREAM_COUNT
FROM   <schema>.EXPLAIN_STREAM
WHERE  <same 8-column join key>
ORDER BY STREAM_ID;

-- Predicates (per operator), optional enrichment:
SELECT OPERATOR_ID, PREDICATE_ID, HOW_APPLIED, PREDICATE_TEXT
FROM   <schema>.EXPLAIN_PREDICATE
WHERE  <same 8-column join key>;
```

In Db2's explain model, `SOURCE_ID`/`TARGET_ID` < 0 (often `-1`) denote a base object on the stream
rather than an operator — those streams are the leaf's table/index inputs; `TARGET_ID` of the topmost
operator's outbound stream is the consumer (`RETURN`). Build the tree by treating an
operator `op` as the **parent** of every operator that feeds it via a stream (`stream.TARGET_ID ==
op.OPERATOR_ID and stream.SOURCE_ID` is an operator).

### 3.2 The plan-JSON shape

The DBM backend's plan obfuscator/normalizer expects a **JSON plan string** in a structure compatible
with what `datadog_agent.obfuscate_sql_exec_plan` parses
([`_research/code-dbm-payload-contract.md`](_research/code-dbm-payload-contract.md) §4.1;
[`_research/code-postgres-dbm-samples.md`](_research/code-postgres-dbm-samples.md) §4.5). Postgres
ships Postgres' native `EXPLAIN (FORMAT JSON)` array-of-`{"Plan": {...}}`. Db2 has no native JSON, so
we **synthesize** an equivalent nested-node document. Mirror the Postgres key names where they map, so
the obfuscator and the UI's plan renderer behave consistently **(verify the exact key names the Go
`obfuscate_sql_exec_plan` and the backend plan renderer require for a non-Postgres source — this is
the single biggest plan-shape open question, [`12-risks-open-questions.md`](12-risks-open-questions.md))**:

```jsonc
// synthesized Db2 plan document (one root node, children nested)
{
  "Node Type":      "TBSCAN",          // EXPLAIN_OPERATOR.OPERATOR_TYPE
  "Total Cost":     121.89559,         // EXPLAIN_OPERATOR.TOTAL_COST  (timerons)
  "IO Cost":        136.0,             // EXPLAIN_OPERATOR.IO_COST
  "CPU Cost":       ...,               // EXPLAIN_OPERATOR.CPU_COST
  "First Row Cost": ...,               // EXPLAIN_OPERATOR.FIRST_ROW_COST
  "Plan Rows":      10000,             // EXPLAIN_STREAM.STREAM_COUNT into this node (est. cardinality)
  "Relation Name":  "INVENTORY_ITEMS", // EXPLAIN_STREAM.OBJECT_NAME (leaf only)
  "Schema":         "DB2INST1",        // EXPLAIN_STREAM.OBJECT_SCHEMA (leaf only)
  "operator_id":    2,                 // EXPLAIN_OPERATOR.OPERATOR_ID (Db2-specific, for traceability)
  "Plans": [ /* child nodes, recursively */ ]
}
```

```python
def _build_plan_tree(operators, streams):
    nodes = {op['operator_id']: {
        "Node Type":      op['operator_type'],
        "Total Cost":     _to_float(op['total_cost']),
        "IO Cost":        _to_float(op['io_cost']),
        "CPU Cost":       _to_float(op.get('cpu_cost')),
        "First Row Cost": _to_float(op.get('first_row_cost')),
        "Plans":          [],
    } for op in operators}

    root_id = min(nodes)                       # OPERATOR_ID 1 == RETURN (the live test's root)
    for s in streams:
        src, tgt = s['source_id'], s['target_id']
        if src in nodes and tgt in nodes:      # operator -> operator edge
            nodes[tgt]["Plans"].append(nodes[src])
        elif s.get('object_name'):             # base-object input -> annotate the consuming leaf
            leaf = nodes.get(tgt)
            if leaf is not None:
                leaf["Relation Name"] = s['object_name']
                leaf["Schema"]        = s['object_schema']
                leaf["Plan Rows"]     = _to_int(s.get('stream_count'))
    return nodes[root_id]

raw_plan        = json.dumps(self._build_plan_tree(operators, streams))
normalized_plan = datadog_agent.obfuscate_sql_exec_plan(raw_plan, normalize=True)
obfuscated_plan = datadog_agent.obfuscate_sql_exec_plan(raw_plan)
plan_signature  = compute_exec_plan_signature(normalized_plan)   # base helper, reuse verbatim
```

- `compute_exec_plan_signature` (base `utils/db/sql.py:48`) JSON-decodes, re-encodes with
  `sort_keys=True`, then `mmh3.hash64` — order-independent, identical trees collapse. **Reuse
  verbatim** so plan grouping matches every other DBM product.
- The cost numbers arrive as Db2 `DOUBLE` rendered like `+1.21895591735840E+002`
  (verified live, §0.3) → coerce with `float()`; `default_json_event_encoding` also handles `Decimal`.
- `STREAM_COUNT` is the **estimated** cardinality on the edge (this is `EXPLAIN`, not `EXPLAIN ANALYZE`
  — Db2 explain has no actual-rows; costs/cardinalities are optimizer estimates, like Postgres
  `EXPLAIN` without `ANALYZE`). Do **not** claim actual-row counts.

### 3.3 Statement obfuscation

The plan event also carries the obfuscated **statement** and `query_signature` — computed exactly as
in [`05-dbm-query-metrics.md`](05-dbm-query-metrics.md) §2 (`obfuscate_sql_with_metadata` +
`compute_sql_signature`, `replace_null_character=True`, strip the leading `/*dd...*/` comment). For
Path B we obtain the text from `EXPLAIN_STATEMENT.STATEMENT_TEXT` (or carry it from the metrics row
that supplied the `EXECUTABLE_ID`); for Path A the text is the input. **Obfuscate the statement before
shipping** — never ship raw SQL on the `plan` event (raw text is the opt-in `rqt`/`rqp` path only,
[`_research/code-dbm-payload-contract.md`](_research/code-dbm-payload-contract.md) §4.3).

### 3.4 The plan event payload (`dbm_type:"plan"`)

Mirror the Postgres plan event verbatim
([`_research/code-dbm-payload-contract.md`](_research/code-dbm-payload-contract.md) §4.1) with the
Db2 source strings. Submit via `self._check.database_monitoring_query_sample(json.dumps(event,
default=default_json_event_encoding))`.

```python
event = {
    "host":             self._check.reported_hostname,
    "database_instance": self._check.database_identifier,
    "dbm_type":         "plan",
    "ddagentversion":   datadog_agent.get_version(),
    "ddsource":         "db2",                                  # NOT "ibm_db2" (00-README key-risk #2)
    "ddtags":           ",".join(self._dbtags(db_name)),        # COMMA-JOINED STRING (samples track)
    "timestamp":        time.time() * 1000,                     # epoch MILLISECONDS
    "cloud_metadata":   self._check.cloud_metadata,
    "service":          self._config.service,
    "network": {"client": {"ip": ..., "port": ..., "hostname": ...}},  # from the sample (06) if any
    "db": {
        "instance":        db_name,
        "plan": {
            "definition":        obfuscated_plan,               # the synthesized JSON plan string (§3.2)
            "signature":         plan_signature,                # compute_exec_plan_signature(normalized)
            "collection_errors": collection_errors,             # [{"code":..., "message":...}] or None
        },
        "query_signature": query_signature,                     # compute_sql_signature(obfuscated_sql)
        "resource_hash":   query_signature,                     # == query_signature (as in pg)
        "statement":       obfuscated_statement,                # obfuscated SQL
        "metadata": {"tables": dd_tables, "commands": dd_commands, "comments": dd_comments},
        "query_truncated": truncation_state,                    # from 05/06 (LENGTH(STMT_TEXT))
    },
    "db2": { "executable_id": exec_id_hex, "explain_level": "P", ... },  # db-specific extras (opaque to backend)
}
```

- **`ddtags` is a comma-joined *string* on the samples track** (it is a *list* only on the activity
  track) — match per type exactly
  ([`_research/code-dbm-payload-contract.md`](_research/code-dbm-payload-contract.md) §4.1/§5).
- **Emit a plan event even when EXPLAIN failed** — `plan.definition`/`signature` `None` and
  `collection_errors` carries the `DBExplainError`-style code (§5/§7), exactly as Postgres does, so the
  failure is recorded once per window and surfaces in the UI.

---

## 4. Parameter-marker handling

This is the crux that **Path B largely eliminates** but Path A must confront. Cached statements keep
their `?` parameter markers verbatim (verified live,
[`_research/db2-live-pkgcache.md`](_research/db2-live-pkgcache.md) §5:
`UPDATE inventory_items SET quantity = ? WHERE sku = ?`). This is the exact Db2 analog of Postgres'
`$1`/`$2` problem ([`_research/code-postgres-dbm-samples.md`](_research/code-postgres-dbm-samples.md)
§7).

- **Path B (recommended): no marker problem.** `EXPLAIN_FROM_SECTION` reads the **already-compiled**
  section — the optimizer already chose an access plan for the prepared statement when the app prepared
  it. Markers are irrelevant to reading that plan back. This is *why* Path B is the recommendation
  (§1.3): it is the Db2 equivalent of Postgres' `force_generic_plan` workaround, but obtained for free
  from the real compiled section.

- **Path A (fallback): needs representative values or a generic-plan mode.** `EXPLAIN PLAN FOR ... ?
  ...` may raise `SQL0418N` (untyped parameter marker not allowed here) or produce a degenerate plan.
  Two mitigations, in order of preference:
  1. **`SET CURRENT EXPLAIN MODE` + reopt / `REOPT ONCE`** to coax Db2 into compiling the parameterized
     statement with deferred binding **(verify the exact special-register / `REOPT` incantation that
     lets `EXPLAIN PLAN FOR` accept untyped `?` on 12.1.4)** — the closest analog to Postgres'
     `plan_cache_mode = force_generic_plan`.
  2. **Cast the markers / substitute representative literals.** Replace `?` with typed nulls
     (`CAST(NULL AS INTEGER)`) or representative sample values. This mirrors Postgres' "EXECUTE with N
     `null` args" trick, but Db2 marker typing is finicky — `NULL` short-circuits some predicates to
     "no rows," skewing the plan, so representative non-null values are safer when the type is known.
  Carry a `parameterized_query` `DBExplainError` and **fall through to Path B** whenever a cached
  `EXECUTABLE_ID` exists — i.e. Path A's marker handling only matters for the text-only,
  no-`EXECUTABLE_ID` case.

> **Design consequence:** prefer Path B so this entire section is mostly moot. Reach for Path A's
> marker handling only for live-sample statements that are no longer in the cache.

---

## 5. Caching by `query_signature` + rate-limiting

Explaining is expensive (a compile or a section read + ~3 table reads + table writes) and the plan for
a given query rarely changes. Reuse the **exact Postgres cache/limiter design**
([`_research/code-postgres-dbm-samples.md`](_research/code-postgres-dbm-samples.md) §5), built on the
base `RateLimitingTTLCache` / `ConstantRateLimiter` / `TTLCache`
([`05-dbm-query-metrics.md`](05-dbm-query-metrics.md) §5;
[`09-implementation-architecture.md`](09-implementation-architecture.md)). `acquire(key)` returns
`True` only if the key is absent and the cache is not full — "acquire == may proceed."

| Cache | Type | Default | Key | Purpose |
|---|---|---|---|---|
| `_explain_setup_cache` | `TTLCache` | `maxsize=1000, ttl=300s` | `explain_schema` | don't re-bootstrap / re-probe a broken instance every loop (§2) |
| `_explained_statements_ratelimiter` | `RateLimitingTTLCache` | `maxsize=5000`, `ttl=3600/explained_queries_per_hour_per_query` (=60s) | `(db_name, query_signature)` | **collect a plan at most ~once/min per logical query** — the key dedup that makes this affordable |
| `_seen_plans_ratelimiter` | `RateLimitingTTLCache` | `maxsize=10000`, `ttl=3600/samples_per_hour_per_query` (=240s) | `(query_signature, plan_signature)` | ingestion rate per (query, plan) — same plan re-seen is dropped for the window |
| `_explain_errors_cache` | `TTLCache` | `maxsize=5000, ttl=86400s` | `query_signature` | negative cache of un-explainable queries (don't retry a doomed explain for a day) |

Flow per candidate statement (mirrors Postgres `_collect_plan_for_statement`):

```python
def _maybe_explain(self, row):
    qsig = row['query_signature']
    if not self._explained_statements_ratelimiter.acquire((self._db_name, qsig)):
        return                                   # explained recently -> skip (the big cost saver)
    if qsig in self._explain_errors_cache:
        return                                   # known-unexplainable -> skip for a day
    plan, err = self._explain(row)               # Path B (preferred) or Path A; bootstrap-gated (§2)
    if err is not None:
        self._explain_errors_cache[qsig] = err   # cache the negative (unless privilege error, retry those)
    event = self._build_plan_event(row, plan, err)
    if self._seen_plans_ratelimiter.acquire((qsig, event_plan_signature)):
        self._check.database_monitoring_query_sample(
            json.dumps(event, default=default_json_event_encoding))
```

- **Collect once per signature, not per `EXECUTABLE_ID`.** Because literal variants + re-prepares
  fragment one logical query across many `EXECUTABLE_ID`s
  ([`_research/db2-live-pkgcache.md`](_research/db2-live-pkgcache.md) §4/§5), keying the limiter on
  `query_signature` (computed from obfuscated text) — not the raw id — avoids re-explaining the "same"
  query N times. (We still *explain via* one representative `EXECUTABLE_ID` per signature on Path B.)
- **The DBMAsyncJob loop itself is rate-limited** via `ConstantRateLimiter(rate_limit=1/interval)` —
  this is the "spike-gated" control [`10-implementation-phases.md`](10-implementation-phases.md) calls
  for: the explain loop runs on its own slow cadence, independent of the (1s) sample loop.
- **Mirror the `DBExplainError` taxonomy** ([`_research/code-postgres-dbm-samples.md`](_research/code-postgres-dbm-samples.md)
  §12) for `collection_errors[].code`: `no_plans_possible`, `parameterized_query`, `query_truncated`,
  `connection_error`, `database_error`, `failed_function` (bootstrap/SYSINSTALLOBJECTS failure),
  `undefined_table` (explain tables missing + uncreatable), plus a Db2 `section_not_found` for an
  `EXECUTABLE_ID` evicted between metrics read and explain. Permission errors are **not** cached (the
  user may fix the grant), every other code is.

---

## 6. Privileges + the explain-table write footprint

### 6.1 Grants

```sql
-- Path B: explain the compiled section from the package cache
GRANT EXECUTE ON PROCEDURE SYSPROC.EXPLAIN_FROM_SECTION TO USER datadog;          -- (verify proc sig/grant)
-- Bootstrapping the explain tables (only if the agent must create them):
GRANT EXECUTE ON PROCEDURE SYSPROC.SYSINSTALLOBJECTS    TO USER datadog;          -- (verify)
-- INSERT/SELECT on the explain tables in the agent's explain schema:
GRANT INSERT, SELECT, DELETE ON <explain_schema>.EXPLAIN_STATEMENT TO USER datadog;  -- + OPERATOR/STREAM/
                                                                                     --   PREDICATE/OBJECT/INSTANCE
-- Path A: EXPLAIN PLAN FOR additionally needs EXPLAIN authority on the statement's objects (verify),
-- i.e. the monitoring user must be able to compile the statement (SELECT/EXECUTE on referenced objects).
```

- The live test ran as `DB2INST1` (instance owner) which has all of this implicitly; a **dedicated
  `datadog` user needs the explicit grants above** — and crucially the `EXPLAIN_FROM_SECTION` /
  `SYSINSTALLOBJECTS` execute grants were **not verified for a non-owner** (§0, §1.3). Confirm with a
  spike before P3 commits **(verify)**. Cross-reference the consolidated privilege matrix in
  [`03-reference-architecture.md`](03-reference-architecture.md) once it lands.
- If the agent is allowed only to **read** pre-existing explain tables (no create/insert), only Path B
  against tables a DBA pre-creates is viable; surface a `failed_function`/`undefined_table` error
  otherwise.

### 6.2 Write footprint (the cost the customer pays)

Unlike Postgres `EXPLAIN` (read-only, no persisted artifact), **both Db2 paths WRITE rows into the
explain tables on every explain.** This is the defining operational difference and must be managed:

- **Each explain inserts a row-set** (one `EXPLAIN_STATEMENT`, N `EXPLAIN_OPERATOR`, M `EXPLAIN_STREAM`,
  …) under a fresh `EXPLAIN_TIME`. Left unmanaged these tables grow unbounded.
- **Use a dedicated agent explain schema** (§2) so the agent's churn never pollutes a customer's
  explain history in `SYSTOOLS`.
- **Delete-after-read.** Immediately after reading back a plan (§3.1), `DELETE` that row-set by its
  8-column join key (hence the `DELETE` grant above) — keep the tables near-empty. Alternatively
  periodically truncate the agent schema's explain tables. This bounds the footprint to roughly one
  in-flight plan at a time.
- **The rate-limiter (§5) is also a write-throttle** — ~1 explain/min/query caps insert volume.
- **Write contention / isolation** under a busy agent loop was **not** load-tested (§0); keep explain
  on its own slow cadence and its own connection (§8) to avoid interfering with the workload
  **(verify under load, [`11-testing-and-validation.md`](11-testing-and-validation.md))**.

---

## 7. Honest feasibility assessment

**Feasible, and de-risked by the live test — but the highest-effort, highest-variance DBM piece (P3,
~3–5 wk, [`10-implementation-phases.md`](10-implementation-phases.md)).** What is *proven* vs *open*:

**Proven (live, §0):**
- Explain tables exist on 12.1.4 (in `SYSTOOLS`) and `SYSINSTALLOBJECTS('EXPLAIN',...)` creates them.
- `EXPLAIN PLAN FOR` runs without executing the statement and produces a real costed operator tree.
- The `EXPLAIN_OPERATOR` schema + the 8-column join key are known; cost/IO numbers are readable.
- The `EXECUTABLE_ID` that Path B needs is the same stable id the metrics collector already reads
  ([`_research/db2-live-pkgcache.md`](_research/db2-live-pkgcache.md)).

**Open / risk-bearing (all carried in [`12-risks-open-questions.md`](12-risks-open-questions.md)):**
1. **`EXPLAIN_FROM_SECTION` (Path B) was never actually run** — only `EXPLAIN PLAN FOR` (Path A) was
   proven. The exact procedure signature, its source-type arg (`'M'`), its OUT params, and whether a
   non-owner `datadog` user can call it are all **(verify)**. *If Path B turns out to be unavailable/
   unprivileged, we fall back to Path A and inherit the full §4 parameter-marker problem* — the single
   biggest fidelity risk.
2. **The plan-JSON shape the backend/obfuscator accept for a non-Postgres source is unverified** (§3.2).
   `datadog_agent.obfuscate_sql_exec_plan` and the UI renderer may expect specific key names; a wrong
   shape ships but renders poorly. Needs a round-trip test against a real agent.
3. **Tree assembly from `EXPLAIN_STREAM` edges** (the `SOURCE_ID`/`TARGET_ID` < 0 base-object
   convention, multi-input joins, subquery/`SORT` materialization) is more involved than the 2-node
   live example; complex plans (joins, CTEs, columnar) need iterative validation.
4. **Write footprint + contention** (§6.2) is an operational cost Postgres simply does not have;
   delete-after-read mitigates but was not load-tested.
5. **Plan = optimizer estimate, not actuals.** Db2 explain (like pg `EXPLAIN` without `ANALYZE`) gives
   estimated cardinalities/costs only — no actual-rows/actual-time. Set expectations accordingly.

**Honest limits to state in the feature's docs:** plans are estimates; the first interval after cache
churn under-reports; literal-heavy apps can thrash; explain writes to tables (mitigated, not zero);
Path B fidelity depends on the section still being cached at explain time; and **if Path B is blocked,
parameterized OLTP statements (the common case) are hard to plan via Path A.** Ship Path B first,
behind its own `query_samples`-style config gate, **disabled until the §0/§7 spike confirms the
procedure + privileges** — it is independently deferrable without blocking metrics (05), samples (06),
or metadata.

---

## 8. Connection isolation + scheduling

Identical to the metrics collector ([`05-dbm-query-metrics.md`](05-dbm-query-metrics.md) §5/§8.3): the
plan collector is a `DBMAsyncJob` (`dbms="db2"`, `job_name="query-samples"` or a dedicated
`"explain-plans"` job) with its **own dedicated `ibm_db` connection** — never share the main check's
or the metrics job's handle across threads. Because every explain **writes** to the explain tables, an
isolated connection also keeps the explain transaction (and its `DELETE`-after-read) off the
metrics/sample read path. `shutdown_callback` closes the connection;
[`09-implementation-architecture.md`](09-implementation-architecture.md) owns the wiring.

> **Whether plans live in the samples job (06) or a separate explain job is a wiring choice (09).**
> Functionally this doc's collector consumes either (a) the hot `(query_signature, EXECUTABLE_ID)`
> pairs from the metrics job (05) — the recommended Path B feed — or (b) the live sampled statements
> from the samples job (06) — the Path A feed. Either way it owns the explain-table bootstrap, the
> populate→read→delete cycle, and the `dbm_type:"plan"` emission.

---

## 9. Implementation checklist

- [ ] **Spike first (gating):** run `EXPLAIN_FROM_SECTION` as a non-owner `datadog` user against a
      live `EXECUTABLE_ID`; confirm proc signature, OUT params, source arg, and grants (§1.3, §6, §7).
- [ ] `Db2ExecutionPlans` collector (`DBMAsyncJob`, `dbms="db2"`, own `ibm_db` conn) (§8).
- [ ] Explain-table bootstrap: probe → `SYSINSTALLOBJECTS('EXPLAIN','C',NULL,schema)` → swallow 42710;
      cache per-schema in `TTLCache(1000,300)`; dedicated agent explain schema (§2).
- [ ] **Path B primary** (`EXPLAIN_FROM_SECTION` by `EXECUTABLE_ID`); **Path A fallback**
      (`EXPLAIN PLAN FOR` text) only when no id / B unavailable (§1).
- [ ] Read `EXPLAIN_OPERATOR`/`EXPLAIN_STREAM`/`EXPLAIN_PREDICATE` by the 8-column join key; assemble
      operator tree (nodes from OPERATOR, edges from STREAM) (§3.1).
- [ ] Serialize to plan-JSON (Postgres-compatible keys, `float()` the `E+002` costs); `(verify)` the
      shape against the real agent obfuscator (§3.2).
- [ ] `datadog_agent.obfuscate_sql_exec_plan` (definition + `normalize=True`); `plan_signature =
      compute_exec_plan_signature(normalized)` (§3.2).
- [ ] Obfuscate statement + `query_signature` (reuse 05 §2); never ship raw SQL on the plan event (§3.3).
- [ ] `dbm_type:"plan"` payload: `ddsource:"db2"`, `ddtags` **comma-joined string**, ms timestamp,
      `db.plan.{definition,signature,collection_errors}` (§3.4).
- [ ] Parameter markers: rely on Path B; Path A → reopt/representative values + `parameterized_query`
      fallthrough (§4).
- [ ] Rate-limit: `_explained_statements_ratelimiter` (60s) by `(db,query_signature)`;
      `_seen_plans_ratelimiter` (240s) by `(query_signature,plan_signature)`; `_explain_errors_cache`
      (1d) (§5).
- [ ] **Delete-after-read** the explain row-set; dedicated schema; never write to `SYSTOOLS` (§6.2).
- [ ] Emit a plan event even on failure with a `DBExplainError`-style `collection_errors` code (§3.4, §5).
- [ ] Gate the whole feature behind its own config flag, **default disabled** until the spike passes (§7).

---

## 10. Citations

- **Authoritative Db2 behavior (live, 2026-06-15, container `db2-primary` / `TESTDB` / 12.1.4):**
  [`_research/_raw/05-explain-test.txt`](_research/_raw/05-explain-test.txt) (explain tables exist in
  `SYSTOOLS`; `EXPLAIN PLAN FOR` succeeded; `RETURN<-TBSCAN` plan with `TOTAL_COST`/`IO_COST`;
  `EXPLAIN_OPERATOR` schema + 8-column join key), and
  [`_research/db2-live-pkgcache.md`](_research/db2-live-pkgcache.md) (§3 the `SYSINSTALLOBJECTS` /
  `CREATE FUNCTION SYSTOOLS` calls in the cache; §3/§4 `EXECUTABLE_ID` stability; §5 `?`-marker
  preservation).
- **Postgres pattern this mirrors:**
  [`_research/code-postgres-dbm-samples.md`](_research/code-postgres-dbm-samples.md) (§4 EXPLAIN run +
  obfuscation/encoding, §5 caches/rate-limits, §7 parameterized-query workaround, §12 `DBExplainError`,
  §13 the Db2 translation notes that name `EXPLAIN_FROM_SECTION`).
- **Payload contract:** [`_research/code-dbm-payload-contract.md`](_research/code-dbm-payload-contract.md)
  (§4.1 plan event shape, §4.3 raw vs obfuscated, §8 field reference, §11/§12 `ddsource:"db2"`).
- **Base helpers (reuse, do not reimplement):**
  `datadog_checks_base/datadog_checks/base/utils/db/sql.py:48` (`compute_exec_plan_signature`), `:18`
  (`compute_sql_signature`), `datadog_checks_base/datadog_checks/base/utils/db/utils.py:249`
  (`obfuscate_sql_with_metadata`), `:289` (`DBMAsyncJob`/`RateLimitingTTLCache`/`ConstantRateLimiter`),
  `:237` (`default_json_event_encoding`),
  `datadog_checks_base/datadog_checks/base/checks/base.py:772` (`database_monitoring_query_sample`).
- **Sibling docs:** [`03-reference-architecture.md`](03-reference-architecture.md),
  [`05-dbm-query-metrics.md`](05-dbm-query-metrics.md),
  [`06-dbm-query-samples-activity.md`](06-dbm-query-samples-activity.md),
  [`09-implementation-architecture.md`](09-implementation-architecture.md),
  [`10-implementation-phases.md`](10-implementation-phases.md),
  [`11-testing-and-validation.md`](11-testing-and-validation.md),
  [`12-risks-open-questions.md`](12-risks-open-questions.md).
