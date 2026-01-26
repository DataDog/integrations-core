# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
from unittest import mock

import pytest
from semver import VersionInfo

from datadog_checks.postgres.migration_utils import (
    CHECK_TABLE_EXISTS_QUERY,
    GET_ALEMBIC_VERSION_QUERY,
    GET_GOLANG_MIGRATE_VERSION_QUERY,
    GET_PRISMA_MIGRATIONS_QUERY,
    GET_TYPEORM_MIGRATIONS_QUERY,
    collect_alembic_migration,
    collect_golang_migrate_migration,
    collect_prisma_migration,
    collect_typeorm_migration,
)
from datadog_checks.postgres.migrations import (
    COLLECT_DDL_EVENTS_QUERY,
    DATABASE_INFORMATION_QUERY,
    MARK_DDL_EVENTS_PROCESSED_QUERY,
    PRUNE_DDL_EVENTS_QUERY,
    SETUP_DDL_FUNCTION_QUERY,
    SETUP_DDL_TABLE_QUERY,
    SETUP_DDL_TRIGGER_QUERY,
    PostgresMigrationCollector,
)

pytestmark = pytest.mark.unit


@pytest.fixture
def mock_check():
    check = mock.MagicMock()
    check.reported_hostname = "test-host"
    check.database_identifier = "test-db-instance"
    check.version = VersionInfo(14, 0, 0)
    check.cloud_metadata = {"cloud": "aws"}
    check._get_main_db.return_value.__enter__ = mock.MagicMock()
    check._get_main_db.return_value.__exit__ = mock.MagicMock()
    return check


@pytest.fixture
def mock_config():
    config = mock.MagicMock()
    config.collect_migrations.enabled = True
    config.collect_migrations.collection_interval = 300
    config.collect_migrations.ddl_tracking_enabled = True
    config.collect_migrations.migration_tools = ("alembic", "golang-migrate", "prisma", "typeorm")
    config.collect_migrations.run_sync = True
    config.collect_migrations.exclude_databases = None
    config.collect_migrations.include_databases = None
    config.collect_migrations.ddl_events_ttl = 7
    config.min_collection_interval = 15
    return config


class TestPostgresMigrationCollectorInit:
    def test_init_with_valid_config(self, mock_check, mock_config):
        collector = PostgresMigrationCollector(mock_check, mock_config)

        assert collector.collection_interval == 300
        assert collector._ddl_tracking_enabled is True
        assert collector._migration_tools == ("alembic", "golang-migrate", "prisma", "typeorm")
        assert collector._ddl_setup_complete == {}
        assert collector._exclude_databases == ()
        assert collector._include_databases == ()

    def test_init_with_ddl_tracking_disabled(self, mock_check, mock_config):
        mock_config.collect_migrations.ddl_tracking_enabled = False
        collector = PostgresMigrationCollector(mock_check, mock_config)

        assert collector._ddl_tracking_enabled is False

    def test_init_with_database_filters(self, mock_check, mock_config):
        mock_config.collect_migrations.exclude_databases = ("template.*", "test_db")
        mock_config.collect_migrations.include_databases = ("prod_.*", "staging_.*")
        collector = PostgresMigrationCollector(mock_check, mock_config)

        assert collector._exclude_databases == ("template.*", "test_db")
        assert collector._include_databases == ("prod_.*", "staging_.*")


class TestCheckTableExists:
    def test_table_exists(self, mock_check, mock_config):
        from datadog_checks.postgres.migration_utils import check_table_exists

        mock_cursor = mock.MagicMock()
        mock_cursor.fetchone.return_value = {"exists": True}

        result = check_table_exists(mock_cursor, "test_table")

        mock_cursor.execute.assert_called_once_with(CHECK_TABLE_EXISTS_QUERY, ("test_table",))
        assert result is True

    def test_table_not_exists(self, mock_check, mock_config):
        from datadog_checks.postgres.migration_utils import check_table_exists

        mock_cursor = mock.MagicMock()
        mock_cursor.fetchone.return_value = {"exists": False}

        result = check_table_exists(mock_cursor, "nonexistent_table")

        assert result is False

    def test_table_exists_no_result(self, mock_check, mock_config):
        from datadog_checks.postgres.migration_utils import check_table_exists

        mock_cursor = mock.MagicMock()
        mock_cursor.fetchone.return_value = None

        result = check_table_exists(mock_cursor, "test_table")

        assert result is False


class TestCollectAlembicMigration:
    def test_alembic_table_exists_with_version(self):
        mock_cursor = mock.MagicMock()
        mock_cursor.fetchone.side_effect = [
            {"exists": True},
            {"version_num": "abc123def456"},
        ]

        result = collect_alembic_migration(mock_cursor)

        assert result["detected"] is True
        assert result["version"] == "abc123def456"
        assert result["dirty"] is None
        assert result["migrations"] == []

    def test_alembic_table_not_exists(self):
        mock_cursor = mock.MagicMock()
        mock_cursor.fetchone.return_value = {"exists": False}

        result = collect_alembic_migration(mock_cursor)

        assert result["detected"] is False
        assert result["version"] is None
        assert result["dirty"] is None
        assert result["migrations"] == []

    def test_alembic_table_exists_no_version(self):
        mock_cursor = mock.MagicMock()
        mock_cursor.fetchone.side_effect = [
            {"exists": True},
            None,
        ]

        result = collect_alembic_migration(mock_cursor)

        assert result["detected"] is True
        assert result["version"] is None
        assert result["dirty"] is None
        assert result["migrations"] == []


class TestCollectGolangMigrateMigration:
    def test_golang_migrate_table_exists(self):
        mock_cursor = mock.MagicMock()
        mock_cursor.fetchone.side_effect = [
            {"exists": True},
            {"version": 5, "dirty": False},
        ]

        result = collect_golang_migrate_migration(mock_cursor)

        assert result["detected"] is True
        assert result["version"] == 5
        assert result["dirty"] is False
        assert result["migrations"] == []

    def test_golang_migrate_dirty_migration(self):
        mock_cursor = mock.MagicMock()
        mock_cursor.fetchone.side_effect = [
            {"exists": True},
            {"version": 3, "dirty": True},
        ]

        result = collect_golang_migrate_migration(mock_cursor)

        assert result["detected"] is True
        assert result["version"] == 3
        assert result["dirty"] is True
        assert result["migrations"] == []

    def test_golang_migrate_table_not_exists(self):
        mock_cursor = mock.MagicMock()
        mock_cursor.fetchone.return_value = {"exists": False}

        result = collect_golang_migrate_migration(mock_cursor)

        assert result["detected"] is False
        assert result["version"] is None
        assert result["dirty"] is None
        assert result["migrations"] == []


class TestCollectPrismaMigration:
    def test_prisma_table_exists_with_migrations(self):
        mock_cursor = mock.MagicMock()
        mock_cursor.fetchone.return_value = {"exists": True}
        mock_cursor.fetchall.return_value = [
            {
                "id": "abc123",
                "migration_name": "20240101_init",
                "finished_at": "2024-01-01T00:00:00Z",
                "applied_steps_count": 1,
            },
            {
                "id": "def456",
                "migration_name": "20240102_add_users",
                "finished_at": "2024-01-02T00:00:00Z",
                "applied_steps_count": 1,
            },
        ]

        result = collect_prisma_migration(mock_cursor)

        assert result["detected"] is True
        assert result["version"] == "20240101_init"
        assert result["dirty"] is None
        assert len(result["migrations"]) == 2
        assert result["migrations"][0]["migration_name"] == "20240101_init"

    def test_prisma_table_not_exists(self):
        mock_cursor = mock.MagicMock()
        mock_cursor.fetchone.return_value = {"exists": False}

        result = collect_prisma_migration(mock_cursor)

        assert result["detected"] is False
        assert result["version"] is None
        assert result["dirty"] is None
        assert result["migrations"] == []


class TestCollectTypeormMigration:
    def test_typeorm_table_exists_with_migrations(self):
        mock_cursor = mock.MagicMock()
        mock_cursor.fetchone.return_value = {"exists": True}
        mock_cursor.fetchall.return_value = [
            {"id": 1, "name": "InitialMigration1704067200000", "timestamp": 1704067200000},
            {"id": 2, "name": "AddUsersTable1704153600000", "timestamp": 1704153600000},
        ]

        result = collect_typeorm_migration(mock_cursor)

        assert result["detected"] is True
        assert result["version"] == "InitialMigration1704067200000"
        assert result["dirty"] is None
        assert len(result["migrations"]) == 2
        assert result["migrations"][0]["name"] == "InitialMigration1704067200000"

    def test_typeorm_table_not_exists(self):
        mock_cursor = mock.MagicMock()
        mock_cursor.fetchone.return_value = {"exists": False}

        result = collect_typeorm_migration(mock_cursor)

        assert result["detected"] is False
        assert result["version"] is None
        assert result["dirty"] is None
        assert result["migrations"] == []


class TestCreateMigrationEventPayload:
    def test_create_payload_with_all_data(self, mock_check, mock_config):
        collector = PostgresMigrationCollector(mock_check, mock_config)
        collector._tags_no_db = ["env:prod", "service:test"]

        ddl_events = [
            {
                "event_id": "550e8400-e29b-41d4-a716-446655440000",
                "event_time": "2026-01-21T10:00:00Z",
                "event_type": "CREATE TABLE",
                "object_type": "table",
                "object_identity": "public.users",
                "schema_name": "public",
                "ddl_command": "CREATE TABLE users (id INT)",
                "executed_by": "app_user",
                "application_name": "alembic",
                "client_addr": "10.0.0.1",
                "backend_pid": 12345,
                "transaction_id": 987654321,
                "session_id": "12345-2026-01-21T09:00:00",
            }
        ]
        migration_tools = {
            "alembic": {"detected": True, "version": "abc123", "dirty": None, "migrations": []},
            "golang_migrate": {"detected": False, "version": None, "dirty": None, "migrations": []},
            "prisma": {"detected": False, "version": None, "dirty": None, "migrations": []},
            "typeorm": {"detected": False, "version": None, "dirty": None, "migrations": []},
        }
        database_name = "test_database"
        collection_timestamp = 1705838000000.0

        with mock.patch("datadog_checks.postgres.migrations.datadog_agent.get_version", return_value="7.50.0"):
            with mock.patch("datadog_checks.postgres.migrations.time.time", return_value=1705838400.0):
                payload = collector._create_migration_event_payload(
                    ddl_events, migration_tools, database_name, collection_timestamp
                )

        assert payload["host"] == "test-host"
        assert payload["database_instance"] == "test-db-instance"
        assert payload["agent_version"] == "7.50.0"
        assert payload["dbms"] == "postgres"
        assert payload["kind"] == "pg_migrations"
        assert payload["collection_interval"] == 300
        assert payload["tags"] == ["env:prod", "service:test", "db:test_database"]
        assert payload["timestamp"] == 1705838400000.0
        assert payload["cloud_metadata"] == {"cloud": "aws"}
        assert payload["database_name"] == "test_database"
        assert payload["collection_timestamp"] == 1705838000000.0
        assert payload["metadata"]["ddl_events"] == ddl_events
        assert payload["metadata"]["migration_tools"] == migration_tools

    def test_create_payload_with_empty_data(self, mock_check, mock_config):
        collector = PostgresMigrationCollector(mock_check, mock_config)
        collector._tags_no_db = []

        with mock.patch("datadog_checks.postgres.migrations.datadog_agent.get_version", return_value="7.50.0"):
            with mock.patch("datadog_checks.postgres.migrations.time.time", return_value=1705838400.0):
                payload = collector._create_migration_event_payload([], {}, "mydb", 1705838000000.0)

        assert payload["metadata"]["ddl_events"] == []
        assert payload["metadata"]["migration_tools"] == {}
        assert payload["database_name"] == "mydb"
        assert payload["collection_timestamp"] == 1705838000000.0


class TestCollectMigrationVersions:
    def test_collect_all_migration_tools(self, mock_check, mock_config):
        collector = PostgresMigrationCollector(mock_check, mock_config)

        mock_cursor = mock.MagicMock()
        mock_cursor.fetchone.return_value = {"exists": False}

        result = collector._collect_migration_versions(mock_cursor)

        assert "alembic" in result
        assert "golang_migrate" in result
        assert "prisma" in result
        assert "typeorm" in result

    def test_collect_only_specified_tools(self, mock_check, mock_config):
        mock_config.collect_migrations.migration_tools = ("alembic",)
        collector = PostgresMigrationCollector(mock_check, mock_config)

        mock_cursor = mock.MagicMock()
        mock_cursor.fetchone.return_value = {"exists": False}

        result = collector._collect_migration_versions(mock_cursor)

        assert "alembic" in result
        assert "golang_migrate" not in result
        assert "prisma" not in result
        assert "typeorm" not in result


class TestGetDatabases:
    def test_get_databases_no_filters(self, mock_check, mock_config):
        collector = PostgresMigrationCollector(mock_check, mock_config)

        mock_cursor = mock.MagicMock()
        mock_cursor.fetchall.return_value = [
            {"id": "1", "name": "postgres", "encoding": "UTF8", "owner": "postgres", "description": None},
            {"id": "2", "name": "myapp", "encoding": "UTF8", "owner": "app_user", "description": None},
        ]

        mock_conn = mock.MagicMock()
        mock_conn.cursor.return_value.__enter__ = mock.MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = mock.MagicMock(return_value=False)
        mock_check._get_main_db.return_value.__enter__.return_value = mock_conn

        result = collector._get_databases()

        assert len(result) == 2
        assert result[0]["name"] == "postgres"
        assert result[1]["name"] == "myapp"

    def test_get_databases_with_exclude_filter(self, mock_check, mock_config):
        mock_config.collect_migrations.exclude_databases = ("test_.*",)
        collector = PostgresMigrationCollector(mock_check, mock_config)

        mock_cursor = mock.MagicMock()
        mock_cursor.fetchall.return_value = [
            {"id": "1", "name": "prod_db", "encoding": "UTF8", "owner": "postgres", "description": None}
        ]

        mock_conn = mock.MagicMock()
        mock_conn.cursor.return_value.__enter__ = mock.MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = mock.MagicMock(return_value=False)
        mock_check._get_main_db.return_value.__enter__.return_value = mock_conn

        collector._get_databases()

        executed_query = mock_cursor.execute.call_args[0][0]
        assert "datname !~ 'test_.*'" in executed_query

    def test_get_databases_with_include_filter(self, mock_check, mock_config):
        mock_config.collect_migrations.include_databases = ("prod_.*", "staging_.*")
        collector = PostgresMigrationCollector(mock_check, mock_config)

        mock_cursor = mock.MagicMock()
        mock_cursor.fetchall.return_value = [
            {"id": "1", "name": "prod_app", "encoding": "UTF8", "owner": "postgres", "description": None}
        ]

        mock_conn = mock.MagicMock()
        mock_conn.cursor.return_value.__enter__ = mock.MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = mock.MagicMock(return_value=False)
        mock_check._get_main_db.return_value.__enter__.return_value = mock_conn

        collector._get_databases()

        executed_query = mock_cursor.execute.call_args[0][0]
        assert "datname ~ 'prod_.*'" in executed_query
        assert "datname ~ 'staging_.*'" in executed_query
        assert " OR " in executed_query

    def test_get_databases_with_autodiscovery(self, mock_check, mock_config):
        collector = PostgresMigrationCollector(mock_check, mock_config)
        mock_check.autodiscovery = mock.MagicMock()
        mock_check.autodiscovery.get_items.return_value = ["db1", "db2"]

        mock_cursor = mock.MagicMock()
        mock_cursor.fetchall.return_value = [
            {"id": "1", "name": "db1", "encoding": "UTF8", "owner": "postgres", "description": None}
        ]

        mock_conn = mock.MagicMock()
        mock_conn.cursor.return_value.__enter__ = mock.MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = mock.MagicMock(return_value=False)
        mock_check._get_main_db.return_value.__enter__.return_value = mock_conn

        collector._get_databases()

        executed_query = mock_cursor.execute.call_args[0][0]
        assert "datname IN ('db1', 'db2')" in executed_query


class TestSQLQueries:
    def test_ddl_table_setup_query_format(self):
        assert "datadog_schema_events" in SETUP_DDL_TABLE_QUERY
        assert "CREATE TABLE IF NOT EXISTS" in SETUP_DDL_TABLE_QUERY
        assert "event_id UUID" in SETUP_DDL_TABLE_QUERY
        assert "gen_random_uuid()" in SETUP_DDL_TABLE_QUERY
        assert "event_time" in SETUP_DDL_TABLE_QUERY
        assert "event_type" in SETUP_DDL_TABLE_QUERY
        assert "processed" in SETUP_DDL_TABLE_QUERY
        assert "backend_pid" in SETUP_DDL_TABLE_QUERY
        assert "transaction_id" in SETUP_DDL_TABLE_QUERY
        assert "session_id" in SETUP_DDL_TABLE_QUERY

    def test_ddl_function_query_format(self):
        assert "datadog_capture_ddl_event" in SETUP_DDL_FUNCTION_QUERY
        assert "event_trigger" in SETUP_DDL_FUNCTION_QUERY
        assert "pg_event_trigger_ddl_commands" in SETUP_DDL_FUNCTION_QUERY
        assert "pg_backend_pid()" in SETUP_DDL_FUNCTION_QUERY
        assert "txid_current()" in SETUP_DDL_FUNCTION_QUERY
        assert "v_session_id" in SETUP_DDL_FUNCTION_QUERY

    def test_ddl_trigger_query_format(self):
        assert "datadog_ddl_trigger" in SETUP_DDL_TRIGGER_QUERY
        assert "ddl_command_end" in SETUP_DDL_TRIGGER_QUERY

    def test_collect_ddl_events_query_format(self):
        assert "SELECT" in COLLECT_DDL_EVENTS_QUERY
        assert "event_id" in COLLECT_DDL_EVENTS_QUERY
        assert "backend_pid" in COLLECT_DDL_EVENTS_QUERY
        assert "transaction_id" in COLLECT_DDL_EVENTS_QUERY
        assert "session_id" in COLLECT_DDL_EVENTS_QUERY
        assert "processed = FALSE" in COLLECT_DDL_EVENTS_QUERY
        assert "LIMIT 1000" in COLLECT_DDL_EVENTS_QUERY

    def test_mark_processed_query_format(self):
        assert "UPDATE" in MARK_DDL_EVENTS_PROCESSED_QUERY
        assert "processed = TRUE" in MARK_DDL_EVENTS_PROCESSED_QUERY
        assert "event_id" in MARK_DDL_EVENTS_PROCESSED_QUERY

    def test_migration_tool_queries_exist(self):
        assert "alembic_version" in GET_ALEMBIC_VERSION_QUERY
        assert "schema_migrations" in GET_GOLANG_MIGRATE_VERSION_QUERY
        assert "_prisma_migrations" in GET_PRISMA_MIGRATIONS_QUERY
        assert "migrations" in GET_TYPEORM_MIGRATIONS_QUERY

    def test_database_information_query_format(self):
        assert "pg_catalog.pg_database" in DATABASE_INFORMATION_QUERY
        assert "datname" in DATABASE_INFORMATION_QUERY
        assert "template%" in DATABASE_INFORMATION_QUERY

    def test_prune_ddl_events_query_format(self):
        assert "DELETE FROM" in PRUNE_DDL_EVENTS_QUERY
        assert "datadog_schema_events" in PRUNE_DDL_EVENTS_QUERY
        assert "processed = TRUE" in PRUNE_DDL_EVENTS_QUERY
        assert "event_time" in PRUNE_DDL_EVENTS_QUERY
        assert "INTERVAL" in PRUNE_DDL_EVENTS_QUERY


class TestDDLEventsTTL:
    def test_init_with_ddl_events_ttl(self, mock_check, mock_config):
        collector = PostgresMigrationCollector(mock_check, mock_config)
        assert collector._ddl_events_ttl == 7

    def test_init_with_ddl_events_ttl_disabled(self, mock_check, mock_config):
        mock_config.collect_migrations.ddl_events_ttl = None
        collector = PostgresMigrationCollector(mock_check, mock_config)
        assert collector._ddl_events_ttl is None

    def test_init_with_ddl_events_ttl_zero(self, mock_check, mock_config):
        mock_config.collect_migrations.ddl_events_ttl = 0
        collector = PostgresMigrationCollector(mock_check, mock_config)
        assert collector._ddl_events_ttl == 0


class TestPruneOldDDLEvents:
    def test_prune_with_ttl_disabled(self, mock_check, mock_config):
        mock_config.collect_migrations.ddl_events_ttl = None
        collector = PostgresMigrationCollector(mock_check, mock_config)
        mock_conn = mock.MagicMock()

        result = collector._prune_old_ddl_events(mock_conn, "test_db")

        assert result == 0
        mock_conn.cursor.assert_not_called()

    def test_prune_with_ttl_zero(self, mock_check, mock_config):
        mock_config.collect_migrations.ddl_events_ttl = 0
        collector = PostgresMigrationCollector(mock_check, mock_config)
        mock_conn = mock.MagicMock()

        result = collector._prune_old_ddl_events(mock_conn, "test_db")

        assert result == 0
        mock_conn.cursor.assert_not_called()

    def test_prune_with_valid_ttl(self, mock_check, mock_config):
        mock_config.collect_migrations.ddl_events_ttl = 7
        collector = PostgresMigrationCollector(mock_check, mock_config)

        mock_cursor = mock.MagicMock()
        mock_cursor.rowcount = 5

        mock_conn = mock.MagicMock()
        mock_conn.cursor.return_value.__enter__ = mock.MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = mock.MagicMock(return_value=False)

        result = collector._prune_old_ddl_events(mock_conn, "test_db")

        assert result == 5
        mock_cursor.execute.assert_called_once()
        executed_query = mock_cursor.execute.call_args[0][0]
        assert "DELETE FROM" in executed_query
        assert "7" in executed_query
        mock_conn.commit.assert_called_once()

    def test_prune_with_no_events_to_prune(self, mock_check, mock_config):
        mock_config.collect_migrations.ddl_events_ttl = 7
        collector = PostgresMigrationCollector(mock_check, mock_config)

        mock_cursor = mock.MagicMock()
        mock_cursor.rowcount = 0

        mock_conn = mock.MagicMock()
        mock_conn.cursor.return_value.__enter__ = mock.MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = mock.MagicMock(return_value=False)

        result = collector._prune_old_ddl_events(mock_conn, "test_db")

        assert result == 0
        mock_conn.commit.assert_called_once()

    def test_prune_handles_exception(self, mock_check, mock_config):
        mock_config.collect_migrations.ddl_events_ttl = 7
        collector = PostgresMigrationCollector(mock_check, mock_config)

        mock_cursor = mock.MagicMock()
        mock_cursor.execute.side_effect = Exception("Database error")

        mock_conn = mock.MagicMock()
        mock_conn.cursor.return_value.__enter__ = mock.MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = mock.MagicMock(return_value=False)

        result = collector._prune_old_ddl_events(mock_conn, "test_db")

        assert result == 0
