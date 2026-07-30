# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import logging
import re
from typing import Dict, List, Optional, Tuple

import psycopg

from datadog_checks.base.utils.tracking import tracked_method

from .util import DBExplainError
from .version_utils import V12

PARAMETERIZED_QUERY_PATTERN = re.compile(r"(?<!')\$(?!'\$')[\d]+(?!')")

logger = logging.getLogger(__name__)

PREPARE_STATEMENT_QUERY = 'PREPARE dd_{query_signature} AS {statement}'

PARAM_TYPES_COUNT_QUERY = '''\
SELECT CARDINALITY(parameter_types) FROM pg_prepared_statements WHERE name = 'dd_{query_signature}'
'''

EXECUTE_PREPARED_STATEMENT_QUERY = 'EXECUTE dd_{prepared_statement}{parameters}'

EXPLAIN_QUERY = 'SELECT {explain_function}(%s)'

# Errors raised when PostgreSQL can't resolve a parameter's type while preparing or explaining a parameterized
# query (e.g. untyped NULL parameters from ORMs using the extended query protocol: "operator does not exist:
# bigint = text"). The parameter types that made the original query valid aren't available in pg_stat_activity,
# so these queries can't be explained and the failure is deterministic for a given query signature.
EXPECTED_PARAMETER_TYPE_ERRORS = (
    psycopg.errors.IndeterminateDatatype,
    psycopg.errors.UndefinedFunction,
    psycopg.errors.DatatypeMismatch,
    psycopg.errors.AmbiguousFunction,
)


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
    def explain_statement(
        self, dbname: str, statement: str, obfuscated_statement: str, query_signature: str
    ) -> Tuple[Optional[Dict], Optional[DBExplainError], Optional[str]]:
        if self._check.version < V12:
            # if pg version < 12, skip explaining parameterized queries because
            # plan_cache_mode is not supported
            e = psycopg.errors.UndefinedParameter("Unable to explain parameterized query")
            logger.debug(
                "Unable to explain parameterized query. Postgres version %s does not support plan_cache_mode",
                self._check.version,
            )
            return None, DBExplainError.parameterized_query, '{}'.format(type(e))
        with self._check.db_pool.get_connection(dbname) as conn:
            try:
                self._set_plan_cache_mode(conn)
                prepared_statement_error = self._create_prepared_statement(
                    conn, statement, obfuscated_statement, query_signature
                )
            except Exception as e:
                # an unexpected failure creating the prepared statement means we cannot explain the query
                return None, DBExplainError.failed_to_explain_with_prepared_statement, '{}'.format(type(e))

            if prepared_statement_error is not None:
                # an expected, deterministic parameter type-resolution failure (e.g. untyped NULL parameters).
                error_code, err_msg = prepared_statement_error
                return None, error_code, err_msg

            try:
                result, explain_error = self._explain_prepared_statement(
                    conn, statement, obfuscated_statement, query_signature
                )
                if explain_error is not None:
                    # an expected, deterministic parameter type-resolution failure surfaced during EXPLAIN EXECUTE
                    error_code, err_msg = explain_error
                    return None, error_code, err_msg
                elif result:
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
                self._deallocate_prepared_statement(conn, query_signature)

    def _set_plan_cache_mode(self, conn):
        self._execute_query(conn, "SET plan_cache_mode = force_generic_plan")

    @tracked_method(agent_check_getter=agent_check_getter)
    def _create_prepared_statement(
        self, conn, statement: str, obfuscated_statement: str, query_signature: str
    ) -> Optional[Tuple[DBExplainError, str]]:
        # Returns None on success, or a (DBExplainError, err_msg) tuple when the query can't be prepared because
        # a parameter's type can't be resolved. Other unexpected errors are re-raised.
        try:
            self._execute_query(
                conn,
                PREPARE_STATEMENT_QUERY.format(query_signature=query_signature, statement=statement),
            )
            return None
        except EXPECTED_PARAMETER_TYPE_ERRORS as e:
            # The parameter types can't be resolved, so this query can't be prepared (and therefore can't be
            # explained). Map the failure to the corresponding explain error code.
            self._log_failed_statement(
                'Failed to create prepared statement when explaining statement(%s)=[%s] | err=[%s]',
                statement,
                obfuscated_statement,
                query_signature,
                e,
            )
            return self._map_parameter_type_error(e)
        except Exception as e:
            self._log_failed_statement(
                'Failed to create prepared statement when explaining statement(%s)=[%s] | err=[%s]',
                statement,
                obfuscated_statement,
                query_signature,
                e,
            )
            raise

    def _map_parameter_type_error(self, e: Exception) -> Tuple[DBExplainError, str]:
        # Map an unresolved parameter-type error to its specific explain error code so cached responses
        # and emitted error tags reflect the actual failure rather than a generic one.
        if isinstance(e, psycopg.errors.IndeterminateDatatype):
            return DBExplainError.indeterminate_datatype, '{}'.format(type(e))
        if isinstance(e, psycopg.errors.DatatypeMismatch):
            return DBExplainError.datatype_mismatch, '{}'.format(type(e))
        return DBExplainError.undefined_function, '{}'.format(type(e))

    def _log_failed_statement(
        self, message: str, statement: str, obfuscated_statement: str, query_signature: str, e: Exception
    ) -> None:
        # Logs the obfuscated statement by default, falling back to the raw statement only when explicitly
        # configured. The message is expected to interpolate (query_signature, statement, error) in that order.
        logged_statement = obfuscated_statement
        if self._config.log_unobfuscated_plans:
            logged_statement = statement
        logger.debug(message, query_signature, logged_statement, e)

    @tracked_method(agent_check_getter=agent_check_getter)
    def _get_number_of_parameters_for_prepared_statement(self, conn, query_signature):
        rows = self._execute_query_and_fetch_rows(conn, PARAM_TYPES_COUNT_QUERY.format(query_signature=query_signature))
        return rows[0][0] if rows else 0

    @tracked_method(agent_check_getter=agent_check_getter)
    def _generate_prepared_statement_query(self, conn, query_signature: str) -> str:
        parameters = ""
        num_params = self._get_number_of_parameters_for_prepared_statement(conn, query_signature)

        if num_params > 0:
            null_parameters = ','.join('null' for _ in range(num_params))
            parameters = f"({null_parameters})"

        return EXECUTE_PREPARED_STATEMENT_QUERY.format(prepared_statement=query_signature, parameters=parameters)

    @tracked_method(agent_check_getter=agent_check_getter)
    def _explain_prepared_statement(
        self, conn, statement: str, obfuscated_statement: str, query_signature: str
    ) -> Tuple[Optional[List], Optional[Tuple[DBExplainError, str]]]:
        # Returns (rows, None) on success, or (None, (DBExplainError, err_msg)) when a parameter's type can't be
        # resolved during EXPLAIN EXECUTE. Other unexpected errors are re-raised.
        try:
            prepared_statement_query = self._generate_prepared_statement_query(conn, query_signature)
            rows = self._execute_query_and_fetch_rows(
                conn,
                EXPLAIN_QUERY.format(explain_function=self._explain_function),
                (prepared_statement_query,),
            )
            return rows, None
        except EXPECTED_PARAMETER_TYPE_ERRORS as e:
            # The parameter types couldn't be resolved during EXPLAIN EXECUTE, so the query can't be explained.
            self._log_failed_statement(
                'Failed to explain parameterized statement(%s)=[%s] | err=[%s]',
                statement,
                obfuscated_statement,
                query_signature,
                e,
            )
            return None, self._map_parameter_type_error(e)
        except Exception as e:
            self._log_failed_statement(
                'Failed to explain parameterized statement(%s)=[%s] | err=[%s]',
                statement,
                obfuscated_statement,
                query_signature,
                e,
            )
            raise

    def _deallocate_prepared_statement(self, conn, query_signature):
        try:
            self._execute_query(conn, "DEALLOCATE PREPARE dd_{query_signature}".format(query_signature=query_signature))
        except Exception as e:
            logger.debug(
                'Failed to deallocate prepared statement query_signature=[%s] | err=[%s]',
                query_signature,
                e,
            )

    def _execute_query(self, conn, query):
        with conn.cursor() as cursor:
            logger.debug('Executing query=[%s]', query)
            cursor.execute(query, ignore_query_metric=True)

    def _execute_query_and_fetch_rows(self, conn, query, params=None):
        with conn.cursor() as cursor:
            cursor.execute(query, params, ignore_query_metric=True)
            return cursor.fetchall()

    def _is_parameterized_query(self, statement: str) -> bool:
        # Use regex to match $1 to determine if a query is parameterized
        # BUT single quoted string '$1' should not be considered as a parameter
        # e.g. SELECT * FROM products WHERE id = $1; -- $1 is a parameter
        # e.g. SELECT * FROM products WHERE id = '$1'; -- '$1' is not a parameter
        return PARAMETERIZED_QUERY_PATTERN.search(statement) is not None
