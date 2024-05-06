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
    #TODO Report truncation to the backend
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
            schemas[schema["id"]] = copy.deepcopy(schema) # TODO a deep copy ? kind of costs not much to be safe
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
                #TODO log error
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
        self._tags = [t for t in check.tags if not t.startswith('dd.internal')]
        self._tags.append("boris:data")
        self.schemas_per_db = {} 

        base_event = {
            "host": None,
            "agent_version": datadog_agent.get_version(),
            "dbms": "sqlserver",
            "kind": "sqlserver_databases",
            "collection_interval": schemas_collection_interval,
            "dbms_version": None,
            "tags": self._tags, #in postgres it's no DB ?
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
        self._dataSubmitter.set_base_event_data(self._check.resolved_hostname, self._tags, self._check._config.cloud_metadata, 
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
            return None
    # TODO how often ?

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
        self._log.debug("Running query [%s]", SCHEMA_QUERY)
        cursor.execute(SCHEMA_QUERY)
        schemas = []
        columns = [i[0] for i in cursor.description]
        schemas = [dict(zip(columns, [str(item) for item in row])) for row in cursor.fetchall()]
        self._log.debug("fetched schemas len(rows)=%s", len(schemas))
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

    # TODO refactor the next 3 to have a base function when everythng is settled.
    def _populate_with_columns_data(self, table_ids, name_to_id, id_to_all, schema, cursor):
        # get columns if we dont have a dict here unlike postgres
        cursor.execute(COLUMN_QUERY.format(table_ids, schema["name"]))
        data = cursor.fetchall()
        columns = []
        #TODO we need it cause if I put AS default its a forbidden key word and to be inline with postgres we need it
        for i in cursor.description:
            if str(i[0]).lower() == "column_default":
                columns.append("default")
            else:
                columns.append(str(i[0]).lower())
        

        rows = [dict(zip(columns, [str(item) for item in row])) for row in data]       
        for row in rows:
            table_id = name_to_id.get(str(row.get("table_name")))
            if table_id is not None:
                # exclude "table_name" from the row dict
                row.pop("table_name", None)
                if "nullable" in row:
                    if row["nullable"].lower() == "no" or row["nullable"].lower() == "false":
                        #to make compatible with postgres 
                        row["nullable"] = False
                    else:
                        row["nullable"] = True
                id_to_all.get(table_id)["columns"] = id_to_all.get(table_id).get("columns",[]) + [row]
        return len(data)
    
    def _populate_with_partitions_data(self, table_ids, id_to_all, cursor):
        cursor.execute(PARTITIONS_QUERY.format(table_ids))
        columns = [str(i[0]).lower() for i in cursor.description] 
        rows = [dict(zip(columns, row)) for row in cursor.fetchall()]
        for row in rows:
            id  = row.pop("id", None)
            if id is not None:
                #TODO what happens if not found ? 
                id_to_all.get(str(id))["partitions"] = row
            else:
                print("todo error")
            row.pop("id", None)
        print("end")

    def _populate_with_index_data(self, table_ids, id_to_all, cursor):
        cursor.execute(INDEX_QUERY.format(table_ids))
        columns = [str(i[0]).lower() for i in cursor.description] 
        rows = [dict(zip(columns, row)) for row in cursor.fetchall()]
        for row in rows:
            id  = row.pop("id", None)
            if id is not None:
                id_to_all.get(str(id))["indexes"] = row
            else:
                print("todo error")
            row.pop("id", None)
        print("end")

    def _populate_with_foreign_keys_data(self, table_ids, id_to_all, cursor):
            cursor.execute(FOREIGN_KEY_QUERY.format(table_ids))
            columns = [str(i[0]).lower() for i in cursor.description] 
            rows = [dict(zip(columns, row)) for row in cursor.fetchall()]
            for row in rows:
                id  = row.pop("id", None)
                if id is not None:
                    id_to_all.get(str(id))["foreign_keys"] = row
                else:
                    print("todo error")  
            print("end")
        #return execute_query_output_result_as_a_dict(COLUMN_QUERY.format(table_name, schema_name), cursor)

    def _get_tables(self, schema, cursor):
        cursor.execute(TABLES_IN_SCHEMA_QUERY.format(schema["id"]))
        columns = [str(i[0]).lower() for i in cursor.description]
        rows = [dict(zip(columns, row)) for row in cursor.fetchall()]
        return [ {"id" : str(row["id"]), "name" : row['name'], "columns" : []} for row in rows ] 

    #TODO its hard to get the partition key - for later ? 

        # TODO check out sys.partitions in postgres we deliver some data about patitions
        # "partition_key": str (if has partitions) - equiv ? 
        # may be use this  https://littlekendra.com/2016/03/15/find-the-partitioning-key-on-an-existing-table-with-partition_ordinal/
        # for more in depth search, it's not trivial to determine partition key like in Postgres
       
