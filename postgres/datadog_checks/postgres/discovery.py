from typing import List, Callable
from datadog_checks.base.utils.discovery import Discovery
import psycopg2
import logging
from connections import MultiDatabaseConnectionPool

AUTODISCOVERY_QUERY: str = """select {columns} from pg_catalog.pg_database where datistemplate = false;"""

class PostgresAutodiscovery(Discovery): 
    def __init__(self, host: str, include: List[str], exclude: List[str], interval: int, max_databases: int, log: logging.Logger, conn_pool: MultiDatabaseConnectionPool) -> None:
        # parent class asks for includelist to be a dictionary
        super(PostgresAutodiscovery, self).__init__(self._get_databases, include={'.*': 10}, exclude=[], interval=60)
        self.host = host
        self._conn_pool = conn_pool

    
    def get_items(self) -> List[str]:
        """
        Get_items() from parent class returns a generator with four objects:
            > yield pattern, key(item), item, config
        This function takes the item of interest (dbname) from this four-tuple
        and returns the full list of database names from the generator.
        """
        items = list(super().get_items())
        items_parsed = [item[1] for item in items]
        return items_parsed
    
    def _get_autodiscovery_query(self) -> str:
        autodiscovery_query = AUTODISCOVERY_QUERY.format(columns=', '.join(['datname']))
        return autodiscovery_query
    
    def _get_databases(self) -> List[str]:
        with self._conn_pool.get_connection_cm('postgres', self.default_ttl)
        try:
            conn = self._conn_pool.get_connection('postgres', self.default_ttl)
        except psycopg2.OperationalError:

        cursor = conn.cursor()
        autodiscovery_query = self._get_autodiscovery_query()
        cursor.execute(autodiscovery_query)
        databases = list(cursor.fetchall())
        databases = [x[0] for x in databases] # fetchall returns list of tuples representing rows, so need to parse
        print("Databases found were: ", databases)
        return databases 