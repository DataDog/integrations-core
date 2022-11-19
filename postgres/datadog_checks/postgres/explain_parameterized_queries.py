import logging

import psycopg2

from datadog_checks.base.utils.db.sql import compute_sql_signature
from .version_utils import V12

logger = logging.getLogger(__name__)

PREPARED_STATEMENT_EXISTS_QUERY = '''\
SELECT * FROM pg_prepared_statements WHERE name = 'dd_{query_signature}'
'''

PREPARE_STATEMENT_QUERY = 'PREPARE dd_{query_signature} AS {statement}'

PARAM_TYPES_FOR_PREPARED_STATEMENT_QUERY = '''\
SELECT parameter_types FROM pg_prepared_statements WHERE name = 'dd_{query_signature}'
'''

EXECUTE_PREPARED_STATEMENT_QUERY = 'EXECUTE dd_{prepared_statement}({null_parameter})'

# TODO: Get from statement_samples file
EXPLAIN_QUERY = 'SELECT {explain_function}($stmt${statement}$stmt$)'


class ExplainParameterizedQueries:
    # TODO: Docstring on how this works
    def __init__(self, check, config):
        self._check = check
        self._config = config

    def explain_statement(self, dbname, statement, obfuscated_statement):
        if self._check.version < V12:
            return None
        self._set_plan_cache_mode(dbname)

        query_signature = compute_sql_signature(obfuscated_statement)
        if not self._create_prepared_statement(dbname, statement, obfuscated_statement, query_signature):
            return None
        result = self._explain_prepared_statement(dbname, statement, obfuscated_statement, query_signature)
        if result:
            return result[0][0][0]
        return None

    def _set_plan_cache_mode(self, dbname):
        self._execute_query(dbname, "SET plan_cache_mode = force_generic_plan")

    def _prepared_statement_exists(self, dbname, statement, obfuscated_statement, query_signature):
        try:
            return (
                len(
                    self._execute_query_and_fetch_rows(
                        dbname, PREPARED_STATEMENT_EXISTS_QUERY.format(query_signature=query_signature)
                    )
                )
                > 0
            )
        except Exception as e:
            if self._config.log_unobfuscated_plans:
                logger.warning(
                    'Failed to check if prepared statement exists for statement(%s)=[%s] | err=[%s]',
                    query_signature,
                    statement,
                    e,
                )
            else:
                logger.warning(
                    'Failed to check if prepared statement exists for statement(%s)=[%s] | err=[%s]',
                    query_signature,
                    obfuscated_statement,
                    e,
                )
            return False

    def _create_prepared_statement(self, dbname, statement, obfuscated_statement, query_signature):
        # TODO: Is there an 'ON CONFLICT DO NOTHING' equivalent for prepared statements so we can avoid this?
        if self._prepared_statement_exists(dbname, statement, obfuscated_statement, query_signature):
            return True
        try:
            self._execute_query(
                dbname,
                PREPARE_STATEMENT_QUERY.format(query_signature=query_signature, statement=statement),
            )
            return True
        except Exception as e:
            if self._config.log_unobfuscated_plans:
                logger.warning(
                    'Failed to create prepared statement when explaining statement(%s)=[%s] | err=[%s]',
                    query_signature,
                    statement,
                    e,
                )
            else:
                logger.warning(
                    'Failed to create prepared statement when explaining statement(%s)=[%s] | err=[%s]',
                    query_signature,
                    obfuscated_statement,
                    e,
                )
        return False

    def _get_number_of_parameters_for_prepared_statement(self, dbname, query_signature):
        rows = self._execute_query_and_fetch_rows(
            dbname, PARAM_TYPES_FOR_PREPARED_STATEMENT_QUERY.format(query_signature=query_signature)
        )
        if rows:
            # e.g. [['{integer,record,text,text}']] -> '{integer,record,text,text}'
            param_types = rows[0][0]
            # e.g. '{integer,record,text,text}' -> 'integer,record,text,text'
            param_types = param_types.replace('{', '').replace('}', '')
            # e.g. 'integer,record,text,text' -> ['integer', 'record', 'text', 'text']
            return len(param_types.split(','))
        return 0

    def _explain_prepared_statement(self, dbname, statement, obfuscated_statement, query_signature):
        null_parameter = ','.join(
            'null' for _ in range(self._get_number_of_parameters_for_prepared_statement(dbname, query_signature))
        )
        execute_prepared_statement_query = EXECUTE_PREPARED_STATEMENT_QUERY.format(
            prepared_statement=query_signature, null_parameter=null_parameter
        )
        try:
            rows = self._execute_query_and_fetch_rows(
                dbname,
                EXPLAIN_QUERY.format(
                    explain_function=self._config.statement_samples_config.get(
                        'explain_function', 'datadog.explain_statement'
                    ),
                    statement=execute_prepared_statement_query,
                ),
            )
            return rows
        except Exception as e:
            if self._config.log_unobfuscated_plans:
                logger.warning(
                    'Failed to explain parameterized statement(%s)=[%s] | err=[%s]',
                    query_signature,
                    statement,
                    e,
                )
            else:
                logger.warning(
                    'Failed to explain parameterized statement(%s)=[%s] | err=[%s]',
                    query_signature,
                    obfuscated_statement,
                    e,
                )
        return None

    def _execute_query(self, dbname, query):
        with self._check._get_db(dbname).cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
            logger.debug('Executing query=[%s]', query)
            cursor.execute(query)

    def _execute_query_and_fetch_rows(self, dbname, query):
        with self._check._get_db(dbname).cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
            logger.debug('Executing query=[%s] and fetching rows', query)
            cursor.execute(query)
            return cursor.fetchall()
