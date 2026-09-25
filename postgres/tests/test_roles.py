# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from concurrent.futures.thread import ThreadPoolExecutor

import pytest

from datadog_checks.base.utils.db.utils import DBMAsyncJob
from datadog_checks.postgres.role_collector import PostgresRoleCollector, RoleSnapshotEmitter
from datadog_checks.postgres.version_utils import V13, V15

from .utils import _get_superconn, requires_over_14, requires_over_15, run_one_check

pytestmark = [pytest.mark.integration, pytest.mark.usefixtures('dd_environment')]


@pytest.fixture(autouse=True)
def stop_orphaned_threads():
    DBMAsyncJob.executor.shutdown(wait=True)
    DBMAsyncJob.executor = ThreadPoolExecutor()


@pytest.fixture
def roles_instance(pg_instance):
    pg_instance['dbm'] = True
    pg_instance['min_collection_interval'] = 0.1
    pg_instance['query_samples'] = {'enabled': False}
    pg_instance['query_activity'] = {'enabled': False}
    pg_instance['query_metrics'] = {'enabled': False}
    pg_instance['collect_settings'] = {'enabled': False, 'run_sync': True}
    pg_instance['collect_schemas'] = {'enabled': False}
    pg_instance['collect_column_statistics'] = {'enabled': False}
    pg_instance['collect_roles'] = {
        'enabled': True,
        'collection_interval': 600,
        'include_databases': ['^datadog_test$'],
    }
    return pg_instance


@pytest.fixture
def role_catalog(roles_instance):
    with _get_superconn(roles_instance) as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                CREATE ROLE dd_role_obs_owner NOLOGIN;
                CREATE ROLE dd_role_obs_reader NOINHERIT LOGIN CONNECTION LIMIT 3
                    VALID UNTIL '2030-01-01 00:00:00+00';
                CREATE ROLE dd_role_obs_member NOINHERIT;
                CREATE ROLE dd_role_obs_grantor NOLOGIN;
                CREATE ROLE dd_role_obs_granted NOLOGIN;
                CREATE ROLE dd_role_obs_never_expires NOLOGIN VALID UNTIL 'infinity';
                CREATE ROLE dd_role_obs_bypass_rls NOLOGIN BYPASSRLS;
                GRANT dd_role_obs_reader TO datadog;
                GRANT dd_role_obs_reader TO dd_role_obs_member WITH ADMIN OPTION;
                GRANT dd_role_obs_reader TO dd_role_obs_grantor WITH ADMIN OPTION;
                SET ROLE dd_role_obs_grantor;
                GRANT dd_role_obs_reader TO dd_role_obs_granted;
                RESET ROLE;
                ALTER ROLE dd_role_obs_reader IN DATABASE datadog_test SET statement_timeout = '5s';
                CREATE SCHEMA dd_role_obs AUTHORIZATION dd_role_obs_owner;
                CREATE TABLE dd_role_obs.items (id integer);
                ALTER TABLE dd_role_obs.items OWNER TO dd_role_obs_owner;
                CREATE TABLE dd_role_obs.partitioned_items (id integer) PARTITION BY RANGE (id);
                ALTER TABLE dd_role_obs.partitioned_items OWNER TO dd_role_obs_owner;
                CREATE SEQUENCE dd_role_obs.item_sequence;
                ALTER SEQUENCE dd_role_obs.item_sequence OWNER TO dd_role_obs_owner;
                CREATE VIEW dd_role_obs.item_view AS SELECT id FROM dd_role_obs.items;
                ALTER VIEW dd_role_obs.item_view OWNER TO dd_role_obs_owner;
                CREATE VIEW dd_role_obs.invoker_view AS SELECT id FROM dd_role_obs.items;
                ALTER VIEW dd_role_obs.invoker_view OWNER TO dd_role_obs_owner;
                CREATE VIEW dd_role_obs.invoker_view_on AS SELECT id FROM dd_role_obs.items;
                ALTER VIEW dd_role_obs.invoker_view_on OWNER TO dd_role_obs_owner;
                CREATE VIEW dd_role_obs.invoker_view_one AS SELECT id FROM dd_role_obs.items;
                ALTER VIEW dd_role_obs.invoker_view_one OWNER TO dd_role_obs_owner;
                CREATE MATERIALIZED VIEW dd_role_obs.item_summary AS
                    SELECT count(*) AS item_count FROM dd_role_obs.items;
                ALTER MATERIALIZED VIEW dd_role_obs.item_summary OWNER TO dd_role_obs_owner;
                CREATE PROCEDURE dd_role_obs.refresh_items()
                    LANGUAGE sql AS 'DELETE FROM dd_role_obs.items WHERE false';
                ALTER PROCEDURE dd_role_obs.refresh_items() OWNER TO dd_role_obs_owner;
                CREATE FOREIGN DATA WRAPPER dd_role_obs_fdw NO HANDLER;
                CREATE SERVER dd_role_obs_server FOREIGN DATA WRAPPER dd_role_obs_fdw;
                CREATE FOREIGN TABLE dd_role_obs.foreign_items (id integer) SERVER dd_role_obs_server;
                ALTER FOREIGN TABLE dd_role_obs.foreign_items OWNER TO dd_role_obs_owner;
                GRANT USAGE ON SCHEMA dd_role_obs TO dd_role_obs_reader;
                GRANT SELECT ON dd_role_obs.item_view TO PUBLIC;
                GRANT SELECT ON dd_role_obs.items TO dd_role_obs_reader WITH GRANT OPTION;
                ALTER DEFAULT PRIVILEGES FOR ROLE dd_role_obs_owner IN SCHEMA dd_role_obs
                    GRANT SELECT ON TABLES TO dd_role_obs_reader;
                ALTER DEFAULT PRIVILEGES FOR ROLE dd_role_obs_owner
                    GRANT EXECUTE ON FUNCTIONS TO dd_role_obs_reader WITH GRANT OPTION;
                CREATE FUNCTION dd_role_obs.count_items() RETURNS bigint
                    LANGUAGE sql SECURITY DEFINER
                    AS 'SELECT count(*) FROM dd_role_obs.items';
                ALTER FUNCTION dd_role_obs.count_items() OWNER TO dd_role_obs_owner;
                CREATE AGGREGATE dd_role_obs.item_total(integer) (
                    SFUNC = int4pl, STYPE = integer, INITCOND = '0'
                );
                ALTER AGGREGATE dd_role_obs.item_total(integer) OWNER TO dd_role_obs_owner;
                GRANT EXECUTE ON FUNCTION dd_role_obs.item_total(integer) TO dd_role_obs_reader;
                DO $$
                BEGIN
                    IF current_setting('server_version_num')::integer >= 150000 THEN
                        EXECUTE 'ALTER VIEW dd_role_obs.invoker_view SET (security_invoker = true)';
                        -- Postgres stores reloptions verbatim, so each accepted boolean
                        -- spelling shows up differently in pg_class.reloptions.
                        EXECUTE 'ALTER VIEW dd_role_obs.invoker_view_on SET (security_invoker = on)';
                        EXECUTE 'ALTER VIEW dd_role_obs.invoker_view_one SET (security_invoker = 1)';
                        EXECUTE 'ALTER DEFAULT PRIVILEGES FOR ROLE dd_role_obs_owner '
                            'GRANT USAGE ON SCHEMAS TO dd_role_obs_reader WITH GRANT OPTION';
                    END IF;
                    IF current_setting('server_version_num')::integer >= 160000 THEN
                        EXECUTE 'GRANT dd_role_obs_reader TO dd_role_obs_member WITH INHERIT FALSE';
                    END IF;
                END
                $$;
                """
            )
    yield
    with _get_superconn(roles_instance) as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                DROP SCHEMA IF EXISTS dd_role_obs CASCADE;
                DROP SERVER IF EXISTS dd_role_obs_server CASCADE;
                DROP FOREIGN DATA WRAPPER IF EXISTS dd_role_obs_fdw CASCADE;
                DROP OWNED BY dd_role_obs_reader;
                DROP OWNED BY dd_role_obs_member;
                DROP OWNED BY dd_role_obs_grantor;
                DROP OWNED BY dd_role_obs_granted;
                DROP OWNED BY dd_role_obs_never_expires;
                DROP OWNED BY dd_role_obs_bypass_rls;
                DROP OWNED BY dd_role_obs_owner;
                DROP ROLE IF EXISTS dd_role_obs_bypass_rls;
                DROP ROLE IF EXISTS dd_role_obs_never_expires;
                DROP ROLE IF EXISTS dd_role_obs_granted;
                DROP ROLE IF EXISTS dd_role_obs_grantor;
                DROP ROLE IF EXISTS dd_role_obs_member;
                DROP ROLE IF EXISTS dd_role_obs_reader;
                DROP ROLE IF EXISTS dd_role_obs_owner;
                """
            )


@pytest.mark.parametrize(
    'row_count, expected_payload_sizes',
    [
        (9_999, [9_999]),
        (10_000, [10_000, 0]),
        (10_001, [10_000, 1]),
    ],
)
def test_role_snapshot_emitter_chunk_boundaries(row_count, expected_payload_sizes):
    events = []
    emitter = RoleSnapshotEmitter(
        {'kind': 'pg_roles', 'collection_started_at': 1},
        ('roles', 'memberships'),
        events.append,
        10_000,
    )

    for index in range(row_count):
        array_name = 'roles' if index % 2 == 0 else 'memberships'
        emitter.append(array_name, {'index': index})
    emitter.flush_terminal()

    assert [len(event['roles']) + len(event['memberships']) for event in events] == expected_payload_sizes
    assert all(event['collection_started_at'] == 1 for event in events)
    assert all('collection_payloads_count' not in event for event in events[:-1])
    assert events[-1]['collection_payloads_count'] == len(events)


def test_role_snapshot_emitter_successful_empty_scope():
    events = []
    emitter = RoleSnapshotEmitter({'kind': 'pg_roles'}, ('roles', 'memberships'), events.append, 10_000)

    emitter.flush_terminal()

    assert events == [
        {
            'kind': 'pg_roles',
            'timestamp': events[0]['timestamp'],
            'roles': [],
            'memberships': [],
            'collection_payloads_count': 1,
        }
    ]


def test_role_snapshot_emitter_discard_does_not_complete_partial_snapshot():
    events = []
    emitter = RoleSnapshotEmitter({'kind': 'pg_roles'}, ('roles',), events.append, 2)

    emitter.append('roles', {'role_name': 'first'})
    emitter.append('roles', {'role_name': 'second'})
    emitter.append('roles', {'role_name': 'discarded'})
    emitter.discard()

    assert len(events) == 1
    assert [role['role_name'] for role in events[0]['roles']] == ['first', 'second']
    assert 'collection_payloads_count' not in events[0]


@requires_over_14
def test_collect_roles_payload_contract(integration_check, roles_instance, role_catalog, aggregator):
    check = integration_check(roles_instance)

    run_one_check(check)

    metadata = aggregator.get_event_platform_events('dbm-metadata')
    role_events = [event for event in metadata if event['kind'] == 'pg_roles']
    privilege_events = [event for event in metadata if event['kind'] == 'pg_role_privileges']
    assert len(role_events) == 1
    assert len(privilege_events) == 1

    role_event = role_events[0]
    assert role_event['database_instance']
    assert role_event['collection_payloads_count'] == 1
    assert role_event['collection_interval'] == 600
    assert role_event['roles']
    assert role_event['memberships']
    assert set(role_event['roles'][0]) == {
        'role_name',
        'role_oid',
        'is_super',
        'can_inherit',
        'can_create_role',
        'can_create_db',
        'can_login',
        'is_replication',
        'can_bypass_rls',
        'conn_limit',
        'valid_until',
    }
    assert set(role_event['memberships'][0]) == {
        'group_role_name',
        'member_role_name',
        'grantor_role_name',
        'admin_option',
        'member_can_inherit',
    }
    reader = next(role for role in role_event['roles'] if role['role_name'] == 'dd_role_obs_reader')
    assert reader['can_inherit'] is False
    assert reader['conn_limit'] == 3
    assert reader['valid_until'] == '2030-01-01T00:00:00+00:00'
    assert reader['can_bypass_rls'] is False
    assert (
        next(role for role in role_event['roles'] if role['role_name'] == 'dd_role_obs_bypass_rls')['can_bypass_rls']
        is True
    )
    assert (
        next(role for role in role_event['roles'] if role['role_name'] == 'dd_role_obs_never_expires')['valid_until']
        == 'infinity'
    )
    member_grant = next(
        membership
        for membership in role_event['memberships']
        if membership['group_role_name'] == 'dd_role_obs_reader'
        and membership['member_role_name'] == 'dd_role_obs_member'
    )
    assert member_grant['admin_option'] is True
    assert member_grant['member_can_inherit'] is False
    assert any(
        membership['group_role_name'] == 'dd_role_obs_reader'
        and membership['member_role_name'] == 'dd_role_obs_granted'
        and membership['grantor_role_name'] == 'dd_role_obs_grantor'
        for membership in role_event['memberships']
    )
    assert {
        'role_name': 'dd_role_obs_reader',
        'database_name': 'datadog_test',
        'setting_name': 'statement_timeout',
        'setting_value': '5s',
    } in role_event['settings']

    privilege_event = privilege_events[0]
    assert privilege_event['database_name'] == 'datadog_test'
    assert privilege_event['collection_payloads_count'] == 1
    assert privilege_event['object_privileges']
    assert privilege_event['objects']
    assert set(privilege_event['object_privileges'][0]) == {
        'database_name',
        'object_type',
        'schema_name',
        'object_name',
        'column_name',
        'grantee_name',
        'grantor_name',
        'privilege',
        'is_grantable',
        'owner_name',
    }
    assert set(privilege_event['objects'][0]) == {
        'database_name',
        'object_type',
        'schema_name',
        'object_name',
        'object_oid',
        'owner_name',
        'is_security_definer',
        'security_invoker',
        'has_default_acl',
    }
    assert 'row_policies' not in privilege_event
    assert all('rls_enabled' not in obj and 'rls_forced' not in obj for obj in privilege_event['objects'])
    assert any(
        privilege['object_type'] == 'view'
        and privilege['schema_name'] == 'dd_role_obs'
        and privilege['object_name'] == 'item_view'
        and privilege['grantee_name'] == 'PUBLIC'
        and privilege['privilege'] == 'SELECT'
        for privilege in privilege_event['object_privileges']
    )
    assert any(
        privilege['schema_name'] == 'dd_role_obs'
        and privilege['object_name'] == 'items'
        and privilege['grantee_name'] == 'dd_role_obs_reader'
        and privilege['privilege'] == 'SELECT'
        and privilege['is_grantable']
        for privilege in privilege_event['object_privileges']
    )
    assert any(
        privilege['schema_name'] == 'dd_role_obs'
        and privilege['owner_name'] == 'dd_role_obs_owner'
        and privilege['grantee_name'] == 'dd_role_obs_reader'
        for privilege in privilege_event['default_privileges']
    )
    assert any(
        privilege['schema_name'] == ''
        and privilege['object_type'] == 'function'
        and privilege['grantee_name'] == 'dd_role_obs_reader'
        and privilege['is_grantable']
        for privilege in privilege_event['default_privileges']
    )
    if check.version >= V15:
        assert any(
            privilege['schema_name'] == ''
            and privilege['object_type'] == 'schema'
            and privilege['grantee_name'] == 'dd_role_obs_reader'
            and privilege['is_grantable']
            for privilege in privilege_event['default_privileges']
        )
    expected_object_types = {
        'aggregate',
        'foreign_table',
        'function',
        'materialized_view',
        'partitioned_table',
        'procedure',
        'sequence',
        'table',
        'view',
    }
    assert expected_object_types <= {
        obj['object_type'] for obj in privilege_event['objects'] if obj['schema_name'] == 'dd_role_obs'
    }
    assert any(
        obj['schema_name'] == 'dd_role_obs' and obj['object_name'] == 'count_items()' and obj['is_security_definer']
        for obj in privilege_event['objects']
    )
    assert any(
        obj['schema_name'] == 'dd_role_obs'
        and obj['object_name'] == 'item_total(integer)'
        and obj['object_type'] == 'aggregate'
        for obj in privilege_event['objects']
    )
    assert any(
        privilege['schema_name'] == 'dd_role_obs'
        and privilege['object_name'] == 'item_total(integer)'
        and privilege['object_type'] == 'aggregate'
        and privilege['grantee_name'] == 'dd_role_obs_reader'
        and privilege['privilege'] == 'EXECUTE'
        for privilege in privilege_event['object_privileges']
    )
    invoker_view = next(
        obj
        for obj in privilege_event['objects']
        if obj['schema_name'] == 'dd_role_obs' and obj['object_name'] == 'invoker_view'
    )
    assert invoker_view['security_invoker'] is (check.version >= V15)
    assert any(
        dependency['dependent_schema_name'] == 'dd_role_obs'
        and dependency['dependent_object_name'] == 'item_view'
        and dependency['referenced_object_name'] == 'items'
        for dependency in privilege_event['object_dependencies']
    )
    assert any(
        dependency['dependent_object_type'] == 'materialized_view'
        and dependency['dependent_schema_name'] == 'dd_role_obs'
        and dependency['dependent_object_name'] == 'item_summary'
        and dependency['referenced_object_type'] == 'table'
        and dependency['referenced_object_name'] == 'items'
        for dependency in privilege_event['object_dependencies']
    )


@requires_over_15
def test_collect_roles_security_invoker_boolean_spellings(integration_check, roles_instance, role_catalog, aggregator):
    """A view created with `security_invoker = on` or `= 1` must be reported as security invoker.

    Postgres keeps the literal text in pg_class.reloptions instead of normalizing it, so reading
    the option by exact string comparison misreports the security model of such views.
    """
    check = integration_check(roles_instance)

    run_one_check(check)

    privilege_event = next(
        event for event in aggregator.get_event_platform_events('dbm-metadata') if event['kind'] == 'pg_role_privileges'
    )

    assert {
        obj['object_name']: obj['security_invoker']
        for obj in privilege_event['objects']
        if obj['schema_name'] == 'dd_role_obs' and obj['object_type'] == 'view'
    } == {
        'item_view': False,
        'invoker_view': True,
        'invoker_view_on': True,
        'invoker_view_one': True,
    }


def test_collect_roles_disabled(integration_check, roles_instance, aggregator):
    roles_instance['collect_roles']['enabled'] = False
    check = integration_check(roles_instance)

    run_one_check(check)

    metadata = aggregator.get_event_platform_events('dbm-metadata')
    assert not [event for event in metadata if event['kind'] in {'pg_roles', 'pg_role_privileges'}]


def test_collect_roles_unsupported_version(integration_check, roles_instance, aggregator):
    check = integration_check(roles_instance)
    check.version = V13

    assert not check.metadata_samples._role_collector.collect_roles([])

    metadata = aggregator.get_event_platform_events('dbm-metadata')
    assert not [event for event in metadata if event['kind'] in {'pg_roles', 'pg_role_privileges'}]


@requires_over_14
def test_collect_roles_database_failure_has_no_terminal_payload(
    integration_check, roles_instance, aggregator, monkeypatch
):
    check = integration_check(roles_instance)
    collector = check.metadata_samples._role_collector
    collector._config.payload_chunk_size = 1
    original_collect_query = PostgresRoleCollector._collect_query

    def fail_after_privileges(self, cursor, query, params, array_name, emitter):
        if array_name == 'objects':
            raise RuntimeError("injected object collection failure")
        return original_collect_query(self, cursor, query, params, array_name, emitter)

    monkeypatch.setattr(PostgresRoleCollector, '_collect_query', fail_after_privileges)

    run_one_check(check)

    metadata = aggregator.get_event_platform_events('dbm-metadata')
    privilege_events = [event for event in metadata if event['kind'] == 'pg_role_privileges']
    assert privilege_events
    assert all('collection_payloads_count' not in event for event in privilege_events)
    assert any(event['kind'] == 'pg_roles' for event in metadata)


def test_collect_roles_updates_timestamp_on_failure(integration_check, roles_instance, monkeypatch):
    check = integration_check(roles_instance)
    job = check.metadata_samples
    job._tags_no_db = []

    def fail(_tags):
        raise RuntimeError("injected collection failure")

    monkeypatch.setattr(job._role_collector, 'collect_roles', fail)

    with pytest.raises(RuntimeError, match="injected collection failure"):
        job._collect_postgres_roles()

    assert job._last_roles_query_time > 0


def test_metadata_schedule_includes_role_collection_interval(integration_check, roles_instance):
    roles_instance['collect_roles']['collection_interval'] = 300

    check = integration_check(roles_instance)

    assert check.metadata_samples.collection_interval == 300


@requires_over_14
def test_collect_roles_database_list_failure_keeps_instance_scope(
    integration_check, roles_instance, aggregator, monkeypatch
):
    check = integration_check(roles_instance)

    def fail():
        raise RuntimeError("injected database list failure")

    monkeypatch.setattr(check.metadata_samples._role_collector, '_get_databases', fail)

    run_one_check(check)

    metadata = aggregator.get_event_platform_events('dbm-metadata')
    assert any(event['kind'] == 'pg_roles' and event['collection_payloads_count'] == 1 for event in metadata)
    assert not any(event['kind'] == 'pg_role_privileges' for event in metadata)
