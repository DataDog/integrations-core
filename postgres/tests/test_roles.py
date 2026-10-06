# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import contextlib
import json
from concurrent.futures.thread import ThreadPoolExecutor

import psycopg
import pytest

from datadog_checks.base.utils.db.utils import DBMAsyncJob
from datadog_checks.postgres import metadata as metadata_module
from datadog_checks.postgres.role_collector import (
    DATABASE_ARRAYS,
    INSTANCE_ARRAYS,
    PostgresRoleCollector,
    RoleSnapshotEmitter,
)
from datadog_checks.postgres.version_utils import V10, V11, V14, V15, V16

from .common import POSTGRES_VERSION
from .utils import _get_superconn, requires_over_15, run_one_check

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
                ALTER ROLE dd_role_obs_owner SET pgrst.jwt_secret = 'dd-role-obs-secret';
                ALTER ROLE dd_role_obs_owner SET "DdRoleObs.Api_Key" = 'dd-role-obs-mixed-case-secret';
                ALTER ROLE dd_role_obs_owner SET pg_stat_statements.track = 'all';
                ALTER ROLE dd_role_obs_owner SET "PgAudit.Log" = 'none';
                ALTER ROLE dd_role_obs_owner SET pg_trgm.similarity_threshold = '0.42';
                ALTER ROLE dd_role_obs_owner SET role = 'dd_role_obs_reader';
                CREATE SCHEMA dd_role_obs AUTHORIZATION dd_role_obs_owner;
                CREATE TABLE dd_role_obs.items (id integer);
                ALTER TABLE dd_role_obs.items OWNER TO dd_role_obs_owner;
                CREATE TABLE dd_role_obs.patients (id integer, name text, ssn text, retired text);
                ALTER TABLE dd_role_obs.patients OWNER TO dd_role_obs_owner;
                GRANT SELECT ON dd_role_obs.patients TO dd_role_obs_member;
                GRANT SELECT (id, name), UPDATE (name) ON dd_role_obs.patients TO dd_role_obs_reader;
                GRANT SELECT (ssn) ON dd_role_obs.patients TO dd_role_obs_reader;
                REVOKE SELECT (ssn) ON dd_role_obs.patients FROM dd_role_obs_reader;
                GRANT SELECT (retired) ON dd_role_obs.patients TO dd_role_obs_reader;
                ALTER TABLE dd_role_obs.patients DROP COLUMN retired;
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
                CREATE FUNCTION dd_role_obs.item_stats(min_id integer, OUT item_count bigint, OUT max_id integer)
                    LANGUAGE sql
                    AS 'SELECT count(*), max(id) FROM dd_role_obs.items WHERE id >= min_id';
                ALTER FUNCTION dd_role_obs.item_stats(integer) OWNER TO dd_role_obs_owner;
                GRANT EXECUTE ON FUNCTION dd_role_obs.item_stats(integer) TO dd_role_obs_reader;
                CREATE AGGREGATE dd_role_obs.item_total(integer) (
                    SFUNC = int4pl, STYPE = integer, INITCOND = '0'
                );
                ALTER AGGREGATE dd_role_obs.item_total(integer) OWNER TO dd_role_obs_owner;
                GRANT EXECUTE ON FUNCTION dd_role_obs.item_total(integer) TO dd_role_obs_reader;
                DO $$
                BEGIN
                    IF current_setting('server_version_num')::integer >= 100000 THEN
                        EXECUTE 'CREATE TABLE dd_role_obs.partitioned_items (id integer) PARTITION BY RANGE (id)';
                        EXECUTE 'ALTER TABLE dd_role_obs.partitioned_items OWNER TO dd_role_obs_owner';
                    END IF;
                    IF current_setting('server_version_num')::integer >= 110000 THEN
                        EXECUTE $sql$CREATE PROCEDURE dd_role_obs.refresh_items()
                            LANGUAGE sql AS 'DELETE FROM dd_role_obs.items WHERE false'$sql$;
                        EXECUTE 'ALTER PROCEDURE dd_role_obs.refresh_items() OWNER TO dd_role_obs_owner';
                    END IF;
                    -- Procedures accept OUT parameters from PostgreSQL 14.
                    IF current_setting('server_version_num')::integer >= 140000 THEN
                        EXECUTE $sql$CREATE PROCEDURE dd_role_obs.count_items_from(
                                IN min_id integer, OUT item_count bigint
                            ) LANGUAGE sql AS 'SELECT count(*) FROM dd_role_obs.items WHERE id >= min_id'$sql$;
                        EXECUTE 'ALTER PROCEDURE dd_role_obs.count_items_from(integer) OWNER TO dd_role_obs_owner';
                        EXECUTE 'GRANT EXECUTE ON PROCEDURE dd_role_obs.count_items_from(integer) '
                            'TO dd_role_obs_reader';
                    END IF;
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
                        EXECUTE 'GRANT dd_role_obs_reader TO dd_role_obs_member WITH INHERIT FALSE, SET FALSE';
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


def test_collect_roles_payload_contract(integration_check, roles_instance, role_catalog, aggregator):
    check = integration_check(roles_instance)

    run_one_check(check)

    metadata = aggregator.get_event_platform_events('dbm-metadata')
    role_events = [event for event in metadata if event['kind'] == 'pg_roles']
    privilege_events = [event for event in metadata if event['kind'] == 'pg_role_privileges']
    assert len(role_events) == 1
    assert len(privilege_events) == 1

    role_event = role_events[0]
    oid = _role_oids(role_event)
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
        'group_role_oid',
        'member_role_oid',
        'grantor_role_oid',
        'admin_option',
        'member_can_inherit',
        'member_can_set',
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
        if membership['group_role_oid'] == oid['dd_role_obs_reader']
        and membership['member_role_oid'] == oid['dd_role_obs_member']
    )
    assert member_grant['admin_option'] is True
    assert member_grant['member_can_inherit'] is False
    # Only PostgreSQL 16 and later can grant a membership without SET ROLE.
    assert member_grant['member_can_set'] is (check.version < V16)
    granted_grant = next(
        membership
        for membership in role_event['memberships']
        if membership['group_role_oid'] == oid['dd_role_obs_reader']
        and membership['member_role_oid'] == oid['dd_role_obs_granted']
    )
    assert granted_grant['grantor_role_oid'] == oid['dd_role_obs_grantor']
    assert granted_grant['member_can_set'] is True
    assert {
        'role_oid': oid['dd_role_obs_reader'],
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
        'object_type',
        'schema_name',
        'object_name',
        'column_name',
        'grantee_oid',
        'grantor_oid',
        'privilege',
        'is_grantable',
        'owner_oid',
    }
    assert set(privilege_event['objects'][0]) == {
        'object_type',
        'schema_name',
        'object_name',
        'object_oid',
        'owner_oid',
        'is_security_definer',
        'security_invoker',
        'has_default_acl',
    }
    assert set(privilege_event['default_privileges'][0]) == {
        'owner_oid',
        'schema_name',
        'object_type',
        'grantee_oid',
        'grantor_oid',
        'privilege',
        'is_grantable',
    }
    assert set(privilege_event['object_dependencies'][0]) == {
        'dependent_object_type',
        'dependent_schema_name',
        'dependent_object_name',
        'referenced_object_type',
        'referenced_schema_name',
        'referenced_object_name',
    }
    assert any(
        privilege['object_type'] == 'view'
        and privilege['schema_name'] == 'dd_role_obs'
        and privilege['object_name'] == 'item_view'
        and privilege['grantee_oid'] == oid['PUBLIC']
        and privilege['privilege'] == 'SELECT'
        for privilege in privilege_event['object_privileges']
    )
    assert any(
        privilege['schema_name'] == 'dd_role_obs'
        and privilege['object_name'] == 'items'
        and privilege['grantee_oid'] == oid['dd_role_obs_reader']
        and privilege['privilege'] == 'SELECT'
        and privilege['is_grantable']
        for privilege in privilege_event['object_privileges']
    )
    assert any(
        privilege['schema_name'] == 'dd_role_obs'
        and privilege['owner_oid'] == oid['dd_role_obs_owner']
        and privilege['grantee_oid'] == oid['dd_role_obs_reader']
        for privilege in privilege_event['default_privileges']
    )
    assert any(
        privilege['schema_name'] == ''
        and privilege['object_type'] == 'function'
        and privilege['grantee_oid'] == oid['dd_role_obs_reader']
        and privilege['is_grantable']
        for privilege in privilege_event['default_privileges']
    )
    if check.version >= V15:
        assert any(
            privilege['schema_name'] == ''
            and privilege['object_type'] == 'schema'
            and privilege['grantee_oid'] == oid['dd_role_obs_reader']
            and privilege['is_grantable']
            for privilege in privilege_event['default_privileges']
        )
    expected_object_types = {
        'aggregate',
        'foreign_table',
        'function',
        'materialized_view',
        'sequence',
        'table',
        'view',
    }
    if check.version >= V10:
        expected_object_types.add('partitioned_table')
    if check.version >= V11:
        expected_object_types.add('procedure')
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
        and privilege['grantee_oid'] == oid['dd_role_obs_reader']
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


def test_collect_roles_redacts_custom_setting_values(integration_check, roles_instance, role_catalog, aggregator):
    """Dotted settings are collected only for allowlisted extensions; all others are skipped.

    Applications and extensions store secrets such as PostgREST's `pgrst.jwt_secret` or PostgreSQL Anonymizer's
    `anon.salt` in role settings, and a module can register such a setting in `pg_settings`. Built-in settings,
    including hidden ones such as `role`, are always collected.
    """
    # Registers pg_trgm's settings in the agent's sessions, so its setting is known to `pg_settings` but is still
    # not on the allowlist.
    with _get_superconn(roles_instance) as conn:
        with conn.cursor() as cursor:
            cursor.execute(f"ALTER ROLE {roles_instance['username']} SET session_preload_libraries = 'pg_trgm'")
    try:
        check = integration_check(roles_instance)

        run_one_check(check)
    finally:
        with _get_superconn(roles_instance) as conn:
            with conn.cursor() as cursor:
                cursor.execute(f"ALTER ROLE {roles_instance['username']} RESET session_preload_libraries")

    metadata = aggregator.get_event_platform_events('dbm-metadata')
    assert 'dd-role-obs-secret' not in json.dumps(metadata)
    assert 'dd-role-obs-mixed-case-secret' not in json.dumps(metadata)
    role_event = next(event for event in metadata if event['kind'] == 'pg_roles')
    oid = _role_oids(role_event)

    assert {
        setting['setting_name']: setting['setting_value']
        for setting in role_event['settings']
        if setting['role_oid'] == oid['dd_role_obs_owner']
    } == {
        'pg_stat_statements.track': 'all',
        'PgAudit.Log': 'none',
        'role': 'dd_role_obs_reader',
    }


@pytest.mark.skipif(
    POSTGRES_VERSION is None or float(POSTGRES_VERSION) >= 16,
    reason='PostgreSQL 16 and later refuse to drop a role that granted a membership',
)
def test_collect_roles_keeps_membership_with_dropped_grantor(integration_check, roles_instance, aggregator):
    """A membership whose grantor was dropped is still in effect and must still be reported.

    Before PostgreSQL 16, dropping the grantor leaves its OID in pg_auth_members.grantor. Omitting the row would
    report that the member does not belong to the group.
    """
    with _get_superconn(roles_instance) as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                CREATE ROLE dd_role_obs_orphan_group NOLOGIN;
                CREATE ROLE dd_role_obs_orphan_member NOLOGIN;
                CREATE ROLE dd_role_obs_orphan_grantor NOLOGIN;
                GRANT dd_role_obs_orphan_group TO dd_role_obs_orphan_grantor WITH ADMIN OPTION;
                SET ROLE dd_role_obs_orphan_grantor;
                GRANT dd_role_obs_orphan_group TO dd_role_obs_orphan_member;
                RESET ROLE;
                """
            )
            cursor.execute("SELECT 'dd_role_obs_orphan_grantor'::regrole::oid")
            grantor_oid = cursor.fetchone()[0]
            cursor.execute("DROP ROLE dd_role_obs_orphan_grantor")
    try:
        check = integration_check(roles_instance)

        run_one_check(check)

        role_event = next(
            event for event in aggregator.get_event_platform_events('dbm-metadata') if event['kind'] == 'pg_roles'
        )
        oid = _role_oids(role_event)
        assert [
            membership['grantor_role_oid']
            for membership in role_event['memberships']
            if membership['group_role_oid'] == oid['dd_role_obs_orphan_group']
            and membership['member_role_oid'] == oid['dd_role_obs_orphan_member']
        ] == [grantor_oid]
    finally:
        with _get_superconn(roles_instance) as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    DROP ROLE IF EXISTS dd_role_obs_orphan_member;
                    DROP ROLE IF EXISTS dd_role_obs_orphan_group;
                    """
                )


def test_collect_roles_names_routines_by_input_types(integration_check, roles_instance, role_catalog, aggregator):
    """Routines are named by their input argument types, the form `GRANT ... ON FUNCTION` accepts.

    Parameter names and OUT parameters are not part of a routine's identity, and including them made names such
    as `pg_stat_statements(...)` list dozens of output columns in every privilege row.
    """
    check = integration_check(roles_instance)

    run_one_check(check)

    privilege_event = next(
        event for event in aggregator.get_event_platform_events('dbm-metadata') if event['kind'] == 'pg_role_privileges'
    )

    def routine_names(array_name):
        return {
            (row['object_type'], row['object_name'])
            for row in privilege_event[array_name]
            if row['schema_name'] == 'dd_role_obs' and row['object_type'] in ('function', 'procedure', 'aggregate')
        }

    granted = {('function', 'item_stats(integer)'), ('aggregate', 'item_total(integer)')}
    ungranted = {('function', 'count_items()')}
    if check.version >= V11:
        ungranted.add(('procedure', 'refresh_items()'))
    if check.version >= V14:
        granted.add(('procedure', 'count_items_from(integer)'))
    assert routine_names('objects') == granted | ungranted
    # Only routines with explicit grants have privilege rows.
    assert routine_names('object_privileges') == granted


def test_collect_roles_names_routines_independently_of_search_path(integration_check, roles_instance, aggregator):
    """A routine's name must not depend on the agent role's search_path.

    Argument types are written unqualified when the session's search_path finds them, so with two same-named
    types an unqualified name would point at a different overload depending on how the agent is configured.
    """
    username = roles_instance['username']
    with _get_superconn(roles_instance) as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                f"""
                CREATE SCHEMA dd_role_obs_path_a;
                CREATE SCHEMA dd_role_obs_path_b;
                CREATE TYPE dd_role_obs_path_a.t AS (x integer);
                CREATE TYPE dd_role_obs_path_b.t AS (x integer);
                CREATE FUNCTION dd_role_obs_path_a.f(dd_role_obs_path_a.t) RETURNS integer
                    LANGUAGE sql AS 'SELECT 1';
                CREATE FUNCTION dd_role_obs_path_a.f(dd_role_obs_path_b.t) RETURNS integer
                    LANGUAGE sql AS 'SELECT 2';
                -- A schema is only part of the effective search_path for roles with USAGE on it.
                GRANT USAGE ON SCHEMA dd_role_obs_path_b TO {username};
                ALTER ROLE {username} SET search_path = dd_role_obs_path_b, public;
                """
            )
    try:
        check = integration_check(roles_instance)

        run_one_check(check)
    finally:
        with _get_superconn(roles_instance) as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    f"""
                    ALTER ROLE {username} RESET search_path;
                    DROP SCHEMA dd_role_obs_path_a CASCADE;
                    DROP SCHEMA dd_role_obs_path_b CASCADE;
                    """
                )

    privilege_event = next(
        event for event in aggregator.get_event_platform_events('dbm-metadata') if event['kind'] == 'pg_role_privileges'
    )
    assert {
        obj['object_name']
        for obj in privilege_event['objects']
        if obj['schema_name'] == 'dd_role_obs_path_a' and obj['object_type'] == 'function'
    } == {'f(dd_role_obs_path_a.t)', 'f(dd_role_obs_path_b.t)'}


def test_collect_roles_ships_only_explicit_privileges(integration_check, roles_instance, role_catalog, aggregator):
    """Objects on default privileges ship no privilege rows; explicitly granted objects ship their complete ACL.

    The backend resolves default privileges from `has_default_acl`, the object type, and the owner. A grant stores
    the full ACL, including the owner and PUBLIC entries it started from, so those rows must still be shipped.
    """
    check = integration_check(roles_instance)

    run_one_check(check)

    metadata = aggregator.get_event_platform_events('dbm-metadata')
    privilege_event = next(event for event in metadata if event['kind'] == 'pg_role_privileges')
    role_name = {v: k for k, v in _role_oids(next(e for e in metadata if e['kind'] == 'pg_roles')).items()}

    def find_object(name):
        return next(
            obj
            for obj in privilege_event['objects']
            if obj['schema_name'] == 'dd_role_obs' and obj['object_name'] == name
        )

    def privileges(name):
        return {
            (role_name[privilege['grantee_oid']], privilege['privilege'])
            for privilege in privilege_event['object_privileges']
            if privilege['schema_name'] == 'dd_role_obs' and privilege['object_name'] == name
        }

    assert find_object('count_items()')['has_default_acl'] is True
    assert privileges('count_items()') == set()
    assert find_object('item_total(integer)')['has_default_acl'] is False
    assert privileges('item_total(integer)') == {
        ('dd_role_obs_owner', 'EXECUTE'),
        ('PUBLIC', 'EXECUTE'),
        ('dd_role_obs_reader', 'EXECUTE'),
    }


def test_collect_roles_column_privileges(integration_check, roles_instance, role_catalog, aggregator):
    """Column grants are reported per column, so access to a column such as `ssn` can be answered.

    Only columns granted individually have rows: a table-level grant stays on the table, and revoked or dropped
    columns have none.
    """
    check = integration_check(roles_instance)

    run_one_check(check)

    metadata = aggregator.get_event_platform_events('dbm-metadata')
    privilege_event = next(event for event in metadata if event['kind'] == 'pg_role_privileges')
    role_name = {v: k for k, v in _role_oids(next(e for e in metadata if e['kind'] == 'pg_roles')).items()}

    assert {
        (privilege['column_name'], role_name[privilege['grantee_oid']], privilege['privilege'])
        for privilege in privilege_event['object_privileges']
        if privilege['schema_name'] == 'dd_role_obs'
        and privilege['object_name'] == 'patients'
        and role_name[privilege['grantee_oid']] in ('dd_role_obs_member', 'dd_role_obs_reader')
    } == {
        ('', 'dd_role_obs_member', 'SELECT'),
        ('id', 'dd_role_obs_reader', 'SELECT'),
        ('name', 'dd_role_obs_reader', 'SELECT'),
        ('name', 'dd_role_obs_reader', 'UPDATE'),
    }


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


def test_collect_roles_database_failure_has_no_terminal_payload(
    integration_check, roles_instance, aggregator, monkeypatch
):
    check = integration_check(roles_instance)
    collector = check.metadata_samples._role_collector
    collector._config.payload_chunk_size = 1
    original_emit_rows = PostgresRoleCollector._emit_rows

    def fail_after_privileges(self, cursor, array_name, emitter):
        if array_name == 'objects':
            raise RuntimeError("injected object collection failure")
        return original_emit_rows(self, cursor, array_name, emitter)

    monkeypatch.setattr(PostgresRoleCollector, '_emit_rows', fail_after_privileges)

    run_one_check(check)

    metadata = aggregator.get_event_platform_events('dbm-metadata')
    privilege_events = [event for event in metadata if event['kind'] == 'pg_role_privileges']
    assert privilege_events
    assert all('collection_payloads_count' not in event for event in privilege_events)
    assert any(event['kind'] == 'pg_roles' for event in metadata)
    assert _database_time_statuses(aggregator) == [('datadog_test', 'error')]


def _role_oids(role_event):
    """Map role names to the OIDs the payloads use, with PUBLIC as 0."""
    return {'PUBLIC': 0, **{role['role_name']: role['role_oid'] for role in role_event['roles']}}


def _collected_databases(aggregator):
    return [
        event['database_name']
        for event in aggregator.get_event_platform_events('dbm-metadata')
        if event['kind'] == 'pg_role_privileges'
    ]


def _database_time_statuses(aggregator):
    statuses = []
    for metric in aggregator.metrics('dd.postgres.roles.database.time'):
        assert sum(tag.startswith('db:') for tag in metric.tags) == 1
        tags = dict(tag.split(':', 1) for tag in metric.tags if tag.startswith(('db:', 'status:')))
        statuses.append((tags['db'], tags['status']))
    return sorted(statuses)


def test_collect_roles_collects_every_database_within_budget(integration_check, roles_instance, aggregator):
    roles_instance['collect_roles']['include_databases'] = ['^dogs_[0-3]$']
    check = integration_check(roles_instance)

    run_one_check(check)

    assert _collected_databases(aggregator) == ['dogs_0', 'dogs_1', 'dogs_2', 'dogs_3']
    aggregator.assert_metric('dd.postgres.roles.skipped_databases', count=0)
    assert _database_time_statuses(aggregator) == [
        ('dogs_0', 'success'),
        ('dogs_1', 'success'),
        ('dogs_2', 'success'),
        ('dogs_3', 'success'),
    ]
    aggregator.assert_metric_has_tag('dd.postgres.roles.time', 'status:success', count=1)
    # One instance payload plus one payload per database.
    aggregator.assert_metric('dd.postgres.roles.payloads_count', value=5, count=1)


def test_collect_roles_resumes_after_exceeding_budget(integration_check, roles_instance, aggregator):
    """A run that exceeds the collection interval stops, and the next run resumes from the first skipped database.

    Without resuming, the databases sorted last would be skipped on every run.
    """
    roles_instance['collect_roles']['include_databases'] = ['^dogs_[0-3]$']
    check = integration_check(roles_instance)
    collector = check.metadata_samples._role_collector
    # Every run exceeds a zero-second budget after its first database.
    collector._config.collection_interval = 0

    collected = []
    # Keep the job uncancelled so the collector can be run again directly.
    run_one_check(check, cancel=False)
    try:
        collected.append(_collected_databases(aggregator))
        aggregator.assert_metric('dd.postgres.roles.skipped_databases', value=3, count=1)
        for _ in range(4):
            aggregator.reset()
            collector.collect_roles([])
            collected.append(_collected_databases(aggregator))
    finally:
        check.cancel()

    assert collected == [['dogs_0'], ['dogs_1'], ['dogs_2'], ['dogs_3'], ['dogs_0']]


@pytest.mark.parametrize(
    'collect_roles_overrides, instance_overrides, expected_databases',
    [
        pytest.param({'include_databases': ['^dogs_[0-2]$']}, {}, ['dogs_0', 'dogs_1', 'dogs_2'], id='include'),
        pytest.param(
            {'include_databases': ['^dogs_[0-2]$'], 'exclude_databases': ['^dogs_1$']},
            {},
            ['dogs_0', 'dogs_2'],
            id='include-and-exclude',
        ),
        pytest.param({'include_databases': ['^dogs_']}, {'dbstrict': True}, ['datadog_test'], id='dbstrict'),
    ],
)
def test_collect_roles_database_filters(
    integration_check, roles_instance, aggregator, collect_roles_overrides, instance_overrides, expected_databases
):
    roles_instance['collect_roles'].update(collect_roles_overrides)
    roles_instance.update(instance_overrides)
    check = integration_check(roles_instance)

    run_one_check(check)

    assert _collected_databases(aggregator) == expected_databases


def test_collect_roles_skips_databases_without_connect_privilege(integration_check, roles_instance, aggregator):
    """A database the agent may not connect to is skipped rather than failing on every run."""
    roles_instance['collect_roles']['include_databases'] = ['^dogs_[0-2]$']
    with _get_superconn(roles_instance) as conn:
        with conn.cursor() as cursor:
            cursor.execute("REVOKE CONNECT ON DATABASE dogs_1 FROM PUBLIC")
    try:
        check = integration_check(roles_instance)

        run_one_check(check)
    finally:
        with _get_superconn(roles_instance) as conn:
            with conn.cursor() as cursor:
                cursor.execute("GRANT CONNECT ON DATABASE dogs_1 TO PUBLIC")

    assert _collected_databases(aggregator) == ['dogs_0', 'dogs_2']
    assert _database_time_statuses(aggregator) == [('dogs_0', 'success'), ('dogs_2', 'success')]
    aggregator.assert_metric_has_tag('dd.postgres.roles.time', 'status:success', count=1)


def test_collect_roles_emits_rows_after_the_snapshot_ends(integration_check, roles_instance, aggregator, monkeypatch):
    """Rows are converted and submitted only after the collection transaction ends.

    The REPEATABLE READ snapshot holds back vacuum while it is open, so it must cover only the queries, not the
    serialization and submission of their results.
    """
    roles_instance['collect_roles']['include_databases'] = ['^dogs_[0-1]$']
    check = integration_check(roles_instance)
    statuses = []
    original_emit_rows = PostgresRoleCollector._emit_rows

    def emit_rows(self, cursor, array_name, emitter):
        statuses.append((array_name, cursor.connection.info.transaction_status))
        return original_emit_rows(self, cursor, array_name, emitter)

    monkeypatch.setattr(PostgresRoleCollector, '_emit_rows', emit_rows)

    run_one_check(check)

    assert len(statuses) == len(INSTANCE_ARRAYS) + 2 * len(DATABASE_ARRAYS)
    assert {status for _, status in statuses} == {psycopg.pq.TransactionStatus.IDLE}


def _fail_in_database(monkeypatch, database_name, failure):
    original_execute = PostgresRoleCollector._execute

    def execute(self, cursor, query, params):
        if cursor.connection.info.dbname == database_name:
            failure(self)
        return original_execute(self, cursor, query, params)

    monkeypatch.setattr(PostgresRoleCollector, '_execute', execute)


def test_collect_roles_database_failure_does_not_affect_other_databases(
    integration_check, roles_instance, aggregator, monkeypatch
):
    roles_instance['collect_roles']['include_databases'] = ['^dogs_[0-2]$']
    check = integration_check(roles_instance)

    def fail(_collector):
        raise RuntimeError("injected database failure")

    _fail_in_database(monkeypatch, 'dogs_1', fail)

    run_one_check(check)

    assert _collected_databases(aggregator) == ['dogs_0', 'dogs_2']
    assert _database_time_statuses(aggregator) == [
        ('dogs_0', 'success'),
        ('dogs_1', 'error'),
        ('dogs_2', 'success'),
    ]
    aggregator.assert_metric_has_tag('dd.postgres.roles.time', 'status:error', count=1)
    aggregator.assert_metric('dd.postgres.roles.payloads_count', value=3, count=1)


def test_collect_roles_cancellation_stops_remaining_databases(
    integration_check, roles_instance, aggregator, monkeypatch
):
    """Cancelling mid-run must stop the fan-out so agent shutdown is not held up, and discard the open snapshot."""
    roles_instance['collect_roles']['include_databases'] = ['^dogs_[0-2]$']
    check = integration_check(roles_instance)

    def cancel(collector):
        collector._cancel_event.set()

    _fail_in_database(monkeypatch, 'dogs_1', cancel)

    run_one_check(check)

    assert _collected_databases(aggregator) == ['dogs_0']
    assert _database_time_statuses(aggregator) == [('dogs_0', 'success'), ('dogs_1', 'cancelled')]
    aggregator.assert_metric_has_tag('dd.postgres.roles.time', 'status:cancelled', count=1)


def test_collect_roles_cancelled_before_start_reports_cancelled(integration_check, roles_instance, aggregator):
    """A run skipped because the job is shutting down must not look like a successful run that found no roles."""
    check = integration_check(roles_instance)
    check.version = V14
    collector = check.metadata_samples._role_collector
    collector._cancel_event.set()

    collector.collect_roles([])

    assert not aggregator.get_event_platform_events('dbm-metadata')
    aggregator.assert_metric_has_tag('dd.postgres.roles.time', 'status:cancelled', count=1)
    aggregator.assert_metric_has_tag('dd.postgres.roles.rows_count', 'status:cancelled', count=1)


@pytest.mark.parametrize('fails', [False, True], ids=['success', 'failure'])
def test_collect_roles_runs_once_per_collection_interval(integration_check, roles_instance, monkeypatch, fails):
    """Roles are collected on the first tick at least one collection interval after the previous collection.

    A collection's own duration must not push the next one back by a whole tick, and a failed collection must not
    be retried on every tick.
    """
    check = integration_check(roles_instance)
    job = check.metadata_samples
    job._tags_no_db = []
    clock = {'now': 0.0}
    monkeypatch.setattr(metadata_module.time, 'time', lambda: clock['now'])
    collected_at = []

    def collect(_tags):
        collected_at.append(clock['now'])
        clock['now'] += 5
        if fails:
            raise RuntimeError("injected collection failure")

    monkeypatch.setattr(job._role_collector, 'collect_roles', collect)

    # The collection interval is 600 seconds; the job ticks every 300.
    for tick in (1000, 1300, 1600, 1900, 2200):
        clock['now'] = tick
        job._rate_limiter.last_event = tick
        with contextlib.suppress(RuntimeError):
            job.report_postgres_metadata()

    assert collected_at == [1000, 1600, 2200]


def test_metadata_schedule_includes_role_collection_interval(integration_check, roles_instance):
    roles_instance['collect_roles']['collection_interval'] = 300

    check = integration_check(roles_instance)

    assert check.metadata_samples.collection_interval == 300


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
