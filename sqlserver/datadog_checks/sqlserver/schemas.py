# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

try:
    import datadog_agent
except ImportError:
    from ..stubs import datadog_agent

import json
import time

from datadog_checks.base import is_affirmative
from datadog_checks.base.utils.db.utils import DBMAsyncJob, default_json_event_encoding
from datadog_checks.base.utils.tracking import tracked_method
from datadog_checks.sqlserver.const import (
    DEFAULT_SCHEMAS_COLLECTION_INTERVAL,
    STATIC_INFO_ENGINE_EDITION,
    STATIC_INFO_MAJOR_VERSION,
    STATIC_INFO_VERSION,
    SWITCH_DB_STATEMENT,
)
from datadog_checks.sqlserver.queries import (
    COLUMN_QUERY,
    DB_QUERY,
    FOREIGN_KEY_QUERY,
    FOREIGN_KEY_QUERY_PRE_2017,
    INDEX_QUERY,
    INDEX_QUERY_PRE_2017,
    PARTITIONS_QUERY,
    SCHEMA_QUERY,
    TABLES_IN_SCHEMA_QUERY,
)
from datadog_checks.sqlserver.utils import (
    convert_to_bool,
    execute_query,
    get_list_chunks,
    is_azure_sql_database,
    is_collation_case_insensitive,
)


class SubmitData:
    def __init__(self, submit_data_function, base_event, logger):
        self._submit_to_agent_queue = submit_data_function
        self._base_event = base_event
        self._log = logger

        self._columns_count = 0
        self._total_columns_sent = 0
        self.db_to_schemas = {}  # dbname : { id : schema }
        self.db_info = {}  # name to info

    def set_base_event_data(self, hostname, tags, cloud_metadata, dbms_version):
        self._base_event["host"] = hostname
        self._base_event["tags"] = tags
        self._base_event["cloud_metadata"] = cloud_metadata
        self._base_event["dbms_version"] = dbms_version

    def reset(self):
        self._total_columns_sent = 0
        self._columns_count = 0
        self.db_to_schemas.clear()
        self.db_info.clear()

    def store_db_infos(self, db_infos, databases):
        dbs = set(databases)
        for db_info in db_infos:
            case_insensitive = is_collation_case_insensitive(db_info.get('collation'))
            db_name = db_info['name']
            db_name_lower = db_name.lower()
            if db_name not in dbs:
                if db_name.lower() in dbs and case_insensitive:
                    db_name = db_name_lower
                else:
                    self._log.debug(
                        "Skipping db {} as it is not in the databases list {} or collation is case sensitive".format(
                            db_name, dbs
                        )
                    )
                    continue
            self.db_info[db_name] = db_info

    def store(self, db_name, schema, tables, columns_count):
        self._columns_count += columns_count
        schemas = self.db_to_schemas.setdefault(db_name, {})
        if schema["id"] in schemas:
            known_tables = schemas[schema["id"]].setdefault("tables", [])
            known_tables = known_tables.extend(tables)
        else:
            schemas[schema["id"]] = schema
            schemas[schema["id"]]["tables"] = tables

    def columns_since_last_submit(self):
        return self._columns_count

    def truncate(self, json_event):
        max_length = 1000
        if len(json_event) > max_length:
            return json_event[:max_length] + " ... (truncated)"
        else:
            return json_event

    def send_truncated_msg(self, db_name, time_spent):
        event = {
            **self._base_event,
            "metadata": [],
            "timestamp": time.time() * 1000,
            "collection_errors": [{"error_type": "truncated", "message": ""}],
        }
        db_info = self.db_info[db_name]
        event["metadata"] = [{**(db_info)}]
        event["collection_errors"][0]["message"] = (
            "Truncated after fetching {} columns, elapsed time is {}s, database is {}".format(
                self._total_columns_sent, time_spent, db_name
            )
        )
        json_event = json.dumps(event, default=default_json_event_encoding)
        self._log.debug("Reporting truncation of schema collection: {}".format(self.truncate(json_event)))
        self._submit_to_agent_queue(json_event)

    def submit(self):
        if not self.db_to_schemas:
            return
        self._total_columns_sent += self._columns_count
        self._columns_count = 0
        event = {**self._base_event, "metadata": [], "timestamp": time.time() * 1000}
        for db, schemas_by_id in self.db_to_schemas.items():
            db_info = {}
            db_info = self.db_info[db]
            event["metadata"] = event["metadata"] + [{**(db_info), "schemas": list(schemas_by_id.values())}]
        json_event = json.dumps(event, default=default_json_event_encoding)
        self._log.debug("Reporting the following payload for schema collection: {}".format(self.truncate(json_event)))
        self._submit_to_agent_queue(json_event)
        self.db_to_schemas.clear()


def agent_check_getter(self):
    return self._check


class Schemas(DBMAsyncJob):

    TABLES_CHUNK_SIZE = 500
    # Note: in async mode execution time also cannot exceed 2 checks.
    DEFAULT_MAX_EXECUTION_TIME = 10
    MAX_COLUMNS_PER_EVENT = 100_000

    def __init__(self, check, config):
        self._check = check
        self._log = check.log
        self.schemas_per_db = {}
        self._last_schemas_collect_time = None
        collection_interval = config.schema_config.get('collection_interval', DEFAULT_SCHEMAS_COLLECTION_INTERVAL)
        self._max_execution_time = min(
            config.schema_config.get('max_execution_time', self.DEFAULT_MAX_EXECUTION_TIME), collection_interval
        )
        super(Schemas, self).__init__(
            check,
            run_sync=True,
            enabled=is_affirmative(config.schema_config.get('enabled', False)),
            expected_db_exceptions=(),
            # min collection interval is a desired collection interval for a check as a whole.
            min_collection_interval=config.min_collection_interval,
            dbms="sqlserver",
            rate_limit=1 / float(collection_interval),
            job_name="schemas",
            shutdown_callback=self.shut_down,
        )
        base_event = {
            "host": None,
            "agent_version": datadog_agent.get_version(),
            "dbms": "sqlserver",
            "kind": "sqlserver_databases",
            "collection_interval": collection_interval,
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
    def _fetch_schema_data(self, cursor, start_time, db_name):
        schemas = self._query_schema_information(cursor)
        for schema in schemas:
            tables = self._get_tables(schema, cursor)
            tables_chunks = list(get_list_chunks(tables, self.TABLES_CHUNK_SIZE))
            for tables_chunk in tables_chunks:
                schema_collection_elapsed_time = time.time() - start_time
                if schema_collection_elapsed_time > self._max_execution_time:
                    self._data_submitter.submit()
                    self._data_submitter.send_truncated_msg(db_name, schema_collection_elapsed_time)
                    raise StopIteration(
                        """Schema collection took {}s which is longer than allowed limit of {}s,
                        stopped while collecting for db - {}""".format(
                            schema_collection_elapsed_time, self._max_execution_time, db_name
                        )
                    )
                columns_count, tables_info = self._get_tables_data(tables_chunk, schema, cursor)
                self._data_submitter.store(db_name, schema, tables_info, columns_count)
                if self._data_submitter.columns_since_last_submit() > self.MAX_COLUMNS_PER_EVENT:
                    self._data_submitter.submit()
        self._data_submitter.submit()
        return False

    def _fetch_for_databases(self):
        start_time = time.time()
        databases = self._check.get_databases()
        engine_edition = self._check.static_info_cache.get(STATIC_INFO_ENGINE_EDITION)
        with self._check.connection.open_managed_default_connection():
            with self._check.connection.get_managed_cursor() as cursor:
                try:
                    for db_name in databases:
                        try:
                            if not is_azure_sql_database(engine_edition):
                                cursor.execute(SWITCH_DB_STATEMENT.format(db_name))
                            self._fetch_schema_data(cursor, start_time, db_name)
                        except StopIteration as e:
                            self._log.error(
                                """While executing fetch schemas for databse {},
                                   the following exception occured {}""".format(
                                    db_name, e
                                )
                            )
                            break
                        except Exception as e:
                            self._log.error(
                                """While executing fetch schemas for databse {},
                                   the following exception occured {}""".format(
                                    db_name, e
                                )
                            )
                finally:
                    # Switch DB back to MASTER
                    if not is_azure_sql_database(engine_edition):
                        cursor.execute(SWITCH_DB_STATEMENT.format(self._check.connection.DEFAULT_DATABASE))

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
        db_infos = self._query_db_information(databases)
        self._data_submitter.store_db_infos(db_infos, databases)
        self._fetch_for_databases()
        self._data_submitter.submit()
        self._log.debug("Finished collect_schemas_data")

    def _query_db_information(self, db_names):
        with self._check.connection.open_managed_default_connection():
            with self._check.connection.get_managed_cursor() as cursor:
                db_names_formatted = ",".join(["'{}'".format(t) for t in db_names])
                return execute_query(DB_QUERY.format(db_names_formatted), cursor, convert_results_to_str=True)

    @tracked_method(agent_check_getter=agent_check_getter, track_result_length=True)
    def _get_tables(self, schema, cursor):
        """returns a list of tables for schema with their names and empty column array
        list of table dicts
        "id": str
        "name": str
        "columns": []
        """
        tables_info = execute_query(TABLES_IN_SCHEMA_QUERY, cursor, convert_results_to_str=True, parameter=schema["id"])
        for t in tables_info:
            t.setdefault("columns", [])
        return tables_info

    @tracked_method(agent_check_getter=agent_check_getter, track_result_length=True)
    def _query_schema_information(self, cursor):
        """returns a list of schema dicts
        schema
        dict:
            "name": str
            "id": str
            "owner_name": str
        """
        return execute_query(SCHEMA_QUERY, cursor, convert_results_to_str=True)

    @tracked_method(agent_check_getter=agent_check_getter, track_result_length=True)
    def _get_tables_data(self, table_list, schema, cursor):
        """returns extracted column numbers and a list of tables
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
            table_name = str(row.get("table_name"))
            table_id = name_to_id.get(table_name)
            row.pop("table_name", None)
            if "nullable" in row:
                if row["nullable"].lower() == "no" or row["nullable"].lower() == "false":
                    row["nullable"] = False
                else:
                    row["nullable"] = True
            id_to_table_data.get(table_id)["columns"] = id_to_table_data.get(table_id).get("columns", []) + [row]
        return len(data)

    @tracked_method(agent_check_getter=agent_check_getter)
    def _populate_with_partitions_data(self, table_ids, table_id_to_table_data, cursor):
        rows = execute_query(PARTITIONS_QUERY.format(table_ids), cursor)
        for row in rows:
            table_id = row.pop("id", None)
            table_id_str = str(table_id)
            table_id_to_table_data[table_id_str]["partitions"] = row

    @tracked_method(agent_check_getter=agent_check_getter)
    def _populate_with_index_data(self, table_ids, table_id_to_table_data, cursor):
        index_query = INDEX_QUERY
        if self._check.static_info_cache.get(STATIC_INFO_MAJOR_VERSION) <= 2016:
            index_query = INDEX_QUERY_PRE_2017
        rows = execute_query(index_query.format(table_ids), cursor)
        for row in rows:
            table_id = row.pop("id", None)
            table_id_str = str(table_id)
            if "is_unique" in row:
                row["is_unique"] = convert_to_bool(row["is_unique"])
            if "is_primary_key" in row:
                row["is_primary_key"] = convert_to_bool(row["is_primary_key"])
            if "is_disabled" in row:
                row["is_disabled"] = convert_to_bool(row["is_disabled"])
            if "is_unique_constraint" in row:
                row["is_unique_constraint"] = convert_to_bool(row["is_unique_constraint"])
            table_id_to_table_data[table_id_str].setdefault("indexes", [])
            table_id_to_table_data[table_id_str]["indexes"].append(row)

    @tracked_method(agent_check_getter=agent_check_getter, track_result_length=True)
    def _populate_with_foreign_keys_data(self, table_ids, table_id_to_table_data, cursor):
        foreign_key_query = FOREIGN_KEY_QUERY
        if self._check.static_info_cache.get(STATIC_INFO_MAJOR_VERSION) <= 2016:
            foreign_key_query = FOREIGN_KEY_QUERY_PRE_2017
        rows = execute_query(foreign_key_query.format(table_ids), cursor)
        for row in rows:
            table_id = row.pop("id", None)
            table_id_str = str(table_id)
            table_id_to_table_data.get(table_id_str).setdefault("foreign_keys", [])
            table_id_to_table_data.get(table_id_str)["foreign_keys"].append(row)
