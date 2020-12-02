import json
import time

import psycopg2

from datadog_checks.base.log import get_check_logger

try:
    import datadog_agent
except ImportError:
    from ..stubs import datadog_agent

from datadog import statsd

from datadog_checks.base.utils.db.sql import submit_statement_sample_events, compute_exec_plan_signature, compute_sql_signature
from datadog_checks.base.utils.db.utils import ConstantRateLimiter

VALID_EXPLAIN_STATEMENTS = frozenset({'select', 'table', 'delete', 'insert', 'replace', 'update'})

# keys from pg_stat_activity to include along with each (sample & execution plan)
pg_stat_activity_sample_keys = [
    'query_start',
    'datname',
    'usesysid',
    'application_name',
    'client_addr',
    'client_port',
    'wait_event_type',
    'wait_event',
    'state',
]


class PostgresStatementSamples(object):
    """Collects telemetry for SQL statements"""

    def __init__(self, config):
        self.config = config
        self.log = get_check_logger()
        self._rate_limiter = ConstantRateLimiter(config.collect_exec_plans_rate_limit)
        self._activity_last_query_start = None

    def _get_new_pg_stat_activity(self, db, instance_tags=None):
        start_time = time.time()
        query = """
        SELECT * FROM {pg_stat_activity_view}
        WHERE datname = %s
        AND coalesce(TRIM(query), '') != ''
        """.format(
            pg_stat_activity_view=self.config.pg_stat_activity_view
        )
        db.rollback()
        with db.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
            if self._activity_last_query_start:
                cursor.execute(query + " AND query_start > %s", (self.config.dbname, self._activity_last_query_start,))
            else:
                cursor.execute(query, (self.config.dbname,))
            rows = cursor.fetchall()

        rows = [r for r in rows if r['query'] and r['datname'] and self.can_explain_statement(r['query'])]
        max_query_start = max(r['query_start'] for r in rows)
        if self._activity_last_query_start is None or max_query_start > self._activity_last_query_start:
            self._activity_last_query_start = max_query_start

        # TODO: once stable, either remove these development metrics or make them configurable in a debug mode
        statsd.histogram(
            "dd.postgres.get_new_pg_stat_activity.time", (time.time() - start_time) * 1000, tags=instance_tags
        )
        statsd.histogram("dd.postgres.get_new_pg_stat_activity.rows", len(rows), tags=instance_tags)
        statsd.increment("dd.postgres.get_new_pg_stat_activity.total_rows", len(rows), tags=instance_tags)
        return rows

    def collect_statement_samples(self, db, instance_tags):
        start_time = time.time()
        # avoid reprocessing the exact same statement
        seen_statements = set()
        # keep only one sample per unique (query, plan)
        seen_statement_plan_sigs = set()
        while time.time() - start_time < self.config.collect_exec_plans_time_limit:
            if len(seen_statement_plan_sigs) > self.config.collect_exec_plans_event_limit:
                break
            self._rate_limiter.sleep()
            samples = self._get_new_pg_stat_activity(db, instance_tags=instance_tags)
            events = self._explain_new_pg_stat_activity(
                db, samples, seen_statements, seen_statement_plan_sigs, instance_tags
            )
            if events:
                submit_statement_sample_events(events, instance_tags, "postgres")

        statsd.gauge(
            "dd.postgres.collect_execution_plans.total.time", (time.time() - start_time) * 1000, tags=instance_tags
        )
        statsd.gauge("dd.postgres.collect_execution_plans.seen_statements", len(seen_statements), tags=instance_tags)
        statsd.gauge(
            "dd.postgres.collect_execution_plans.seen_statement_plan_sigs",
            len(seen_statement_plan_sigs),
            tags=instance_tags,
        )

    def can_explain_statement(self, statement):
        # TODO: cleaner query cleaning to strip comments, etc.
        if statement == '<insufficient privilege>':
            self.log.warn("Insufficient privilege to collect statement.")
            return False
        if statement.strip().split(' ', 1)[0].lower() not in VALID_EXPLAIN_STATEMENTS:
            return False
        if statement.startswith('SELECT {}'.format(self.config.collect_exec_plan_function)):
            return False
        return True

    def _run_explain(self, db, statement, instance_tags=None):
        if not self.can_explain_statement(statement):
            return
        with db.cursor() as cursor:
            try:
                start_time = time.time()
                cursor.execute(
                    """SELECT {explain_function}($stmt${statement}$stmt$)""".format(
                        explain_function=self.config.collect_exec_plan_function, statement=statement
                    )
                )
                result = cursor.fetchone()
                statsd.histogram("dd.postgres.run_explain.time", (time.time() - start_time) * 1000, tags=instance_tags)
            except psycopg2.errors.UndefinedFunction:
                self.log.warn(
                    "Failed to collect execution plan due to undefined explain_function: %s.",
                    self.config.collect_exec_plan_function,
                )
                return None
            except Exception as e:
                statsd.increment("dd.postgres.run_explain.error", tags=instance_tags)
                self.log.error("failed to collect execution plan for query='%s'. (%s): %s", statement, type(e), e)
                return None
        if not result or len(result) < 1 or len(result[0]) < 1:
            return None
        return result[0][0]

    def _explain_new_pg_stat_activity(self, db, samples, seen_statements, seen_statement_plan_sigs, instance_tags):
        start_time = time.time()
        events = []
        for row in samples:
            original_statement = row['query']
            if original_statement in seen_statements:
                continue
            seen_statements.add(original_statement)

            plan_dict = None
            try:
                plan_dict = self._run_explain(db, original_statement, instance_tags)
            except Exception:
                statsd.increment("dd.postgres.explain_new_pg_stat_activity.error")
                self.log.exception("failed to explain & process query '%s'", original_statement)

            # Plans have several important signatures to tag events with. Note that for postgres, the
            # query_signature and resource_hash will be the same value.
            # - `plan_signature` - hash computed from the normalized JSON plan to group identical plan trees
            # - `resource_hash` - hash computed off the raw sql text to match apm resources
            # - `query_signature` - hash computed from the raw sql text to match query metrics
            if plan_dict:
                plan = json.dumps(plan_dict)
                normalized_plan = datadog_agent.obfuscate_sql_exec_plan(plan, normalize=True)
                obfuscated_plan = datadog_agent.obfuscate_sql_exec_plan(plan)
                plan_signature = compute_exec_plan_signature(normalized_plan)
                plan_cost = (plan_dict.get('Plan', {}).get('Total Cost', 0.0) or 0.0)
            else:
                plan = None
                normalized_plan = None
                obfuscated_plan = None
                plan_signature = None
                plan_cost = None

            obfuscated_statement = datadog_agent.obfuscate_sql(original_statement)
            query_signature = compute_sql_signature(obfuscated_statement)
            apm_resource_hash = query_signature
            statement_plan_sig = (query_signature, plan_signature)

            if statement_plan_sig not in seen_statement_plan_sigs:
                seen_statement_plan_sigs.add(statement_plan_sig)
                event = {
                    'db': {
                        'instance': row['datname'],
                        'statement': obfuscated_statement,
                        'query_signature': query_signature,
                        'resource_hash': apm_resource_hash,
                        'plan': obfuscated_plan,
                        'plan_cost': plan_cost,
                        'plan_signature': plan_signature,
                        'postgres': {k: row[k] for k in pg_stat_activity_sample_keys if k in row},
                    }
                }
                if self.config.collect_exec_plan_debug:
                    event['db']['debug'] = {
                        'original_plan': plan,
                        'normalized_plan': normalized_plan,
                        'original_statement': original_statement,
                    }
                events.append(event)
        statsd.histogram(
            "dd.postgres.explain_new_pg_stat_activity.time", (time.time() - start_time) * 1000, tags=instance_tags
        )
        return events
