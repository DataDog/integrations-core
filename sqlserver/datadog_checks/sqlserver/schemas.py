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

class Schemas:

    def __init__(self, do_for_databases, log):
        self._do_for_databases = do_for_databases 
        self.schemas_per_db = {} 
        self._log = log

    def collect_schemas_data(self):
        #schemas per db
        def fetch_schema_data(cursor, db_name):
            schemas = self._query_schema_information(cursor)
            pdb.set_trace()
            self._get_table_data_per_schema(schemas, cursor)
            pdb.set_trace()
            self.schemas_per_db[db_name] = schemas
        self._do_for_databases(fetch_schema_data)
        pdb.set_trace()
        print(self.schemas_per_db)

#per DB per sqhema per tables. 
    # TODO how often ?
    # TODO put in a class
    #TODOTODO do we need this map/list format if we are not dumping in json ??? May be we need to send query results as they are ? 
    def _query_schema_information(self, cursor):

        # principal_id is kind of like an owner not sure if need it.
        self._log.debug("collecting db schemas")
        self._log.debug("Running query [%s]", SCHEMA_QUERY)
        cursor.execute(SCHEMA_QUERY)
        schemas = []
        columns = [i[0] for i in cursor.description]
        schemas = [dict(zip(columns, row)) for row in cursor.fetchall()]
        for schema in schemas:
            schema["tables"] = {}
        self._log.debug("fetched schemas len(rows)=%s", len(schemas))
        return schemas

    def _get_table_data_per_schema(self, schemas, cursor):
        for schema in schemas:
            self._get_tables_and_their_data(schema, cursor)

    def _get_tables_and_their_data(self, schema, cursor):
        self._get_table_infos(schema, cursor)
        tables_dict_for_schema = schema['tables']
        for table_object_id, table_value in tables_dict_for_schema.items():
            table_value["columns"] = self._get_columns_data_per_table(table_object_id, cursor)
            table_value["partitions"] = self._get_partitions_data_per_table(table_object_id, cursor)
            table_value["indexes"] = self._get_index_data_per_table(table_object_id, cursor)
            table_value["foreign_keys"] = self._get_foreign_key_data_per_table(table_object_id, cursor)

    def _get_table_infos(self, schema, cursor):
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

    def _get_columns_data_per_table(self, table_object_id, cursor):

        #TABLE_SCHEMA, TABLE_NAME, COLUMN_NAME, DATA_TYPE, COLUMN_DEFAULT 
        # in sys.columns I cannot see a data type but there are other things   
        #object_id   name       
        #column_id   system_type_id user_type_id max_length precision scale collation_name   
        # is_nullable is_ansi_padded is_rowguidcol is_identity is_computed is_filestream is_replicated 
        # is_non_sql_subscribed is_merge_published is_dts_replicated is_xml_document xml_collection_id 
        # default_object_id rule_object_id is_sparse is_column_set generated_always_type generated_always_type_desc                                   encryption_type encryption_type_desc                                             encryption_algorithm_name                                                                                                        column_encryption_key_id column_encryption_key_database_name                                                                                              is_hidden is_masked graph_type  graph_type_desc                                              is_data_deletion_filter_column ledger_view_column_type ledger_view_column_type_desc                                 is_dropped_ledger_column
        # might be slower then in sys.columns as we cant get data by object_id .... but we get data_type
        #COLUMN_QUERY = "SELECT COLUMN_NAME, DATA_TYPE, COLUMN_DEFAULT FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA={} and TABLE_NAME={};".format(schema_name, )
        
        #if using query 2 we need to figure out user_type_id - its like a user defined type
        # TODO AL in all query 2 will be query 2 faster ? or its just less convinient at the end ... ? object_id is nice
        return execute_query_output_result_as_a_dict(COLUMN_QUERY.format(table_object_id), cursor)

    
    def _get_partitions_data_per_table(self, table_object_id, cursor):
        # TODO check out sys.partitions in postgres we deliver some data about patitions
        # "partition_key": str (if has partitions) - equiv ? 
        # may be use this  https://littlekendra.com/2016/03/15/find-the-partitioning-key-on-an-existing-table-with-partition_ordinal/
        # for more in depth search, it's not trivial to determine partition key like in Postgres
        
        return execute_query_output_result_as_a_dict(PARTITIONS_QUERY.format(table_object_id), cursor)

    def _get_index_data_per_table(self, table_object_id, cursor):           
        # object_id   name  index_id    type type_desc is_unique data_space_id ignore_dup_key is_primary_key is_unique_constraint 
        # fill_factor is_padded is_disabled is_hypothetical is_ignored_in_optimization allow_row_locks allow_page_locks has_filter 
        # filter_definition            
        #May be better to query sys.index_columns ?                                                                                                                                                                                                                                            compression_delay suppress_dup_key_messages auto_created optimize_for_sequential_key
        #INDEX_QUERY = "SELECT name, type, is_unique, is_primary_key, is_unique_constraint, is_disabled FROM sys.indexes WHERE object_id={}"
        return execute_query_output_result_as_a_dict(INDEX_QUERY.format(table_object_id), cursor)


        
        # foreign keys
        # name object_id principal_id schema_id parent_object_id type type_desc create_date modify_date is_ms_shipped 
        # is_published is_schema_published referenced_object_id key_index_id is_disabled is_not_for_replication 
        # is_not_trusted delete_referential_action delete_referential_action_desc update_referential_action 
        # update_referential_action_desc is_system_named compression_delay suppress_dup_key_messages auto_created optimize_for_sequential_key
        # SELECT name , OBJECT_NAME(parent_object_id) FROM sys.foreign_keys;
        # fk.name AS foreign_key_name, OBJECT_NAME(fk.parent_object_id) AS parent_table, COL_NAME(fkc.parent_object_id, fkc.parent_column_id) AS parent_column, OBJECT_NAME(fk.referenced_object_id) AS referenced_table, COL_NAME(fkc.referenced_object_id, fkc.referenced_column_id) AS referenced_column FROM  sys.foreign_keys fk JOIN  sys.foreign_key_columns fkc ON fk.object_id = fkc.constraint_object_id WHERE  fk.parent_object_id = 'YourTableObjectID' -- Replace 'YourTableObjectID' with the object_id of your table
    def _get_foreign_key_data_per_table(self, table_object_id, cursor):           
        return execute_query_output_result_as_a_dict(FOREIGN_KEY_QUERY.format(table_object_id), cursor)
