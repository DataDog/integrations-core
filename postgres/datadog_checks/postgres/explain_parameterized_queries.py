import logging

import psycopg2

from datadog_checks.base.utils.db.sql import compute_sql_signature

logger = logging.getLogger(__name__)

PREPARE_STATEMENT_QUERY = "PREPARE {query_signature} AS {statement}"

PREPARED_STATEMENT_EXISTS_QUERY = """\
SELECT * FROM pg_prepared_statements WHERE name = '{query_signature}'
"""

PARAM_TYPES_FOR_PREPARED_STATEMENT_QUERY = """\
SELECT parameter_types FROM pg_prepared_statements WHERE name = '{query_signature}'
"""

EXECUTE_PREPARED_STATEMENT_QUERY = "EXECUTE {prepared_statement}({null_parameter})"

# TODO: Get from statement_samples file
EXPLAIN_QUERY = "SELECT {explain_function}($stmt${statement}$stmt$)"


class ExplainParameterizedQueries:
    def __init__(self, check, config):
        self._check = check
        self._config = config

    def explain_statement(self, statement, obfuscated_statement):
        query_signature = compute_sql_signature(obfuscated_statement)
        if not self._create_prepared_statement(statement, obfuscated_statement, query_signature):
            return None
        return self._explain_prepared_statement(statement, obfuscated_statement, query_signature)

    def _prepared_statement_exists(self, statement, obfuscated_statement, query_signature):
        try:
            return (
                len(
                    self._execute_query_and_fetch_rows(
                        PREPARED_STATEMENT_EXISTS_QUERY.format(query_signature=query_signature)
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

    def _create_prepared_statement(self, statement, obfuscated_statement, query_signature):
        # TODO: Is there an 'ON CONFLICT DO NOTHING' equivalent for prepared statements so we can avoid this?
        if self._prepared_statement_exists(statement, obfuscated_statement, query_signature):
            return True
        try:
            self._execute_query(PREPARE_STATEMENT_QUERY.format(query_signature=query_signature, statement=statement))
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

    def _get_number_of_parameters_for_prepared_statement(self, query_signature):
        rows = self._execute_query_and_fetch_rows(
            PARAM_TYPES_FOR_PREPARED_STATEMENT_QUERY.format(query_signature=query_signature)
        )
        if rows:
            # e.g. [['{integer,record,text,text}']] -> '{integer,record,text,text}'
            param_types = rows[0][0]
            # e.g. '{integer,record,text,text}' -> 'integer,record,text,text'
            param_types = param_types.replace('{', '').replace('}', '')
            # e.g. 'integer,record,text,text' -> ['integer', 'record', 'text', 'text']
            return len(param_types.split(','))
        return 0

    def _explain_prepared_statement(self, statement, obfuscated_statement, query_signature):
        null_parameter = ','.join(
            'null' for _ in range(self._get_number_of_parameters_for_prepared_statement(query_signature))
        )
        execute_prepared_statement_query = EXECUTE_PREPARED_STATEMENT_QUERY.format(
            prepared_statement=query_signature, null_parameter=null_parameter
        )
        try:
            rows = self._execute_query_and_fetch_rows(
                EXPLAIN_QUERY.format(
                    explain_function=self._config.statement_samples_config.get(
                        'explain_function', 'datadog.explain_statement'
                    ),
                    statement=execute_prepared_statement_query,
                ),
            )
            logger.warning('EXPLAINED PREPARED STATEMENT=[%s]', rows)
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

    def _execute_query(self, query):
        with self._check._get_db(self._config.dbname).cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
            logger.debug('Executing query=[%s]', query)
            cursor.execute(query)

    def _execute_query_and_fetch_rows(self, query):
        with self._check._get_db(self._config.dbname).cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
            logger.debug('Executing query=[%s] and fetching rows', query)
            cursor.execute(query)
            return cursor.fetchall()

    def _log_all_prepared_statements_for_sessions(self):
        with self._check._get_db(self._config.dbname).cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
            cursor.execute("SELECT * FROM pg_prepared_statements")
            logger.warning("ALL PREPARED STATEMENTS: %s", cursor.fetchall())
