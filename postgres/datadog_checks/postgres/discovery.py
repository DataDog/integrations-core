# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from typing import Dict, List

from datadog_checks.base import AgentCheck
from datadog_checks.base.utils.discovery import Discovery
from datadog_checks.postgres.cursor import CommenterCursor
from datadog_checks.postgres.util import DatabaseConfigurationError, warning_with_tags

AUTODISCOVERY_QUERY: str = """select datname from pg_catalog.pg_database where datistemplate = false;"""
DEFAULT_EXCLUDES = ["cloudsqladmin", "rdsadmin"]
DEFAULT_MAX_DATABASES = 100
DEFAULT_REFRESH = 600


class PostgresAutodiscovery(Discovery):
    def __init__(
        self,
        check: AgentCheck,
        global_view_db: str,
        autodiscovery_config: Dict,
        default_ttl: int,
    ) -> None:
        super(PostgresAutodiscovery, self).__init__(
            self._get_databases,
            # parent class asks for includelist to be a dictionary
            include={db: 0 for db in autodiscovery_config.get("include", [".*"])},
            exclude=autodiscovery_config.get("exclude", DEFAULT_EXCLUDES),
            interval=autodiscovery_config.get("refresh", DEFAULT_REFRESH),
        )
        self._default_ttl = default_ttl
        self._db = global_view_db
        self._check = check
        self._log = self._check.log
        self.db_pool = self._check.db_pool
        self._max_databases = autodiscovery_config.get("max_databases", DEFAULT_MAX_DATABASES)
        self._cache_filtered = []

    def get_items(self) -> List[str]:
        """
        Get_items() from parent class returns a generator with four objects:
            > yield pattern, key(item), item, config
        This function takes the item of interest (dbname) from this four-tuple
        and returns the full list of database names from the generator.
        """
        prev_cached_items_len = len(self._cache_filtered)
        items = list(super().get_items())

        # check if the items got refreshed + went over limit
        # before this function applies
        # the max_databases limit
        if len(items) != prev_cached_items_len and len(items) > self._max_databases:
            self._check.record_warning(
                DatabaseConfigurationError.autodiscovered_databases_exceeds_limit,
                warning_with_tags(
                    "Autodiscovery found %d databases, which was more than the specified limit of %d. "
                    "Increase `max_databases` in the `database_autodiscovery` block of the agent configuration "
                    "to see these extra databases. "
                    "The database list will be truncated.",
                    len(items),
                    self._max_databases,
                    code=DatabaseConfigurationError.autodiscovered_databases_exceeds_limit.value,
                    max_databases=self._max_databases,
                ),
            )

        items_parsed = [item[1] for item in items][: self._max_databases]
        self._cache_filtered = items_parsed
        return items_parsed

    def _get_databases(self) -> List[str]:
        with self.db_pool.get_connection(self._db, self._default_ttl) as conn:
            with conn.cursor(cursor_factory=CommenterCursor) as cursor:
                cursor.execute(AUTODISCOVERY_QUERY)
                databases = list(cursor.fetchall())
                databases = [
                    x[0] for x in databases
                ]  # fetchall returns list of tuples representing rows, so need to parse
                self._log.debug("Autodiscovered databases were: {}".format(databases))
                return databases
