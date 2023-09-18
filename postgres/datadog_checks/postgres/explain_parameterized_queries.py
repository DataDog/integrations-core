# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import logging
import re

from psycopg.rows import dict_row

from datadog_checks.base.utils.db.sql import compute_sql_signature
from datadog_checks.base.utils.tracking import tracked_method

from .version_utils import V12

logger = logging.getLogger(__name__)

PREPARE_STATEMENT_QUERY = 'PREPARE dd_{query_signature} AS {statement}'

PARAM_TYPES_COUNT_QUERY = '''\
SELECT CARDINALITY(parameter_types) as count FROM pg_prepared_statements WHERE name = 'dd_{query_signature}'
'''

EXECUTE_PREPARED_STATEMENT_QUERY = 'EXECUTE dd_{prepared_statement}({generic_values})'

EXPLAIN_QUERY = 'SELECT {explain_function}($stmt${statement}$stmt$) as explain_statement'


def agent_check_getter(self):
    return self._check


class ExplainParameterizedQueries:
    '''
    ExplainParameterizedQueries will attempt to use a workaround to explain a parameterized query.

    High-level explanation:
        Given the query: `SELECT * FROM products WHERE id = $1;`

        We're unable to explain this because we do not know the value of the parameter ($1). Attempting to explain
        this will result in an error.
            e.g. `EXPLAIN SELECT * FROM products WHERE id = $1;`
                Returns: error
        We could provide `null` as a value because it works with any datatype, but this will also not work
        because Postgres knows that no rows will be returned.
            e.g. `EXPLAIN SELECT * FROM products WHERE id = null;`
                Returns: no plan

        However, with Postgres versions 12 and above, you can control how the query planner behaves with
        the `plan_cache_mode`. The mode `force_generic_plan` will force Postgres to produce a generic plan.

        Furthermore, we're still faced with the problem of not knowing how many parameters there
        are in a query. So is there a clever way we can go about finding this information?
        Yes, if we create a prepared statement, the `pg_prepared_statements` table provides
        information such as how many parameters are required and the type.

        Note, prepared statements created by the user defined in the integration config are not persisted.
        When the session ends, all prepared statements are automatically deallocated by Postgres.

        Walkthrough:
            1. Set the plan cache mode: `SET plan_cache_mode = force_generic_plan;`
            2. Create a prepared statement: `PREPARE dd_products AS SELECT * FROM products WHERE id = $1;`
            3. Query `pg_prepared_statements` to determine how many parameters a query requires
            and provide generic values (null).
            4. Execute and explain: `EXPLAIN EXECUTE dd_products(null);`
                Returns: (plan)
    '''

    def __init__(self, check, config):
        self._check = check
        self._config = config

    @tracked_method(agent_check_getter=agent_check_getter)
    def explain_statement(self, dbname, statement, obfuscated_statement):
        if self._check.version < V12:
            return None

        query_signature = compute_sql_signature(obfuscated_statement)
        with self._check.db_pool.get_connection(dbname, self._check._config.idle_connection_timeout) as conn:
            self._set_plan_cache_mode(conn)

            if not self._create_prepared_statement(conn, statement, obfuscated_statement, query_signature):
                return None

            result = self._explain_prepared_statement(conn, statement, obfuscated_statement, query_signature)
            self._deallocate_prepared_statement(conn, query_signature)
            if result:
                return result[0]['explain_statement'][0]
        return None

    def _set_plan_cache_mode(self, conn):
        self._execute_query(conn, "SET plan_cache_mode = force_generic_plan")

    @tracked_method(agent_check_getter=agent_check_getter)
    def _create_prepared_statement(self, conn, statement, obfuscated_statement, query_signature):
        try:
            self._execute_query(
                conn, PREPARE_STATEMENT_QUERY.format(query_signature=query_signature, statement=statement)
            )
            return True
        except Exception as e:
            logged_statement = obfuscated_statement
            if self._config.log_unobfuscated_plans:
                logged_statement = statement
            logger.warning(
                'Failed to create prepared statement when explaining statement(%s)=[%s] | err=[%s]',
                query_signature,
                logged_statement,
                e,
            )
        return False

    @tracked_method(agent_check_getter=agent_check_getter)
    def _get_number_of_parameters_for_prepared_statement(self, conn, query_signature):
        rows = self._execute_query_and_fetch_rows(conn, PARAM_TYPES_COUNT_QUERY.format(query_signature=query_signature))
        count = 0
        if rows and 'count' in rows[0]:
            count = rows[0]['count']
        return count

    @tracked_method(agent_check_getter=agent_check_getter)
    def _explain_prepared_statement(self, conn, statement, obfuscated_statement, query_signature):
        null_parameter = ','.join(
            'null' for _ in range(self._get_number_of_parameters_for_prepared_statement(conn, query_signature))
        )
        execute_prepared_statement_query = EXECUTE_PREPARED_STATEMENT_QUERY.format(
            prepared_statement=query_signature, generic_values=null_parameter
        )
        try:
            return self._execute_query_and_fetch_rows(
                conn,
                EXPLAIN_QUERY.format(
                    explain_function=self._config.statement_samples_config.get(
                        'explain_function', 'datadog.explain_statement'
                    ),
                    statement=execute_prepared_statement_query,
                ),
            )
        except Exception as e:
            logged_statement = obfuscated_statement
            if self._config.log_unobfuscated_plans:
                logged_statement = statement
            logger.warning(
                'Failed to explain parameterized statement(%s)=[%s] | err=[%s]',
                query_signature,
                logged_statement,
                e,
            )
        return None

    def _deallocate_prepared_statement(self, conn, query_signature):
        try:
            self._execute_query(conn, "DEALLOCATE PREPARE dd_{query_signature}".format(query_signature=query_signature))
        except Exception as e:
            logger.warning(
                'Failed to deallocate prepared statement query_signature=[%s] | err=[%s]',
                query_signature,
                e,
            )

    def _execute_query(self, conn, query):
        with conn.cursor(row_factory=dict_row) as cursor:
            logger.debug('Executing query=[%s]', query)
            cursor.execute(query)

    def _execute_query_and_fetch_rows(self, conn, query):
        with conn.cursor(row_factory=dict_row) as cursor:
            logger.debug('Executing query=[%s]', query)
            cursor.execute(query)
            return cursor.fetchall()

    def _is_parameterized_query(self, statement: str) -> bool:
        # Use regex to match $1 to determine if a query is parameterized
        # BUT single quoted string '$1' should not be considered as a parameter
        # e.g. SELECT * FROM products WHERE id = $1; -- $1 is a parameter
        # e.g. SELECT * FROM products WHERE id = '$1'; -- '$1' is not a parameter
        parameterized_query_pattern = r"(?<!')\$(?!'\$')[\d]+(?!')"
        return re.search(parameterized_query_pattern, statement) is not None
