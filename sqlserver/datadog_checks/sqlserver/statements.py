# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import binascii
import copy
import math
import time
from typing import Any, Iterator

from cachetools import TTLCache
from lxml import etree as ET

from datadog_checks.base import is_affirmative
from datadog_checks.base.utils.common import ensure_unicode, to_native_string
from datadog_checks.base.utils.db.health import HealthStatus
from datadog_checks.base.utils.db.sql import compute_sql_signature
from datadog_checks.base.utils.db.statement_metrics import StatementMetrics
from datadog_checks.base.utils.db.utils import (
    DBMAsyncJob,
    RateLimitingTTLCache,
    default_json_event_encoding,
    obfuscate_sql_with_metadata,
)
from datadog_checks.base.utils.serialization import json
from datadog_checks.base.utils.tracking import tracked_method
from datadog_checks.sqlserver.config import SQLServerConfig
from datadog_checks.sqlserver.const import STATIC_INFO_ENGINE_EDITION, STATIC_INFO_MAJOR_VERSION, STATIC_INFO_VERSION
from datadog_checks.sqlserver.diagnose import SQLSERVER_DBM_SETUP_DOCS_URL, SYSTEM_DATABASES
from datadog_checks.sqlserver.health import SqlServerHealthEvent
from datadog_checks.sqlserver.utils import (
    is_azure_sql_database,
    needs_comment_recovery,
    raise_if_cancelled,
    read_last_query_plan_stats,
    read_trace_flag_2451,
    supports_last_query_plan_stats,
)

DEFAULT_COLLECTION_INTERVAL = 60

DEFAULT_REAL_PLANS_SAMPLES_PER_HOUR_PER_QUERY = 4
# A real plan adds runtime counters per operator and per thread to its estimated plan, so it can be twice as large at a
# high degree of parallelism.
DEFAULT_REAL_PLAN_MAX_SIZE_BYTES = 1_000_000
# How long the LAST_QUERY_PLAN_STATS setting of each database and trace flag 2451 are trusted before being read again.
LAST_QUERY_PLAN_STATS_REFRESH_INTERVAL = 600
# An actual plan holds at least one of these. Without them, it's a simplified plan with no runtime data.
REAL_PLAN_RUNTIME_ELEMENTS = ("<RunTimeInformation", "<QueryTimeStats")

SQL_SERVER_QUERY_METRICS_COLUMNS = [
    "execution_count",
    "total_worker_time",
    "total_physical_reads",
    "total_logical_writes",
    "total_logical_reads",
    "total_clr_time",
    "total_elapsed_time",
    "total_rows",
    "total_dop",
    "total_grant_kb",
    "total_used_grant_kb",
    "total_ideal_grant_kb",
    "total_reserved_threads",
    "total_used_threads",
    "total_columnstore_segment_reads",
    "total_columnstore_segment_skips",
    "total_spills",
]

STATEMENT_METRICS_QUERY = """\
with qstats as (
    select
        qs.query_hash,
        qs.query_plan_hash,
        qs.last_execution_time,
        qs.last_elapsed_time,
        CONCAT(
            CONVERT(VARCHAR(64), CONVERT(binary(64), qs.plan_handle), 1),
            CONVERT(VARCHAR(10), CONVERT(varbinary(4), qs.statement_start_offset), 1),
            CONVERT(VARCHAR(10), CONVERT(varbinary(4), qs.statement_end_offset), 1)) as plan_handle_and_offsets,
           (select value from sys.dm_exec_plan_attributes(qs.plan_handle) where attribute = 'dbid') as dbid,
           eps.object_id as sproc_object_id,
           {query_metrics_columns}
    from sys.dm_exec_query_stats qs
    left join sys.dm_exec_procedure_stats eps ON eps.plan_handle = qs.plan_handle
),
qstats_aggr as (
    select
        query_hash,
        query_plan_hash,
        CAST(qs.dbid as int) as dbid,
        D.name as database_name,
        max(plan_handle_and_offsets) as plan_handle_and_offsets,
        max(last_execution_time) as last_execution_time,
        max(last_elapsed_time) as last_elapsed_time,
        sproc_object_id,
        {query_metrics_column_sums}
    from qstats qs
    left join sys.databases D on qs.dbid = D.database_id
    group by query_hash, query_plan_hash, qs.dbid, D.name, sproc_object_id
),
qstats_aggr_split as (
    select TOP {limit}
        convert(varbinary(64), convert(binary(64), substring(plan_handle_and_offsets, 1, 64), 1)) as plan_handle,
        convert(int, convert(varbinary(10), substring(plan_handle_and_offsets, 64+1, 10), 1)) as statement_start_offset,
        convert(int, convert(varbinary(10), substring(plan_handle_and_offsets, 64+11, 10), 1)) as statement_end_offset,
        *
    from qstats_aggr
    where DATEADD(ms, last_elapsed_time / 1000, last_execution_time) > dateadd(second, -?, getdate())
)
select
    SUBSTRING(text, (statement_start_offset / 2) + 1,
    ((CASE statement_end_offset
        WHEN -1 THEN DATALENGTH(text)
        ELSE statement_end_offset END
            - statement_start_offset) / 2) + 1) AS statement_text,
    SUBSTRING(qt.text, 1, {proc_char_limit}) as text,
    encrypted as is_encrypted,
    OBJECT_SCHEMA_NAME(s.sproc_object_id, s.dbid) as schema_name,
    OBJECT_NAME(s.sproc_object_id, s.dbid) as procedure_name,
    s.* from qstats_aggr_split s
    cross apply sys.dm_exec_sql_text(s.plan_handle) qt
"""

# This query is an optimized version of the statement metrics query
# which removes the additional database aggregate dimension
STATEMENT_METRICS_QUERY_NO_AGGREGATES = """\
with qstats_aggr as (
    select TOP {limit}
        qs.query_hash,
        qs.query_plan_hash,
        max(CONCAT(
            CONVERT(VARCHAR(64), CONVERT(binary(64), qs.plan_handle), 1),
            CONVERT(VARCHAR(10), CONVERT(varbinary(4), qs.statement_start_offset), 1),
            CONVERT(VARCHAR(10), CONVERT(varbinary(4), qs.statement_end_offset), 1))) as plan_handle_and_offsets,
        eps.object_id as sproc_object_id,
        {query_metrics_column_sums}
        from sys.dm_exec_query_stats qs
        left join sys.dm_exec_procedure_stats eps ON eps.plan_handle = qs.plan_handle
        where qs.last_execution_time > dateadd(second, -?, getdate())
        group by qs.query_hash, qs.query_plan_hash, eps.object_id
),
qstats_aggr_split as (select
    convert(varbinary(64), convert(binary(64), substring(plan_handle_and_offsets, 1, 64), 1)) as plan_handle,
    convert(int, convert(varbinary(10), substring(plan_handle_and_offsets, 64+1, 10), 1)) as statement_start_offset,
    convert(int, convert(varbinary(10), substring(plan_handle_and_offsets, 64+11, 10), 1)) as statement_end_offset,
    * from qstats_aggr
)
select
    SUBSTRING(text, (statement_start_offset / 2) + 1,
        ((CASE statement_end_offset
        WHEN -1 THEN DATALENGTH(text)
        ELSE statement_end_offset
    END - statement_start_offset) / 2) + 1) AS statement_text,
    SUBSTRING(qt.text, 1, {proc_char_limit}) as text,
    encrypted as is_encrypted,
    {database_name_column}
    s.* from qstats_aggr_split s
    cross apply sys.dm_exec_sql_text(s.plan_handle) qt
"""

STATEMENT_METRICS_QUERY_AZURE_SQL_DATABASE = """\
with qstats as (
    select
        qs.query_hash,
        qs.query_plan_hash,
        qs.last_execution_time,
        qs.last_elapsed_time,
        CONCAT(
            CONVERT(VARCHAR(64), CONVERT(binary(64), qs.plan_handle), 1),
            CONVERT(VARCHAR(10), CONVERT(varbinary(4), qs.statement_start_offset), 1),
            CONVERT(VARCHAR(10), CONVERT(varbinary(4), qs.statement_end_offset), 1)) as plan_handle_and_offsets,
           (select value from sys.dm_exec_plan_attributes(qs.plan_handle) where attribute = 'dbid') as dbid,
           eps.object_id as sproc_object_id,
           {query_metrics_columns}
    from sys.dm_exec_query_stats qs
    left join sys.dm_exec_procedure_stats eps ON eps.plan_handle = qs.plan_handle
),
qstats_aggr as (
    select
        query_hash,
        query_plan_hash,
        CAST(qs.dbid as int) as dbid,
        DB_NAME(CAST(qs.dbid as int)) as database_name,
        max(plan_handle_and_offsets) as plan_handle_and_offsets,
        max(last_execution_time) as last_execution_time,
        max(last_elapsed_time) as last_elapsed_time,
        sproc_object_id,
        {query_metrics_column_sums}
    from qstats qs
    group by query_hash, query_plan_hash, qs.dbid, sproc_object_id
),
qstats_aggr_split as (
    select TOP {limit}
        convert(varbinary(64), convert(binary(64), substring(plan_handle_and_offsets, 1, 64), 1)) as plan_handle,
        convert(int, convert(varbinary(10), substring(plan_handle_and_offsets, 64+1, 10), 1)) as statement_start_offset,
        convert(int, convert(varbinary(10), substring(plan_handle_and_offsets, 64+11, 10), 1)) as statement_end_offset,
        *
    from qstats_aggr
    where DATEADD(ms, last_elapsed_time / 1000, last_execution_time) > dateadd(second, -?, getdate())
)
select
    SUBSTRING(text, (statement_start_offset / 2) + 1,
    ((CASE statement_end_offset
        WHEN -1 THEN DATALENGTH(text)
        ELSE statement_end_offset END
            - statement_start_offset) / 2) + 1) AS statement_text,
    SUBSTRING(qt.text, 1, {proc_char_limit}) as text,
    encrypted as is_encrypted,
    OBJECT_SCHEMA_NAME(s.sproc_object_id, s.dbid) as schema_name,
    OBJECT_NAME(s.sproc_object_id, s.dbid) as procedure_name,
    s.* from qstats_aggr_split s
    cross apply sys.dm_exec_sql_text(s.plan_handle) qt
"""

PLAN_LOOKUP_QUERY = """\
select cast(query_plan as nvarchar(max)) as query_plan, encrypted as is_encrypted
from sys.dm_exec_query_plan(CONVERT(varbinary(max), ?, 1))
"""

# The plan's QueryTimeStats are wrong: on SQL Server 2019 and 2022 each statement has the times of the one before, and
# 2025 swaps CPU and elapsed time. So the real plan event takes the last execution's statistics of its statement from
# sys.dm_exec_query_stats, whose times are in microseconds. last_execution_time is in the server's time zone, so it gets
# the server's current UTC offset, as an ISO 8601 string because pyodbc can't read the datetimeoffset type.
REAL_PLAN_LOOKUP_QUERY = """\
select cast(ps.query_plan as nvarchar(max)) as query_plan,
    CONVERT(varchar(34),
        TODATETIMEOFFSET(qs.last_execution_time, DATEPART(TZOFFSET, SYSDATETIMEOFFSET())), 126
    ) as last_execution_time,
    qs.last_elapsed_time, qs.last_worker_time, qs.last_dop, qs.last_grant_kb, qs.last_used_grant_kb, qs.last_spills,
    qs.last_rows
from sys.dm_exec_query_plan_stats(CONVERT(varbinary(max), ?, 1)) ps
outer apply (
    select top 1 last_execution_time, last_elapsed_time, last_worker_time, last_dop, last_grant_kb, last_used_grant_kb,
        last_spills, last_rows
    from sys.dm_exec_query_stats
    where plan_handle = CONVERT(varbinary(max), ?, 1) and statement_start_offset = ? and statement_end_offset = ?
) qs
"""
REAL_PLAN_STATEMENT_STATS_COLUMNS = (
    "last_elapsed_time",
    "last_worker_time",
    "last_dop",
    "last_grant_kb",
    "last_used_grant_kb",
    "last_spills",
    "last_rows",
)


def _row_key(row):
    """
    :param row: a normalized row from STATEMENT_METRICS_QUERY
    :return: a tuple uniquely identifying this row
    """
    return (row.get('database_name'), row['query_signature'], row['query_hash'], row.get('procedure_name'))


XML_PLAN_OBFUSCATION_ATTRS = frozenset(
    {
        "StatementText",
        "ConstValue",
        "ScalarString",
        "ParameterCompiledValue",
        "ParameterRuntimeValue",
    }
)


def agent_check_getter(self):
    return self._check


def _hash_to_hex(hash):
    return to_native_string(binascii.hexlify(hash))


def obfuscate_xml_plan(raw_plan, obfuscator_options=None):
    """
    Obfuscates SQL text & Parameters from the provided SQL Server XML Plan
    Also strips unnecessary whitespace
    """
    parser = ET.XMLParser(resolve_entities=False, load_dtd=False, no_network=True)
    tree = ET.fromstring(raw_plan, parser=parser)
    for e in tree.iter():
        if e.text:
            e.text = e.text.strip()
        if e.tail:
            e.tail = e.tail.strip()
        for k in XML_PLAN_OBFUSCATION_ATTRS:
            val = e.attrib.get(k, None)
            if val:
                statement = obfuscate_sql_with_metadata(val, obfuscator_options, replace_null_character=True)
                e.attrib[k] = ensure_unicode(statement['query'])
    return to_native_string(ET.tostring(tree, encoding="UTF-8"))


class SqlserverStatementMetrics(DBMAsyncJob):
    """Collects query metrics and plans"""

    def __init__(self, check, config: SQLServerConfig):
        # do not emit any dd.internal metrics for DBM specific check code
        self.log = check.log
        self._config = config
        collection_interval = float(
            self._config.statement_metrics_config.get('collection_interval', DEFAULT_COLLECTION_INTERVAL)
        )
        if collection_interval <= 0:
            collection_interval = DEFAULT_COLLECTION_INTERVAL
        self.collection_interval = collection_interval
        super(SqlserverStatementMetrics, self).__init__(
            check,
            run_sync=is_affirmative(self._config.statement_metrics_config.get('run_sync', False)),
            enabled=is_affirmative(self._config.statement_metrics_config.get('enabled', True)),
            expected_db_exceptions=(),
            min_collection_interval=self._config.min_collection_interval,
            dbms=check.dbms,
            rate_limit=1 / float(collection_interval),
            job_name="query-metrics",
            shutdown_callback=self._close_db_conn,
        )
        self.disable_secondary_tags = is_affirmative(
            self._config.statement_metrics_config.get('disable_secondary_tags', False)
        )
        self.dm_exec_query_stats_row_limit = int(
            self._config.statement_metrics_config.get('dm_exec_query_stats_row_limit', 10000)
        )
        self.enforce_collection_interval_deadline = is_affirmative(
            self._config.statement_metrics_config.get('enforce_collection_interval_deadline', True)
        )
        self._state = StatementMetrics()
        self._init_caches()
        self._conn_key_prefix = "dbm-"
        self._statement_metrics_query = None
        self._last_stats_query_time = None
        self._max_query_metrics = self._config.statement_metrics_config.get("max_queries", 250)

        self._collect_execution_plans = is_affirmative(self._config.statement_metrics_config.get('collect_plans', True))
        self._collect_raw_query_statement = self._config.collect_raw_query_statement.get("enabled", False)

        real_plans_config = self._real_plans_config()
        self._collect_real_plans = is_affirmative(real_plans_config.get('enabled', False))
        self._real_plan_max_size_bytes = int(
            real_plans_config.get('max_plan_size_bytes', DEFAULT_REAL_PLAN_MAX_SIZE_BYTES)
        )
        self._real_plans_version_unsupported_warned = False
        # LAST_QUERY_PLAN_STATS of each database whose real plans were looked for, None when it couldn't be read.
        self._last_query_plan_stats_by_db: dict[str, bool | None] = {}
        self._trace_flag_2451 = False
        self._last_query_plan_stats_read_at = 0.0
        # The databases with LAST_QUERY_PLAN_STATS off, so each database's warning is logged once, and the health
        # event goes to warning with the first one and back to OK when the last one is fixed.
        self._last_query_plan_stats_disabled_dbs: set[str] = set()

    def _real_plans_config(self) -> dict:
        return self._config.statement_metrics_config.get('collect_real_plans', {}) or {}

    def _init_caches(self):
        # full_statement_text_cache: limit the ingestion rate of full statement text events per query_signature
        self._full_statement_text_cache = TTLCache(
            maxsize=self._check.instance.get('full_statement_text_cache_max_size', 10000),
            ttl=60 * 60 / self._check.instance.get('full_statement_text_samples_per_hour_per_query', 1),
        )

        # seen_plans_ratelimiter: limit the ingestion rate per unique plan.
        # plans, we only really need them once per hour
        self._seen_plans_ratelimiter = RateLimitingTTLCache(
            # assuming ~100 bytes per entry (query & plan signature, key hash, 4 pointers (ordered dict), expiry time)
            # total size: 10k * 100 = 1 Mb
            maxsize=int(self._check.instance.get('seen_samples_cache_maxsize', 10000)),
            ttl=60 * 60 / int(self._check.instance.get('samples_per_hour_per_query', 4)),
        )

        # seen_real_plans_ratelimiter: limit the ingestion rate of real plans per unique plan, separately from
        # estimated plans.
        real_plans_per_hour = int(
            self._real_plans_config().get('samples_per_hour_per_query', DEFAULT_REAL_PLANS_SAMPLES_PER_HOUR_PER_QUERY)
        )
        self._seen_real_plans_ratelimiter = RateLimitingTTLCache(
            maxsize=int(self._check.instance.get('seen_samples_cache_maxsize', 10000)),
            ttl=60 * 60 / real_plans_per_hour,
        )

    def shutdown(self) -> None:
        self._check = None

    def _close_db_conn(self):
        pass

    def _get_available_query_metrics_columns(self, cursor, all_expected_columns):
        cursor.execute("select top 0 * from sys.dm_exec_query_stats")
        all_columns = {i[0] for i in cursor.description}
        available_columns = [c for c in all_expected_columns if c in all_columns]
        missing_columns = set(all_expected_columns) - set(available_columns)
        if missing_columns:
            self.log.debug(
                "missing the following expected query metrics columns from dm_exec_query_stats: %s", missing_columns
            )
        self.log.debug("found available sys.dm_exec_query_stats columns: %s", available_columns)
        return available_columns

    def _get_statement_metrics_query_cached(self, cursor):
        if self._statement_metrics_query:
            return self._statement_metrics_query
        available_columns = self._get_available_query_metrics_columns(cursor, SQL_SERVER_QUERY_METRICS_COLUMNS)

        engine_edition = self._check.static_info_cache.get(STATIC_INFO_ENGINE_EDITION, "")
        database_name_column = ""
        if self.disable_secondary_tags:
            # If disable_secondary_tags is enabled, we need to use the query without aggregates
            statements_query = STATEMENT_METRICS_QUERY_NO_AGGREGATES
            if is_azure_sql_database(engine_edition):
                # This query does not group by database, so elsewhere a row can span several. Azure SQL Database
                # connects to one, so DB_NAME() names it. Keep it argument-less: resolving a dbid needs
                # sys.dm_exec_plan_attributes, admin-only on the Basic/S0/S1 tiers this setting works around.
                database_name_column = "DB_NAME() as database_name,"
        elif is_azure_sql_database(engine_edition):
            # If the database is Azure SQL Database, we need to use the Azure SQL Database specific query
            statements_query = STATEMENT_METRICS_QUERY_AZURE_SQL_DATABASE
        else:
            # Otherwise, we use the default query
            statements_query = STATEMENT_METRICS_QUERY

        self._statement_metrics_query = statements_query.format(
            query_metrics_columns=', '.join(['qs.{} as {}'.format(col, col) for col in available_columns]),
            query_metrics_column_sums=', '.join(['sum(qs.{}) as {}'.format(c, c) for c in available_columns]),
            limit=self.dm_exec_query_stats_row_limit,
            proc_char_limit=self._config.stored_procedure_characters_limit,
            database_name_column=database_name_column,
        )
        return self._statement_metrics_query

    def lookback_window(self):
        return self._config.statement_metrics_config.get('lookback_window', None)

    @tracked_method(agent_check_getter=agent_check_getter, track_result_length=True)
    def _load_raw_query_metrics_rows(self, cursor):
        self.log.debug("collecting sql server statement metrics")
        statement_metrics_query = self._get_statement_metrics_query_cached(cursor)
        now = time.time()
        query_interval = self.collection_interval * 2
        if self.lookback_window():
            query_interval = self.lookback_window()
        if self._last_stats_query_time:
            query_interval = max(query_interval, now - self._last_stats_query_time)
        self._last_stats_query_time = now
        params = (math.ceil(query_interval),)
        self.log.debug("Running query [%s] %s", statement_metrics_query, params)
        cursor.execute(statement_metrics_query, params)
        columns = [i[0] for i in cursor.description]
        # construct row dicts manually as there's no DictCursor for pyodbc
        rows = [dict(zip(columns, row)) for row in cursor.fetchall()]
        self.log.debug("loaded sql server statement metrics len(rows)=%s", len(rows))
        return rows

    def _should_include_query_metrics_row(self, row):
        if 'database_name' not in row:
            # Unaggregated query metrics row without a database name
            return True

        engine_edition = self._check.static_info_cache.get(STATIC_INFO_ENGINE_EDITION, "")
        if is_azure_sql_database(engine_edition):
            configured_database = self._check.instance.get('database')
            if not configured_database or configured_database == 'master':
                # If no database configured or the configured database is master, include all rows
                return True
            if not row['database_name'] or str(row['database_name']).lower() != configured_database.lower():
                # If the row's database name does not match the configured database, exclude the row
                return False

        return True

    def _normalize_queries(self, rows):
        normalized_rows = []

        for row in rows:
            if not self._should_include_query_metrics_row(row):
                continue
            # Attempt to obfuscate SQL statement with metadata
            try:
                statement = obfuscate_sql_with_metadata(
                    row['statement_text'], self._config.obfuscator_options, replace_null_character=True
                )
                metadata = statement['metadata']
                comments = metadata.get('comments', [])

            except Exception as e:
                if self._config.log_unobfuscated_queries:
                    self.log.warning("Failed to obfuscate query=[%s] | err=[%s]", repr(row['statement_text']), e)
                else:
                    self.log.debug("Failed to obfuscate query | err=[%s]", e)
                self._check.count(
                    "dd.sqlserver.statements.error",
                    1,
                    **self._check.debug_stats_kwargs(tags=["error:obfuscate-query-{}".format(type(e))]),
                )
                # If we can't obfuscate the query, give up.
                continue

            # Extract obfuscated statement and update row fields
            obfuscated_statement = statement['query']
            query_signature = compute_sql_signature(obfuscated_statement)

            procedure_signature = None
            procedure_content = None
            row['is_proc'] = bool(row.get('procedure_name'))
            has_sproc_context = row['is_proc'] or bool(row.get('sproc_object_id'))
            needs_procedure_metadata = has_sproc_context or self.disable_secondary_tags
            should_recover_comments = needs_comment_recovery(row.get('text'), comments)
            if row.get('text') and (needs_procedure_metadata or should_recover_comments):
                try:
                    full_text_statement = obfuscate_sql_with_metadata(
                        row['text'], self._config.obfuscator_options, replace_null_character=True
                    )
                    full_text_comments = full_text_statement['metadata'].get('comments', [])
                    if full_text_comments:
                        comments = list(dict.fromkeys(comments + full_text_comments))
                    if needs_procedure_metadata:
                        procedure_content = full_text_statement['query']
                        procedure_signature = compute_sql_signature(full_text_statement['query'])
                        if not row.get('procedure_name'):
                            procedures = full_text_statement['metadata'].get('procedures')
                            if procedures:
                                row['procedure_name'] = procedures[0].lower()
                                row['is_proc'] = True
                except Exception as e:
                    if needs_procedure_metadata:
                        procedure_signature = '__procedure_obfuscation_error__'
                        procedure_content = '__procedure_obfuscation_error__'
                    if self._config.log_unobfuscated_queries:
                        self.log.warning("Failed to obfuscate query text=[%s] | err=[%s]", repr(row['text']), e)
                    else:
                        self.log.debug(
                            "Failed to obfuscate query text for query_signature=[%s] | err=[%s]", query_signature, e
                        )
                    if needs_procedure_metadata:
                        self._check.count(
                            "dd.sqlserver.statements.error",
                            1,
                            **self._check.debug_stats_kwargs(tags=["error:obfuscate-sproc-{}".format(type(e))]),
                        )
                    # If we can't obfuscate the full text, keep the row using the obfuscated statement text.

            if procedure_content:
                row['procedure_text'] = procedure_content

            if procedure_signature:
                row['procedure_signature'] = procedure_signature

            if row.get('procedure_name') and row.get('schema_name'):
                # convert to lowercase for backward compatibility
                row['procedure_name'] = f"{row['schema_name']}.{row['procedure_name']}".lower()

            row['dd_comments'] = comments
            row['text'] = obfuscated_statement
            row['query_signature'] = query_signature
            row['query_hash'] = _hash_to_hex(row['query_hash'])
            row['query_plan_hash'] = _hash_to_hex(row['query_plan_hash'])
            row['plan_handle'] = _hash_to_hex(row['plan_handle'])

            row['dd_tables'] = metadata.get('tables', None)
            row['dd_commands'] = metadata.get('commands', None)

            normalized_rows.append(row)
        return normalized_rows

    def _collect_metrics_rows(self, cursor):
        rows = self._load_raw_query_metrics_rows(cursor)
        rows = self._normalize_queries(rows)
        if not rows:
            return []
        metric_columns = [c for c in rows[0].keys() if c.startswith("total_") or c == 'execution_count']
        rows = self._state.compute_derivative_rows(rows, metric_columns, key=_row_key)
        return rows

    @staticmethod
    def _to_metrics_payload_row(row):
        row = dict(row.items())
        # remove the statement_text field, so we do not forward deobfuscated text
        # to the backend
        if 'statement_text' in row:
            del row['statement_text']
        # we're already able to link to the procedure via procedure_name and procedure_signature so we don't need
        # the text in metrics payloads
        if 'procedure_text' in row:
            del row['procedure_text']
        return row

    def _to_metrics_payload(self, rows, max_queries):
        # sort by total_elapsed_time and return the top max_queries
        rows = sorted(rows, key=lambda i: i['total_elapsed_time'], reverse=True)
        rows = rows[:max_queries]
        return {
            'host': self._check.reported_hostname,
            "database_instance": self._check.database_identifier,
            'timestamp': time.time() * 1000,
            'min_collection_interval': self.collection_interval,
            'tags': self._check.tag_manager.get_tags(),
            'kind': 'query_metrics',
            'cloud_metadata': self._check.cloud_metadata,
            'sqlserver_rows': [self._to_metrics_payload_row(r) for r in rows],
            'sqlserver_version': self._check.static_info_cache.get(STATIC_INFO_VERSION, ""),
            'sqlserver_engine_edition': self._check.static_info_cache.get(STATIC_INFO_ENGINE_EDITION, ""),
            'ddagentversion': self._check.agent_version,
            'service': self._config.service,
        }

    @tracked_method(agent_check_getter=agent_check_getter)
    def collect_statement_metrics_and_plans(self):
        """
        Collects statement metrics and plans.
        :return:
        """
        raise_if_cancelled(self._cancel_event)

        plans_submitted = 0
        deadline = time.time() + self.collection_interval

        # re-use the check's conn module, but set extra_key=dbm- to ensure we get our own
        # raw connection. adodbapi and pyodbc modules are thread safe, but connections are not.
        with self._check.connection.open_managed_default_connection(self._conn_key_prefix):
            with self._check.connection.get_managed_cursor(self._conn_key_prefix) as cursor:
                rows = self._collect_metrics_rows(cursor)
                if not rows:
                    return
                for event in self._rows_to_fqt_events(rows):
                    self._check.database_monitoring_query_sample(json.dumps(event, default=default_json_event_encoding))
                payload = self._to_metrics_payload(rows, self._max_query_metrics)
                self._check.database_monitoring_query_metrics(json.dumps(payload, default=default_json_event_encoding))
                if self._collect_execution_plans:
                    for event in self._collect_plans(rows, cursor, deadline):
                        self._check.database_monitoring_query_sample(
                            json.dumps(event, default=default_json_event_encoding)
                        )
                        plans_submitted += 1

        self._check.count(
            "dd.sqlserver.statements.plans_submitted.count", plans_submitted, **self._check.debug_stats_kwargs()
        )
        self._check.gauge(
            "dd.sqlserver.statements.seen_plans_cache.len",
            len(self._seen_plans_ratelimiter),
            **self._check.debug_stats_kwargs(),
        )
        self._check.gauge(
            "dd.sqlserver.statements.fqt_cache.len",
            len(self._full_statement_text_cache),
            **self._check.debug_stats_kwargs(),
        )

    def _rows_to_fqt_events(self, rows):
        for row in rows:
            query_cache_key = _row_key(row)
            if query_cache_key in self._full_statement_text_cache:
                continue
            self._full_statement_text_cache[query_cache_key] = True
            tags = self._check.tag_manager.get_tags()
            if 'database_name' in row:
                tags += ["db:{}".format(row['database_name'])]
            yield {
                "timestamp": time.time() * 1000,
                "host": self._check.reported_hostname,
                "database_instance": self._check.database_identifier,
                "ddagentversion": self._check.agent_version,
                "ddsource": "sqlserver",
                "ddtags": ",".join(tags),
                "dbm_type": "fqt",
                'service': self._config.service,
                "db": {
                    "instance": row.get('database_name', None),
                    "query_signature": row['query_signature'],
                    "procedure_signature": row.get('procedure_signature', None),
                    "statement": row['text'],
                    "metadata": {
                        "tables": row['dd_tables'],
                        "commands": row['dd_commands'],
                        "comments": row.get('dd_comments', None),
                    },
                },
                'sqlserver': {
                    'query_hash': row['query_hash'],
                    'query_plan_hash': row['query_plan_hash'],
                },
            }

    def run_job(self):
        self.collect_statement_metrics_and_plans()

    @tracked_method(agent_check_getter=agent_check_getter)
    def _load_plan(self, plan_handle, cursor):
        self.log.debug("collecting plan. plan_handle=%s", plan_handle)
        self.log.debug("Running query [%s] %s", PLAN_LOOKUP_QUERY, (plan_handle,))
        cursor.execute(PLAN_LOOKUP_QUERY, ("0x" + plan_handle,))
        result = cursor.fetchone()
        if not result:
            self.log.debug("failed to loan plan, it must have just been expired out of the plan cache")
            return None, None
        raw_plan, is_plan_encrypted = result
        if not raw_plan:
            self.log.debug("plan was null in the plan cache")
        return raw_plan, is_plan_encrypted

    @tracked_method(agent_check_getter=agent_check_getter)
    def _collect_plans(self, rows, cursor, deadline):
        attempted_plan_keys = set()
        collect_real_plans = self._collect_real_plans and self._real_plans_supported()
        for row in rows:
            if self.enforce_collection_interval_deadline and time.time() > deadline:
                self.log.debug("ending plan collection early because check deadline has been exceeded")
                self._check.count("dd.sqlserver.statements.deadline_exceeded", 1, **self._check.debug_stats_kwargs())
                return
            plan_key = (row['query_signature'], row['query_hash'], row['query_plan_hash'])
            # for stored procedures, we only want to look up plans for the entire procedure
            # not every query that is executed within the proc. In order to accomplish this,
            # we use the plan handle
            if row['is_proc'] or row['is_encrypted']:
                plan_key = row['plan_handle']
            # Skip duplicates in this pass without suppressing failed keys in later passes.
            if (
                plan_key in attempted_plan_keys
                or plan_key in self._seen_plans_ratelimiter
                or len(self._seen_plans_ratelimiter) >= self._seen_plans_ratelimiter.maxsize
            ):
                continue
            attempted_plan_keys.add(plan_key)
            raise_if_cancelled(self._cancel_event)
            try:
                raw_plan, is_plan_encrypted = self._load_plan(row['plan_handle'], cursor)
            except Exception as e:
                # A connection closed during cancellation may surface as a database error.
                raise_if_cancelled(self._cancel_event)
                self.log.debug("Failed to load plan. plan_handle=%s error=%s", row['plan_handle'], e)
                error_tags = ["error:load-plan-{}".format(type(e))]
                self._check.count("dd.sqlserver.statements.error", 1, **self._check.debug_stats_kwargs(tags=error_tags))
                continue
            if self._seen_plans_ratelimiter.acquire(plan_key):
                obfuscated_plan = None
                collection_errors = []

                try:
                    if raw_plan:
                        obfuscated_plan = obfuscate_xml_plan(raw_plan, self._config.obfuscator_options)
                except Exception as e:
                    context = (
                        "query_signature=[{0}] query_hash=[{1}] query_plan_hash=[{2}] plan_handle=[{3}] err=[{4}]"
                    ).format(row['query_signature'], row['query_hash'], row['query_plan_hash'], row['plan_handle'], e)
                    if self._config.log_unobfuscated_plans:
                        self.log.warning("Failed to obfuscate plan=[%s] | %s", repr(raw_plan), context)
                    else:
                        self.log.debug("Failed to obfuscate plan | %s", context)
                    collection_errors.append({'code': "obfuscate_xml_plan_error", 'message': str(e)})
                    self._check.count(
                        "dd.sqlserver.statements.error",
                        1,
                        **self._check.debug_stats_kwargs(tags=["error:obfuscate-xml-plan-{}".format(type(e))]),
                    )
                tags = self._check.tag_manager.get_tags()

                if is_plan_encrypted:
                    collection_errors.append({'code': "plan_encrypted", 'message': "cannot collect encrypted plan"})

                # Do not submit plan events if no plan is available and there is no collection error.
                # This avoids sending empty plan events when a plan is not available in the cache.
                if not raw_plan and not collection_errors:
                    continue

                # for stored procedures, we want to send the plan
                # events with the full procedure text, not the text
                # for the individual statement encapsulated within the proc
                text_key = 'text'
                if row['is_proc']:
                    text_key = 'procedure_text'
                query_signature = row['query_signature']
                # for procedure plans, it only makes sense to send the
                # procedure_signature
                if row['is_proc']:
                    query_signature = None
                if 'database_name' in row:
                    tags += ["db:{}".format(row['database_name'])]
                obfuscated_plan_event = {
                    "host": self._check.reported_hostname,
                    "database_instance": self._check.database_identifier,
                    "ddagentversion": self._check.agent_version,
                    "ddsource": "sqlserver",
                    "ddtags": ",".join(tags),
                    "timestamp": time.time() * 1000,
                    "dbm_type": "plan",
                    "cloud_metadata": self._check.cloud_metadata,
                    'sqlserver_version': self._check.static_info_cache.get(STATIC_INFO_VERSION, ""),
                    'sqlserver_engine_edition': self._check.static_info_cache.get(STATIC_INFO_ENGINE_EDITION, ""),
                    'service': self._config.service,
                    "db": {
                        "instance": row.get("database_name", None),
                        "plan": {
                            "definition": obfuscated_plan,
                            "signature": row['query_plan_hash'],
                            "collection_errors": collection_errors if collection_errors else None,
                        },
                        "query_signature": query_signature,
                        "procedure_signature": row.get('procedure_signature', None),
                        "procedure_name": row.get('procedure_name', None),
                        "statement": row.get(text_key),
                        "metadata": {
                            "tables": row['dd_tables'],
                            "commands": row['dd_commands'],
                            "comments": row['dd_comments'],
                        },
                    },
                    'sqlserver': {
                        "is_plan_encrypted": is_plan_encrypted,
                        "is_statement_encrypted": row['is_encrypted'],
                        'query_hash': row['query_hash'],
                        'query_plan_hash': row['query_plan_hash'],
                        'plan_handle': row['plan_handle'],
                        'execution_count': row.get('execution_count', None),
                        'total_elapsed_time': row.get('total_elapsed_time', None),
                    },
                }
                if self._collect_raw_query_statement:
                    raw_plan_event = copy.deepcopy(obfuscated_plan_event)
                    raw_plan_event["dbm_type"] = "rqp"  # raw query plan
                    raw_plan_event["db"]["plan"]["definition"] = raw_plan
                    if raw_plan:
                        # add the raw signature to the event so we can use it to look up the raw plan.
                        # query_plan_hash only identifies the plan shape, so hash the raw plan content instead.
                        raw_plan_signature = compute_sql_signature(raw_plan)
                        raw_plan_event["db"]["plan"]["raw_signature"] = raw_plan_signature
                        obfuscated_plan_event["db"]["plan"]["raw_signature"] = raw_plan_signature
                    yield raw_plan_event
                yield obfuscated_plan_event
                if collect_real_plans and raw_plan and not is_plan_encrypted:
                    yield from self._collect_real_plan_events(row, plan_key, obfuscated_plan_event, cursor, deadline)

    def _real_plans_supported(self) -> bool:
        major_version = self._check.static_info_cache.get(STATIC_INFO_MAJOR_VERSION)
        engine_edition = self._check.static_info_cache.get(STATIC_INFO_ENGINE_EDITION)
        if supports_last_query_plan_stats(major_version, engine_edition):
            return True
        # Until the version is known, skip real plans without warning.
        if major_version is not None and not self._real_plans_version_unsupported_warned:
            self._real_plans_version_unsupported_warned = True
            self.log.warning(
                "Real execution plans need SQL Server 2019 or later, or Azure SQL, but this server's major version is "
                "%s: only estimated plans are collected. Turn off `query_metrics.collect_real_plans` to remove this "
                "warning: %s",
                major_version,
                SQLSERVER_DBM_SETUP_DOCS_URL,
            )
            self._check.health.submit_health_event(
                name=SqlServerHealthEvent.REAL_PLANS_VERSION_UNSUPPORTED, status=HealthStatus.WARNING
            )
        return False

    def _last_query_plan_stats_enabled(self, cursor, db_name: str | None) -> bool:
        """
        Whether the database keeps the last actual plan of its queries. The settings are read at most every
        `LAST_QUERY_PLAN_STATS_REFRESH_INTERVAL` seconds. When a database's setting can't be read, or the row has no
        database, its real plans are looked for anyway, and only kept if they hold runtime data.
        """
        now = time.time()
        if now - self._last_query_plan_stats_read_at >= LAST_QUERY_PLAN_STATS_REFRESH_INTERVAL:
            self._last_query_plan_stats_read_at = now
            try:
                self._trace_flag_2451 = read_trace_flag_2451(cursor)
            except Exception as e:
                raise_if_cancelled(self._cancel_event)
                self.log.debug("Failed to read the status of trace flag 2451: %s", e)
                self._trace_flag_2451 = False
            self._last_query_plan_stats_by_db = {}
            # Read the failing databases again, so the health event goes back to OK once they're fixed, even when
            # none of their plans gets collected.
            for failing_db in sorted(self._last_query_plan_stats_disabled_dbs):
                self._read_last_query_plan_stats(cursor, failing_db)
        if self._trace_flag_2451 or not db_name:
            return True
        if db_name not in self._last_query_plan_stats_by_db:
            self._read_last_query_plan_stats(cursor, db_name)
        return self._last_query_plan_stats_by_db[db_name] is not False

    def _read_last_query_plan_stats(self, cursor, db_name: str) -> None:
        enabled: bool | None = True
        if not self._trace_flag_2451:
            try:
                enabled = read_last_query_plan_stats(cursor, db_name)
            except Exception as e:
                raise_if_cancelled(self._cancel_event)
                self.log.debug("Failed to read LAST_QUERY_PLAN_STATS in database '%s': %s", db_name, e)
                enabled = None
        self._last_query_plan_stats_by_db[db_name] = enabled
        # The system databases run the Agent's own queries, so a warning there is noise. Their real plans are still
        # collected when the setting is on.
        if enabled is False and db_name.lower() not in SYSTEM_DATABASES:
            if db_name not in self._last_query_plan_stats_disabled_dbs:
                if not self._last_query_plan_stats_disabled_dbs:
                    self._check.health.submit_health_event(
                        name=SqlServerHealthEvent.LAST_QUERY_PLAN_STATS_DISABLED, status=HealthStatus.WARNING
                    )
                self._last_query_plan_stats_disabled_dbs.add(db_name)
                self.log.warning(
                    "LAST_QUERY_PLAN_STATS is off in database '%s', so its real execution plans aren't collected. "
                    "Turn it on in that database with `ALTER DATABASE SCOPED CONFIGURATION SET LAST_QUERY_PLAN_STATS "
                    "= ON;`: %s",
                    db_name,
                    SQLSERVER_DBM_SETUP_DOCS_URL,
                )
        elif db_name in self._last_query_plan_stats_disabled_dbs:
            self._last_query_plan_stats_disabled_dbs.remove(db_name)
            if not self._last_query_plan_stats_disabled_dbs:
                self._check.health.submit_health_event(
                    name=SqlServerHealthEvent.LAST_QUERY_PLAN_STATS_DISABLED, status=HealthStatus.OK
                )

    @tracked_method(agent_check_getter=agent_check_getter)
    def _load_real_plan(self, row: dict, cursor) -> dict | None:
        """The real plan of the row's cached plan, with the last execution's statistics of the row's statement."""
        params = (
            "0x" + row['plan_handle'],
            "0x" + row['plan_handle'],
            row['statement_start_offset'],
            row['statement_end_offset'],
        )
        self.log.debug("Running query [%s] %s", REAL_PLAN_LOOKUP_QUERY, params)
        cursor.execute(REAL_PLAN_LOOKUP_QUERY, params)
        columns = [column[0] for column in cursor.description]
        result = cursor.fetchone()
        return dict(zip(columns, result)) if result else None

    def _count_real_plan(self, status: str) -> None:
        self._check.count(
            "dd.sqlserver.statements.real_plans", 1, **self._check.debug_stats_kwargs(tags=["status:" + status])
        )

    def _collect_real_plan_events(
        self, row: dict, plan_key: Any, plan_event: dict, cursor, deadline: float
    ) -> Iterator[dict]:
        """
        Yields the real plan event of a row, the last actual plan of its cached plan, built from its estimated plan
        event, and its raw copy when raw collection is on.
        """
        if plan_key in self._seen_real_plans_ratelimiter:
            return
        if self.enforce_collection_interval_deadline and time.time() > deadline:
            return
        if not self._last_query_plan_stats_enabled(cursor, row.get('database_name')):
            self._count_real_plan("db_disabled")
            return
        raise_if_cancelled(self._cancel_event)
        try:
            real_plan = self._load_real_plan(row, cursor) or {}
        except Exception as e:
            # A connection closed during cancellation may surface as a database error.
            raise_if_cancelled(self._cancel_event)
            self.log.debug("Failed to load real plan. plan_handle=%s error=%s", row['plan_handle'], e)
            self._count_real_plan("error")
            return
        raw_plan = real_plan.get('query_plan')
        if not raw_plan:
            self._count_real_plan("empty")
            return
        if not any(element in raw_plan for element in REAL_PLAN_RUNTIME_ELEMENTS):
            self._count_real_plan("no_runtime_data")
            return
        if len(raw_plan.encode('utf-8')) > self._real_plan_max_size_bytes:
            self._count_real_plan("too_large")
            return
        try:
            obfuscated_plan = obfuscate_xml_plan(raw_plan, self._config.obfuscator_options)
        except Exception as e:
            if self._config.log_unobfuscated_plans:
                self.log.warning("Failed to obfuscate real plan=[%s] | err=[%s]", repr(raw_plan), e)
            else:
                self.log.debug("Failed to obfuscate real plan | plan_handle=[%s] err=[%s]", row['plan_handle'], e)
            self._count_real_plan("error")
            return
        if not self._seen_real_plans_ratelimiter.acquire(plan_key):
            return

        real_plan_event = copy.deepcopy(plan_event)
        real_plan_event["timestamp"] = time.time() * 1000
        real_plan_event["db"]["plan"] = {
            "definition": obfuscated_plan,
            "signature": row['query_plan_hash'],
            "type": "real",
            "source": "last_query_plan_stats",
            "collection_errors": None,
        }
        # The plan describes the last execution of the cached plan, not one of the executions the metrics count.
        real_plan_event["sqlserver"]["last_execution_time"] = real_plan.get('last_execution_time')
        # A procedure's plan covers all its statements, so one statement's statistics would misdescribe it.
        if not row['is_proc']:
            for column in REAL_PLAN_STATEMENT_STATS_COLUMNS:
                real_plan_event["sqlserver"][column] = real_plan.get(column)
        if self._collect_raw_query_statement:
            raw_plan_event = copy.deepcopy(real_plan_event)
            raw_plan_event["dbm_type"] = "rqp"  # raw query plan
            raw_plan_event["db"]["plan"]["definition"] = raw_plan
            raw_plan_signature = compute_sql_signature(raw_plan)
            raw_plan_event["db"]["plan"]["raw_signature"] = raw_plan_signature
            real_plan_event["db"]["plan"]["raw_signature"] = raw_plan_signature
            yield raw_plan_event
        self._count_real_plan("collected")
        yield real_plan_event
