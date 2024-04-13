from datadog_checks.sqlserver.const import (
    TABLES_IN_SCHEMA_QUERY,
    COLUMN_QUERY,
    PARTITIONS_QUERY,
    INDEX_QUERY,
    FOREIGN_KEY_QUERY,
    SCHEMA_QUERY,
)

from datadog_checks.sqlserver.utils import (
    execute_query_output_result_as_a_dict,
)

import pdb

class DataForProcessedDB:
    def __init__(self, db_name, schema_list, table_list):
        self._db_name = db_name
        self.schema_list = schema_list
        self.table_list = table_list
        self.current_schema_index = 0
        self.current_table_index = 0
    def stop_processing(self, schema_index, table_index):
        self.current_schema_index = schema_index
        self.current_table_index = table_index


class Schemas:

    def __init__(self, check):
        self._check = check 
        #self._index = [db_index, schema_index, table_index] 
        self.schemas_per_db = {} 
        self._log = check.log
        #TODO is this class unique per host ?
        self._start_time_for_host = []
        #TODO per DB may be ? 
        self._last_time_collected_diff_per_db = {}

        self._index = None
        self._data_for_processed_db = None
        self.databases = []
        self.current_table_list = None
        self.current_schema_list = None
    
    #intially a,b,c DBs new_db_list say c, d,e old_db_list_with_new old list say a, b, c, d, e.
    # new_db_list say d,e
    def _move_index_to_existing_db(self, old_db_list_with_new, new_db_list):
        if self._index is None:
            print("error")
            #self._log.error()
            return
        if len(new_db_list) == 0:
            self._index = None
            return
        start = self._index["db"]
        for i in range(start, len(old_db_list_with_new)):
            if old_db_list_with_new[self._index["db"]] not in new_db_list:
                if i != len(old_db_list_with_new) -1:
                    self._index["db"] = i+1
                    # if we move index at least ones then schema and table are invalidated
                    self._index["schema"] = None
                    self._index["table_object_id_index"] = None
                    self.current_table_list = None
                    self.current_schema_list = None
            else:
                #we are happy with found DB in index
                return
        #if we reached the end of old DBs but there is nothing to take
        self._index = None
        return

            #if we reach the end and index is still None than we take the first from the new list its not important
            # as before we add all new DBs to the old list but like for function consistency

    # outputs db, schema, and table to start with
    # I did this with the idea that trying to connect to a DB that doesnt exist is bad
    # but now I re4alize that switch DB will throw and we are happy... I mean it can happen if the DB is 
    def _init_schema_collection2(self):
        if len(self.databases) == 0:
            self.databases = self._check.get_databases()
            if len(self.databases) == 0:
                self._index = None
                return
            self._index = 0
            return
        else:
            # add new DBs to the end of the list
            updated_databases = self._check.get_databases()
            for new_db in updated_databases:
                if new_db not in self.databases:
                    self.databases.append(new_db)
            # move index if it is currently on a DB that is not in a new list
            self._move_index_to_existing_db(self, self.databases, updated_databases)
            if self._index is None:
                return
            # remove dbs from the list, while updating the index
            current_db_name = self.databases[self._index["db"]]
            new_db_list = []
            for db in self.databases:
                if db in updated_databases:
                    new_db_list.append(db)
            self.databases = new_db_list
            #this shouldnt throw as we ve chosen it to be in the new list.
            self._index["db"] = self.databases.index(current_db_name)
                      
    def _init_schema_collection(self):
        if len(self.databases) == 0:
            self.databases = self._check.get_databases()
            if len(self.databases) == 0:
                self._index = None
                return
            self._index = 0
            return  
        else:
            if self._index is None:
                print("error")  
            #TODO if db dissapeared we invalidate indexes should be done in exception treatment of use DB
            if self.databases[self._index] not in self._check.get_databases():
                    #we dont move the index as on first use db its gonna throw and continue the loop
                    self.current_schema_list = None
                    self.current_table_list = None



                

            

   #TODO update this at the very end as it constantly changing
    """schemas data struct is a dictionnary with key being a schema name the value is
    schema
    dict:
        "name": str
        "schema_id": str
        "principal_id": str
        "tables" : dict
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
    def collect_schemas_data(self):
        #schemas per db
        # flush previous collection
        self.schemas_per_db = {} 
        # init the index
        self._init_schema_collection()
        if self._index is None:
            return
        
        def fetch_schema_data(cursor, db_name):
            schemas = self._query_schema_information(cursor)
            self._get_table_data_per_schema(schemas, cursor)
            self.schemas_per_db[db_name] = schemas
            return False
        
        # dont need an index just always safe the last one.
        def fetch_schema_data2(cursor, db_name):
            # check if we start from scratch or not 
            if self.current_schema_list is None:
                # find new schemas:
                schemas = self._query_schema_information(cursor)
            else:
                schemas = self.current_schema_list  
            #ok we have schemas now tables
            if self.current_table_list is None:
                schemas[0]["tables"] = self._get_tables2(schemas[0], cursor)

            for index_sh, schema in enumerate(schemas):  
                if schema["tables"] is not None:
                    schema["tables"] = self._get_tables2(schema, cursor)
                for index_t,table in enumerate(schema["tables"]):
                    stop = self._get_table_data2(self, table, schema, cursor)
                    if stop:
                        self.current_table_list = schema["tables"][index_t:]
                        self.current_schema_list = schemas[index_sh:]
                        return False
            return True
        self._check._do_for_databases(fetch_schema_data2, self.databases[self.index["db"]:])
        pdb.set_trace()
        print(self.schemas_per_db)
    
    #TODO we need to take care of new DB / removed DB 
    #def get_current_db_times(cursor):
        # list of all known DBs

        #def execute_time_query():
          # self._last_time_collected_diff_per_db =

    def collect_schema_diffs(self):
                #schemas per db
        def fetch_schema_diff_data(cursor, db_name):
            schemas = self._query_schema_information(cursor)
            self._get_table_diff_per_schema(schemas, cursor)
            #self.schemas_per_db[db_name] = schemas[]
        self._do_for_databases(fetch_schema_diff_data)
        pdb.set_trace()
        print(self.schemas_per_db)

#per DB per sqhema per tables. 
    # TODO how often ?
    # TODO put in a class
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

    def _get_table_data_per_schema(self, schemas, cursor):
        for schema in schemas:
            self._get_tables(schema, cursor)
            self._get_table_data(schema, cursor)
    
    #TODO will nedd a separate query for changed indexes
    def _get_table_diff_per_schema(self, schemas, cursor):
        for schema in schemas:
            self._get_changed_tables(schema, cursor)
        for schema in schemas:
            self._get_table_data(schema, cursor)

    # def payload consume , push in data amount 
    def _get_table_data2(self, table, schema, cursor):
        #while processing tables we would like to stop after X amount of data in payload.
        table["columns"] = self._get_columns_data_per_table(table["name"], schema["name"], cursor)
        table["partitions"] = self._get_partitions_data_per_table(table["object_id"], cursor)
        if str(table["object_id"]) == "1803153469":
            pdb.set_trace()
            print("should have index")

        table["indexes"] = self._get_index_data_per_table(table["object_id"], cursor)
        table["foreign_keys"] = self._get_foreign_key_data_per_table(table["object_id"], cursor)
        return False


    # def payload consume , push in data amount 
    def _get_table_data(self, schema, cursor):
        #while processing tables we would like to stop after X amount of data in payload.
        tables_dict_for_schema = schema['tables']
        for table_object_id, table_value in tables_dict_for_schema.items():
            table_value["columns"] = self._get_columns_data_per_table(table_value["name"], schema["name"], cursor)
            table_value["partitions"] = self._get_partitions_data_per_table(table_object_id, cursor)
            if str(table_object_id) == "1803153469":
                pdb.set_trace()
                print("should have index")

            table_value["indexes"] = self._get_index_data_per_table(table_object_id, cursor)
            table_value["foreign_keys"] = self._get_foreign_key_data_per_table(table_object_id, cursor)
        return False
    
    
    def _get_data_for_table(self, schema, table, cursor):
        #while processing tables we would like to stop after X amount of data in payload.
        tables_dict_for_schema = schema['tables']
        for table_object_id, table_value in tables_dict_for_schema.items():
            table_value["columns"] = self._get_columns_data_per_table(table_value["name"], schema["name"], cursor)
            table_value["partitions"] = self._get_partitions_data_per_table(table_object_id, cursor)
            if str(table_object_id) == "1803153469":
                pdb.set_trace()
                print("should have index")

            table_value["indexes"] = self._get_index_data_per_table(table_object_id, cursor)
            table_value["foreign_keys"] = self._get_foreign_key_data_per_table(table_object_id, cursor)
        return False
    
    #TODO in SQLServer partitioned child tables should have the same object_id might be worth checking with a test.
    def _get_tables_and_their_data(self, schema, cursor):        
        self._get_tables(schema, cursor)
        tables_dict_for_schema = schema['tables']
        for table_object_id, table_value in tables_dict_for_schema.items():
            table_value["columns"] = self._get_columns_data_per_table(table_value["name"], schema["name"], cursor)
            table_value["partitions"] = self._get_partitions_data_per_table(table_object_id, cursor)
            if str(table_object_id) == "1803153469":
                pdb.set_trace()
                print("should have index")

            table_value["indexes"] = self._get_index_data_per_table(table_object_id, cursor)
            table_value["foreign_keys"] = self._get_foreign_key_data_per_table(table_object_id, cursor)

    # TODO how often ?
    # TODO put in a class
    #TODOTODO do we need this map/list format if we are not dumping in json ??? May be we need to send query results as they are ? 
    def _get_tables2(self, schema, cursor):

        cursor.execute(TABLES_IN_SCHEMA_QUERY.format(schema["schema_id"]))
        columns = [str(i[0]).lower() for i in cursor.description]
        rows = [dict(zip(columns, row)) for row in cursor.fetchall()] #TODO may be more optimal to patch columns with index etc 
        # rows = [dict(zip(columns + ["columns", "indexes", "partitions", "foreign_keys"], row + [[], [], [], []])) for row in cursor.fetchall()] #TODO may be this works
        return [ {"object_id" : row["object_id"], "name" : row['name'], "columns" : [], "indexes" : [], "partitions" : [], "foreign_keys" : []} for row in rows ]                  

    # TODO how often ?
    # TODO put in a class
    #TODOTODO do we need this map/list format if we are not dumping in json ??? May be we need to send query results as they are ? 
    def _get_tables(self, schema, cursor):
        tables_dict_for_schema = schema['tables']
            
        # TODO modify_date - there is a modify date !!! 
        # TODO what is principal_id
        # TODO is_replicated - might be interesting ? 
        
        cursor.execute(TABLES_IN_SCHEMA_QUERY.format(schema["schema_id"]))
        columns = [str(i[0]).lower() for i in cursor.description]
        rows = [dict(zip(columns, row)) for row in cursor.fetchall()]
        for row in rows:            
            tables_dict_for_schema[row['object_id']] = {"name" : row['name'], "columns" : [], "indexes" : [], "partitions" : [], "foreign_keys" : []}
        return

    def _get_columns_data_per_table(self, table_name, schema_name, cursor):
        return execute_query_output_result_as_a_dict(COLUMN_QUERY.format(table_name, schema_name), cursor)

    #TODO table 1803153469 is in  sys.indexes but not in sys.index_columns ... shell we do something about it ?
    def _get_index_data_per_table(self, table_object_id, cursor):           
        return execute_query_output_result_as_a_dict(INDEX_QUERY.format(table_object_id), cursor)

    #TODO its hard to get the partition key - for later ? 
    def _get_partitions_data_per_table(self, table_object_id, cursor):
        # TODO check out sys.partitions in postgres we deliver some data about patitions
        # "partition_key": str (if has partitions) - equiv ? 
        # may be use this  https://littlekendra.com/2016/03/15/find-the-partitioning-key-on-an-existing-table-with-partition_ordinal/
        # for more in depth search, it's not trivial to determine partition key like in Postgres
        return execute_query_output_result_as_a_dict(PARTITIONS_QUERY.format(table_object_id), cursor, "partition_count")

    def _get_foreign_key_data_per_table(self, table_object_id, cursor):  
        return execute_query_output_result_as_a_dict(FOREIGN_KEY_QUERY.format(table_object_id), cursor, "foreign_key_count")         
