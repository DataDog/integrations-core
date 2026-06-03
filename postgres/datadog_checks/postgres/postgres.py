# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import contextlib
import copy
import functools
import json as _stdlib_json
import os
import re
import threading
from collections.abc import Mapping
from string import Template
from time import time

import psycopg
from cachetools import TTLCache
from psycopg import sql as psycopg_sql

from datadog_checks.base import AgentCheck
from datadog_checks.base.checks.db import DatabaseCheck
from datadog_checks.base.utils.db import QueryExecutor
from datadog_checks.base.utils.db.core import QueryManager
from datadog_checks.base.utils.db.health import HealthEvent, HealthStatus
from datadog_checks.base.utils.db.utils import (
    default_json_event_encoding,
    tracked_query,
)
from datadog_checks.base.utils.db.utils import resolve_db_host as agent_host_resolver
from datadog_checks.base.utils.serialization import json
from datadog_checks.postgres.connection_pool import (
    AWSTokenProvider,
    AzureTokenProvider,
    LRUConnectionPoolManager,
    PostgresConnectionArgs,
    TokenAwareConnection,
    TokenProvider,
)
from datadog_checks.postgres.data_observability import PostgresDataObservability
from datadog_checks.postgres.discovery import PostgresAutodiscovery
from datadog_checks.postgres.health import PostgresHealth
from datadog_checks.postgres.metadata import PostgresMetadata
from datadog_checks.postgres.metrics_cache import PostgresMetricsCache
from datadog_checks.postgres.relationsmanager import (
    DYNAMIC_RELATION_QUERIES,
    INDEX_BLOAT,
    RELATION_METRICS,
    TABLE_BLOAT,
    RelationsManager,
)
from datadog_checks.postgres.sds.sds_emitter import build_payload, emit_sds_results
from datadog_checks.postgres.statement_samples import PostgresStatementSamples
from datadog_checks.postgres.statements import PostgresStatementMetrics

from .__about__ import __version__
from .config import build_config, sanitize
from .diagnose import run_diagnostics
from .util import (
    ANALYZE_PROGRESS_METRICS,
    AWS_RDS_HOSTNAME_SUFFIX,
    AZURE_DEPLOYMENT_TYPE_TO_RESOURCE_TYPE,
    BUFFERCACHE_METRICS,
    CLUSTER_VACUUM_PROGRESS_METRICS,
    CONNECTION_METRICS,
    CONNECTION_METRICS_BY_DB,
    COUNT_METRICS,
    FUNCTION_METRICS,
    IDLE_TX_LOCK_AGE_METRICS,
    INDEX_PROGRESS_METRICS,
    QUERY_PG_CONTROL_CHECKPOINT,
    QUERY_PG_CONTROL_CHECKPOINT_LT_10,
    QUERY_PG_REPLICATION_SLOTS,
    QUERY_PG_REPLICATION_SLOTS_STATS,
    QUERY_PG_REPLICATION_STATS_METRICS,
    QUERY_PG_STAT_DATABASE,
    QUERY_PG_STAT_DATABASE_CONFLICTS,
    QUERY_PG_STAT_RECOVERY_PREFETCH,
    QUERY_PG_STAT_WAL_RECEIVER,
    QUERY_PG_UPTIME,
    QUERY_PG_WAIT_EVENT_METRICS,
    REPLICATION_METRICS,
    SLRU_METRICS,
    SNAPSHOT_TXID_METRICS,
    SNAPSHOT_TXID_METRICS_LT_13,
    STAT_IO_METRICS,
    STAT_SUBSCRIPTION_METRICS,
    STAT_SUBSCRIPTION_STATS_METRICS,
    STAT_WAL_METRICS,
    STAT_WAL_METRICS_LT_18,
    SUBSCRIPTION_STATE_METRICS,
    VACUUM_PROGRESS_METRICS,
    VACUUM_PROGRESS_METRICS_LT_17,
    WAL_FILE_METRICS,
    DatabaseConfigurationError,
    DatabaseHealthCheckError,  # noqa: F401
    fmt,
    get_schema_field,
    payload_pg_version,
    warning_with_tags,
)
from .version_utils import V9, V9_2, V10, V12, V13, V14, V15, V16, V17, V18, VersionUtils

try:
    import datadog_agent
except ImportError:
    from datadog_checks.base.stubs import datadog_agent

MAX_CUSTOM_RESULTS = 100

PG_SETTINGS_QUERY = "SELECT name, setting FROM pg_settings WHERE name IN (%s, %s, %s, %s)"

# --- Data security analysis (DEMO ONLY) ---------------------------------------
# Tunables for the TABLESAMPLE-based scan used by `data_security.scan_type=sampling`.
DATA_SECURITY_DEFAULT_INTERVAL = 15  # seconds between scan passes
DATA_SECURITY_DEFAULT_MAX_ROWS = 1000  # default per-table LIMIT when entry omits max_rows
DATA_SECURITY_DEFAULT_MIN_ROWS = 0  # default per-table minimum guaranteed rows
DATA_SECURITY_SAMPLING_MIN_PCT_FLOOR = 0.0001  # never below this TABLESAMPLE pct
DATA_SECURITY_SAMPLING_MAX_PCT_CAP = 100.0  # never above this TABLESAMPLE pct
DATA_SECURITY_SAMPLING_BUFFER_MULTIPLIER = 2  # over-sample by Nx then LIMIT
# REPEATABLE seed is generated per scan from time() so each pass gets a fresh
# (but still self-consistent within one query) random draw.


def _compile_data_security_rules(rules, log=None):
    """
    Build a tuple of ``(rule_id, compiled_regex)`` detectors from the
    ``data_security.rules`` config. Each rule entry is expected to be a mapping
    with a ``pattern`` (treated as a regular expression) and a ``rule_id``.
    Invalid entries (missing pattern or uncompilable regex) are skipped with a
    warning. Returns an empty tuple when no usable rule is configured.
    """
    detectors = []
    for rule in rules or ():
        if not isinstance(rule, Mapping):
            if log is not None:
                log.warning("data_security: skipping malformed rule (not a mapping): %r", rule)
            continue
        pattern = rule.get("pattern")
        rule_id = rule.get("rule_id") or "unknown"
        if not pattern:
            if log is not None:
                log.warning("data_security: skipping rule without pattern: %r", rule)
            continue
        try:
            detectors.append((rule_id, re.compile(pattern)))
        except re.error as e:
            if log is not None:
                log.warning("data_security: skipping rule_id=%s with invalid pattern %r: %s", rule_id, pattern, e)
    return tuple(detectors)


def _detect_sensitive_data(rows, detectors=()):
    """
    Walk a list of dict rows and return a (rows_affected, columns_affected,
    matched_kinds) tuple. A row is "affected" if any column value matched any
    of the configured PII detectors; a column is "affected" if it matched at
    least once across the sample. `matched_kinds` is the set of detector
    rule ids that fired at least once on the sample.
    """
    rows_affected = 0
    columns_affected = set()
    matched_kinds = set()
    for row in rows:
        if not isinstance(row, dict):
            continue
        row_has_match = False
        for column, value in row.items():
            if value is None:
                continue
            text = value if isinstance(value, str) else str(value)
            for kind, regex in detectors:
                if regex.search(text):
                    columns_affected.add(column)
                    matched_kinds.add(kind)
                    row_has_match = True
                    break
        if row_has_match:
            rows_affected += 1
    return rows_affected, columns_affected, matched_kinds


# Composed via psycopg.sql so `qualified_table` is a safely quoted Identifier;
# floor/cap/buffer/min_rows/max_rows are inlined as SQL literals, while
# `schema`, `table` and `seed` flow through as %(name)s parameters.
#
# The sample pct is bounded above by max_cap and below by three lower bounds,
# whichever is largest:
#   * a hard floor (min_floor),
#   * one-block-on-average  ->  100 / relpages, so SYSTEM (which samples at
#     page granularity) reliably picks at least one block on a wide table,
#   * min_rows in expectation  ->  min_rows * 100 / reltuples,
#   * max_rows oversample     ->  max_rows * BUFFER * 100 / reltuples.
# GREATEST(_, 1) on pages/reltuples handles tables that were never ANALYZE'd
# (where relpages/reltuples may be 0 or -1).
DATA_SECURITY_SAMPLING_QUERY_TEMPLATE = """
WITH stats AS (
    SELECT
        GREATEST(COALESCE(c.relpages::bigint, 0), 1)   AS pages,
        GREATEST(COALESCE(c.reltuples::bigint, 0), 1)  AS estimated_rows,
        GREATEST(COALESCE(c.reltuples::bigint, 0), 0)  AS estimated_rows_reported
    FROM pg_class c
    JOIN pg_namespace n ON n.oid = c.relnamespace
    WHERE c.relname = %(table)s AND n.nspname = %(schema)s
),
pct AS (
    SELECT LEAST(
        {max_cap}::float,
        GREATEST(
            {min_floor}::float,
            100.0 / pages,
            ({min_rows}::float * 100.0 / estimated_rows),
            ({max_rows}::float * {buffer_multiplier} * 100.0 / estimated_rows)
        )
    ) AS sample_pct
    FROM stats
)
SELECT
    (SELECT estimated_rows_reported FROM stats) AS estimated_rows,
    COALESCE(json_agg(row_to_json(t)), '[]'::json)::text AS rows_json
FROM (
    SELECT * FROM {qualified_table} TABLESAMPLE SYSTEM(
        (SELECT sample_pct FROM pct)
    ) REPEATABLE(%(seed)s)
    LIMIT {max_rows}
) AS t;
"""

# Full scan ignores min_rows / max_rows on purpose — it's an unbounded read of
# the entire relation, intended for tables small enough that a full dump is OK.
# `estimated_rows` is taken from pg_class.reltuples and clamped at 0 to handle
# tables that were never ANALYZE'd (reltuples may be -1).
DATA_SECURITY_FULL_QUERY_TEMPLATE = """
SELECT
    (
        SELECT GREATEST(COALESCE(c.reltuples::bigint, 0), 0)
        FROM pg_class c
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE c.relname = %(table)s AND n.nspname = %(schema)s
    ) AS estimated_rows,
    COALESCE(json_agg(row_to_json(t)), '[]'::json)::text AS rows_json
FROM {qualified_table} AS t;
"""


class PostgreSql(DatabaseCheck):
    """Collects per-database, and optionally per-relation metrics, custom metrics"""

    __NAMESPACE__ = 'postgresql'

    SOURCE_TYPE_NAME = 'postgresql'
    SERVICE_CHECK_NAME = 'postgres.can_connect'
    METADATA_TRANSFORMERS = {'version': VersionUtils.transform_version}

    HA_SUPPORTED = True

    def __init__(self, name, init_config, instances):
        super(PostgreSql, self).__init__(name, init_config, instances)
        self.health = PostgresHealth(self)
        self._resolved_hostname = None
        self._database_identifier = None
        self._agent_hostname = None
        self._database_hostname = None
        self._db = None
        self._cloud_metadata: dict[str, dict] = None
        self.version = None
        self.raw_version = None
        self.system_identifier = None
        self.cluster_name = None
        self.is_aurora = None
        self.wal_level = None
        self._version_utils = VersionUtils()
        self._last_data_security_run = 0.0

        config, validation_result = build_config(self)
        self._config = config
        self._validation_result = validation_result
        # Log validation errors and warnings
        for error in validation_result.errors:
            self.log.error(error)
        for warning in validation_result.warnings:
            self.log.warning(warning)

        self._tags = list(self._config.tags)
        self.add_core_tags()

        # Submit the initialization health event in case the `check` method is never called
        self._submit_initialization_health_event()

        # Abort initializing the check if the config is invalid
        if validation_result.valid is False:
            self.log.error("Configuration validation failed: %s", validation_result.errors)
            raise validation_result.errors[0]

        # Keep a copy of the tags without the internal resource tags so they can be used for paths that don't
        # go through the agent internal metrics submission processing those tags
        self._non_internal_tags = copy.deepcopy(self.tags)
        self.set_resource_tags()
        self.pg_settings = {}
        self._warnings_by_code = {}
        self.db_pool = LRUConnectionPoolManager(
            max_db=self._config.max_connections,
            base_conn_args=self.build_connection_args(),
            statement_timeout=self._config.query_timeout,
            sqlascii_encodings=self._config.query_encodings,
            token_provider=self.build_token_provider(),
        )
        self.metrics_cache = PostgresMetricsCache(self._config)
        self.statement_metrics = PostgresStatementMetrics(self, self._config)
        self.statement_samples = PostgresStatementSamples(self, self._config)
        self.metadata_samples = PostgresMetadata(self, self._config)
        self.data_observability = PostgresDataObservability(self, self._config)
        self._relations_manager = RelationsManager(self._config.relations, self._config.max_relations)
        self._clean_state()
        self._query_manager = QueryManager(self, lambda _: None, queries=[])  # query executor is set later
        self.check_initializations.append(
            lambda: RelationsManager.validate_relations_config(list(self._config.relations))
        )
        self.check_initializations.append(self.set_resolved_hostname_metadata)
        self.check_initializations.append(self._connect)
        self.check_initializations.append(self.load_cluster_name)
        self.check_initializations.append(self.load_version)
        self.check_initializations.append(self.load_system_identifier)
        self.check_initializations.append(self.initialize_is_aurora)
        self.check_initializations.append(self._query_manager.compile_queries)
        self.tags_without_db = [t for t in copy.copy(self.tags) if not t.startswith("db:")]
        self.autodiscovery = self._build_autodiscovery()
        self._dynamic_queries = []
        # _database_instance_emitted: limit the collection and transmission of the database instance metadata
        self._database_instance_emitted = TTLCache(
            maxsize=1,
            ttl=self._config.database_instance_collection_interval,
        )  # type: TTLCache

        self.diagnosis.register(functools.partial(run_diagnostics, self))

        self._cancel_lock = threading.Lock()
        self._is_running = False
        self._cancelled = False

    def database_monitoring_column_statistics(self, raw_event: str):
        self.event_platform_event(raw_event, "dbm-column-statistics")

    @staticmethod
    def _split_qualified_table(table_name):
        # Accepts "schema.table" or "table" (defaults to public schema).
        if "." in table_name:
            schema, table = table_name.split(".", 1)
        else:
            schema, table = "public", table_name
        return schema, table

    def _build_data_security_query(self, schema, table, scan_type, max_rows, min_rows):
        qualified_table = psycopg_sql.Identifier(schema, table)
        if scan_type == "full":
            # Full scan deliberately ignores min_rows / max_rows. We still bind
            # schema/table as params so the query can look up reltuples for the
            # `estimated_rows` column.
            query = psycopg_sql.SQL(DATA_SECURITY_FULL_QUERY_TEMPLATE).format(
                qualified_table=qualified_table,
            )
            return query, {"schema": schema, "table": table}
        if scan_type == "sampling":
            query = psycopg_sql.SQL(DATA_SECURITY_SAMPLING_QUERY_TEMPLATE).format(
                qualified_table=qualified_table,
                min_floor=psycopg_sql.Literal(DATA_SECURITY_SAMPLING_MIN_PCT_FLOOR),
                max_cap=psycopg_sql.Literal(DATA_SECURITY_SAMPLING_MAX_PCT_CAP),
                buffer_multiplier=psycopg_sql.Literal(DATA_SECURITY_SAMPLING_BUFFER_MULTIPLIER),
                min_rows=psycopg_sql.Literal(min_rows),
                max_rows=psycopg_sql.Literal(max_rows),
            )
            params = {"schema": schema, "table": table, "seed": time()}
            return query, params
        return None, None

    def scan_with_sds(self, rows):
        """
        Walk a list of dict rows and scan each column value through the Agent's
        Sensitive Data Scanner (the ``datadog_agent.scan`` binding). A value is
        considered a match when the scanner mutated it (e.g. redacted it).

        Returns the same ``(rows_affected, columns_affected, matched_kinds)``
        tuple as ``_detect_sensitive_data`` so the rest of the pipeline is
        unchanged.

        Note: this relies on the Agent-side default SDS scanner. The
        RC-provided ``data_security.rules`` are intentionally NOT forwarded to
        the scanner here for now.
        """
        rows_affected = 0
        columns_affected = set()
        matched_kinds = set()
        for row in rows:
            if not isinstance(row, dict):
                continue
            row_has_match = False
            for column, value in row.items():
                if value is None:
                    continue
                text = value if isinstance(value, str) else str(value)
                try:
                    self.log.info("data_security: scan_with_sds - input text: %s", text)
                    processed = datadog_agent.scan(text)
                    self.log.info("data_security: scan_with_sds - output text: %s", processed)
                except Exception as e:
                    self.log.debug("data_security: sds scan failed for column=%s: %s", column, e)
                    continue
                if processed is not None and processed != text:
                    columns_affected.add(column)
                    matched_kinds.add("sds")
                    row_has_match = True
            if row_has_match:
                rows_affected += 1
        return rows_affected, columns_affected, matched_kinds

    def _scan_table_for_data_security(
        self, table_name, scan_type, max_rows, min_rows, send_samples, send_sds_results=False, detectors=None
    ):
        schema, table = self._split_qualified_table(table_name)
        query, params = self._build_data_security_query(schema, table, scan_type, max_rows, min_rows)
        if query is None:
            self.log.warning("data_security: unknown scan_type=%r for table=%s, skipping", scan_type, table_name)
            return

        try:
            with self.db() as conn:
                with conn.cursor() as cursor:
                    # The check's CommenterCursor.execute() assumes `query` is a
                    # str and calls .strip() on it, so we have to render the
                    # psycopg.sql.Composable to text ourselves first. Runtime
                    # `%(name)s` placeholders are preserved through as_string
                    # and bound by the cursor as usual.
                    cursor.execute(query.as_string(cursor), params)
                    row = cursor.fetchone()
                    estimated_rows = int(row[0]) if row and row[0] is not None else None
                    rows_json = row[1] if row and row[1] is not None else '[]'
        except psycopg.Error as e:
            self.log.warning("data_security: failed to scan table=%s (%s): %s", table_name, scan_type, e)
            return

        try:
            parsed_rows = json.loads(rows_json) if rows_json else []
        except (TypeError, ValueError):
            parsed_rows = []
        if not isinstance(parsed_rows, list):
            parsed_rows = []

        sample_size = len(parsed_rows)
        # Use the Agent-side Sensitive Data Scanner (datadog_agent.scan) rather than the
        # local regex detectors. _detect_sensitive_data and the RC rule compilation are
        # kept in place for now but no longer drive this scan.
        rows_affected, columns_affected, matched_kinds = self.scan_with_sds(parsed_rows)

        if send_sds_results:
            self._emit_sds_results(
                table_name=table_name,
                schema=schema,
                table=table,
                scan_type=scan_type,
                sample_size=sample_size,
                rows_affected=rows_affected,
                columns_affected=columns_affected,
                matched_kinds=matched_kinds,
            )

        sensitive_data = {
            "estimated_row_count": estimated_rows,
            "sample_size": sample_size,
            "rows_affected": rows_affected,
            "rows_affected_ratio": (rows_affected / sample_size) if sample_size else 0.0,
            "columns_affected": sorted(columns_affected),
            "columns_affected_count": len(columns_affected),
            "matched_kinds": sorted(matched_kinds),
        }

        event_body = {"sensitive_data": sensitive_data}
        if send_samples:
            event_body["sampled_events"] = parsed_rows

        try:
            pretty_json = _stdlib_json.dumps(event_body, indent=2, default=str)
        except (TypeError, ValueError):
            pretty_json = rows_json

        title_parts = [
            "Data security analysis",
            "db={}".format(self.database_identifier),
            "table={}".format(table_name),
            "scan={}".format(scan_type),
        ]
        if scan_type == "sampling":
            title_parts.append("max_rows={}".format(max_rows))
        msg_title = " | ".join(title_parts)

        event_tags = [t for t in self._non_internal_tags if not t.startswith("db:")] + [
            "kind:data_security_analysis",
            "scan_kind:{}".format(scan_type),
            "table:{}".format(table_name),
            "database_instance:{}".format(self.database_identifier),
        ]
        if scan_type == "sampling":
            event_tags.append("max_rows:{}".format(max_rows))
            event_tags.append("min_rows:{}".format(min_rows))

        self.log.info(
            "data_security: scanned table=%s scan_kind=%s estimated_row_count=%s sample_size=%s "
            "rows_affected=%s columns_affected=%s matched_kinds=%s database_instance=%s",
            table_name,
            scan_type,
            estimated_rows,
            sample_size,
            rows_affected,
            sorted(columns_affected),
            sorted(matched_kinds),
            self.database_identifier,
        )
        self.event(
            {
                "timestamp": int(time()),
                "event_type": "postgres.data_security_analysis",
                "source_type_name": self.SOURCE_TYPE_NAME,
                "msg_title": msg_title,
                "msg_text": "%%%\n```json\n{}\n```\n%%%".format(pretty_json),
                "aggregation_key": "postgres-data-security:{}:{}".format(self.database_identifier, table_name),
                "alert_type": "info",
                "priority": "low",
                "host": self.reported_hostname,
                "tags": event_tags,
            }
        )

    def _rds_instance_metadata(self):
        # Derive the RDS DB instance identifier and region from the configured AWS endpoint
        # (e.g. "customers-04.cfxdfe8cpixl.us-west-2.rds.amazonaws.com" -> "customers-04",
        # "us-west-2"). Falls back to the resolved hostname / configured host when the endpoint
        # is not an RDS endpoint, so resource_name is always populated (required by the intake).
        aws = getattr(self._config, "aws", None)
        endpoint = (
            (getattr(aws, "instance_endpoint", None) if aws else None) or self.resolved_hostname or self._config.host
        )
        region = getattr(aws, "region", None) if aws else None
        instance_identifier = endpoint
        if endpoint and AWS_RDS_HOSTNAME_SUFFIX in endpoint:
            parts = endpoint.split(".", 3)
            if len(parts) == 4:
                instance_identifier = parts[0]
                if not region:
                    region = parts[2]
        return instance_identifier, region

    def _emit_sds_results(
        self,
        *,
        table_name,
        schema,
        table,
        scan_type,
        sample_size,
        rows_affected,
        columns_affected,
        matched_kinds,
    ):
        # Map the demo PII detection output onto the shared SdsResultPayload schema and forward it
        # to the sds-intake. This must never break the data_security scan, so all failures are
        # swallowed with a log line.
        try:
            rule_id = ",".join(sorted(matched_kinds)) if matched_kinds else "unknown"
            db_matches = [
                {
                    "rule_id": rule_id,
                    "column_name": column,
                    # The demo detector only tracks aggregate counts, not per-column counts, so we
                    # report the sample-wide affected/total rows for every matched column.
                    "count_matched_rows": rows_affected,
                    "count_total_rows": sample_size,
                }
                for column in sorted(columns_affected)
            ]
            # Nothing sensitive found: skip emitting an empty result.
            if not db_matches:
                return

            # Mimic an agentless RDS-instance scan so the backend routes this through the
            # RdsExtractor: the resource type must be "aws_rds_instance" and the location must
            # be carried in the `rds_table` oneof (the flat database/table fields are ignored
            # for RDS). The scan source defaults to AGENTLESS in build_payload.
            instance_identifier, region = self._rds_instance_metadata()
            # instance_arn is intentionally left unset: we can't build a valid ARN without the AWS
            # account id, and the backend identifies the resource via resource.name (RedAPL lookup),
            # not the ARN. database_name/table_name carry the meaningful location for RDS.
            rds_table = {"database_name": self._config.dbname, "table_name": table}
            scan_result = {
                "duration": 0,
                "db_matches": db_matches,
                "location": {"rds_table": rds_table},
            }
            payload = build_payload(
                resource_type="aws_rds_instance",
                resource_name=instance_identifier,
                scan_results=[scan_result],
                scanner_version=__version__,
                region=region,
                stats={"files_scanned": 1},
            )
            emit_sds_results(self, payload)
            self.log.info(
                "data_security: emitted sds-result for table=%s schema=%s scan_kind=%s matched_columns=%d",
                table_name,
                schema,
                scan_type,
                len(db_matches),
            )
        except Exception:
            self.log.exception("data_security: failed to emit sds-result for table=%s", table_name)

    def _data_security_scan(self):
        # DEMO ONLY: walks the `data_security.tables` list, runs either a full
        # SELECT or a TABLESAMPLE sampling scan against each one, and emits a
        # single Datadog event per table. Each event always carries the
        # `sensitive_data` summary (row/column-level PII hit counts); raw row
        # contents are only included as `sampled_events` when the
        # `data_security.send_samples` flag is enabled.
        cfg = self.instance.get("data_security") or {}
        if not cfg.get("enabled"):
            return
        interval = cfg.get("interval", DATA_SECURITY_DEFAULT_INTERVAL)
        now = time()
        if now - self._last_data_security_run < interval:
            return
        self._last_data_security_run = now

        # POC: ping the new datadog_agent.hello_world binding (backed by the Agent's
        # pkg/util/sds package) when the data_security scan initializes. Guarded with
        # hasattr so it never breaks the scan on Agents without the new binding.
        if hasattr(datadog_agent, "hello_world"):
            datadog_agent.hello_world()

        send_samples = bool(cfg.get("send_samples"))
        # When enabled, also forward findings to the sds-intake as a protobuf SdsResultPayload
        # (DSPM), in addition to the Datadog event emitted per table.
        send_sds_results = bool(cfg.get("send_sds_results"))

        # Build the PII detectors from the user-configured `data_security.rules`
        # (list of {pattern, rule_id}). Falls back to the hardcoded default
        # detector when no usable rule is configured.
        detectors = _compile_data_security_rules(cfg.get("rules"), self.log)

        for entry in cfg.get("tables") or []:
            table_name = entry.get("table_name")
            scan_type = entry.get("scan_type", "sampling")
            max_rows = entry.get("max_rows", DATA_SECURITY_DEFAULT_MAX_ROWS)
            min_rows = entry.get("min_rows", DATA_SECURITY_DEFAULT_MIN_ROWS)
            if not table_name:
                self.log.warning("data_security: skipping entry without table_name: %s", entry)
                continue
            try:
                self._scan_table_for_data_security(
                    table_name, scan_type, max_rows, min_rows, send_samples, send_sds_results, detectors
                )
            except Exception:
                self.log.exception(
                    "data_security: unexpected error scanning table=%s scan_type=%s max_rows=%s min_rows=%s",
                    table_name,
                    scan_type,
                    max_rows,
                    min_rows,
                )

    def _submit_initialization_health_event(self):
        try:
            # Handle the config validation result after we've set tags so those tags are included in the health event
            # TODO: Use the submission debouncer to only send this every 6 hours
            self.health.submit_health_event(
                name=HealthEvent.INITIALIZATION,
                status=(
                    HealthStatus.ERROR
                    if not self._validation_result.valid
                    else HealthStatus.WARNING
                    if self._validation_result.warnings
                    else HealthStatus.OK
                ),
                cooldown_time=60 * 60 * 6,  # 6 hours
                data={
                    "errors": [str(error) for error in self._validation_result.errors],
                    "warnings": self._validation_result.warnings,
                    "initialized_at": self._validation_result.created_at,
                    "config": sanitize(self._config),
                    "instance": sanitize(self.instance),
                    "features": self._validation_result.features,
                },
            )
        except Exception as e:
            self.log.error("Error submitting health event for initialization: %s", e)

    def _build_autodiscovery(self):
        if not self._config.database_autodiscovery.enabled:
            return None

        if not self._config.relations:
            self.log.warning(
                "Database autodiscovery is enabled, but relation-level metrics are not being collected."
                "All metrics will be gathered from global view."
            )

        discovery = PostgresAutodiscovery(
            self,
            self._config.database_autodiscovery.global_view_db,
            self._config.database_autodiscovery,
            self._config.idle_connection_timeout,
        )
        return discovery

    @property
    def tags(self):
        return self._tags

    @property
    def dbms(self):
        # Override the default to return "postgres" instead of "postgresql"
        return "postgres"

    def add_core_tags(self):
        """
        Add tags that should be attached to every metric/event but which require check calculations outside the config.
        """
        self.tags.append("database_hostname:{}".format(self.database_hostname))
        self.tags.append("database_instance:{}".format(self.database_identifier))

    def set_resource_tags(self):
        if self._config.gcp.project_id and self._config.gcp.instance_id:
            self.tags.append(
                "dd.internal.resource:gcp_sql_database_instance:{}:{}".format(
                    self._config.gcp.project_id, self._config.gcp.instance_id
                )
            )
        if self._config.aws.instance_endpoint:
            self.tags.append(
                "dd.internal.resource:aws_rds_instance:{}".format(
                    self._config.aws.instance_endpoint,
                )
            )
        elif AWS_RDS_HOSTNAME_SUFFIX in self.resolved_hostname:
            # allow for detecting if the host is an RDS host, and emit
            # the resource properly even if the `aws` config is unset
            self.tags.append("dd.internal.resource:aws_rds_instance:{}".format(self.resolved_hostname))
        if self._config.azure.deployment_type and self._config.azure.fully_qualified_domain_name:
            deployment_type = self._config.azure.deployment_type
            # some `deployment_type`s map to multiple `resource_type`s
            resource_type = AZURE_DEPLOYMENT_TYPE_TO_RESOURCE_TYPE.get(deployment_type)
            if resource_type:
                self.tags.append(
                    "dd.internal.resource:{}:{}".format(resource_type, self._config.azure.fully_qualified_domain_name)
                )
        # finally, tag the `database_instance` resource for this instance
        # metrics intake will use this tag to add all the tags for the instance
        self.tags.append(
            "dd.internal.resource:database_instance:{}".format(
                self.database_identifier,
            )
        )

    def _new_query_executor(self, queries, db):
        return QueryExecutor(
            functools.partial(self.execute_query_raw, db=db),
            self,
            queries=queries,
            tags=self.tags_without_db,
            hostname=self.reported_hostname,
            track_operation_time=True,
        )

    def execute_query_raw(self, query, db):
        with db() as conn:
            with conn.cursor() as cursor:
                cursor.execute(query)
                rows = cursor.fetchall()
                return rows

    def _close_db(self):
        if self._db:
            try:
                self._db.close()
            except Exception:
                pass
            finally:
                self._db = None

    @contextlib.contextmanager
    def db(self):
        """
        db context manager that yields a healthy connection to the main database
        """
        if not self._db or self._db.closed:
            # if the connection is closed, we need to reinitialize the connection
            self._db = self._new_connection(self._config.dbname)
            # once the connection is reinitialized, we need to reload the pg_settings
            self._load_pg_settings(self._db)
        if self._db.info.status != psycopg.pq.ConnStatus.OK:
            self._db.rollback()
        try:
            yield self._db
        except (psycopg.InterfaceError, InterruptedError):
            # if we get an interface error or an interrupted error,
            # we gracefully close the connection
            self.log.warning(
                "Connection to the database %s has been interrupted, closing connection", self._config.dbname
            )
            self._close_db()
            raise
        except Exception:
            self.log.exception("Unhandled exception while using database connection %s", self._config.dbname)
            raise

    def _connection_health_check(self, conn):
        try:
            # run a simple query to check if the connection is healthy
            # health check should run after a connection is established
            with conn.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchall()
                self.log.debug("Connection health check passed for database %s", conn.info.dbname)
        except psycopg.Error as e:
            err_msg = f"Database {self._config.dbname} connection health check failed: {str(e)}"
            self.log.error(err_msg)
            raise DatabaseHealthCheckError(err_msg)

    @property
    def dynamic_queries(self):
        if self._dynamic_queries:
            return self._dynamic_queries

        if self.version is None:
            self.log.debug("Version set to None due to incorrect identified version, aborting dynamic queries")
            return None

        self.log.debug("Generating dynamic queries")
        queries = []
        per_database_queries = []  # queries that need to be run per database, used for autodiscovery
        if self.version >= V9_2:
            q_pg_stat_database = copy.deepcopy(QUERY_PG_STAT_DATABASE)
            if len(self._config.ignore_databases) > 0:
                q_pg_stat_database["query"] += " WHERE " + " AND ".join(
                    "datname not ilike '{}'".format(db) for db in self._config.ignore_databases
                )
            q_pg_stat_database_conflicts = copy.deepcopy(QUERY_PG_STAT_DATABASE_CONFLICTS)
            if len(self._config.ignore_databases) > 0:
                q_pg_stat_database_conflicts["query"] += " WHERE " + " AND ".join(
                    "datname not ilike '{}'".format(db) for db in self._config.ignore_databases
                )

            if self._config.dbstrict and len(self._config.ignore_databases) == 0:
                q_pg_stat_database["query"] += " WHERE datname in('{}')".format(self._config.dbname)
                q_pg_stat_database_conflicts["query"] += " WHERE datname in('{}')".format(self._config.dbname)
            elif self._config.dbstrict and len(self._config.ignore_databases) > 0:
                q_pg_stat_database["query"] += " AND datname in('{}')".format(self._config.dbname)
                q_pg_stat_database_conflicts["query"] += " AND datname in('{}')".format(self._config.dbname)

            queries.extend(
                [
                    q_pg_stat_database,
                    q_pg_stat_database_conflicts,
                    QUERY_PG_UPTIME,
                ]
            )

        if self.is_aurora and self.wal_level != 'logical':
            self.log.debug("logical wal_level is required to use pg_current_wal_lsn() on Aurora")

        else:
            self.log.debug("Adding control checkpoint metrics")

            if self.version >= V10:
                queries.append(QUERY_PG_CONTROL_CHECKPOINT)

            else:
                queries.append(QUERY_PG_CONTROL_CHECKPOINT_LT_10)

        if self.version >= V10:
            # Wal receiver is not supported on aurora
            # select * from pg_stat_wal_receiver;
            # ERROR:  Function pg_stat_get_wal_receiver() is currently not supported in Aurora
            if self.is_aurora is False:
                queries.append(QUERY_PG_STAT_WAL_RECEIVER)
                if self._config.collect_wal_metrics is not False:
                    # collect wal metrics for pg >= 10 by default (uses pg_ls_waldir via SQL)
                    # unless the user has explicitly disabled it
                    queries.append(WAL_FILE_METRICS)
            if self._config.collect_buffercache_metrics:
                queries.append(BUFFERCACHE_METRICS)
            queries.append(QUERY_PG_REPLICATION_SLOTS)
            queries.append(QUERY_PG_REPLICATION_STATS_METRICS)
            queries.append(VACUUM_PROGRESS_METRICS if self.version >= V17 else VACUUM_PROGRESS_METRICS_LT_17)
            queries.append(STAT_SUBSCRIPTION_METRICS)
            queries.append(QUERY_PG_WAIT_EVENT_METRICS)

        if self.version >= V12:
            queries.append(CLUSTER_VACUUM_PROGRESS_METRICS)
            queries.append(INDEX_PROGRESS_METRICS)

        if self.version >= V13:
            queries.append(ANALYZE_PROGRESS_METRICS)
            queries.append(SNAPSHOT_TXID_METRICS)
        if self.version < V13:
            queries.append(SNAPSHOT_TXID_METRICS_LT_13)
        if self.version >= V14:
            if self.is_aurora is False:
                if self.version >= V18:
                    queries.append(STAT_WAL_METRICS)
                else:
                    queries.append(STAT_WAL_METRICS_LT_18)
            queries.append(QUERY_PG_REPLICATION_SLOTS_STATS)
            queries.append(SUBSCRIPTION_STATE_METRICS)
        if self.version >= V15:
            queries.append(STAT_SUBSCRIPTION_STATS_METRICS)
            queries.append(QUERY_PG_STAT_RECOVERY_PREFETCH)
        if self.version >= V16:
            if self._config.dbm:
                queries.append(STAT_IO_METRICS)

        if self._config.dbm and self._config.locks_idle_in_transaction.enabled:
            query_def = copy.deepcopy(IDLE_TX_LOCK_AGE_METRICS)
            query_def['collection_interval'] = self._config.locks_idle_in_transaction.collection_interval
            max_rows = self._config.locks_idle_in_transaction.max_rows
            query_def['query'] = query_def['query'].format(max_rows=max_rows)
            per_database_queries.append(query_def)

        if not queries:
            self.log.debug("no dynamic queries defined")
            return None

        # Dynamic queries for relationsmanager
        if self._config.relations:
            for query in DYNAMIC_RELATION_QUERIES:
                query = copy.copy(query)
                formatted_query = self._relations_manager.filter_relation_query(query['query'], 'nspname')
                query['query'] = formatted_query
                per_database_queries.append(query)

        if self.autodiscovery:
            self._collect_dynamic_queries_autodiscovery(per_database_queries)
        else:
            queries.extend(per_database_queries)
        self._dynamic_queries.append(self._new_query_executor(queries, db=self.db))
        for dynamic_query in self._dynamic_queries:
            dynamic_query.compile_queries()
        self.log.debug("initialized %s dynamic querie(s)", len(queries))

        return self._dynamic_queries

    def run(self):
        # TODO: move this lock into the base class
        with self._cancel_lock:
            if self._cancelled:
                self.log.debug("run() skipped, check already cancelled")
                return ''
            self._is_running = True
        try:
            return super().run()
        finally:
            needs_finalize = False
            with self._cancel_lock:
                self._is_running = False
                if self._cancelled:
                    needs_finalize = True
            if needs_finalize:
                self.log.debug("Check cancel has been signaled, finalizing now that run() is complete")
                self._finalize()

    def cancel(self):
        """Signal that the check is being unscheduled.

        This method can be called while check() is running on another thread
        (the GIL is released during psycopg I/O). It must not perform any
        destructive operations — closing connections or nulling attributes that
        check() depends on — because that causes a SIGSEGV in libpq when
        check() resumes.

        Destructive cleanup is deferred to _finalize(), which is called either
        here (if the check is idle) or by run()'s finally block (if the check
        is in-flight). The Agent guarantees it will not call run() again after
        cancel().
        """
        self.log.debug("Marking check as cancelled")
        self._cancel_async_jobs()
        needs_finalize = False
        with self._cancel_lock:
            self._cancelled = True
            if not self._is_running:
                needs_finalize = True
        if needs_finalize:
            self.log.debug("cancel() finalizing immediately, check is idle")
            self._finalize()
        else:
            self.log.debug("cancel() deferred finalize, check is still running")

    @property
    def _async_jobs(self):
        """Return the async jobs active for this check's configuration."""
        jobs = []
        if self._config.dbm:
            jobs.extend([self.statement_metrics, self.statement_samples, self.metadata_samples])
        elif self._config.data_observability.enabled:
            jobs.append(self.metadata_samples)
        if self._config.data_observability.enabled:
            jobs.append(self.data_observability)
        return jobs

    def _cancel_async_jobs(self):
        """Signal async jobs to stop. Safe to call while check() is running."""
        for job in self._async_jobs:
            job.cancel()

    def _finalize(self):
        """Tear down check state. Must not run while check() is executing."""
        self.log.debug("Finalizing check: closing connections and clearing state")
        for job in self._async_jobs:
            if job._job_loop_future:
                job._job_loop_future.result()
                job._job_loop_future = None
            job._shutdown()
        self._clean_state()
        self.check_initializations.clear()
        # TODO: move diagnosis cleanup into AgentCheck.cancel() in the base class
        self._diagnosis = None
        self.log.check = None
        self._query_manager = None
        self.health = None
        self._close_db()
        self._close_db_pool()
        self.log.debug("Check cleanup complete")

    def _clean_state(self):
        self.log.debug("Cleaning state")
        self.metrics_cache.clean_state()
        self._dynamic_queries = []

    def _get_debug_tags(self):
        return ['agent_hostname:{}'.format(self.agent_hostname)]

    def _get_replication_role(self):
        with self.db() as conn:
            with conn.cursor() as cursor:
                cursor.execute('SELECT pg_is_in_recovery();')
                role = cursor.fetchone()[0]
                # value fetched for role is of <type 'bool'>
                return "standby" if role else "master"

    def _collect_wal_metrics(self):
        if self.version >= V10:
            # _collect_stats will gather wal file metrics
            # for PG >= V10
            return
        wal_file_age = self._get_local_wal_file_age()
        if wal_file_age is not None:
            self.gauge(
                "wal_age",
                wal_file_age,
                tags=self.tags_without_db,
                hostname=self.reported_hostname,
            )

    def _get_local_wal_file_age(self):
        wal_log_dir = os.path.join(self._config.data_directory, "pg_xlog")
        if not os.path.isdir(wal_log_dir):
            self.log.warning(
                "Cannot access WAL log directory: %s. Ensure that you are "
                "running the agent on your local postgres database.",
                wal_log_dir,
            )
            return None

        all_dir_contents = os.listdir(wal_log_dir)
        all_files = [f for f in all_dir_contents if os.path.isfile(os.path.join(wal_log_dir, f))]

        # files extensions that are not valid WAL files
        exluded_file_exts = [".backup", ".history"]
        all_wal_files = [
            os.path.join(wal_log_dir, file_name)
            for file_name in all_files
            if not any(ext for ext in exluded_file_exts if file_name.endswith(ext))
        ]
        if len(all_wal_files) < 1:
            self.log.warning("No WAL files found in directory: %s.", wal_log_dir)
            return None

        oldest_file = min(all_wal_files, key=os.path.getctime)
        now = time()
        oldest_file_age = now - os.path.getctime(oldest_file)
        return oldest_file_age

    def load_system_identifier(self):
        with self.db() as conn:
            with conn.cursor() as cursor:
                cursor.execute('SELECT system_identifier FROM pg_control_system();')
                self.system_identifier = cursor.fetchone()[0]

    def load_cluster_name(self):
        with self.db() as conn:
            with conn.cursor() as cursor:
                cursor.execute('SHOW cluster_name;')
                self.cluster_name = cursor.fetchone()[0]

    def load_version(self):
        self.raw_version = self._version_utils.get_raw_version(self.db())
        self.version = self._version_utils.parse_version(self.raw_version)
        self.set_metadata('version', self.raw_version)

    def initialize_is_aurora(self):
        if self.is_aurora is None:
            self.is_aurora = self._version_utils.is_aurora(self.db())
        return self.is_aurora

    def _get_wal_level(self):
        with self.db() as conn:
            with conn.cursor() as cursor:
                cursor.execute('SHOW wal_level;')
                wal_level = cursor.fetchone()[0]
                return wal_level

    @property
    def reported_hostname(self):
        # type: () -> str
        if self._config.exclude_hostname:
            return None
        return self.resolved_hostname

    @property
    def resolved_hostname(self):
        # type: () -> str
        if self._resolved_hostname is None:
            if self._config.reported_hostname:
                self._resolved_hostname = self._config.reported_hostname
            else:
                self._resolved_hostname = self.resolve_db_host()
        return self._resolved_hostname

    @property
    def database_identifier(self):
        # type: () -> str
        if self._database_identifier is None:
            template = Template(self._config.database_identifier.template)
            tag_dict = {}
            tags = self.tags.copy()
            # sort tags to ensure consistent ordering
            tags.sort()
            for t in tags:
                if ':' in t:
                    key, value = t.split(':', 1)
                    if key in tag_dict:
                        tag_dict[key] += f",{value}"
                    else:
                        tag_dict[key] = value
            tag_dict['resolved_hostname'] = self.resolved_hostname
            tag_dict['host'] = str(self._config.host)
            tag_dict['port'] = str(self._config.port)
            self._database_identifier = template.safe_substitute(**tag_dict)
        return self._database_identifier

    @property
    def cloud_metadata(self):
        if self._cloud_metadata is None:
            self._cloud_metadata = {
                "aws": self._config.aws.model_dump(),
                "azure": self._config.azure.model_dump(),
                "gcp": self._config.gcp.model_dump(),
            }
        return self._cloud_metadata

    def set_resolved_hostname_metadata(self):
        """
        set_resolved_hostname_metadata cannot be invoked in the __init__ method because it calls self.set_metadata.
        self.set_metadata can only be called successfully after the __init__ method has completed because
        it relies on the metadata manager, which in turn relies on having a check_id set. The Agent only
        sets the check_id after initialization has completed.
        """
        self.set_metadata('resolved_hostname', self._resolved_hostname)

    @property
    def agent_hostname(self):
        # type: () -> str
        if self._agent_hostname is None:
            self._agent_hostname = datadog_agent.get_hostname()
        return self._agent_hostname

    @property
    def database_hostname(self):
        # type: () -> str
        if self._database_hostname is None:
            self._database_hostname = self.resolve_db_host()
        return self._database_hostname

    def resolve_db_host(self):
        return agent_host_resolver(self._config.host)

    def _run_query_scope(self, scope, is_custom_metrics, cols, descriptors, dbname=None):
        if scope is None:
            return None
        if scope == REPLICATION_METRICS or not self.version >= V9:
            log_func = self.log.debug
        else:
            log_func = self.log.warning

        results = None
        is_relations = scope.get('relation') and self._relations_manager.has_relations
        try:
            with self.db() if dbname is None else self.db_pool.get_connection(dbname) as conn:
                with conn.cursor() as cursor:
                    query = fmt.format(scope['query'], metrics_columns=", ".join(cols))
                    with tracked_query(check=self, operation='custom_metrics' if is_custom_metrics else scope['name']):
                        # if this is a relation-specific query, we need to list all relations last
                        if is_relations:
                            schema_field = get_schema_field(descriptors)
                            formatted_query = self._relations_manager.filter_relation_query(query, schema_field)
                            cursor.execute(formatted_query)
                        else:
                            self.log.debug("Running query: %s", str(query))
                            cursor.execute(query.replace(r'%', r'%%'))

                        results = cursor.fetchall()
                        if not results:
                            return None

                        if is_custom_metrics and len(results) > MAX_CUSTOM_RESULTS:
                            self.log.debug(
                                "Query: %s returned more than %s results (%s). Truncating",
                                query,
                                MAX_CUSTOM_RESULTS,
                                len(results),
                            )
                            results = results[:MAX_CUSTOM_RESULTS]

                        if is_relations and len(results) > self._config.max_relations:
                            self.log.debug(
                                "Query: %s returned more than %s results (%s). "
                                "Truncating. You can edit this limit by setting the `max_relations` config option",
                                query,
                                self._config.max_relations,
                                len(results),
                            )
                            results = results[: self._config.max_relations]

                        return results

        except psycopg.errors.FeatureNotSupported as e:
            # This happens for example when trying to get replication metrics from readers in Aurora. Let's ignore it.
            log_func(e)
            self.log.debug("Disabling replication metrics")
            self.is_aurora = False
            self.metrics_cache.replication_metrics = {}
        except psycopg.errors.UndefinedFunction as e:
            log_func(e)
            log_func(
                "It seems the PG version has been incorrectly identified as %s. "
                "A reattempt to identify the right version will happen on next agent run." % self.version
            )
            self._clean_state()
        except (psycopg.ProgrammingError, psycopg.errors.QueryCanceled) as e:
            log_func("Not all metrics may be available: %s" % str(e))
        except psycopg.Error as e:
            log_func(
                "Error while executing query: %s. ",
                e,
            )

            return None

    def _query_scope(self, scope, instance_tags, is_custom_metrics, dbname=None):
        if scope is None:
            return None
        # build query
        cols = list(scope['metrics'])  # list of metrics to query, in some order
        # we must remember that order to parse results

        # A descriptor is the association of a Postgres column name (e.g. 'schemaname')
        # to a tag name (e.g. 'schema').
        descriptors = scope['descriptors']
        results = self._run_query_scope(scope, is_custom_metrics, cols, descriptors, dbname=dbname)
        if not results:
            return None

        # Parse and submit results.

        num_results = 0

        for row in results:
            # A row contains descriptor values on the left (used for tagging), and
            # metric values on the right (used as values for metrics).
            # E.g.: (descriptor, descriptor, ..., value, value, value, value, ...)

            expected_number_of_columns = len(descriptors) + len(cols)
            if len(row) != expected_number_of_columns:
                raise RuntimeError(
                    'Row does not contain enough values: expected {} ({} descriptors + {} columns), got {}'.format(
                        expected_number_of_columns, len(descriptors), len(cols), len(row)
                    )
                )

            descriptor_values = row[: len(descriptors)]
            column_values = row[len(descriptors) :]

            # build a map of descriptors and their values
            desc_map = {name: value for (_, name), value in zip(descriptors, descriptor_values)}

            # Build tags.

            # Add tags from the instance.
            # Special-case the "db" tag, which overrides the one that is passed as instance_tag
            # The reason is that pg_stat_database returns all databases regardless of the
            # connection.
            if not scope['relation'] and not scope.get('use_global_db_tag', False):
                tags = copy.copy(self.tags_without_db)
            elif dbname is not None:
                # if dbname is specified in this function, we are querying an autodiscovered database
                # and we need to tag it
                tags = copy.copy(self.tags_without_db)
                tags.append("db:{}".format(dbname))
            else:
                tags = copy.copy(instance_tags)

            # Add tags from descriptors.
            tags += [("%s:%s" % (k, v)) for (k, v) in desc_map.items()]

            # Submit metrics to the Agent.
            for column, value in zip(cols, column_values):
                name, submit_metric = scope['metrics'][column]
                submit_metric(self, name, value, tags=set(tags), hostname=self.reported_hostname)

                # if relation-level metrics idx_scan or seq_scan, cache it
                if name in ('index_scans', 'seq_scans'):
                    self._cache_table_activity(dbname, desc_map['table'], name, value)

            num_results += 1

        return num_results

    def _cache_table_activity(
        self,
        dbname: str,
        tablename: str,
        metric_name: str,
        value: int,
    ):
        db = dbname if self.autodiscovery else self._config.dbname
        if db not in self.metrics_cache.table_activity_metrics.keys():
            self.metrics_cache.table_activity_metrics[db] = {}
        if tablename not in self.metrics_cache.table_activity_metrics[db].keys():
            self.metrics_cache.table_activity_metrics[db][tablename] = {
                'index_scans': 0,
                'seq_scans': 0,
            }

        self.metrics_cache.table_activity_metrics[db][tablename][metric_name] = value

    def _collect_metric_autodiscovery(self, instance_tags, scopes, scope_type):
        if not self.autodiscovery:
            return

        start_time = time()
        databases = self.autodiscovery.get_items()
        for db in databases:
            try:
                for scope in scopes:
                    self._query_scope(scope, instance_tags, False, dbname=db)
            except Exception as e:
                self.log.error("Error collecting metrics for database %s %s", db, str(e))
        elapsed_ms = (time() - start_time) * 1000
        self.histogram(
            f"dd.postgres.{scope_type}.time",
            elapsed_ms,
            tags=self.tags + self._get_debug_tags(),
            hostname=self.reported_hostname,
            raw=True,
        )
        telemetry_metric = scope_type.replace("_", "", 1)  # remove the first underscore to match telemetry convention
        datadog_agent.emit_agent_telemetry("postgres", f"{telemetry_metric}_ms", elapsed_ms, "histogram")
        if elapsed_ms > self._config.min_collection_interval * 1000:
            self.record_warning(
                DatabaseConfigurationError.autodiscovered_metrics_exceeds_collection_interval,
                warning_with_tags(
                    "Collecting metrics on autodiscovery metrics took %d ms, which is longer than "
                    "the minimum collection interval. Consider increasing the min_collection_interval parameter "
                    "in the postgres yaml configuration.",
                    int(elapsed_ms),
                    code=DatabaseConfigurationError.autodiscovered_metrics_exceeds_collection_interval.value,
                    min_collection_interval=self._config.min_collection_interval,
                ),
            )

    def _collect_dynamic_queries_autodiscovery(self, queries):
        if not self.autodiscovery:
            return

        databases = self.autodiscovery.get_items()
        for dbname in databases:
            db = functools.partial(self.db_pool.get_connection, dbname=dbname)
            self._dynamic_queries.append(self._new_query_executor(queries, db=db))

    def _emit_running_metric(self):
        self.gauge("running", 1, tags=self.tags_without_db, hostname=self.reported_hostname)

    def _collect_stats(self, instance_tags):
        """Query pg_stat_* for various metrics
        If relations is not an empty list, gather per-relation metrics
        on top of that.
        If custom_metrics is not an empty list, gather custom metrics defined in postgres.yaml
        """
        db_instance_metrics = self.metrics_cache.get_instance_metrics(self.version)
        bgw_instance_metrics = self.metrics_cache.get_bgw_metrics(self.version)
        archiver_instance_metrics = self.metrics_cache.get_archiver_metrics(self.version)

        metric_scope = [CONNECTION_METRICS]

        connection_metrics_by_db = copy.deepcopy(CONNECTION_METRICS_BY_DB)
        databases_to_ignore = ""
        if len(self._config.ignore_databases) > 0:
            escaped_databases = ["'{}'".format(db.replace("'", "''")) for db in self._config.ignore_databases]
            databases_to_ignore = "AND datname NOT IN ({})".format(", ".join(escaped_databases))
        connection_metrics_by_db["query"] = connection_metrics_by_db["query"].format(
            ignore_database_filter=databases_to_ignore
        )
        metric_scope.append(connection_metrics_by_db)
        self.log.debug("Connection Metrics by DB query [%s]", connection_metrics_by_db["query"])

        per_database_metric_scope = []

        if self._config.collect_function_metrics:
            # Function metrics are collected from all databases discovered
            per_database_metric_scope.append(FUNCTION_METRICS)
        if self._config.collect_count_metrics:
            # Count metrics are collected from all databases discovered
            per_database_metric_scope.append(COUNT_METRICS)
        if self.version >= V13:
            metric_scope.append(SLRU_METRICS)

        # Do we need relation-specific metrics?
        if self._config.relations:
            relations_scopes = list(RELATION_METRICS)

            if self._config.collect_bloat_metrics:
                relations_scopes.extend([INDEX_BLOAT, TABLE_BLOAT])

            # If autodiscovery is enabled, get relation metrics from all databases found
            if self.autodiscovery:
                self._collect_metric_autodiscovery(
                    instance_tags,
                    scopes=relations_scopes,
                    scope_type='_collect_relations_autodiscovery',
                )
            # otherwise, continue just with dbname
            else:
                metric_scope.extend(relations_scopes)

        replication_metrics = self.metrics_cache.get_replication_metrics(self.version, self.is_aurora)
        if replication_metrics:
            replication_metrics_query = copy.deepcopy(REPLICATION_METRICS)
            replication_metrics_query['metrics'] = replication_metrics
            metric_scope.append(replication_metrics_query)

        results_len = self._query_scope(db_instance_metrics, instance_tags, False)
        if results_len is not None:
            self.gauge(
                "db.count",
                results_len,
                tags=self.tags_without_db,
                hostname=self.reported_hostname,
            )

        self._query_scope(bgw_instance_metrics, instance_tags, False)
        self._query_scope(archiver_instance_metrics, instance_tags, False)

        if self._config.collect_checksum_metrics and self.version >= V12:
            # SHOW queries need manual cursor execution so can't be bundled with the metrics
            with self.db() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("SHOW data_checksums;")
                    enabled = cursor.fetchone()[0]
                    self.count(
                        "checksums.enabled",
                        1,
                        tags=self.tags_without_db + ["enabled:" + "true" if enabled == "on" else "false"],
                        hostname=self.reported_hostname,
                    )
        if self._config.collect_activity_metrics:
            activity_metrics = self.metrics_cache.get_activity_metrics(self.version)
            self._query_scope(activity_metrics, instance_tags, False)

        if per_database_metric_scope:
            # if autodiscovery is enabled, get per-database metrics from all databases found
            if self.autodiscovery:
                self._collect_metric_autodiscovery(
                    instance_tags,
                    scopes=per_database_metric_scope,
                    scope_type='_collect_stat_autodiscovery',
                )
            else:
                # otherwise, continue just with dbname
                metric_scope.extend(per_database_metric_scope)

        for scope in list(metric_scope):
            self._query_scope(scope, instance_tags, False)

        for scope in self._config.custom_metrics:
            self._query_scope(scope, instance_tags, True)

        if self.dynamic_queries:
            for dynamic_query in self.dynamic_queries:
                dynamic_query.execute()

    def build_token_provider(self) -> TokenProvider:
        if self._config.aws.managed_authentication.enabled:
            return AWSTokenProvider(
                host=self._config.host,
                port=self._config.port,
                username=self._config.username,
                region=self._config.aws.region,
                role_arn=self._config.aws.managed_authentication.role_arn,
            )
        elif self._config.azure.managed_authentication.enabled:
            auth_type = self._config.azure.managed_authentication.auth_type
            return AzureTokenProvider(
                auth_type=auth_type,
                client_id=self._config.azure.managed_authentication.client_id,
                tenant_id=self._config.azure.managed_authentication.tenant_id,
                identity_scope=self._config.azure.managed_authentication.identity_scope,
            )
        else:
            return None

    def build_connection_args(self) -> PostgresConnectionArgs:
        if self._config.host == 'localhost' and self._config.password == '':
            return PostgresConnectionArgs(
                application_name=self._config.application_name,
                username=self._config.username,
            )
        else:
            return PostgresConnectionArgs(
                application_name=self._config.application_name,
                username=self._config.username,
                host=self._config.host,
                port=self._config.port,
                password=self._config.password,
                ssl_mode=self._config.ssl,
                ssl_cert=self._config.ssl_cert,
                ssl_root_cert=self._config.ssl_root_cert,
                ssl_key=self._config.ssl_key,
                ssl_password=self._config.ssl_password,
            )

    def _new_connection(self, dbname):
        # TODO: Keeping this main connection outside of the pool for now to keep existing behavior.
        # We should move this to the pool in the future.
        conn_args = self.build_connection_args()
        kwargs = conn_args.as_kwargs(dbname=dbname)

        # Pass the token_provider as a kwarg so it's available to TokenAwareConnection.connect()
        if self.db_pool.token_provider:
            kwargs["token_provider"] = self.db_pool.token_provider

        conn = TokenAwareConnection.connect(**kwargs)
        try:
            self.db_pool._configure_connection(conn)
        except Exception:
            conn.close()
            raise
        return conn

    def _connect(self):
        """
        Get and memoize connections to instances.
        The connection created here will be persistent. It will not be automatically
        evicted from the connection pool.
        """
        with self.db() as conn:
            self._connection_health_check(conn)

    # Reload pg_settings on a new connection to the main db
    def _load_pg_settings(self, db):
        try:
            with db.cursor() as cursor:
                self.log.debug("Running query [%s]", PG_SETTINGS_QUERY)
                cursor.execute(
                    PG_SETTINGS_QUERY,
                    (
                        "pg_stat_statements.max",
                        "track_activity_query_size",
                        "track_io_timing",
                        "shared_preload_libraries",
                    ),
                )
                rows = cursor.fetchall()
                self.pg_settings.clear()
                for setting in rows:
                    name, val = setting
                    self.pg_settings[name] = val
        except psycopg.Error as err:
            self.log.warning("Failed to query for pg_settings: %s", repr(err))
            self.count(
                "dd.postgres.error",
                1,
                tags=self.tags + ["error:load-pg-settings"] + self._get_debug_tags(),
                hostname=self.reported_hostname,
                raw=True,
            )

    def _get_main_db(self):
        """
        Returns a memoized, persistent psycopg connection to `self.dbname`.
        Threadsafe as long as no transactions are used
        :return: a psycopg connection
        """
        # reload settings for the main DB only once every time the connection is reestablished
        conn = self.db_pool.get_connection(
            self._config.dbname,
            persistent=True,
        )

        return conn

    def _close_db_pool(self):
        self.db_pool.close_all()

    def record_warning(self, code, message):
        # type: (DatabaseConfigurationError, str) -> None
        self._warnings_by_code[code] = message

    def _report_warnings(self):
        messages = self._warnings_by_code.values()
        # Reset the warnings for the next check run
        self._warnings_by_code = {}

        for warning in messages:
            self.warning(warning)

    @property
    def dbms_version(self):
        return payload_pg_version(self.version)

    def _send_database_instance_metadata(self):
        if self.database_identifier not in self._database_instance_emitted:
            event = {
                "host": self.reported_hostname,
                "port": self._config.port,
                "database_instance": self.database_identifier,
                "database_hostname": self.database_hostname,
                "agent_version": datadog_agent.get_version(),
                "ddagenthostname": self.agent_hostname,
                "dbms": "postgres",
                "kind": "database_instance",
                "collection_interval": self._config.database_instance_collection_interval,
                'dbms_version': self.dbms_version,
                'integration_version': __version__,
                "tags": [t for t in self._non_internal_tags if not t.startswith('db:')],
                "timestamp": time() * 1000,
                "cloud_metadata": self.cloud_metadata,
                "metadata": {
                    "dbm": self._config.dbm,
                    "connection_host": self._config.host,
                },
            }
            self._database_instance_emitted[self.database_identifier] = event
            self.database_monitoring_metadata(json.dumps(event, default=default_json_event_encoding))

    def debug_stats_kwargs(self, tags=None):
        tags = self.tags + self._get_debug_tags() + (tags or [])
        return {
            'tags': tags,
            "hostname": self.reported_hostname,
        }

    def check(self, _):
        # Resend the initialization event. The submitter will debounce it
        self._submit_initialization_health_event()

        tags = copy.copy(self.tags)
        self.tags_without_db = [t for t in copy.copy(self.tags) if not t.startswith("db:")]
        # Reset _non_internal_tags to prevent stale dynamic tags (e.g., replication_role) from accumulating
        self._non_internal_tags = [t for t in copy.copy(self.tags) if not t.startswith("dd.internal")]
        tags_to_add = []
        try:
            # Check version
            self._connect()
            # We don't want to cache versions between runs to capture minor updates for metadata
            self.load_version()

            # Check wal_level
            self.wal_level = self._get_wal_level()

            # Add raw version as a tag
            tags.append(f'postgresql_version:{self.raw_version}')
            tags_to_add.append(f'postgresql_version:{self.raw_version}')

            # Add system identifier as a tag
            if self.system_identifier:
                tags.append(f'system_identifier:{self.system_identifier}')
                tags_to_add.append(f'system_identifier:{self.system_identifier}')

            # Add cluster name if it was set
            if self.cluster_name:
                tags.append(f'postgresql_cluster_name:{self.cluster_name}')
                tags_to_add.append(f'postgresql_cluster_name:{self.cluster_name}')

            if self._config.tag_replication_role:
                replication_role_tag = "replication_role:{}".format(self._get_replication_role())
                tags.append(replication_role_tag)
                tags_to_add.append(replication_role_tag)
            self._update_tag_sets(tags_to_add)
            self._send_database_instance_metadata()

            self.log.debug("Running check against version %s: is_aurora: %s", str(self.version), str(self.is_aurora))
            self._emit_running_metric()

            if not self._config.only_custom_queries:
                self._collect_stats(tags)
                if not self._cancelled:
                    if self._config.dbm:
                        self.statement_metrics.run_job_loop(tags)
                        self.statement_samples.run_job_loop(tags)
                        self.metadata_samples.run_job_loop(tags)
                    elif self._config.data_observability.enabled:
                        self.metadata_samples.run_job_loop(tags)
                    if self._config.data_observability.enabled:
                        self.data_observability.run_job_loop(tags)
                if self._config.collect_wal_metrics is True:
                    # collect wal metrics for pg < 10 only when explicitly enabled
                    # (requires local filesystem access to the WAL directory)
                    self._collect_wal_metrics()

            if self._query_manager.queries:
                self._query_manager.executor = functools.partial(self.execute_query_raw, db=self.db)
                self._query_manager.execute(extra_tags=tags)

            self._data_security_scan()

        except Exception as e:
            self.log.exception("Unable to collect postgres metrics.")
            self._clean_state()
            message = 'Error establishing connection to postgres://{}:{}/{}, error is {}'.format(
                self._config.host, self._config.port, self._config.dbname, str(e)
            )
            self.service_check(
                self.SERVICE_CHECK_NAME,
                AgentCheck.CRITICAL,
                tags=tags,
                message=message,
                hostname=self.reported_hostname,
                raw=True,
            )
            raise e
        else:
            self.service_check(
                self.SERVICE_CHECK_NAME,
                AgentCheck.OK,
                tags=tags,
                hostname=self.reported_hostname,
                raw=True,
            )
        finally:
            # Add the warnings saved during the execution of the check
            self._report_warnings()

    def _update_tag_sets(self, tags):
        self._non_internal_tags = list(set(self._non_internal_tags) | set(tags))
        self.tags_without_db = list(set(self.tags_without_db) | set(tags))
