# 09 — Implementation Architecture (the code the implementing agent writes)

> **Audience.** The engineer (or AI agent) who is going to *write the code*. The "what to build and
> why" lives in the feature docs — [`03-reference-architecture.md`](03-reference-architecture.md)
> (the DBM blueprint), [`04-metrics-fidelity-plan.md`](04-metrics-fidelity-plan.md) (standard-metric
> expansion), [`05-dbm-query-metrics.md`](05-dbm-query-metrics.md),
> [`06-dbm-query-samples-activity.md`](06-dbm-query-samples-activity.md),
> [`07-dbm-execution-plans.md`](07-dbm-execution-plans.md), and
> `08-dbm-schemas-and-settings.md` (settings/schemas on `dbm-metadata`; the planned doc-08 slot —
> see [`00-README.md`](00-README.md) line 40 "Settings / schemas" and the P4 row). **This doc is the
> concrete module layout, the class skeletons, the `IbmDb2Check` wiring, the config surface, the
> manifest/metadata changes, and the file-by-file change list** that turns those designs into a
> working integration. Sequencing onto phases is in
> [`10-implementation-phases.md`](10-implementation-phases.md); the test plan is in
> [`11-testing-and-validation.md`](11-testing-and-validation.md).
>
> **Mirror target.** The SQL Server integration is the canonical "DBM bolted onto a pre-existing
> metrics-only check" example — exactly Db2's situation. Every module below mirrors a SQL Server
> sibling at `/home/bits/dd/integrations-core/sqlserver/datadog_checks/sqlserver/`.
>
> Db2 items that have not been verified against the live 12.1.4 container are marked **(verify)**.

---

## 0. TL;DR

The current check (`ibm_db2/datadog_checks/ibm_db2/ibm_db2.py`) is a single `IbmDb2Check(AgentCheck)`
with one persistent `self._conn`, hand-rolled `self.gauge(...)` submission, and a 6-method
synchronous query loop. To reach pg/mysql/sqlserver fidelity we:

1. Re-base the check on `DatabaseCheck` and give it identity properties (`reported_hostname`,
   `database_identifier`, `dbms="db2"`, `dbms_version`, `tags`, `cloud_metadata`), a `TagManager`, a
   static-info cache, and a `_send_database_instance_metadata` heartbeat.
2. Add a **connection layer** that hands each background job its OWN `ibm_db` connection keyed by a
   `key_prefix` (the `ibm_db` C driver's connection/statement handles are **not** safe to share across
   threads — §2.3).
3. Add four `DBMAsyncJob` collectors as new modules — `statements.py` (query metrics + FQT),
   `statement_samples.py` (samples + activity + plans), `metadata.py` (settings) and a
   `schemas.py` (`SchemaCollector`) — each gated by config and run via `run_job_loop` in `check()`.
4. Add the DBM config surface to `assets/configuration/spec.yaml` (`dbm`, `query_metrics`,
   `query_samples`, `query_activity`, `collect_settings`, `collect_schemas`, `obfuscator_options`,
   identity keys), regenerate `config_models/*` and `conf.yaml.example` via `ddev`.
5. Register DBM in `manifest.json` (DBM category tag + owner) — **no manifest boolean flag exists**;
   DBM "registration" is the `database_instance` *event*, not a manifest field.

DBM telemetry rides the event-platform tracks (`dbm-metrics`, `dbm-samples`, `dbm-activity`,
`dbm-metadata`, `dbm-health`); it is **not** catalogued in `metadata.csv` (only the handful of
`dd.db2.*` internal health gauges/counts are).

---

## 1. Target module layout

Directory: `/home/bits/dd/integrations-core/ibm_db2/datadog_checks/ibm_db2/`

| File | Status | Role | Mirrors (sqlserver) |
|---|---|---|---|
| `ibm_db2.py` | **modify** | `IbmDb2Check(DatabaseCheck)` orchestrator: identity props, `TagManager`, static-info cache, instantiate collectors, fan out `run_job_loop` when `dbm`, `cancel()` teardown, `database_instance` heartbeat. | `sqlserver.py` |
| `config.py` | **new** | `IbmDb2Config` — parse every option (incl. all DBM blocks) into typed attributes; build the `obfuscator_options` JSON string; `sanitize()` redacts password. | `config.py` |
| `connection.py` | **new** | `Db2Connection` — per-`key_prefix` `ibm_db` connection cache + `open_managed_default_connection` / `executed_managed_query` context managers; sets `CASE_LOWER` + isolation `UR`. Wraps existing `get_connection_data`/scrub helpers. | `connection.py` |
| `const.py` | **new** | Static-info cache keys (`STATIC_INFO_VERSION`, `STATIC_INFO_EDITION`, `STATIC_INFO_MEMBERS`), default intervals, `DBM_MIGRATED_METRICS` (if any standard metric is superseded by DBM). | `const.py` |
| `statements.py` | **new** | `Db2StatementMetrics(DBMAsyncJob)` — query metrics (delta over `MON_GET_PKG_CACHE_STMT`) + FQT events. | `statements.py` |
| `statement_samples.py` | **new** | `Db2StatementSamples(DBMAsyncJob)` — activity snapshot (`dbm-activity`) + sample/plan events (`dbm-samples`). Activity + samples are co-located here for Db2 because both read the in-flight `MON_GET_ACTIVITY`/`MON_GET_PKG_CACHE_STMT` surface; see [`06`](06-dbm-query-samples-activity.md). | `activity.py` + postgres `statement_samples.py` |
| `execution_plans.py` | **new (P3, deferrable)** | `Db2ExecutionPlans` helper used by `statement_samples.py` to assemble a JSON plan tree from the EXPLAIN tables and emit `dbm_type:"plan"`. Highest-risk piece — see [`07`](07-dbm-execution-plans.md). | (postgres `explain_parameterized_queries.py`) |
| `metadata.py` | **new** | `Db2Metadata(DBMAsyncJob)` — settings from `SYSIBMADM.DBMCFG`∪`DBCFG`∪`REG_VARIABLES` on `dbm-metadata`; delegates schema collection to `schemas.py`. See `08-dbm-schemas-and-settings.md`. | `metadata.py` |
| `schemas.py` | **new (P4)** | `Db2SchemaCollector(SchemaCollector)` over `SYSCAT.SCHEMATA/TABLES/COLUMNS/INDEXES/REFERENCES`. | `schemas.py` |
| `queries.py` | **modify (expand)** | Keep the 5 existing standard-metric `MON_GET_*` SQL constants; add the standard-metric expansion SQL from [`04`](04-metrics-fidelity-plan.md) and the DBM SQL templates (`PKG_CACHE_STMT_QUERY`, `ACTIVITY_QUERY`, `CONNECTIONS_QUERY`, `SETTINGS_QUERY`, schema queries). | `queries.py` |
| `util.py` | **new** (note: existing helper file is `utils.py`) | DBM-specific helpers: `Db2Version` parse → static-info dict, `payload_db2_version()`, member/partition helpers, row-key builders. Keep the existing `utils.py` (version/scrub/status-map) as-is; new DBM helpers go in `util.py` to avoid churning the shipped file, OR extend `utils.py` directly (recommended — one helpers module; rename references if you do). | `utils.py` |
| `utils.py` | **keep / extend** | Existing `get_version`, `scrub_connection_string`, `status_to_service_check`, `DB_STATUS_MAP`. | — |
| `config_models/*`, `data/conf.yaml.example` | **regenerate** | Autogenerated from `spec.yaml` via `ddev` — never hand-edit (except `validators.py`, `__init__.py`). | generated |

**Minimum-viable DBM build** (per [`03`](03-reference-architecture.md) and the sqlserver template):
`config.py` + `connection.py` + `statements.py` + `statement_samples.py` (activity portion) +
`metadata.py` (settings) + the `database_instance` heartbeat in `ibm_db2.py`. `execution_plans.py`
(P3) and `schemas.py` (P4) are independent follow-ons.

---

## 2. Integration with the existing check + connection

### 2.1 Re-base `IbmDb2Check` on `DatabaseCheck`

Today: `class IbmDb2Check(AgentCheck)` (`ibm_db2.py:29`). DBM event submitters
(`database_monitoring_query_metrics/sample/activity/metadata`) and the identity-property contract live
on `datadog_checks.base.checks.db.DatabaseCheck`. Switch the base class and add a `__NAMESPACE__`.

```python
# ibm_db2.py (sketch — additions over the current class)
from datadog_checks.base.checks.db import DatabaseCheck
from datadog_checks.base.utils.db.utils import TagManager, resolve_db_host
from cachetools import TTLCache

from .config import IbmDb2Config
from .connection import Db2Connection
from .statements import Db2StatementMetrics
from .statement_samples import Db2StatementSamples
from .metadata import Db2Metadata
from . import const


class IbmDb2Check(DatabaseCheck):
    __NAMESPACE__ = 'ibm_db2'          # keeps the existing ibm_db2.* metric prefix

    METRIC_PREFIX = 'ibm_db2'
    SERVICE_CHECK_CONNECT = '{}.can_connect'.format(METRIC_PREFIX)
    SERVICE_CHECK_STATUS = '{}.status'.format(METRIC_PREFIX)
    EVENT_TABLE_SPACE_STATE = '{}.tablespace_state_change'.format(METRIC_PREFIX)

    def __init__(self, name, init_config, instances):
        super().__init__(name, init_config, instances)
        self._config = IbmDb2Config(self.instance, self.init_config)

        # --- existing attrs preserved (now sourced via _config) ---
        self._db = self._config.db
        self._tags = list(self._config.tags)
        self._tags.append('db:{}'.format(self._db))          # unchanged behavior
        self._table_space_states = {}
        self._conn = None                                    # main (foreground) connection

        # --- DBM identity / tag plumbing ---
        self.tag_manager = TagManager(normalizer=lambda t: self.normalize_tag(t).lower())
        self.tag_manager.set_tags_from_list(self._tags)
        self._resolved_hostname = None
        self._database_identifier = None
        self.static_info_cache = TTLCache(maxsize=10, ttl=24 * 60 * 60)
        self._connection = Db2Connection(self, self._config)  # per-key_prefix conn pool

        # --- database_instance heartbeat debounce ---
        self._database_instance_emitted = TTLCache(
            maxsize=1, ttl=self._config.database_instance_collection_interval
        )

        # --- DBM collectors (instantiated always; each gated by its own `enabled`) ---
        self._query_metrics = Db2StatementMetrics(self, self._config)
        self._samples = Db2StatementSamples(self, self._config)
        self._metadata = Db2Metadata(self, self._config)

        # existing synchronous standard-metric loop, unchanged
        self._query_methods = (
            self.query_instance, self.query_database, self.query_buffer_pool,
            self.query_table_space, self.query_transaction_log, self.query_custom,
        )

    def check(self, instance):
        if self._conn is None:
            self._conn = self.get_connection()           # main conn (existing code path)
        self.emit_connection_service_checks()
        if self._conn is None:
            return

        self.collect_metadata()
        self._load_static_info()                          # version/edition into static_info_cache
        self._send_database_instance_metadata()           # registration / heartbeat event

        for query_method in self._query_methods:           # unchanged standard metrics
            try:
                query_method()
            except ConnectionError:
                raise
            except Exception as e:
                self.log.warning('Encountered error running `%s`: %s', query_method.__name__, str(e))

        if self._config.dbm_enabled:                       # DBM fan-out (mirrors sqlserver.py:913)
            tags = self.tag_manager.get_tags()
            self._query_metrics.run_job_loop(tags)
            self._samples.run_job_loop(tags)
            self._metadata.run_job_loop(tags)

    def cancel(self):                                      # tear down every background thread
        self._query_metrics.cancel()
        self._samples.cancel()
        self._metadata.cancel()
```

The existing standard-metric path (`query_*`, `iter_rows`, `get_connection`, `get_connection_data`,
`track_table_space_state_changes`, `parse_version`) is preserved verbatim — DBM is purely additive.

### 2.2 Identity properties (DBM payload `host` / `database_instance`)

`DatabaseCheck` requires these (the four DBM submitters and `SchemaCollector` read them). Mirror
sqlserver `sqlserver.py:340-397`.

```python
    @property
    def dbms(self):
        return "db2"                                       # selects backend parser + dd.db2.* names

    @property
    def dbms_version(self):
        return self.static_info_cache.get(const.STATIC_INFO_VERSION)  # set by _load_static_info()

    @property
    def reported_hostname(self):
        if self._config.exclude_hostname:                  # emit_hostname == False -> None
            return None
        return self.resolved_hostname

    @property
    def resolved_hostname(self):
        if self._resolved_hostname is None:
            if self._config.reported_hostname:
                self._resolved_hostname = self._config.reported_hostname
            else:
                # resolve_db_host(self._config.host) — same helper pg/mysql/sqlserver use
                self._resolved_hostname = resolve_db_host(self._config.host)
        return self._resolved_hostname

    @property
    def database_identifier(self):
        # template default "$resolved_hostname"; allow override like sqlserver.py:365-397
        if self._database_identifier is None:
            template = self._config.database_identifier.get('template') or '$resolved_hostname'
            # substitute $resolved_hostname / $host / $port / $db from tags + config
            self._database_identifier = self._render_identifier(template)
        return self._database_identifier

    @property
    def tags(self):
        return self.tag_manager.get_tags()

    @property
    def cloud_metadata(self):
        return self._config.cloud_metadata
```

`database_identifier` matters for multi-instance hosts: a single Db2 server can host several databases
(each its own check instance). Default `$resolved_hostname` collapses them; document that operators set
`database_identifier` to e.g. `$resolved_hostname:$db` to separate instances **(verify)** the chosen
default with the DBM backend team — postgres uses `$resolved_hostname`, and the per-db split is via the
`db` tag.

### 2.3 Background jobs get their OWN `ibm_db` connections (thread-safety)

This is the single most important correctness constraint. The `ibm_db` C extension returns a *connection
handle* and a *statement handle* (no Python cursor object); these handles are **not safe to use
concurrently from multiple threads** — they wrap a single CLI/ODBC connection context. The current
check has exactly one `self._conn` reused on the (synchronous) main thread; that is fine today but a
background `DBMAsyncJob` thread sharing it would corrupt in-flight fetches.

SQL Server solves this with a `key_prefix` that namespaces a connection cache so each subsystem opens
its own raw connection (`connection.py:521-526`, prefixes at `statements.py:289` `"dbm-"`,
`activity.py:209` `"dbm-activity-"`, `metadata.py:84` `"dbm-metadata-"`). Db2 must build the same layer
over `ibm_db.connect`.

```python
# connection.py (sketch)
import threading
import ibm_db
from .utils import scrub_connection_string

DEFAULT_ISOLATION = 'UR'  # uncommitted read: monitoring must never block writers (verify ibm_db API)

class Db2Connection:
    """Per-key_prefix ibm_db connection pool. Each DBM job uses a distinct prefix so background
    threads never share a connection handle with the main check or each other."""

    def __init__(self, check, config):
        self._check = check
        self._config = config
        self._conns = {}                 # key_prefix -> ibm_db conn handle
        self._lock = threading.RLock()   # guards the dict, not the handles

    def _connect(self, key_prefix):
        target, user, pwd = self._check.get_connection_data(
            self._config.db, self._config.username, self._config.password,
            self._config.host, self._config.port, self._config.security,
            self._config.tls_cert, self._config.connection_timeout,
        )
        options = {ibm_db.ATTR_CASE: ibm_db.CASE_LOWER}     # lowercase columns, same as main conn
        conn = ibm_db.connect(target, user, pwd, options)
        # SET CURRENT ISOLATION = UR so monitoring reads take no locks (mirrors mssql READ UNCOMMITTED)
        ibm_db.exec_immediate(conn, "SET CURRENT ISOLATION = {}".format(DEFAULT_ISOLATION))  # (verify)
        return conn

    def get(self, key_prefix):
        with self._lock:
            conn = self._conns.get(key_prefix)
            if conn is None:
                conn = self._conns[key_prefix] = self._connect(key_prefix)
            return conn

    @contextmanager
    def executed_managed_query(self, key_prefix, query, params=None):
        """Yields an iterator of dict rows (ibm_db.fetch_assoc already returns dicts)."""
        conn = self.get(key_prefix)
        stmt = ibm_db.exec_immediate(conn, query)          # or ibm_db.prepare/execute for params
        def rows():
            row = ibm_db.fetch_assoc(stmt)
            while row is not False:
                yield row
                row = ibm_db.fetch_assoc(stmt)
        yield rows()

    def close(self, key_prefix):
        with self._lock:
            conn = self._conns.pop(key_prefix, None)
        if conn is not None:
            ibm_db.close(conn)
```

Each collector picks a distinct prefix and passes `self._close` as the `DBMAsyncJob`
`shutdown_callback`:

- `statements.py` → `"dbm-statements-"`
- `statement_samples.py` → `"dbm-samples-"`
- `metadata.py` → `"dbm-metadata-"`
- `schemas.py` → `"dbm-schemas-"`

Because `ibm_db.fetch_assoc` with `CASE_LOWER` already yields lowercase-keyed dict rows, we skip the
`dict(zip(cursor.description, row))` step SQL Server needs (it has no DictCursor). **(verify)** that
`ibm_db.connect` from a `ThreadPoolExecutor` worker thread is permitted by the bundled `ibm_db==3.2.6`
build — the live container is the place to confirm; if a fresh connect-per-thread is required (no reuse),
open and close inside each `run_job()` instead of caching in `self._conns`.

### 2.4 Static info cache (version / edition / members)

Cache the version once per day, like sqlserver `load_static_information()` (`sqlserver.py:413-494`).
Reuse the existing `utils.get_version` (`ibm_db.get_db_info(conn, SQL_DBMS_VER)`) plus
`SYSIBMADM.ENV_INST_INFO` for edition and `SYSIBMADM.DB2_MEMBER` for member count **(verify)**:

```python
    def _load_static_info(self):
        if const.STATIC_INFO_VERSION not in self.static_info_cache:
            self.static_info_cache[const.STATIC_INFO_VERSION] = get_version(self._conn)  # "12.01.0404"
        # edition / member count likewise, guarded the same way
```

`dbms_version` reads from this cache; the `db2_version` payload key uses `payload_db2_version()` in
`util.py` to format it for the backend (mirrors postgres `payload_pg_version`).

### 2.5 `database_instance` heartbeat (DBM registration)

There is **no manifest flag** that makes a host show up in the DBM UI; that is done by emitting a
`database_instance` event every run with `metadata.dbm = config.dbm_enabled` (sqlserver
`sqlserver.py:1151-1173`, debounced by a 1-entry `TTLCache`). Implement
`_send_database_instance_metadata` to emit via `database_monitoring_metadata` with the host's
`database_identifier`, `dbms="db2"`, `dbms_version`, tags, cloud metadata, and `collection_interval =
config.database_instance_collection_interval`. Debounce with `self._database_instance_emitted`.

---

## 3. DBM collectors — `DBMAsyncJob` skeletons

All three subclass `DBMAsyncJob` (`base/utils/db/utils.py:289`). Construction pattern is identical to
sqlserver (`statements.py:257-277`): read the per-collector config block for `enabled` /
`collection_interval` / `run_sync`, set `dbms="db2"`, `rate_limit = 1/interval`, a `job_name`, and a
`shutdown_callback` that closes the dedicated connection.

### 3.1 `statements.py` — `Db2StatementMetrics` (query metrics + FQT)

Design in [`05-dbm-query-metrics.md`](05-dbm-query-metrics.md). Source: `TABLE(MON_GET_PKG_CACHE_STMT
(NULL, NULL, NULL, -1))` — the Db2 analog of `pg_stat_statements`/`dm_exec_query_stats`. Reuse the
shared delta engine and signature/obfuscation helpers — **do not reimplement**.

```python
# statements.py (sketch)
from datadog_checks.base.utils.db.statement_metrics import StatementMetrics
from datadog_checks.base.utils.db.sql import compute_sql_signature
from datadog_checks.base.utils.db.utils import (
    DBMAsyncJob, obfuscate_sql_with_metadata, default_json_event_encoding,
)
from cachetools import TTLCache
from . import queries

DEFAULT_QUERY_METRICS_INTERVAL = 60
CONN_PREFIX = "dbm-statements-"


class Db2StatementMetrics(DBMAsyncJob):
    def __init__(self, check, config):
        self._check = check
        self._config = config
        cfg = config.statement_metrics_config
        interval = float(cfg.get('collection_interval', DEFAULT_QUERY_METRICS_INTERVAL)) or DEFAULT_QUERY_METRICS_INTERVAL
        self._metrics_collection_interval = interval
        self._state = StatementMetrics()                  # holds previous snapshot
        self._full_statement_text_cache = TTLCache(
            maxsize=cfg.get('full_statement_text_cache_max_size', 10000),
            ttl=60 * 60 / cfg.get('full_statement_text_samples_per_hour_per_query', 1),
        )
        super().__init__(
            check,
            run_sync=is_affirmative(cfg.get('run_sync', False)),
            enabled=is_affirmative(cfg.get('enabled', True)),
            expected_db_exceptions=(),                     # add ibm_db.Error class once known (verify)
            min_collection_interval=config.min_collection_interval,
            dbms="db2",
            rate_limit=1 / interval,
            job_name="query-metrics",
            shutdown_callback=lambda: check._connection.close(CONN_PREFIX),
        )

    def run_job(self):
        rows = self._collect_and_diff()
        for event in self._rows_to_fqt_events(rows):
            self._check.database_monitoring_query_sample(json.dumps(event, default=default_json_event_encoding))
        for payload in self._to_metrics_payloads(rows):
            self._check.database_monitoring_query_metrics(payload)

    def _collect_and_diff(self):
        with self._check._connection.executed_managed_query(CONN_PREFIX, queries.PKG_CACHE_STMT_QUERY) as rows:
            raw = list(rows)
        normalized = self._normalize(raw)                  # obfuscate STMT_TEXT, compute query_signature
        metric_columns = [c for c in normalized[0] if c in DB2_STMT_METRIC_COLUMNS] if normalized else []
        return self._state.compute_derivative_rows(
            normalized, metric_columns,
            key=_row_key,                                  # (query_signature, db, member?) — see below
            execution_indicators=['num_exec_with_metrics'],       # NUM_EXEC_WITH_METRICS must increase
        )

    def _normalize(self, raw):
        out = []
        for row in raw:
            statement = obfuscate_sql_with_metadata(
                row['stmt_text'], self._config.obfuscator_options, replace_null_character=True,
            )                                              # Db2 CLOB text -> strip \x00
            row['query'] = statement['query']
            row['query_signature'] = compute_sql_signature(statement['query'])
            row['dd_tables'] = statement['metadata'].get('tables')
            row['dd_commands'] = statement['metadata'].get('commands')
            row['dd_comments'] = statement['metadata'].get('comments')
            del row['stmt_text']
            out.append(row)
        return out
```

Key decisions (from [`05`](05-dbm-query-metrics.md) and the postgres research):

- **Row key** `_row_key(row) = (row['query_signature'], row['db'], row.get('member'))` — signature
  rather than raw `EXECUTABLE_ID`, so statements that normalize to the same text merge. `EXECUTABLE_ID`
  is `VARBINARY` — used only for the in-snapshot grouping if needed **(verify)** column availability.
- **Metric columns** introspected at runtime (mirror postgres `statements.py:211-232`): `SELECT ...
  FETCH FIRST 1 ROWS ONLY` to discover available `MON_GET_PKG_CACHE_STMT` columns rather than
  hard-coding by fixpack. Candidates (counters): `num_executions`, `total_act_time`, `total_cpu_time`,
  `stmt_exec_time`, `rows_read`, `rows_returned`, `rows_modified`, `total_sorts`, `pool_data_l_reads`,
  `pool_data_p_reads`, `lock_wait_time`, `lock_waits`, `lock_timeouts`, `deadlocks` **(verify all
  names against 12.1.4)**.
- **Stats-reset / no-change / indicator guards** are all handled by `compute_derivative_rows` — a
  negative diff (package-cache eviction = reset) drops the whole row; `execution_indicators` filters
  re-inserted phantoms. Call it **exactly once per run**.
- **Payload**: wrapper key `db2_rows`, version key `db2_version`, `host`/`database_instance` from the
  identity props, batch-split under `batch_max_content_size`. FQT events `ddsource:"db2"`,
  `dbm_type:"fqt"`, dialect block `"db2": {...}`.

### 3.2 `statement_samples.py` — `Db2StatementSamples` (activity + samples + plans)

Design in [`06-dbm-query-samples-activity.md`](06-dbm-query-samples-activity.md) (and plans in
[`07`](07-dbm-execution-plans.md)). One `DBMAsyncJob` produces two tracks:

- **`dbm-activity`** — the in-flight active-session snapshot from `TABLE(MON_GET_ACTIVITY(-1, -1))`
  (+ `WLM_GET_WORKLOAD_OCCURRENCE_ACTIVITIES`), connection summary from
  `TABLE(MON_GET_CONNECTION(NULL, -1))`, blocking linkage from `SYSIBMADM.MON_LOCKWAITS` **(verify)**.
  Payload keys `db2_activity` (sessions) + `db2_connections` (counts), `ddtags` as a **list**,
  size-capped at `MAX_PAYLOAD_BYTES`.
- **`dbm-samples`** — `dbm_type:"plan"` events when `execution_plans.py` can assemble a plan for a
  newly-seen `(query_signature, plan_signature)` (rate-limited via `RateLimitingTTLCache`); optional
  `dbm_type:"rqt"`/`"rqp"` raw events under `collect_raw_query_statement`.

```python
# statement_samples.py (sketch — shape only)
class Db2StatementSamples(DBMAsyncJob):
    def __init__(self, check, config):
        self._check, self._config = check, config
        act = config.activity_config
        interval = float(act.get('collection_interval', 10)) or 10
        self._seen_plans = RateLimitingTTLCache(maxsize=10000, ttl=3600)  # 1 plan/query/hour
        super().__init__(
            check, dbms="db2", job_name="query-activity",
            enabled=is_affirmative(act.get('enabled', True)),
            run_sync=is_affirmative(act.get('run_sync', False)),
            rate_limit=1 / interval, min_collection_interval=config.min_collection_interval,
            shutdown_callback=lambda: check._connection.close("dbm-samples-"),
        )

    def run_job(self):
        self._collect_activity()           # -> database_monitoring_query_activity(...)
        if self._config.query_samples_config.get('enabled', True):
            self._collect_samples_and_plans()   # -> database_monitoring_query_sample(...)
```

`execution_plans.py` is invoked from `_collect_samples_and_plans`; it runs `EXPLAIN`/reads the EXPLAIN
tables (`EXPLAIN_STATEMENT`, `EXPLAIN_OPERATOR`, `EXPLAIN_STREAM`, `EXPLAIN_OBJECT`), assembles a JSON
tree, then `compute_exec_plan_signature(normalized_json)`. This is the **P3 / highest-risk** piece and
is deliberately separable — ship activity + samples without plans first ([`07`](07-dbm-execution-plans.md),
[`10`](10-implementation-phases.md) P3).

### 3.3 `metadata.py` — `Db2Metadata` (settings + schema delegation)

Design in `08-dbm-schemas-and-settings.md`. `job_name="database-metadata"`, default interval 600s.

```python
class Db2Metadata(DBMAsyncJob):
    def run_job(self):
        if self._config.settings_config.get('enabled', True):
            self.report_db2_metadata()           # SYSIBMADM.DBMCFG ∪ DBCFG ∪ REG_VARIABLES
        if self._config.schema_config.get('enabled', False):
            self._schemas.collect_schemas()       # delegates to Db2SchemaCollector
```

`report_db2_metadata` emits `dbm-metadata` with `kind:"db2_configs"`, `metadata` = the settings rows.
`schemas.py` subclasses `SchemaCollector` and overrides only `kind` (`"db2_databases"`),
`_get_databases`, `_get_cursor`, `_get_next`, `_map_row` (over `SYSCAT.*`); the base handles chunking +
the envelope.

### 3.4 What we deliberately skip

No Db2 analog (or low first-fidelity value): SQL Server deadlocks (XE-based), agent-job history, stored
procedure metrics, Extended Events. Db2 deadlock detail lives in event monitors / `db2diag.log` — out of
scope for first fidelity (revisit in [`99-review-and-gaps.md`](99-review-and-gaps.md)).

---

## 4. Config surface

### 4.1 `conf.yaml.example` / `spec.yaml` additions

Edit **only** `assets/configuration/spec.yaml` (source of truth), then regenerate. Add these instance
options after the existing `connection_timeout`, mirroring sqlserver `spec.yaml` blocks
(`code-sqlserver-dbm-template.md` §2.4) and the conventions in
[`code-integration-scaffolding.md`](_research/code-integration-scaffolding.md) §3, §11.5:

| YAML key | Shape / defaults | Note |
|---|---|---|
| `dbm` | bool, default `false` | master switch; `Requires` nothing, gates everything. |
| `query_metrics` | obj: `enabled: true`, `collection_interval: 60`, `run_sync`, `full_statement_text_cache_max_size: 10000`, `full_statement_text_samples_per_hour_per_query: 1` | Requires `dbm: true`. See [`05`](05-dbm-query-metrics.md). |
| `query_activity` | obj: `enabled: true`, `collection_interval: 10`, `run_sync` | Requires `dbm: true`. |
| `query_samples` | obj: `enabled: true`, `collection_interval`, `samples_per_hour_per_query: 4`, `explained_queries_per_hour_per_query` | Requires `dbm: true`. See [`06`](06-dbm-query-samples-activity.md)/[`07`](07-dbm-execution-plans.md). |
| `collect_settings` | obj: `enabled: true`, `collection_interval: 600` | Requires `dbm: true`. See `08`. |
| `collect_schemas` | obj: `enabled: false`, `collection_interval: 600`, `max_tables: 300` | Requires `dbm: true`. See `08`. |
| `collect_raw_query_statement` | obj: `enabled: false`, `cache_max_size: 10000`, `samples_per_hour_per_query: 1` | RQT/RQP emission. |
| `obfuscator_options` | obj: `collect_tables`, `collect_commands`, `collect_comments`, `replace_digits`, `keep_sql_alias`, `obfuscation_mode`, ... | dialect set in code, not YAML. |
| `reported_hostname` | string | override DBM `host`. |
| `exclude_hostname` | bool, default `false` | emit DBM events with no host. |
| `database_identifier` | obj: `template: "$resolved_hostname"` | controls `database_instance`. |
| `database_instance_collection_interval` | number, default `300` **(verify; pick a value)** | heartbeat debounce ttl. |
| `propagate_agent_tags` | bool, default `false` | merge agent host tags. |
| `aws` / `gcp` / `azure` | cloud metadata objects | only applied when `dbm`. |

These spec blocks become nested pydantic models after regeneration. The check reads them through
`IbmDb2Config` (which can wrap `ConfigMixin`'s `self.config`, or read `self.instance.get(...)` directly
— either is acceptable per scaffolding §3.4; `config.py` keeps the parsing in one place).

### 4.2 `config.py` skeleton

```python
# config.py (sketch)
import json
from datadog_checks.base import is_affirmative
from datadog_checks.base.utils.serialization import json as ddjson

class IbmDb2Config:
    def __init__(self, instance, init_config):
        self.db = instance.get('db', '')
        self.username = instance.get('username', '')
        self.password = instance.get('password', '')
        self.host = instance.get('host', '')
        self.port = instance.get('port', 50000)
        self.security = instance.get('security', 'none')
        self.tls_cert = instance.get('tls_cert')
        self.connection_timeout = instance.get('connection_timeout')
        self.tags = list(instance.get('tags', []))
        self.service = instance.get('service') or init_config.get('service')
        self.min_collection_interval = instance.get('min_collection_interval', 15)

        # DBM
        self.dbm_enabled = is_affirmative(instance.get('dbm', False))
        self.statement_metrics_config = instance.get('query_metrics', {}) or {}
        self.query_samples_config = instance.get('query_samples', {}) or {}
        self.activity_config = instance.get('query_activity', {}) or {}
        self.settings_config = instance.get('collect_settings', {}) or {}
        self.schema_config = instance.get('collect_schemas', {}) or {}
        self.cloud_metadata = self._build_cloud_metadata(instance)
        self.reported_hostname = instance.get('reported_hostname')
        self.exclude_hostname = is_affirmative(instance.get('exclude_hostname', False))
        self.database_identifier = instance.get('database_identifier', {}) or {}
        self.database_instance_collection_interval = instance.get(
            'database_instance_collection_interval', 300)
        self.obfuscator_options = self._build_obfuscator_options(instance)

    def _build_obfuscator_options(self, instance):
        opts = instance.get('obfuscator_options', {}) or {}
        return json.dumps({
            'dbms': 'db2',                                 # (verify) Go obfuscator supports 'db2';
                                                           # else fall back to a generic SQL dialect
            'replace_digits': is_affirmative(opts.get('replace_digits', False)),
            'keep_sql_alias': is_affirmative(opts.get('keep_sql_alias', True)),
            'return_json_metadata': is_affirmative(opts.get('collect_metadata', True)),
            'table_names': is_affirmative(opts.get('collect_tables', True)),
            'collect_commands': is_affirmative(opts.get('collect_commands', True)),
            'collect_comments': is_affirmative(opts.get('collect_comments', True)),
            'obfuscation_mode': opts.get('obfuscation_mode', 'obfuscate_and_normalize'),
        })
```

The **obfuscator `dbms` dialect** is the one true open question: confirm the Agent `pkg/obfuscate`
recognizes `'db2'`; if not, use the closest supported SQL dialect. This must be settled before
`statements.py` ships because `query_signature` (the APM-correlation hash) is computed over the
obfuscated text — see [`05`](05-dbm-query-metrics.md) and `code-base-framework.md` §D.2.

### 4.3 Regeneration commands

From inside `ibm_db2/` (scaffolding §8):

```bash
ddev -x validate config -s      # rewrites data/conf.yaml.example from spec.yaml
ddev -x validate models -s      # rewrites config_models/{instance,shared,defaults}.py
```

`config_models/validators.py` and `config_models/__init__.py` are hand-editable; the rest are
generated. `pyproject.toml` `datadog-checks-base>=37.33.0` may need a bump if a newer base API is used
(e.g. `SchemaCollector`); add a `changelog.d/<PR>.changed` fragment if so.

---

## 5. Manifest / metadata changes (register DBM)

Per `code-sqlserver-dbm-template.md` §8.5 and scaffolding §11.6-11.7: **DBM is not a manifest boolean.**
What changes:

1. **`manifest.json`** — optional but recommended for catalog parity:
   - Add a DBM classifier tag, e.g. `"Category::Caching"` is wrong; use the DBM-related category the
     catalog requires — sqlserver/postgres carry `"Category::Data Stores"` (already present) plus the
     offering. **(verify)** the exact DBM catalog tag (`ddev validate ci` enforces it); do not invent
     one. Optionally move `owner` from `"agent-integrations"` to `"database-monitoring"`.
   - `metrics.check` stays `ibm_db2.connection.active`; prefix stays `ibm_db2.`.
   - `app_uuid` (`e588293a-...`) and `source_type_id` (`10054`) are **stable — never change**.
2. **`metadata.csv`** — DBM samples/activity/plans are event-platform data, **not** Agent metrics, so
   they are NOT catalogued here. Only add rows for the standard-metric expansion ([`04`](04-metrics-fidelity-plan.md))
   and for the few internal DBM health gauges the check emits via `self.gauge`/`self.count`
   (`dd.db2.async_job.*` are `raw=True` and excluded from the catalog). Remember `monotonic_count`
   submissions are catalogued as `count` (only `count`/`gauge`/`rate` are valid `metric_type` values).
3. **`assets/dataflows.yaml`** — leave as-is; DBM is not a `data_type` here (confirmed: pg/mysql/mssql
   dataflows declare only metrics/logs/events). DBM rides the event-platform tracks.
4. **`assets/service_checks.json`** — add an entry only if a new DBM connectivity service check is
   introduced (optional; the existing `can_connect` covers the main connection).
5. **`README.md`** — add a DBM setup subsection (grants: `EXECUTE` on `MON_GET_PKG_CACHE_STMT`,
   `MON_GET_ACTIVITY`, `MON_GET_CONNECTION`, read on `SYSIBMADM.*`/`SYSCAT.*`; enabling `dbm: true`) and
   reference samples/activity under "Data Collected". Validate with `ddev validate readmes -x`.

---

## 6. File-by-file change list

**New files** (`datadog_checks/ibm_db2/`):

| File | Contents | Phase ([`10`](10-implementation-phases.md)) |
|---|---|---|
| `config.py` | `IbmDb2Config` + `obfuscator_options` builder + cloud metadata. | P2 (with first collector) |
| `connection.py` | `Db2Connection` per-`key_prefix` pool + managed-query context manager + `UR` isolation. | P2 |
| `const.py` | static-info keys, default intervals, `DBM_MIGRATED_METRICS`. | P2 |
| `util.py` | `payload_db2_version`, member helpers, row-key builders (or fold into `utils.py`). | P2 |
| `statements.py` | `Db2StatementMetrics(DBMAsyncJob)`. | **P2** |
| `statement_samples.py` | `Db2StatementSamples(DBMAsyncJob)` (activity + samples). | **P2/P3** |
| `execution_plans.py` | EXPLAIN-tree assembly + plan events. | **P3** |
| `metadata.py` | `Db2Metadata(DBMAsyncJob)` (settings). | **P4** |
| `schemas.py` | `Db2SchemaCollector(SchemaCollector)`. | **P4** |

**Modified files:**

| File | Change |
|---|---|
| `ibm_db2.py` | base class `AgentCheck`→`DatabaseCheck`; `__NAMESPACE__='ibm_db2'`; build `IbmDb2Config`, `TagManager`, `Db2Connection`, static-info cache; instantiate 3 collectors; `_load_static_info` + `_send_database_instance_metadata` in `check()`; gate `run_job_loop` fan-out on `dbm_enabled`; add `cancel()`; add identity props. Keep all existing `query_*`/`iter_rows`/`get_connection*`/event code. |
| `queries.py` | add `PKG_CACHE_STMT_QUERY`, `ACTIVITY_QUERY`, `CONNECTIONS_QUERY`, `SETTINGS_QUERY`, schema queries + the standard-metric expansion SQL from [`04`](04-metrics-fidelity-plan.md). |
| `utils.py` | optionally add edition/member parsing; keep existing helpers. |
| `assets/configuration/spec.yaml` | add the DBM blocks (§4.1). **Edit-then-regenerate.** |
| `config_models/*`, `data/conf.yaml.example` | regenerated (`ddev -x validate config/models -s`). |
| `manifest.json` | DBM category tag / owner (§5.1) — `app_uuid`/`source_type_id` untouched. |
| `metadata.csv` | standard-metric expansion rows only (§5.2). |
| `README.md` | DBM setup + grants + Data Collected (§5.5). |
| `pyproject.toml` | bump `datadog-checks-base` min if newer base API used; `__about__.py` minor bump. |
| `hatch.toml` / `tests/docker/docker-compose.yaml` | add Db2 `12.1` to the matrix + a 12.1 image tag — see [`11`](11-testing-and-validation.md) and scaffolding §13. |
| `changelog.d/<PR>.added` | one fragment per feature PR. |

**New tests** (mirror `sqlserver/tests/`): `test_statements.py`, `test_activity.py`,
`test_metadata.py`, `test_connection.py`, plus DBM fixtures in `conftest.py`/`common.py`. Detailed in
[`11-testing-and-validation.md`](11-testing-and-validation.md).

---

## 7. Staffing onto the phases (doc 10)

[`10-implementation-phases.md`](10-implementation-phases.md) sequences the work; this maps each module
to its phase:

- **P1 — standard-metric expansion** ([`04`](04-metrics-fidelity-plan.md)): touches `queries.py` +
  `ibm_db2.py` `query_*` + `metadata.csv` only. **No DBM scaffolding.** Independent of everything below.
- **P2 — DBM foundation + query metrics** ([`05`](05-dbm-query-metrics.md)): the big architectural lift.
  Re-base on `DatabaseCheck`, add `config.py` + `connection.py` + `const.py` + `util.py`, the
  `database_instance` heartbeat, identity props, and ship `statements.py`. This phase establishes the
  per-job connection isolation (§2.3) that every later collector depends on — do it first.
- **P3 — samples + activity (+ plans)** ([`06`](06-dbm-query-samples-activity.md),
  [`07`](07-dbm-execution-plans.md)): `statement_samples.py` (activity first, then samples), then
  `execution_plans.py` last (highest risk; ship activity without it). Reuses P2's `Db2Connection`.
- **P4 — settings + schemas** (`08-dbm-schemas-and-settings.md`): `metadata.py` + `schemas.py`. Independent
  of P2/P3 collectors (only needs the P2 foundation); can run in parallel with P3.
- **Cross-cutting** ([`11`](11-testing-and-validation.md)): the Db2 `12.1` test image/matrix and the
  per-collector test modules land alongside each phase.

The connection-isolation layer (§2.3) and the obfuscator-dialect decision (§4.2) are the two
P2 gating items — settle both before P3/P4 build on them.

---

## 8. Open items to verify on the live 12.1.4 container

1. `ibm_db.connect` from a worker thread + whether handle reuse across runs is safe, or connect-per-run
   is required (§2.3).
2. `SET CURRENT ISOLATION = UR` syntax/effect via `ibm_db.exec_immediate` (§2.3).
3. Exact `MON_GET_PKG_CACHE_STMT` / `MON_GET_ACTIVITY` / `MON_GET_CONNECTION` column names + that
   `STMT_TEXT` is returned (and any truncation) — introspect, don't hard-code (§3.1).
4. Agent obfuscator `dbms='db2'` support; fallback dialect otherwise (§4.2).
5. `database_identifier` default + `database_instance_collection_interval` value with the DBM backend
   team (§2.2, §4.1).
6. The exact DBM catalog/classifier tag `ddev validate ci` expects in `manifest.json` (§5.1).
7. Blocking-tree source (`SYSIBMADM.MON_LOCKWAITS` vs `MON_GET_APPL_LOCKWAIT`) for activity (§3.2).
```
