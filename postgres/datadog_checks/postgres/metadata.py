# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from typing import Dict, Optional, Tuple  # noqa: F401

import time
import json
import psycopg2

try:
    import datadog_agent
except ImportError:
    from ..stubs import datadog_agent

from datadog_checks.base import is_affirmative
from datadog_checks.base.utils.db.utils import (
    DBMAsyncJob,
    default_json_event_encoding,
)
from datadog_checks.postgres.connections import MultiDatabaseConnectionPool
from datadog_checks.base.utils.tracking import tracked_method

# default pg_settings collection interval in seconds
DEFAULT_SETTINGS_COLLECTION_INTERVAL = 600
DEFAULT_SCHEMA_COLLECTION_INTERVAL = 600

PG_SETTINGS_QUERY = """
SELECT name, setting FROM pg_settings
"""

SCHEMAS_QUERY = '''
SELECT
  s.schema_name AS schema_name,
  s.schema_owner AS schema_owner,
  t.table_name AS table_name,
  c.column_name AS column_name,
  c.data_type AS data_type,
  c.column_default AS column_default,
  c.is_nullable::boolean AS nullable
FROM
  information_schema.schemata s
  LEFT JOIN information_schema.tables t ON s.schema_name = t.table_schema
  LEFT JOIN information_schema.columns c ON t.table_schema = c.table_schema AND t.table_name = c.table_name
WHERE
  s.schema_name <> 'information_schema' AND
  s.schema_name <> 'pg_catalog';
'''


def agent_check_getter(self):
    return self._check


class PostgresMetadata(DBMAsyncJob):
    """
    Collects database metadata. Supports:
        1. cloud metadata collection for resource creations
        2. collection of pg_settings
    """

    def __init__(self, check, config, shutdown_callback):
        self.pg_settings_collection_interval = config.metadata_config.get(
            'settings_collection_interval', DEFAULT_SETTINGS_COLLECTION_INTERVAL
        )
        self.pg_schema_collection_interval = config.metadata_config.get(
            'schema_collection_interval', DEFAULT_SCHEMA_COLLECTION_INTERVAL
        )

        # by default, send resources every 5 minutes
        self.collection_interval = min(300, self.pg_settings_collection_interval)
        self._conn_pool = MultiDatabaseConnectionPool(check._new_connection)

        def shutdown_cb():
            self._conn_pool.close_all_connections()
            return shutdown_callback()

        super(PostgresMetadata, self).__init__(
            check,
            rate_limit=1 / self.collection_interval,
            run_sync=is_affirmative(config.metadata_config.get('run_sync', False)),
            enabled=True,
            dbms="postgres",
            min_collection_interval=self.collection_interval,
            expected_db_exceptions=(psycopg2.errors.DatabaseError,),
            job_name="database-metadata",
            shutdown_callback=shutdown_cb,
        )
        self._check = check
        self._config = config
        self._collect_pg_settings_enabled = is_affirmative(config.metadata_config.get('collect_settings', False))
        self._collect_schemas_enabled = is_affirmative(config.metadata_config.get('schema_collection_interval', False))
        self._schema_db_names = is_affirmative(config.metadata_config.get('db_names', []))
        self._pg_settings_cached = None
        self._time_since_last_pg_settings_query = 0
        self._time_since_last_information_schema_query = 0
        self._conn_ttl_ms = self._config.idle_connection_timeout
        self._tags_no_db = None
        self.tags = None

    def _dbtags(self, db, *extra_tags):
        """
        Returns the default instance tags with the initial "db" tag replaced with the provided tag
        """
        t = ["db:" + db]
        if extra_tags:
            t.extend(extra_tags)
        if self._tags_no_db:
            t.extend(self._tags_no_db)
        return t

    def run_job(self):
        # do not emit any dd.internal metrics for DBM specific check code
        self.tags = [t for t in self._tags if not t.startswith('dd.internal')]
        self._tags_no_db = [t for t in self.tags if not t.startswith('db:')]
        self.report_resources_and_settings()
        self.report_schemas()
        self._conn_pool.prune_connections()

    @tracked_method(agent_check_getter=agent_check_getter)
    def report_resources_and_settings(self):
        # Only query for settings if configured to do so &&
        # don't report more often than the configured collection interval
        elapsed_s = time.time() - self._time_since_last_pg_settings_query
        if elapsed_s >= self.pg_settings_collection_interval and self._collect_pg_settings_enabled:
            self._pg_settings_cached = self._collect_postgres_settings()
        event = {
            "host": self._check.resolved_hostname,
            "agent_version": datadog_agent.get_version(),
            "dbms": "postgres",
            "kind": "pg_settings",
            "collection_interval": self.collection_interval,
            'dbms_version': self._payload_pg_version(),
            "tags": self._tags_no_db,
            "timestamp": time.time() * 1000,
            "cloud_metadata": self._config.cloud_metadata,
            "metadata": self._pg_settings_cached,
        }
        self._check.database_monitoring_metadata(json.dumps(event, default=default_json_event_encoding))

    @tracked_method(agent_check_getter=agent_check_getter)
    def report_schemas(self):
        rows = []
        # Only query for schemas if configured to do so &&
        # don't report more often than the configured collection interval
        elapsed_s = time.time() - self._time_since_last_information_schema_query
        if elapsed_s >= self.pg_schema_collection_interval and self._collect_schemas_enabled:
            rows = self._collect_postgres_settings()
            self._pg_settings_cached = rows
        if rows:
            event = {
                "host": self._check.resolved_hostname,
                "agent_version": datadog_agent.get_version(),
                "dbms": "postgres",
                "kind": "pg_databases",
                "collection_interval": self.pg_schema_collection_interval,
                'dbms_version': self._payload_pg_version(),
                "tags": self._tags_no_db,
                "timestamp": time.time() * 1000,
                "cloud_metadata": self._config.cloud_metadata,
                "metadata": self._pg_settings_cached,
            }
            self._check.database_monitoring_metadata(json.dumps(event, default=default_json_event_encoding))

    def _payload_pg_version(self):
        version = self._check.version
        if not version:
            return ""
        return 'v{major}.{minor}.{patch}'.format(major=version.major, minor=version.minor, patch=version.patch)

    @tracked_method(agent_check_getter=agent_check_getter)
    def _collect_postgres_settings(self):
        with self._conn_pool.get_connection(self._config.dbname, ttl_ms=self._conn_ttl_ms).cursor(
            cursor_factory=psycopg2.extras.DictCursor
        ) as cursor:
            self._log.debug("Running query [%s] %s", PG_SETTINGS_QUERY)
            self._time_since_last_pg_settings_query = time.time()
            cursor.execute(PG_SETTINGS_QUERY)
            rows = cursor.fetchall()
            self._log.debug("Loaded %s rows from pg_settings", len(rows))
            return [dict(row) for row in rows]

    @tracked_method(agent_check_getter=agent_check_getter)
    def _collect_postgres_schemas(self):
        with self._conn_pool.get_connection(self._config.dbname, ttl_ms=self._conn_ttl_ms).cursor(
                cursor_factory=psycopg2.extras.DictCursor
        ) as cursor:
            self._log.debug("Running query [%s] %s", SCHEMAS_QUERY)
            self._time_since_last_information_schema_query = time.time()
            cursor.execute(SCHEMAS_QUERY)
            rows = cursor.fetchall()
            self._log.debug("Loaded %s rows from information_schema", len(rows))
            # Transform the query result into the desired JSON structure
            schemas = []
            current_schema = None
            current_table = None

            for row in rows:
                schema_name = row['schema_name']
                schema_owner = row['schema_owner']
                table_name = row['table_name']
                column_name = row['column_name']
                data_type = row['data_type']
                column_default = row['column_default']
                nullable = row['nullable']

                if current_schema is None or current_schema['name'] != schema_name:
                    current_schema = {
                        'name': schema_name,
                        'owner': schema_owner,
                        'tables': []
                    }
                    schemas.append(current_schema)

                if current_table is None or current_table['name'] != table_name:
                    current_table = {
                        'name': table_name,
                        'columns': []
                    }
                    current_schema['tables'].append(current_table)

                current_table['columns'].append({
                    'name': column_name,
                    'data_type': data_type,
                    'default': column_default,
                    'nullable': nullable
                })
        # TODO: need to get these fields too
        #     "description": "This database belongs to us.",
        # "encoding": "UTF-8",
        # "id": "564182",
        # "name": "kolesky",
        # "owner": "us",