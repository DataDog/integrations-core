# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import time
from contextlib import closing
from operator import attrgetter

import pymysql

from datadog_checks.mysql.cursor import CommenterDictCursor
from datadog_checks.mysql.databases_data import DEFAULT_DATABASES_DATA_COLLECTION_INTERVAL, DatabasesData

from .util import connect_with_autocommit

try:
    import datadog_agent
except ImportError:
    from ..stubs import datadog_agent

from datadog_checks.base import is_affirmative
from datadog_checks.base.utils.db.utils import (
    DBMAsyncJob,
    default_json_event_encoding,
)
from datadog_checks.base.utils.serialization import json
from datadog_checks.base.utils.tracking import tracked_method

# default pg_settings collection interval in seconds
DEFAULT_SETTINGS_COLLECTION_INTERVAL = 600

MARIADB_TABLE_NAME = "information_schema.GLOBAL_VARIABLES"
MYSQL_TABLE_NAME = "performance_schema.global_variables"

SETTINGS_QUERY = """
SELECT
    variable_name,
    variable_value
FROM
    {table_name}
"""


class MySQLMetadata(DBMAsyncJob):
    """
    Collects database metadata. Supports:
    1. collection of performance_schema.global_variables
    2. collection of databases(schemas) data
    """

    def __init__(self, check, config, connection_args):
        self._databases_data_enabled = is_affirmative(config.schemas_config.get("enabled", False))
        self._databases_data_collection_interval = config.schemas_config.get(
            "collection_interval", DEFAULT_DATABASES_DATA_COLLECTION_INTERVAL
        )
        self._settings_enabled = is_affirmative(config.settings_config.get('enabled', False))

        self._settings_collection_interval = float(
            config.settings_config.get('collection_interval', DEFAULT_SETTINGS_COLLECTION_INTERVAL)
        )

        if self._databases_data_enabled and not self._settings_enabled:
            self.collection_interval = self._databases_data_collection_interval
        elif not self._databases_data_enabled and self._settings_enabled:
            self.collection_interval = self._settings_collection_interval
        else:
            self.collection_interval = min(self._databases_data_collection_interval, self._settings_collection_interval)

        self.enabled = self._databases_data_enabled or self._settings_enabled

        super(MySQLMetadata, self).__init__(
            check,
            rate_limit=1 / self.collection_interval,
            run_sync=is_affirmative(config.settings_config.get('run_sync', False)),
            enabled=self.enabled,
            min_collection_interval=config.min_collection_interval,
            dbms="mysql",
            expected_db_exceptions=(pymysql.err.DatabaseError,),
            job_name="database-metadata",
            shutdown_callback=self._close_db_conn,
        )
        self._check = check
        self._config = config
        self._version_processed = False
        self._connection_args = connection_args
        self._db = None
        self._databases_data = DatabasesData(self, check, config)
        self._last_settings_collection_time = 0
        self._last_databases_collection_time = 0

    def get_db_connection(self):
        """
        lazy reconnect db
        pymysql connections are not thread safe so we can't reuse the same connection from the main check
        :return:
        """
        if not self._db:
            self._db = connect_with_autocommit(**self._connection_args)
        return self._db

    def _close_db_conn(self):
        if self._db:
            try:
                self._db.close()
            except Exception:
                self._log.debug("Failed to close db connection", exc_info=1)
            finally:
                self._db = None

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

    def run_job(self):
        elapsed_time_settings = time.time() - self._last_settings_collection_time
        if self._settings_enabled and elapsed_time_settings >= self._settings_collection_interval:
            self._last_settings_collection_time = time.time()
            try:
                self.report_mysql_metadata()
            except Exception as e:
                self._log.error(
                    """An error occurred while collecting database settings.
                                These may be unavailable until the error is resolved. The error - {}""".format(
                        e
                    )
                )

        elapsed_time_databases = time.time() - self._last_databases_collection_time
        if self._databases_data_enabled and elapsed_time_databases >= self._databases_data_collection_interval:
            self._last_databases_collection_time = time.time()
            try:
                self._databases_data._collect_databases_data(self._tags)
            except Exception as e:
                self._log.error(
                    """An error occurred while collecting schema data.
                                These may be unavailable until the error is resolved. The error - {}""".format(
                        e
                    )
                )

    def shut_down(self):
        self._databases_data.shut_down()

    @tracked_method(agent_check_getter=attrgetter('_check'))
    def report_mysql_metadata(self):
        settings = []
        table_name = (
            MYSQL_TABLE_NAME
            if not self._check.is_mariadb and self._check.version.version_compatible((5, 7, 0))
            else MARIADB_TABLE_NAME
        )
        query = SETTINGS_QUERY.format(table_name=table_name)
        with closing(self.get_db_connection().cursor(CommenterDictCursor)) as cursor:
            self._cursor_run(
                cursor,
                query,
            )
            rows = cursor.fetchall()
            settings = [dict(row) for row in rows]
        event = {
            "host": self._check.resolved_hostname,
            "agent_version": datadog_agent.get_version(),
            "dbms": "mysql",
            "kind": "mysql_variables",
            "collection_interval": self.collection_interval,
            'dbms_version': self._check.version.version + '+' + self._check.version.build,
            "tags": self._tags,
            "timestamp": time.time() * 1000,
            "cloud_metadata": self._config.cloud_metadata,
            "metadata": settings,
        }
        self._check.database_monitoring_metadata(json.dumps(event, default=default_json_event_encoding))
