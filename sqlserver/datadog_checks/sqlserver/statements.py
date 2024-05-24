# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import binascii
import math
import time

from cachetools import TTLCache
from lxml import etree as ET

from datadog_checks.base import is_affirmative
from datadog_checks.base.utils.common import ensure_unicode, to_native_string
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
from datadog_checks.sqlserver.utils import extract_sql_comments_and_procedure_name

try:
    import datadog_agent
except ImportError:
    from ..stubs import datadog_agent

from datadog_checks.sqlserver.const import STATIC_INFO_ENGINE_EDITION, STATIC_INFO_VERSION

DEFAULT_COLLECTION_INTERVAL = 60

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
    s.* from qstats_aggr_split s
    cross apply sys.dm_exec_sql_text(s.plan_handle) qt
"""

PLAN_LOOKUP_QUERY = """\
select cast(query_plan as nvarchar(max)) as query_plan, encrypted as is_encrypted
from sys.dm_exec_query_plan(CONVERT(varbinary(max), ?, 1))
"""


def _row_key(row):
    """
    :param row: a normalized row from STATEMENT_METRICS_QUERY
    :return: a tuple uniquely identifying this row
    """
    return (
        row.get('database_name'),
        row['query_signature'],
        row['query_hash'],
        row['query_plan_hash'],
    )


XML_PLAN_OBFUSCATION_ATTRS = frozenset(
    {
        "StatementText",
        "ConstValue",
        "ScalarString",
        "ParameterCompiledValue",
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
    tree = ET.fromstring(raw_plan)
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
        self.tags = [t for t in check.tags if not t.startswith('dd.internal')]
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
            dbms="sqlserver",
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

        statements_query = (
            STATEMENT_METRICS_QUERY_NO_AGGREGATES if self.disable_secondary_tags else STATEMENT_METRICS_QUERY
        )
        self._statement_metrics_query = statements_query.format(
            query_metrics_columns=', '.join(['qs.{} as {}'.format(col, col) for col in available_columns]),
            query_metrics_column_sums=', '.join(['sum(qs.{}) as {}'.format(c, c) for c in available_columns]),
            limit=self.dm_exec_query_stats_row_limit,
            proc_char_limit=self._config.stored_procedure_characters_limit,
        )
        return self._statement_metrics_query

    @tracked_method(agent_check_getter=agent_check_getter, track_result_length=True)
    def _load_raw_query_metrics_rows(self, cursor):
        self.log.debug("collecting sql server statement metrics")
        statement_metrics_query = self._get_statement_metrics_query_cached(cursor)
        now = time.time()
        query_interval = self.collection_interval * 2
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

    def _normalize_queries(self, rows):
        normalized_rows = []

        for row in rows:
            # Attempt to obfuscate SQL statement with metadata
            procedure_statement = None
            try:
                statement = obfuscate_sql_with_metadata(
                    row['statement_text'], self._config.obfuscator_options, replace_null_character=True
                )
                comments, row['is_proc'], procedure_name = extract_sql_comments_and_procedure_name(row['text'])

            except Exception as e:
                if self._config.log_unobfuscated_queries:
                    self.log.warning("Failed to obfuscate query=[%s] | err=[%s]", repr(row['statement_text']), e)
                else:
                    self.log.debug("Failed to obfuscate query | err=[%s]", e)
                self._check.count(
                    "dd.sqlserver.statements.error",
                    1,
                    **self._check.debug_stats_kwargs(tags=["error:obfuscate-query-{}".format(type(e))])
                )
                # If we can't obfuscate the query, give up.
                continue

            # Extract obfuscated statement and update row fields
            obfuscated_statement = statement['query']
            query_signature = compute_sql_signature(obfuscated_statement)

            procedure_signature = None
            procedure_content = None
            if row['is_proc']:
                try:
                    procedure_statement = obfuscate_sql_with_metadata(
                        row['text'], self._config.obfuscator_options, replace_null_character=True
                    )
                    procedure_content = procedure_statement['query']
                    procedure_signature = compute_sql_signature(procedure_statement['query'])
                except Exception as e:
                    procedure_signature = '__procedure_obfuscation_error__'
                    procedure_content = '__procedure_obfuscation_error__'
                    if self._config.log_unobfuscated_queries:
                        self.log.warning("Failed to obfuscate stored procedure=[%s] | err=[%s]", repr(row['text']), e)
                    else:
                        self.log.debug(
                            "Failed to obfuscate stored procedure for query_signature=[%s] | err=[%s]",
                            query_signature,
                            e,
                        )
                    self._check.count(
                        "dd.sqlserver.statements.error",
                        1,
                        **self._check.debug_stats_kwargs(tags=["error:obfuscate-sproc-{}".format(type(e))])
                    )
                    # If we can't obfuscate the stored procedure, we don't need to give up for this row,
                    # we just won't have the association with the stored procedure in the metrics payload

            if procedure_content:
                row['procedure_text'] = procedure_content

            if procedure_signature:
                row['procedure_signature'] = procedure_signature

            if procedure_name:
                row['procedure_name'] = procedure_name

            row['dd_comments'] = comments
            row['text'] = obfuscated_statement
            row['query_signature'] = query_signature
            row['query_hash'] = _hash_to_hex(row['query_hash'])
            row['query_plan_hash'] = _hash_to_hex(row['query_plan_hash'])
            row['plan_handle'] = _hash_to_hex(row['plan_handle'])

            metadata = statement['metadata']
            row['dd_tables'] = metadata.get('tables', None)
            row['dd_commands'] = metadata.get('commands', None)

            if not comments:
                row['dd_comments'] = metadata.get('comments', None)

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
            'host': self._check.resolved_hostname,
            'timestamp': time.time() * 1000,
            'min_collection_interval': self.collection_interval,
            'tags': self.tags,
            'kind': 'query_metrics',
            'cloud_metadata': self._config.cloud_metadata,
            'sqlserver_rows': [self._to_metrics_payload_row(r) for r in rows],
            'sqlserver_version': self._check.static_info_cache.get(STATIC_INFO_VERSION, ""),
            'sqlserver_engine_edition': self._check.static_info_cache.get(STATIC_INFO_ENGINE_EDITION, ""),
            'ddagentversion': datadog_agent.get_version(),
            'ddagenthostname': self._check.agent_hostname,
        }

    @tracked_method(agent_check_getter=agent_check_getter)
    def collect_statement_metrics_and_plans(self):
        """
        Collects statement metrics and plans.
        :return:
        """
        plans_submitted = 0
        deadline = time.time() + self.collection_interval

        # re-use the check's conn module, but set extra_key=dbm- to ensure we get our own
        # raw connection. adodbapi and pyodbc modules are thread safe, but connections are not.
        with self._check.connection.open_managed_default_connection(key_prefix=self._conn_key_prefix):
            with self._check.connection.get_managed_cursor(key_prefix=self._conn_key_prefix) as cursor:
                rows = self._collect_metrics_rows(cursor)
                if not rows:
                    return
                for event in self._rows_to_fqt_events(rows):
                    self._check.database_monitoring_query_sample(json.dumps(event, default=default_json_event_encoding))
                payload = self._to_metrics_payload(rows, self._max_query_metrics)
                self._check.database_monitoring_query_metrics(json.dumps(payload, default=default_json_event_encoding))
                for event in self._collect_plans(rows, cursor, deadline):
                    self._check.database_monitoring_query_sample(json.dumps(event, default=default_json_event_encoding))
                    plans_submitted += 1

        self._check.count(
            "dd.sqlserver.statements.plans_submitted.count", plans_submitted, **self._check.debug_stats_kwargs()
        )
        self._check.gauge(
            "dd.sqlserver.statements.seen_plans_cache.len",
            len(self._seen_plans_ratelimiter),
            **self._check.debug_stats_kwargs()
        )
        self._check.gauge(
            "dd.sqlserver.statements.fqt_cache.len",
            len(self._full_statement_text_cache),
            **self._check.debug_stats_kwargs()
        )

    def _rows_to_fqt_events(self, rows):
        for row in rows:
            query_cache_key = _row_key(row)
            if query_cache_key in self._full_statement_text_cache:
                continue
            self._full_statement_text_cache[query_cache_key] = True
            tags = list(self.tags)
            if 'database_name' in row:
                tags += ["db:{}".format(row['database_name'])]
            yield {
                "timestamp": time.time() * 1000,
                "host": self._check.resolved_hostname,
                "ddagentversion": datadog_agent.get_version(),
                "ddsource": "sqlserver",
                "ddtags": ",".join(tags),
                "dbm_type": "fqt",
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
            if self._seen_plans_ratelimiter.acquire(plan_key):
                raw_plan, is_plan_encrypted = self._load_plan(row['plan_handle'], cursor)
                obfuscated_plan, collection_errors = None, None

                try:
                    if raw_plan:
                        obfuscated_plan = obfuscate_xml_plan(raw_plan, self._config.obfuscator_options)
                except Exception as e:
                    context = (
                        "query_signature=[{0}] query_hash=[{1}] query_plan_hash=[{2}] plan_handle=[{3}] err=[{4}]"
                    ).format(row['query_signature'], row['query_hash'], row['query_plan_hash'], row['plan_handle'], e)
                    if self._config.log_unobfuscated_plans:
                        self.log.warning("Failed to obfuscate plan=[%s] | %s", raw_plan, context)
                    else:
                        self.log.debug("Failed to obfuscate plan | %s", context)
                    collection_errors = [{'code': "obfuscate_xml_plan_error", 'message': str(e)}]
                    self._check.count(
                        "dd.sqlserver.statements.error",
                        1,
                        **self._check.debug_stats_kwargs(tags=["error:obfuscate-xml-plan-{}".format(type(e))])
                    )
                tags = list(self.tags)

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
                yield {
                    "host": self._check.resolved_hostname,
                    "ddagentversion": datadog_agent.get_version(),
                    "ddsource": "sqlserver",
                    "ddtags": ",".join(tags),
                    "timestamp": time.time() * 1000,
                    "dbm_type": "plan",
                    "cloud_metadata": self._config.cloud_metadata,
                    'sqlserver_version': self._check.static_info_cache.get(STATIC_INFO_VERSION, ""),
                    'sqlserver_engine_edition': self._check.static_info_cache.get(STATIC_INFO_ENGINE_EDITION, ""),
                    "db": {
                        "instance": row.get("database_name", None),
                        "plan": {
                            "definition": obfuscated_plan,
                            "signature": row['query_plan_hash'],
                            "collection_errors": collection_errors,
                        },
                        "query_signature": query_signature,
                        "procedure_signature": row.get('procedure_signature', None),
                        "procedure_name": row.get('procedure_name', None),
                        "statement": row[text_key],
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
