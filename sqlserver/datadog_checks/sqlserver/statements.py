import binascii
import math
import time

from cachetools import TTLCache
from lxml import etree as ET

from datadog_checks.base import is_affirmative
from datadog_checks.base.utils.common import ensure_unicode, to_native_string
from datadog_checks.base.utils.db.sql import compute_sql_signature
from datadog_checks.base.utils.db.statement_metrics import StatementMetrics
from datadog_checks.base.utils.db.utils import DBMAsyncJob, RateLimitingTTLCache, default_json_event_encoding
from datadog_checks.base.utils.serialization import json
from datadog_checks.base.utils.tracking import tracked_method

try:
    import datadog_agent
except ImportError:
    from ..stubs import datadog_agent

DEFAULT_COLLECTION_INTERVAL = 10

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
    select TOP {limit} text, query_hash, query_plan_hash,
           (select value from sys.dm_exec_plan_attributes(plan_handle) where attribute = 'dbid') as dbid,
           (select value from sys.dm_exec_plan_attributes(plan_handle) where attribute = 'user_id') as user_id,
           {query_metrics_columns}
    from sys.dm_exec_query_stats
        cross apply sys.dm_exec_sql_text(sql_handle)
    where last_execution_time > dateadd(second, -?, getdate())
)
select text, query_hash, query_plan_hash, CAST(S.dbid as int) as dbid, D.name as database_name, U.name as user_name,
    {query_metrics_column_sums}
    from qstats S
    left join sys.databases D on S.dbid = D.database_id
    left join sys.sysusers U on S.user_id = U.uid
    group by text, query_hash, query_plan_hash, S.dbid, D.name, U.name
"""

PLAN_LOOKUP_QUERY = """\
select cast(query_plan as nvarchar(max)) as query_plan from sys.dm_exec_query_stats
    cross apply sys.dm_exec_query_plan(plan_handle)
where
    query_hash = CONVERT(varbinary(max), ?, 1) and query_plan_hash = CONVERT(varbinary(max), ?, 1)
"""


def _row_key(row):
    """
    :param row: a normalized row from STATEMENT_METRICS_QUERY
    :return: a tuple uniquely identifying this row
    """
    return row['database_name'], row['user_name'], row['query_signature'], row['query_hash'], row['query_plan_hash']


XML_PLAN_OBFUSCATION_ATTRS = {
    "StatementText",
    "ConstValue",
    "ScalarString",
    "ParameterCompiledValue",
}


def agent_check_getter(self):
    return self.check


def _hash_to_hex(hash):
    return to_native_string(binascii.hexlify(hash))


def obfuscate_xml_plan(raw_plan):
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
                e.attrib[k] = ensure_unicode(datadog_agent.obfuscate_sql(val))
    return to_native_string(ET.tostring(tree, encoding="UTF-8"))


class SqlserverStatementMetrics(DBMAsyncJob):
    """Collects query metrics and plans"""

    def __init__(self, check):
        self.check = check
        self.log = check.log
        collection_interval = float(
            check.statement_metrics_config.get('collection_interval', DEFAULT_COLLECTION_INTERVAL)
        )
        if collection_interval <= 0:
            collection_interval = DEFAULT_COLLECTION_INTERVAL
        self.collection_interval = collection_interval
        super(SqlserverStatementMetrics, self).__init__(
            check,
            run_sync=is_affirmative(check.statement_metrics_config.get('run_sync', False)),
            enabled=is_affirmative(check.statement_metrics_config.get('enabled', True)),
            expected_db_exceptions=(),
            min_collection_interval=check.min_collection_interval,
            config_host=check.resolved_hostname,
            dbms="sqlserver",
            rate_limit=1 / float(collection_interval),
            job_name="query-metrics",
            shutdown_callback=self._close_db_conn,
        )
        self.dm_exec_query_stats_row_limit = int(
            check.statement_metrics_config.get('dm_exec_query_stats_row_limit', 10000)
        )
        self.enforce_collection_interval_deadline = bool(
            check.statement_metrics_config.get('enforce_collection_interval_deadline', True)
        )
        self._state = StatementMetrics()
        self._init_caches()
        self._conn_key_prefix = "dbm-"
        self._statement_metrics_query = None
        self._last_stats_query_time = None

    def _init_caches(self):
        # full_statement_text_cache: limit the ingestion rate of full statement text events per query_signature
        self._full_statement_text_cache = TTLCache(
            maxsize=self.check.instance.get('full_statement_text_cache_max_size', 10000),
            ttl=60 * 60 / self.check.instance.get('full_statement_text_samples_per_hour_per_query', 1),
        )

        # seen_plans_ratelimiter: limit the ingestion rate per unique plan.
        # plans, we only really need them once per hour
        self._seen_plans_ratelimiter = RateLimitingTTLCache(
            # assuming ~100 bytes per entry (query & plan signature, key hash, 4 pointers (ordered dict), expiry time)
            # total size: 10k * 100 = 1 Mb
            maxsize=int(self.check.instance.get('seen_samples_cache_maxsize', 10000)),
            ttl=60 * 60 / int(self.check.instance.get('samples_per_hour_per_query', 4)),
        )

    def _close_db_conn(self):
        pass

    def _get_available_query_metrics_columns(self, cursor, all_expected_columns):
        cursor.execute("select top 0 * from sys.dm_exec_query_stats")
        all_columns = set([i[0] for i in cursor.description])
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
        self._statement_metrics_query = STATEMENT_METRICS_QUERY.format(
            query_metrics_columns=', '.join(available_columns),
            query_metrics_column_sums=', '.join(['sum({}) as {}'.format(c, c) for c in available_columns]),
            collection_interval=int(math.ceil(self.collection_interval) * 2),
            limit=self.dm_exec_query_stats_row_limit,
        )
        return self._statement_metrics_query

    @tracked_method(agent_check_getter=agent_check_getter, track_result_length=True)
    def _load_raw_query_metrics_rows(self, cursor):
        self.log.debug("collecting sql server statement metrics")
        statement_metrics_query = self._get_statement_metrics_query_cached(cursor)
        now = time.time()
        query_interval = self.collection_interval
        if self._last_stats_query_time:
            query_interval = now - self._last_stats_query_time
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
            try:
                obfuscated_statement = datadog_agent.obfuscate_sql(row['text'])
            except Exception as e:
                # obfuscation errors are relatively common so only log them during debugging
                self.log.debug("Failed to obfuscate query: %s", e)
                self.check.count(
                    "dd.sqlserver.statements.error",
                    1,
                    **self.check.debug_stats_kwargs(tags=["error:obfuscate-query-{}".format(type(e))])
                )
                continue
            row['text'] = obfuscated_statement
            row['query_signature'] = compute_sql_signature(obfuscated_statement)
            row['query_hash'] = _hash_to_hex(row['query_hash'])
            row['query_plan_hash'] = _hash_to_hex(row['query_plan_hash'])
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
        row = {k: v for k, v in row.items()}
        # truncate query text to the maximum length supported by metrics tags
        row['text'] = row['text'][0:200]
        return row

    def _to_metrics_payload(self, rows):
        return {
            'host': self.check.resolved_hostname,
            'timestamp': time.time() * 1000,
            'min_collection_interval': self.collection_interval,
            'tags': self.check.tags,
            'sqlserver_rows': [self._to_metrics_payload_row(r) for r in rows],
            'sqlserver_version': self.check.static_info_cache.get("version", ""),
            'ddagentversion': datadog_agent.get_version(),
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
        with self.check.connection.open_managed_default_connection(key_prefix=self._conn_key_prefix):
            with self.check.connection.get_managed_cursor(key_prefix=self._conn_key_prefix) as cursor:
                rows = self._collect_metrics_rows(cursor)
                if not rows:
                    return
                for event in self._rows_to_fqt_events(rows):
                    self.check.database_monitoring_query_sample(json.dumps(event, default=default_json_event_encoding))
                payload = self._to_metrics_payload(rows)
                self.check.database_monitoring_query_metrics(json.dumps(payload, default=default_json_event_encoding))
                for event in self._collect_plans(rows, cursor, deadline):
                    self.check.database_monitoring_query_sample(json.dumps(event, default=default_json_event_encoding))
                    plans_submitted += 1

        self.check.count(
            "dd.sqlserver.statements.plans_submitted.count", plans_submitted, **self.check.debug_stats_kwargs()
        )
        self.check.gauge(
            "dd.sqlserver.statements.seen_plans_cache.len",
            len(self._seen_plans_ratelimiter),
            **self.check.debug_stats_kwargs()
        )
        self.check.gauge(
            "dd.sqlserver.statements.fqt_cache.len",
            len(self._full_statement_text_cache),
            **self.check.debug_stats_kwargs()
        )

    def _rows_to_fqt_events(self, rows):
        for row in rows:
            query_cache_key = _row_key(row)
            if query_cache_key in self._full_statement_text_cache:
                continue
            self._full_statement_text_cache[query_cache_key] = True
            tags = self.check.tags + ["db:{}".format(row['database_name'])]
            yield {
                "timestamp": time.time() * 1000,
                "host": self.check.resolved_hostname,
                "ddagentversion": datadog_agent.get_version(),
                "ddsource": "sqlserver",
                "ddtags": ",".join(tags),
                "dbm_type": "fqt",
                "db": {
                    "instance": row['database_name'],
                    "query_signature": row['query_signature'],
                    "user": row.get("user_name", None),
                    "statement": row['text'],
                },
                'sqlserver': {
                    'query_hash': row['query_hash'],
                    'query_plan_hash': row['query_plan_hash'],
                },
            }

    def run_job(self):
        self.collect_statement_metrics_and_plans()

    @tracked_method(agent_check_getter=agent_check_getter)
    def _load_plan(self, query_hash, query_plan_hash, cursor):
        self.log.debug("collecting plan. query_hash=%s query_plan_hash=%s", query_hash, query_plan_hash)
        self.log.debug("Running query [%s] %s", PLAN_LOOKUP_QUERY, (query_hash, query_plan_hash))
        cursor.execute(PLAN_LOOKUP_QUERY, ("0x" + query_hash, "0x" + query_plan_hash))
        result = cursor.fetchall()
        if not result:
            self.log.debug("failed to loan plan, it must have just been expired out of the plan cache")
            return None
        return result[0][0]

    @tracked_method(agent_check_getter=agent_check_getter)
    def _collect_plans(self, rows, cursor, deadline):
        for row in rows:
            if self.enforce_collection_interval_deadline and time.time() > deadline:
                self.log.debug("ending plan collection early because check deadline has been exceeded")
                self.check.count("dd.sqlserver.statements.deadline_exceeded", 1, **self.check.debug_stats_kwargs())
                return
            plan_key = (row['query_signature'], row['query_hash'], row['query_plan_hash'])
            if self._seen_plans_ratelimiter.acquire(plan_key):
                raw_plan = self._load_plan(row['query_hash'], row['query_plan_hash'], cursor)
                obfuscated_plan, collection_errors = None, None

                try:
                    obfuscated_plan = obfuscate_xml_plan(raw_plan)
                except Exception as e:
                    self.log.debug(
                        "failed to obfuscate XML Plan query_signature=%s query_hash=%s query_plan_hash=%s: %s",
                        row['query_signature'],
                        row['query_hash'],
                        row['query_plan_hash'],
                        e,
                    )
                    collection_errors = [{'code': "obfuscate_xml_plan_error", 'message': str(e)}]
                    self.check.count(
                        "dd.sqlserver.statements.error",
                        1,
                        **self.check.debug_stats_kwargs(tags=["error:obfuscate-xml-plan-{}".format(type(e))])
                    )

                tags = self.check.tags + ["db:{}".format(row['database_name'])]
                yield {
                    "host": self._db_hostname,
                    "ddagentversion": datadog_agent.get_version(),
                    "ddsource": "sqlserver",
                    "ddtags": ",".join(tags),
                    "timestamp": time.time() * 1000,
                    "dbm_type": "plan",
                    "db": {
                        "instance": row.get("database_name", None),
                        "plan": {
                            "definition": obfuscated_plan,
                            "signature": row['query_plan_hash'],
                            "collection_errors": collection_errors,
                        },
                        "query_signature": row['query_signature'],
                        "user": row.get("user_name", None),
                        "statement": row['text'],
                    },
                    'sqlserver': {
                        'query_hash': row['query_hash'],
                        'query_plan_hash': row['query_plan_hash'],
                    },
                }
