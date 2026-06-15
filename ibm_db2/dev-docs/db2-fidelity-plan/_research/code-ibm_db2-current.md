# Current `ibm_db2` Integration — Complete Code Audit

Raw research input for a Db2 high-fidelity / DBM implementation plan. Target Db2 version: **12.1** (live container 12.1.4). All code findings cite absolute paths in `/home/bits/dd/integrations-core/ibm_db2`. Documentation URLs in the source code all point at the **11.1** Knowledge Center (`SSEPGG_11.1.0`); the table functions referenced are still present in 12.1.

Integration version: **4.3.0** (`datadog_checks/ibm_db2/__about__.py:4`). Min Agent: **6.11.0** (`manifest.json`, `README.md:9`). Min `datadog-checks-base`: **37.33.0** (`pyproject.toml:31`).

---

## 1. Architecture overview

- Single check class `IbmDb2Check(AgentCheck)` in `datadog_checks/ibm_db2/ibm_db2.py:29`. Classic `AgentCheck`, **not** a DBM-style check (no async collectors, no `DBMAsyncJob`, no statement/activity/sample collection — see §10).
- Driver: the **`ibm_db`** Python C-extension (PyPI `ibm-db`), imported at module top (`ibm_db2.py:23`). Pinned to `ibm_db==3.2.6` for Py3 (`README.md:24`, `hatch.toml:14`, `tests/common.py:36`). Not bundled with the Agent — operator must `pip install ibm_db` into the Agent's embedded env (`README.md:19-53`).
- Windows special-case: before importing `ibm_db`, the check appends the `clidriver/bin` DLL dir via `os.add_dll_directory` (`ibm_db2.py:15-21`).
- Metric prefix `ibm_db2` (`ibm_db2.py:30`). Helper `IbmDb2Check.m(metric)` → `'ibm_db2.<metric>'` (`ibm_db2.py:633-635`).
- All SQL lives in `datadog_checks/ibm_db2/queries.py` as module constants built from column tuples. There is **no** YAML query manifest, no `QueryManager`/`QueryExecutor` — queries are run directly through `ibm_db.exec_immediate`.

### Check lifecycle (`ibm_db2.py:76-91`)

```python
def check(self, instance):
    if self._conn is None:
        self._conn = self.get_connection()
    self.emit_connection_service_checks()
    if self._conn is None:
        return
    self.collect_metadata()
    for query_method in self._query_methods:
        try:
            query_method()
        except ConnectionError:
            raise
        except Exception as e:
            self.log.warning('Encountered error running `%s`: %s', query_method.__name__, str(e))
            continue
```

`self._query_methods` tuple (`ibm_db2.py:67-74`), executed in order every run:
1. `query_instance`
2. `query_database`
3. `query_buffer_pool`
4. `query_table_space`
5. `query_transaction_log`
6. `query_custom`

Per-method exceptions are swallowed and logged at WARNING (one failing query does not abort the run). A `requests.ConnectionError` (raised from `iter_rows` on reconnect failure) **does** propagate and aborts the run. Confirmed by `tests/test_unit.py:93-121`.

---

## 2. Connection handling (`ibm_db` driver usage)

### Connection construction
- Instance attrs parsed in `__init__` (`ibm_db2.py:35-54`): `db`, `username`, `password`, `host`, `port` (default `50000`), `tags`, `security` (default `'none'`), `tls_cert`, `connection_timeout`.
- `'db:<db>'` is appended unconditionally to `self._tags` (`ibm_db2.py:48`) — global tag on every metric/event/service check.
- `self._conn = None`; connection is lazily created on first `check()` (`ibm_db2.py:54`, `:77-78`).

### `get_connection_data` (classmethod, `ibm_db2.py:591-608`)
Builds the connection string. When `host` is set:
```
database={db};hostname={host};port={port};protocol=tcpip;uid={username};pwd={password}
```
Then appends, in order:
- `;security=ssl;` if `security == 'ssl'`
- `;security=ssl;sslservercertificate={tls_cert}` if `tls_cert` set (note: this **re-adds** `security=ssl` — duplicated when both set)
- `;connecttimeout={connection_timeout}` if set

When `host` is empty (`else` branch, `:605-607`, marked `# no cov`): `target = db` (uses a **cataloged DSN** — the bare database name resolves via `db2cli.ini`/`db2dsdriver.cfg`). The `SQL1531N` troubleshooting note (`README.md:197-209`) is about this path failing when no host/port and no catalog files exist.

When `host` is set, `username`/`password` are blanked and folded into the connection string instead (`ibm_db2.py:597-598`).

### `get_connection` (`ibm_db2.py:554-578`)
- Calls `get_connection_data(...)`.
- Sets `connection_options = {ibm_db.ATTR_CASE: ibm_db.CASE_LOWER}` so all result column names come back lowercase (`ibm_db2.py:567`) — this is why all dict keys in `iter_rows`/query methods are lowercase.
- `ibm_db.connect(target, username, password, connection_options)`.
- On exception: logs error (password scrubbed via `scrub_connection_string`), returns `None`.

### Connection is a single persistent handle
- One `self._conn` per check instance, opened once, reused across runs. **No connection pooling, no per-query connections, no explicit close** (no `ibm_db.close` in the check; only the test `conftest.DbManager.connect` closes — `tests/conftest.py:62`).
- **Reconnect logic** in `iter_rows` (`ibm_db2.py:610-631`): if `ibm_db.exec_immediate` raises, it logs, calls `get_connection()` to rebuild `self._conn`, re-emits connect service checks, and retries `exec_immediate` once. If reconnection fails it raises `requests.ConnectionError("Unable to create new connection")`. There is an explicit `# ToDo` (`:617-618`) noting the better strategy would be to null `self._conn` and retry next run.
- Tested: `test_retry_connection` and `test_fails_to_reconnect` (`tests/test_unit.py:31-62`).

### `iter_rows` (`ibm_db2.py:610-631`)
Generic generator: `cursor = ibm_db.exec_immediate(self._conn, query)`, then loops `row = method(cursor)` yielding until `row is False`. `method` is one of:
- `ibm_db.fetch_assoc` (dict keyed by lowercase column name) — used by all built-in queries.
- `ibm_db.fetch_tuple` (positional tuple) — used by custom queries (`ibm_db2.py:461`).

---

## 3. Metadata collection (version)

- `collect_metadata` (`ibm_db2.py:93-107`), decorated `@AgentCheck.metadata_entrypoint`.
- `get_version(connection)` (`utils.py:27-28`) → `ibm_db.get_db_info(connection, ibm_db.SQL_DBMS_VER)`. Returns raw string format `MM.mm.uuuu`.
- `parse_version` (`ibm_db2.py:109-125`): splits on `.` into `major.minor.update`; `update[:2]` = modification, `update[2:]` = fix pack. Submits via `set_metadata('version', raw, scheme='parts', part_map={major, minor, mod, fix})`. Tested at `tests/test_unit.py:124-133` (`'11.01.0202'` → major 11, minor 1, mod 2, fix 2).
- Surfaces as Agent integration metadata `version.*`; **not** a metric.

---

## 4. Built-in queries → metrics (exhaustive)

All five built-in table functions use the `-1`/`NULL` member argument to aggregate across all members. There is **no per-table, per-index, per-statement, or per-connection granularity** — everything is database/instance/bufferpool/tablespace/log level only.

### 4.1 `query_instance` — `MON_GET_INSTANCE` (`ibm_db2.py:127-131`, `queries.py:15-17`)

SQL: `SELECT total_connections FROM TABLE(MON_GET_INSTANCE(-1))`

| Metric | Type | Source column | Notes |
|---|---|---|---|
| `ibm_db2.connection.active` | gauge | `total_connections` | unit `connection`. "current number of connections" |

### 4.2 `query_database` — `MON_GET_DATABASE` (`ibm_db2.py:133-190`, `queries.py:20-40`)

SQL: `SELECT appls_cur_cons, appls_in_db2, connections_top, current timestamp AS current_time, db_status, deadlocks, last_backup, lock_list_in_use, lock_timeouts, lock_wait_time, lock_waits, num_locks_held, num_locks_waiting, rows_modified, rows_read, rows_returned, total_cons FROM TABLE(MON_GET_DATABASE(-1))`

Note: `current timestamp AS current_time` is a SQL special register, not a `MON_GET_DATABASE` column — used only to compute backup age.

| Metric | Type | Source column(s) / formula | Unit | Code |
|---|---|---|---|---|
| (service check) `ibm_db2.status` | service_check | `db_status` via `status_to_service_check` | — | `:137` |
| `ibm_db2.application.active` | gauge | `appls_cur_cons` | connection | `:140` |
| `ibm_db2.application.executing` | gauge | `appls_in_db2` | connection | `:143` |
| `ibm_db2.connection.max` | gauge | `connections_top` | connection | `:146` |
| `ibm_db2.connection.total` | monotonic_count | `total_cons` | connection | `:149` |
| `ibm_db2.lock.dead` | monotonic_count | `deadlocks` | lock | `:152` |
| `ibm_db2.lock.timeouts` | monotonic_count | `lock_timeouts` | lock | `:155` |
| `ibm_db2.lock.active` | gauge | `num_locks_held` | lock | `:158` |
| `ibm_db2.lock.waiting` | gauge | `num_locks_waiting` | lock | `:161` |
| `ibm_db2.lock.wait` | gauge | `lock_wait_time / lock_waits` (0 if `lock_waits` falsy) | millisecond | `:165-169` |
| `ibm_db2.lock.pages` | gauge | `lock_list_in_use / 4096` | page (4 KiB) | `:173` |
| `ibm_db2.backup.latest` | gauge | `(current_time - last_backup).total_seconds()`, else `-1` | second | `:176-181` |
| `ibm_db2.row.modified.total` | monotonic_count | `rows_modified` | row | `:184` |
| `ibm_db2.row.reads.total` | monotonic_count | `rows_read` | row | `:187` |
| `ibm_db2.row.returned.total` | monotonic_count | `rows_returned` | row | `:190` |

`ibm_db2.lock.pages`: `lock_list_in_use` is reported in **bytes**; dividing by 4096 converts to 4 KiB pages (the LOCKLIST cfg unit). `ibm_db2.lock.wait` is **average** ms per wait (running totals divided), not instantaneous.

### 4.3 `query_buffer_pool` — `MON_GET_BUFFERPOOL` (`ibm_db2.py:192-377`, `queries.py:43-79`)

SQL: `SELECT <32 columns> FROM TABLE(MON_GET_BUFFERPOOL(NULL, -1))` — one row **per buffer pool**.

Columns selected (`queries.py:44-78`): `bp_name`, plus `pool_async_{col,data,index,xda}_lbp_pages_found`, `pool_{col,data,index,xda}_gbp_l_reads`, `pool_{col,data,index,xda}_gbp_p_reads`, `pool_{col,data,index,xda}_l_reads`, `pool_{col,data,index,xda}_lbp_pages_found`, `pool_{col,data,index,xda}_p_reads`, `pool_temp_{col,data,index,xda}_l_reads`, `pool_temp_{col,data,index,xda}_p_reads`.

**Tag added:** `bufferpool:<bp_name>` (`ibm_db2.py:197-198`) plus `self._tags`.

For each of the four page classes (`column`, `data`, `index`, `xda`), the code computes (using `column` as the example, `:204-225`):
- `*_reads_physical = pool_<x>_p_reads + pool_temp_<x>_p_reads` → `bufferpool.<x>.reads.physical` (monotonic_count)
- `*_reads_logical = pool_<x>_l_reads + pool_temp_<x>_l_reads` → `bufferpool.<x>.reads.logical` (monotonic_count)
- `bufferpool.<x>.reads.total = physical + logical` (monotonic_count)
- `pages_found = pool_<x>_lbp_pages_found - pool_async_<x>_lbp_pages_found`
- `bufferpool.<x>.hit_percent = pages_found / reads_logical * 100` (gauge, 0 if reads_logical falsy)

Group (pureScale GBP) variants, only emitted when `*_gbp_l_reads` is truthy (all marked `# no cov` — not exercised in the single-node test container):
- `group_<x>_reads_logical = pool_<x>_gbp_l_reads or 0`
- `group_<x>_pages_found = group_<x>_reads_logical - (pool_<x>_gbp_p_reads or 0)`
- `bufferpool.group.<x>.hit_percent` (gauge)

**Aggregate (all four classes summed)** (`:348-377`):
- `bufferpool.reads.physical`, `bufferpool.reads.logical`, `bufferpool.reads.total` (monotonic_count)
- `bufferpool.hit_percent` (gauge)
- `bufferpool.group.hit_percent` (gauge, pureScale-only `# no cov`)

Resulting buffer-pool metrics (each per `bufferpool:` tag):

| Metric | Type |
|---|---|
| `ibm_db2.bufferpool.column.reads.physical` / `.logical` / `.total` | count |
| `ibm_db2.bufferpool.column.hit_percent` | gauge |
| `ibm_db2.bufferpool.data.reads.physical` / `.logical` / `.total` | count |
| `ibm_db2.bufferpool.data.hit_percent` | gauge |
| `ibm_db2.bufferpool.index.reads.physical` / `.logical` / `.total` | count |
| `ibm_db2.bufferpool.index.hit_percent` | gauge |
| `ibm_db2.bufferpool.xda.reads.physical` / `.logical` / `.total` | count |
| `ibm_db2.bufferpool.xda.hit_percent` | gauge |
| `ibm_db2.bufferpool.reads.physical` / `.logical` / `.total` | count |
| `ibm_db2.bufferpool.hit_percent` | gauge |
| `ibm_db2.bufferpool.group.{column,data,index,xda,}.hit_percent` | gauge (pureScale only, not in metadata.csv except `group.{...}.hit_percent`) |

Note: `bufferpool.group.*.hit_percent` metrics **are** declared in `metadata.csv:13-17` but are only emitted in pureScale.

### 4.4 `query_table_space` — `MON_GET_TABLESPACE` (`ibm_db2.py:379-412`, `queries.py:82-91`)

SQL: `SELECT tbsp_name, tbsp_page_size, tbsp_state, tbsp_total_pages, tbsp_usable_pages, tbsp_used_pages FROM TABLE(MON_GET_TABLESPACE(NULL, -1))` — one row **per table space**.

**Tag added:** `tablespace:<tbsp_name>` (`ibm_db2.py:385-386`) plus `self._tags`.

| Metric | Type | Formula | Unit |
|---|---|---|---|
| `ibm_db2.tablespace.size` | gauge | `tbsp_total_pages * tbsp_page_size` | byte |
| `ibm_db2.tablespace.usable` | gauge | `tbsp_usable_pages * tbsp_page_size` | byte |
| `ibm_db2.tablespace.used` | gauge | `tbsp_used_pages * tbsp_page_size` | byte |
| `ibm_db2.tablespace.utilized` | gauge | `tbsp_used_pages / tbsp_usable_pages * 100` (0 if usable falsy) | percent |

`tbsp_state` drives the `tablespace_state_change` event (§7), no metric.

### 4.5 `query_transaction_log` — `MON_GET_TRANSACTION_LOG` (`ibm_db2.py:414-441`, `queries.py:94-98`)

SQL: `SELECT log_reads, log_writes, total_log_available, total_log_used FROM TABLE(MON_GET_TRANSACTION_LOG(-1))`

`block_size = 4096` hard-coded (`:418`).

| Metric | Type | Formula | Unit |
|---|---|---|---|
| `ibm_db2.log.used` | gauge | `total_log_used / 4096` | block (4 KiB) |
| `ibm_db2.log.available` | gauge | `total_log_available / 4096`; if `available == -1` (infinite log) → `0` | block (4 KiB) |
| `ibm_db2.log.utilized` | gauge | `total_log_used / total_log_available * 100`; `0` if infinite | percent |
| `ibm_db2.log.reads` | monotonic_count | `log_reads` | read |
| `ibm_db2.log.writes` | monotonic_count | `log_writes` | write |

Note bug-adjacent behavior: when `available == -1`, `available` is left at `-1` for the divide check then set to `utilized=0`; the gauge `log.available` is then submitted as `0` (the `available /= block_size` only runs in the else branch — `:428-434`).

### 4.6 Full metric inventory

`metadata.csv` declares **49 metrics** (`metadata.csv:2-50`). Test coverage list `STANDARD` in `tests/metrics.py:4-49` enumerates **44** metrics actually asserted in the single-node container (the 5 `bufferpool.group.*` are pureScale-only and not asserted). `test_integration_e2e.py::_assert_standard` calls `aggregator.assert_all_metrics_covered()` against that list, all tagged `db:datadog` + `foo:bar`.

Metric type summary: counts are emitted as `monotonic_count` (raw cumulative counters from MON_GET); declared in `metadata.csv` as type `count`. Gauges are point-in-time or computed ratios.

---

## 5. Tags

- Global (every metric/event/service check): `db:<db>` (auto-added `ibm_db2.py:48`) + any user `tags`.
- Buffer-pool metrics also get `bufferpool:<bp_name>`.
- Table-space metrics also get `tablespace:<tbsp_name>`.
- No `host`/instance/member/partition tag is added by the check itself (host comes from the Agent hostname). No `wlm`/workload, application, schema, table, or query-signature dimensions.
- `disable_generic_tags` / `enable_legacy_tags_normalization` options exist (base-check behaviors; `enable_legacy_tags_normalization` default `True`, added in 4.3.0 to preserve hyphens — `config_models/defaults.py:23-24`, `CHANGELOG.md`).

---

## 6. Service checks

Defined in `assets/service_checks.json` and emitted in code:

1. **`ibm_db2.can_connect`** (`SERVICE_CHECK_CONNECT`, `ibm_db2.py:31`). Emitted by `emit_connection_service_checks` (`:580-589`) on **every** check run and on reconnect attempts. `OK` if `self._conn` is not None, else `CRITICAL` with message `"Unable to create new connection to database: <db>"`. Statuses: ok, critical. Tested `tests/test_unit.py:65-70`.
2. **`ibm_db2.status`** (`SERVICE_CHECK_STATUS`, `ibm_db2.py:32`). Emitted in `query_database` (`:137`) from `db_status` via `status_to_service_check` (`utils.py:23-24`). Statuses: ok, warning, critical, unknown.

`DB_STATUS_MAP` (`utils.py:13-20`):
| `db_status` | ServiceCheck |
|---|---|
| `ACTIVE` | OK |
| `QUIESCE_PEND` | WARNING |
| `QUIESCED` | CRITICAL |
| `ROLLFWD` | WARNING |
| `ACTIVE_STANDBY` | OK |
| `STANDBY` | OK |
| (anything else) | UNKNOWN |

Both service checks carry `host` + `db` groups (`service_checks.json`).

---

## 7. Events

- **`ibm_db2.tablespace_state_change`** (`EVENT_TABLE_SPACE_STATE`, `ibm_db2.py:33`). `manifest.json` declares `creates_events: true`.
- `track_table_space_state_changes` (`ibm_db2.py:536-552`): keeps in-memory `self._table_space_states[name]`; if the state changes between runs, emits an `info` event titled "Table space state change", text `State of \`<name>\` changed from \`<prev>\` to \`<new>\`.`, `source_type_name='ibm_db2'`, host = Agent hostname, with the tablespace tags.
- State is **per-process memory only** — lost on Agent restart; no persistence. Tested `tests/test_integration.py:46-53`.

---

## 8. Custom queries (`query_custom`, `ibm_db2.py:443-534`)

- Per-instance `custom_queries` and `init_config.global_custom_queries`, merged via `use_global_custom_queries` (`true`|`false`|`extend`, default `'true'` — `ibm_db2.py:56-66`, `defaults.py:43-44`). `iter_unique` dedups (`ibm_db2.py:66`). `only_custom_queries: true` is a documented option (`conf.yaml.example:70-74`) but note: **`only_custom_queries` is read from config but the built-in query methods are not actually gated on it in `ibm_db2.py`** — `_query_methods` always includes the five built-ins. (The option appears in `InstanceConfig` and defaults but the check never branches on `self.instance.get('only_custom_queries')`.)
- Each query needs `metric_prefix`, `query`, `columns`; optional `tags`. Columns map to submission methods (`gauge`/`count`/`rate`/`monotonic_count`/...) or `type: tag`. Uses `ibm_db.fetch_tuple`. All-or-nothing per row (`for/else` at `:530-534`). Values coerced with `float()`.
- Sample (`conf.yaml.example:109-118`): `SELECT files_closed, tbsp_name FROM TABLE(MON_GET_TABLESPACE(NULL, -1))` → `ibm_db2.tablespace.files_closed`. Tested `tests/test_integration.py:56-113`.

---

## 9. Config options (full list)

From `config_models/instance.py:44-67`, defaults in `config_models/defaults.py`, spec `assets/configuration/spec.yaml`, sample `conf.yaml.example`:

**Instance (required):** `db` (str), `username` (str), `password` (str, secret).

**Instance (optional):**
| Option | Type | Default | Source |
|---|---|---|---|
| `host` | str | none (uses DSN) | spec:38 |
| `port` | int | `50000` | defaults:35 |
| `security` | `none`\|`ssl` | `none` | defaults:39 |
| `tls_cert` | str | — | spec:61 |
| `connection_timeout` | int | `10` (sec) | defaults:11 |
| `only_custom_queries` | bool | `false` | defaults:31 (⚠ not enforced in code) |
| `use_global_custom_queries` | str | `'true'` | defaults:43 |
| `custom_queries` | list | — | spec:76 |
| `tags` | list | — | spec |
| `service` | str | — | instance + shared |
| `min_collection_interval` | float | `15` | defaults:27 |
| `empty_default_hostname` | bool | `false` | defaults:19 |
| `disable_generic_tags` | bool | `false` | defaults:15 |
| `enable_legacy_tags_normalization` | bool | `true` | defaults:23 (new in 4.3.0) |
| `metric_patterns` | include/exclude regex | — | instance.py:57 |

**init_config (shared):** `global_custom_queries` (list), `service` (str) — `config_models/shared.py:29-30`.

`config_models/validators.py` is the template stub (no custom validators).

---

## 10. Logs pipeline

- `assets/logs/ibm_db2.yaml`: grok pipeline for `db2diag.log`. Parses timestamp, recordID, PID/TID/PROC, INSTANCE/NODE/DB, APPHDL/APPID, AUTHID/HOSTNAME, EDUID/EDUNAME, FUNCTION (prodName/compName/name/probe), MESSAGE, CALLED/OSERR, RETCODE, ARG. Facets: `db.instance`, `logger.name`, `db.recordID`, `function.compName`, `function.name`, `db.partition`. Status remapper on `level`.
- Config sample for log tailing of `/home/db2inst1/sqllib/db2dump/db2diag.log` with a multi-line rule (`conf.yaml.example:175-183`, `README.md:135-145`).
- `assets/logs/ibm_db2_tests.yaml` exists for pipeline tests.

---

## 11. Dashboard (`assets/dashboards/overview.json`)

Title "IBM Db2 Overview", `layout_type: free`, template vars `$host` and `$db`. 29 top-level widgets (several `note`/`image` decoration). Metric-backed widgets:

| Widget | Type | Query |
|---|---|---|
| Database status | check_status | `ibm_db2.status` |
| Time since last backup | query_value | `avg:ibm_db2.backup.latest{$host,$db}` |
| Table space utilization | toplist | `top(avg:ibm_db2.tablespace.utilized{} by {tablespace},10,...)` |
| Buffer pool cache hit ratio | query_value | `avg:ibm_db2.bufferpool.hit_percent{}` |
| Max simultaneous connections | query_value | `avg:ibm_db2.connection.max{}` |
| Log utilization | query_value | `avg:ibm_db2.log.utilized{}` |
| Active connections | query_value | `avg:ibm_db2.connection.active{}` |
| Established connections | timeseries | `ibm_db2.connection.total.as_count()` |
| Deadlocks | timeseries | `ibm_db2.lock.dead.as_count()` |
| Average lock wait | query_value | `ibm_db2.lock.wait` |
| Lock timeouts | timeseries | `ibm_db2.lock.timeouts.as_count()` |
| Active Connections | timeseries | `connection.max`, `connection.active` |
| Average Tablespace Usage | timeseries | `tablespace.usable`, `tablespace.used` |
| Total Row Reads and Updates | timeseries | `row.modified.total`, `row.reads.total` (.as_count) |
| Log Utilization | timeseries | `log.available`, `log.used` |
| Total Column/Data/Index/XDA Reads | timeseries (×4) | `bufferpool.<x>.reads.total.as_count()` |
| Log Reads and Writes | timeseries | `log.reads`, `log.writes` (.as_count) |
| Total Bufferpool Reads | timeseries | `bufferpool.reads.total.as_count()` |

`metadata.path` check metric `ibm_db2.connection.active` (`manifest.json:48`). Source type id `10054`. Dataflows `assets/dataflows.yaml`: provides metrics, logs, events (no DBM data type).

---

## 12. Tests

- `tests/test_unit.py`: password scrubber, reconnect/fail-reconnect, OK-on-every-run, query error swallowing, ConnectionError propagation, `parse_version`, `get_connection_data` string building.
- `tests/test_integration.py`: bad config → CRITICAL; bufferpool/tablespace tag prefixes; tablespace state-change event; custom queries (instance + init_config); metadata version.
- `tests/test_integration_e2e.py`: `test_standard` asserts all `metrics.STANDARD` covered with `db:datadog`+`foo:bar`; `test_e2e` via `dd_agent_check(rate=True)`.
- `tests/test_bench.py`: benchmarks `check`.
- `tests/conftest.py` `DbManager`: creates db `datadog` (UTF-8/us), enables monitor switches (`HEALTH_MON`, `DFT_MON_STMT`, `DFT_MON_LOCK`, `DFT_MON_TABLE`, `DFT_MON_BUFPOOL`), takes a backup (quiesce → deactivate → backup → activate → unquiesce). E2E installs `ibm_db==3.2.6` (`common.py:36`).
- Test image: `taskana/db2:${DB2_VERSION}` (`tests/docker/docker-compose.yaml:5`), `LICENSE=accept`. **`hatch.toml` test matrix pins `DB2_VERSION=11.1`, Python 3.13** (`hatch.toml:5-8`) — the CI matrix does **not** test 12.1.
- Test creds: db `datadog`, user `db2inst1`/`db2inst1-pwd`, port `50000` (`tests/common.py`).

---

## 13. Required Db2 privileges (operator setup)

`README.md:58-106`: read-only user recommended; needs `EXECUTE` on the five table functions, or one of `DATAACCESS`/`DBADM`/`SQLADM`. Must enable monitor switches `HEALTH_MON`, `DFT_MON_STMT`, `DFT_MON_LOCK`, `DFT_MON_TABLE`, `DFT_MON_BUFPOOL` via `update dbm cfg`.

---

## 14. Limitations vs a high-fidelity DBM integration (candid)

Comparison baseline: `postgres`/`sqlserver`/`mysql` DBM checks expose query-level metrics, normalized query samples, execution plans, wait events, active sessions, and schema metadata via `DBMAsyncJob` collectors. The current `ibm_db2` check has **none** of that. Concrete gaps:

**No DBM / query-level observability at all**
- No statement metrics. No use of `MON_GET_PKG_CACHE_STMT` / `MON_GET_PKG_CACHE_STMT_DETAILS` (the Db2 equivalent of `pg_stat_statements`), so no per-query exec count, CPU time, rows read, total/avg exec time, sort time, etc.
- No query text collection, no SQL obfuscation/normalization (no `datadog_checks.base.utils.db.sql` usage), no query signatures.
- No execution plans. Db2 exposes `EXPLAIN` / `db2exfmt` / `MON_GET_PKG_CACHE_STMT` `STMT_TEXT` + section actuals, none captured.
- No active session / activity sampling. No use of `MON_GET_ACTIVITY` / `MON_GET_AGENT` / `WLM_GET_WORKLOAD_OCCURRENCE_ACTIVITIES` / `SYSIBMADM.MON_CURRENT_SQL` / `MON_GET_UNIT_OF_WORK`. No "what is running right now" / blocking-tree / wait-event data.
- No wait-event taxonomy. Db2 `MON_GET_*` `*_WAIT_TIME` / `MON_GET_DATABASE` time-spent elements (e.g. `total_wait_time`, `lock_wait_time`, `log_disk_wait_time`, `pool_read_time`) are largely unused — only an aggregate average `lock.wait` is derived.

**No async / decoupled collection**
- Everything runs synchronously inside one `check()` on the default `min_collection_interval` (15s). DBM checks run heavy collectors (samples, statements, plans) on independent schedules via `DBMAsyncJob` with their own intervals and rate limiting. No such separation here.

**Coarse granularity / missing dimensions**
- Metrics are aggregated to instance/database/bufferpool/tablespace/log only. **No per-table, per-index, per-schema, per-application, per-connection, per-workload (WLM), or per-member/partition metrics**, despite `MON_GET_TABLE`, `MON_GET_INDEX`, `MON_GET_CONNECTION`, `MON_GET_WORKLOAD`, `MON_GET_SERVICE_SUBCLASS`, `MON_GET_MEMORY_POOL/SET`, `MON_GET_EXTENT_MOVEMENT_STATUS`, `MON_GET_HADR` all being available.
- No partition/member tag — `-1`/`NULL` arg always aggregates across members, so multi-member (DPF) / pureScale topologies are flattened. pureScale GBP metrics exist but are emitted untagged-by-member.

**No schema / metadata collection**
- No table/column/index inventory, no `SYSCAT.*` catalog scraping, no schema snapshots (DBM "Database Monitoring → schemas"). No `dbms_metadata` equivalent.

**No HADR / replication / availability metrics**
- `MON_GET_HADR` (log gap, replay delay, standby state, connection status) not collected, despite the `db_status` map having `STANDBY`/`ACTIVE_STANDBY` entries. No log-shipping lag.

**Connection-handling weaknesses**
- Single persistent unguarded connection; reconnect is best-effort with an acknowledged `# ToDo` (`ibm_db2.py:617-618`). No pool, no health probe, no statement timeout per query, no read-only enforcement. `connection_timeout` only sets `connecttimeout`; no query timeout.
- Connection string can duplicate `security=ssl` when both `security: ssl` and `tls_cert` are set (`ibm_db2.py:599-602`).

**Driver / packaging friction**
- `ibm_db` is a compiled C extension **not bundled** with the Agent; operators must manually `pip install ibm_db` (version-specific per Agent/Python), plus the CLI/ODBC driver. Air-gapped install is a multi-step manual process (`README.md:211-263`). A DBM-grade integration would want this packaged.

**Config / correctness nits**
- `only_custom_queries` is documented and modeled but **not actually honored** by `check()` (built-in queries always run).
- `infinite log` handling submits `log.available = 0` rather than a sentinel, conflating "infinite" with "none".
- Events (tablespace state) are in-memory only and lost across restarts.
- All MON element doc links target the 11.1 Knowledge Center; should be validated against 12.1 element availability/semantics.

**No events/RUM-grade richer signals**
- Only one event type (tablespace state). No lock-escalation, deadlock-detail (participants/victim SQL), config-change, or failover events.

**Version coverage**
- CI tests only against Db2 11.1 (`hatch.toml`). Target 12.1 is untested in-repo; new 12.x MON elements/columns (and column-organized/BLU, `MON_GET_*` additions) are not exercised.

---

## 15. Key file reference index (absolute paths)

- Check logic: `/home/bits/dd/integrations-core/ibm_db2/datadog_checks/ibm_db2/ibm_db2.py`
- SQL: `/home/bits/dd/integrations-core/ibm_db2/datadog_checks/ibm_db2/queries.py`
- Utils (version, status map, scrub): `/home/bits/dd/integrations-core/ibm_db2/datadog_checks/ibm_db2/utils.py`
- Config models: `/home/bits/dd/integrations-core/ibm_db2/datadog_checks/ibm_db2/config_models/{instance,defaults,shared,validators}.py`
- Sample conf: `/home/bits/dd/integrations-core/ibm_db2/datadog_checks/ibm_db2/data/conf.yaml.example`
- Spec: `/home/bits/dd/integrations-core/ibm_db2/assets/configuration/spec.yaml`
- Metrics catalog: `/home/bits/dd/integrations-core/ibm_db2/metadata.csv`
- Service checks: `/home/bits/dd/integrations-core/ibm_db2/assets/service_checks.json`
- Manifest: `/home/bits/dd/integrations-core/ibm_db2/manifest.json`
- Dashboard: `/home/bits/dd/integrations-core/ibm_db2/assets/dashboards/overview.json`
- Logs pipeline: `/home/bits/dd/integrations-core/ibm_db2/assets/logs/ibm_db2.yaml`
- Dataflows: `/home/bits/dd/integrations-core/ibm_db2/assets/dataflows.yaml`
- Tests: `/home/bits/dd/integrations-core/ibm_db2/tests/{test_unit,test_integration,test_integration_e2e,test_bench,common,conftest,metrics}.py`
- Test compose: `/home/bits/dd/integrations-core/ibm_db2/tests/docker/docker-compose.yaml`
- Hatch matrix: `/home/bits/dd/integrations-core/ibm_db2/hatch.toml`
- DBM reference (for contrast): `/home/bits/dd/integrations-core/sqlserver/datadog_checks/sqlserver/{statements,activity,metadata,deadlocks,xe_collection}.py`; `/home/bits/dd/integrations-core/postgres/datadog_checks/postgres/{statements,statement_samples,explain_parameterized_queries,metadata}.py`

### Source links (IBM docs, as cited in code — 11.1 Knowledge Center)
- `MON_GET_INSTANCE`: r0060770; `MON_GET_DATABASE`: r0060769; `MON_GET_BUFFERPOOL`: r0053942; `MON_GET_TABLESPACE`: r0053943; `MON_GET_TRANSACTION_LOG`: r0059253 (all under `SSEPGG_11.1.0/com.ibm.db2.luw.sql.rtn.doc`).
- Monitor element reference root: `https://www.ibm.com/support/knowledgecenter/SSEPGG_11.1.0/com.ibm.db2.luw.admin.mon.doc/doc/r0001140.html`
- Monitor procedures/functions (12.1 / db2oc): `https://www.ibm.com/docs/en/db2oc?topic=views-monitor-procedures-functions`
