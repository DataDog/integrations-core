# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json
from types import SimpleNamespace
from unittest import mock

import psycopg
import pytest

from datadog_checks.base.utils.diagnose import Diagnosis
from datadog_checks.postgres.diagnose import (
    RECOMMENDED_TRACK_ACTIVITY_QUERY_SIZE,
    _safe_identifier,
    _split_function,
)
from datadog_checks.postgres.util import (
    DIAGNOSTIC_METADATA,
    DatabaseConfigurationError,
    build_description,
    build_remediation,
)

pytestmark = pytest.mark.unit


# -- Helpers ------------------------------------------------------------------


def _setting(name):
    """Matcher for ``SELECT setting FROM pg_settings WHERE name = %s`` with the given name."""

    def predicate(sql, params):
        return 'pg_settings' in sql and params == (name,)

    predicate.__qualname__ = "_setting({!r})".format(name)
    return predicate


def _schema(name):
    """Matcher for schema-existence probes."""

    def predicate(sql, params):
        return 'pg_namespace' in sql and params == (name,)

    predicate.__qualname__ = "_schema({!r})".format(name)
    return predicate


def _extension_schema(name):
    """Matcher for extension-schema probes."""

    def predicate(sql, params):
        return 'pg_extension' in sql and 'pg_namespace' in sql and params == (name,)

    predicate.__qualname__ = "_extension_schema({!r})".format(name)
    return predicate


class FakeCursor:
    """Cursor stub that dispatches SQL -> canned result.

    ``responses`` is a list of ``(matcher, rows_or_exception)`` pairs. ``matcher`` is either:
      - a string: substring-matched against the SQL (params ignored)
      - a callable ``(sql, params) -> bool``
    The first matching entry wins.
    """

    def __init__(self, responses, default=None):
        self._responses = responses
        self._default = default
        self._rows = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def execute(self, sql, params=None):
        for matcher, result in self._responses:
            if callable(matcher):
                ok = matcher(sql, params)
            else:
                ok = matcher in sql
            if ok:
                if isinstance(result, Exception):
                    raise result
                self._rows = list(result)
                return
        if self._default is not None:
            if isinstance(self._default, Exception):
                raise self._default
            self._rows = list(self._default)
            return
        # No match -> empty result, makes tests strict about their mocks.
        self._rows = []

    def fetchone(self):
        return self._rows[0] if self._rows else None

    def fetchall(self):
        return list(self._rows)


class FakeConn:
    def __init__(self, responses, default=None):
        self._responses = responses
        self._default = default
        self.info = SimpleNamespace(encoding='utf-8')

    def cursor(self, *args, **kwargs):
        return FakeCursor(self._responses, self._default)

    def close(self):
        pass


def _get_diagnoses(check):
    check.diagnosis.clear()
    return [d._asdict() for d in check.diagnosis.run_explicit()]


def _by_name(diagnoses, name):
    return [d for d in diagnoses if d['name'] == name]


def _patch_connection(check, conn):
    """Patch the probe connection factory on the check's diagnose instance path."""
    return mock.patch('datadog_checks.postgres.postgres.TokenAwareConnection.connect', return_value=conn)


def _patch_per_db(connections):
    """Patch the probe connection factory to dispatch by ``dbname`` kwarg."""
    return mock.patch(
        'datadog_checks.postgres.postgres.TokenAwareConnection.connect',
        side_effect=lambda **kwargs: connections[kwargs['dbname']],
    )


def _explain_call(name='datadog.explain_statement'):
    return "SELECT {}(%s)".format(_safe_identifier(name))


def _successful_explain():
    return [('plan',)]


def _run(check, responses):
    """Run diagnose against a single FakeConn built from ``responses``."""
    with _patch_connection(check, FakeConn(responses)):
        return _get_diagnoses(check)


def _dbm_check(integration_check, pg_instance, **overrides):
    return integration_check(dict(pg_instance, dbm=True, **overrides))


def _override(responses, key, new_result):
    """Replace the result for the matcher matching ``key``.

    String key: exact equality on string matchers. Callable key: qualname equality.
    """
    if callable(key):
        target_qn = getattr(key, '__qualname__', None)

        def hit(m):
            return callable(m) and getattr(m, '__qualname__', None) == target_qn
    else:

        def hit(m):
            return m == key

    out = []
    found = False
    for m, r in responses:
        if hit(m):
            out.append((m, new_result))
            found = True
        else:
            out.append((m, r))
    assert found, "no matcher matching {!r}".format(key)
    return out


def _assert_all_succeed(diagnoses, codes):
    names_and_results = {(d['name'], d['result']) for d in diagnoses}
    for code in codes:
        assert (code.value, Diagnosis.DIAGNOSIS_SUCCESS) in names_and_results, (
            f"expected {code.value} to pass, got {[d for d in diagnoses if d['name'] == code.value]}"
        )


def _happy_server_responses(
    *, server_version='14.5', spl='pg_stat_statements, pgaudit', track_query_size=4096, track_io='on', pgss_max=10000
):
    return [
        ('SHOW SERVER_VERSION', [(server_version,)]),
        (_setting('shared_preload_libraries'), [(spl,)]),
        (_setting('track_activity_query_size'), [(str(track_query_size),)]),
        (_setting('track_io_timing'), [(track_io,)]),
        (_setting('pg_stat_statements.max'), [(str(pgss_max),)]),
        ("rolname = 'pg_monitor'", [(1,)]),
        ("pg_has_role", [(True,)]),
        ("FROM pg_stat_database", [(1,)]),
        ("query = %s", [(0,)]),
    ]


def _happy_dbm_responses():
    return [
        (_schema('datadog'), [(1,)]),
        # USAGE on `datadog` and `public` is granted -- shared substring across both probes.
        ("has_schema_privilege", [(True,)]),
        (_extension_schema('pg_stat_statements'), [('public',)]),
        # pg_stat_statements readable probe — the SQL contains the quoted view name.
        ('SELECT 1 FROM "pg_stat_statements" LIMIT 1', [(1,)]),
        (_explain_call(), _successful_explain()),
    ]


# -- record_warning regression ------------------------------------------------


def test_record_warning_populates_legacy_dict_only(integration_check, pg_instance):
    """`record_warning` feeds `agent status` via `_warnings_by_code`; `agent diagnose` is served
    by the pre-flight orchestrators in `diagnose.py`, so no diagnosis row should be emitted here."""
    check = integration_check(pg_instance)
    code = DatabaseConfigurationError.pg_stat_statements_not_loaded
    check.diagnosis.clear()

    check.record_warning(code, "pg_stat_statements is not loaded")

    assert check._warnings_by_code[code] == "pg_stat_statements is not loaded"
    assert check.diagnosis.diagnoses == []


def test_get_diagnoses_returns_json(integration_check, pg_instance):
    """Seed the cached diagnoses directly (the legacy `record_warning` mirror is gone) and
    verify `get_diagnoses` returns a JSON payload containing the entry."""
    check = integration_check(pg_instance)
    check.diagnosis.clear()
    check.diagnosis.warning(
        name=DatabaseConfigurationError.pg_stat_statements_not_loaded.value,
        diagnosis="pg_stat_statements is not loaded",
        category="postgres",
        description=DIAGNOSTIC_METADATA[DatabaseConfigurationError.pg_stat_statements_not_loaded]["description"],
        remediation=build_remediation(DatabaseConfigurationError.pg_stat_statements_not_loaded),
    )
    with mock.patch.object(check.diagnosis, '_diagnostics', []):
        payload = check.get_diagnoses()
    parsed = json.loads(payload)
    assert any(d['name'] == DatabaseConfigurationError.pg_stat_statements_not_loaded.value for d in parsed)


# -- Connection diagnostic ----------------------------------------------------


@pytest.mark.parametrize('dbm', [False, True])
def test_connection_failure_surfaces_single_fail(integration_check, pg_instance, dbm):
    """Exactly one FAIL row regardless of dbm, and exactly one probe connection opened."""
    check = integration_check(dict(pg_instance, dbm=dbm))
    err = psycopg.OperationalError('could not connect')
    with mock.patch('datadog_checks.postgres.postgres.TokenAwareConnection.connect', side_effect=err) as connect:
        diagnoses = _get_diagnoses(check)
    assert connect.call_count == 1
    rows = _by_name(diagnoses, DatabaseConfigurationError.connection_failure.value)
    assert len(rows) == 1
    assert rows[0]['result'] == Diagnosis.DIAGNOSIS_FAIL
    assert 'could not connect' in rows[0]['diagnosis']
    assert 'troubleshooting' in rows[0]['remediation']


def test_probe_connection_uses_pool_configuration(integration_check, pg_instance):
    check = integration_check(pg_instance)
    conn = FakeConn(_happy_server_responses())
    with mock.patch.object(
        check.db_pool, '_configure_connection', wraps=check.db_pool._configure_connection
    ) as configure:
        with _patch_connection(check, conn):
            _get_diagnoses(check)

    configure.assert_called_once_with(conn)


# -- Server config diagnostics ------------------------------------------------


def test_server_config_happy_path(integration_check, pg_instance):
    """Non-DBM without activity metrics still validates pg_monitor and pg_stat_database
    (both are baseline grants for the integration); pg_stat_activity is only checked when
    activity metrics are enabled."""
    check = integration_check(pg_instance)
    diagnoses = _run(check, _happy_server_responses())

    _assert_all_succeed(
        diagnoses,
        (
            DatabaseConfigurationError.postgres_version_unsupported,
            DatabaseConfigurationError.missing_pg_monitor_role,
            DatabaseConfigurationError.pg_stat_database_not_readable,
        ),
    )
    assert not _by_name(diagnoses, DatabaseConfigurationError.insufficient_privilege_on_pg_stat_activity.value)


def test_dbm_server_config_happy_path(integration_check, pg_instance):
    """With dbm=true the DBM-gated GUC diagnostics also run and should all succeed on a healthy
    Postgres."""
    check = _dbm_check(integration_check, pg_instance)
    diagnoses = _run(check, _happy_server_responses() + _happy_dbm_responses())
    _assert_all_succeed(
        diagnoses,
        (
            DatabaseConfigurationError.shared_preload_libraries_missing_pg_stat_statements,
            DatabaseConfigurationError.track_activity_query_size_too_small,
            DatabaseConfigurationError.track_io_timing_disabled,
            DatabaseConfigurationError.high_pg_stat_statements_max,
        ),
    )


def test_shared_preload_libraries_unreadable_warns(integration_check, pg_instance):
    """Row is hidden from non-pg_monitor users for GUC_SUPERUSER_ONLY settings -- we should
    surface a WARNING instead of silently dropping the diagnostic."""
    check = _dbm_check(integration_check, pg_instance)
    responses = _override(_happy_server_responses(), _setting('shared_preload_libraries'), [])
    diagnoses = _run(check, responses + _happy_dbm_responses())
    spl = _by_name(
        diagnoses,
        DatabaseConfigurationError.shared_preload_libraries_missing_pg_stat_statements.value,
    )
    assert len(spl) == 1, spl
    assert spl[0]['result'] == Diagnosis.DIAGNOSIS_WARNING
    assert 'pg_monitor' in spl[0]['diagnosis']
    assert 'pg_monitor' in spl[0]['remediation']


@pytest.mark.parametrize(
    'kwarg,value,code,assert_in_diagnosis',
    [
        (
            'track_query_size',
            1024,
            DatabaseConfigurationError.track_activity_query_size_too_small,
            str(RECOMMENDED_TRACK_ACTIVITY_QUERY_SIZE),
        ),
        ('track_io', 'off', DatabaseConfigurationError.track_io_timing_disabled, None),
        ('pgss_max', 50000, DatabaseConfigurationError.high_pg_stat_statements_max, '50000'),
    ],
)
def test_dbm_guc_warning(integration_check, pg_instance, kwarg, value, code, assert_in_diagnosis):
    check = _dbm_check(integration_check, pg_instance)
    responses = _happy_server_responses(**{kwarg: value}) + _happy_dbm_responses()
    diagnoses = _run(check, responses)
    entry = _by_name(diagnoses, code.value)[0]
    assert entry['result'] == Diagnosis.DIAGNOSIS_WARNING
    if assert_in_diagnosis:
        assert assert_in_diagnosis in entry['diagnosis']


def test_unsupported_postgres_version_fails(integration_check, pg_instance):
    check = integration_check(pg_instance)
    diagnoses = _run(check, _happy_server_responses(server_version='9.5.1'))
    entry = _by_name(diagnoses, DatabaseConfigurationError.postgres_version_unsupported.value)[0]
    assert entry['result'] == Diagnosis.DIAGNOSIS_FAIL
    assert '9.5' in entry['diagnosis']


# -- Privilege diagnostics ----------------------------------------------------


def test_missing_pg_monitor_role_fails(integration_check, pg_instance):
    check = integration_check(pg_instance)
    responses = _override(_happy_server_responses(), 'pg_has_role', [(False,)])
    diagnoses = _run(check, responses)
    entry = _by_name(diagnoses, DatabaseConfigurationError.missing_pg_monitor_role.value)[0]
    assert entry['result'] == Diagnosis.DIAGNOSIS_FAIL
    assert 'pg_monitor' in entry['remediation']


def test_pg_stat_database_access_fails_on_permission_error(integration_check, pg_instance):
    check = integration_check(pg_instance)
    responses = _override(
        _happy_server_responses(),
        'FROM pg_stat_database',
        psycopg.errors.InsufficientPrivilege('permission denied for relation pg_stat_database'),
    )
    diagnoses = _run(check, responses)
    entry = _by_name(diagnoses, DatabaseConfigurationError.pg_stat_database_not_readable.value)[0]
    assert entry['result'] == Diagnosis.DIAGNOSIS_FAIL
    assert 'pg_stat_database' in entry['diagnosis']
    assert entry['remediation'] == build_remediation(DatabaseConfigurationError.pg_stat_database_not_readable)
    assert 'pg_monitor' in entry['remediation']


def test_insufficient_privilege_on_pg_stat_activity_warns(integration_check, pg_instance):
    check = integration_check(dict(pg_instance, collect_activity_metrics=True))
    responses = _override(_happy_server_responses(), 'query = %s', [(3,)])
    diagnoses = _run(check, responses)
    entry = _by_name(diagnoses, DatabaseConfigurationError.insufficient_privilege_on_pg_stat_activity.value)[0]
    assert entry['result'] == Diagnosis.DIAGNOSIS_WARNING
    assert '3' in entry['diagnosis']


# -- DBM diagnostics ----------------------------------------------------------


def test_dbm_disabled_skips_dbm_diagnostics(integration_check, pg_instance):
    check = integration_check(pg_instance)  # dbm defaults to False
    diagnoses = _run(check, _happy_server_responses() + _happy_dbm_responses())
    # Neither the DBM database-scoped checks nor the DBM-only server GUC checks should run
    # without dbm=true -- running them against a plain Postgres would fail a healthy instance.
    dbm_names = {
        DatabaseConfigurationError.shared_preload_libraries_missing_pg_stat_statements.value,
        DatabaseConfigurationError.track_activity_query_size_too_small.value,
        DatabaseConfigurationError.track_io_timing_disabled.value,
        DatabaseConfigurationError.high_pg_stat_statements_max.value,
        DatabaseConfigurationError.missing_datadog_schema.value,
        DatabaseConfigurationError.missing_schema_usage_grant.value,
        DatabaseConfigurationError.pg_stat_statements_not_created.value,
        DatabaseConfigurationError.pg_stat_statements_not_readable.value,
        DatabaseConfigurationError.undefined_explain_function.value,
    }
    assert not any(d['name'] in dbm_names for d in diagnoses)


def test_dbm_happy_path(integration_check, pg_instance):
    check = _dbm_check(integration_check, pg_instance)
    diagnoses = _run(check, _happy_server_responses() + _happy_dbm_responses())
    _assert_all_succeed(
        diagnoses,
        (
            DatabaseConfigurationError.missing_datadog_schema,
            DatabaseConfigurationError.missing_schema_usage_grant,
            DatabaseConfigurationError.pg_stat_statements_not_created,
            DatabaseConfigurationError.pg_stat_statements_not_readable,
            DatabaseConfigurationError.undefined_explain_function,
        ),
    )


def test_missing_pg_stat_statements_extension_fails(integration_check, pg_instance):
    check = _dbm_check(integration_check, pg_instance)
    dbm_responses = _override(_happy_dbm_responses(), _extension_schema('pg_stat_statements'), [])
    # Simulate extension missing: the readable probe would raise UndefinedTable, swallowed silently.
    dbm_responses = _override(
        dbm_responses,
        'SELECT 1 FROM "pg_stat_statements" LIMIT 1',
        psycopg.errors.UndefinedTable('relation "pg_stat_statements" does not exist'),
    )
    diagnoses = _run(check, _happy_server_responses() + dbm_responses)
    created = _by_name(diagnoses, DatabaseConfigurationError.pg_stat_statements_not_created.value)[0]
    assert created['result'] == Diagnosis.DIAGNOSIS_FAIL
    # readable probe is suppressed when UndefinedTable raised (to avoid double-report)
    assert not _by_name(diagnoses, DatabaseConfigurationError.pg_stat_statements_not_readable.value)


def test_missing_explain_function_fails(integration_check, pg_instance):
    check = _dbm_check(integration_check, pg_instance)
    dbm_responses = _override(
        _happy_dbm_responses(),
        _explain_call(),
        psycopg.errors.UndefinedFunction('function datadog.explain_statement does not exist'),
    )
    diagnoses = _run(check, _happy_server_responses() + dbm_responses)
    entry = _by_name(diagnoses, DatabaseConfigurationError.undefined_explain_function.value)[0]
    assert entry['result'] == Diagnosis.DIAGNOSIS_FAIL
    assert 'explain_statement' in entry['diagnosis']


def test_explain_function_with_trailing_parens_succeeds(integration_check, pg_instance):
    """explain_function configured with trailing () should not produce invalid SQL."""
    check = _dbm_check(
        integration_check, pg_instance, query_samples={'explain_function': 'datadog.explain_statement()'}
    )
    diagnoses = _run(check, _happy_server_responses() + _happy_dbm_responses())
    entries = _by_name(diagnoses, DatabaseConfigurationError.undefined_explain_function.value)
    assert len(entries) == 1
    assert entries[0]['result'] == Diagnosis.DIAGNOSIS_SUCCESS


def test_query_samples_probes_each_monitored_database(integration_check, pg_instance):
    check = _dbm_check(integration_check, pg_instance, query_metrics={'enabled': False})
    connections = {
        pg_instance['dbname']: FakeConn(
            _happy_server_responses()
            + [
                ("pg_catalog.pg_database", [(pg_instance['dbname'],), ('broken_schema',), ('broken_function',)]),
                (_schema('datadog'), [(1,)]),
                ("has_schema_privilege", [(True,)]),
                (_explain_call(), _successful_explain()),
            ]
        ),
        'broken_schema': FakeConn([(_schema('datadog'), [])]),
        'broken_function': FakeConn(
            [
                (_schema('datadog'), [(1,)]),
                ("has_schema_privilege", [(True,)]),
                (
                    _explain_call(),
                    psycopg.errors.UndefinedFunction('function datadog.explain_statement does not exist'),
                ),
            ]
        ),
    }
    with _patch_per_db(connections):
        diagnoses = _get_diagnoses(check)

    missing_schema = _by_name(diagnoses, DatabaseConfigurationError.missing_datadog_schema.value)
    assert any(d['result'] == Diagnosis.DIAGNOSIS_FAIL and 'broken_schema' in d['diagnosis'] for d in missing_schema), (
        missing_schema
    )

    missing_explain = _by_name(diagnoses, DatabaseConfigurationError.undefined_explain_function.value)
    assert any(
        d['result'] == Diagnosis.DIAGNOSIS_FAIL and 'broken_function' in d['diagnosis'] for d in missing_explain
    ), missing_explain


# -- Query-samples database enumeration --------------------------------------


def test_query_samples_with_autodiscovery_probes_query_sampled_databases(integration_check, pg_instance):
    """Query-sample setup follows pg_stat_activity filtering, while autodiscovery still probes connectivity."""
    check = _dbm_check(
        integration_check,
        pg_instance,
        database_autodiscovery={'enabled': True, 'include': ['app_a$'], 'max_databases': 1},
    )
    healthy_dbm = _happy_dbm_responses()
    broken_dbm = [
        (_schema('datadog'), [(1,)]),
        ("has_schema_privilege", [(False,)]),
    ]
    connections = {
        pg_instance['dbname']: FakeConn(
            _happy_server_responses() + [("pg_catalog.pg_database", [('app_a',), ('app_b',)])] + healthy_dbm
        ),
        'app_a': FakeConn(healthy_dbm),
        'app_b': FakeConn(broken_dbm),
    }
    with mock.patch.object(check.autodiscovery, 'get_items', return_value=['app_a']) as get_items:
        with _patch_per_db(connections) as connect:
            diagnoses = _get_diagnoses(check)

    assert get_items.called
    opened_dbnames = {call.kwargs['dbname'] for call in connect.call_args_list}
    assert opened_dbnames == {pg_instance['dbname'], 'app_a', 'app_b'}

    rows = _by_name(diagnoses, DatabaseConfigurationError.missing_schema_usage_grant.value)
    fail_rows = [d for d in rows if d['result'] == Diagnosis.DIAGNOSIS_FAIL]
    assert len(fail_rows) == 2
    assert all('app_b' in d['diagnosis'] for d in fail_rows), fail_rows


def test_query_samples_with_autodiscovery_uses_pg_database_for_setup(integration_check, pg_instance):
    """DBM query-sample setup does not use autodiscovery include/exclude to choose probe databases."""
    check = _dbm_check(
        integration_check,
        pg_instance,
        database_autodiscovery={'enabled': True, 'include': ['matches_nothing_.*']},
    )
    responses = (
        _happy_server_responses() + [("pg_catalog.pg_database", [(pg_instance['dbname'],)])] + _happy_dbm_responses()
    )
    with mock.patch.object(check.autodiscovery, 'get_items', return_value=[]) as get_items:
        with _patch_connection(check, FakeConn(responses)) as connect:
            _get_diagnoses(check)
    assert get_items.called
    opened_dbnames = {call.kwargs['dbname'] for call in connect.call_args_list}
    assert opened_dbnames == {pg_instance['dbname']}


def test_autodiscovery_probe_databases_raises_falls_back_gracefully(integration_check, pg_instance):
    """autodiscovery enabled, get_items() raises -> fall through to pg_database without crashing."""
    check = integration_check(dict(pg_instance, database_autodiscovery={'enabled': True, 'include': ['.*']}))
    responses = _happy_server_responses() + [("pg_catalog.pg_database", [(pg_instance['dbname'],)])]
    with mock.patch.object(check.autodiscovery, 'get_items', side_effect=psycopg.OperationalError('boom')):
        diagnoses = _run(check, responses)
    # Diagnose completed without crashing; config-validation still emits at the bottom.
    assert _by_name(diagnoses, DatabaseConfigurationError.config_validation.value)


def test_query_samples_dbstrict_short_circuits_setup_but_not_autodiscovery(integration_check, pg_instance):
    """`dbstrict` limits query-sample setup to dbname; autodiscovery connectivity still uses its DB list."""
    for ad_enabled in (True, False):
        ad_config = {'enabled': True, 'include': ['.*']} if ad_enabled else {'enabled': False}
        check = _dbm_check(integration_check, pg_instance, dbstrict=True, database_autodiscovery=ad_config)
        responses = _happy_server_responses() + _happy_dbm_responses()

        if ad_enabled and check.autodiscovery is not None:
            with mock.patch.object(check.autodiscovery, 'get_items', return_value=['app_a']) as gi:
                with _patch_connection(check, FakeConn(responses)) as connect:
                    _get_diagnoses(check)
                assert gi.called
        else:
            with _patch_connection(check, FakeConn(responses)) as connect:
                _get_diagnoses(check)
        opened_dbnames = {call.kwargs['dbname'] for call in connect.call_args_list}
        expected = {pg_instance['dbname'], 'app_a'} if ad_enabled else {pg_instance['dbname']}
        assert opened_dbnames == expected, "ad_enabled={}: got {}".format(ad_enabled, opened_dbnames)


# -- Per-database DBM probes (autodiscovery + cluster-level checks) ----------


def test_query_samples_disabled_probes_pg_stat_statements_on_main_db_only(integration_check, pg_instance):
    """With query_samples disabled, query_metrics reads pg_stat_statements from the main DB only,
    even with autodiscovery. Datadog-schema and explain-function probes are query_samples
    prerequisites and don't fire anywhere. Per-DB connectivity is still validated."""
    check = _dbm_check(
        integration_check,
        pg_instance,
        query_samples={'enabled': False},
        query_activity={'enabled': False},
        database_autodiscovery={'enabled': True, 'include': ['app_.*']},
    )
    main_dbm = [
        (_extension_schema('pg_stat_statements'), [('public',)]),
        ('SELECT 1 FROM "pg_stat_statements" LIMIT 1', [(1,)]),
    ]
    connections = {
        pg_instance['dbname']: FakeConn(_happy_server_responses() + main_dbm),
        'app_a': FakeConn([]),
        'app_b': FakeConn([]),
    }
    with mock.patch.object(check.autodiscovery, 'get_items', return_value=['app_a', 'app_b']):
        with _patch_per_db(connections):
            diagnoses = _get_diagnoses(check)

    for code in (
        DatabaseConfigurationError.pg_stat_statements_not_created,
        DatabaseConfigurationError.pg_stat_statements_not_readable,
    ):
        rows = _by_name(diagnoses, code.value)
        assert len(rows) == 1, (code.value, rows)
        assert rows[0]['result'] == Diagnosis.DIAGNOSIS_SUCCESS
        assert pg_instance['dbname'] in rows[0]['diagnosis']
    assert not _by_name(diagnoses, DatabaseConfigurationError.missing_schema_usage_grant.value)
    assert not _by_name(diagnoses, DatabaseConfigurationError.undefined_explain_function.value)
    assert not _by_name(diagnoses, DatabaseConfigurationError.missing_datadog_schema.value)


def test_schema_usage_grant_fails_when_missing(integration_check, pg_instance):
    """Documented setup step `GRANT USAGE ON SCHEMA public TO datadog` must be verified --
    a catalog-only check would mask this since pg_proc joins succeed without USAGE."""
    check = _dbm_check(integration_check, pg_instance)

    def usage_predicate(sql, params):
        return 'has_schema_privilege' in sql and params == ('public',)

    usage_predicate.__qualname__ = "usage_predicate(public)"

    dbm_responses = [
        (_schema('datadog'), [(1,)]),
        # USAGE on `datadog` granted, but USAGE on `public` denied.
        (usage_predicate, [(False,)]),
        ("has_schema_privilege", [(True,)]),
        (_extension_schema('pg_stat_statements'), [('public',)]),
        ('SELECT 1 FROM "pg_stat_statements" LIMIT 1', [(1,)]),
        (_explain_call(), _successful_explain()),
    ]
    diagnoses = _run(check, _happy_server_responses() + dbm_responses)

    rows = _by_name(diagnoses, DatabaseConfigurationError.missing_schema_usage_grant.value)
    fail_rows = [d for d in rows if d['result'] == Diagnosis.DIAGNOSIS_FAIL]
    assert len(fail_rows) == 1, rows
    assert 'public' in fail_rows[0]['diagnosis']
    assert 'GRANT USAGE ON SCHEMA public' in fail_rows[0]['remediation']


def test_schema_usage_grant_per_autodiscovered_database(integration_check, pg_instance):
    """USAGE grants are per-database; missing USAGE on `datadog` in one DB only must
    produce a FAIL row scoped to that DB."""
    check = _dbm_check(
        integration_check,
        pg_instance,
        database_autodiscovery={'enabled': True, 'include': ['app_.*']},
    )
    healthy_dbm = _happy_dbm_responses()
    # In app_b, the datadog schema exists but USAGE is denied.
    broken_dbm = _override(_happy_dbm_responses(), 'has_schema_privilege', [(False,)])
    connections = {
        pg_instance['dbname']: FakeConn(
            _happy_server_responses() + [("pg_catalog.pg_database", [('app_a',), ('app_b',)])] + healthy_dbm
        ),
        'app_a': FakeConn(healthy_dbm),
        'app_b': FakeConn(broken_dbm),
    }
    with mock.patch.object(check.autodiscovery, 'get_items', return_value=['app_a', 'app_b']) as get_items:
        with _patch_per_db(connections):
            diagnoses = _get_diagnoses(check)

    assert get_items.called
    rows = _by_name(diagnoses, DatabaseConfigurationError.missing_schema_usage_grant.value)
    fail_rows = [d for d in rows if d['result'] == Diagnosis.DIAGNOSIS_FAIL]
    success_rows = [d for d in rows if d['result'] == Diagnosis.DIAGNOSIS_SUCCESS]
    # Both schemas (datadog, public) FAIL in app_b -> 2 fails, both naming app_b.
    assert all('app_b' in d['diagnosis'] for d in fail_rows), fail_rows
    assert len(fail_rows) == 2
    # Only app_a runs the per-DB loop with healthy responses (main DB isn't in autodiscovery
    # output, so it's skipped in the loop). 2 SUCCESS rows: USAGE on `datadog` + on `public`.
    assert all('app_a' in d['diagnosis'] for d in success_rows), success_rows
    assert len(success_rows) == 2


def test_schema_usage_skipped_when_datadog_schema_missing(integration_check, pg_instance):
    """If the `datadog` schema doesn't exist, the USAGE-on-datadog FAIL is noise on top of
    the schema-existence FAIL. Skip it. USAGE on `public` is independent and still runs."""
    check = _dbm_check(integration_check, pg_instance)
    dbm_responses = _override(_happy_dbm_responses(), _schema('datadog'), [])
    # has_schema_privilege would return False for datadog (NULL row from a missing schema),
    # but the cascade-skip means the probe never queries it for `datadog`. Public still does.
    dbm_responses = _override(
        dbm_responses,
        _explain_call(),
        psycopg.errors.UndefinedFunction('function datadog.explain_statement does not exist'),
    )
    diagnoses = _run(check, _happy_server_responses() + dbm_responses)

    schema_rows = _by_name(diagnoses, DatabaseConfigurationError.missing_datadog_schema.value)
    assert schema_rows and schema_rows[0]['result'] == Diagnosis.DIAGNOSIS_FAIL
    # USAGE rows: only `public` should appear (datadog skipped); and it should be SUCCESS.
    usage_rows = _by_name(diagnoses, DatabaseConfigurationError.missing_schema_usage_grant.value)
    assert len(usage_rows) == 1, usage_rows
    assert 'public' in usage_rows[0]['diagnosis']
    assert usage_rows[0]['result'] == Diagnosis.DIAGNOSIS_SUCCESS


# -- Autodiscovery connectivity probing (regardless of DBM) ------------------


@pytest.mark.parametrize('dbm', [False, True])
def test_autodiscovery_probes_each_database_connectivity(integration_check, pg_instance, dbm):
    """Autodiscovery fans out per-DB connections at runtime (relation/function/count metrics
    without DBM, plus query-metrics/activity with DBM); diagnose must validate that the datadog
    user can CONNECT to each one. A failure on a discovered DB should surface as a
    connection_failure diagnostic with that dbname embedded. DBM-specific schema/explain probes
    must not fire when query_samples is disabled."""
    overrides = {'database_autodiscovery': {'enabled': True, 'include': ['app_.*']}}
    if dbm:
        overrides['dbm'] = True
        overrides['query_samples'] = {'enabled': False}
        main_responses = _happy_server_responses() + [
            (_extension_schema('pg_stat_statements'), [('public',)]),
            ('SELECT 1 FROM "pg_stat_statements" LIMIT 1', [(1,)]),
        ]
    else:
        main_responses = _happy_server_responses()
    check = integration_check(dict(pg_instance, **overrides))
    err = psycopg.OperationalError('permission denied for database "app_b"')

    def connect(**kwargs):
        if kwargs['dbname'] == pg_instance['dbname']:
            return FakeConn(main_responses)
        if kwargs['dbname'] == 'app_a':
            return FakeConn([])
        if kwargs['dbname'] == 'app_b':
            raise err
        raise psycopg.OperationalError('unexpected dbname={}'.format(kwargs['dbname']))

    with mock.patch.object(check.autodiscovery, 'get_items', return_value=['app_a', 'app_b']):
        with mock.patch(
            'datadog_checks.postgres.postgres.TokenAwareConnection.connect', side_effect=connect
        ) as connect_mock:
            diagnoses = _get_diagnoses(check)

    opened_dbnames = {call.kwargs['dbname'] for call in connect_mock.call_args_list}
    assert opened_dbnames == {pg_instance['dbname'], 'app_a', 'app_b'}

    failed = [
        d
        for d in _by_name(diagnoses, DatabaseConfigurationError.connection_failure.value)
        if d['result'] == Diagnosis.DIAGNOSIS_FAIL
    ]
    assert len(failed) == 1, failed
    assert 'app_b' in failed[0]['diagnosis']
    assert 'permission denied' in failed[0]['diagnosis']

    # No DBM-specific per-database probes fire (dbm=false or query_samples disabled).
    assert not _by_name(diagnoses, DatabaseConfigurationError.missing_datadog_schema.value)
    assert not _by_name(diagnoses, DatabaseConfigurationError.undefined_explain_function.value)


# -- Subfeature gating --------------------------------------------------------


@pytest.mark.parametrize(
    'disabled,gated,still_running',
    [
        (
            'query_metrics',
            {
                DatabaseConfigurationError.shared_preload_libraries_missing_pg_stat_statements.value,
                DatabaseConfigurationError.track_io_timing_disabled.value,
                DatabaseConfigurationError.high_pg_stat_statements_max.value,
                DatabaseConfigurationError.pg_stat_statements_not_created.value,
                DatabaseConfigurationError.pg_stat_statements_not_readable.value,
            },
            DatabaseConfigurationError.undefined_explain_function.value,
        ),
        (
            'query_samples',
            {
                DatabaseConfigurationError.missing_datadog_schema.value,
                DatabaseConfigurationError.undefined_explain_function.value,
            },
            DatabaseConfigurationError.pg_stat_statements_not_created.value,
        ),
    ],
)
def test_dbm_subfeature_disabled_skips_prerequisite_probes(
    integration_check, pg_instance, disabled, gated, still_running
):
    """Disabling a subfeature drops its prerequisites without affecting the other subfeature."""
    check = _dbm_check(integration_check, pg_instance, **{disabled: {'enabled': False}})
    # Use responses that would FAIL the gated probes if they ran.
    server = _happy_server_responses(spl='pgaudit') if disabled == 'query_metrics' else _happy_server_responses()
    dbm = [
        (_schema('datadog'), [] if disabled == 'query_samples' else [(1,)]),
        ("has_schema_privilege", [(True,)]),
        (_extension_schema('pg_stat_statements'), [] if disabled == 'query_metrics' else [('public',)]),
        (
            'SELECT 1 FROM "pg_stat_statements" LIMIT 1',
            psycopg.errors.UndefinedTable('boom') if disabled == 'query_metrics' else [(1,)],
        ),
        (
            _explain_call(),
            psycopg.errors.UndefinedFunction('does not exist')
            if disabled == 'query_samples'
            else _successful_explain(),
        ),
    ]
    diagnoses = _run(check, server + dbm)
    assert not any(d['name'] in gated for d in diagnoses), [d['name'] for d in diagnoses if d['name'] in gated]
    assert _by_name(diagnoses, still_running)


def test_dbm_with_both_subfeatures_disabled_still_runs_track_activity_query_size(integration_check, pg_instance):
    """query_activity defaults to enabled and reads pg_stat_activity.query, so the
    track_activity_query_size warning still applies even when metrics+samples are off."""
    check = _dbm_check(
        integration_check,
        pg_instance,
        query_metrics={'enabled': False},
        query_samples={'enabled': False},
    )
    diagnoses = _run(check, _happy_server_responses(track_query_size=1024))
    entry = _by_name(diagnoses, DatabaseConfigurationError.track_activity_query_size_too_small.value)[0]
    assert entry['result'] == Diagnosis.DIAGNOSIS_WARNING


# -- pg_stat_statements_view misconfiguration --------------------------------


def test_pg_stat_statements_readable_fails_when_view_misconfigured(integration_check, pg_instance):
    """Extension is installed but `pg_stat_statements_view` points at a nonexistent name.
    This can no longer be swallowed by the UndefinedTable fast-path; the user needs a FAIL."""
    check = _dbm_check(integration_check, pg_instance, pg_stat_statements_view='public.wrong_view')
    dbm_responses = [
        (_schema('datadog'), [(1,)]),
        ("has_schema_privilege", [(True,)]),
        (_extension_schema('pg_stat_statements'), [('public',)]),
        # But the configured view doesn't exist.
        ('"public"."wrong_view"', psycopg.errors.UndefinedTable('relation "public.wrong_view" does not exist')),
        (_explain_call(), _successful_explain()),
    ]
    diagnoses = _run(check, _happy_server_responses() + dbm_responses)
    entry = _by_name(diagnoses, DatabaseConfigurationError.pg_stat_statements_not_readable.value)[0]
    assert entry['result'] == Diagnosis.DIAGNOSIS_FAIL
    assert 'public.wrong_view' in entry['diagnosis']


def test_pg_stat_statements_readable_reports_extension_schema_outside_search_path(integration_check, pg_instance):
    check = _dbm_check(integration_check, pg_instance)
    dbm_responses = [
        (_schema('datadog'), [(1,)]),
        ("has_schema_privilege", [(True,)]),
        (_extension_schema('pg_stat_statements'), [('extensions',)]),
        (
            'SELECT 1 FROM "pg_stat_statements" LIMIT 1',
            psycopg.errors.UndefinedTable('relation "pg_stat_statements" does not exist'),
        ),
        (_explain_call(), _successful_explain()),
    ]
    diagnoses = _run(check, _happy_server_responses() + dbm_responses)

    entry = _by_name(diagnoses, DatabaseConfigurationError.pg_stat_statements_not_readable.value)[0]
    assert entry['result'] == Diagnosis.DIAGNOSIS_FAIL
    assert 'schema `extensions`' in entry['diagnosis']
    assert 'pg_stat_statements_view: extensions.pg_stat_statements' in entry['remediation']


# -- Unqualified explain_function resolution ---------------------------------


@pytest.mark.parametrize(
    'explain_result,expected_result,assert_in_diagnosis',
    [
        (_successful_explain(), Diagnosis.DIAGNOSIS_SUCCESS, None),
        (
            psycopg.errors.UndefinedFunction('function explain_statement does not exist'),
            Diagnosis.DIAGNOSIS_FAIL,
            'explain_statement',
        ),
    ],
)
def test_unqualified_explain_function(
    integration_check, pg_instance, explain_result, expected_result, assert_in_diagnosis
):
    """Runtime calls `SELECT explain_statement(...)` and lets Postgres' search_path find it.
    The diagnose lookup must follow the same resolution rules rather than hardcoding `public`,
    and the datadog-schema probe must not run when the function is unqualified."""
    check = _dbm_check(integration_check, pg_instance, query_samples={'explain_function': 'explain_statement'})
    dbm_responses = [
        # Unqualified function -> datadog schema probe must not run (no explicit `datadog.`).
        (_schema('datadog'), []),
        ("has_schema_privilege", [(True,)]),
        (_extension_schema('pg_stat_statements'), [('public',)]),
        ('SELECT 1 FROM "pg_stat_statements" LIMIT 1', [(1,)]),
        (_explain_call('explain_statement'), explain_result),
    ]
    diagnoses = _run(check, _happy_server_responses() + dbm_responses)
    assert not _by_name(diagnoses, DatabaseConfigurationError.missing_datadog_schema.value)
    explain = _by_name(diagnoses, DatabaseConfigurationError.undefined_explain_function.value)[0]
    assert explain['result'] == expected_result
    if assert_in_diagnosis:
        assert assert_in_diagnosis in explain['diagnosis']


# -- Cascade skipping ---------------------------------------------------------


def test_cascade_skip_spl_missing_suppresses_pgss_extension_and_readable(integration_check, pg_instance):
    """When SPL lacks pg_stat_statements, the extension+readable FAILs add no information --
    `CREATE EXTENSION` can't succeed until SPL is fixed and the server restarted. Subsumes the
    basic SPL-FAIL case: the root-cause diagnosis is asserted here."""
    check = _dbm_check(integration_check, pg_instance)
    # If the extension/readable diagnostics did run, these would fail — but they shouldn't run.
    dbm_responses = _override(_happy_dbm_responses(), _extension_schema('pg_stat_statements'), [])
    dbm_responses = _override(
        dbm_responses,
        'SELECT 1 FROM "pg_stat_statements" LIMIT 1',
        psycopg.errors.UndefinedTable('does not exist'),
    )
    diagnoses = _run(check, _happy_server_responses(spl='pgaudit') + dbm_responses)
    # Root cause still reported, with the extension name in the diagnosis text.
    spl_entry = _by_name(
        diagnoses,
        DatabaseConfigurationError.shared_preload_libraries_missing_pg_stat_statements.value,
    )[0]
    assert spl_entry['result'] == Diagnosis.DIAGNOSIS_FAIL
    assert 'pg_stat_statements' in spl_entry['diagnosis']
    # Downstream diagnostics skipped entirely (no entry, not even SUCCESS).
    assert not _by_name(diagnoses, DatabaseConfigurationError.pg_stat_statements_not_created.value)
    assert not _by_name(diagnoses, DatabaseConfigurationError.pg_stat_statements_not_readable.value)


def test_cascade_skip_pg_monitor_missing_suppresses_pg_stat_activity_warning(integration_check, pg_instance):
    """Without pg_monitor, pg_stat_activity masking is a symptom -- the root cause is the role FAIL."""
    check = integration_check(dict(pg_instance, collect_activity_metrics=True))
    responses = _override(_happy_server_responses(), 'pg_has_role', [(False,)])
    # Flip the pg_stat_activity masked-row count to non-zero, so the WARNING *would* fire absent cascade.
    responses = _override(responses, 'query = %s', [(16,)])
    diagnoses = _run(check, responses)
    role_entry = _by_name(diagnoses, DatabaseConfigurationError.missing_pg_monitor_role.value)[0]
    assert role_entry['result'] == Diagnosis.DIAGNOSIS_FAIL
    assert not _by_name(diagnoses, DatabaseConfigurationError.insufficient_privilege_on_pg_stat_activity.value)


def test_cascade_skip_missing_schema_suppresses_explain_function_in_datadog_schema(integration_check, pg_instance):
    """When `datadog` schema is missing, `datadog.explain_statement` can't exist -- the schema
    FAIL is the actionable item; don't emit an explain-function FAIL with a nonsensical fix.
    Subsumes the basic missing-schema FAIL case."""
    check = _dbm_check(integration_check, pg_instance)
    dbm_responses = _override(_happy_dbm_responses(), _schema('datadog'), [])
    # If the explain-function diagnostic did run, this would produce a FAIL — but it shouldn't run.
    dbm_responses = _override(
        dbm_responses,
        _explain_call(),
        psycopg.errors.UndefinedFunction('function datadog.explain_statement does not exist'),
    )
    diagnoses = _run(check, _happy_server_responses() + dbm_responses)
    schema = _by_name(diagnoses, DatabaseConfigurationError.missing_datadog_schema.value)[0]
    assert schema['result'] == Diagnosis.DIAGNOSIS_FAIL
    assert not _by_name(diagnoses, DatabaseConfigurationError.undefined_explain_function.value)


def test_custom_explain_function_schema_skips_datadog_schema_check(integration_check, pg_instance):
    """If the user configured an explain_function outside the `datadog` schema, the
    `datadog` schema is not a DBM prerequisite -- the schema check short-circuits entirely
    (no success, warning, or fail row) and the function check carries the DBM verdict."""
    check = _dbm_check(integration_check, pg_instance, query_samples={'explain_function': 'public.my_explain'})
    dbm_responses = [
        # `datadog` schema is absent -- but since the configured function lives in `public`,
        # _diagnose_datadog_schema must early-return without emitting a missing-schema row.
        (_schema('datadog'), []),
        (_schema('public'), [(1,)]),
        ("has_schema_privilege", [(True,)]),
        (_extension_schema('pg_stat_statements'), [('public',)]),
        ('SELECT 1 FROM "pg_stat_statements" LIMIT 1', [(1,)]),
        (_explain_call('public.my_explain'), _successful_explain()),
    ]
    diagnoses = _run(check, _happy_server_responses() + dbm_responses)
    # No `missing-datadog-schema` diagnosis emitted at all -- success or fail would both be wrong.
    assert not _by_name(diagnoses, DatabaseConfigurationError.missing_datadog_schema.value)
    # The explain-function diagnostic ran and passed (function exists in public).
    explain = _by_name(diagnoses, DatabaseConfigurationError.undefined_explain_function.value)[0]
    assert explain['result'] == Diagnosis.DIAGNOSIS_SUCCESS


def test_custom_explain_function_still_checks_existing_datadog_schema_usage(integration_check, pg_instance):
    check = _dbm_check(integration_check, pg_instance, query_samples={'explain_function': 'public.my_explain'})

    def datadog_usage(sql, params):
        return 'has_schema_privilege' in sql and params == ('datadog',)

    datadog_usage.__qualname__ = "datadog_usage"

    dbm_responses = [
        (_schema('datadog'), [(1,)]),
        (_schema('public'), [(1,)]),
        (datadog_usage, [(False,)]),
        ("has_schema_privilege", [(True,)]),
        (_extension_schema('pg_stat_statements'), [('public',)]),
        ('SELECT 1 FROM "pg_stat_statements" LIMIT 1', [(1,)]),
        (_explain_call('public.my_explain'), _successful_explain()),
    ]
    diagnoses = _run(check, _happy_server_responses() + dbm_responses)

    usage_rows = _by_name(diagnoses, DatabaseConfigurationError.missing_schema_usage_grant.value)
    fail_rows = [d for d in usage_rows if d['result'] == Diagnosis.DIAGNOSIS_FAIL]
    assert len(fail_rows) == 1
    assert 'datadog' in fail_rows[0]['diagnosis']
    explain = _by_name(diagnoses, DatabaseConfigurationError.undefined_explain_function.value)[0]
    assert explain['result'] == Diagnosis.DIAGNOSIS_SUCCESS


def test_custom_explain_function_guidance_uses_override(integration_check, pg_instance):
    check = _dbm_check(integration_check, pg_instance, query_samples={'explain_function': 'public.my_explain'})
    dbm_responses = [
        (_schema('public'), [(1,)]),
        ("has_schema_privilege", [(True,)]),
        (_extension_schema('pg_stat_statements'), [('public',)]),
        ('SELECT 1 FROM "pg_stat_statements" LIMIT 1', [(1,)]),
        (
            _explain_call('public.my_explain'),
            psycopg.errors.UndefinedFunction('function public.my_explain does not exist'),
        ),
    ]
    diagnoses = _run(check, _happy_server_responses() + dbm_responses)

    explain = _by_name(diagnoses, DatabaseConfigurationError.undefined_explain_function.value)[0]
    assert explain['result'] == Diagnosis.DIAGNOSIS_FAIL
    assert 'public.my_explain' in explain['description']
    assert 'public.my_explain' in explain['remediation']
    assert 'datadog.explain_statement' not in explain['description']
    assert 'datadog.explain_statement' not in explain['remediation']


# -- Internal helpers ---------------------------------------------------------


@pytest.mark.parametrize(
    'name,expected',
    [
        ('pg_stat_activity', '"pg_stat_activity"'),
        ('datadog.pg_stat_statements', '"datadog"."pg_stat_statements"'),
        ('datadog.pg_stat_activity()', '"datadog"."pg_stat_activity"()'),
    ],
)
def test_safe_identifier_accepts(name, expected):
    assert _safe_identifier(name) == expected


@pytest.mark.parametrize('name', ['', 'foo; drop table x', 'a.b.c', "a'b", '"injected"'])
def test_safe_identifier_rejects(name):
    with pytest.raises(ValueError):
        _safe_identifier(name)


@pytest.mark.parametrize(
    'name,expected',
    [
        ('datadog.explain_statement', ('datadog', 'explain_statement')),
        # Unqualified -> None schema; resolved via search_path at call time.
        ('explain_statement', (None, 'explain_statement')),
    ],
)
def test_split_function(name, expected):
    assert _split_function(name) == expected


# -- Remediation text ---------------------------------------------------------


def test_build_remediation_has_docs_url_for_every_code():
    for code in DatabaseConfigurationError:
        remediation = build_remediation(code)
        assert 'troubleshooting' in remediation
        assert remediation.endswith('for details.')


def test_pg_stat_statements_not_created_metadata_renders_database_name():
    code = DatabaseConfigurationError.pg_stat_statements_not_created

    assert '{dbname}' not in build_description(code)
    assert '{dbname}' not in build_remediation(code)
    assert 'the monitored database' in build_description(code)
    assert 'the monitored database' in build_remediation(code)

    assert 'app_db' in build_description(code, dbname='app_db')
    assert 'app_db' in build_remediation(code, dbname='app_db')


# -- config-validation diagnostic --------------------------------------------


def _make_validation_result(errors=(), warnings=(), features=()):
    from datadog_checks.postgres.config import ValidationResult

    vr = ValidationResult()
    for err in errors:
        vr.add_error(err)
    for w in warnings:
        vr.add_warning(w)
    for feat in features:
        vr.features.append(feat)
    return vr


def _feature(key, enabled):
    from datadog_checks.postgres.features import Feature, FeatureKey, FeatureNames

    return Feature(key=FeatureKey(key), name=FeatureNames[FeatureKey(key)], enabled=enabled, description=None)


def _config_validation_entries(diagnoses):
    return _by_name(diagnoses, DatabaseConfigurationError.config_validation.value)


def test_config_validation_ok(integration_check, pg_instance):
    check = integration_check(pg_instance)
    check._validation_result = _make_validation_result()
    diagnoses = _run(check, _happy_server_responses())

    entries = _config_validation_entries(diagnoses)
    assert len(entries) == 1
    entry = entries[0]
    assert entry['result'] == Diagnosis.DIAGNOSIS_SUCCESS
    assert entry['diagnosis'] == "Postgres config validation: 0 error(s), 0 warning(s)."


def test_config_validation_warning(integration_check, pg_instance):
    check = integration_check(pg_instance)
    check._validation_result = _make_validation_result(
        warnings=["The `statement_samples` option is deprecated. Use `query_samples` instead."],
    )
    diagnoses = _run(check, _happy_server_responses())

    entry = _config_validation_entries(diagnoses)[0]
    assert entry['result'] == Diagnosis.DIAGNOSIS_WARNING
    assert "0 error(s), 1 warning(s)" in entry['diagnosis']
    assert "Warnings:" in entry['description']
    assert "statement_samples" in entry['description']


def test_config_validation_error(integration_check, pg_instance):
    from datadog_checks.base import ConfigurationError

    check = integration_check(pg_instance)
    check._validation_result = _make_validation_result(
        errors=[ConfigurationError("Application name can include only ASCII characters: foo")],
    )
    diagnoses = _run(check, _happy_server_responses())

    entry = _config_validation_entries(diagnoses)[0]
    assert entry['result'] == Diagnosis.DIAGNOSIS_FAIL
    assert "1 error(s), 0 warning(s)" in entry['diagnosis']
    assert "Errors:" in entry['description']
    assert "Application name can include only ASCII characters: foo" in entry['description']
    assert entry['remediation'] == (
        "Resolve the errors and warnings listed above by editing the Postgres integration configuration "
        "for this instance, then restart the agent."
    )


def test_config_validation_emits_when_connection_fails(integration_check, pg_instance):
    check = integration_check(pg_instance)
    check._validation_result = _make_validation_result(warnings=["invalid ssl option"])
    err = psycopg.OperationalError('could not connect')
    with mock.patch('datadog_checks.postgres.postgres.TokenAwareConnection.connect', side_effect=err):
        diagnoses = _get_diagnoses(check)

    entries = _config_validation_entries(diagnoses)
    assert len(entries) == 1
    assert entries[0]['result'] == Diagnosis.DIAGNOSIS_WARNING
    # connection_failure still fires alongside config-validation.
    assert _by_name(diagnoses, DatabaseConfigurationError.connection_failure.value)


def test_config_validation_handles_missing_validation_result(integration_check, pg_instance):
    check = integration_check(pg_instance)
    check._validation_result = None
    diagnoses = _run(check, _happy_server_responses())
    entry = _config_validation_entries(diagnoses)[0]
    assert entry['result'] == Diagnosis.DIAGNOSIS_WARNING
    assert entry['diagnosis'] == "Postgres config validation did not complete (check initialization failed)."


def test_config_validation_renders_features(integration_check, pg_instance):
    check = integration_check(pg_instance)
    check._validation_result = _make_validation_result(
        warnings=["some warning"],
        features=[
            _feature("query_metrics", enabled=True),
            _feature("query_samples", enabled=True),
            _feature("relation_metrics", enabled=False),
            _feature("collect_schemas", enabled=False),
        ],
    )
    diagnoses = _run(check, _happy_server_responses())
    entry = _config_validation_entries(diagnoses)[0]
    assert "Features enabled: query_metrics, query_samples" in entry['description']
    assert "Features disabled: relation_metrics, collect_schemas" in entry['description']


def test_config_validation_strings_are_neutral(integration_check, pg_instance):
    """No user-facing string may reference the internal surface this probe mirrors."""
    from datadog_checks.base import ConfigurationError

    check = integration_check(pg_instance)
    check._validation_result = _make_validation_result(
        errors=[ConfigurationError("bad config")],
        warnings=["deprecated option"],
        features=[_feature("query_metrics", enabled=True)],
    )
    diagnoses = _run(check, _happy_server_responses())

    entry = _config_validation_entries(diagnoses)[0]
    forbidden = ("agent health", "health event", "dbm-health", "dbm_health")
    for field in ('diagnosis', 'description', 'remediation'):
        text = (entry.get(field) or "").lower()
        for token in forbidden:
            assert token not in text, "{} leaked forbidden token {!r}: {!r}".format(field, token, entry.get(field))
