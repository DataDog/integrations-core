# DBM Payload Contract — Code Research (postgres / mysql / sqlserver)

Raw input for the Db2 DBM implementation plan. Reverse-engineered from the **actual** source in
`/home/bits/dd/integrations-core`. Every claim is cited with an absolute file path + line range.
Target Db2 version: **12.1** (live container 12.1.4).

> Scope note: This file documents the *payload contracts the DBM backend expects* — the event-platform
> tracks, the required top-level keys, the per-row schemas, host/instance identity resolution, and the
> manifest/metadata requirements to register a DBM product. It does **not** prescribe Db2-specific SQL
> (that belongs in the collector-design docs); it documents the *envelope* every collector must fill.

---

## 0. The submission API (how everything reaches the backend)

All DBM payloads are JSON strings submitted to the Agent's **event-platform forwarder** on one of five
named tracks. The base check exposes one helper per track.

`AgentCheck` (legacy/duplicated):
`/home/bits/dd/integrations-core/datadog_checks_base/datadog_checks/base/checks/base.py:772-817`

```python
def database_monitoring_query_sample(self, raw_event):    # track "dbm-samples"
def database_monitoring_query_metrics(self, raw_event):   # track "dbm-metrics"
def database_monitoring_query_activity(self, raw_event):  # track "dbm-activity"
def database_monitoring_metadata(self, raw_event):        # track "dbm-metadata"
def event_platform_event(self, raw_event, event_track_type):  # generic
```

`DatabaseCheck` (the modern base class that new DBM integrations should subclass):
`/home/bits/dd/integrations-core/datadog_checks_base/datadog_checks/base/checks/db.py:10-54`

```python
class DatabaseCheck(AgentCheck):
    def database_monitoring_query_sample(self, raw_event: str):    -> "dbm-samples"
    def database_monitoring_query_metrics(self, raw_event: str):   -> "dbm-metrics"
    def database_monitoring_query_activity(self, raw_event: str):  -> "dbm-activity"
    def database_monitoring_metadata(self, raw_event: str):        -> "dbm-metadata"
    def database_monitoring_health(self, raw_event: str):          -> "dbm-health"
    # abstract identity properties the base relies on:
    @property reported_hostname -> str | None
    @property database_identifier -> str
    @property dbms -> str            # default: class name lowercased
    @property dbms_version -> str
    @property tags -> list[str]
    @property cloud_metadata -> dict
```

**Track names (exact strings):** `dbm-samples`, `dbm-metrics`, `dbm-activity`, `dbm-metadata`,
`dbm-health`. Defined in `base.py:777-798` and `db.py:12-24`. The backend routes/parses each track
differently; the `dbm_type` / `kind` field inside the JSON further discriminates sub-types within a track.

**Serialization:** Every payload is `json.dumps(event, default=default_json_event_encoding)`.
The encoder coerces non-JSON types — Decimal→float, date/datetime→ISO-8601 string, IPv4Address→str,
bytes→utf-8 str; anything else raises `TypeError`.
`/home/bits/dd/integrations-core/datadog_checks_base/datadog_checks/base/utils/db/utils.py:237-246`
Use `from datadog_checks.base.utils.serialization import json` (orjson wrapper; may return bytes —
`event_platform_event` handles bytes/str both, `base.py:811-817`).

**A `None` payload is silently dropped** (`base.py:774-775` etc.) — never raises.

---

## 1. Track-to-event-type matrix (what each `dbm_type`/`kind` means)

| Track | Discriminator key | Values seen in code | Builder |
|---|---|---|---|
| `dbm-metrics` | (none — the wrapper *is* the type) | per-statement metrics payload with `<dbms>_rows` | pg `statements.py`, mysql `statements.py` |
| `dbm-samples` | `dbm_type` | `plan`, `fqt`, `rqt`, `rqp` | pg/mysql/sqlserver `statement_samples.py`/`activity.py` |
| `dbm-activity` | `dbm_type` = `activity` | `activity` | `statement_samples.py` / `activity.py` |
| `dbm-metadata` | `kind` | `database_instance`, `pg_settings`, `pg_extension`, `pg_databases` (schemas) | `postgres.py`, `metadata.py`, `schemas.py` |
| `dbm-health` | `name`+`status` | `initialization`/`unknown_error`/`missed_collection` × `ok`/`warning`/`error` | `utils/db/health.py` |

`dbm_type` legend (samples track):
- `plan` = obfuscated execution-plan sample event (`_collect_plan_for_statement`).
- `fqt` = "full query text" — emits the de-obfuscated/normalized statement once per (signature, db, role), rate-limited.
- `rqt` = "raw query text" — emitted only when `collect_raw_query_statement` is on.
- `rqp` = "raw query plan" — raw (un-obfuscated) plan, only when raw-statement collection on.

---

## 2. Host / instance identity (CRITICAL — shared by every payload)

These properties are computed once on the **check** object and injected into every payload. Db2 must
implement equivalents. Source: `/home/bits/dd/integrations-core/postgres/datadog_checks/postgres/postgres.py`.

### 2.1 `reported_hostname` (the `host` field)
`postgres.py:680-685`
```python
@property
def reported_hostname(self):
    if self._config.exclude_hostname:   # opt-out: send host=None for "headless"/serverless
        return None
    return self.resolved_hostname
```

### 2.2 `resolved_hostname`
`postgres.py:687-695` — config override wins, else DNS-resolve the DB host:
```python
if self._config.reported_hostname:
    self._resolved_hostname = self._config.reported_hostname
else:
    self._resolved_hostname = self.resolve_db_host()
```
`resolve_db_host` logic (`utils/db/utils.py:181-212`):
- host ending `.local` → returned verbatim.
- localhost / 127.0.0.1 / `_is_local_db_host` → **agent hostname** (`datadog_agent.get_hostname()`).
- else `socket.gethostbyname(db_host)`; if it equals the agent host's IP → agent hostname; otherwise
  return the configured db_host (falls back to db_host on any DNS failure).

### 2.3 `database_identifier` (the `database_instance` field)
`postgres.py:697-717` — a **template** rendered from the instance tags + host/port. This is the stable
key the backend uses to de-dup instances:
```python
template = Template(self._config.database_identifier.template)  # default template e.g. "$resolved_hostname"
# build tag_dict from "key:value" tags (sorted, comma-joined on dup keys), then add:
tag_dict['resolved_hostname'] = self.resolved_hostname
tag_dict['host'] = str(self._config.host)
tag_dict['port'] = str(self._config.port)
self._database_identifier = template.safe_substitute(**tag_dict)
```
Postgres default template token: `resolved_hostname`. Db2 should default `database_identifier.template`
to `$resolved_hostname` (or a host:port composite) and allow override.

### 2.4 `database_hostname`, `agent_hostname`
`postgres.py:739-750`
```python
@property agent_hostname    -> datadog_agent.get_hostname()      # the DD Agent's own host
@property database_hostname -> self.resolve_db_host()            # the DB server host
```

### 2.5 `cloud_metadata`
`postgres.py:719-727` — always `{"aws": {...}, "azure": {...}, "gcp": {...}}` (each from config
`model_dump()`). Present on metrics/samples/activity/metadata payloads. For Db2 (on-prem first) these
can be empty dicts but the **key must exist**.

### 2.6 Tag conventions baked into identity
`postgres.py:258-296`:
- `database_hostname:<host>` and `database_instance:<identifier>` are added to **every** metric/event.
- `dd.internal.resource:database_instance:<identifier>` — backend uses this to fan out instance tags.
- Cloud resource tags: `dd.internal.resource:aws_rds_instance:<endpoint>`,
  `gcp_sql_database_instance:<project>:<instance>`, azure variants.
- DBM payloads **strip** `dd.internal.*` tags before sending
  (`statements.py:236`, `statement_samples.py:474`, `metadata.py:165`):
  `self.tags = [t for t in self._tags if not t.startswith('dd.internal')]`
  and a `_tags_no_db` variant strips `db:` too (the backend re-adds `db:` from each row's instance).

---

## 3. `dbm-metrics` — per-statement (query) metrics payload

### 3.1 Postgres wrapper
`/home/bits/dd/integrations-core/postgres/datadog_checks/postgres/statements.py:252-297`
```python
payload_wrapper = {
    'host':                   self._check.reported_hostname,
    'timestamp':              time.time() * 1000,            # epoch ms (float)
    'min_collection_interval': self._metrics_collection_interval,  # seconds
    'tags':                   self._tags_no_db,              # list[str], no db:, no dd.internal
    'cloud_metadata':         self._check.cloud_metadata,
    'postgres_version':       payload_pg_version(self._check.version),
    'ddagentversion':         datadog_agent.get_version(),
    'service':                self._config.service,
}
# then, per chunk:
payload["postgres_rows"] = current   # list of metric rows
```
Note: postgres metrics wrapper does **not** carry `database_instance` or `ddsource` — instance attribution
on the metrics track comes from `tags` + the `dd.internal.resource:database_instance` tag.

### 3.2 MySQL wrapper (same contract, different keys)
`/home/bits/dd/integrations-core/mysql/datadog_checks/mysql/statements.py:164-176`
```python
payload = {
    'host':                    self._check.resolved_hostname,
    'timestamp':               time.time() * 1000,
    'mysql_version':           self._check.version.version + '+' + self._check.version.build,
    'mysql_flavor':            self._check.version.flavor,
    'ddagentversion':          datadog_agent.get_version(),
    'min_collection_interval': self._metric_collection_interval,
    'tags':                    tags,                         # dd.internal stripped
    'cloud_metadata':          self._config.cloud_metadata,
    'service':                 self._config.service,
    'mysql_rows':              rows,
}
```

### 3.3 Generalized contract for Db2
Required top-level keys: `host`, `timestamp` (epoch ms), `min_collection_interval` (s),
`tags` (list), `cloud_metadata`, `ddagentversion`, `service`, a DBMS-version key, and a
**`<dbms>_rows`** array holding the per-statement rows. For Db2 use `db2_rows` (mirror the
`<product>_rows` naming convention; backend keys off the track + the `*_rows` field).
Add a `db2_version` key.

### 3.4 Per-row schema (the metric rows)
Rows are produced by obfuscation/normalization, then **first-derivative** diffing against the previous
run (monotonic counters → per-interval deltas). The normalization step (postgres
`statements.py:522-546`) attaches:
- `query` — obfuscated SQL (the original raw text is replaced).
- `query_signature` — `compute_sql_signature(obfuscated_query)`
  (`datadog_checks.base.utils.db.sql.compute_sql_signature`).
- `dd_tables`, `dd_commands`, `dd_comments` — from obfuscator metadata.
- plus the raw stat columns from the source view (calls, rows, exec time, blocks, etc.).

Derivative computation: `StatementMetrics.compute_derivative_rows`
`/home/bits/dd/integrations-core/datadog_checks_base/datadog_checks/base/utils/db/statement_metrics.py:25-123`.
- `key` = unique row id across runs. Postgres uses `(query_signature, datname, rolname)`
  (`statements.py:137-142`); Db2 should use `(query_signature, <db/schema>, <user>)`.
- `metrics` = set of monotonic columns to diff.
- `execution_indicators` = columns that must increase to count the query as "executed"
  (postgres: `['calls']`). Negative diff anywhere ⇒ stats reset ⇒ whole row dropped; zero change ⇒ dropped.
- Duplicate rows (same key) are summed before diffing (`_merge_duplicate_rows`, lines 126-150).

**Payload chunking / size limit:** `statements.py:271-297` — recursively bisects `rows` so each serialized
payload stays under `batch_max_content_size`. A single row over the limit is **dropped with a warning**.
The default must match the Agent forwarder's `database_monitoring.metrics.batch_max_content_size`
(see comment `statements.py:164-171`: must not exceed the agent default or the backend rejects the payload).

---

## 4. `dbm-samples` — execution-plan sample events (`dbm_type: "plan"`)

### 4.1 Postgres plan event (the canonical, richest shape)
`/home/bits/dd/integrations-core/postgres/datadog_checks/postgres/statement_samples.py:901-965`
```python
obfuscated_plan_event = {
    "host":             self._check.reported_hostname,
    "database_instance": self._check.database_identifier,
    "dbm_type":         "plan",
    "ddagentversion":   datadog_agent.get_version(),
    "ddsource":         "postgres",                 # <-- product source string
    "ddtags":           ",".join(self._dbtags(row['datname'])),   # COMMA-JOINED STRING
    "timestamp":        time.time() * 1000,
    "cloud_metadata":   self._check.cloud_metadata,
    "service":          self._config.service,
    "network": {
        "client": {"ip": ..., "port": ..., "hostname": ...},
    },
    "db": {
        "instance":        row['datname'],
        "plan": {
            "definition":        obfuscated_plan,        # obfuscated JSON plan string
            "signature":         plan_signature,         # compute_exec_plan_signature(normalized_plan)
            "collection_errors": collection_errors,      # [{"code":..., "message":...}] or None
            # when raw collection on: "raw_signature": raw_plan_signature
        },
        "query_signature": row['query_signature'],
        "resource_hash":   row['query_signature'],       # = query_signature for pg
        "application":     row.get('application_name'),
        "user":            row['usename'],
        "statement":       row['statement'],             # obfuscated SQL
        "metadata": {"tables":..., "commands":..., "comments":...},
        "query_truncated": <"truncated"|"not_truncated"|"unknown">,
    },
    "postgres": { ...all activity row cols except excluded keys... },
}
# optional duration/timestamp override for idle txns (lines 943-953)
```
Key signatures:
- `query_signature` = `compute_sql_signature(obfuscated_sql)`.
- `plan_signature` = `compute_exec_plan_signature(normalized_plan)`.
- `resource_hash` = APM resource match (pg: equals query_signature).
Imports: `from datadog_checks.base.utils.db.sql import compute_exec_plan_signature, compute_sql_signature`
(`statement_samples.py:31`).
Plan obfuscation: `datadog_agent.obfuscate_sql_exec_plan(raw_plan, normalize=True)` and `(raw_plan)`
(`statement_samples.py:891-892`).

**Important `ddtags` quirk:** in **sample/plan/fqt/rqt** events `ddtags` is a **comma-joined string**;
in the **activity** event `ddtags` is a **list** (see §5). Match per type exactly.

### 4.2 FQT event (`dbm_type: "fqt"`) — full query text
Postgres `statement_samples.py` analog in `statements.py:548-581`; mysql `statements.py:367-393`:
```python
{
  "timestamp": ..., "host": reported_hostname, "database_instance": database_identifier,
  "ddagentversion": ..., "ddsource": "<dbms>", "ddtags": "<comma-joined>",
  "dbm_type": "fqt", "service": ...,
  "db": {"instance": <db>, "query_signature": ..., "statement": <obfuscated sql>,
         "metadata": {"tables":..,"commands":..,"comments":..}},
  "<dbms>": { ...db-specific identity, e.g. datname/rolname or schema... },
}
```
Rate-limited to N samples/hour/query via `_full_statement_text_cache` (TTLCache).
(postgres metrics path emits FQT; mysql metrics path emits FQT — emitted alongside metrics, not samples.)

### 4.3 RQT / RQP (raw text / raw plan)
Only when `collect_raw_query_statement.enabled`. RQT: `statement_samples.py:616-642`
(adds `db.raw_query_signature` + raw `statement`). RQP: `statement_samples.py:957-964`
(deep-copies the plan event, sets `dbm_type="rqp"`, `db.statement`=raw sql,
`db.plan.definition`=raw plan, `db.plan.raw_signature`).

---

## 5. `dbm-activity` — active-session snapshot (`dbm_type: "activity"`)

### 5.1 Postgres
`/home/bits/dd/integrations-core/postgres/datadog_checks/postgres/statement_samples.py:989-1011`
```python
event = {
    "host":               self._check.reported_hostname,
    "database_instance":  self._check.database_identifier,
    "ddagentversion":     datadog_agent.get_version(),
    "ddsource":           "postgres",
    "dbm_type":           "activity",
    "collection_interval": self._activity_coll_interval,   # seconds
    "ddtags":             self._tags_no_db,                 # LIST (not comma-joined here)
    "timestamp":          time.time() * 1000,
    "cloud_metadata":     self._check.cloud_metadata,
    "service":            self._config.service,
    "postgres_activity":    active_sessions,                # list of per-session dicts
    "postgres_connections": active_connections,            # list of connection-count dicts
}
```

### 5.2 SQL Server (confirms the cross-DBMS shape, incl. version fields)
`/home/bits/dd/integrations-core/sqlserver/datadog_checks/sqlserver/activity.py:463-480`
```python
{
  "host":..., "database_instance":..., "ddagentversion":..., "ddsource":"sqlserver",
  "dbm_type":"activity", "collection_interval":..., "ddtags": <list>, "timestamp":...,
  "sqlserver_version":..., "sqlserver_engine_edition":..., "cloud_metadata":..., "service":...,
  "sqlserver_activity": active_sessions,
  "sqlserver_connections": active_connections,
}
```

### 5.3 MySQL
`/home/bits/dd/integrations-core/mysql/datadog_checks/mysql/activity.py:392-402` — same skeleton with
`mysql_activity` / and (per grep) a connections analog.

### 5.4 Generalized contract for Db2
Top-level: `host`, `database_instance`, `ddagentversion`, `ddsource:"db2"`, `dbm_type:"activity"`,
`collection_interval` (s), `ddtags` (**list**), `timestamp` (ms), `cloud_metadata`, `service`,
**`db2_activity`** (list of active sessions), and optionally **`db2_connections`** (list of
connection-count rows). Add a `db2_version` key (mirror sqlserver_version).

### 5.5 Per-session row schema (the activity rows)
Postgres builds active sessions by filtering `pg_stat_activity` rows
(`statement_samples.py:570-596`, `_create_activity_event` lines 989-996):
- drop sessions that are idle (`state == 'idle'`) unless backend_type != client backend.
- **strip all null-valued keys** and the raw `query` key from each row
  (`row = {k:v for k,v in row.items() if v is not None and k != 'query'}`).
- add `query_truncated` (`truncated`/`not_truncated`/`unknown`), and `statement` (obfuscated; falls
  back to `"ERROR: failed to obfuscate"`).
- each row already carries `query_signature`, `dd_tables/commands/comments`, plus the raw activity columns.
Row cap: `payload_row_limit` (postgres default **3500**; conf example line 562). SQL Server caps by
**bytes** instead: `MAX_PAYLOAD_BYTES = 19e6` and drops sorted-tail rows over the limit
(`sqlserver/activity.py:31, 275-298`). Either approach is acceptable; pick one and warn on truncation.

Connections rows (postgres `PG_ACTIVE_CONNECTIONS_QUERY`, `statement_samples.py:114-124`):
`{application_name, state, usename, datname, connections:<count>}`. SQL Server analog
(`activity.py:35-44`): `{user_name, connections, status, database_name}`.

---

## 6. `dbm-metadata` — instance registration, settings, extensions, schemas

This track carries multiple sub-types, discriminated by **`kind`**. All share host/instance identity.

### 6.1 `kind: "database_instance"` — the registration / heartbeat event (MOST IMPORTANT for DBM enablement)
`/home/bits/dd/integrations-core/postgres/datadog_checks/postgres/postgres.py:1198-1221`
```python
event = {
    "host":                self.reported_hostname,
    "port":                self._config.port,
    "database_instance":   self.database_identifier,
    "database_hostname":   self.database_hostname,
    "agent_version":       datadog_agent.get_version(),      # NB key is "agent_version", not ddagentversion
    "ddagenthostname":     self.agent_hostname,              # the Agent's own hostname
    "dbms":                "postgres",                       # <-- product identifier
    "kind":                "database_instance",
    "collection_interval": self._config.database_instance_collection_interval,
    "dbms_version":        self.dbms_version,
    "integration_version": __version__,
    "tags":                [t for t in self._non_internal_tags if not t.startswith('db:')],
    "timestamp":           time() * 1000,
    "cloud_metadata":      self.cloud_metadata,
    "metadata": {
        "dbm":             self._config.dbm,                 # bool: is DBM enabled for this instance
        "connection_host": self._config.host,
    },
}
```
- Emitted **once per `database_identifier`** per agent lifetime, debounced by `_database_instance_emitted`
  dict (`postgres.py:1199-1220`). Re-sent each check run via `_send_database_instance_metadata`
  (`postgres.py:1267`) but the backend/submitter debounces by `collection_interval`.
- This is the event that **registers the instance in the DBM product UI**. Without it the host won't
  show up as a DBM instance. `metadata.dbm` must be `true`.
- **Note the two odd keys vs. other payloads:** here it's `agent_version` (not `ddagentversion`) and
  there is an extra top-level `ddagenthostname` + `port` + `database_hostname` + `integration_version`.

### 6.2 `kind: "pg_settings"` and `kind: "pg_extension"`
`/home/bits/dd/integrations-core/postgres/datadog_checks/postgres/metadata.py:176-226`
```python
event = {
    "host":..., "database_instance":..., "agent_version": datadog_agent.get_version(),
    "dbms": "postgres",
    "kind": "pg_settings",          # or "pg_extension"
    "collection_interval": <s>,
    "dbms_version": payload_pg_version(...),
    "tags": self._tags_no_db,
    "timestamp": time.time()*1000,
    "cloud_metadata":...,
    "metadata": <list of settings/extensions dicts>,   # array of objects
}
```
Db2 equivalents would be `kind: "db2_settings"` / `db2_<config>` carrying `dbm.cfg`/`db cfg`/registry rows.
These are **optional** for first-fidelity; `database_instance` is the mandatory one.

### 6.3 `kind: "pg_databases"` — schema/table metadata (the schema collector)
Base collector: `/home/bits/dd/integrations-core/datadog_checks_base/datadog_checks/base/utils/db/schemas.py:135-163`
```python
base_event = {
    "host":                 self._check.reported_hostname,
    "database_instance":    self._check.database_identifier,
    "kind":                 self.kind,                  # subclass returns e.g. "pg_databases"
    "agent_version":        datadog_agent.get_version(),
    "collection_interval":  self._config.collection_interval,
    "dbms":                 self._check.dbms,
    "dbms_version":         str(self._check.dbms_version),
    "tags":                 self._check.tags,
    "cloud_metadata":       self._check.cloud_metadata,
    "collection_started_at": self._collection_started_at,  # ms
}
# per flushed chunk (maybe_flush, lines 150-163):
event["timestamp"] = now_ms()
event["metadata"]  = self._queued_rows                 # array of database objects
# on the LAST chunk only:
event["collection_payloads_count"] = <int>             # snapshot completeness signal
```
- Postgres `kind` = `"pg_databases"` (`postgres/schemas.py:204-205`).
- Chunked at `payload_chunk_size` (default **10_000** rows, `schemas.py:39`); default
  `collection_interval` **3600s** (`schemas.py:38`).
- The `collection_payloads_count` on the final payload lets the backend know it has received the whole
  snapshot. Db2's schema collector (if implemented) **must** subclass `SchemaCollector` and only override
  `kind`, `_get_databases`, `_get_cursor`, `_get_next`, `_map_row` (lines 165-204).

---

## 7. `dbm-health` — agent/collector health events

`/home/bits/dd/integrations-core/datadog_checks_base/datadog_checks/base/utils/db/health.py:56-135`
```python
self.check.event_platform_event(
    json.dumps({
        'timestamp':       time.time()*1000,
        'version':         1,
        'check_id':        self.check.check_id,
        'category':        <__NAMESPACE__ or classname.lower()>,   # e.g. "postgres"
        'name':            <HealthEvent>,    # initialization | unknown_error | missed_collection
        'status':          <HealthStatus>,   # ok | warning | error
        'tags':            tags or [],
        'ddagentversion':  datadog_agent.get_version(),
        'ddagenthostname': datadog_agent.get_hostname(),
        'data':            data,             # arbitrary JSON-serializable dict
    }),
    "dbm-health",
)
```
- `HealthEvent` enum: `initialization`, `unknown_error`, `missed_collection` (lines 29-37).
- `HealthStatus` enum: `ok`, `warning`, `error` (lines 39-46).
- Cooldown de-dup via TLRUCache keyed by `category|name|status[|values]` (lines 94-101);
  `DEFAULT_COOLDOWN = 300s`.
- `submit_exception_health_event` auto-fills `{file,line,function,exception_type}` from the traceback
  (lines 120-134).
- Postgres subclasses it: `postgres/health.py` (`PostgresHealth(Health)`, `PostgresHealthEvent`).
- **Optional** for first-fidelity but cheap; the `initialization` event is resent each check run
  (`postgres.py:1231-1232`).

---

## 8. Standard field reference (copy-paste contract)

| Field | Type | Meaning | Present on |
|---|---|---|---|
| `host` | str \| null | `reported_hostname` (null if `exclude_hostname`) | all |
| `database_instance` | str | `database_identifier` template result | samples, activity, metadata, schemas |
| `database_hostname` | str | resolved DB server host | database_instance event |
| `ddagenthostname` | str | the DD Agent's own hostname | database_instance, health |
| `ddagentversion` / `agent_version` | str | `datadog_agent.get_version()` (key name varies! see §6.1) | all |
| `integration_version` | str | check `__version__` | database_instance event |
| `ddsource` | str | product source string (`postgres`/`mysql`/`sqlserver` → `db2`) | samples, activity |
| `dbms` | str | product id (`postgres`...→`db2`) | metadata/schemas |
| `dbm_type` | str | `plan`/`fqt`/`rqt`/`rqp`/`activity` | samples, activity |
| `kind` | str | `database_instance`/`pg_settings`/`pg_extension`/`pg_databases` | metadata, schemas |
| `<dbms>_version` | str | DB version string | metrics, activity, db_instance, schemas (`dbms_version`) |
| `timestamp` | float | epoch **milliseconds** (`time.time()*1000`) | all |
| `collection_interval` / `min_collection_interval` | number | seconds | per type |
| `tags` | list[str] | dd.internal stripped; db:/no-db variants per type | metrics, activity(metadata), db_instance |
| `ddtags` | str (samples) / list (activity) | **comma-joined** in samples, **list** in activity | samples vs activity |
| `cloud_metadata` | dict | `{aws,azure,gcp}` | most |
| `service` | str | `config.service` | metrics, samples, activity |
| `<dbms>_rows` | list | metric rows | metrics |
| `<dbms>_activity` | list | active sessions | activity |
| `<dbms>_connections` | list | connection counts | activity |
| `metadata` | list/dict | settings/extensions/schema objects (or `{dbm,connection_host}`) | metadata |

`payload_pg_version` style helper (postgres `util.py`) builds the version string; Db2 needs a
`payload_db2_version` returning e.g. `"12.1.4"`.

---

## 9. Async-job framework (how collectors are scheduled)

All four collectors subclass **`DBMAsyncJob`**
(`/home/bits/dd/integrations-core/datadog_checks_base/datadog_checks/base/utils/db/utils.py:289+`).
Constructor args used by postgres (`statements.py:148-159`, `statement_samples.py:148-164`,
`metadata.py:104-115`):
- `check`, `run_sync` (bool), `enabled` (bool), `min_collection_interval`, `dbms="postgres"`,
  `rate_limit=1/collection_interval`, `job_name="query-metrics"|"query-samples"|"database-metadata"`,
  `expected_db_exceptions=(...)`.
- `run_job()` is the override; it strips `dd.internal` tags into `self.tags` and computes `_tags_no_db`,
  then does the collection.

Db2 should create one DBMAsyncJob per concern (metrics, samples/activity, metadata) and wire them from
the check's `check()` method, gated by config `enabled` flags.

---

## 10. Config surface the backend/agent expect (defaults to mirror)

From postgres config models + conf example
(`postgres/datadog_checks/postgres/config_models/instance.py`,
`postgres/datadog_checks/postgres/data/conf.yaml.example`):

- Top-level `dbm: bool` (default false) — master DBM switch; sets `metadata.dbm` in the
  database_instance event. **Required** to turn the host into a DBM instance.
- `query_metrics`: `enabled`, `collection_interval` (default **10s**), `run_sync`,
  `batch_max_content_size`, `full_statement_text_cache_max_size`,
  `full_statement_text_samples_per_hour_per_query`, `pg_stat_statements_max_warning_threshold`.
- `query_samples`: `enabled`, `collection_interval` (default **1s**), `samples_per_hour_per_query`
  (default **15**), `explained_queries_per_hour_per_query`, `seen_samples_cache_maxsize`,
  `explain_parameterized_queries`, `run_sync`.
- `query_activity`: `enabled`, `collection_interval` (default **10s**), `payload_row_limit`
  (default **3500**).
- `collect_settings` / `collect_schemas` / `collect_column_statistics`: each `enabled`,
  `collection_interval` (settings/schemas default **600**/**3600**).
- `database_instance_collection_interval` (default **1800s**, see defaults.py:59) — how often the
  database_instance event is re-emitted.
- `reported_hostname`, `exclude_hostname`, `database_identifier.template`, `service`, `tags`,
  `min_collection_interval` (default 15), `collect_raw_query_statement.enabled`,
  `obfuscator_options` (collect_tables/collect_metadata/collect_commands/keep_dollar_quoted_func, etc.),
  cloud blocks `aws`/`azure`/`gcp`.

Obfuscator options are serialized and passed to `datadog_agent.obfuscate_sql(query, options)` /
`obfuscate_sql_with_metadata` (`utils/db/utils.py:249-289`). Postgres sets `obfuscate_options['dbms']
= 'postgresql'` (`statements.py:182`); Db2 should set an appropriate dbms hint
(the Go obfuscator's dialect — likely `'db2'` or default SQL; verify against the agent obfuscator).

---

## 11. Manifest / metadata requirements to register a DBM product

### 11.1 `manifest.json`
Current `ibm_db2/manifest.json` (already exists):
`/home/bits/dd/integrations-core/ibm_db2/manifest.json`
- `manifest_version: "2.0.0"`, `app_id: "ibm-db2"`, `owner: "agent-integrations"`,
  `assets.integration.source_type_id: 10054`, `metrics.prefix: "ibm_db2."`, `auto_install: true`.

Postgres manifest for comparison (`/home/bits/dd/integrations-core/postgres/manifest.json`):
- `owner: "database-monitoring"`, `source_type_id: 28`, classifier tags incl.
  `Category::Data Stores`, `process_signatures`, dashboards/monitors/saved_views assets.

**Key finding:** The manifest schema in integrations-core has **no DBM-specific boolean flag.** There is
no `"dbm": true` field in `manifest.json`. DBM enablement is driven by:
1. The **runtime** `database_instance` metadata event with `metadata.dbm = true` (§6.1), and
2. The product being recognized by `ddsource`/`dbms` string + `source_type_id` on the backend side.
So registering Db2 as a DBM product is primarily a **backend + payload** concern, not a manifest field.
The manifest changes worth making for parity: add DBM-oriented `classifier_tags` and (optionally) move
`owner` to `database-monitoring` if the DBM team will own it. The decisive artifact is shipping the
five tracks with correct `dbms:"db2"` / `ddsource:"db2"` and a `database_instance` event with `dbm:true`.

### 11.2 `metadata.csv`
DBM does not require special rows in `metadata.csv` for the payload contract — `metadata.csv` documents
*standard metrics* (`metric_name,metric_type,interval,unit_name,...`). The DBM telemetry travels on the
event-platform tracks, not as standard metrics, so it is **not** declared in `metadata.csv`.
(The check still emits `dd.<dbms>.*` internal telemetry gauges/histograms/counts for self-monitoring —
e.g. `dd.postgres.statement_metrics.error`, `dd.postgres.collect_statement_samples.time` — but these
are debug/internal and tagged with `_get_debug_tags()`; they are not part of the backend contract.)

### 11.3 Source identity strings the backend keys on
- `ddsource` on samples/activity = `"db2"` (must be a recognized DBM source).
- `dbms` on metadata/schemas = `"db2"`.
- `DatabaseCheck.dbms` defaults to `self.__class__.__name__.lower()` (`db.py:36-38`) — override to
  return `"db2"` explicitly on the Db2 check.
- `health.category` = `__NAMESPACE__` (the integration namespace, i.e. `ibm_db2`) or classname.

---

## 12. Db2-specific call-outs for the implementation agent

1. **Subclass `DatabaseCheck`** (not bare `AgentCheck`) so the five `database_monitoring_*` helpers and
   the abstract identity properties are available. Implement `reported_hostname`, `database_identifier`,
   `dbms`→`"db2"`, `dbms_version`, `tags`, `cloud_metadata`. Existing `ibm_db2.py` currently subclasses
   plain `AgentCheck` (`/home/bits/dd/integrations-core/ibm_db2/datadog_checks/ibm_db2/ibm_db2.py`),
   uses `self._tags`, and parses version in `parse_version`/`get_version` (lines 96-119) — that version
   string feeds the `db2_version`/`dbms_version` fields.
2. **Naming convention:** use `db2_rows` (metrics), `db2_activity` + `db2_connections` (activity),
   `db2_version` everywhere a `<dbms>_version` appears. `ddsource:"db2"`, `dbms:"db2"`.
3. **Emit the `database_instance` event with `metadata.dbm = true`** on every check run, debounced —
   this is the single most important payload for the host to appear as a DBM instance.
4. **`ddtags` is a string in samples but a list in activity** — do not unify them.
5. **`timestamp` is epoch milliseconds** (`time.time() * 1000`) everywhere.
6. **Strip `dd.internal.*` tags** from all DBM payloads; strip `db:` for the no-db tag variant.
7. **Obfuscation + signatures:** reuse
   `datadog_checks.base.utils.db.utils.obfuscate_sql_with_metadata`,
   `datadog_checks.base.utils.db.sql.compute_sql_signature` / `compute_exec_plan_signature`,
   and `datadog_agent.obfuscate_sql_exec_plan`. Set the obfuscator `dbms` hint for Db2.
8. **Reuse `StatementMetrics.compute_derivative_rows`** for the monotonic→delta diffing; pick a stable
   `key` tuple and `execution_indicators` (a Db2 column that increments only on execution, e.g.
   `num_executions` from `MON_GET_PKG_CACHE_STMT` / `NUM_EXEC_WITH_METRICS`).
9. **Reuse `SchemaCollector`** (`utils/db/schemas.py`) if schema collection is in scope; only override
   the four abstract methods + `kind`.
10. **Health is optional** but `Health` base class is ready to subclass.

---

## 13. Primary source index (absolute paths)

- Submission API: `datadog_checks_base/datadog_checks/base/checks/base.py:772-817`;
  `datadog_checks_base/datadog_checks/base/checks/db.py:1-54`
- Identity: `postgres/datadog_checks/postgres/postgres.py:249-296, 680-750, 1198-1221`
- Hostname resolution + json encoder + obfuscation: `datadog_checks_base/datadog_checks/base/utils/db/utils.py:181-289`
- Metrics payload: `postgres/datadog_checks/postgres/statements.py:252-297, 522-581`;
  `mysql/datadog_checks/mysql/statements.py:164-176, 367-393`
- Derivative diffing: `datadog_checks_base/datadog_checks/base/utils/db/statement_metrics.py:25-150`
- Samples/plan/activity: `postgres/datadog_checks/postgres/statement_samples.py:570-1011`;
  `sqlserver/datadog_checks/sqlserver/activity.py:31, 275-345, 463-505`;
  `mysql/datadog_checks/mysql/activity.py:392-402`
- Metadata (settings/extensions/db_instance): `postgres/datadog_checks/postgres/metadata.py:176-226`;
  `postgres/datadog_checks/postgres/postgres.py:1198-1221`
- Schema collector: `datadog_checks_base/datadog_checks/base/utils/db/schemas.py:1-205`;
  `postgres/datadog_checks/postgres/schemas.py:204-205`
- Health: `datadog_checks_base/datadog_checks/base/utils/db/health.py:1-135`;
  `postgres/datadog_checks/postgres/health.py`
- Manifest/metadata: `ibm_db2/manifest.json`; `postgres/manifest.json`
- Existing Db2 check: `ibm_db2/datadog_checks/ibm_db2/ibm_db2.py`
