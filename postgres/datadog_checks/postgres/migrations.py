# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import contextlib
import json
import time
from typing import TYPE_CHECKING

import psycopg
from psycopg.rows import dict_row

try:
    import datadog_agent
except ImportError:
    from datadog_checks.base.stubs import datadog_agent

if TYPE_CHECKING:
    from datadog_checks.postgres import PostgreSql

from datadog_checks.base.utils.db.utils import DBMAsyncJob, default_json_event_encoding
from datadog_checks.base.utils.tracking import tracked_method

from .migration_utils import (
    SUPPORTED_MIGRATION_TOOLS,
    collect_alembic_migration,
    collect_golang_migrate_migration,
    collect_prisma_migration,
    collect_typeorm_migration,
)
from .util import payload_pg_version

DDL_EVENTS_TABLE = "datadog_schema_events"

DATABASE_INFORMATION_QUERY = """
SELECT db.oid::text                  AS id,
       datname                       AS name,
       pg_encoding_to_char(encoding) AS encoding,
       rolname                       AS owner,
       shobj_description(db.oid, 'pg_database') AS description
FROM   pg_catalog.pg_database db
       JOIN pg_roles a
         ON datdba = a.oid
        WHERE datname NOT LIKE 'template%'
"""

SETUP_DDL_TABLE_QUERY = f"""
CREATE TABLE IF NOT EXISTS {DDL_EVENTS_TABLE} (
    event_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_time TIMESTAMPTZ DEFAULT NOW(),
    event_type TEXT NOT NULL,
    object_type TEXT,
    object_identity TEXT,
    schema_name TEXT,
    ddl_command TEXT,
    executed_by TEXT,
    application_name TEXT,
    client_addr INET,
    backend_pid INTEGER,
    transaction_id BIGINT,
    session_id TEXT,
    processed BOOLEAN DEFAULT FALSE
);
"""

SETUP_DDL_FUNCTION_QUERY = f"""
CREATE OR REPLACE FUNCTION datadog_capture_ddl_event()
RETURNS event_trigger AS $$
DECLARE
    obj record;
    v_session_id TEXT;
BEGIN
    SELECT pg_backend_pid()::text || '-' || COALESCE(backend_start::text, 'unknown')
    INTO v_session_id
    FROM pg_stat_activity
    WHERE pid = pg_backend_pid();

    FOR obj IN SELECT * FROM pg_event_trigger_ddl_commands()
    LOOP
        INSERT INTO {DDL_EVENTS_TABLE} (
            event_type, object_type, object_identity, schema_name, ddl_command,
            executed_by, application_name, client_addr,
            backend_pid, transaction_id, session_id
        ) VALUES (
            TG_TAG,
            obj.object_type,
            obj.object_identity,
            obj.schema_name,
            current_query(),
            current_user,
            current_setting('application_name', true),
            inet_client_addr(),
            pg_backend_pid(),
            txid_current(),
            v_session_id
        );
    END LOOP;
END;
$$ LANGUAGE plpgsql;
"""

SETUP_DDL_TRIGGER_QUERY = """
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_event_trigger WHERE evtname = 'datadog_ddl_trigger') THEN
        CREATE EVENT TRIGGER datadog_ddl_trigger ON ddl_command_end
        EXECUTE PROCEDURE datadog_capture_ddl_event();
    END IF;
END;
$$;
"""

CHECK_DDL_TABLE_EXISTS_QUERY = f"""
SELECT EXISTS (
    SELECT FROM pg_tables WHERE tablename = '{DDL_EVENTS_TABLE}'
);
"""

COLLECT_DDL_EVENTS_QUERY = f"""
SELECT event_id, event_time, event_type, object_type, object_identity, schema_name,
       ddl_command, executed_by, application_name, client_addr,
       backend_pid, transaction_id, session_id
FROM {DDL_EVENTS_TABLE}
WHERE processed = FALSE
ORDER BY event_time ASC
LIMIT 1000;
"""

MARK_DDL_EVENTS_PROCESSED_QUERY = f"""
UPDATE {DDL_EVENTS_TABLE}
SET processed = TRUE
WHERE event_id = ANY(%s);
"""

PRUNE_DDL_EVENTS_QUERY = f"""
DELETE FROM {DDL_EVENTS_TABLE}
WHERE processed = TRUE
AND event_time < NOW() - INTERVAL '%s days';
"""


def agent_check_getter(self):
    return self._check


class PostgresMigrationCollector(DBMAsyncJob):
    def __init__(self, check: PostgreSql, config):
        self.collection_interval = config.collect_migrations.collection_interval
        self._ddl_tracking_enabled = config.collect_migrations.ddl_tracking_enabled
        # Auto-detect all supported tools by default, or use specified filter
        self._migration_tools = config.collect_migrations.migration_tools or SUPPORTED_MIGRATION_TOOLS
        self._exclude_databases = config.collect_migrations.exclude_databases or ()
        self._include_databases = config.collect_migrations.include_databases or ()
        self._ddl_events_ttl = config.collect_migrations.ddl_events_ttl

        super(PostgresMigrationCollector, self).__init__(
            check,
            rate_limit=1 / float(self.collection_interval),
            run_sync=config.collect_migrations.run_sync,
            enabled=config.collect_migrations.enabled,
            dbms="postgres",
            min_collection_interval=config.min_collection_interval,
            expected_db_exceptions=(psycopg.errors.DatabaseError,),
            job_name="migrations-collector",
        )
        self._check = check
        self._config = config
        self._ddl_setup_complete = {}
        self._tags_no_db = None
        self.tags = None

    def run_job(self):
        self.tags = [t for t in self._tags if not t.startswith("dd.internal")]
        self._tags_no_db = [t for t in self.tags if not t.startswith("db:")]
        self._collect_migrations()

    def _get_databases(self) -> list[dict]:
        with self._check._get_main_db() as conn:
            with conn.cursor(row_factory=dict_row) as cursor:
                query = DATABASE_INFORMATION_QUERY
                for exclude_regex in self._exclude_databases:
                    query += " AND datname !~ '{}'".format(exclude_regex)
                if self._include_databases:
                    query += f" AND ({
                        ' OR '.join(f"datname ~ '{include_regex}'" for include_regex in self._include_databases)
                    })"
                if self._check.autodiscovery:
                    autodiscovery_databases = self._check.autodiscovery.get_items()
                    if autodiscovery_databases:
                        query += " AND datname IN ({})".format(", ".join(f"'{db}'" for db in autodiscovery_databases))
                cursor.execute(query)
                return cursor.fetchall()

    @contextlib.contextmanager
    def _get_db_cursor(self, database_name: str):
        with self._check.db_pool.get_connection(database_name) as conn:
            with conn.cursor(row_factory=dict_row) as cursor:
                yield conn, cursor

    @tracked_method(agent_check_getter=agent_check_getter)
    def _collect_migrations(self):
        if self._cancel_event.is_set():
            raise Exception("Job loop cancelled. Aborting query.")

        collection_timestamp = time.time() * 1000
        databases = self._get_databases()
        self._log.debug("Collecting migrations from %d databases", len(databases))

        for db_row in databases:
            if self._cancel_event.is_set():
                raise Exception("Job loop cancelled. Aborting query.")

            database_name = db_row["name"]
            try:
                with self._get_db_cursor(database_name) as (conn, cursor):
                    ddl_events = []
                    if self._ddl_tracking_enabled:
                        self._ensure_ddl_tracking_setup(conn, database_name)
                        ddl_events = self._collect_ddl_events(conn, database_name)
                        self._prune_old_ddl_events(conn, database_name)

                    migration_tools = self._collect_migration_versions(cursor)

                    event = self._create_migration_event_payload(
                        ddl_events, migration_tools, database_name, collection_timestamp
                    )
                    self._check.database_monitoring_metadata(json.dumps(event, default=default_json_event_encoding))
            except Exception as e:
                self._log.error("Failed to collect migrations from database %s: %s", database_name, e)

    def _ensure_ddl_tracking_setup(self, conn, database_name: str):
        if self._ddl_setup_complete.get(database_name):
            return

        try:
            with conn.cursor(row_factory=dict_row) as cursor:
                cursor.execute(CHECK_DDL_TABLE_EXISTS_QUERY)
                result = cursor.fetchone()
                table_exists = result["exists"] if result else False

                if not table_exists:
                    self._log.info("Setting up DDL tracking infrastructure in database %s", database_name)
                    cursor.execute(SETUP_DDL_TABLE_QUERY)
                    cursor.execute(SETUP_DDL_FUNCTION_QUERY)
                    cursor.execute(SETUP_DDL_TRIGGER_QUERY)
                    conn.commit()
                    self._log.info("DDL tracking infrastructure created successfully in database %s", database_name)

            self._ddl_setup_complete[database_name] = True
        except psycopg.errors.InsufficientPrivilege as e:
            self._log.warning(
                "Insufficient privileges to create DDL tracking infrastructure in database %s: %s", database_name, e
            )
            self._ddl_setup_complete[database_name] = True
        except Exception as e:
            self._log.error("Failed to setup DDL tracking in database %s: %s", database_name, e)
            raise

    def _collect_ddl_events(self, conn, database_name: str) -> list[dict]:
        events = []
        try:
            with conn.cursor(row_factory=dict_row) as cursor:
                cursor.execute(COLLECT_DDL_EVENTS_QUERY)
                rows = cursor.fetchall()

                if rows:
                    event_ids = [row["event_id"] for row in rows]
                    for row in rows:
                        event = dict(row)
                        if event.get("event_id") is not None:
                            event["event_id"] = str(event["event_id"])
                        if event.get("event_time") is not None:
                            event["event_time"] = event["event_time"].isoformat()
                        if event.get("client_addr") is not None:
                            event["client_addr"] = str(event["client_addr"])
                        events.append(event)
                    cursor.execute(MARK_DDL_EVENTS_PROCESSED_QUERY, (event_ids,))
                    conn.commit()
                    self._log.debug(
                        "Collected and marked %d DDL events as processed from database %s", len(events), database_name
                    )

        except Exception as e:
            self._log.error("Failed to collect DDL events from database %s: %s", database_name, e)

        return events

    def _prune_old_ddl_events(self, conn, database_name: str) -> int:
        if self._ddl_events_ttl is None or self._ddl_events_ttl <= 0:
            return 0

        pruned_count = 0
        try:
            with conn.cursor() as cursor:
                cursor.execute(PRUNE_DDL_EVENTS_QUERY % int(self._ddl_events_ttl))
                pruned_count = cursor.rowcount
                conn.commit()
                if pruned_count > 0:
                    self._log.debug(
                        "Pruned %d old DDL events from database %s (TTL: %d days)",
                        pruned_count,
                        database_name,
                        int(self._ddl_events_ttl),
                    )
        except Exception as e:
            self._log.error("Failed to prune old DDL events from database %s: %s", database_name, e)

        return pruned_count

    def _collect_migration_versions(self, cursor) -> dict:
        migration_tools = {}

        if "alembic" in self._migration_tools:
            migration_tools["alembic"] = collect_alembic_migration(cursor, self._log)

        if "golang-migrate" in self._migration_tools:
            migration_tools["golang_migrate"] = collect_golang_migrate_migration(cursor, self._log)

        if "prisma" in self._migration_tools:
            migration_tools["prisma"] = collect_prisma_migration(cursor, self._log)

        if "typeorm" in self._migration_tools:
            migration_tools["typeorm"] = collect_typeorm_migration(cursor, self._log)

        return migration_tools

    def _create_migration_event_payload(
        self, ddl_events: list[dict], migration_tools: dict, database_name: str, collection_timestamp: float
    ) -> dict:
        return {
            "host": self._check.reported_hostname,
            "database_instance": self._check.database_identifier,
            "agent_version": datadog_agent.get_version(),
            "dbms": "postgres",
            "kind": "pg_migrations",
            "collection_interval": self.collection_interval,
            "dbms_version": payload_pg_version(self._check.version),
            "tags": self._tags_no_db + [f"db:{database_name}"],
            "timestamp": time.time() * 1000,
            "cloud_metadata": self._check.cloud_metadata,
            "database_name": database_name,
            "collection_timestamp": collection_timestamp,
            "metadata": {
                "ddl_events": ddl_events,
                "migration_tools": migration_tools,
            },
        }
