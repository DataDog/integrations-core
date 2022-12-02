import logging

import psycopg2

from datadog_checks.base.utils.db.sql import compute_sql_signature
from datadog_checks.base.utils.tracking import tracked_method

from .version_utils import V12

logger = logging.getLogger(__name__)

PREPARE_STATEMENT_QUERY = 'PREPARE dd_{query_signature} AS {statement}'

PREPARED_STATEMENT_EXISTS_QUERY = '''\
SELECT * FROM pg_prepared_statements WHERE name = 'dd_{query_signature}'
'''

PARAM_TYPES_FOR_PREPARED_STATEMENT_QUERY = '''\
SELECT parameter_types FROM pg_prepared_statements WHERE name = 'dd_{query_signature}'
'''

PG_PREPARED_STATEMENTS_SIZE_ESTIMATE_QUERY = "SELECT SUM(octet_length(ps.*::text)) FROM pg_prepared_statements AS ps"

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

    # Roughly equates to 4,882 prepared statements. This was calcuated by (20mb / 4096 bytes).
    # 4096 comes from DBM's recommended `track_activity_query_size` of 4096 which limits the SQL text retrieved
    # from `pg_stat_activity` and `pg_stat_statements` which is where the query statements come from.
    DEFAULT_MAX_ALLOWABLE_SPACE_MB = 20

    def __init__(self, check, config):
        self._check = check
        self._config = config

    @tracked_method(agent_check_getter=agent_check_getter)
    def explain_statement(self, dbname, statement, obfuscated_statement, tags):
        if self._check.version < V12:
            return None
        self._set_plan_cache_mode(dbname)

        query_signature = compute_sql_signature(obfuscated_statement)
        if not self._create_prepared_statement(dbname, statement, obfuscated_statement, query_signature):
            return None

        result = self._explain_prepared_statement(dbname, statement, obfuscated_statement, query_signature)
        self._cleanup_pg_prepared_statements(dbname, tags)
        if result:
            return result[0][0][0]
        return None

    def _set_plan_cache_mode(self, dbname):
        self._execute_query(dbname, "SET plan_cache_mode = force_generic_plan")

    @tracked_method(agent_check_getter=agent_check_getter)
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

    @tracked_method(agent_check_getter=agent_check_getter)
    def _create_prepared_statement(self, dbname, statement, obfuscated_statement, query_signature):
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

    @tracked_method(agent_check_getter=agent_check_getter)
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
                    explain_function=self._config.statement_samples_config.get(
                        'explain_function', 'datadog.explain_statement'
                    ),
                    statement=execute_prepared_statement_query,
                ),
            )
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

    @tracked_method(agent_check_getter=agent_check_getter)
    def _cleanup_pg_prepared_statements(self, dbname, tags):
        '''
        Prepared statements are not deallocated until the session ends, so to prevent taking up a lot of space,
        this method estimates how much space we've allocated for prepared statements and deallocates
        ~all~ prepared statements if we've reached our max (configurable option).
        '''
        rows = self._execute_query_and_fetch_rows(dbname, PG_PREPARED_STATEMENTS_SIZE_ESTIMATE_QUERY)
        pg_prepared_statements_mb = 0
        if rows:
            pg_prepared_statements_mb = rows[0][0] / 1048576  # 1MB

        max_pg_prepared_statements_space = self._config.statement_samples_config.get(
            'max_pg_prepared_statements_space', ExplainParameterizedQueries.DEFAULT_MAX_ALLOWABLE_SPACE_MB
        )
        if pg_prepared_statements_mb >= max_pg_prepared_statements_space:
            self._execute_query(dbname, "DEALLOCATE ALL")
            pg_prepared_statements_mb = 0

        self._check.gauge(
            "dd.postgres.explain_parameterized_queries.size",
            pg_prepared_statements_mb,
            tags=tags,
            hostname=self._check.resolved_hostname,
        )
        self._check.gauge(
            "dd.postgres.explain_parameterized_queries.max",
            max_pg_prepared_statements_space,
            tags=tags,
            hostname=self._check.resolved_hostname,
        )

    def _execute_query(self, dbname, query):
        with self._check._get_db(dbname).cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
            logger.debug('Executing query=[%s]', query)
            cursor.execute(query)

    def _execute_query_and_fetch_rows(self, dbname, query):
        with self._check._get_db(dbname).cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
            logger.debug('Executing query=[%s] and fetching rows', query)
            cursor.execute(query)
            return cursor.fetchall()
