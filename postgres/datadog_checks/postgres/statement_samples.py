import json
import logging
import os
import re
import time
from concurrent.futures.thread import ThreadPoolExecutor

import psycopg2
from cachetools import TTLCache

try:
    import datadog_agent
except ImportError:
    from ..stubs import datadog_agent

from datadog_checks.base import is_affirmative
from datadog_checks.base.log import get_check_logger
from datadog_checks.base.utils.db.sql import compute_exec_plan_signature, compute_sql_signature
from datadog_checks.base.utils.db.statement_samples import statement_samples_client
from datadog_checks.base.utils.db.utils import ConstantRateLimiter, resolve_db_host

VALID_EXPLAIN_STATEMENTS = frozenset({'select', 'table', 'delete', 'insert', 'replace', 'update'})

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
    WHERE datname = %s
    AND coalesce(TRIM(query), '') != ''
    AND query_start IS NOT NULL
""",
).strip()


class PostgresStatementSamples(object):
    """
    Collects statement samples and execution plans.
    """

    executor = ThreadPoolExecutor()

    def __init__(self, check, config):
        self._check = check
        self._db = None
        self._config = config
        self._log = get_check_logger()
        self._activity_last_query_start = None
        self._last_check_run = 0
        self._collection_loop_future = None
        self._tags = None
        self._tags_str = None
        self._service = "postgres"
        self._db_hostname = resolve_db_host(self._config.host)
        self._enabled = is_affirmative(self._config.statement_samples_config.get('enabled', False))
        self._run_sync = is_affirmative(self._config.statement_samples_config.get('run_sync', False))
        self._rate_limiter = ConstantRateLimiter(
            float(self._config.statement_samples_config.get('collections_per_second', 1))
        )
        self._explain_function = self._config.statement_samples_config.get(
            'explain_function', 'datadog.explain_statement'
        )

        # explained_statements_cache: limit how often we try to re-explain the same query
        self._explained_statements_cache = TTLCache(
            maxsize=int(self._config.statement_samples_config.get('explained_statements_cache_maxsize', 5000)),
            ttl=60 * 60 / int(self._config.statement_samples_config.get('explained_statements_per_hour_per_query', 60)),
        )

        # seen_samples_cache: limit the ingestion rate per (query_signature, plan_signature)
        self._seen_samples_cache = TTLCache(
            # assuming ~100 bytes per entry (query & plan signature, key hash, 4 pointers (ordered dict), expiry time)
            # total size: 10k * 100 = 1 Mb
            maxsize=int(self._config.statement_samples_config.get('seen_samples_cache_maxsize', 10000)),
            ttl=60 * 60 / int(self._config.statement_samples_config.get('samples_per_hour_per_query', 15)),
        )

    def run_sampler(self, tags):
        """
        start the sampler thread if not already running
        :param tags:
        :return:
        """
        if not self._enabled:
            self._log.debug("Statement sampler not enabled")
            return
        self._tags = tags
        self._tags_str = ','.join(self._tags)
        for t in self._tags:
            if t.startswith('service:'):
                self._service = t[len('service:') :]
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
        with self._get_db().cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
            params = (self._config.dbname,)
            if self._activity_last_query_start:
                query = query + " AND query_start > %s"
                params = params + (self._activity_last_query_start,)
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

    def _get_db(self):
        # while psycopg2 is threadsafe (meaning in theory we should be able to use the same connection as the parent
        # check), the parent doesn't use autocommit and instead calls commit() and rollback() explicitly, meaning
        # it can cause strange clashing issues if we're trying to use the same connection from another thread here.
        # since the statement sampler runs continuously it's best we have our own connection here with autocommit
        # enabled
        if not self._db or self._db.closed:
            self._db = self._check._new_connection()
            self._db.set_session(autocommit=True)
        if self._db.status != psycopg2.extensions.STATUS_READY:
            # Some transaction went wrong and the connection is in an unhealthy state. Let's fix that
            self._db.rollback()
        return self._db

    def _collection_loop(self):
        try:
            self._log.info("Starting statement sampler collection loop")
            while True:
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
            self.close()

    def close(self):
        if self._db and not self._db.closed:
            try:
                self._db.close()
            except Exception:
                self._log.exception("failed to close DB connection")
        self._db = None

    def _collect_statement_samples(self):
        self._rate_limiter.sleep()
        start_time = time.time()
        rows = self._get_new_pg_stat_activity()
        rows = self._filter_valid_statement_rows(rows)
        events = self._explain_pg_stat_activity(rows)
        submitted_count, failed_count = statement_samples_client.submit_events(events)
        elapsed_ms = (time.time() - start_time) * 1000
        self._check.histogram("dd.postgres.collect_statement_samples.time", elapsed_ms, tags=self._tags)
        self._check.count(
            "dd.postgres.collect_statement_samples.events_submitted.count", submitted_count, tags=self._tags
        )
        self._check.count(
            "dd.postgres.statement_samples.error", failed_count, tags=self._tags + ["error:submit-events"]
        )
        self._check.gauge(
            "dd.postgres.collect_statement_samples.seen_samples_cache.len",
            len(self._seen_samples_cache),
            tags=self._tags,
        )
        self._check.gauge(
            "dd.postgres.collect_statement_samples.explained_statements_cache.len",
            len(self._explained_statements_cache),
            tags=self._tags,
        )

    def _can_explain_statement(self, obfuscated_statement):
        if obfuscated_statement.startswith('SELECT {}'.format(self._explain_function)):
            return False
        if obfuscated_statement.startswith('autovacuum:'):
            return False
        if obfuscated_statement.split(' ', 1)[0].lower() not in VALID_EXPLAIN_STATEMENTS:
            return False
        return True

    def _run_explain(self, statement, obfuscated_statement):
        if not self._can_explain_statement(obfuscated_statement):
            return None
        with self._get_db().cursor() as cursor:
            try:
                start_time = time.time()
                self._log.debug("Running query: %s(%s)", self._explain_function, obfuscated_statement)
                cursor.execute(
                    """SELECT {explain_function}($stmt${statement}$stmt$)""".format(
                        explain_function=self._explain_function, statement=statement
                    )
                )
                result = cursor.fetchone()
                self._check.histogram(
                    "dd.postgres.run_explain.time", (time.time() - start_time) * 1000, tags=self._tags
                )
            except psycopg2.errors.UndefinedFunction:
                self._log.warning(
                    "Failed to collect execution plan due to undefined explain_function=%s",
                    self._explain_function,
                )
                self._check.count(
                    "dd.postgres.statement_samples.error", 1, tags=self._tags + ["error:explain-undefined-function"]
                )
                return None
            except Exception as e:
                self._log.debug("Failed to collect execution plan. query='%s'", obfuscated_statement, exc_info=1)
                self._check.count(
                    "dd.postgres.statement_samples.error", 1, tags=self._tags + ["error:explain-{}".format(type(e))]
                )
                return None
        if not result or len(result) < 1 or len(result[0]) < 1:
            return None
        return result[0][0]

    def _collect_plan_for_statement(self, row):
        try:
            obfuscated_statement = datadog_agent.obfuscate_sql(row['query'])
        except Exception as e:
            self._log.debug("Failed to obfuscate statement: %s", e)
            self._check.count("dd.postgres.statement_samples.error", 1, tags=self._tags + ["error:sql-obfuscate"])
            return None

        # limit the rate of explains done to the database
        query_signature = compute_sql_signature(obfuscated_statement)
        if query_signature in self._explained_statements_cache:
            return None
        self._explained_statements_cache[query_signature] = True

        # Plans have several important signatures to tag events with. Note that for postgres, the
        # query_signature and resource_hash will be the same value.
        # - `plan_signature` - hash computed from the normalized JSON plan to group identical plan trees
        # - `resource_hash` - hash computed off the raw sql text to match apm resources
        # - `query_signature` - hash computed from the raw sql text to match query metrics
        plan_dict = self._run_explain(row['query'], obfuscated_statement)
        plan, normalized_plan, obfuscated_plan, plan_signature, plan_cost = None, None, None, None, None
        if plan_dict:
            plan = json.dumps(plan_dict)
            normalized_plan = datadog_agent.obfuscate_sql_exec_plan(plan, normalize=True)
            obfuscated_plan = datadog_agent.obfuscate_sql_exec_plan(plan)
            plan_signature = compute_exec_plan_signature(normalized_plan)
            plan_cost = plan_dict.get('Plan', {}).get('Total Cost', 0.0) or 0.0

        statement_plan_sig = (query_signature, plan_signature)
        if statement_plan_sig not in self._seen_samples_cache:
            self._seen_samples_cache[statement_plan_sig] = True
            event = {
                "host": self._db_hostname,
                "service": self._service,
                "ddsource": "postgres",
                "ddtags": self._tags_str,
                "network": {
                    "client": {
                        "ip": row.get('client_addr', None),
                        "port": row.get('client_port', None),
                        "hostname": row.get('client_hostname', None),
                    }
                },
                "db": {
                    "instance": row.get('datname', None),
                    "plan": {"definition": obfuscated_plan, "cost": plan_cost, "signature": plan_signature},
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
                    event['timestamp'] = time.mktime(row['state_change'].timetuple()) * 1000
            else:
                event['timestamp'] = time.time() * 1000
            return event

    def _explain_pg_stat_activity(self, rows):
        for row in rows:
            try:
                event = self._collect_plan_for_statement(row)
                if event:
                    yield event
            except Exception:
                self._log.exception("Crashed trying to collect execution plan for statement")
                self._check.count(
                    "dd.postgres.statement_samples.error",
                    1,
                    tags=self._tags + ["error:collect-plan-for-statement-crash"],
                )
