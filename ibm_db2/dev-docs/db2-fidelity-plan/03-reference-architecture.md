# 03 — Reference Architecture: How a High-Fidelity DBM Integration Is Built

**What this is.** The blueprint. This doc explains *how* a postgres/mysql/sqlserver-grade Datadog
Database Monitoring (DBM) integration is structured — the shared `datadog_checks_base` framework it
builds on, the per-feature collector pattern, the JSON payload contracts each collector emits, and how
an existing metrics-only engine bolts DBM on. Everything here is what the Db2 work in
[`09-implementation-architecture`](09-implementation-architecture.md) and
[`10-implementation-phases`](10-implementation-phases.md) will mirror. The feature-specific docs
(`05`–`08`) drill into one collector each; this doc is the map that ties them together.

**Audience.** An engineer or implementing AI agent who already knows the postgres/mysql integrations —
`pg_stat_statements`, `DBMAsyncJob`, the `dbm-*` tracks, obfuscation/signatures — but knows little
about IBM Db2. Db2 specifics are introduced inline; the deep Db2 primer is
[`01-db2-monitoring-primer`](01-db2-monitoring-primer.md), and the current-state audit is
[`02-current-integration-audit`](02-current-integration-audit.md).

**Why a blueprint matters here.** There is **no single "DBM check" base class** to subclass and be
done. Each integration *assembles* the framework pieces below into a check class plus a set of
background collectors. SQL Server is the canonical example of adding DBM to a pre-existing
metrics-only check (exactly Db2's situation), so §6 treats it as the template. Get the assembly right
once and every feature slots into the same skeleton.

**Sourcing.** Every claim is grounded in the `_research/*.md` code studies, cited by file path.
The load-bearing files are:
`_research/code-base-framework.md` (the framework API inventory),
`_research/code-dbm-payload-contract.md` (the JSON envelope contract),
`_research/code-sqlserver-dbm-template.md` (the structural template),
`_research/code-postgres-dbm-statements.md`, `_research/code-postgres-dbm-samples.md`,
`_research/code-postgres-dbm-metadata-schemas.md`, `_research/code-mysql-dbm.md` (per-feature
collectors), and `_research/code-integration-scaffolding.md` (repo conventions). Where those files
flag something as unverified for Db2, this doc repeats the flag rather than papering over it.

---

## 0. The shape of a DBM integration in one diagram

A high-fidelity integration splits cleanly into **two largely independent halves**
(`_research/code-base-framework.md` lines 9-18):

```
                          IbmDb2Check(DatabaseCheck)            <-- the orchestrator (§5)
                          __NAMESPACE__ = "ibm_db2"
                          dbms = "db2"
        ┌──────────────────────────┴───────────────────────────────────┐
        │                                                                │
  HALF 1: PLAIN METRICS (synchronous)              HALF 2: DBM FEATURES (background threads)
  runs inline every check()                        each is a DBMAsyncJob with its own thread + connection
        │                                                                │
  QueryManager / Query / transformers              Db2StatementMetrics   -> dbm-metrics + dbm-samples(fqt)
  (or hand-rolled self.gauge(...))                 Db2StatementSamples   -> dbm-samples(plan) + dbm-activity
  -> standard ibm_db2.* metrics                    Db2Metadata           -> dbm-metadata(settings) + schemas
                                                   (Health)              -> dbm-health
                                                   + database_instance event (registration) -> dbm-metadata
```

Half 1 is what `ibm_db2` ships today (49 metrics, hand-rolled `self.gauge` — see
[`02-current-integration-audit`](02-current-integration-audit.md)) and what
[`04-metrics-fidelity-plan`](04-metrics-fidelity-plan.md) widens. Half 2 is entirely net-new and is
the headline of this plan. The two halves share only the check object: its identity properties, tag
manager, connection helpers, and version cache. The rest of this doc is mostly about Half 2.

**Five event-platform tracks** carry all DBM data (`_research/code-dbm-payload-contract.md` lines
49-51): `dbm-metrics`, `dbm-samples`, `dbm-activity`, `dbm-metadata`, `dbm-health`. These are *not*
standard Agent metrics — they ride the event-platform forwarder, are not declared in `metadata.csv`,
and are not a `dataflows.yaml` entry (`_research/code-integration-scaffolding.md` §11.6-11.7). The
backend routes each track by name, then sub-discriminates within a track by a `dbm_type` or `kind`
field inside the JSON.

---

## 1. The shared `datadog_checks_base` framework

Everything lives under
`/home/bits/dd/integrations-core/datadog_checks_base/datadog_checks/base/utils/db/`
(`_research/code-base-framework.md` §A). Import these — **do not reimplement them**; the signatures
(especially the hashing) must match what the backend expects.

### 1.1 `DatabaseCheck` — the base class to subclass

`datadog_checks/base/checks/db.py` defines `DatabaseCheck(AgentCheck)`
(`_research/code-dbm-payload-contract.md` lines 30-47). It provides the five `database_monitoring_*`
submitters (§3.1) and declares the abstract **identity properties** every payload reads. New DBM
integrations subclass `DatabaseCheck`; `ibm_db2` currently subclasses bare `AgentCheck`
(`_research/code-sqlserver-dbm-template.md` line 173) and must switch. The identity contract
(`_research/code-base-framework.md` §I, `_research/code-dbm-payload-contract.md` §2):

| Property | Becomes payload field | Db2 implementation |
|---|---|---|
| `reported_hostname -> str\|None` | `host` (null if `exclude_hostname`) | `resolve_db_host()`-derived, override-able |
| `database_identifier -> str` | `database_instance` | `Template` rendered from tags; default `$resolved_hostname` |
| `dbms -> str` | `dbms` / `ddsource` | **override to `"db2"`** (default is classname `"ibmdb2check"`) |
| `dbms_version -> str` | `db2_version` / `dbms_version` | reuse existing `get_version()` (`ibm_db2.py:96-119`) |
| `tags -> list[str]` | `tags` | `tag_manager.get_tags()` |
| `cloud_metadata -> dict` | `cloud_metadata` | `{aws,azure,gcp}` (empty dicts on-prem, but **keys must exist**) |

Why this matters for Db2 specifically: `dbms` defaults to `self.__class__.__name__.lower()`
(`_research/code-dbm-payload-contract.md` line 584) which would yield the wrong source string, so the
explicit override to `"db2"` is mandatory — the backend keys DBM ingestion on this. The exact source
string (`db2` vs `ibm_db2`) is flagged unverified in `00-README`/`99`; resolve it against the backend
before shipping.

### 1.2 Plain-metrics engine: `QueryManager` / `Query` / transformers

For standard (non-DBM) metrics, the declarative path is `Query` specs run by a `QueryManager`
(`_research/code-base-framework.md` §B). A `Query` is a dict of `name`/`query`/`columns`/`extras`/
`tags`/`collection_interval`; each column maps to a submission transformer (`gauge`, `count`,
`monotonic_count`, `rate`, `tag`, `temporal_percent`, etc.). The `QueryManager` runs each query, maps
columns to `AgentCheck` submission methods, and self-throttles per-query.

**Relevance to Db2:** the current check does *not* use `QueryManager`; it hand-rolls `self.gauge(...)`
(`_research/code-base-framework.md` lines 102, 428-430). Both patterns are acceptable; the metric
breadth work in [`04-metrics-fidelity-plan`](04-metrics-fidelity-plan.md) decides whether to adopt
`QueryManager`. **This is Half 1 and is orthogonal to DBM** — none of the DBM collectors use the
transformer engine; they hand-build JSON payloads.

### 1.3 `DBMAsyncJob` — the background-collector base (the heart of Half 2)

`utils/db/utils.py:289` (`_research/code-base-framework.md` §E,
`_research/code-postgres-dbm-samples.md` §6). Every DBM feature is a subclass that overrides one
method, `run_job()`. The check calls `job.run_job_loop(tags)` once per check run; the framework owns
the threading, rate-limiting, and health.

Constructor parameters that matter (`_research/code-base-framework.md` lines 198-213):

```python
DBMAsyncJob(
  check,                       # the DatabaseCheck instance
  min_collection_interval=15,  # the MAIN check interval; loop self-stops if inactive for 2x this
  dbms="db2",                  # used in all dd.db2.async_job.* telemetry metric names
  rate_limit=1/collection_interval,   # executions/sec; loop sleeps to hold this
  run_sync=False,              # run inline (tests / very short intervals) vs background thread
  enabled=True,
  expected_db_exceptions=(),   # exception classes logged as warnings, not crashes
  shutdown_callback=None,      # e.g. close the dedicated DBM connection
  job_name="query-metrics",    # becomes a job:<name> tag
)
```

Lifecycle (`_research/code-base-framework.md` §E.2, `_research/code-mysql-dbm.md` §0):

1. `run_job_loop(tags)` is called **every main check run**. It is idempotent and non-blocking: it
   either runs `run_job()` inline (`run_sync`) or submits `_job_loop` to a shared
   `ThreadPoolExecutor(100000)` **once**, then returns. Subsequent calls just refresh `_last_check_run`
   (the heartbeat that keeps the loop alive).
2. `_job_loop` runs `run_job()` on a `ConstantRateLimiter` cadence, checking a `_cancel_event` each
   iteration. It **self-terminates** if the main check stops calling `run_job_loop` for
   `min_collection_interval * 2` seconds (emits `dd.db2.async_job.inactive_stop`).
3. The check's `cancel()` must call `job.cancel()` for every job
   (`_research/code-sqlserver-dbm-template.md` §3.4).

This means each collector runs on its **own independent cadence** in its **own thread** — query
metrics every 60s, activity every 10s, metadata every 600s — decoupled from the main check's interval,
yet kept alive by it. Crashes and missed collections auto-emit `dbm-health` events and
`dd.db2.async_job.{error,missed_collection,cancel,inactive_stop}` counts
(`_research/code-base-framework.md` §E.3).

### 1.4 `StatementMetrics` — the monotonic→delta engine

`utils/db/statement_metrics.py` (`_research/code-base-framework.md` §C,
`_research/code-postgres-dbm-statements.md` §3). Statement stat tables (pg `pg_stat_statements`, mysql
`events_statements_summary_by_digest`, mssql `sys.dm_exec_query_stats`, **Db2
`MON_GET_PKG_CACHE_STMT`**) are cumulative monotonic counters. The integration ships per-interval
*deltas*, computed by:

```python
StatementMetrics()  # holds a _previous_statements snapshot cache
.compute_derivative_rows(rows, metric_columns, key=<callable>, execution_indicators=[...]) -> list[dict]
```

Semantics (must be called **exactly once per collection run** — it mutates the cache):

- `key` = a callable returning a hashable identity for a statement across runs. Postgres uses
  `(query_signature, datname, rolname)`; mysql `(schema_name, query_signature)`. **Db2** should key
  the snapshot diff on the stable statement identity and re-merge by signature (see §5.2 and
  [`05-dbm-query-metrics`](05-dbm-query-metrics.md)).
- `metric_columns` = the cumulative counters to diff; all other columns pass through unchanged.
- **Stats-reset handling:** if *any* diffed metric goes negative for a row, the whole row is dropped
  (counter reset / cache eviction = new baseline). Zero-change rows are dropped.
- `execution_indicators` = columns that must have *increased* for the row to emit — filters phantom
  re-inserted entries. **For Db2 this is `num_exec_with_metrics`** (NOT `num_executions` — `99` flags
  the latter as a `10`-doc error; `num_exec_with_metrics` is the column that increments only when
  metrics were actually captured).
- First run of any key produces no output (becomes the baseline).

Duplicate rows sharing a key are summed before diffing. Reuse this verbatim — both pg v1 and mysql use
this exact class; pg v2 reimplements the same algorithm in `delta_detector.py` for an incremental
optimization that Db2 does not need initially.

### 1.5 SQL obfuscation, signatures, comment propagation

`utils/db/sql.py` + the obfuscation helper in `utils/db/utils.py`
(`_research/code-base-framework.md` §D, `_research/code-postgres-dbm-statements.md` §4-5):

- **`obfuscate_sql_with_metadata(query, options_json, replace_null_character=False)`** — calls the
  Agent's Go obfuscator (`datadog_agent.obfuscate_sql`) and returns
  `{'query': <obfuscated>, 'metadata': {'tables','commands','comments','procedures'}}`. **Set
  `replace_null_character=True` for Db2** (CLOB/VARCHAR text can carry embedded nulls, same reasoning
  as SQL Server). The `options` is a JSON string built from `obfuscator_options` config; its `dbms`
  field selects the dialect (`'postgres'`/`'mysql'`/`'mssql'` → **`'db2'` for Db2, if the Go
  obfuscator supports it; else a generic SQL value — flagged unverified**,
  `_research/code-base-framework.md` lines 175-177).
- **`compute_sql_signature(obfuscated_query) -> hex`** — `mmh3.hash64(..., signed=False)[0]` as
  lowercase hex. This is the `query_signature`. **It must match the APM resource hash** so DBM↔APM
  correlation works — reuse it, never reimplement (`_research/code-postgres-dbm-statements.md`
  lines 200-209).
- **`compute_exec_plan_signature(normalized_json_plan) -> hex`** — re-serializes JSON with sorted keys,
  then mmh3 hex. This is the plan `signature`; sorting makes it order-independent.
- **`default_json_event_encoding`** (`utils/db/utils.py:237`) — the `json.dumps(default=...)` encoder:
  `Decimal→float`, `datetime/date→isoformat`, `IPv4Address→str`, `bytes→utf-8`. The `ibm_db` driver
  returns `Decimal` for many numerics, so **every DBM payload must serialize through this**.
- **`sql_commenter.py`** (`generate_sql_comment`/`add_sql_comment`) — SQLCommenter injection for
  trace-to-query linking. Lower priority for a metrics-first Db2 plan; relevant later.

### 1.6 Rate-limiting / dedup caches

From `utils/db/utils.py` (`_research/code-base-framework.md` §E.4,
`_research/code-postgres-dbm-samples.md` §5):

- `ConstantRateLimiter(rate_limit_s)` — the per-job loop pacer inside `DBMAsyncJob`.
- `RateLimitingTTLCache(maxsize, ttl)` — `.acquire(key)` returns `True` at most once per `ttl` per key.
  Used for "1 plan/sample per (query, plan) per window" and "1 FQT per query per hour".
- `cachetools.TTLCache` — used for full-query-text dedup and per-DB collection-strategy caches.

### 1.7 `SchemaCollector` — the streamed schema-metadata base

`utils/db/schemas.py` (`_research/code-base-framework.md` §G,
`_research/code-postgres-dbm-metadata-schemas.md` §3). An ABC that streams `database → schemas →
tables → {columns,indexes,foreign_keys}` into chunked `dbm-metadata` events. A subclass overrides only
five members: `kind` (property), `_get_databases()`, `_get_cursor(db)`, `_get_next(cursor)`,
`_map_row(db, row)`. The base owns chunking (`payload_chunk_size`, default 10,000), the event envelope,
per-DB error isolation, the `collection_payloads_count` snapshot-completeness signal, and telemetry
(`dd.db2.schema.{time,tables_count,payloads_count}`). It is **not** itself a `DBMAsyncJob` — the
metadata job invokes it on its own interval. Detail in [`08-dbm-schemas-and-settings`](08-dbm-schemas-and-settings.md).

### 1.8 `TagManager`, `Health`, tracking

- **`TagManager`** (`utils/db/utils.py:548`, `_research/code-base-framework.md` §I.1) — key→[values]
  tag store with `set_tag`/`set_tags_from_list`/`get_tags(include_internal=, include_db=)`. Internal
  tags (`dd.internal.*`) are excluded from DBM payloads; the per-database `db:` tag is excludable for
  instance-level/metrics payloads. Instantiate with a normalizer:
  `TagManager(normalizer=lambda t: self.normalize_tag(t).lower())`.
- **`Health`** (`utils/db/health.py`, `_research/code-base-framework.md` §H) — `dbm-health` event
  emitter with cooldown. `DBMAsyncJob` drives it automatically on crashes/missed collections;
  `INITIALIZATION` is optional but cheap.
- **`tracked_method` / `tracked_query`** (`utils/tracking.py`) — decorators emitting
  `dd.<check>.<method>.{time,error,result_length}` debug metrics around collector methods.

---

## 2. The per-feature collection pattern (what each collector does, and its cadence)

Every collector follows the same skeleton: **subclass `DBMAsyncJob`; in `run_job()` query a source,
obfuscate + sign, build a JSON payload, submit it on a track.** Below is what each one does, with the
postgres/mysql/sqlserver reference and the default cadence. The Db2 source column is the plan's
proposal (live-verified in the `db2-live-*.md` research; see the feature docs for the column-level
mapping).

| Feature | Collector (pg/mysql/mssql) | Track(s) | Default cadence | Db2 source |
|---|---|---|---|---|
| **Query metrics** | `*StatementMetrics` | `dbm-metrics` + `dbm-samples`(fqt) | 10s pg/mysql, 60s mssql | `MON_GET_PKG_CACHE_STMT` |
| **Query samples + plans** | `*StatementSamples` | `dbm-samples`(plan/rqt/rqp) | 1s | `MON_CURRENT_SQL` + EXPLAIN tables |
| **Activity** | (same samples job, pg) / `*Activity` (mysql/mssql) | `dbm-activity` | 10s | `MON_CURRENT_SQL` / `MON_GET_ACTIVITY` |
| **Settings/metadata** | `*Metadata` | `dbm-metadata`(`*_configs`) | 600s | `SYSIBMADM.DBMCFG` ∪ `DBCFG` |
| **Schemas** | `*SchemaCollector` (driven by metadata job) | `dbm-metadata`(`*_databases`) | 3600s | `SYSCAT.*` |
| **Instance registration** | check-level `_send_database_instance_metadata` | `dbm-metadata`(`database_instance`) | 300s (re-emit) | check identity |
| **Health** | `Health` (auto) | `dbm-health` | on event | n/a |

### 2.1 Query metrics (`dbm-metrics`) — the delta-counters feature

Pipeline (postgres `_research/code-postgres-dbm-statements.md` §3-8, mysql `_research/code-mysql-dbm.md`
§1): query the cumulative stat table → introspect available columns (don't hard-code by version) →
obfuscate each statement, compute `query_signature`, attach `dd_tables/commands/comments` →
`compute_derivative_rows` to diff → build the `<dbms>_rows` wrapper (§3.2) and submit on `dbm-metrics`
→ emit one **FQT** event per new `(signature, db)` on `dbm-samples` (rate-limited ~1/hr). Db2 detail:
[`05-dbm-query-metrics`](05-dbm-query-metrics.md).

### 2.2 Query samples + execution plans (`dbm-samples`)

Pipeline (postgres `_research/code-postgres-dbm-samples.md` §1-8): one snapshot of the active-statement
view per loop → filter + obfuscate + sign each row → for explainable statements, run EXPLAIN (gated by
a per-query rate limiter and a per-DB collection-strategy cache) → obfuscate the plan, compute
`plan_signature` → emit a `dbm_type:"plan"` event per `(query_signature, plan_signature)` window. The
postgres collector additionally produces the activity snapshot from the same loop. Db2 plans are the
**highest-risk feature** ([`07-dbm-execution-plans`](07-dbm-execution-plans.md)): Db2 has no inline
JSON plan; plans live in EXPLAIN tables and must be assembled into a JSON tree, or read via
`EXPLAIN_FROM_SECTION` (section explain) which sidesteps the parameterized-query problem entirely
(`_research/code-postgres-dbm-samples.md` §13). Samples detail:
[`06-dbm-query-samples-activity`](06-dbm-query-samples-activity.md).

### 2.3 Activity (`dbm-activity`)

Pipeline (sqlserver `_research/code-sqlserver-dbm-template.md` §5.2, mysql `_research/code-mysql-dbm.md`
§3): query the active-session view + a connection-count aggregate → obfuscate/sign each session, drop
null fields → enforce a payload cap (row limit, pg default 3500; or byte cap `MAX_PAYLOAD_BYTES=19e6`,
mssql) keeping the longest-running → emit one `dbm_type:"activity"` event with `<dbms>_activity` (+
optional `<dbms>_connections`). Blocking-session linkage comes from a lock view
(`SYSIBMADM.MON_LOCKWAITS` for Db2). Note the live-probed caveat (`db2-live-activity.md`): fast OLTP
statements can be invisible to `MON_CURRENT_SQL` — see [`06`](06-dbm-query-samples-activity.md).

### 2.4 Settings + schemas (`dbm-metadata`)

The metadata job (`*Metadata`, a single `DBMAsyncJob`) owns *both* settings and schema collection,
ticking on the GCD of their intervals and self-throttling each sub-task
(`_research/code-postgres-dbm-metadata-schemas.md` §1, `_research/code-mysql-dbm.md` §4). Settings emit
a flat `metadata` list under a `kind:"<dbms>_configs"`/`"<dbms>_settings"` envelope; schemas delegate
to the `SchemaCollector` subclass (§1.7). **Db2 splits config across scopes** (instance `DBMCFG`,
database `DBCFG`, registry) where postgres has one flat `pg_settings` — emit one payload per scope or a
merged one. Detail: [`08-dbm-schemas-and-settings`](08-dbm-schemas-and-settings.md).

### 2.5 Instance registration — the single must-have payload

`_send_database_instance_metadata` is a **check-level** method (not a `DBMAsyncJob`), called every
`check()` run and debounced by a 1-entry TTLCache keyed on `database_identifier`
(`_research/code-sqlserver-dbm-template.md` §3.5, `_research/code-dbm-payload-contract.md` §6.1). It
emits a `kind:"database_instance"` event on `dbm-metadata` carrying **`metadata.dbm = true`**. **This
is the event that registers the host as a DBM instance in the product UI** — without it, no DBM data is
attributed and the host never appears under DBM. It is the cheapest, highest-leverage payload; ship it
first (it lands in P1, see [`10-implementation-phases`](10-implementation-phases.md)).

---

## 3. The DBM payload contracts (the JSON envelope every collector fills)

All contracts are from `_research/code-dbm-payload-contract.md`. The backend is strict about these
shapes — copy them exactly, changing only the dialect-named keys.

### 3.1 Submission API

`DatabaseCheck` exposes one helper per track; each takes a JSON **string** and forwards to the
event-platform forwarder (`_research/code-dbm-payload-contract.md` §0):

```python
check.database_monitoring_query_metrics(raw)   # -> "dbm-metrics"
check.database_monitoring_query_sample(raw)     # -> "dbm-samples"   (fqt, plan, rqt, rqp)
check.database_monitoring_query_activity(raw)    # -> "dbm-activity"
check.database_monitoring_metadata(raw)          # -> "dbm-metadata"  (database_instance, settings, schemas)
check.database_monitoring_health(raw)            # -> "dbm-health"
```

Serialize every payload with `json.dumps(event, default=default_json_event_encoding)`. A `None` payload
is silently dropped (never raises).

### 3.2 Query-metrics payload (`dbm-metrics`)

One event per collection run (`_research/code-dbm-payload-contract.md` §3). Required top-level keys:

```jsonc
{
  "host": "<reported_hostname>",
  "timestamp": <epoch_ms>,                    // time.time() * 1000, FLOAT, everywhere
  "min_collection_interval": <seconds>,
  "tags": [ ... ],                            // dd.internal.* stripped; "no-db" variant (no db: tag)
  "cloud_metadata": { "aws": {}, "azure": {}, "gcp": {} },
  "db2_version": "12.1.4",                     // <dbms>_version
  "ddagentversion": "<x.y.z>",
  "service": "<config.service>",
  "db2_rows": [ <per-statement delta row>, ... ]   // <dbms>_rows
}
```

Each row in `db2_rows`: the **delta** counters + obfuscated `query` text + `query_signature` +
`dd_tables`/`dd_commands`/`dd_comments` + the identity columns. The de-obfuscated text is stripped
before sending. **Payload is recursively bisected** to stay under `batch_max_content_size` (default
20MB, matching the Agent forwarder); a single oversized row is dropped with a warning. For Db2 the
wrapper key is `db2_rows` and the version key `db2_version` (the backend has per-dbms parsers; the row
column names must be agreed with the DBM backend — `_research/code-postgres-dbm-statements.md`
line 275).

### 3.3 FQT event (`dbm-samples`, `dbm_type:"fqt"`)

One per unique query per TTL window (`_research/code-dbm-payload-contract.md` §4.2):

```jsonc
{
  "timestamp": <ms>, "host": ..., "database_instance": "<database_identifier>",
  "ddagentversion": ..., "ddsource": "db2", "ddtags": "<comma-joined string>",
  "dbm_type": "fqt", "service": ...,
  "db": { "instance": "<db>", "query_signature": "...", "statement": "<obfuscated>",
          "metadata": {"tables": [...], "commands": [...], "comments": [...]} },
  "db2": { ...dialect-specific identity (schema/user)... }
}
```

### 3.4 Plan event (`dbm-samples`, `dbm_type:"plan"`)

The richest shape (`_research/code-dbm-payload-contract.md` §4.1,
`_research/code-postgres-dbm-samples.md` §8.1):

```jsonc
{
  "host": ..., "database_instance": ..., "dbm_type": "plan",
  "ddagentversion": ..., "ddsource": "db2", "ddtags": "<comma-joined string>",
  "timestamp": <ms>, "cloud_metadata": {...}, "service": ...,
  "network": { "client": { "ip": ..., "port": ..., "hostname": ... } },
  "db": {
    "instance": "<db>",
    "plan": { "definition": "<obfuscated JSON plan>",
              "signature": "<compute_exec_plan_signature(normalized_plan)>",
              "collection_errors": [{"code": "...", "message": "..."}] | null },
    "query_signature": "...", "resource_hash": "...",   // resource_hash == query_signature
    "statement": "<obfuscated SQL>",
    "metadata": {"tables": ..., "commands": ..., "comments": ...},
    "query_truncated": "truncated" | "not_truncated" | "unknown"
  },
  "db2": { ...engine-specific stats... }
}
```

A plan event is emitted **even when EXPLAIN fails** — `plan` fields null, `collection_errors` carries
the failure code (mirror the `DBExplainError` taxonomy, `_research/code-postgres-dbm-samples.md` §12).
`rqt`/`rqp` (raw text/plan) variants only when `collect_raw_query_statement.enabled`.

### 3.5 Activity payload (`dbm-activity`, `dbm_type:"activity"`)

```jsonc
{
  "host": ..., "database_instance": ..., "ddagentversion": ...,
  "ddsource": "db2", "dbm_type": "activity",
  "collection_interval": <s>, "ddtags": [ ... ],   // LIST here, NOT comma-string
  "timestamp": <ms>, "cloud_metadata": {...}, "service": ...,
  "db2_version": "...",
  "db2_activity": [ <active session row>, ... ],
  "db2_connections": [ <connection-count row>, ... ]
}
```

**Watch the `ddtags` quirk** (`_research/code-dbm-payload-contract.md` §4 note, §12 item 4): `ddtags`
is a **comma-joined string** in samples/plan/fqt/rqt events but a **list** in the activity event. Do
not unify them.

### 3.6 Metadata payloads (`dbm-metadata`, discriminated by `kind`)

**Instance registration** (`kind:"database_instance"`, `_research/code-dbm-payload-contract.md` §6.1) —
note the odd keys vs other payloads: `agent_version` (not `ddagentversion`), plus top-level `port`,
`database_hostname`, `ddagenthostname`, `integration_version`:

```jsonc
{
  "host": ..., "port": <port>, "database_instance": ..., "database_hostname": ...,
  "agent_version": ..., "ddagenthostname": ..., "dbms": "db2", "kind": "database_instance",
  "collection_interval": <database_instance_collection_interval>, "dbms_version": "12.1.4",
  "integration_version": "<__version__>",
  "tags": [ ... ], "timestamp": <ms>, "cloud_metadata": {...},
  "metadata": { "dbm": true, "connection_host": "<config.host>" }   // dbm:true is mandatory
}
```

**Settings** (`kind:"db2_configs"`/`"db2_settings"`) and **schemas** (`kind:"db2_databases"`) share the
envelope: `host`, `database_instance`, `agent_version`/`dbms`, `kind`, `collection_interval`,
`dbms_version`, `tags`, `timestamp`, `cloud_metadata`, and a `metadata` array. Schema events add
`collection_started_at` and, on the final chunk, `collection_payloads_count`
(`_research/code-dbm-payload-contract.md` §6.2-6.3).

### 3.7 Identity & tag rules (apply to all payloads)

- `host` = `reported_hostname` (null when `exclude_hostname`).
- `database_instance` = `database_identifier`, a `Template` rendered from tags + host/port; the stable
  de-dup key the backend uses (`_research/code-dbm-payload-contract.md` §2.3). Default token
  `$resolved_hostname`.
- `timestamp` = epoch **milliseconds** (`time.time() * 1000`) everywhere.
- **Strip `dd.internal.*` tags** from all DBM payloads; strip `db:` too for the "no-db" variant used by
  metrics/settings (`_research/code-dbm-payload-contract.md` §2.6).
- `cloud_metadata` keys (`aws`/`azure`/`gcp`) must always be present even if empty.

---

## 4. Registering as a DBM product (manifest / metadata)

**Key finding** (`_research/code-dbm-payload-contract.md` §11, `_research/code-integration-scaffolding.md`
§11.6-11.7): **there is no manifest flag that turns on DBM.** No `"dbm": true` in `manifest.json`, no
DBM rows in `metadata.csv`, no DBM `data_type` in `dataflows.yaml`. Registration is entirely a
**runtime + payload** concern:

1. Ship the `database_instance` event with `metadata.dbm = true` (§3.6) — the decisive artifact.
2. Use the correct `dbms:"db2"` / `ddsource:"db2"` strings on every track, plus the existing
   `source_type_id` (10054 for `ibm_db2`), so the backend recognizes the product.

Optional manifest parity changes (verify against `ddev validate ci`/catalog rules first): move
`manifest.json` `owner` to `database-monitoring` and add a DBM-oriented `classifier_tag`. The
internal `dd.db2.*` telemetry gauges the check emits for self-monitoring are debug-only and are *not*
part of the backend contract (so they need no `metadata.csv` rows). Scaffolding/`ddev` mechanics are in
[`09-implementation-architecture`](09-implementation-architecture.md) and
[`11-testing-and-validation`](11-testing-and-validation.md).

---

## 5. SQL Server as the canonical "DBM added to an existing engine" template

SQL Server is the closest structural analog to Db2's situation: a pre-existing metrics-only check that
later gained the full DBM suite. `_research/code-sqlserver-dbm-template.md` is the authoritative study;
this section distills what Db2 should copy.

### 5.1 Module layout to mirror

SQL Server is "a metrics-only check **plus** six independent DBM collectors, each its own module and
each a `DBMAsyncJob`" (`_research/code-sqlserver-dbm-template.md` §0-1). The minimum-viable Db2 set is
**statements + samples/activity + metadata(settings) + the `database_instance` event** — the rest
(deadlocks, agent-jobs, XE, stored-procedure metrics) are SQL-Server-specific with no clean Db2 analog
and are skipped (`_research/code-sqlserver-dbm-template.md` §0, §9 item 10). New/modified files under
`ibm_db2/datadog_checks/ibm_db2/` (`_research/code-sqlserver-dbm-template.md` §8):

| File | Mirrors | Role |
|---|---|---|
| `statements.py` | `sqlserver/statements.py` | `Db2StatementMetrics(DBMAsyncJob)` over `MON_GET_PKG_CACHE_STMT` |
| `statement_samples.py` | `postgres/statement_samples.py` | `Db2StatementSamples(DBMAsyncJob)` — samples/plans/activity |
| `metadata.py` | `sqlserver/metadata.py` | `Db2Metadata(DBMAsyncJob)` — settings (+ owns the schema collector) |
| `schemas.py` | `sqlserver/schemas.py` | `Db2SchemaCollector(SchemaCollector)` over `SYSCAT.*` (optional) |
| `config.py` | `sqlserver/config.py` | parse `dbm`, `query_metrics`, `query_activity`, `collect_settings`, identity, obfuscator |
| connection layer (in `ibm_db2.py` or new `connection.py`) | `sqlserver/connection.py` | per-job connection isolation (§5.3) |
| `health.py` | `sqlserver/health.py` | `Db2Health(Health)` (optional) |
| `const.py` | `sqlserver/const.py` | static-info cache keys + default intervals |

Plus modifying `ibm_db2.py` (subclass `DatabaseCheck`, add `__NAMESPACE__`, instantiate collectors,
gate `run_job_loop` behind `dbm_enabled`, add `cancel()`, add identity props) and the
spec/generated-config files (`_research/code-sqlserver-dbm-template.md` §8.2-8.3).

### 5.2 The orchestrator wiring (copy this skeleton)

`SQLServer(DatabaseCheck)` (`_research/code-sqlserver-dbm-template.md` §3) is the pattern:

```python
class IbmDb2Check(DatabaseCheck):
    __NAMESPACE__ = "ibm_db2"

    def __init__(self, ...):
        ...
        self.tag_manager = TagManager(normalizer=lambda t: self.normalize_tag(t).lower())
        # one attribute per collector
        self.statement_metrics = Db2StatementMetrics(self, self._config)
        self.statement_samples  = Db2StatementSamples(self, self._config)
        self.metadata           = Db2Metadata(self, self._config)

    def check(self, _):
        ... # Half 1: synchronous standard metrics
        if self._config.dbm_enabled:
            self._send_database_instance_metadata()          # registration (debounced)
            self.statement_metrics.run_job_loop(self.tag_manager.get_tags())
            self.statement_samples.run_job_loop(self.tag_manager.get_tags())
            self.metadata.run_job_loop(self.tag_manager.get_tags())

    def cancel(self):
        self.statement_metrics.cancel()
        self.statement_samples.cancel()
        self.metadata.cancel()
```

The master switch `dbm: true` (`config.py`, `is_affirmative(instance.get('dbm', False))`,
`_research/code-sqlserver-dbm-template.md` §2.1) gates the entire fan-out *and* is stamped into the
`database_instance` event as `metadata.dbm`. Per-collector config is one YAML block each
(`query_metrics`, `query_activity`, `collect_settings`, `collect_schemas`), each a dict with at least
`enabled` + `collection_interval`; each collector reads its own block in its `__init__`
(`_research/code-sqlserver-dbm-template.md` §2.2-2.3). Copy SQL Server's key names verbatim where a Db2
analog exists, so the DBM UI/docs stay consistent. Default intervals: query_metrics 60, query_activity
10, settings/schemas 600, `database_instance` re-emit 300.

### 5.3 Connection isolation — the CRITICAL Db2 adaptation

SQL Server gives each background collector its **own** raw connection, namespaced by a `key_prefix`
(`"dbm-"`, `"dbm-activity-"`, `"dbm-metadata-"`), so threads never share a driver connection object
(drivers are not thread-safe even when the module is) (`_research/code-sqlserver-dbm-template.md` §4).
It also runs `SET TRANSACTION ISOLATION LEVEL READ UNCOMMITTED` on every DBM connection so monitoring
reads never block writers.

**Db2's driver differs** (`_research/code-sqlserver-dbm-template.md` §4.6, §9): Db2 uses the `ibm_db`
C driver, which has **no cursor object** — `ibm_db.exec_immediate` returns a statement handle and you
iterate with `ibm_db.fetch_assoc`/`fetch_tuple`. So Db2 must build its **own** connection-isolation
layer mirroring SQL Server's `key_prefix` map (or open a fresh `ibm_db.connect` per job), reusing the
existing `get_connection`/`get_connection_data` (`ibm_db2.py:554-608`) but namespaced per job. Two
Db2-favourable simplifications: (1) `ibm_db.fetch_assoc` with `ATTR_CASE=CASE_LOWER` already yields
lowercase-keyed dict rows, so the `dict(zip(columns,row))` step every SQL Server collector does is
unnecessary; (2) the isolation-level analog is `SET CURRENT ISOLATION = UR` (uncommitted read) on each
DBM connection. Each job passes `shutdown_callback=self._close_db_conn` to close its connection on
teardown.

### 5.4 Static-info cache (version/edition discovery)

SQL Server caches version/edition once per day in a `static_info_cache` TTLCache and every collector
reads from it to stamp `<dbms>_version` (`_research/code-sqlserver-dbm-template.md` §3.6). Db2 should
cache the `get_version()` result (`ibm_db2.py:96-119`) the same way and expose it via `dbms_version`.
Edition/topology gating (pureScale, HADR) lives in `db2-editions-versions.md` and feeds
[`12-risks-open-questions`](12-risks-open-questions.md).

### 5.5 What Db2 must adapt rather than copy verbatim

From `_research/code-sqlserver-dbm-template.md` §9 and the live-probe research:

1. **Driver model** — statement handles, not cursors (§5.3).
2. **Obfuscator dialect** — set `obfuscator_options['dbms']` to the Db2 hint (verify support).
3. **Diff key & execution indicator** — key the snapshot on `HEX(EXECUTABLE_ID)` (stable per
   `db2-live-pkgcache.md`), re-merge by `query_signature`; execution indicator is
   **`num_exec_with_metrics`** (not `num_executions`).
4. **Payload naming** — `db2_rows`, `db2_activity`, `db2_connections`, `db2_version`, `ddsource:"db2"`,
   `dbms:"db2"`.
5. **Units** — Db2 `MON_GET_*` timings are mixed µs/ms (`db2-live-pkgcache.md`); do **not** copy
   MySQL's picosecond math or assume a single unit.
6. **Execution plans** — no inline JSON plan; assemble from EXPLAIN tables or use section explain
   (`EXPLAIN_FROM_SECTION`). Highest-risk; isolated in P3 ([`07`](07-dbm-execution-plans.md)).
7. **Activity blind spot** — `MON_CURRENT_SQL` can miss fast OLTP statements
   (`db2-live-activity.md`); design [`06`](06-dbm-query-samples-activity.md) around it.
8. **Skip** deadlocks, agent-jobs, XE, stored-procedure metrics for first fidelity.

---

## 6. How this doc connects to the rest of the plan

- The framework APIs (§1) and the orchestrator skeleton (§5.2) are realized in
  [`09-implementation-architecture`](09-implementation-architecture.md) (file-by-file design) and
  sequenced in [`10-implementation-phases`](10-implementation-phases.md) (P0→P5).
- Each per-feature pattern (§2) and payload contract (§3) is expanded into a dedicated doc:
  [`05-dbm-query-metrics`](05-dbm-query-metrics.md), [`06-dbm-query-samples-activity`](06-dbm-query-samples-activity.md),
  [`07-dbm-execution-plans`](07-dbm-execution-plans.md), [`08-dbm-schemas-and-settings`](08-dbm-schemas-and-settings.md).
- Half 1 (standard metrics, §0/§1.2) is [`04-metrics-fidelity-plan`](04-metrics-fidelity-plan.md).
- Db2 background a pg/mysql engineer needs is [`01-db2-monitoring-primer`](01-db2-monitoring-primer.md);
  the current-state baseline is [`02-current-integration-audit`](02-current-integration-audit.md).
- Testing/CI (incl. standing up Db2 12.1) is [`11-testing-and-validation`](11-testing-and-validation.md);
  open risks (obfuscator dialect, `ddsource` string, plan complexity, edition gating) are
  [`12-risks-open-questions`](12-risks-open-questions.md).

**The one-sentence blueprint:** subclass `DatabaseCheck`, give it a `TagManager` and identity
properties, add one `DBMAsyncJob` per feature each with its own isolated `ibm_db` connection, have each
`run_job()` query a `MON_GET_*`/`SYSCAT`/EXPLAIN source then obfuscate-sign-and-submit a JSON payload on
its track using the base helpers, and emit the `database_instance` event with `dbm:true` so the host
registers — then fill in the feature-specific SQL and payload rows from docs `05`–`08`.

---

## Citations (absolute paths)

- Framework inventory: `ibm_db2/dev-docs/db2-fidelity-plan/_research/code-base-framework.md`
- Payload contracts: `ibm_db2/dev-docs/db2-fidelity-plan/_research/code-dbm-payload-contract.md`
- SQL Server template: `ibm_db2/dev-docs/db2-fidelity-plan/_research/code-sqlserver-dbm-template.md`
- Query metrics: `ibm_db2/dev-docs/db2-fidelity-plan/_research/code-postgres-dbm-statements.md`
- Samples/plans/activity: `ibm_db2/dev-docs/db2-fidelity-plan/_research/code-postgres-dbm-samples.md`
- Metadata/schemas: `ibm_db2/dev-docs/db2-fidelity-plan/_research/code-postgres-dbm-metadata-schemas.md`
- MySQL collectors: `ibm_db2/dev-docs/db2-fidelity-plan/_research/code-mysql-dbm.md`
- Repo/`ddev` conventions: `ibm_db2/dev-docs/db2-fidelity-plan/_research/code-integration-scaffolding.md`
- Live-probed Db2 sources: `_research/db2-live-pkgcache.md`, `_research/db2-live-activity.md`,
  `_research/db2-config-settings.md`, `_research/db2-editions-versions.md`
- Base source (the framework itself):
  `datadog_checks_base/datadog_checks/base/{checks/db.py,checks/base.py,utils/db/{utils,statement_metrics,sql,schemas,health}.py}`
- SQL Server reference: `sqlserver/datadog_checks/sqlserver/{sqlserver,statements,activity,metadata,schemas,connection,config}.py`
</content>
</invoke>
