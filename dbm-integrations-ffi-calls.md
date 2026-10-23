# DBM Integrations: Agent FFI Surface

The set of Agent FFI calls (`aggregator` and `datadog_agent` modules) that the DBM integrations need, for porting to a new IPC framework.

- Integrations: `postgres`, `mysql`, `sqlserver`, `mongo`, `clickhouse` (all subclass `DatabaseCheck`).
- Includes calls made by integration code, shared `datadog_checks_base` DB helpers, and the inherited `AgentCheck` / `DatabaseCheck` base classes.
- Out of scope: `datadog_agent.obfuscate_*`.

## 1. Required calls

Fourteen calls in total. "All" means all five integrations.

| # | Call | Signature | Returns | Used by | Volume |
|---|---|---|---|---|---|
| 1 | `aggregator.submit_metric` | `(check, check_id, mtype, name, value, tags, hostname, flush_first_value)` | — | All | Very high: every metric, every run |
| 2 | `aggregator.submit_service_check` | `(check, check_id, name, status, tags, hostname, message)` | — | All | Low: per run |
| 3 | `aggregator.submit_event` | `(check, check_id, event: dict)` | — | mongo | Rare: on replica set state change |
| 4 | `aggregator.submit_event_platform_event` | `(check, check_id, raw_event: str, event_type: str)` | — | All | High: large JSON payloads from async job threads |
| 5 | `datadog_agent.log` | `(message, level)` | — | All | High: every `self.log.*` record |
| 6 | `datadog_agent.get_config` | `(key)` | `Any` | All | Low: init and first run, plus each `set_metadata` / `should_profile_memory` call |
| 7 | `datadog_agent.get_hostname` | `()` | `str` | All | Low: init, cached |
| 8 | `datadog_agent.get_version` | `()` | `str` | All | Medium: embedded in many payloads, partially cached |
| 9 | `datadog_agent.get_host_tags` | `()` | JSON `str` | postgres, mysql, sqlserver, mongo | Low |
| 10 | `datadog_agent.set_check_metadata` | `(check_id, name, value)` | — | All except sqlserver | Low: per run |
| 11 | `datadog_agent.tracemalloc_enabled` | `()` | `bool` | All | Per run and per async job iteration |
| 12 | `datadog_agent.read_persistent_cache` | `(key)` | `str` | clickhouse | Low: job startup |
| 13 | `datadog_agent.write_persistent_cache` | `(key, value)` | — | clickhouse | Per job iteration |
| 14 | `datadog_agent.emit_agent_telemetry` | `(check_name, metric_name, value, metric_type)` | — | postgres | Medium: per collection |

## 2. Values each call must carry

### `submit_metric`: `mtype`

| Type | Needed | Source |
|---|---|---|
| `GAUGE` | ✅ | All |
| `RATE` | ✅ | All (QueryManager `rate` / `temporal_percent`, mysql and mongo type maps, sqlserver perf counters) |
| `COUNT` | ✅ | All (`dd.<dbms>.*` internal metrics, `DBMAsyncJob` counters) |
| `MONOTONIC_COUNT` | ✅ | All except mongo built-ins (QueryManager, mysql map, sqlserver QueryExecutor, mongo custom queries) |
| `HISTOGRAM` | ✅ | All except mongo (`dd.<dbms>.operation.time`, `dd.<dbms>.schema.time`, `dd.<dbms>.*.time`) |
| `HISTORATE`, `COUNTER` | Parity only | Not used by built-in metrics; reachable only through user-defined `custom_queries` types |

`flush_first_value` is part of the signature and must be passed through.

### `submit_event_platform_event`: `event_type`

| Track | Integrations |
|---|---|
| `dbm-samples` | All |
| `dbm-metrics` | All |
| `dbm-activity` | All |
| `dbm-metadata` | All |
| `dbm-health` | postgres, mysql, sqlserver, clickhouse |
| `dbm-column-statistics` | postgres |
| `do-query-results` | postgres, mysql, sqlserver |

### `submit_service_check`: names

`status` is the standard integer (0 = OK, 1 = WARNING, 2 = CRITICAL, 3 = UNKNOWN).

| Integration | Service checks |
|---|---|
| postgres | `postgres.can_connect` |
| mysql | `mysql.can_connect`, `mysql.replication.slave_running`, `mysql.replication.replica_running`, `mysql.replication.group.status` |
| sqlserver | `sqlserver.can_connect`, `sqlserver.database.can_connect` |
| mongo | `mongodb.can_connect` |
| clickhouse | `clickhouse.can_connect` |

### `submit_event`

Mongo only: replica set member state change. The dict keys are `timestamp`, `source_type_name`, `msg_title`, `msg_text`, `host` and `tags`.

### `get_config`: keys

| Key | Caller |
|---|---|
| `integration_tracing`, `integration_tracing_futures`, `integration_profiling` | Base module import (once per process) |
| `log_level` | Logging init (once per process) |
| `integration_trusted_providers`, `integration_ignore_untrusted_file_params`, `integration_file_paths_allowlist`, `integration_security_excluded_checks` | `load_configuration_models` → `security_config` (first run) |
| `enable_metadata_collection` | `set_metadata` |
| `tracemalloc_include`, `tracemalloc_exclude` (and legacy `_whitelist` / `_blacklist`) | `should_profile_memory` (only when `tracemalloc_enabled()` is true) |

### `set_check_metadata`: names

| Integration | Names |
|---|---|
| postgres | `version`, `resolved_hostname` |
| mysql | `version`, `flavor`, `resolved_hostname` |
| mongo | `version`, `modules`, `resolved_hostname`, `cluster_name` |
| clickhouse | `version` (expanded into `version.*` parts) |

### `read_/write_persistent_cache`: keys (clickhouse)

Keys are prefixed by the base class with the check ID. Values are strings holding microsecond timestamps, or JSON for the `*_node_checkpoints` keys.

- `query_metrics_last_checkpoint_microseconds`
- `query_errors_last_checkpoint_microseconds`
- `query_completions_last_checkpoint_microseconds`
- `async_insert_flush_log_last_checkpoint_microseconds`
- `<each key above>_node_checkpoints`

### `emit_agent_telemetry` (postgres)

`check_name` is always `postgres`. `metric_type` is `histogram` or `gauge`. Metric names include `collect_activity_snapshot_ms`, `collect_statement_samples_ms`, `collect_statement_samples_count`, and dynamic `<method>_ms` / `<method>_count` values.

## 3. Not needed

These exist on the base classes but no DBM integration reaches them:

- `aggregator`: `submit_histogram_bucket`, `submit_histogram_bucket_multi`
- `datadog_agent`: `send_log`, `set_external_tags`, `report_issue`, `resolve_issue`, `get_process_start_time`, `get_clustername`, and `emit_agent_telemetry` for generic resources
