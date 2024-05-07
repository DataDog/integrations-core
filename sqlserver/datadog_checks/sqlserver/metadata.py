# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import time
from datadog_checks.base import is_affirmative
from datadog_checks.base.utils.db.utils import (
    DBMAsyncJob,
    default_json_event_encoding,
)
from datadog_checks.base.utils.serialization import json
from datadog_checks.base.utils.tracking import tracked_method
from datadog_checks.sqlserver.config import SQLServerConfig

try:
    import datadog_agent
except ImportError:
    from ..stubs import datadog_agent

from datadog_checks.sqlserver.const import STATIC_INFO_ENGINE_EDITION, STATIC_INFO_VERSION

# default settings collection interval in seconds
DEFAULT_SETTINGS_COLLECTION_INTERVAL = 600

SETTINGS_QUERY = """\
SELECT {columns} FROM sys.configurations
"""

SQL_SERVER_SETTINGS_COLUMNS = [
    "name",
    "value",
    "minimum",
    "maximum",
    "value_in_use",
    "is_dynamic",
    "is_advanced",
]

# some columns use the sql_varient type, which isn't supported
# by most pyodbc drivers, instead we can cast these values to VARCHAR
SQL_COLS_CAST_TYPE = {
    "minimum": "varchar(max)",
    "maximum": "varchar(max)",
    "value_in_use": "varchar(max)",
    "value": "varchar(max)",
}


def agent_check_getter(self):
    return self._check


class SqlserverMetadata(DBMAsyncJob):
    """
    Collects database metadata. Supports:
        1. collection of sqlserver instance settings
    """

    def __init__(self, check, config: SQLServerConfig):
        # do not emit any dd.internal metrics for DBM specific check code
        self.tags = [t for t in check.tags if not t.startswith('dd.internal')]
        self.log = check.log
        self._config = config
        self.collection_interval = self._config.settings_config.get(
            'collection_interval', DEFAULT_SETTINGS_COLLECTION_INTERVAL
        )

        super(SqlserverMetadata, self).__init__(
            check,
            run_sync=is_affirmative(self._config.settings_config.get('run_sync', False)),
            enabled=is_affirmative(self._config.settings_config.get('enabled', False)),
            expected_db_exceptions=(),
            min_collection_interval=self._config.min_collection_interval,
            dbms="sqlserver",
            rate_limit=1 / float(self.collection_interval),
            job_name="database-metadata",
            shutdown_callback=self._close_db_conn,
        )
        self.disable_secondary_tags = is_affirmative(
            self._config.statement_metrics_config.get('disable_secondary_tags', False)
        )
        self._conn_key_prefix = "dbm-metadata-"
        self._settings_query = None
        self._time_since_last_settings_query = 0
        self._max_query_metrics = self._config.statement_metrics_config.get("max_queries", 250)

    def _close_db_conn(self):
        pass

    def run_job(self):
        self.report_sqlserver_metadata()

    def _get_available_settings_columns(self, cursor, all_expected_columns):
        cursor.execute("select top 0 * from sys.configurations")
        all_columns = {i[0] for i in cursor.description}
        available_columns = [c for c in all_expected_columns if c in all_columns]
        missing_columns = set(all_expected_columns) - set(available_columns)
        if missing_columns:
            self.log.debug(
                "missing the following expected settings columns from sys.configurations: %s", missing_columns
            )
        self.log.debug("found available sys.configurations columns: %s", available_columns)
        return available_columns

    def _get_settings_query_cached(self, cursor):
        if self._settings_query:
            return self._settings_query
        available_columns = self._get_available_settings_columns(cursor, SQL_SERVER_SETTINGS_COLUMNS)
        formatted_columns = []
        for column in available_columns:
            if column in SQL_COLS_CAST_TYPE:
                formatted_columns.append(f"CAST({column} AS {SQL_COLS_CAST_TYPE[column]}) AS {column}")
            else:
                formatted_columns.append(column)
        self._settings_query = SETTINGS_QUERY.format(
            columns=', '.join(formatted_columns),
        )
        return self._settings_query

    @tracked_method(agent_check_getter=agent_check_getter, track_result_length=True)
    def _load_settings_rows(self, cursor):
        self.log.debug("collecting sql server instance settings")
        query = self._get_settings_query_cached(cursor)
        self.log.debug("Running query [%s]", query)
        cursor.execute(query)
        columns = [i[0] for i in cursor.description]
        # construct row dicts manually as there's no DictCursor for pyodbc
        rows = [dict(zip(columns, row)) for row in cursor.fetchall()]
        self.log.debug("loaded sql server settings len(rows)=%s", len(rows))
        return rows
    
    """schemas data struct is a dictionnary with key being a schema name the value is
    schema
    dict:
        "name": str
        "schema_id": str
        "principal_id": str
        "tables" : dict
            name: list of columns                  
                "columns": dict
                    name: str
                    data_type: str
                    default: str


    """
    @tracked_method(agent_check_getter=agent_check_getter, track_result_length=True)
    def _query_schema_information(self, cursor):

        # principal_id is kind of like an owner

        # Todo put in consts
        # there is also principal_id not sure if need it.
        SCHEMA_QUERY = "SELECT name,schema_id,principal_id FROM sys.schemas;"
        self.log.debug("collecting db schemas")
        self.log.debug("Running query [%s]", SCHEMA_QUERY)
        cursor.execute(SCHEMA_QUERY)
        schemas = []
        columns = [i[0] for i in cursor.description]
        schemas = [dict(zip(columns, row)) for row in cursor.fetchall()]
        schemas_by_name = {}

        schemas_by_name = {}

        for schema in schemas:
            name = schema['name'].lower()
            #add tables
            schema['tables'] = {}
            schemas_by_name[name] = schema

        self.log.debug("fetched schemas len(rows)=%s", len(schemas))
        return schemas_by_name

    def _get_table_infos(self, schemas, cursor):
        #TODO do we need this for sqlserver ? 
        #If any tables are partitioned, only the master paritition table name will be returned, and none of its children.

        # TODO 
        #Do we need a limit ? like in postgress , seems not
        #limit = self._config.schemas_metadata_config.get("max_tables", 300)

        TABLES_QUERY = "SELECT TABLE_SCHEMA, TABLE_NAME, COLUMN_NAME, DATA_TYPE, COLUMN_DEFAULT FROM INFORMATION_SCHEMA.COLUMNS;"
        cursor.execute(TABLES_QUERY)
        #TODO
        #             nullable: bool column ?
        #TODO
        #"foreign_keys": dict (if has foreign keys)
        #    name: str
        #    definition: str
        #TODO
        #        "indexes": dict (if has indexes)
        #    name: str
        #    definition: str
        #TODO
        #"toast_table": str (if associated toast table exists) - equivalent in sql server
        
        # "partition_key": str (if has partitions) - equiv ? 

        # "num_partitions": int (if has partitions) - equiv ? 
        #apply lower case ? 
        #this is just to avoid doing something like row[0] , row[1] etc 
        columns = [str(i[0]).lower() for i in cursor.description]
        rows = [dict(zip(columns, row)) for row in cursor.fetchall()]
        
        for row in rows:
            if len(row) != 5:
                #TODO some warning ? 
                print("warning") 

            #TODO treat not found 
            schema = schemas[row['table_schema']]

            tables_dict_for_schema = schema['tables']

            #do the same mapping as in postgres for some uniformity otherwise could've just loop and exclude some keys
            if row['table_name'] not in tables_dict_for_schema:
                #new table
                tables_dict_for_schema[row['table_name']] = []
            column = {}
            column['name'] = row['column_name']
            column['data_type'] = row['data_type']
            column['default'] = row['column_default']
            #table is an array of column dict for now.
            tables_dict_for_schema[row['table_name']].append(column)
            # table dict has a key columns with value arrray of dicts

#self._sort_and_limit_table_info(cursor, dbname, table_info, limit)
# for now not sort and limit
    @tracked_method(agent_check_getter=agent_check_getter)
    def report_sqlserver_metadata(self):
        with self._check.connection.open_managed_default_connection(key_prefix=self._conn_key_prefix):
            with self._check.connection.get_managed_cursor(key_prefix=self._conn_key_prefix) as cursor:
                settings_rows = self._load_settings_rows(cursor)
                event = {
                    "host": self._check.resolved_hostname,
                    "agent_version": datadog_agent.get_version(),
                    "dbms": "sqlserver",
                    "kind": "sqlserver_configs",
                    "collection_interval": self.collection_interval,
                    'dbms_version': "{},{}".format(
                        self._check.static_info_cache.get(STATIC_INFO_VERSION, ""),
                        self._check.static_info_cache.get(STATIC_INFO_ENGINE_EDITION, ""),
                    ),
                    "tags": self.tags,
                    "timestamp": time.time() * 1000,
                    "cloud_metadata": self._config.cloud_metadata,
                    "metadata": settings_rows,
                }
                self._check.database_monitoring_metadata(json.dumps(event, default=default_json_event_encoding))
