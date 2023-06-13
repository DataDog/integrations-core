# Proof of concept script for Postgres db autodiscovery.
# Pass a host to discover databases on that host.

from typing import List, Callable
import psycopg2
import sys
import os
import threading
import datetime

sys.path.append(os.path.abspath("/home/ec2-user/dd/integrations-core/datadog_checks_base"))

from util import fmt
from datadog_checks.base.utils.discovery import Discovery

# sys.path.append(os.path.abspath("/home/ec2-user/dd/integrations-core"))
from relationsmanager import RelationsManager, SIZE_METRICS
from connections import MultiDatabaseConnectionPoolLimited


AUTODISCOVERY_QUERY: str = """select {columns} from pg_catalog.pg_database where datistemplate = false;"""


class PostgresAutodiscovery(Discovery): 
    def __init__(self, host: str, max_conn: int) -> None:
        super(PostgresAutodiscovery, self).__init__(self._get_databases, include={'.*': 10}, exclude=[])
        self.host = host
        relations_config = [{'relation_regex': '.*'}]
        self._relations_manager = RelationsManager(relations_config)
        self._conn_pool = MultiDatabaseConnectionPoolLimited(self._connect, max_conn)
        self.default_ttl = 60000
        # get once to cache dbs
        self.get_items()
        # self._conn_pool = psycopg2.ThreadedConnectionPool(minconn=0, maxconn=maxconn, user="postgres", password="p0stgres", port="5432")
    
    def get_items(self) -> List[str]:
        """
        Get_items() from parent class returns a generator with four objects:
            > yield pattern, key(item), item, config
        This function takes the item of interest (dbname) from this four-tuple
        and returns the full list of database names from the generator.
        """
        items = list(super(PostgresAutodiscovery, self).get_items())
        items_parsed = [item[1] for item in items]
        return items_parsed
   
    def _connect(self, dbname: str = None) -> None:
        # Use ident method
        connection_string = "host="+self.host+" user=postgres password=p0stgres"
        if dbname is not None:
            connection_string += " dbname=" + dbname
        conn = psycopg2.connect(connection_string)

        print("connected")
        return conn

    def _get_autodiscovery_query(self) -> str:
        autodiscovery_query = AUTODISCOVERY_QUERY.format(columns=', '.join(['datname']))
        return autodiscovery_query

    def _get_databases(self) -> List[str]:
        conn = self._conn_pool.get_connection('postgres', self.default_ttl)
        cursor = conn.cursor()
        autodiscovery_query = self._get_autodiscovery_query()
        cursor.execute(autodiscovery_query)
        databases = list(cursor.fetchall())
        databases = [x[0] for x in databases] # fetchall returns list of tuples representing rows, so need to parse
        print("got", databases)
        return databases 

    def query_relations(self, database: str) -> None:
        # print(cached_dbs)
        conn = self._conn_pool.get_connection(database, self.default_ttl)
        cursor = conn.cursor()
        query = fmt.format(SIZE_METRICS['query'], metrics_columns=", ".join(SIZE_METRICS['metrics']))
        formatted_query = self._relations_manager.filter_relation_query(query, "nspname")
        cursor.execute(formatted_query)
        relations = list(cursor.fetchall())
        # print(relations)

    def query_relations_all_databases_threaded(self) -> None:
        self._print_num_connections()
        databases = self.get_items()

        db_threads = list()
        for database in databases:
            print("getting relations from", database)
            self._print_num_connections()
            thread = threading.Thread(target=self.query_relations, args=(database,))
            db_threads.append(thread)
            thread.start()

        for index, thread in enumerate(db_threads):
            thread.join()

        self._print_num_connections()

    def query_relations_all_databases_sync(self) -> None:
        self._print_num_connections()
        databases = self.get_items()

        for database in databases:
            print("getting relations from", database)
            self._print_num_connections()
            self.query_relations(database)

        self._print_num_connections()


    def _print_num_connections(self) -> None:
        conn = self._conn_pool.get_connection('postgres', self.default_ttl)
        cursor = conn.cursor()
        cursor.execute("SELECT sum(numbackends) FROM pg_stat_database;")
        rows = list(cursor.fetchall())
        print("NUM CONNECTIONS IS",rows[0])

if __name__ == "__main__":
    discovery = PostgresAutodiscovery("0.0.0.0", 5)
    a_database = discovery.get_items()[0]
    discovery._print_num_connections()
    discovery.query_relations(a_database)

    time = datetime.datetime.now()
    discovery.query_relations_all_databases_sync()
    print("elapsed: ", datetime.datetime.now() - time, "non-threaded finished")

    time = datetime.datetime.now()
    discovery.query_relations_all_databases_threaded()
    print("elapsed: ", datetime.datetime.now() - time, "threaded finished")