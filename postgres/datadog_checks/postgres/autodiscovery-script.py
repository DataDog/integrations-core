# Proof of concept script for Postgres db autodiscovery.
# Pass a host to discover databases on that host.

from typing import List, Callable
import psycopg2
import sys
import os
import threading
import time
from six import iteritems
from  datetime import datetime
from datadog import initialize, statsd

sys.path.append(os.path.abspath("/home/ec2-user/dd/integrations-core/datadog_checks_base"))

from util import fmt, get_schema_field
from datadog_checks.base.utils.discovery import Discovery
from datadog_checks.base import AgentCheck

# sys.path.append(os.path.abspath("/home/ec2-user/dd/integrations-core"))
from relationsmanager import RelationsManager, RELATION_METRICS
from connections import MultiDatabaseConnectionPoolLimited


AUTODISCOVERY_QUERY: str = """select {columns} from pg_catalog.pg_database where datistemplate = false;"""

options = {
    'statsd_host':'127.0.0.1',
    'statsd_port':8125
}

initialize(**options)

class PostgresAutodiscovery(Discovery): 
    def __init__(self, host: str, max_conn: int) -> None:
        super(PostgresAutodiscovery, self).__init__(self._get_databases, include={'.*': 10}, exclude=[], interval=60)
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
        items = list(super().get_items())
        items_parsed = [item[1] for item in items]
        return items_parsed
   
    def _connect(self, dbname: str = None) -> None:
        # Use ident method
        connection_string = "host="+self.host+" user=postgres password=p0stgres"
        if dbname is not None:
            connection_string += " dbname=" + dbname
        conn = psycopg2.connect(connection_string)

        # print("connected")
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
        print("Databases found were: ", databases)
        return databases 
    
    def run_query_scope(self, cursor, scope, cols, descriptors):
        # try:
        query = fmt.format(scope['query'], metrics_columns=", ".join(cols))
        schema_field = get_schema_field(descriptors)
        # print(schema_field)
        formatted_query = self._relations_manager.filter_relation_query(query, schema_field)
        # print(formatted_query)
        # while(1):
        #     pass
        cursor.execute(formatted_query)
        
        results = cursor.fetchall()
        return results

    def query_relations(self, database: str) -> None:
        # print(cached_dbs)
        conn = None
        # wait for connection to open up
        while conn == None:
            conn = self._conn_pool.get_connection(database, self.default_ttl)
        print("got connection")
        cursor = conn.cursor()

        # now query all relations metrics
        for scope in RELATION_METRICS:
            cols = list(scope['metrics']) 
            descriptors = scope['descriptors']
            results = self.run_query_scope(cursor, scope, cols, descriptors)
            # print(results)
            if not results:
                print("got none")    
                self._conn_pool.release(database)
                return None
            print("got results")
            for row in results:
                descriptor_values = row[: len(descriptors)]
                column_values = row[len(descriptors) :]

                # build a map of descriptors and values
                desc_map = {name: value for (_, name), value in zip(descriptors, descriptor_values)}

                # build tags
                tags = ['db'+database]
                # add tags from descriptors
                tags += [("%s:%s" % (k, v)) for (k, v) in iteritems(desc_map)]

                # now submit!
                for column, value in zip(cols, column_values):
                    name, submit_metric = scope['metrics'][column]
                    # only submit gauge metrics
                    if submit_metric[1] == AgentCheck.gauge:
                        statsd.set('eden_test'+name, value, tags=set(tags), hostname='eden-test-pgautodiscovery')

        print("done getting")
        # print(relations)
        self._conn_pool.release(database)
        # self._conn_pool.get_connection(database, self.default_ttl)

    def query_relations_all_databases_threaded(self) -> None:
        self._print_num_connections()
        databases = self.get_items()

        db_threads = list()
        for i, database in enumerate(databases):         
            if i % 10 == 0:
                # report samples
                self._print_num_connections()

            thread = threading.Thread(target=self.query_relations, args=(database,), name=database)
            db_threads.append(thread)
            thread.start()

        for index, thread in enumerate(db_threads):
            thread.join()

        self._print_num_connections()

    def query_relations_all_databases_sync(self) -> None:
        self._print_num_connections()
        databases = self.get_items()

        for i, database in enumerate(databases):
            if i % 10 == 0:
                # report samples
                self._print_num_connections()
            self.query_relations(database)

        self._print_num_connections()


    def _print_num_connections(self) -> None:
        # wait for connection to open up
        conn = None
        while conn == None:
            conn = self._conn_pool.get_connection('postgres', self.default_ttl)

        cursor = conn.cursor()
        cursor.execute("SELECT sum(numbackends) FROM pg_stat_database;")
        rows = list(cursor.fetchall())
        print("NUM CONNECTIONS IS",rows[0])
        # self._conn_pool.release('postgres') 

if __name__ == "__main__":
    discovery = PostgresAutodiscovery("0.0.0.0", 10)
    a_database = discovery.get_items()[0]
    discovery._print_num_connections()
    discovery.query_relations(a_database)

    now = datetime.now()
    discovery.query_relations_all_databases_sync()
    print("elapsed: ", datetime.now() - now, "non-threaded finished")

    # now = datetime.now()
    # discovery.query_relations_all_databases_threaded()
    # print("elapsed: ", datetime.now() - now, "threaded finished")