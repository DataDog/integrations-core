from datadog_checks.sqlserver.const import (
    TABLES_IN_SCHEMA_QUERY,
    COLUMN_QUERY,
    PARTITIONS_QUERY,
    INDEX_QUERY,
    FOREIGN_KEY_QUERY,
    SCHEMA_QUERY,
)

from datadog_checks.sqlserver.utils import (
    execute_query_output_result_as_a_dict, get_list_chunks
)

import pdb

import time
import json
import copy

from datadog_checks.base.utils.db.utils import default_json_event_encoding

class SubmitData: 
    MAX_COLUMN_COUNT  = 100_000

    def __init__(self, submit_data_function, base_event, logger):
        self._submit = submit_data_function
        self._columns_count  = 0
        self.db_to_schemas = {} # dbname : { id : schema }
        self._base_event = base_event
        self._log = logger

    def store(self, db_name, schema, tables, columns_count):
        self._columns_count += columns_count
        schemas = self.db_to_schemas.setdefault(db_name, {})
        if schema["schema_id"] in schemas:
            known_tables = schemas[schema["schema_id"]].setdefault("tables",[])
            known_tables = known_tables + tables
        else:
            schemas[schema["schema_id"]] = copy.deepcopy(schema) # TODO a deep copy ? kind of costs not much to be safe
            schemas[schema["schema_id"]]["tables"] = tables
        if self._columns_count > self.MAX_COLUMN_COUNT:
            self._submit()

    def submit(self):
        pdb.set_trace()
        if not bool(self.db_to_schemas):
            return
        self._columns_count  = 0
        event = {**self._base_event,
                 "metadata" : [],
                 "timestamp": time.time() * 1000
                 }
        for db, schemas_by_id in self.db_to_schemas.items():
            event["metadata"] =  event["metadata"] + [{"db_name":db, "schemas": list(schemas_by_id.values()) }]
        json_event = json.dumps(event, default=default_json_event_encoding)
        self._log.debug("Reporting the following payload for schema collection: {}".format(json_event))
        self._submit(json_event)
        self.db_to_schemas = {}

#TODO Introduce total max for data
class Schemas:
    def __init__(self, check):
        self._check = check 
        self._log = check.log
        self.schemas_per_db = {} 
        base_event = {
                "host": self._check.resolved_hostname,
                #"agent_version": datadog_agent.get_version(),
                "dbms": "sqlserver", #TODO ?
                "kind": "", # TODO ? 
                #"collection_interval": self.schemas_collection_interval,
                #"dbms_version": self._payload_pg_version(),
                #"tags": self._tags_no_db,
                #"cloud_metadata": self._config.cloud_metadata,
            }
        self._dataSubmitter = SubmitData(self._check.database_monitoring_metadata, base_event, self._log)

        # These are fields related to the work to do while doing the initial intake
        # for diffs there should eb a self._done_db_list which will be used to see if new dbs have appeared/disappeared.
        self._databases_to_query = []
        self._current_table_list = None
        self._current_schema_list = None
        self._number_of_collected_tables = 0 #TODO later switch to columns

    def reset_data_collection(self):
        self._current_table_list = None  
        self._current_schema_list = None
        self._number_of_collected_tables = 0
       
    def _init_schema_collection(self):
        currently_known_databases = self._check.get_databases()
        if len(self._databases_to_query) == 0:
            self._databases_to_query = self._check.get_databases()
            return  
        else:
            if self._databases_to_query[0] not in currently_known_databases:
                #TODO if db dissapeared we invalidate indexes should be done in exception treatment of use DB ?
                #if DB is not there the first use db will throw and we continue until we find an existing db or exaust the list
                # the idea is always finish the existing DB list and then run "diff" logic which will create a new list of "tasks"
                self.reset_data_collection()

   #TODO update this at the very end as it constantly changing
    """schemas data struct is a dictionnary with key being a schema name the value is
    schema
    dict:
        "name": str
        "schema_id": str
        "principal_id": str
        "tables" : []
            object_id : str
            name : str
            columns: list of columns                  
                "columns": dict
                    name: str
                    data_type: str
                    default: str
                    is_nullable : str
            indexes : list of indexes - important
            foreign_keys : list of foreign keys
            partitions useful to know the number 
    """
    
    #sends all the data in one go but split in chunks (like Seth's solution)
    def collect_schemas_data(self):
        
        base_event = {
                "host": self._check.resolved_hostname,
                #"agent_version": datadog_agent.get_version(),
                "dbms": "sqlserver", #TODO ?
                "kind": "", # TODO ? 
                #"collection_interval": self.schemas_collection_interval,
                #"dbms_version": self._payload_pg_version(),
                #"tags": self._tags_no_db,
                #"cloud_metadata": self._config.cloud_metadata,
            }

        def fetch_schema_data(cursor, db_name):
            schemas = self._query_schema_information(cursor)
            chunk_size = 50
            for schema in schemas:
                tables = self._get_tables(schema, cursor)            
                tables_chunk = list(get_list_chunks(tables, chunk_size))
                for tables_chunk in tables_chunk:
                    columns_count, tables = self._get_tables_data(tables_chunk, schema, cursor)
                    self._dataSubmitter.store(db_name, schema, tables, columns_count)  
                #self._dataSubmitter.submit() # we force submit when we reach the end of schema, it's like in Seths solution
                if len(tables) == 0:
                    self._dataSubmitter.store(db_name, schema, [], 0)
                # to ask him if this is needed or we can submit only on 100 000 column
            # tells if we want to move to the next DB or stop
            return True
        self._check.do_for_databases(fetch_schema_data, self._check.get_databases())
        # submit the last chunk of data if any
        self._dataSubmitter.submit()
        
    # TODO how often ?

    #TODOTODO do we need this map/list format if we are not dumping in json ??? May be we need to send query results as they are ? 

    #TODO Looks fine similar to Postgres, do we need to do someting with prinicipal_id
    # or reporting principal_id is ok
    def _query_schema_information(self, cursor):

        # principal_id is kind of like an owner not sure if need it.
        self._log.debug("collecting db schemas")
        self._log.debug("Running query [%s]", SCHEMA_QUERY)
        cursor.execute(SCHEMA_QUERY)
        schemas = []
        columns = [i[0] for i in cursor.description]
        schemas = [dict(zip(columns, row)) for row in cursor.fetchall()]
        for schema in schemas:
            schema["tables"] = []
        self._log.debug("fetched schemas len(rows)=%s", len(schemas))
        return schemas
        
    #TODO collect diffs : we need to take care of new DB / removed DB . schemas new removed
    # will nedd a separate query for changed indexes
    def _get_tables_data(self, table_list, schema, cursor):
        if len(table_list) == 0:
            return
        name_to_id = {}
        id_to_all = {}
        table_names = ",".join(["'{}'".format(t.get("name")) for t in table_list])
        table_ids = ",".join(["{}".format(t.get("object_id")) for t in table_list])
        for t in table_list:
            name_to_id[t["name"]] = t["object_id"] 
            id_to_all[t["object_id"]] = t
        total_columns_number  = self._populate_with_columns_data(table_names, name_to_id, id_to_all, schema, cursor)
        self._populate_with_partitions_data(table_ids, id_to_all, cursor)
        self._populate_with_foreign_keys_data(table_ids, id_to_all, cursor)
        self._populate_with_index_data(table_ids, id_to_all, cursor)
        # unwrap id_to_all
        return total_columns_number, list(id_to_all.values())

    def _populate_with_columns_data(self, table_names, name_to_id, id_to_all, schema, cursor):
        # get columns if we dont have a dict here unlike postgres
        cursor.execute(COLUMN_QUERY.format(table_names, schema["name"]))
        data = cursor.fetchall()
        columns = [str(i[0]).lower() for i in cursor.description]
        rows = [dict(zip(columns, row)) for row in data]       
        for row in rows:
            table_id = name_to_id.get(str(row.get("table_name")))
            if table_id is not None:
                # exclude "table_name" from the row dict
                row.pop("table_name", None)
                id_to_all.get(table_id)["columns"] = id_to_all.get(table_id).get("columns",[]) + [row]
        return len(data)
    
    def _populate_with_partitions_data(self, table_ids, id_to_all, cursor):
        cursor.execute(PARTITIONS_QUERY.format(table_ids))
        columns = [str(i[0]).lower() for i in cursor.description] 
        rows = [dict(zip(columns, row)) for row in cursor.fetchall()]
        for row in rows:
            id  = row.pop("object_id", None)
            if id is not None:
                #TODO what happens if not found ? 
                id_to_all.get(id)["partitions"] = row
            else:
                print("todo error")
            row.pop("object_id", None)
        print("end")

    def _populate_with_index_data(self, table_ids, id_to_all, cursor):
        cursor.execute(INDEX_QUERY.format(table_ids))
        columns = [str(i[0]).lower() for i in cursor.description] 
        rows = [dict(zip(columns, row)) for row in cursor.fetchall()]
        for row in rows:
            id  = row.pop("object_id", None)
            if id is not None:
                id_to_all.get(id)["indexes"] = row
            else:
                print("todo error")
            row.pop("object_id", None)
        print("end")

    def _populate_with_foreign_keys_data(self, table_ids, id_to_all, cursor):
            cursor.execute(FOREIGN_KEY_QUERY.format(table_ids))
            columns = [str(i[0]).lower() for i in cursor.description] 
            rows = [dict(zip(columns, row)) for row in cursor.fetchall()]
            for row in rows:
                id  = row.pop("object_id", None)
                if id is not None:
                    id_to_all.get(id)["foreign_keys"] = row
                else:
                    print("todo error")  
            print("end")
        #return execute_query_output_result_as_a_dict(COLUMN_QUERY.format(table_name, schema_name), cursor)
    
        
    #TODO in SQLServer partitioned child tables should have the same object_id might be worth checking with a test.

    #TODOTODO do we need this map/list format if we are not dumping in json ??? May be we need to send query results as they are ? 
    def _get_tables(self, schema, cursor):
        cursor.execute(TABLES_IN_SCHEMA_QUERY.format(schema["schema_id"]))
        columns = [str(i[0]).lower() for i in cursor.description]
        rows = [dict(zip(columns, row)) for row in cursor.fetchall()] #TODO may be more optimal to patch columns with index etc 
        # rows = [dict(zip(columns + ["columns", "indexes", "partitions", "foreign_keys"], row + [[], [], [], []])) for row in cursor.fetchall()] #TODO may be this works
        return [ {"object_id" : row["object_id"], "name" : row['name'], "columns" : [], "indexes" : [], "partitions" : [], "foreign_keys" : []} for row in rows ]                  


    #TODO table 1803153469 is in  sys.indexes but not in sys.index_columns ... shell we do something about it ?


    #TODO its hard to get the partition key - for later ? 

        # TODO check out sys.partitions in postgres we deliver some data about patitions
        # "partition_key": str (if has partitions) - equiv ? 
        # may be use this  https://littlekendra.com/2016/03/15/find-the-partitioning-key-on-an-existing-table-with-partition_ordinal/
        # for more in depth search, it's not trivial to determine partition key like in Postgres
       
