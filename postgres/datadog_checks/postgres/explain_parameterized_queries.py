# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import logging
import re

import psycopg2

from datadog_checks.base.utils.db.sql import compute_sql_signature
from datadog_checks.base.utils.tracking import tracked_method
from datadog_checks.postgres.cursor import CommenterDictCursor

from .util import DBExplainError
from .version_utils import V12

logger = logging.getLogger(__name__)

PREPARE_STATEMENT_QUERY = 'PREPARE dd_{query_signature} AS {statement}'

PARAM_TYPES_COUNT_QUERY = '''\
SELECT CARDINALITY(parameter_types) FROM pg_prepared_statements WHERE name = 'dd_{query_signature}'
'''

EXECUTE_PREPARED_STATEMENT_QUERY = 'EXECUTE dd_{prepared_statement}({generic_values})'

EXPLAIN_QUERY = 'SELECT {explain_function}($stmt${statement}$stmt$)'


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

    def __init__(self, check, config, explain_function):
        self._check = check
        self._config = config
        self._explain_function = explain_function

    @tracked_method(agent_check_getter=agent_check_getter)
    def explain_statement(self, dbname, statement, obfuscated_statement):
        if self._check.version < V12:
            # if pg version < 12, skip explaining parameterized queries because
            # plan_cache_mode is not supported
            e = psycopg2.errors.UndefinedParameter("Unable to explain parameterized query")
            logger.debug(
                "Unable to explain parameterized query. Postgres version %s does not support plan_cache_mode",
                self._check.version,
            )
            return None, DBExplainError.parameterized_query, '{}'.format(type(e))
        self._set_plan_cache_mode(dbname)

        query_signature = compute_sql_signature(obfuscated_statement)
        try:
            self._create_prepared_statement(dbname, statement, obfuscated_statement, query_signature)
        except Exception as e:
            # if we fail to create a prepared statement, we cannot explain the query
            return None, DBExplainError.failed_to_explain_with_prepared_statement, '{}'.format(type(e))

        try:
            result = self._explain_prepared_statement(dbname, statement, obfuscated_statement, query_signature)
            if result:
                plan = result[0][0][0]
                return plan, DBExplainError.explained_with_prepared_statement, None
            else:
                # the explain function was executed but no plan was returned
                logger.debug(
                    "Unable to explain parameterized query. "
                    "The explain function %s was executed but no plan was returned",
                    self._explain_function,
                )
                return None, DBExplainError.no_plan_returned_with_prepared_statement, None
        except Exception as e:
            return None, DBExplainError.failed_to_explain_with_prepared_statement, '{}'.format(type(e))
        finally:
            self._deallocate_prepared_statement(dbname, query_signature)

    def _set_plan_cache_mode(self, dbname):
        self._execute_query(dbname, "SET plan_cache_mode = force_generic_plan")

    @tracked_method(agent_check_getter=agent_check_getter)
    def _create_prepared_statement(self, dbname, statement, obfuscated_statement, query_signature):
        try:
            self._execute_query(
                dbname,
                PREPARE_STATEMENT_QUERY.format(query_signature=query_signature, statement=statement),
            )
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
            raise

    @tracked_method(agent_check_getter=agent_check_getter)
    def _get_number_of_parameters_for_prepared_statement(self, dbname, query_signature):
        rows = self._execute_query_and_fetch_rows(
            dbname, PARAM_TYPES_COUNT_QUERY.format(query_signature=query_signature)
        )
        return rows[0][0] if rows else 0

    @tracked_method(agent_check_getter=agent_check_getter)
    def _explain_prepared_statement(self, dbname, statement, obfuscated_statement, query_signature):
        null_parameter = ','.join(
            'null' for _ in range(self._get_number_of_parameters_for_prepared_statement(dbname, query_signature))
        )
        execute_prepared_statement_query = EXECUTE_PREPARED_STATEMENT_QUERY.format(
            prepared_statement=query_signature, generic_values=null_parameter
        )
        try:
            return self._execute_query_and_fetch_rows(
                dbname,
                EXPLAIN_QUERY.format(
                    explain_function=self._explain_function,
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
            raise

    def _deallocate_prepared_statement(self, dbname, query_signature):
        try:
            self._execute_query(
                dbname, "DEALLOCATE PREPARE dd_{query_signature}".format(query_signature=query_signature)
            )
        except Exception as e:
            logger.warning(
                'Failed to deallocate prepared statement query_signature=[%s] | err=[%s]',
                query_signature,
                e,
            )

    def _execute_query(self, dbname, query):
        # Psycopg2 connections do not get closed when context ends;
        # leaving context will just mark the connection as inactive in MultiDatabaseConnectionPool
        with self._check.db_pool.get_connection(dbname, self._check._config.idle_connection_timeout) as conn:
            with conn.cursor(cursor_factory=CommenterDictCursor) as cursor:
                logger.debug('Executing query=[%s]', query)
                cursor.execute(query)

    def _execute_query_and_fetch_rows(self, dbname, query):
        with self._check.db_pool.get_connection(dbname, self._check._config.idle_connection_timeout) as conn:
            with conn.cursor(cursor_factory=CommenterDictCursor) as cursor:
                cursor.execute(query)
                return cursor.fetchall()

    def _is_parameterized_query(self, statement: str) -> bool:
        # Use regex to match $1 to determine if a query is parameterized
        # BUT single quoted string '$1' should not be considered as a parameter
        # e.g. SELECT * FROM products WHERE id = $1; -- $1 is a parameter
        # e.g. SELECT * FROM products WHERE id = '$1'; -- '$1' is not a parameter
        parameterized_query_pattern = r"(?<!')\$(?!'\$')[\d]+(?!')"
        return re.search(parameterized_query_pattern, statement) is not None
