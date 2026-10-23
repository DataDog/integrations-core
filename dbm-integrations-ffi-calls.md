# DBM Integrations: Agent FFI Call Matrix
Scope: `postgres`, `mysql`, `sqlserver`, `mongo`, `clickhouse` (all subclass `DatabaseCheck`).
Out of scope: `datadog_agent.obfuscate_*`.
Legend: ✅ called by integration code · 🔷 called only via shared `datadog_checks_base` helpers · — not called
## 1. Matrix
| FFI module | FFI call | Python entry point | postgres | mysql | sqlserver | mongo | clickhouse |
|---|---|---|---|---|---|---|---|
| `aggregator` | `submit_metric` | `gauge`/`count`/`monotonic_count`/`rate`/`histogram`, QueryManager/QueryExecutor transformers | ✅ | ✅ | ✅ | ✅ | ✅ |
| `aggregator` | `submit_service_check` | `service_check` | ✅ | ✅ | ✅ | ✅ | ✅ |
| `aggregator` | `submit_event` | `event` | — | — | — | ✅ | — |
| `aggregator` | `submit_event_platform_event` | `database_monitoring_*`, `event_platform_event` | ✅ | ✅ | ✅ | ✅ | ✅ |
| `aggregator` | `submit_histogram_bucket` | `submit_histogram_bucket` | — | — | — | — | — |
| `datadog_agent` | `get_hostname` | `DatabaseCheck.agent_hostname`, `resolve_db_host`, `DatabaseHealth`, direct | 🔷 | ✅ | ✅ | ✅ | 🔷 |
| `datadog_agent` | `get_version` | `DatabaseCheck.agent_version`, `SchemaCollector.base_event`, `DatabaseHealth`, direct | 🔷 | 🔷 | 🔷 | ✅ | 🔷 |
| `datadog_agent` | `get_host_tags` | `get_agent_host_tags()` | 🔷 | 🔷 | 🔷 | 🔷 | — |
| `datadog_agent` | `emit_agent_telemetry` | direct | ✅ | — | — | — | — |
| `datadog_agent` | `set_check_metadata` | `set_metadata` | ✅ | ✅ | ✅ | ✅ | ✅ |
| `datadog_agent` | `read_persistent_cache` | `read_persistent_cache` | — | — | — | — | ✅ |
| `datadog_agent` | `write_persistent_cache` | `write_persistent_cache` | — | — | — | — | ✅ |
| `datadog_agent` | `get_config` | `AgentCheck` init, `is_metadata_collection_enabled`, `should_profile_memory`, logging | 🔷 | 🔷 | 🔷 | 🔷 | 🔷 |
| `datadog_agent` | `tracemalloc_enabled` | `should_profile_memory()` in `DBMAsyncJob` loop | 🔷 | 🔷 | 🔷 | 🔷 | 🔷 |
| `datadog_agent` | `log` | `AgentLogHandler` (every `self.log.*`) | 🔷 | 🔷 | 🔷 | 🔷 | 🔷 |
| `datadog_agent` | `set_external_tags` | `set_external_tags` | — | — | — | — | — |
| `datadog_agent` | `send_log` | `send_log` | — | — | — | — | — |
> SQL Server's `set_metadata` calls come from the base check's version metadata; the others call it directly (see §5).
## 2. `submit_metric`: metric types per integration
Submission type → in-app type: `gauge`→gauge, `rate`→gauge, `count`→count, `monotonic_count`→count, `histogram`→rate (+ aggregates).
| Submission type | postgres | mysql | sqlserver | mongo | clickhouse | Notes |
|---|---|---|---|---|---|---|
| `gauge` | ✅ | ✅ | ✅ | ✅ | ✅ | Most integration metrics; `dd.<dbms>.schema.tables_count` / `.payloads_count` (SchemaCollector) |
| `rate` | ✅ (QueryManager) | ✅ (status/variable maps, `mysql.performance.*_time`) | ✅ (`PERF_COUNTER_BULK_COUNT` perf counters) | ✅ (`metrics.py` RATE map) | ✅ (via `temporal_percent`) | |
| `count` | ✅ | ✅ | ✅ | 🔷 | ✅ | Internal `dd.<dbms>.*.error`, `dd.<dbms>.async_job.{missed_collection,cancel,inactive_stop,error}` (DBMAsyncJob, all five) |
| `monotonic_count` | ✅ (QueryManager, `pg_stat_statements.dealloc`) | ✅ (`MONOTONIC` map) | ✅ (QueryExecutor) | custom queries only | ✅ (incl. `monotonic_gauge`) | |
| `histogram` | ✅ | ✅ | ✅ | — | ✅ | `dd.<dbms>.operation.time` (`tracked_query`), `dd.<dbms>.schema.time`, `dd.<dbms>.*.time` |
| `historate` / `counter` | — | — | — | — | — | |
QueryManager transformer fan-out: `monotonic_gauge` = `gauge` (`<name>.total`) + `monotonic_count` (`<name>.count`); `temporal_percent` = `rate`; `time_elapsed` = `gauge`.
User-configurable types: `custom_queries` (all), SQL Server `custom_metrics[].type`, Mongo `custom_queries[].metric_type` (`gauge`/`rate`/`count`/`monotonic_count`).
## 3. `submit_event_platform_event`: event track types
| Track type | Python entry point | postgres | mysql | sqlserver | mongo | clickhouse |
|---|---|---|---|---|---|---|
| `dbm-samples` | `database_monitoring_query_sample` | `plan`, `fqt` | `plan`, `fqt` | `plan`, `fqt`, XE `rqt` | `plan`, `fqt`, slow-op explain plans | `fqt`, query completion `plan` |
| `dbm-metrics` | `database_monitoring_query_metrics` | `query_metrics` | `query_metrics` | `query_metrics`, `procedure_metrics` | `query_metrics` | `query_metrics`, `buffer_metrics` |
| `dbm-activity` | `database_monitoring_query_activity` | `activity` | `activity` | `activity`, `deadlocks`, `agent_jobs`, XE `query_completion` / `query_error` | `activity`, `slow_query` | `activity` (samples), `query_completion`, `query_error`, `async_inserts_flush`, `storage_health` |
| `dbm-metadata` | `database_monitoring_metadata` | `database_instance`, `pg_settings`, `pg_extension`, `pg_databases` | `database_instance`, `mysql_variables`, `mysql_databases` | `database_instance`, `sqlserver_configs`, `sqlserver_databases`, `sqlserver_views` | `mongodb_instance`, `mongodb_databases` | `database_instance`, `clickhouse_databases` |
| `dbm-health` | `database_monitoring_health` / `DatabaseHealth.submit_health_event` | ✅ | ✅ | ✅ | — | ✅ |
| `dbm-column-statistics` | `PostgreSql.database_monitoring_column_statistics` | `column_statistics` | — | — | — | — |
| `do-query-results` | `event_platform_event` (Data Observability) | ✅ | ✅ | ✅ | — | — |
Values in cells are the payload `dbm_type` / `kind` discriminators.
`dbm-health` events include `MISSED_COLLECTION` (warning) and `UNKNOWN_ERROR` (error) from `DBMAsyncJob`, plus integration-specific initialization/config events.
## 4. `submit_service_check` / `submit_event`
| Integration | Service checks | Events (`submit_event`) |
|---|---|---|
| postgres | `postgres.can_connect` | — |
| mysql | `mysql.can_connect`, `mysql.replication.slave_running`, `mysql.replication.replica_running`, `mysql.replication.group.status` | — |
| sqlserver | `sqlserver.can_connect`, `sqlserver.database.can_connect` (autodiscovery) | — |
| mongo | `mongodb.can_connect` | Replica set member state change (`action:mongo_replset_member_status_change`, `member_status`, `previous_member_status`, `replset`) |
| clickhouse | `clickhouse.can_connect` | — |
## 5. Other `datadog_agent` calls
| FFI call | Integration | Details |
|---|---|---|
| `emit_agent_telemetry` | postgres | Namespace `postgres`: `<method>_ms` (histogram), `<method>_count` (histogram), `collect_activity_snapshot_ms` (histogram), `collect_statement_samples_ms` (histogram), `collect_statement_samples_count` (gauge), autodiscovery `<metric>_ms` (histogram) |
| `set_check_metadata` | postgres | `version`, `resolved_hostname` |
| `set_check_metadata` | mysql | `version`, `flavor`, `resolved_hostname` |
| `set_check_metadata` | mongo | `version`, `modules`, `resolved_hostname`, `cluster_name` |
| `set_check_metadata` | clickhouse | `version` (`parts` → `calver`) |
| `read_/write_persistent_cache` | clickhouse | Checkpoints (µs): `query_metrics_last_checkpoint_microseconds`, `query_errors_last_checkpoint_microseconds`, `query_completions_last_checkpoint_microseconds`, `async_insert_flush_log_last_checkpoint_microseconds`, plus `<key>_node_checkpoints` (JSON) |
| `get_hostname` | mysql / sqlserver / mongo | mysql: `agent_hostname:` tag; sqlserver: reported hostname fallback; mongo: replica set local-node hostname |
| `get_version` | mongo | `agent_version` / `ddagentversion` in instance, schema, samples, slow-op, query-metrics payloads |
## 6. Inherited from `AgentCheck` / `DatabaseCheck`
These run for every DBM integration regardless of integration code.
| FFI call | Trigger | Frequency | Details |
|---|---|---|---|
| `datadog_agent.get_config` | Module import of `checks/base.py` | Once per process | `integration_tracing`, `integration_tracing_futures`, `integration_profiling` |
| `datadog_agent.get_config` | Logging init | Once per process | `log_level` |
| `datadog_agent.get_hostname` | `AgentCheck.__init__` | Once per check instance | Sets deprecated `self.hostname` |
| `datadog_agent.get_config` | `load_configuration_models` → `security_config` | First run | `integration_trusted_providers`, `integration_ignore_untrusted_file_params`, `integration_file_paths_allowlist`, `integration_security_excluded_checks` |
| `datadog_agent.tracemalloc_enabled` (+ `get_config` for tracemalloc include/exclude) | `run()` and `DBMAsyncJob` loop → `should_profile_memory()` | Every run / job iteration | Memory profiling gate |
| `datadog_agent.get_config` | `set_metadata` → `is_metadata_collection_enabled()` | Per `set_metadata` call | `enable_metadata_collection` |
| `datadog_agent.log` | `AgentLogHandler` | Per log record | All `self.log.*` output |
| `datadog_agent.get_hostname` / `get_version` | `DatabaseCheck.agent_hostname` / `agent_version` | Cached after first access | Used in DBM payloads |
| `aggregator.submit_metric` (`gauge`) | `run()` debug metrics | Per run, when `debug_metrics.metric_contexts` is enabled | Metric limiter context counts |

Available on the base class but not reached by any DBM integration: `emit_agent_telemetry` (genresources), `send_log`, `set_external_tags`, `report_issue`, `resolve_issue`, `get_config('logs_enabled')`, `get_config('proxy')`.
