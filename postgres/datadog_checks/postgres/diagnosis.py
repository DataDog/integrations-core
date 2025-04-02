from typing import Callable

import psycopg2

from .version_utils import V10

POSTGRES_SETTINGS = """
SELECT name, setting
FROM pg_settings
WHERE name IN (
    'shared_preload_libraries',
    'track_activity_query_size',
    'pg_stat_statements.track',
    'pg_stat_statements.max',
    'pg_stat_statements.track_utility',
    'track_io_timing'
);
"""

PG_STAT_DATABASE_DIAGNOSTIC_QUERY = """
SELECT pg_has_role('{database_user}', oid, 'member') as has_role
FROM pg_roles
WHERE rolname = 'pg_monitor';
"""


class PostgresDiagnostics:
    """Used to generate the diagnostic tests for the Postgres Integration"""

    def __init__(self, check):
        self.check = check

    """
    Returns a list of diagnostic functions depending on if DBM is enbaled or not
    """

    def get_diagnostic_functions(self) -> list[Callable[[], None]]:
        funcs = self._base_diagnostic_functions()

        if self.check._config.dbm_enabled:
            dbm_specific_diagnostic_functions = self._dbm_diagnostic_functions()

            if dbm_specific_diagnostic_functions:
                funcs.append(dbm_specific_diagnostic_functions)

        return funcs

    def _dbm_diagnostic_functions(self) -> list[Callable[[], None]]:
        funcs = []

        # Check Postgres Settings
        return funcs

    def _base_diagnostic_functions(self) -> list[Callable[[], None]]:
        diagnostic_category = "Base Postgres Integration Diagnostics"
        funcs: Callable[[]] = []

        def diagnose_pg_stat_database_privileges():
            diagnostic_name = "pg_stat_database Priviledges"
            diagnostic_description = "Checks the Datadog user's priviledges for the 'pg_stat_database' table"

            pg_stat_database_diagnostic_query = (
                f"""SELECT has_table_privilege('{self.check._config.user}', 'pg_stat_database', 'SELECT')"""
            )

            with self.check.db_pool.get_connection("postgres", self.check._config.idle_connection_timeout) as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
                    cursor.execute(pg_stat_database_diagnostic_query)
                    rows = cursor.fetchall()

                    for row in rows:
                        result = row[0]

                        if result:
                            self.check.diagnosis.success(
                                name=diagnostic_name,
                                category=diagnostic_category,
                                description=diagnostic_description,
                                diagnosis="The datadog user 'datadog' has SELECT priviledges on the 'pg_stat_database' \
                                    table",
                            )

                        else:
                            self.check.diagnosis.fail(
                                name=diagnostic_name,
                                category=diagnostic_category,
                                description=diagnostic_description,
                                diagnosis=f"The datadog user '{self.check._config.user}' doesn't have SELECT \
                                    priviledges for the 'pg_stat_database' table",
                                remediation=f"""Grant the Datadog user '{self.check._config.user}' SELECT priviledges \
                                    for the pg_stat_database using the following command:\
                                    \nGRANT SELECT ON pg_stat_database TO datadog;""",
                            )

        def diagnose_pg_monitor_grant():
            diagnostic_name = "pg_monitor Priviledges"
            diagnostic_description = "Checks the Datadog user's priviledges "
            query = PG_STAT_DATABASE_DIAGNOSTIC_QUERY.format(database_user=self.check._config.user)

            raw_version = self.check._version_utils.get_raw_version(self.check.db())
            version = self.check._version_utils.parse_version(raw_version)

            if version < V10:
                self.check.diagnosis.success(
                    name=diagnostic_name,
                    category=diagnostic_category,
                    description=diagnostic_description,
                    diagnosis="Skipping the check for pg_monitor as this is not applicable for Postgres versions < 10",
                )

            else:
                with self.check.db_pool.get_connection("postgres", self.check._config.idle_connection_timeout) as conn:
                    with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
                        cursor.execute(query)
                        rows = cursor.fetchall()

                        self.check.diagnosis.fail(
                            name=diagnostic_name,
                            category=diagnostic_category,
                            description=diagnostic_description,
                            diagnosis=f"Checking the status of the datadog user {rows}",
                            remediation=""" here """,
                        )

        funcs.append(diagnose_pg_stat_database_privileges)
        funcs.append(diagnose_pg_monitor_grant)

        return funcs
