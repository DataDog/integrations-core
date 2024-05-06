try:
    import datadog_agent
except ImportError:
    from ..stubs import datadog_agent
import time

from datadog_checks.sqlserver.const import (
    TABLES_IN_SCHEMA_QUERY,
    COLUMN_QUERY,
    PARTITIONS_QUERY,
    INDEX_QUERY,
    FOREIGN_KEY_QUERY,
    SCHEMA_QUERY,
    DB_QUERY,
    STATIC_INFO_VERSION,
    STATIC_INFO_ENGINE_EDITION
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
    MAX_COLUMN_COUNT  = 10_000

    # REDAPL has a 3MB limit per resource
    MAX_TOTAL_COLUMN_COUNT = 100_000 

    def __init__(self, submit_data_function, base_event, logger):
        self._submit_to_agent_queue = submit_data_function
        self._base_event = base_event
        self._log = logger

        self._columns_count  = 0
        self._total_columns_count = 0
        self.db_to_schemas = {} # dbname : { id : schema }
        self.db_info = {} # name to info

    def set_base_event_data(self, hostname, tags, cloud_metadata, dbms_version):
        self._base_event["host"] = hostname
        self._base_event["tags"] = tags
        self._base_event["cloud_metadata"] = cloud_metadata
        self._base_event["dbms_version"] = dbms_version        

    def reset(self):
        self._columns_count = 0
        self._total_columns_count = 0
        self.db_to_schemas = {}
        self.db_info = {}
    
    def store_db_info(self, db_name, db_info):
        self.db_info[db_name] = db_info

    def store(self, db_name, schema, tables, columns_count):
        self._columns_count += columns_count
        self._total_columns_count += columns_count
        schemas = self.db_to_schemas.setdefault(db_name, {})
        if schema["id"] in schemas:
            known_tables = schemas[schema["id"]].setdefault("tables",[])
            known_tables = known_tables + tables
        else:
            schemas[schema["id"]] = copy.deepcopy(schema)
            schemas[schema["id"]]["tables"] = tables
        if self._columns_count > self.MAX_COLUMN_COUNT:
            self._submit()

    def exceeded_total_columns_number(self):
        return self._total_columns_count > self.MAX_TOTAL_COLUMN_COUNT

    def submit(self):
        if not bool(self.db_to_schemas):
            return
        self._columns_count  = 0
        event = {**self._base_event,
                 "metadata" : [],
                 "timestamp": time.time() * 1000
                 }
        for db, schemas_by_id in self.db_to_schemas.items():
            db_info = {}
            if db not in self.db_info:
                self._log.error("Couldn't find database info for %s", db)
                db_info["name"] = db
            else:
                db_info = self.db_info[db]
            event["metadata"] =  event["metadata"] + [{**(db_info), "schemas": list(schemas_by_id.values())}]
        json_event = json.dumps(event, default=default_json_event_encoding)
        self._log.debug("Reporting the following payload for schema collection: {}".format(json_event))
        self._submit_to_agent_queue(json_event)
        self.db_to_schemas = {}

class Schemas:

    # Requests for infromation about tables are done for a certain amount of tables at the time
    # This number of tables doesnt slow down performance by much (15% compared to 500 tables)
    # but allows the queue to be stable.
    TABLES_CHUNK_SIZE = 50

    def __init__(self, check, schemas_collection_interval):
        self._check = check 
        self._log = check.log
        self.schemas_per_db = {} 

        base_event = {
            "host": None,
            "agent_version": datadog_agent.get_version(),
            "dbms": "sqlserver",
            "kind": "sqlserver_databases",
            "collection_interval": schemas_collection_interval,
            "dbms_version": None,
            "tags": self._check.non_internal_tags,
            "cloud_metadata": self._check._config.cloud_metadata,
        }
        self._dataSubmitter = SubmitData(self._check.database_monitoring_metadata, base_event, self._log)

    """schemas data struct is a dictionnary with key being a schema name the value is
    schema
    dict:
        "name": str
        "id": str
        "owner_name": str
        "tables" : list of tables dicts
            table 
            dict:
                "id" : str
                "name" : str
                columns: list of columns dicts                 
                    columns 
                    dict:
                        "name": str
                        "data_type": str
                        "default": str
                        "nullable": bool
            indexes : list of index dicts
                index
                dict:
                    "name": str
                    "type": str
                    "is_unique": bool
                    "is_primary_key": bool
                    "is_unique_constraint": bool
                    "is_disabled": bool,
                    "column_names": str
            foreign_keys : list of foreign key dicts
                foreign_key
                dict:
                    "foreign_key_name": str
                    "referencing_table": str
                    "referencing_column": str
                    "referenced_table": str
                    "referenced_column": str
            partitions: list of partitions dict
                partition
                dict:
                    "partition_count": int
            partitions useful to know the number 
    """
    def collect_schemas_data(self):
        self._dataSubmitter.reset()
        self._dataSubmitter.set_base_event_data(self._check.resolved_hostname, self._check.non_internal_tags, self._check._config.cloud_metadata, 
                                                "{},{}".format(
                                                self._check.static_info_cache.get(STATIC_INFO_VERSION, ""),
                                                self._check.static_info_cache.get(STATIC_INFO_ENGINE_EDITION, ""),)
        )
        #returns if to stop, True means stop iterating.
        def fetch_schema_data(cursor, db_name):
            db_info  = self._query_db_information(db_name, cursor)
            schemas = self._query_schema_information(cursor)
            self._dataSubmitter.store_db_info(db_name, db_info)
            for schema in schemas:
                tables = self._get_tables(schema, cursor)         
                tables_chunk = list(get_list_chunks(tables, self.TABLES_CHUNK_SIZE))
                for tables_chunk in tables_chunk:
                    if self._dataSubmitter.exceeded_total_columns_number():
                        #TODO Report truncation to the backend
                        self._log.warning("Truncated data due to the max limit, stopped on db - {} on schema {}".format(db_name, schema["name"]))
                        return True                    
                    columns_count, tables_info = self._get_tables_data(tables_chunk, schema, cursor)
                    self._dataSubmitter.store(db_name, schema, tables_info, columns_count)  
                    self._dataSubmitter.submit() # Submit is forced after each 50 tables chunk
                if len(tables) == 0:
                    self._dataSubmitter.store(db_name, schema, [], 0)
            self._dataSubmitter.submit()
            return False
        self._check.do_for_databases(fetch_schema_data, self._check.get_databases())
        self._log.debug("Finished collect_schemas_data")
        self._dataSubmitter.submit()

    def _query_db_information(self, db_name, cursor):
        db_info = execute_query_output_result_as_a_dict(DB_QUERY.format(db_name), cursor)
        if len(db_info) == 1:
            return db_info[0]
        else:
            self._log.error("Couldnt query database information for %s", db_name)
            return None        

    """ returns a list of tables for schema with their names and empty column array
    list of table dicts
    "id": str
    "name": str
    "columns": [] 
    """
    def _get_tables(self, schema, cursor):
        cursor.execute(TABLES_IN_SCHEMA_QUERY.format(schema["id"]))
        columns = [str(i[0]).lower() for i in cursor.description]
        rows = [dict(zip(columns, row)) for row in cursor.fetchall()]
        return [ {"id" : str(row["id"]), "name" : row['name'], "columns" : []} for row in rows ] 

    """schemas data struct is a dictionnary with key being a schema name the value is
    schema
    dict:
        "name": str
        "id": str
        "owner_name": str
        "tables" : list of tables dicts
            table 
            dict:
                "id" : str
                "name" : str
                columns: list of columns dicts                 
                    columns 
                    dict:
                        "name": str
                        "data_type": str
                        "default": str
                        "nullable": bool
            indexes : list of index dicts
                index
                dict:
                    "name": str
                    "type": str
                    "is_unique": bool
                    "is_primary_key": bool
                    "is_unique_constraint": bool
                    "is_disabled": bool,
                    "column_names": str
            foreign_keys : list of foreign key dicts
                foreign_key
                dict:
                    "foreign_key_name": str
                    "referencing_table": str
                    "referencing_column": str
                    "referenced_table": str
                    "referenced_column": str
            partitions: list of partitions dict
                partition
                dict:
                    "partition_count": int
            partitions useful to know the number 
    """    
    """fetches schemas dict 
    schema
    dict:
        "name": str
        "id": str
        "owner_name": str"""
    def _query_schema_information(self, cursor):
        cursor.execute(SCHEMA_QUERY)
        schemas = []
        columns = [i[0] for i in cursor.description]
        schemas = [dict(zip(columns, [str(item) for item in row])) for row in cursor.fetchall()]
        return schemas
    
    """ returns extracted column numbers and a list of tables
        "tables" : list of tables dicts
        table 
        dict:
            "id" : str
            "name" : str
            columns: list of columns dicts                 
                columns 
                dict:
                    "name": str
                    "data_type": str
                    "default": str
                    "nullable": bool
            indexes : list of index dicts
                index
                dict:
                    "name": str
                    "type": str
                    "is_unique": bool
                    "is_primary_key": bool
                    "is_unique_constraint": bool
                    "is_disabled": bool,
                    "column_names": str
            foreign_keys : list of foreign key dicts
                foreign_key
                dict:
                    "foreign_key_name": str
                    "referencing_table": str
                    "referencing_column": str
                    "referenced_table": str
                    "referenced_column": str
            partitions: list of partitions dict
                partition
                dict:
                    "partition_count": int
    """
    def _get_tables_data(self, table_list, schema, cursor):
        if len(table_list) == 0:
            return
        name_to_id = {}
        id_to_table_data = {}
        table_ids_object = ",".join(["OBJECT_NAME({})".format(t.get("id")) for t in table_list])
        table_ids = ",".join(["{}".format(t.get("id")) for t in table_list])
        for t in table_list:
            name_to_id[t["name"]] = t["id"] 
            id_to_table_data[t["id"]] = t
        total_columns_number  = self._populate_with_columns_data(table_ids_object, name_to_id, id_to_table_data, schema, cursor)
        self._populate_with_partitions_data(table_ids, id_to_table_data, cursor)
        self._populate_with_foreign_keys_data(table_ids, id_to_table_data, cursor)
        self._populate_with_index_data(table_ids, id_to_table_data, cursor)
        return total_columns_number, list(id_to_table_data.values())

    """ 
    adds columns list data to each table in a provided list
    """
    def _populate_with_columns_data(self, table_ids, name_to_id, id_to_table_data, schema, cursor):
        cursor.execute(COLUMN_QUERY.format(table_ids, schema["name"]))
        data = cursor.fetchall()
        columns = []
        # AS default - cannot be used in sqlserver query as this word is reserved
        columns = ["default" if str(i[0]).lower() == "column_default" else str(i[0]).lower() for i in cursor.description]
        rows = [dict(zip(columns, [str(item) for item in row])) for row in data]       
        for row in rows:
            table_id = name_to_id.get(str(row.get("table_name")))
            if table_id is not None:
                row.pop("table_name", None)
                if "nullable" in row:
                    if row["nullable"].lower() == "no" or row["nullable"].lower() == "false":
                        row["nullable"] = False
                    else:
                        row["nullable"] = True
                if table_id in id_to_table_data:        
                    id_to_table_data.get(table_id)["columns"] = id_to_table_data.get(table_id).get("columns",[]) + [row]
                else:
                    self._log.error("Columns found for an unkown table with the object_id: %s", table_id)
            else:
                self._log.error("Couldn't find id of a table: %s", table_id)
        return len(data)
    
    """ 
    adds partitions dict to each table in a provided list
    """
    def _populate_with_partitions_data(self, table_ids, id_to_table_data, cursor):
        cursor.execute(PARTITIONS_QUERY.format(table_ids))
        columns = [str(i[0]).lower() for i in cursor.description] 
        rows = [dict(zip(columns, row)) for row in cursor.fetchall()]
        for row in rows:
            id  = row.pop("id", None)
            if id is not None: 
                id_str = str(id)
                if id_str in id_to_table_data:
                    id_to_table_data[id_str]["partitions"] = row
                else:
                    self._log.error("Partition found for an unkown table with the object_id: %s", id_str)
            else:
                self._log.error("Return rows of [%s] query should have id column", PARTITIONS_QUERY)

    def _populate_with_index_data(self, table_ids, id_to_table_data, cursor):
        cursor.execute(INDEX_QUERY.format(table_ids))
        columns = [str(i[0]).lower() for i in cursor.description] 
        rows = [dict(zip(columns, row)) for row in cursor.fetchall()]
        for row in rows:
            id  = row.pop("id", None)
            if id is not None:
                id_str = str(id)
                if id_str in id_to_table_data:
                    id_to_table_data[id_str].setdefault("indexes", [])
                    id_to_table_data[id_str]["indexes"].append(row)
                else:
                    self._log.error("Index found for an unkown table with the object_id: %s", id_str)
            else:
                self._log.error("Return rows of [%s] query should have id column", INDEX_QUERY)

    def _populate_with_foreign_keys_data(self, table_ids, id_to_table_data, cursor):
            cursor.execute(FOREIGN_KEY_QUERY.format(table_ids))
            columns = [str(i[0]).lower() for i in cursor.description] 
            rows = [dict(zip(columns, row)) for row in cursor.fetchall()]
            for row in rows:
                id  = row.pop("id", None)
                if id is not None:
                    id_str = str(id)
                    if id_str in id_to_table_data:
                        id_to_table_data.get(str(id)).setdefault("foreign_keys", [])
                        id_to_table_data.get(str(id))["foreign_keys"].append(row)
                    else:
                        self._log.error("Foreign key found for an unkown table with the object_id: %s", id_str)
                else:
                    self._log.error("Return rows of [%s] query should have id column", FOREIGN_KEY_QUERY)  
       
