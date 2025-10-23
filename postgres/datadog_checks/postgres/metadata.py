# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import json
import re
import time

import psycopg
from psycopg.rows import dict_row

from .schemas import PostgresSchemaCollector

try:
    import datadog_agent  # type: ignore
except ImportError:
    from datadog_checks.base.stubs import datadog_agent

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datadog_checks.postgres import PostgreSql

from datadog_checks.base.utils.db.utils import DBMAsyncJob, default_json_event_encoding
from datadog_checks.base.utils.tracking import tracked_method
from datadog_checks.postgres.config_models import InstanceConfig

from .util import payload_pg_version

# PG_EXTENSION_INFO_QUERY is used to collect extension names and versions from
# the pg_extension table. Schema names and roles are retrieved from their re-
# spective catalog tables.
PG_EXTENSION_INFO_QUERY = """
SELECT
e.oid::text AS id,
e.extname AS name,
r.rolname AS owner,
ns.nspname AS schema_name,
e.extrelocatable AS relocatable,
e.extversion AS version
FROM pg_extension e
LEFT JOIN pg_namespace ns on e.extnamespace = ns.oid
     JOIN pg_roles r ON e.extowner = r.oid;
"""

# PG_SETTINGS_QUERY is used to collect all the settings from the pg_settings table
# Edge case: If source is 'session', it uses reset_val
# (which represents the value that the setting would revert to on session end or reset),
# otherwise, it uses the current setting value.
PG_SETTINGS_QUERY = """
SELECT
name,
case when source = 'session' then reset_val else setting end as setting,
source,
sourcefile,
pending_restart
FROM pg_settings
"""

PG_EXTENSIONS_QUERY = """
SELECT extname, nspname schemaname
FROM pg_extension left join pg_namespace on extnamespace = pg_namespace.oid;
"""

PG_EXTENSION_LOADER_QUERY = {
    'pg_trgm': "SELECT word_similarity('foo', 'bar');",
    'plpgsql': "DO $$ BEGIN PERFORM 1; END$$;",
    'pgcrypto': "SELECT armor('foo');",
    'hstore': "SELECT 'a=>1'::hstore;",
}


def agent_check_getter(self):
    return self._check


class PostgresMetadata(DBMAsyncJob):
    """
    Collects database metadata. Supports:
        1. cloud metadata collection for resource creations
        2. collection of pg_settings
    """

    def __init__(self, check: PostgreSql, config: InstanceConfig):
        self.pg_settings_ignored_patterns = list(config.collect_settings.ignored_settings_patterns)
        self.pg_settings_collection_interval = config.collect_settings.collection_interval
        # Extensions currently doesn't have a separate collection interval option
        self.pg_extensions_collection_interval = self.pg_settings_collection_interval
        self.schemas_collection_interval = config.collect_schemas.collection_interval

        # by default, send resources every 10 minutes
        self.collection_interval = min(
            self.pg_extensions_collection_interval,
            self.pg_settings_collection_interval,
            self.schemas_collection_interval,
        )

        super(PostgresMetadata, self).__init__(
            check,
            rate_limit=1 / float(self.collection_interval),
            run_sync=config.collect_settings.run_sync,
            enabled=config.collect_settings.enabled or config.collect_schemas.enabled,
            dbms="postgres",
            min_collection_interval=config.min_collection_interval,
            expected_db_exceptions=(psycopg.errors.DatabaseError,),
            job_name="database-metadata",
        )
        self._check = check
        self._config = config
        self.db_pool = self._check.db_pool
        self._collect_pg_settings_enabled = config.collect_settings.enabled
        self._collect_extensions_enabled = self._collect_pg_settings_enabled
        self._collect_schemas_enabled = config.collect_schemas.enabled
        self._schema_collector = PostgresSchemaCollector(check) if config.collect_schemas.enabled else None
        self._pg_settings_cached = None
        self._compiled_patterns_cache = {}
        self._extensions_cached = None
        self._time_since_last_extension_query = 0
        self._time_since_last_settings_query = 0
        self._last_schemas_query_time = 0
        self.column_buffer_size = 100_000
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

    def _get_compiled_pattern(self, pattern_str):
        """
        Get a compiled regex pattern from cache, compiling it if not already cached.
        """
        if pattern_str not in self._compiled_patterns_cache:
            self._compiled_patterns_cache[pattern_str] = re.compile(pattern_str)
        return self._compiled_patterns_cache[pattern_str]

    def run_job(self):
        # do not emit any dd.internal metrics for DBM specific check code
        self.tags = [t for t in self._tags if not t.startswith("dd.internal")]
        self._tags_no_db = [t for t in self.tags if not t.startswith("db:")]
        self.report_postgres_metadata()
        self.report_postgres_extensions()

    @tracked_method(agent_check_getter=agent_check_getter)
    def report_postgres_extensions(self):
        # Only query if configured, according to interval
        elapsed_s = time.time() - self._time_since_last_extension_query
        if elapsed_s >= self.pg_extensions_collection_interval and self._collect_extensions_enabled:
            self._extensions_cached = self._collect_postgres_extensions()
            event = {
                "host": self._check.reported_hostname,
                "database_instance": self._check.database_identifier,
                "agent_version": datadog_agent.get_version(),
                "dbms": "postgres",
                "kind": "pg_extension",
                "collection_interval": self.pg_extensions_collection_interval,
                "dbms_version": payload_pg_version(self._check.version),
                "tags": self._tags_no_db,
                "timestamp": time.time() * 1000,
                "cloud_metadata": self._check.cloud_metadata,
                "metadata": self._extensions_cached,
            }
            self._check.database_monitoring_metadata(json.dumps(event, default=default_json_event_encoding))

    @tracked_method(agent_check_getter=agent_check_getter)
    def _collect_postgres_extensions(self):
        if self._cancel_event.is_set():
            raise Exception("Job loop cancelled. Aborting query.")
        with self._check._get_main_db() as conn:
            with conn.cursor(row_factory=dict_row) as cursor:
                self._time_since_last_extension_query = time.time()

                # Get loaded extensions
                cursor.execute(PG_EXTENSION_INFO_QUERY)
                rows = cursor.fetchall()

                self._log.debug("Loaded %s rows from pg_extension", len(rows))
                return [dict(row) for row in rows]

    @tracked_method(agent_check_getter=agent_check_getter)
    def report_postgres_metadata(self):
        # Only query for settings if configured to do so &&
        # don't report more often than the configured collection interval
        elapsed_s = time.time() - self._time_since_last_settings_query
        if elapsed_s >= self.pg_settings_collection_interval and self._collect_pg_settings_enabled:
            self._pg_settings_cached = self._collect_postgres_settings()
            event = {
                "host": self._check.reported_hostname,
                "database_instance": self._check.database_identifier,
                "agent_version": datadog_agent.get_version(),
                "dbms": "postgres",
                "kind": "pg_settings",
                "collection_interval": self.pg_settings_collection_interval,
                "dbms_version": payload_pg_version(self._check.version),
                "tags": self._tags_no_db,
                "timestamp": time.time() * 1000,
                "cloud_metadata": self._check.cloud_metadata,
                "metadata": self._pg_settings_cached,
            }
            self._check.database_monitoring_metadata(json.dumps(event, default=default_json_event_encoding))

        if (
            self._collect_extensions_enabled
            and time.time() - self._last_schemas_query_time < self.schemas_collection_interval
        ):
            self._collect_postgres_schemas()

    @tracked_method(agent_check_getter=agent_check_getter)
    def _collect_postgres_schemas(self):
        started = self._schema_collector.collect_schemas()
        if not started:
            # TODO: Emit health event for over-long collection
            self._log.warning("Previous schema collection still in progress, skipping this collection")

    @tracked_method(agent_check_getter=agent_check_getter)
    def _collect_postgres_settings(self):
        if self._cancel_event.is_set():
            raise Exception("Job loop cancelled. Aborting query.")
        with self._check._get_main_db() as conn:
            with conn.cursor(row_factory=dict_row) as cursor:
                # Get loaded extensions
                cursor.execute(PG_EXTENSIONS_QUERY)
                rows = cursor.fetchall()
                query = PG_SETTINGS_QUERY
                for row in rows:
                    extension = row['extname']
                    if extension in PG_EXTENSION_LOADER_QUERY:
                        if row['schemaname'] in ['pg_catalog', 'public']:
                            query = PG_EXTENSION_LOADER_QUERY[extension] + "\n" + query
                        else:
                            self._log.warning(
                                "unable to collect settings for extension %s in schema %s",
                                extension,
                                row['schemaname'],
                            )
                    else:
                        self._log.warning("unable to collect settings for unknown extension %s", extension)

                if self.pg_settings_ignored_patterns:
                    query = query + " WHERE name NOT LIKE ALL(%s)"

                self._log.debug(
                    "Running query [%s] and patterns are %s",
                    query,
                    self.pg_settings_ignored_patterns,
                )
                self._time_since_last_settings_query = time.time()
                cursor.execute(query, (self.pg_settings_ignored_patterns,))
                # pg3 returns a set of results for each statement in the multiple statement query
                # We want to retrieve the last one that actually has the settings results
                rows = []
                has_more_results = True
                while has_more_results:
                    if cursor.pgresult.status == psycopg.pq.ExecStatus.TUPLES_OK:
                        rows = cursor.fetchall()
                    has_more_results = cursor.nextset()
                self._log.debug("Loaded %s rows from pg_settings", rows)
                self._log.debug("Loaded %s rows from pg_settings", len(rows))
                return rows
