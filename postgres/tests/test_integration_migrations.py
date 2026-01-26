# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from concurrent.futures.thread import ThreadPoolExecutor

import pytest

from datadog_checks.base.utils.db.utils import DBMAsyncJob

from .common import DB_NAME, USER
from .utils import _get_superconn, run_one_check

pytestmark = [pytest.mark.integration, pytest.mark.usefixtures('dd_environment')]


@pytest.fixture
def migrations_instance(pg_instance):
    pg_instance['dbm'] = True
    pg_instance['min_collection_interval'] = 0.1
    pg_instance['query_samples'] = {'enabled': False}
    pg_instance['query_activity'] = {'enabled': False}
    pg_instance['query_metrics'] = {'enabled': False}
    pg_instance['collect_settings'] = {'enabled': False}
    pg_instance['collect_schemas'] = {'enabled': False}
    pg_instance['collect_migrations'] = {
        'enabled': True,
        'run_sync': True,
        'collection_interval': 0.1,
        'ddl_tracking_enabled': False,
        'migration_tools': ['alembic', 'golang-migrate', 'prisma', 'typeorm'],
    }
    return pg_instance


@pytest.fixture(autouse=True)
def stop_orphaned_threads():
    DBMAsyncJob.executor.shutdown(wait=True)
    DBMAsyncJob.executor = ThreadPoolExecutor()


@pytest.fixture
def setup_alembic_table(pg_instance):
    conn = _get_superconn(pg_instance)
    with conn.cursor() as cursor:
        cursor.execute("DROP TABLE IF EXISTS alembic_version")
        cursor.execute("CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL PRIMARY KEY)")
        cursor.execute("INSERT INTO alembic_version (version_num) VALUES ('abc123def456')")
        cursor.execute(f"GRANT SELECT ON alembic_version TO {USER}")
    yield
    with conn.cursor() as cursor:
        cursor.execute("DROP TABLE IF EXISTS alembic_version")
    conn.close()


@pytest.fixture
def setup_golang_migrate_table(pg_instance):
    conn = _get_superconn(pg_instance)
    with conn.cursor() as cursor:
        cursor.execute("DROP TABLE IF EXISTS schema_migrations")
        cursor.execute("CREATE TABLE schema_migrations (version BIGINT NOT NULL PRIMARY KEY, dirty BOOLEAN NOT NULL)")
        cursor.execute("INSERT INTO schema_migrations (version, dirty) VALUES (20260121100000, FALSE)")
        cursor.execute(f"GRANT SELECT ON schema_migrations TO {USER}")
    yield
    with conn.cursor() as cursor:
        cursor.execute("DROP TABLE IF EXISTS schema_migrations")
    conn.close()


@pytest.fixture
def setup_prisma_table(pg_instance):
    conn = _get_superconn(pg_instance)
    with conn.cursor() as cursor:
        cursor.execute("DROP TABLE IF EXISTS _prisma_migrations")
        cursor.execute("""
            CREATE TABLE _prisma_migrations (
                id VARCHAR(36) NOT NULL PRIMARY KEY,
                checksum VARCHAR(64) NOT NULL,
                finished_at TIMESTAMPTZ,
                migration_name VARCHAR(255) NOT NULL,
                logs TEXT,
                rolled_back_at TIMESTAMPTZ,
                started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                applied_steps_count INTEGER NOT NULL DEFAULT 0
            )
        """)
        cursor.execute("""
            INSERT INTO _prisma_migrations (id, checksum, finished_at, migration_name, applied_steps_count)
            VALUES ('abc123', 'checksum123', NOW(), '20260121_init', 1)
        """)
        cursor.execute(f"GRANT SELECT ON _prisma_migrations TO {USER}")
    yield
    with conn.cursor() as cursor:
        cursor.execute("DROP TABLE IF EXISTS _prisma_migrations")
    conn.close()


@pytest.fixture
def setup_typeorm_table(pg_instance):
    conn = _get_superconn(pg_instance)
    with conn.cursor() as cursor:
        cursor.execute("DROP TABLE IF EXISTS migrations")
        cursor.execute("""
            CREATE TABLE migrations (
                id SERIAL PRIMARY KEY,
                timestamp BIGINT NOT NULL,
                name VARCHAR(255) NOT NULL
            )
        """)
        cursor.execute(
            "INSERT INTO migrations (timestamp, name) VALUES (1705824000000, 'InitialMigration1705824000000')"
        )
        cursor.execute(f"GRANT SELECT ON migrations TO {USER}")
    yield
    with conn.cursor() as cursor:
        cursor.execute("DROP TABLE IF EXISTS migrations")
    conn.close()


@pytest.fixture
def setup_ddl_infrastructure(pg_instance):
    conn = _get_superconn(pg_instance)
    with conn.cursor() as cursor:
        cursor.execute("DROP EVENT TRIGGER IF EXISTS datadog_ddl_trigger")
        cursor.execute("DROP FUNCTION IF EXISTS datadog_capture_ddl_event() CASCADE")
        cursor.execute("DROP TABLE IF EXISTS datadog_schema_events")
        cursor.execute("""
            CREATE TABLE datadog_schema_events (
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
            )
        """)
        cursor.execute(f"GRANT SELECT, UPDATE, DELETE ON datadog_schema_events TO {USER}")
        cursor.execute("""
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
                    INSERT INTO datadog_schema_events (
                        event_type, object_type, object_identity, schema_name, ddl_command,
                        executed_by, application_name, client_addr, backend_pid, transaction_id, session_id
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
            $$ LANGUAGE plpgsql
        """)
        cursor.execute("""
            CREATE EVENT TRIGGER datadog_ddl_trigger ON ddl_command_end
            EXECUTE PROCEDURE datadog_capture_ddl_event()
        """)
    yield
    with conn.cursor() as cursor:
        cursor.execute("DROP EVENT TRIGGER IF EXISTS datadog_ddl_trigger")
        cursor.execute("DROP FUNCTION IF EXISTS datadog_capture_ddl_event() CASCADE")
        cursor.execute("DROP TABLE IF EXISTS datadog_schema_events")
    conn.close()


@pytest.fixture
def cleanup_ddl_infrastructure(pg_instance):
    conn = _get_superconn(pg_instance)
    with conn.cursor() as cursor:
        cursor.execute("DROP EVENT TRIGGER IF EXISTS datadog_ddl_trigger")
        cursor.execute("DROP FUNCTION IF EXISTS datadog_capture_ddl_event() CASCADE")
        cursor.execute("DROP TABLE IF EXISTS datadog_schema_events")
    conn.close()
    yield
    conn = _get_superconn(pg_instance)
    with conn.cursor() as cursor:
        cursor.execute("DROP EVENT TRIGGER IF EXISTS datadog_ddl_trigger")
        cursor.execute("DROP FUNCTION IF EXISTS datadog_capture_ddl_event() CASCADE")
        cursor.execute("DROP TABLE IF EXISTS datadog_schema_events")
    conn.close()


def test_collect_migrations_event_structure(integration_check, migrations_instance, aggregator):
    check = integration_check(migrations_instance)
    run_one_check(check)
    dbm_metadata = aggregator.get_event_platform_events("dbm-metadata")
    event = next((e for e in dbm_metadata if e['kind'] == 'pg_migrations'), None)

    assert event is not None
    assert event['host'] == "stubbed.hostname"
    assert event['dbms'] == "postgres"
    assert event['kind'] == "pg_migrations"
    assert 'timestamp' in event
    assert 'collection_interval' in event
    assert 'database_instance' in event
    assert 'metadata' in event
    assert 'ddl_events' in event['metadata']
    assert 'migration_tools' in event['metadata']
    assert 'database_name' in event
    assert event['database_name'] is not None
    assert 'collection_timestamp' in event
    assert event['collection_timestamp'] is not None
    assert any('db:' in tag for tag in event.get('tags', []))


def test_collect_alembic_version(integration_check, migrations_instance, aggregator, setup_alembic_table):
    check = integration_check(migrations_instance)
    run_one_check(check)
    dbm_metadata = aggregator.get_event_platform_events("dbm-metadata")
    event = next((e for e in dbm_metadata if e['kind'] == 'pg_migrations' and e.get('database_name') == DB_NAME), None)

    assert event is not None
    alembic = event['metadata']['migration_tools'].get('alembic', {})
    assert alembic.get('detected') is True
    assert alembic.get('version') == 'abc123def456'
    assert alembic.get('dirty') is None
    assert alembic.get('migrations') == []


def test_collect_golang_migrate_version(integration_check, migrations_instance, aggregator, setup_golang_migrate_table):
    check = integration_check(migrations_instance)
    run_one_check(check)
    dbm_metadata = aggregator.get_event_platform_events("dbm-metadata")
    event = next((e for e in dbm_metadata if e['kind'] == 'pg_migrations' and e.get('database_name') == DB_NAME), None)

    assert event is not None
    golang_migrate = event['metadata']['migration_tools'].get('golang_migrate', {})
    assert golang_migrate.get('detected') is True
    assert golang_migrate.get('version') == 20260121100000
    assert golang_migrate.get('dirty') is False
    assert golang_migrate.get('migrations') == []


def test_collect_prisma_migrations(integration_check, migrations_instance, aggregator, setup_prisma_table):
    check = integration_check(migrations_instance)
    run_one_check(check)
    dbm_metadata = aggregator.get_event_platform_events("dbm-metadata")
    event = next((e for e in dbm_metadata if e['kind'] == 'pg_migrations' and e.get('database_name') == DB_NAME), None)

    assert event is not None
    prisma = event['metadata']['migration_tools'].get('prisma', {})
    assert prisma.get('detected') is True
    assert prisma.get('version') == '20260121_init'
    assert prisma.get('dirty') is None
    assert len(prisma.get('migrations', [])) == 1
    assert prisma['migrations'][0]['migration_name'] == '20260121_init'


def test_collect_typeorm_migrations(integration_check, migrations_instance, aggregator, setup_typeorm_table):
    check = integration_check(migrations_instance)
    run_one_check(check)
    dbm_metadata = aggregator.get_event_platform_events("dbm-metadata")
    event = next((e for e in dbm_metadata if e['kind'] == 'pg_migrations' and e.get('database_name') == DB_NAME), None)

    assert event is not None
    typeorm = event['metadata']['migration_tools'].get('typeorm', {})
    assert typeorm.get('detected') is True
    assert typeorm.get('version') == 'InitialMigration1705824000000'
    assert typeorm.get('dirty') is None
    assert len(typeorm.get('migrations', [])) == 1
    assert typeorm['migrations'][0]['name'] == 'InitialMigration1705824000000'


def test_ddl_event_capture(integration_check, migrations_instance, aggregator, pg_instance, setup_ddl_infrastructure):
    import time

    migrations_instance['collect_migrations']['ddl_tracking_enabled'] = True
    check = integration_check(migrations_instance)
    run_one_check(check, cancel=False)
    aggregator.reset()

    conn = _get_superconn(pg_instance)
    with conn.cursor() as cursor:
        cursor.execute("DROP TABLE IF EXISTS test_ddl_capture")
        cursor.execute("CREATE TABLE test_ddl_capture (id SERIAL PRIMARY KEY, name TEXT)")
    conn.close()

    time.sleep(0.2)
    run_one_check(check, cancel=True)
    dbm_metadata = aggregator.get_event_platform_events("dbm-metadata")
    event = next((e for e in dbm_metadata if e['kind'] == 'pg_migrations' and e.get('database_name') == DB_NAME), None)

    assert event is not None
    ddl_events = event['metadata'].get('ddl_events', [])
    create_table_events = [
        e
        for e in ddl_events
        if 'test_ddl_capture' in (e.get('object_identity') or '') and e.get('object_type') == 'table'
    ]
    assert len(create_table_events) >= 1
    create_event = create_table_events[0]
    assert create_event['event_type'] == 'CREATE TABLE'
    assert create_event['object_type'] == 'table'
    assert 'executed_by' in create_event
    assert 'event_id' in create_event
    assert create_event['event_id'] is not None
    assert 'backend_pid' in create_event
    assert 'transaction_id' in create_event
    assert 'session_id' in create_event

    conn = _get_superconn(pg_instance)
    with conn.cursor() as cursor:
        cursor.execute("DROP TABLE IF EXISTS test_ddl_capture")
    conn.close()


def test_ddl_tracking_disabled(
    integration_check, migrations_instance, aggregator, pg_instance, cleanup_ddl_infrastructure
):
    check = integration_check(migrations_instance)
    run_one_check(check)

    dbm_metadata = aggregator.get_event_platform_events("dbm-metadata")
    event = next((e for e in dbm_metadata if e['kind'] == 'pg_migrations'), None)

    assert event is not None
    ddl_events = event['metadata'].get('ddl_events', [])
    assert ddl_events == []

    conn = _get_superconn(pg_instance)
    with conn.cursor() as cursor:
        cursor.execute("SELECT EXISTS (SELECT FROM pg_tables WHERE tablename = 'datadog_schema_events')")
        result = cursor.fetchone()
        assert result[0] is False
    conn.close()


def test_no_migration_tables_present(integration_check, migrations_instance, aggregator):
    check = integration_check(migrations_instance)
    run_one_check(check)
    dbm_metadata = aggregator.get_event_platform_events("dbm-metadata")
    event = next((e for e in dbm_metadata if e['kind'] == 'pg_migrations'), None)

    assert event is not None
    migration_tools = event['metadata']['migration_tools']
    for tool_key in ['alembic', 'golang_migrate', 'prisma', 'typeorm']:
        assert migration_tools[tool_key].get('detected') is False


def test_specific_migration_tools_only(
    integration_check, migrations_instance, aggregator, setup_alembic_table, setup_golang_migrate_table
):
    migrations_instance['collect_migrations']['migration_tools'] = ['alembic']
    check = integration_check(migrations_instance)
    run_one_check(check)

    dbm_metadata = aggregator.get_event_platform_events("dbm-metadata")
    event = next((e for e in dbm_metadata if e['kind'] == 'pg_migrations' and e.get('database_name') == DB_NAME), None)

    assert event is not None
    migration_tools = event['metadata']['migration_tools']
    assert 'alembic' in migration_tools
    assert migration_tools['alembic'].get('detected') is True
    assert 'golang_migrate' not in migration_tools
    assert 'prisma' not in migration_tools
    assert 'typeorm' not in migration_tools


def test_include_databases_filter(integration_check, migrations_instance, aggregator, setup_alembic_table):
    migrations_instance['collect_migrations']['include_databases'] = ['datadog_test']
    check = integration_check(migrations_instance)
    run_one_check(check)

    dbm_metadata = aggregator.get_event_platform_events("dbm-metadata")
    events = [e for e in dbm_metadata if e['kind'] == 'pg_migrations']

    assert len(events) >= 1
    event = events[0]
    assert event['database_name'] == 'datadog_test'


def test_exclude_databases_filter(integration_check, migrations_instance, aggregator, setup_alembic_table):
    migrations_instance['collect_migrations']['exclude_databases'] = ['datadog_test']
    check = integration_check(migrations_instance)
    run_one_check(check)

    dbm_metadata = aggregator.get_event_platform_events("dbm-metadata")
    events = [e for e in dbm_metadata if e['kind'] == 'pg_migrations']

    for event in events:
        assert event.get('database_name') != 'datadog_test'


def test_collection_timestamp_shared_across_databases(integration_check, migrations_instance, aggregator):
    check = integration_check(migrations_instance)
    run_one_check(check)

    dbm_metadata = aggregator.get_event_platform_events("dbm-metadata")
    events = [e for e in dbm_metadata if e['kind'] == 'pg_migrations']

    if len(events) > 1:
        first_ts = events[0].get('collection_timestamp')
        for event in events[1:]:
            assert event.get('collection_timestamp') == first_ts


def test_ddl_events_ttl_pruning(
    integration_check, migrations_instance, aggregator, pg_instance, setup_ddl_infrastructure
):
    import time

    # Set a very low TTL (0 days) to test immediate pruning
    migrations_instance['collect_migrations']['ddl_tracking_enabled'] = True
    migrations_instance['collect_migrations']['ddl_events_ttl'] = 0

    check = integration_check(migrations_instance)
    run_one_check(check, cancel=False)
    aggregator.reset()

    # Create a DDL event and mark it as processed manually
    conn = _get_superconn(pg_instance)
    with conn.cursor() as cursor:
        # Insert a processed event with an old timestamp
        cursor.execute("""
            INSERT INTO datadog_schema_events
            (event_type, object_type, object_identity, schema_name, executed_by, processed, event_time)
            VALUES ('TEST', 'table', 'public.old_test', 'public', 'test_user', TRUE, NOW() - INTERVAL '10 days')
        """)
        # Verify the event was inserted
        cursor.execute("SELECT COUNT(*) FROM datadog_schema_events WHERE object_identity = 'public.old_test'")
        count_before = cursor.fetchone()[0]
        assert count_before == 1
    conn.close()

    # With TTL=0, pruning is disabled
    time.sleep(0.1)
    run_one_check(check, cancel=False)

    # Verify the event was NOT pruned (TTL=0 disables pruning)
    conn = _get_superconn(pg_instance)
    with conn.cursor() as cursor:
        cursor.execute("SELECT COUNT(*) FROM datadog_schema_events WHERE object_identity = 'public.old_test'")
        count_after = cursor.fetchone()[0]
        assert count_after == 1  # Event should still exist since TTL=0 disables pruning
    conn.close()


def test_ddl_events_ttl_pruning_active(
    integration_check, migrations_instance, aggregator, pg_instance, setup_ddl_infrastructure
):
    import time

    # Enable pruning with a positive TTL
    migrations_instance['collect_migrations']['ddl_tracking_enabled'] = True
    migrations_instance['collect_migrations']['ddl_events_ttl'] = 1  # 1 day TTL

    check = integration_check(migrations_instance)
    run_one_check(check, cancel=False)
    aggregator.reset()

    # Insert a processed event with a very old timestamp (older than TTL)
    conn = _get_superconn(pg_instance)
    with conn.cursor() as cursor:
        cursor.execute("""
            INSERT INTO datadog_schema_events
            (event_type, object_type, object_identity, schema_name, executed_by, processed, event_time)
            VALUES ('TEST', 'table', 'public.very_old_test', 'public', 'test_user', TRUE, NOW() - INTERVAL '30 days')
        """)
        # Insert a recent event that should NOT be pruned
        cursor.execute("""
            INSERT INTO datadog_schema_events
            (event_type, object_type, object_identity, schema_name, executed_by, processed, event_time)
            VALUES ('TEST', 'table', 'public.recent_test', 'public', 'test_user', TRUE, NOW())
        """)
    conn.close()

    time.sleep(0.1)
    run_one_check(check, cancel=True)

    # Verify the old event was pruned but the recent one remains
    conn = _get_superconn(pg_instance)
    with conn.cursor() as cursor:
        cursor.execute("SELECT COUNT(*) FROM datadog_schema_events WHERE object_identity = 'public.very_old_test'")
        old_count = cursor.fetchone()[0]
        assert old_count == 0  # Old event should be pruned

        cursor.execute("SELECT COUNT(*) FROM datadog_schema_events WHERE object_identity = 'public.recent_test'")
        recent_count = cursor.fetchone()[0]
        assert recent_count == 1  # Recent event should remain
    conn.close()


def test_schema_collection_includes_migration_context(integration_check, pg_instance, aggregator, setup_alembic_table):
    """Test that schema collection includes migration_context when collect_migrations is enabled."""
    instance = pg_instance.copy()
    instance['dbm'] = True
    instance['min_collection_interval'] = 0.1
    instance['query_samples'] = {'enabled': False}
    instance['query_activity'] = {'enabled': False}
    instance['query_metrics'] = {'enabled': False}
    instance['collect_settings'] = {'enabled': False}
    instance['collect_schemas'] = {'enabled': True}
    instance['collect_migrations'] = {
        'enabled': True,
        'run_sync': True,
        'collection_interval': 0.1,
        'ddl_tracking_enabled': False,
        'migration_tools': ['alembic'],
    }

    check = integration_check(instance)
    run_one_check(check)

    dbm_metadata = aggregator.get_event_platform_events("dbm-metadata")
    schema_events = [e for e in dbm_metadata if e['kind'] == 'pg_databases']

    # Find the schema event for datadog_test database
    datadog_test_events = [e for e in schema_events if any(db.get('name') == DB_NAME for db in e.get('metadata', []))]

    assert len(datadog_test_events) >= 1
    event = datadog_test_events[0]

    # Find the database entry that has migration_context
    for db_entry in event.get('metadata', []):
        if db_entry.get('name') == DB_NAME:
            assert 'migration_context' in db_entry
            assert 'alembic' in db_entry['migration_context']
            assert db_entry['migration_context']['alembic']['version'] == 'abc123def456'
            break
    else:
        pytest.fail("Could not find datadog_test database entry with migration_context")


def test_schema_collection_no_migration_context_when_disabled(
    integration_check, pg_instance, aggregator, setup_alembic_table
):
    """Test that schema collection does not include migration_context when collect_migrations is disabled."""
    instance = pg_instance.copy()
    instance['dbm'] = True
    instance['min_collection_interval'] = 0.1
    instance['query_samples'] = {'enabled': False}
    instance['query_activity'] = {'enabled': False}
    instance['query_metrics'] = {'enabled': False}
    instance['collect_settings'] = {'enabled': False}
    instance['collect_schemas'] = {'enabled': True}
    # collect_migrations is not enabled

    check = integration_check(instance)
    run_one_check(check)

    dbm_metadata = aggregator.get_event_platform_events("dbm-metadata")
    schema_events = [e for e in dbm_metadata if e['kind'] == 'pg_databases']

    assert len(schema_events) >= 1

    # Verify no database entry has migration_context
    for event in schema_events:
        for db_entry in event.get('metadata', []):
            assert 'migration_context' not in db_entry, f"migration_context should not be present: {db_entry}"
