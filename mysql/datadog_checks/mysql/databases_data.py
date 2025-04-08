# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

try:
    import datadog_agent
except ImportError:
    from ..stubs import datadog_agent
import json
import time
from collections import defaultdict
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
    SQL_INDEXES_8_0_13,
    SQL_INDEXES_EXPRESSION_COLUMN_CHECK,
    SQL_PARTITION,
    SQL_TABLES,
)

from .util import get_list_chunks

DEFAULT_DATABASES_DATA_COLLECTION_INTERVAL = 600


class SubmitData:

    def __init__(self, submit_data_function, base_event, logger):
        self._submit_to_agent_queue = submit_data_function
        self._base_event = base_event
        self._log = logger

        self._columns_count = 0
        self._total_columns_sent = 0
        self.db_to_tables = {}  # dbname : {"tables" : []}
        self.db_info = {}  # name to info
        self._log.debug("Initialized SubmitData instance")

    def set_base_event_data(self, hostname, tags, cloud_metadata, dbms_version, flavor):
        self._base_event["host"] = hostname
        self._base_event["tags"] = tags
        self._base_event["cloud_metadata"] = cloud_metadata
        self._base_event["dbms_version"] = dbms_version
        self._base_event["flavor"] = flavor
        self._log.debug("Set base event data with hostname: %s, flavor: %s", hostname, flavor)

    def reset(self):
        self._log.debug("Resetting submit data state (columns count: %d, total sent: %d)", 
                       self._columns_count, self._total_columns_sent)
        self._total_columns_sent = 0
        self._columns_count = 0
        self.db_info.clear()

    def store_db_infos(self, db_infos):
        self._log.debug("Storing information for %d databases", len(db_infos))
        for db_info in db_infos:
            self.db_info[db_info['name']] = db_info

    def store(self, db_name, tables, columns_count):
        self._columns_count += columns_count
        known_tables = self.db_to_tables.setdefault(db_name, [])
        known_tables.extend(tables)
        self._log.debug("Stored %d tables with %d columns for database %s (total columns: %d)",
                       len(tables), columns_count, db_name, self._columns_count)

    def columns_since_last_submit(self):
        return self._columns_count

    def truncate(self, json_event):
        max_length = 1000
        if len(json_event) > max_length:
            self._log.debug("Truncating JSON event from %d characters to %d", len(json_event), max_length)
            return json_event[:max_length] + " ... (truncated)"
        else:
            return json_event

    def send_truncated_msg(self, db_name, time_spent):
        self._log.debug("Sending truncated message for database %s after %0.2fs", db_name, time_spent)
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
            self._log.debug("No database tables to submit, skipping submission")
            return
        self._total_columns_sent += self._columns_count
        self._log.debug("Submitting data with %d columns (total sent: %d)", 
                       self._columns_count, self._total_columns_sent)
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


class DatabasesData:

    TABLES_CHUNK_SIZE = 500
    DEFAULT_MAX_EXECUTION_TIME = 60
    MAX_COLUMNS_PER_EVENT = 100_000

    def __init__(self, mysql_metadata, check, config):
        self._metadata = mysql_metadata
        self._check = check
        self._log = check.log
        self._tags = []
        collection_interval = config.schemas_config.get(
            'collection_interval', DEFAULT_DATABASES_DATA_COLLECTION_INTERVAL
        )
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
        self._log.debug("Initialized DatabasesData with collection interval: %ds, max_execution_time: %ds",
                       collection_interval,
                       min(config.schemas_config.get('max_execution_time', self.DEFAULT_MAX_EXECUTION_TIME), 
                           collection_interval))

        self._max_execution_time = min(
            config.schemas_config.get('max_execution_time', self.DEFAULT_MAX_EXECUTION_TIME), collection_interval
        )

    def shut_down(self):
        self._log.debug("Shutting down DatabasesData, submitting any remaining data")
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
            self._log.debug("Database error executing query [%s]: %s, %s", 
                           query, type(e).__name__, str(e))
            raise

    @tracked_method(agent_check_getter=agent_check_getter)
    def _fetch_database_data(self, cursor, start_time, db_name):
        self._log.debug("Fetching database data for %s (elapsed time: %0.2fs)", 
                       db_name, time.time() - start_time)
        tables = self._get_tables(db_name, cursor)
        self._log.debug("Retrieved %d tables for database %s", len(tables), db_name)
        tables_chunks = list(get_list_chunks(tables, self.TABLES_CHUNK_SIZE))
        self._log.debug("Split tables into %d chunks of size %d", 
                       len(tables_chunks), self.TABLES_CHUNK_SIZE)

        for chunk_idx, tables_chunk in enumerate(tables_chunks):
            schema_collection_elapsed_time = time.time() - start_time
            self._log.debug("Processing chunk %d/%d (tables: %d, elapsed time: %0.2fs)",
                           chunk_idx + 1, len(tables_chunks), len(tables_chunk),
                           schema_collection_elapsed_time)

            if schema_collection_elapsed_time > self._max_execution_time:
                self._log.debug("Schema collection time exceeded limit (%0.2fs > %ds), truncating", 
                               schema_collection_elapsed_time, self._max_execution_time)
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
                self._log.debug("Column count exceeded maximum per event (%d > %d), submitting batch",
                               self._data_submitter.columns_since_last_submit(),
                               self.MAX_COLUMNS_PER_EVENT)
                self._data_submitter.submit()
        self._log.debug("Completed processing all chunks for database %s, submitting data", db_name)
        self._data_submitter.submit()

    @tracked_method(agent_check_getter=agent_check_getter)
    def _collect_databases_data(self, tags):
        """
        Collects database information and schemas and submits them to the agent's queue as dictionaries.

        A submitted dictionary:
            dict: A dictionary representing the database information.

            - name (str): The name of the database.
            - default_character_set_name (str): The default character set name.
            - default_collation_name (str): The default collation name.
            - tables (list): A list of table dictionaries.
                - table (dict): A dictionary representing a table.
                    - name (str): The name of the table.
                    - columns (list): A list of column dictionaries.
                        - column (dict): A dictionary representing a column.
                            - name (str): The name of the column.
                            - data_type (str): The data type of the column.
                            - default (str): The default value of the column.
                            - nullable (bool): Whether the column is nullable.
                            - ordinal_position (str): The ordinal position of the column.
                    - indexes (list): A list of index dictionaries.
                        - index (dict): A dictionary representing an index.
                            - name (str): The name of the index.
                            - cardinality (int): The cardinality of the index.
                            - index_type (str): The index method used.
                            - columns (list): A list of column dictionaries
                                - column (dict): A dictionary representing a column.
                                    - name (str): The name of the column.
                                    - sub_part (int): The number of indexed characters if column is partially indexed.
                                    - collation (str): The collation of the column.
                                    - packed (str): How the index is packed.
                                    - nullable (bool): Whether the column is nullable.
                            - non_unique (bool): Whether the index can contain duplicates.
                            - expression (str): If index was built with a functional key part, the expression used.
                    - foreign_keys (list): A list of foreign key dictionaries.
                        - foreign_key (dict): A dictionary representing a foreign key.
                            - constraint_schema (str): The schema of the constraint.
                            - name (str): The name of the foreign key.
                            - column_names (str): The column names in the foreign key.
                            - referenced_table_schema (str): The schema of the referenced table.
                            - referenced_table_name (str): The name of the referenced table.
                            - referenced_column_names (str): The column names in the referenced table.
                            - update_action (str): The update rule for the foreign key.
                            - delete_action (str): The delete rule for the foreign key.
                    - partitions (list): A list of partition dictionaries.
                        - partition (dict): A dictionary representing a partition.
                            - name (str): The name of the partition.
                            - subpartitions (list): A list of subpartition dictionaries.
                                - subpartition (dict): A dictionary representing a subpartition.
                                    - name (str): The name of the subpartition.
                                    - subpartition_ordinal_position (int): The ordinal position of the subpartition.
                                    - subpartition_method (str): The subpartition method.
                                    - subpartition_expression (str): The subpartition expression.
                                    - table_rows (int): The number of rows in the subpartition.
                                    - data_length (int): The data length of the subpartition in bytes.
                            - partition_ordinal_position (int): The ordinal position of the partition.
                            - partition_method (str): The partition method.
                            - partition_expression (str): The partition expression.
                            - partition_description (str): The description of the partition.
                            - table_rows (int): The number of rows in the partition. If partition has subpartitions,
                                                this is the sum of all subpartitions table_rows.
                            - data_length (int): The data length of the partition in bytes. If partition has
                                                 subpartitions, this is the sum of all subpartitions data_length.
        """
        self._log.debug("Starting to collect database schema data")
        self._data_submitter.reset()
        self._tags = tags
        with closing(self._metadata.get_db_connection().cursor(CommenterDictCursor)) as cursor:
            self._log.debug("Obtained database connection cursor")
            self._data_submitter.set_base_event_data(
                self._check.resolved_hostname,
                self._tags,
                self._check._config.cloud_metadata,
                self._check.version.version,
                self._check.version.flavor,
            )
            db_infos = self._query_db_information(cursor)
            self._log.debug("Retrieved information for %d databases", len(db_infos))
            self._data_submitter.store_db_infos(db_infos)
            self._fetch_for_databases(db_infos, cursor)
            self._data_submitter.submit()
            self._log.debug("Finished collect_schemas_data")

    def _fetch_for_databases(self, db_infos, cursor):
        start_time = time.time()
        self._log.debug("Starting to fetch data for %d databases", len(db_infos))
        for i, db_info in enumerate(db_infos):
            db_name = db_info['name']
            self._log.debug("Processing database %d/%d: %s", i+1, len(db_infos), db_name)
            try:
                self._fetch_database_data(cursor, start_time, db_name)
            except StopIteration as e:
                self._log.error(
                    "While executing fetch database data for database {}, the following exception occured {}".format(
                        db_name, e
                    )
                )
                self._log.debug("Stopped iteration while fetching data for database %s: %s", db_name, str(e))
                return
            except Exception as e:
                self._log.error(
                    "While executing fetch database data for database {}, the following exception occured {}".format(
                        db_name, e
                    )
                )
                self._log.debug("Exception details for %s: %s, %s", db_name, type(e).__name__, str(e))
        self._log.debug("Completed fetching data for all databases in %0.2fs", time.time() - start_time)

    @tracked_method(agent_check_getter=agent_check_getter)
    def _query_db_information(self, cursor):
        self._log.debug("Querying database information")
        self._cursor_run(cursor, query=SQL_DATABASES)
        rows = cursor.fetchall()
        self._log.debug("Retrieved information for %d databases", len(rows))
        return rows

    @tracked_method(agent_check_getter=agent_check_getter, track_result_length=True)
    def _get_tables(self, db_name, cursor):
        """returns a list of tables for schema with their names and empty column array
        list of table dicts
        "name": str
        """
        self._log.debug("Getting tables for database %s", db_name)
        self._cursor_run(cursor, query=SQL_TABLES, params=db_name)
        tables_info = cursor.fetchall()
        self._log.debug("Found %d tables in database %s", len(tables_info), db_name)
        return tables_info

    @tracked_method(agent_check_getter=agent_check_getter, track_result_length=True)
    def _get_tables_data(self, table_list, db_name, cursor):
        self._log.debug("Getting table data for %d tables in database %s", len(table_list), db_name)
        if len(table_list) == 0:
            self._log.debug("No tables to process for %s", db_name)
            return 0, []

        table_name_to_table_index = {}
        table_names = ""
        for i, table in enumerate(table_list):
            table_name_to_table_index[table["name"]] = i
            table_names += '"' + str(table["name"]) + '",'
        table_names = table_names[:-1]

        self._log.debug("Populating column data for %d tables in %s", len(table_list), db_name)
        total_columns_number = self._populate_with_columns_data(
            table_name_to_table_index, table_list, table_names, db_name, cursor
        )

        self._log.debug("Populating partition data for %d tables in %s", len(table_list), db_name)
        self._populate_with_partitions_data(table_name_to_table_index, table_list, table_names, db_name, cursor)

        self._log.debug("Populating foreign key data for %d tables in %s", len(table_list), db_name)
        self._populate_with_foreign_keys_data(table_name_to_table_index, table_list, table_names, db_name, cursor)

        self._log.debug("Populating index data for %d tables in %s", len(table_list), db_name)
        self._populate_with_index_data(table_name_to_table_index, table_list, table_names, db_name, cursor)

        self._log.debug("Completed populating all metadata for %d tables with %d columns in %s",
                       len(table_list), total_columns_number, db_name)
        return total_columns_number, table_list

    @tracked_method(agent_check_getter=agent_check_getter)
    def _populate_with_columns_data(self, table_name_to_table_index, table_list, table_names, db_name, cursor):
        self._log.debug("Fetching column data for tables in %s", db_name)
        self._cursor_run(
            cursor,
            query=SQL_COLUMNS.format(table_names),
            params=db_name,
        )
        rows = cursor.fetchall()
        self._log.debug("Processing %d columns across tables in %s", len(rows), db_name)
        for row in rows:
            if "nullable" in row:
                if row["nullable"].lower() == "yes":
                    row["nullable"] = True
                else:
                    row["nullable"] = False
            if "default" in row:
                if row["default"] is not None:
                    row["default"] = str(row["default"])
            table_name = str(row.pop("table_name"))
            table_list[table_name_to_table_index[table_name]].setdefault("columns", [])
            table_list[table_name_to_table_index[table_name]]["columns"].append(row)

        self._log.debug("Added %d columns across tables in %s", len(rows), db_name)
        return len(rows)

    @tracked_method(agent_check_getter=agent_check_getter)
    def _populate_with_index_data(self, table_name_to_table_index, table_list, table_names, db_name, cursor):
        self._log.debug("Checking for expression column support in %s", db_name)
        self._cursor_run(cursor, query=SQL_INDEXES_EXPRESSION_COLUMN_CHECK)
        has_expression_columns = cursor.fetchone()["column_count"] > 0

        query = (
            SQL_INDEXES_8_0_13.format(table_names)
            if has_expression_columns
            else SQL_INDEXES.format(table_names)
        )
        self._log.debug("Using %s query for index data in %s",
                       "8.0.13+" if has_expression_columns else "standard", db_name)

        self._cursor_run(cursor, query=query, params=db_name)
        rows = cursor.fetchall()
        self._log.debug("Retrieved %d index records for tables in %s", len(rows) if rows else 0, db_name)

        if not rows:
            self._log.debug("No indexes found for tables in %s", db_name)
            return

        table_index_dict = defaultdict(lambda: defaultdict(lambda: {}))
        for row in rows:
            table_name = str(row["table_name"])
            table_list[table_name_to_table_index[table_name]].setdefault("indexes", [])
            index_name = str(row["name"])
            index_data = table_index_dict[table_name][index_name]

            # Update index-level info
            index_data["name"] = index_name
            index_data["cardinality"] = int(row["cardinality"])
            index_data["index_type"] = str(row["index_type"])
            index_data["non_unique"] = bool(row["non_unique"])
            if row["expression"]:
                index_data["expression"] = str(row["expression"])

            # Add column info, if exists
            if row["column_name"]:
                index_data.setdefault("columns", [])
                column = {"name": row["column_name"], "nullable": bool(row["nullable"].lower() == "yes")}
                if row["sub_part"]:
                    column["sub_part"] = int(row["sub_part"])
                if row["collation"]:
                    column["collation"] = str(row["collation"])
                if row["packed"]:
                    column["packed"] = str(row["packed"])
                index_data["columns"].append(column)

        index_count = 0
        for table_name, index_dict in table_index_dict.items():
            table_indexes = list(index_dict.values())
            table_list[table_name_to_table_index[table_name]]["indexes"] = table_indexes
            index_count += len(table_indexes)

        self._log.debug("Added %d indexes across tables in %s", index_count, db_name)

    @tracked_method(agent_check_getter=agent_check_getter, track_result_length=True)
    def _populate_with_foreign_keys_data(self, table_name_to_table_index, table_list, table_names, db_name, cursor):
        self._log.debug("Fetching foreign key data for tables in %s", db_name)
        self._cursor_run(cursor, query=SQL_FOREIGN_KEYS.format(table_names), params=db_name)
        rows = cursor.fetchall()
        self._log.debug("Retrieved %d foreign keys for tables in %s", len(rows), db_name)

        fk_count = 0
        for row in rows:
            table_name = row["table_name"]
            table_list[table_name_to_table_index[table_name]].setdefault("foreign_keys", [])
            table_list[table_name_to_table_index[table_name]]["foreign_keys"].append(row)
            fk_count += 1

        self._log.debug("Added %d foreign keys across tables in %s", fk_count, db_name)

    @tracked_method(agent_check_getter=agent_check_getter, track_result_length=True)
    def _populate_with_partitions_data(self, table_name_to_table_index, table_list, table_names, db_name, cursor):
        self._log.debug("Fetching partition data for tables in %s", db_name)
        self._cursor_run(cursor, query=SQL_PARTITION.format(table_names), params=db_name)
        rows = cursor.fetchall()
        self._log.debug("Retrieved %d partition records for tables in %s", len(rows) if rows else 0, db_name)

        if not rows:
            self._log.debug("No partitions found for tables in %s", db_name)
            return
        table_partitions_dict = defaultdict(
            lambda: defaultdict(
                lambda: {
                    "table_rows": 0,
                    "data_length": 0,
                }
            )
        )

        for row in rows:
            table_name = str(row["table_name"])
            table_list[table_name_to_table_index[table_name]].setdefault("partitions", [])
            partition_name = str(row["name"])
            partition_data = table_partitions_dict[table_name][partition_name]

            # Update partition-level info
            partition_data["name"] = partition_name
            partition_data["partition_ordinal_position"] = int(row["partition_ordinal_position"])
            partition_data["partition_method"] = str(row["partition_method"])
            partition_data["partition_expression"] = str(row["partition_expression"]).strip().lower()
            partition_data["partition_description"] = str(row["partition_description"])
            partition_data["table_rows"] += int(row["table_rows"])
            partition_data["data_length"] += int(row["data_length"])

            # Add subpartition info, if exists
            if row["subpartition_name"]:
                partition_data.setdefault("subpartitions", [])
                subpartition = {
                    "name": row["subpartition_name"],
                    "subpartition_ordinal_position": int(row["subpartition_ordinal_position"]),
                    "subpartition_method": str(row["subpartition_method"]),
                    "subpartition_expression": str(row["subpartition_expression"]).strip().lower(),
                    "table_rows": int(row["table_rows"]),
                    "data_length": int(row["data_length"]),
                }
                partition_data["subpartitions"].append(subpartition)

        partition_count = 0
        subpartition_count = 0

        for table_name, partitions_dict in table_partitions_dict.items():
            partitions = list(partitions_dict.values())
            table_list[table_name_to_table_index[table_name]]["partitions"] = partitions
            partition_count += len(partitions)

            for partition in partitions:
                if "subpartitions" in partition:
                    subpartition_count += len(partition["subpartitions"])

        self._log.debug("Added %d partitions and %d subpartitions across tables in %s",
                       partition_count, subpartition_count, db_name)
