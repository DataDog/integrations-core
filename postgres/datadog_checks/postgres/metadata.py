# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json
import time
from typing import Dict, Optional, Tuple  # noqa: F401

import psycopg
from psycopg.rows import dict_row

try:
    import datadog_agent
except ImportError:
    from ..stubs import datadog_agent

from datadog_checks.base import is_affirmative
from datadog_checks.base.utils.db.utils import DBMAsyncJob, default_json_event_encoding
from datadog_checks.base.utils.tracking import tracked_method
from datadog_checks.postgres.connections import MultiDatabaseConnectionPool

# default pg_settings collection interval in seconds
DEFAULT_SETTINGS_COLLECTION_INTERVAL = 600
DEFAULT_RESOURCES_COLLECTION_INTERVAL = 300

PG_SETTINGS_QUERY = """
SELECT name, setting FROM pg_settings
"""


def agent_check_getter(self):
    return self._check


class PostgresMetadata(DBMAsyncJob):
    """
    Collects database metadata. Supports:
        1. cloud metadata collection for resource creations
        2. collection of pg_settings
    """

    def __init__(self, check, config, shutdown_callback):
        self.pg_settings_collection_interval = config.settings_metadata_config.get(
            'collection_interval', DEFAULT_SETTINGS_COLLECTION_INTERVAL
        )
        collection_interval = config.resources_metadata_config.get(
            'collection_interval', DEFAULT_RESOURCES_COLLECTION_INTERVAL
        )

        # by default, send resources every 5 minutes
        self.collection_interval = min(collection_interval, self.pg_settings_collection_interval)
        self._conn_pool = MultiDatabaseConnectionPool(check._new_connection)

        def shutdown_cb():
            self._conn_pool.close_all_connections()
            return shutdown_callback()

        super(PostgresMetadata, self).__init__(
            check,
            rate_limit=1 / self.collection_interval,
            run_sync=is_affirmative(config.settings_metadata_config.get('run_sync', False)),
            enabled=is_affirmative(config.resources_metadata_config.get('enabled', True)),
            dbms="postgres",
            min_collection_interval=config.min_collection_interval,
            expected_db_exceptions=(psycopg.errors.DatabaseError,),
            job_name="database-metadata",
            shutdown_callback=shutdown_cb,
        )
        self._check = check
        self._config = config
        self._collect_pg_settings_enabled = is_affirmative(config.settings_metadata_config.get('enabled', False))
        self._pg_settings_cached = None
        self._time_since_last_settings_query = 0
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
        self.report_postgres_metadata()
        self._conn_pool.prune_connections()

    @tracked_method(agent_check_getter=agent_check_getter)
    def report_postgres_metadata(self):
        # Only query for settings if configured to do so &&
        # don't report more often than the configured collection interval
        elapsed_s = time.time() - self._time_since_last_settings_query
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

    def _payload_pg_version(self):
        version = self._check.version
        if not version:
            return ""
        return 'v{major}.{minor}.{patch}'.format(major=version.major, minor=version.minor, patch=version.patch)

    @tracked_method(agent_check_getter=agent_check_getter)
    def _collect_postgres_settings(self):
        with self._conn_pool.get_connection(self._config.dbname, ttl_ms=self._conn_ttl_ms).cursor(
            row_factory=dict_row
        ) as cursor:
            self._log.debug("Running query [%s]", PG_SETTINGS_QUERY)
            self._time_since_last_settings_query = time.time()
            cursor.execute(PG_SETTINGS_QUERY)
            rows = cursor.fetchall()
            self._log.debug("Loaded %s rows from pg_settings", len(rows))
            return [dict(row) for row in rows]
