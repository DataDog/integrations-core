try:
    import datadog_agent
except ImportError:
    from ..stubs import datadog_agent

import copy
import json
import time

from datadog_checks.base import is_affirmative
from datadog_checks.base.utils.db.utils import (
    default_json_event_encoding,
    DBMAsyncJob
)

from datadog_checks.base.utils.tracking import tracked_method
from datadog_checks.sqlserver.const import (
    COLUMN_QUERY,
    DB_QUERY,
    FOREIGN_KEY_QUERY,
    INDEX_QUERY,
    PARTITIONS_QUERY,
    SCHEMA_QUERY,
    STATIC_INFO_ENGINE_EDITION,
    STATIC_INFO_VERSION,
    TABLES_IN_SCHEMA_QUERY,
    DEFAULT_SCHEMAS_COLLECTION_INTERVAL
)
from datadog_checks.sqlserver.utils import execute_query_output_result_as_dicts, get_list_chunks

class SubmitData:

    def __init__(self, submit_data_function, base_event, logger):
        self._submit_to_agent_queue = submit_data_function
        self._base_event = base_event
        self._log = logger

        self._columns_count = 0
        self.db_to_schemas = {}  # dbname : { id : schema }
        self.db_info = {}  # name to info

    def set_base_event_data(self, hostname, tags, cloud_metadata, dbms_version):
        self._base_event["host"] = hostname
        self._base_event["tags"] = tags
        self._base_event["cloud_metadata"] = cloud_metadata
        self._base_event["dbms_version"] = dbms_version

    def reset(self):
        self._columns_count = 0
        self.db_to_schemas = {}
        self.db_info = {}

    def store_db_infos(self, db_infos):
        for db_info in db_infos:
            self.db_info[db_info['name']] = db_info

    def store(self, db_name, schema, tables, columns_count):
        self._columns_count += columns_count
        schemas = self.db_to_schemas.setdefault(db_name, {})
        if schema["id"] in schemas:
            known_tables = schemas[schema["id"]].setdefault("tables", [])
            known_tables = known_tables + tables
        else:
            schemas[schema["id"]] = copy.deepcopy(schema)
            schemas[schema["id"]]["tables"] = tables

    def columns_since_last_submit(self):
        return self._columns_count
    
    def truncate(self, json_event):
        max_length = 1000
        if len(json_event) > max_length:
            return json_event[:max_length] + " ... (truncated)"
        else:
            return json_event

    #NOTE: DB with no schemas is never submitted
    def submit(self):
        if not self.db_to_schemas:
            return
        self._columns_count = 0
        event = {**self._base_event, "metadata": [], "timestamp": time.time() * 1000}
        for db, schemas_by_id in self.db_to_schemas.items():
            db_info = {}
            if db not in self.db_info:
                self._log.error("Couldn't find database info for %s", db)
                db_info["name"] = db
            else:
                db_info = self.db_info[db]
            event["metadata"] = event["metadata"] + [{**(db_info), "schemas": list(schemas_by_id.values())}]
        json_event = json.dumps(event, default=default_json_event_encoding)
        self._log.debug("Reporting the following payload for schema collection: {}".format(self.truncate(json_event)))
        self._submit_to_agent_queue(json_event)
        self.db_to_schemas = {}


def agent_check_getter(self):
    return self._check


class Schemas(DBMAsyncJob):

    # Requests for infromation about tables are done for a certain amount of tables at the time
    # This number of tables doesnt slow down performance by much (15% compared to 500 tables)
    # but allows the queue to be stable.
    TABLES_CHUNK_SIZE = 500
    # Note: in async mode execution time also cannot exceed 2 checks.
    MAX_EXECUTION_TIME = 10
    MAX_COLUMNS_PER_EVENT = 100_000

    def __init__(self, check, config):
        self._check = check
        self._log = check.log
        self.schemas_per_db = {}
        self._last_schemas_collect_time = None
        collection_interval = config.schema_config.get(
            'collection_interval', DEFAULT_SCHEMAS_COLLECTION_INTERVAL
        )
        self._max_execution_time = min(config.schema_config.get('max_execution_time', self.MAX_EXECUTION_TIME), collection_interval)
        super(Schemas, self).__init__(
            check,
            run_sync=is_affirmative(config.schema_config.get('run_sync', True)),
            enabled=is_affirmative(config.schema_config.get('enabled', False)),
            expected_db_exceptions=(),
            # min collection interval is a desired collection interval for a check as a whole.
            min_collection_interval=config.min_collection_interval,
            dbms="sqlserver",
            rate_limit=1 / float(collection_interval),
            job_name="query-schemas",
            shutdown_callback=self.shut_down,
        )
        base_event = {
            "host": None,
            "agent_version": datadog_agent.get_version(),
            "dbms": "sqlserver",
            "kind": "sqlserver_databases",
            "collection_interval":  collection_interval,
            "dbms_version": None,
            "tags": self._check.non_internal_tags,
            "cloud_metadata": self._check._config.cloud_metadata,
        }
        self._data_submitter = SubmitData(self._check.database_monitoring_metadata, base_event, self._log)

    def run_job(self):
        self._collect_schemas_data()

    def shut_down(self):
        self._data_submitter.submit()

    @tracked_method(agent_check_getter=agent_check_getter)
    def _collect_schemas_data(self):
        """Collects database information and schemas and submits to the agent's queue as dictionaries
        schema dict
        key/value:
            "name": str
            "id": str
            "owner_name": str
            "tables" : list of tables dicts
                table
                key/value:
                    "id" : str
                    "name" : str
                    columns: list of columns dicts
                        columns
                        key/value:
                            "name": str
                            "data_type": str
                            "default": str
                            "nullable": bool
                indexes : list of index dicts
                    index
                    key/value:
                        "name": str
                        "type": str
                        "is_unique": bool
                        "is_primary_key": bool
                        "is_unique_constraint": bool
                        "is_disabled": bool,
                        "column_names": str
                foreign_keys : list of foreign key dicts
                    foreign_key
                    key/value:
                        "foreign_key_name": str
                        "referencing_table": str
                        "referencing_column": str
                        "referenced_table": str
                        "referenced_column": str
                partitions: partition dict
                    partition
                    key/value:
                        "partition_count": int
        """
        start_time = time.thread_time()
        self._data_submitter.reset()
        self._data_submitter.set_base_event_data(
            self._check.resolved_hostname,
            self._check.non_internal_tags,
            self._check._config.cloud_metadata,
            "{},{}".format(
                self._check.static_info_cache.get(STATIC_INFO_VERSION, ""),
                self._check.static_info_cache.get(STATIC_INFO_ENGINE_EDITION, ""),
            ),
        )

        databases = self._check.get_databases()
        db_infos = self._query_db_informations(databases)
        self._data_submitter.store_db_infos(db_infos)

        @tracked_method(agent_check_getter=agent_check_getter)
        def fetch_schema_data(cursor, db_name):
            schemas = self._query_schema_information(cursor)
            for schema in schemas:
                tables = self._get_tables(schema, cursor)
                tables_chunks = list(get_list_chunks(tables, self.TABLES_CHUNK_SIZE))
                for tables_chunk in tables_chunks:
                    if time.thread_time() -  start_time > self.MAX_EXECUTION_TIME:
                        # TODO Report truncation to the backend
                        self._log.warning(
                            "Truncated data due to the effective execution time reaching {}, stopped on db - {} on schema {}".format(
                                self.MAX_EXECUTION_TIME, db_name, schema["name"]
                            )
                        )
                        raise StopIteration

                    columns_count, tables_info = self._get_tables_data(tables_chunk, schema, cursor)

                    self._data_submitter.store(db_name, schema, tables_info, columns_count)
                    if self._data_submitter.columns_since_last_submit() > self.MAX_COLUMNS_PER_EVENT:
                        self._data_submitter.submit()
            self._data_submitter.submit()
            return False

        errors = self._check.do_for_databases(fetch_schema_data, self._check.get_databases())
        if errors:
            for e in errors:
                self._log.error("While executing fetch schemas for databse - %s, the following exception occured - %s", e[0], e[1])
        self._log.debug("Finished collect_schemas_data")
        self._data_submitter.submit()

    def _query_db_informations(self, db_names):
        with self._check.connection.open_managed_default_connection():
            with self._check.connection.get_managed_cursor() as cursor:
                db_names_formatted = ",".join(["'{}'".format(t) for t in db_names])
                return execute_query_output_result_as_dicts(DB_QUERY.format(db_names_formatted), cursor, convert_results_to_str=True)



    @tracked_method(agent_check_getter=agent_check_getter, track_result_length=True)
    def _get_tables(self, schema, cursor):
        """ returns a list of tables for schema with their names and empty column array
        list of table dicts
        "id": str
        "name": str
        "columns": []
        """
        tables_info = execute_query_output_result_as_dicts(
            TABLES_IN_SCHEMA_QUERY, cursor, convert_results_to_str=True, parameter=schema["id"]
        )
        for t in tables_info:
            t.setdefault("columns", [])
        return tables_info

    @tracked_method(agent_check_getter=agent_check_getter, track_result_length=True)
    def _query_schema_information(self, cursor):
        """ returns a list of schema dicts
            schema
            dict:
                "name": str
                "id": str
                "owner_name": str
        """
        return execute_query_output_result_as_dicts(SCHEMA_QUERY, cursor, convert_results_to_str=True)

    @tracked_method(agent_check_getter=agent_check_getter, track_result_length=True)
    def _get_tables_data(self, table_list, schema, cursor):
        """ returns extracted column numbers and a list of tables
            "tables" : list of tables dicts
            table
            key/value:
                "id" : str
                "name" : str
                columns: list of columns dicts
                    columns
                    key/value:
                        "name": str
                        "data_type": str
                        "default": str
                        "nullable": bool
                indexes : list of index dicts
                    index
                    key/value:
                        "name": str
                        "type": str
                        "is_unique": bool
                        "is_primary_key": bool
                        "is_unique_constraint": bool
                        "is_disabled": bool,
                        "column_names": str
                foreign_keys : list of foreign key dicts
                    foreign_key
                    key/value:
                        "foreign_key_name": str
                        "referencing_table": str
                        "referencing_column": str
                        "referenced_table": str
                        "referenced_column": str
                partitions: partition dict
                    partition
                    key/value:
                        "partition_count": int
        """
        if len(table_list) == 0:
            return
        name_to_id = {}
        id_to_table_data = {}
        table_ids_object = ",".join(["OBJECT_NAME({})".format(t.get("id")) for t in table_list])
        table_ids = ",".join(["{}".format(t.get("id")) for t in table_list])
        for t in table_list:
            name_to_id[t["name"]] = t["id"]
            id_to_table_data[t["id"]] = t
        total_columns_number = self._populate_with_columns_data(
            table_ids_object, name_to_id, id_to_table_data, schema, cursor
        )
        self._populate_with_partitions_data(table_ids, id_to_table_data, cursor)
        self._populate_with_foreign_keys_data(table_ids, id_to_table_data, cursor)
        self._populate_with_index_data(table_ids, id_to_table_data, cursor)
        return total_columns_number, list(id_to_table_data.values())

    @tracked_method(agent_check_getter=agent_check_getter)
    def _populate_with_columns_data(self, table_ids, name_to_id, id_to_table_data, schema, cursor):
        cursor.execute(COLUMN_QUERY.format(table_ids, schema["name"]))
        data = cursor.fetchall()
        # AS default - cannot be used in sqlserver query as this word is reserved
        columns = [
            "default" if str(i[0]).lower() == "column_default" else str(i[0]).lower() for i in cursor.description
        ]
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
                    id_to_table_data.get(table_id)["columns"] = id_to_table_data.get(table_id).get("columns", []) + [
                        row
                    ]
                else:
                    self._log.error("Columns found for an unkown table with the object_id: %s", table_id)
            else:
                self._log.error("Couldn't find id of a table: %s", table_id)
        return len(data)

    @tracked_method(agent_check_getter=agent_check_getter)
    def _populate_with_partitions_data(self, table_ids, id_to_table_data, cursor):
        rows = execute_query_output_result_as_dicts(PARTITIONS_QUERY.format(table_ids), cursor)
        for row in rows:
            id = row.pop("id", None)
            if id is not None:
                id_str = str(id)
                if id_str in id_to_table_data:
                    id_to_table_data[id_str]["partitions"] = row
                else:
                    self._log.error("Partition found for an unkown table with the object_id: %s", id_str)
            else:
                self._log.error("Return rows of [%s] query should have id column", PARTITIONS_QUERY)

    @tracked_method(agent_check_getter=agent_check_getter)
    def _populate_with_index_data(self, table_ids, id_to_table_data, cursor):
        rows = execute_query_output_result_as_dicts(INDEX_QUERY.format(table_ids), cursor)
        for row in rows:
            id = row.pop("id", None)
            if id is not None:
                id_str = str(id)
                if id_str in id_to_table_data:
                    id_to_table_data[id_str].setdefault("indexes", [])
                    id_to_table_data[id_str]["indexes"].append(row)
                else:
                    self._log.error("Index found for an unkown table with the object_id: %s", id_str)
            else:
                self._log.error("Return rows of [%s] query should have id column", INDEX_QUERY)

    @tracked_method(agent_check_getter=agent_check_getter, track_result_length=True)
    def _populate_with_foreign_keys_data(self, table_ids, id_to_table_data, cursor):
        rows = execute_query_output_result_as_dicts(FOREIGN_KEY_QUERY.format(table_ids), cursor)
        for row in rows:
            id = row.pop("id", None)
            if id is not None:
                id_str = str(id)
                if id_str in id_to_table_data:
                    id_to_table_data.get(str(id)).setdefault("foreign_keys", [])
                    id_to_table_data.get(str(id))["foreign_keys"].append(row)
                else:
                    self._log.error("Foreign key found for an unkown table with the object_id: %s", id_str)
            else:
                self._log.error("Return rows of [%s] query should have id column", FOREIGN_KEY_QUERY)
