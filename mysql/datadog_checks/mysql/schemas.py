# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

try:
    import datadog_agent
except ImportError:
    from ..stubs import datadog_agent

import json
import time
from contextlib import closing

import pymysql

from datadog_checks.base.utils.db.utils import default_json_event_encoding
from datadog_checks.base.utils.tracking import tracked_method
from datadog_checks.mysql.cursor import CommenterDictCursor
from datadog_checks.mysql.queries import (
    SQL_COLUMNS,
    SQL_DATABASES,
    SQL_FOREIGN_KEYS,
    SQL_INDEXES,
    SQL_PARTITION,
    SQL_TABLES,
)

from .util import fetch_and_convert_to_str, get_list_chunks

DEFAULT_SCHEMAS_COLLECTION_INTERVAL = 600


class SubmitData:

    def __init__(self, submit_data_function, base_event, logger):
        self._submit_to_agent_queue = submit_data_function
        self._base_event = base_event
        self._log = logger

        self._columns_count = 0
        self._total_columns_sent = 0
        self.db_to_tables = {}  # dbname : {"tables" : []}
        self.db_info = {}  # name to info

    def set_base_event_data(self, hostname, tags, cloud_metadata, dbms_version, flavor):
        self._base_event["host"] = hostname
        self._base_event["tags"] = tags
        self._base_event["cloud_metadata"] = cloud_metadata
        self._base_event["dbms_version"] = dbms_version
        self._base_event["flavor"] = flavor

    def reset(self):
        self._total_columns_sent = 0
        self._columns_count = 0
        self.db_info.clear()

    def store_db_infos(self, db_infos):
        for db_info in db_infos:
            self.db_info[db_info['name']] = db_info

    def store(self, db_name, tables, columns_count):
        self._columns_count += columns_count
        known_tables = self.db_to_tables.setdefault(db_name, [])
        known_tables.extend(tables)

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
        if not self.db_to_tables:
            return
        self._total_columns_sent += self._columns_count
        self._columns_count = 0
        event = {**self._base_event, "metadata": [], "timestamp": time.time() * 1000}
        for db, tables in self.db_to_tables.items():
            db_info = self.db_info[db]
            event["metadata"] = event["metadata"] + [{**(db_info), "tables": tables}]
        json_event = json.dumps(event, default=default_json_event_encoding)
        self._log.debug("Reporting the following payload for schema collection: {}".format(self.truncate(json_event)))
        self._submit_to_agent_queue(json_event)
        self.db_to_tables.clear()


def agent_check_getter(self):
    return self._check


class Schemas:

    TABLES_CHUNK_SIZE = 500
    # Note: in async mode execution time also cannot exceed 2 checks.
    DEFAULT_MAX_EXECUTION_TIME = 60
    MAX_COLUMNS_PER_EVENT = 100_000

    def __init__(self, mysql_metadata, check, config):
        self._metadata = mysql_metadata
        self._check = check
        self._log = check.log
        self._tags = []
        collection_interval = config.schemas_config.get('collection_interval', DEFAULT_SCHEMAS_COLLECTION_INTERVAL)
        base_event = {
            "host": None,
            "agent_version": datadog_agent.get_version(),
            "dbms": "mysql",
            "kind": "mysql_databases",
            "collection_interval": collection_interval,
            "dbms_version": None,
            "tags": [],
            "cloud_metadata": self._check._config.cloud_metadata,
        }
        self._data_submitter = SubmitData(self._check.database_monitoring_metadata, base_event, self._log)

        self._max_execution_time = min(
            config.schemas_config.get('max_execution_time', self.DEFAULT_MAX_EXECUTION_TIME), collection_interval
        )

    def shut_down(self):
        self._data_submitter.submit()

    def _cursor_run(self, cursor, query, params=None):
        """
        Run and log the query. If provided, obfuscated params are logged in place of the regular params.
        """
        try:
            self._log.debug("Running query [{}] params={}".format(query, params))
            cursor.execute(query, params)
        except pymysql.DatabaseError as e:
            self._check.count(
                "dd.mysql.db.error",
                1,
                tags=self._tags + ["error:{}".format(type(e))] + self._check._get_debug_tags(),
                hostname=self._check.resolved_hostname,
            )
            raise

    @tracked_method(agent_check_getter=agent_check_getter)
    def _fetch_database_data(self, cursor, start_time, db_name):
        tables = self._get_tables(db_name, cursor)
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
            columns_count, tables_info = self._get_tables_data(tables_chunk, db_name, cursor)
            self._data_submitter.store(db_name, tables_info, columns_count)
            if self._data_submitter.columns_since_last_submit() > self.MAX_COLUMNS_PER_EVENT:
                self._data_submitter.submit()
        self._data_submitter.submit()

    @tracked_method(agent_check_getter=agent_check_getter)
    def _collect_databases_data(self, tags):
        """Collects database information and schemas and submits to the agent's queue as dictionaries
        database dict
        key/value:
            "name": str
            "default_character_set_name": str
            "default_collation_name": str
            "tables" : list of tables dicts
                table
                key/value:
                    "name" : str
                    columns: list of columns dicts
                        columns
                        key/value:
                            "name": str
                            "data_type": str
                            "default": str
                            "nullable": bool
                            "ordinal_position": str
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
        self._tags = tags
        with closing(self._metadata.get_db_connection().cursor(CommenterDictCursor)) as cursor:
            self._data_submitter.set_base_event_data(
                self._check.resolved_hostname,
                self._tags,
                self._check._config.cloud_metadata,
                self._check.version.version,
                self._check.version.flavor,
            )
            db_infos = self._query_db_information(cursor)
            self._data_submitter.store_db_infos(db_infos)
            self._fetch_for_databases(db_infos, cursor)
            self._data_submitter.submit()
            self._log.debug("Finished collect_schemas_data")

    def _fetch_for_databases(self, db_infos, cursor):
        start_time = time.time()
        for db_info in db_infos:
            try:
                self._fetch_database_data(cursor, start_time, db_info['name'])
            except StopIteration as e:
                self._log.error(
                    "While executing fetch database data for databse {}, the following exception occured {}".format(
                        db_info['name'], e
                    )
                )
                return
            except Exception as e:
                self._log.error(
                    "While executing fetch database data for databse {}, the following exception occured {}".format(
                        db_info['name'], e
                    )
                )

    @tracked_method(agent_check_getter=agent_check_getter)
    def _query_db_information(self, cursor):
        self._cursor_run(cursor, query=SQL_DATABASES)
        rows = fetch_and_convert_to_str(cursor)
        return rows

    @tracked_method(agent_check_getter=agent_check_getter, track_result_length=True)
    def _get_tables(self, db_name, cursor):
        """returns a list of tables for schema with their names and empty column array
        list of table dicts
        "id": str
        "name": str
        "columns": []
        """
        self._cursor_run(cursor, query=SQL_TABLES, params=db_name)
        tables_info = fetch_and_convert_to_str(cursor)
        return tables_info

    @tracked_method(agent_check_getter=agent_check_getter, track_result_length=True)
    def _get_tables_data(self, table_list, db_name, cursor):
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
        table_name_to_table_index = {}
        table_names = ""
        for i, table in enumerate(table_list):
            table_name_to_table_index[table["name"]] = i
            table_names += '"' + str(table["name"]) + '",'
        table_names = table_names[:-1]
        total_columns_number = self._populate_with_columns_data(
            table_name_to_table_index, table_list, table_names, db_name, cursor
        )
        self._populate_with_partitions_data(table_name_to_table_index, table_list, table_names, db_name, cursor)
        self._populate_with_foreign_keys_data(table_name_to_table_index, table_list, table_names, db_name, cursor)
        self._populate_with_index_data(table_name_to_table_index, table_list, table_names, db_name, cursor)
        return total_columns_number, table_list

    @tracked_method(agent_check_getter=agent_check_getter)
    def _populate_with_columns_data(self, table_name_to_table_index, table_list, table_names, db_name, cursor):
        self._cursor_run(
            cursor,
            query=SQL_COLUMNS.format(table_names),
            params=db_name,
        )
        rows = fetch_and_convert_to_str(cursor)
        for row in rows:
            if "nullable" in row:
                if row["nullable"].lower() == "yes":
                    row["nullable"] = True
                else:
                    row["nullable"] = False
            table_name = str(row.pop("table_name"))
            table_list[table_name_to_table_index[table_name]].setdefault("columns", [])
            table_list[table_name_to_table_index[table_name]]["columns"].append(row)

        return len(rows)

    @tracked_method(agent_check_getter=agent_check_getter)
    def _populate_with_index_data(self, table_name_to_table_index, table_list, table_names, db_name, cursor):
        self._cursor_run(cursor, query=SQL_INDEXES.format(table_names), params=db_name)
        rows = fetch_and_convert_to_str(cursor)
        for row in rows:
            table_name = str(row.pop("table_name"))
            table_list[table_name_to_table_index[table_name]].setdefault("indexes", [])
            if "nullables" in row:
                nullables_arr = row["nullables"].split(',')
                nullables_converted = ""
                for s in nullables_arr:
                    if s.lower() == "yes":
                        nullables_converted += "true,"
                    else:
                        nullables_converted += "false,"
                row["nullables"] = nullables_converted[:-1]
            table_list[table_name_to_table_index[table_name]]["indexes"].append(row)

    @tracked_method(agent_check_getter=agent_check_getter, track_result_length=True)
    def _populate_with_foreign_keys_data(self, table_name_to_table_index, table_list, table_names, db_name, cursor):
        self._cursor_run(cursor, query=SQL_FOREIGN_KEYS.format(table_names), params=db_name)
        rows = fetch_and_convert_to_str(cursor)

        for row in rows:
            table_name = str(row.pop("table_name"))
            table_list[table_name_to_table_index[table_name]].setdefault("foreign_keys", [])
            table_list[table_name_to_table_index[table_name]]["foreign_keys"].append(row)

    @tracked_method(agent_check_getter=agent_check_getter, track_result_length=True)
    def _populate_with_partitions_data(self, table_name_to_table_index, table_list, table_names, db_name, cursor):
        self._cursor_run(cursor, query=SQL_PARTITION.format(table_names), params=db_name)
        rows = fetch_and_convert_to_str(cursor)
        for row in rows:
            table_name = str(row.pop("table_name"))
            table_list[table_name_to_table_index[table_name]].setdefault("partitions", [])
            table_list[table_name_to_table_index[table_name]]["partitions"].append(row)
