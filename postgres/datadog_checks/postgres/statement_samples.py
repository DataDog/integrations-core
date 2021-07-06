import logging
import os
import re
import threading
import time
from concurrent.futures.thread import ThreadPoolExecutor
from enum import Enum
from typing import Dict, Optional, Tuple

import psycopg2
from cachetools import TTLCache

try:
    import datadog_agent
except ImportError:
    from ..stubs import datadog_agent

from datadog_checks.base import is_affirmative
from datadog_checks.base.log import get_check_logger
from datadog_checks.base.utils.db.sql import compute_exec_plan_signature, compute_sql_signature
from datadog_checks.base.utils.db.utils import (
    ConstantRateLimiter,
    RateLimitingTTLCache,
    default_json_event_encoding,
    resolve_db_host,
)
from datadog_checks.base.utils.serialization import json
from datadog_checks.base.utils.time import get_timestamp

SUPPORTED_EXPLAIN_STATEMENTS = frozenset({'select', 'table', 'delete', 'insert', 'replace', 'update', 'with'})

# columns from pg_stat_activity which correspond to attributes common to all databases and are therefore stored in
# under other standard keys
pg_stat_activity_sample_exclude_keys = {
    # we process & obfuscate this separately
    'query',
    # stored separately
    'application_name',
    'datname',
    'usename',
    'client_addr',
    'client_hostname',
    'client_port',
}

#
PG_STAT_ACTIVITY_QUERY = re.sub(
    r'\s+',
    ' ',
    """
    SELECT * FROM {pg_stat_activity_view}
    WHERE coalesce(TRIM(query), '') != ''
    AND query_start IS NOT NULL
""",
).strip()

EXPLAIN_VALIDATION_QUERY = "SELECT * FROM pg_stat_activity"


class DBExplainError(Enum):
    """
    Denotes the various reasons a query may not have an explain statement.
    """

    # database error i.e connection error
    database_error = 'database_error'

    # this could be the result of a missing EXPLAIN function
    invalid_schema = 'invalid_schema'

    # a value retrieved from the EXPLAIN function could be invalid
    invalid_result = 'invalid_result'

    # some statements cannot be explained i.e AUTOVACUUM
    no_plans_possible = 'no_plans_possible'

    # there could be a problem with the EXPLAIN function (missing, invalid permissions, or an incorrect definition)
    failed_function = 'failed_function'


class PostgresStatementSamples(object):
    """
    Collects statement samples and execution plans.
    """

    executor = ThreadPoolExecutor()

    def __init__(self, check, config):
        self._check = check
        # map[dbname -> psycopg connection]
        self._db_pool = {}
        self._config = config
        self._log = get_check_logger()
        self._activity_last_query_start = None
        self._last_check_run = 0
        self._collection_loop_future = None
        self._cancel_event = threading.Event()
        self._tags = None
        self._tags_no_db = None
        self._db_hostname = resolve_db_host(self._config.host)
        self._enabled = is_affirmative(self._config.statement_samples_config.get('enabled', False))
        self._run_sync = is_affirmative(self._config.statement_samples_config.get('run_sync', False))
        self._rate_limiter = ConstantRateLimiter(
            float(self._config.statement_samples_config.get('collections_per_second', 1))
        )
        self._explain_function = self._config.statement_samples_config.get(
            'explain_function', 'datadog.explain_statement'
        )

        self._collection_strategy_cache = TTLCache(
            maxsize=self._config.statement_samples_config.get('collection_strategy_cache_maxsize', 1000),
            ttl=self._config.statement_samples_config.get('collection_strategy_cache_ttl', 300),
        )

        # explained_statements_ratelimiter: limit how often we try to re-explain the same query
        self._explained_statements_ratelimiter = RateLimitingTTLCache(
            maxsize=int(self._config.statement_samples_config.get('explained_statements_cache_maxsize', 5000)),
            ttl=60 * 60 / int(self._config.statement_samples_config.get('explained_statements_per_hour_per_query', 60)),
        )

        # seen_samples_ratelimiter: limit the ingestion rate per (query_signature, plan_signature)
        self._seen_samples_ratelimiter = RateLimitingTTLCache(
            # assuming ~100 bytes per entry (query & plan signature, key hash, 4 pointers (ordered dict), expiry time)
            # total size: 10k * 100 = 1 Mb
            maxsize=int(self._config.statement_samples_config.get('seen_samples_cache_maxsize', 10000)),
            ttl=60 * 60 / int(self._config.statement_samples_config.get('samples_per_hour_per_query', 15)),
        )

    def cancel(self):
        self._cancel_event.set()

    def _dbtags(self, db, *extra_tags):
        """
        Returns the default instance tags with the initial "db" tag replaced with the provided tag
        """
        t = ["db:" + db]
        if extra_tags:
            t.extend(extra_tags)
        if self._tags_no_db:
            t.extend(self._tags_no_db)
        return t

    def run_sampler(self, tags):
        """
        start the sampler thread if not already running
        :param tags:
        :return:
        """
        if not self._enabled:
            self._log.debug("Statement sampler not enabled")
            return

        # since statement samples are collected from all databases on this host we need to tag telemetry with the
        # right "db" tag which may be different from the initial database that the check is configured to connect to
        self._tags = tags
        self._tags_str = ','.join(self._tags)
        self._tags_no_db = [t for t in tags if not t.startswith('db:')]
        self._last_check_run = time.time()
        if self._run_sync or is_affirmative(os.environ.get('DBM_STATEMENT_SAMPLER_RUN_SYNC', "false")):
            self._log.debug("Running statement sampler synchronously")
            self._collect_statement_samples()
        elif self._collection_loop_future is None or not self._collection_loop_future.running():
            self._collection_loop_future = PostgresStatementSamples.executor.submit(self._collection_loop)
        else:
            self._log.debug("Statement sampler collection loop already running")

    def _get_new_pg_stat_activity(self):
        start_time = time.time()
        query = PG_STAT_ACTIVITY_QUERY.format(pg_stat_activity_view=self._config.pg_stat_activity_view)
        params = ()
        if self._config.dbstrict:
            query = query + " AND datname = %s"
            params = params + (self._config.dbname,)
        else:
            query = query + " AND " + " AND ".join("datname NOT ILIKE %s" for _ in self._config.ignore_databases)
            params = params + tuple(self._config.ignore_databases)
        if self._activity_last_query_start:
            query = query + " AND query_start > %s"
            params = params + (self._activity_last_query_start,)
        with self._get_db(self._config.dbname).cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
            self._log.debug("Running query [%s] %s", query, params)
            cursor.execute(query, params)
            rows = cursor.fetchall()
        self._check.histogram(
            "dd.postgres.get_new_pg_stat_activity.time", (time.time() - start_time) * 1000, tags=self._tags
        )
        self._check.histogram("dd.postgres.get_new_pg_stat_activity.rows", len(rows), tags=self._tags)
        self._log.debug("Loaded %s rows from %s", len(rows), self._config.pg_stat_activity_view)
        return rows

    def _filter_valid_statement_rows(self, rows):
        insufficient_privilege_count = 0
        total_count = 0
        for row in rows:
            total_count += 1
            if not row['datname']:
                continue
            query = row['query']
            if not query:
                continue
            if query == '<insufficient privilege>':
                insufficient_privilege_count += 1
                continue
            if self._activity_last_query_start is None or row['query_start'] > self._activity_last_query_start:
                self._activity_last_query_start = row['query_start']
            yield row
        if insufficient_privilege_count > 0:
            self._log.warning(
                "Insufficient privilege for %s/%s queries when collecting from %s.", self._config.pg_stat_activity_view
            )
            self._check.count(
                "dd.postgres.statement_samples.error",
                insufficient_privilege_count,
                tags=self._tags + ["error:insufficient-privilege"],
            )

    def _get_db(self, dbname):
        # while psycopg2 is threadsafe (meaning in theory we should be able to use the same connection as the parent
        # check), the parent doesn't use autocommit and instead calls commit() and rollback() explicitly, meaning
        # it can cause strange clashing issues if we're trying to use the same connection from another thread here.
        # since the statement sampler runs continuously it's best we have our own connection here with autocommit
        # enabled
        db = self._db_pool.get(dbname)
        if not db or db.closed:
            self._log.debug("initializing connection to dbname=%s", dbname)
            db = self._check._new_connection(dbname)
            db.set_session(autocommit=True)
            self._db_pool[dbname] = db
        if db.status != psycopg2.extensions.STATUS_READY:
            # Some transaction went wrong and the connection is in an unhealthy state. Let's fix that
            db.rollback()
        return db

    def _collection_loop(self):
        try:
            self._log.info("Starting statement sampler collection loop")
            while True:
                if self._cancel_event.isSet():
                    self._log.info("Collection loop cancelled")
                    self._check.count("dd.postgres.statement_samples.collection_loop_cancel", 1, tags=self._tags)
                    break
                if time.time() - self._last_check_run > self._config.min_collection_interval * 2:
                    self._log.info("Sampler collection loop stopping due to check inactivity")
                    self._check.count("dd.postgres.statement_samples.collection_loop_inactive_stop", 1, tags=self._tags)
                    break
                self._collect_statement_samples()
        except psycopg2.errors.DatabaseError as e:
            self._log.warning(
                "Statement sampler database error: %s", e, exc_info=self._log.getEffectiveLevel() == logging.DEBUG
            )
            self._check.count(
                "dd.postgres.statement_samples.error",
                1,
                tags=self._tags + ["error:database-{}".format(type(e))],
            )
        except Exception as e:
            self._log.exception("Statement sampler collection loop crash")
            self._check.count(
                "dd.postgres.statement_samples.error",
                1,
                tags=self._tags + ["error:collection-loop-crash-{}".format(type(e))],
            )
        finally:
            self._log.info("Shutting down statement sampler collection loop")
            self._close_db_pool()

    def _close_db_pool(self):
        for dbname, db in self._db_pool.items():
            if db and not db.closed:
                try:
                    db.close()
                except Exception:
                    self._log.exception("failed to close DB connection for db=%s", dbname)
            self._db_pool[dbname] = None

    def _collect_statement_samples(self):
        self._rate_limiter.sleep()
        start_time = time.time()
        rows = self._get_new_pg_stat_activity()
        rows = self._filter_valid_statement_rows(rows)
        events = self._explain_pg_stat_activity(rows)
        submitted_count = 0
        for e in events:
            self._check.database_monitoring_query_sample(json.dumps(e, default=default_json_event_encoding))
            submitted_count += 1
        elapsed_ms = (time.time() - start_time) * 1000
        self._check.histogram("dd.postgres.collect_statement_samples.time", elapsed_ms, tags=self._tags)
        self._check.count(
            "dd.postgres.collect_statement_samples.events_submitted.count", submitted_count, tags=self._tags
        )
        self._check.gauge(
            "dd.postgres.collect_statement_samples.seen_samples_cache.len",
            len(self._seen_samples_ratelimiter),
            tags=self._tags,
        )
        self._check.gauge(
            "dd.postgres.collect_statement_samples.explained_statements_cache.len",
            len(self._explained_statements_ratelimiter),
            tags=self._tags,
        )

    def _can_explain_statement(self, obfuscated_statement):
        if obfuscated_statement.startswith('SELECT {}'.format(self._explain_function)):
            return False
        if obfuscated_statement.startswith('autovacuum:'):
            return False
        if obfuscated_statement.split(' ', 1)[0].lower() not in SUPPORTED_EXPLAIN_STATEMENTS:
            return False
        return True

    def _get_db_explain_setup_state(self, dbname):
        # type: (str) -> Tuple[Optional[DBExplainError], Optional[Exception]]
        try:
            self._get_db(dbname)
        except (psycopg2.DatabaseError, psycopg2.OperationalError) as e:
            self._log.warning(
                "cannot collect execution plans due to failed DB connection to dbname=%s: %s", dbname, repr(e)
            )
            return DBExplainError.database_error, e

        try:
            result = self._run_explain(dbname, EXPLAIN_VALIDATION_QUERY, EXPLAIN_VALIDATION_QUERY)
        except psycopg2.errors.InvalidSchemaName as e:
            self._log.warning("cannot collect execution plans due to invalid schema in dbname=%s: %s", dbname, repr(e))
            return DBExplainError.invalid_schema, e
        except psycopg2.DatabaseError as e:
            # if the schema is valid then it's some problem with the function (missing, or invalid permissions,
            # incorrect definition)
            self._log.warning("cannot collect execution plans in dbname=%s: %s", dbname, repr(e))
            return DBExplainError.failed_function, e

        if not result:
            return DBExplainError.invalid_result, None

        return None, None

    def _get_db_explain_setup_state_cached(self, dbname):
        # type: (str) -> Tuple[DBExplainError, Exception]
        strategy_cache = self._collection_strategy_cache.get(dbname)
        if strategy_cache:
            db_explain_error, err = strategy_cache
            self._log.debug("using cached explain_setup_state for DB '%s': %s", dbname, db_explain_error)
            return db_explain_error, err

        db_explain_error, err = self._get_db_explain_setup_state(dbname)
        self._collection_strategy_cache[dbname] = (db_explain_error, err)
        self._log.debug("caching new explain_setup_state for DB '%s': %s", dbname, db_explain_error)

        return db_explain_error, err

    def _run_explain(self, dbname, statement, obfuscated_statement):
        start_time = time.time()
        with self._get_db(dbname).cursor() as cursor:
            self._log.debug("Running query on dbname=%s: %s(%s)", dbname, self._explain_function, obfuscated_statement)
            cursor.execute(
                """SELECT {explain_function}($stmt${statement}$stmt$)""".format(
                    explain_function=self._explain_function, statement=statement
                )
            )
            result = cursor.fetchone()
            self._check.histogram(
                "dd.postgres.run_explain.time", (time.time() - start_time) * 1000, tags=self._dbtags(dbname)
            )
            if not result or len(result) < 1 or len(result[0]) < 1:
                return None
            return result[0][0]

    def _run_explain_safe(self, dbname, statement, obfuscated_statement):
        # type: (str, str, str) -> Tuple[Optional[Dict], Optional[DBExplainError], Optional[Exception]]
        if not self._can_explain_statement(obfuscated_statement):
            return None, DBExplainError.no_plans_possible, None

        db_explain_error, err = self._get_db_explain_setup_state_cached(dbname)
        if db_explain_error is not None:
            self._check.count(
                "dd.postgres.statement_samples.error",
                1,
                tags=self._dbtags(dbname, "error:explain-{}".format(db_explain_error)),
            )
            return None, db_explain_error, err

        try:
            return self._run_explain(dbname, statement, obfuscated_statement), None, None
        except psycopg2.errors.DatabaseError as e:
            self._log.debug("Failed to collect execution plan: %s", repr(e))
            self._check.count(
                "dd.postgres.statement_samples.error",
                1,
                tags=self._dbtags(dbname, "error:explain-{}".format(type(e))),
            )
            return None, DBExplainError.database_error, e

    def _collect_plan_for_statement(self, row):
        try:
            obfuscated_statement = datadog_agent.obfuscate_sql(row['query'])
        except Exception as e:
            self._log.debug("Failed to obfuscate statement: %s", e)
            self._check.count(
                "dd.postgres.statement_samples.error", 1, tags=self._dbtags(row['datname'], "error:sql-obfuscate")
            )
            return None

        # limit the rate of explains done to the database
        query_signature = compute_sql_signature(obfuscated_statement)
        cache_key = (row['datname'], query_signature)
        if not self._explained_statements_ratelimiter.acquire(cache_key):
            return None

        # Plans have several important signatures to tag events with. Note that for postgres, the
        # query_signature and resource_hash will be the same value.
        # - `plan_signature` - hash computed from the normalized JSON plan to group identical plan trees
        # - `resource_hash` - hash computed off the raw sql text to match apm resources
        # - `query_signature` - hash computed from the raw sql text to match query metrics
        plan_dict, explain_err_code, err = self._run_explain_safe(row['datname'], row['query'], obfuscated_statement)
        collection_error = None
        if explain_err_code:
            collection_error = {'code': explain_err_code.value, 'message': '{}'.format(type(err)) if err else None}

        plan, normalized_plan, obfuscated_plan, plan_signature, plan_cost = None, None, None, None, None
        if plan_dict:
            plan = json.dumps(plan_dict)
            # if we're using the orjson implementation then json.dumps returns bytes
            plan = plan.decode('utf-8') if isinstance(plan, bytes) else plan
            normalized_plan = datadog_agent.obfuscate_sql_exec_plan(plan, normalize=True)
            obfuscated_plan = datadog_agent.obfuscate_sql_exec_plan(plan)
            plan_signature = compute_exec_plan_signature(normalized_plan)
            plan_cost = plan_dict.get('Plan', {}).get('Total Cost', 0.0) or 0.0

        statement_plan_sig = (query_signature, plan_signature)
        if self._seen_samples_ratelimiter.acquire(statement_plan_sig):
            event = {
                "host": self._db_hostname,
                "ddsource": "postgres",
                "ddtags": ",".join(self._dbtags(row['datname'])),
                "timestamp": time.time() * 1000,
                "network": {
                    "client": {
                        "ip": row.get('client_addr', None),
                        "port": row.get('client_port', None),
                        "hostname": row.get('client_hostname', None),
                    }
                },
                "db": {
                    "instance": row.get('datname', None),
                    "plan": {
                        "definition": obfuscated_plan,
                        "cost": plan_cost,
                        "signature": plan_signature,
                        "collection_error": collection_error,
                    },
                    "query_signature": query_signature,
                    "resource_hash": query_signature,
                    "application": row.get('application_name', None),
                    "user": row['usename'],
                    "statement": obfuscated_statement,
                },
                'postgres': {k: v for k, v in row.items() if k not in pg_stat_activity_sample_exclude_keys},
            }
            if row['state'] in {'idle', 'idle in transaction'}:
                if row['state_change'] and row['query_start']:
                    event['duration'] = (row['state_change'] - row['query_start']).total_seconds() * 1e9
                    # If the transaction is idle then we have a more specific "end time" than the current time at
                    # which we're collecting this event. According to the postgres docs, all of the timestamps in
                    # pg_stat_activity are `timestamp with time zone` so the timezone should always be present. However,
                    # if there is something wrong and it's missing then we can't use `state_change` for the timestamp
                    # of the event else we risk the timestamp being significantly off and the event getting dropped
                    # during ingestion.
                    if row['state_change'].tzinfo:
                        event['timestamp'] = get_timestamp(row['state_change']) * 1000
            return event

    def _explain_pg_stat_activity(self, rows):
        for row in rows:
            try:
                event = self._collect_plan_for_statement(row)
                if event:
                    yield event
            except Exception:
                self._log.exception(
                    "Crashed trying to collect execution plan for statement in dbname=%s", row['datname']
                )
                self._check.count(
                    "dd.postgres.statement_samples.error",
                    1,
                    tags=self._tags + ["error:collect-plan-for-statement-crash"],
                )
