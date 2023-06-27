from typing import Dict, List, Callable
from datadog_checks.base.utils.discovery import Discovery
from datadog_checks.postgres.connections import MultiDatabaseConnectionPool
import logging

AUTODISCOVERY_QUERY: str = """select {columns} from pg_catalog.pg_database where datistemplate = false;"""

class PostgresAutodiscovery(Discovery): 
    def __init__(self, global_view_db: str, autodiscovery_config: Dict, log: logging.Logger, conn_pool: MultiDatabaseConnectionPool, default_ttl: int) -> None:
        # parent class asks for includelist to be a dictionary
        parsed_include = self._parse_includelist(autodiscovery_config.get("include", [".*"]))
        super(PostgresAutodiscovery, self).__init__(self._get_databases, include=parsed_include, exclude=autodiscovery_config.get("exclude", []), interval=autodiscovery_config.get("refresh", 3600))
        self._log = log
        self._db = global_view_db
        self._conn_pool = conn_pool
        self._default_ttl = default_ttl
        self._max_databases = autodiscovery_config.get("max_databases", 100)

    def _parse_includelist(self, include: List[str]) -> Dict[str, int]:
        ret = {}
        for item in include:
            ret[item] = 0
        return ret
    
    def get_items(self) -> List[str]:
        """
        Get_items() from parent class returns a generator with four objects:
            > yield pattern, key(item), item, config
        This function takes the item of interest (dbname) from this four-tuple
        and returns the full list of database names from the generator.
        """
        items = list(super().get_items())
        items_parsed = [item[1] for item in items]
        if len(items_parsed) > self._max_databases:
            items_parsed = items_parsed[:self._max_databases]
            self._log.warning("Autodiscovery found more than {} databases, which was specified as a limit. Truncating list and running checks only on \
                              the following databases: {}".format(self._max_databases, items_parsed))
        return items_parsed
    
    def _get_autodiscovery_query(self) -> str:
        autodiscovery_query = AUTODISCOVERY_QUERY.format(columns=', '.join(['datname']))
        return autodiscovery_query
    
    def _get_databases(self) -> List[str]:
        with self._conn_pool.get_connection(self._db, self._default_ttl) as conn:
            cursor = conn.cursor()
            autodiscovery_query = self._get_autodiscovery_query()
            cursor.execute(autodiscovery_query)
            databases = list(cursor.fetchall())
            databases = [x[0] for x in databases] # fetchall returns list of tuples representing rows, so need to parse
            self._log.info("Databases found were: {}".format(databases))
            return databases 
