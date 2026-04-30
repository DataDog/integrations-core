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
    return mock.patch('datadog_checks.postgres.diagnose.TokenAwareConnection.connect', return_value=conn)


def _explain_call(name='datadog.explain_statement'):
    return "SELECT {}(%s)".format(_safe_identifier(name))


def _successful_explain():
    return [('plan',)]


def _main_database_only_connection(dbname, conn):
    def connect(**kwargs):
        if kwargs['dbname'] != dbname:
            raise psycopg.OperationalError('unexpected database probe')
        return conn

    return connect


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


def test_connection_fails_surfaces_fail(integration_check, pg_instance):
    check = integration_check(pg_instance)
    err = psycopg.OperationalError('could not connect')
    with mock.patch('datadog_checks.postgres.diagnose.TokenAwareConnection.connect', side_effect=err):
        diagnoses = _get_diagnoses(check)

    conn_fail = _by_name(diagnoses, DatabaseConfigurationError.connection_failure.value)
    assert len(conn_fail) == 1  # connection & dbm orchestrators both call open; DBM skipped when dbm=false
    assert conn_fail[0]['result'] == Diagnosis.DIAGNOSIS_FAIL
    assert 'could not connect' in conn_fail[0]['diagnosis']
    assert 'troubleshooting' in conn_fail[0]['remediation']


def test_connection_fails_dbm_enabled_reports_once(integration_check, pg_instance):
    """With dbm=true, the single orchestrator opens one probe connection -- one FAIL row."""
    check = integration_check(dict(pg_instance, dbm=True))
    err = psycopg.OperationalError('boom')
    with mock.patch('datadog_checks.postgres.diagnose.TokenAwareConnection.connect', side_effect=err) as connect:
        diagnoses = _get_diagnoses(check)
    assert connect.call_count == 1
    conn_diags = _by_name(diagnoses, DatabaseConfigurationError.connection_failure.value)
    assert len(conn_diags) == 1
    assert conn_diags[0]['result'] == Diagnosis.DIAGNOSIS_FAIL


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
        ("query = %s", [(0,)]),
    ]


def test_server_config_happy_path(integration_check, pg_instance):
    """Non-DBM without activity metrics does not require pg_monitor or pg_stat_activity."""
    check = integration_check(pg_instance)
    conn = FakeConn(_happy_server_responses())
    with _patch_connection(check, conn):
        diagnoses = _get_diagnoses(check)

    names_and_results = {(d['name'], d['result']) for d in diagnoses}
    assert (
        DatabaseConfigurationError.postgres_version_unsupported.value,
        Diagnosis.DIAGNOSIS_SUCCESS,
    ) in names_and_results
    assert not _by_name(diagnoses, DatabaseConfigurationError.missing_pg_monitor_role.value)
    assert not _by_name(diagnoses, DatabaseConfigurationError.insufficient_privilege_on_pg_stat_activity.value)


def test_dbm_server_config_happy_path(integration_check, pg_instance):
    """With dbm=true the DBM-gated GUC diagnostics also run and should all succeed on a healthy
    Postgres."""
    check = integration_check(dict(pg_instance, dbm=True))
    conn = FakeConn(_happy_server_responses() + _happy_dbm_responses())
    with _patch_connection(check, conn):
        diagnoses = _get_diagnoses(check)

    names_and_results = {(d['name'], d['result']) for d in diagnoses}
    for code in (
        DatabaseConfigurationError.shared_preload_libraries_missing_pg_stat_statements,
        DatabaseConfigurationError.track_activity_query_size_too_small,
        DatabaseConfigurationError.track_io_timing_disabled,
        DatabaseConfigurationError.high_pg_stat_statements_max,
    ):
        assert (code.value, Diagnosis.DIAGNOSIS_SUCCESS) in names_and_results, (
            f"expected {code.value} to pass, got {[d for d in diagnoses if d['name'] == code.value]}"
        )


def test_shared_preload_libraries_missing_fails(integration_check, pg_instance):
    check = integration_check(dict(pg_instance, dbm=True))
    responses = _happy_server_responses(spl='pgaudit') + _happy_dbm_responses()
    with _patch_connection(check, FakeConn(responses)):
        diagnoses = _get_diagnoses(check)
    spl = _by_name(
        diagnoses,
        DatabaseConfigurationError.shared_preload_libraries_missing_pg_stat_statements.value,
    )
    assert spl and spl[0]['result'] == Diagnosis.DIAGNOSIS_FAIL
    assert 'pg_stat_statements' in spl[0]['diagnosis']


def test_shared_preload_libraries_unreadable_warns(integration_check, pg_instance):
    """Row is hidden from non-pg_monitor users for GUC_SUPERUSER_ONLY settings -- we should
    surface a WARNING instead of silently dropping the diagnostic."""
    check = integration_check(dict(pg_instance, dbm=True))
    # Replace only the shared_preload_libraries response with an empty result (simulates the
    # pg_settings row being filtered out for non-pg_monitor members).
    responses = [
        (m, r)
        for (m, r) in _happy_server_responses()
        if getattr(m, "__qualname__", "") != _setting('shared_preload_libraries').__qualname__
    ]
    responses.append((_setting('shared_preload_libraries'), []))
    responses += _happy_dbm_responses()
    with _patch_connection(check, FakeConn(responses)):
        diagnoses = _get_diagnoses(check)
    spl = _by_name(
        diagnoses,
        DatabaseConfigurationError.shared_preload_libraries_missing_pg_stat_statements.value,
    )
    assert len(spl) == 1, spl
    assert spl[0]['result'] == Diagnosis.DIAGNOSIS_WARNING
    assert 'pg_monitor' in spl[0]['diagnosis']
    # Remediation should point at the pg_monitor fix.
    assert 'pg_monitor' in spl[0]['remediation']


def test_track_activity_query_size_too_small_warns(integration_check, pg_instance):
    check = integration_check(dict(pg_instance, dbm=True))
    responses = _happy_server_responses(track_query_size=1024) + _happy_dbm_responses()
    with _patch_connection(check, FakeConn(responses)):
        diagnoses = _get_diagnoses(check)
    entry = _by_name(diagnoses, DatabaseConfigurationError.track_activity_query_size_too_small.value)[0]
    assert entry['result'] == Diagnosis.DIAGNOSIS_WARNING
    assert str(RECOMMENDED_TRACK_ACTIVITY_QUERY_SIZE) in entry['diagnosis']


def test_track_io_timing_off_warns(integration_check, pg_instance):
    check = integration_check(dict(pg_instance, dbm=True))
    responses = _happy_server_responses(track_io='off') + _happy_dbm_responses()
    with _patch_connection(check, FakeConn(responses)):
        diagnoses = _get_diagnoses(check)
    entry = _by_name(diagnoses, DatabaseConfigurationError.track_io_timing_disabled.value)[0]
    assert entry['result'] == Diagnosis.DIAGNOSIS_WARNING


def test_pg_stat_statements_max_above_threshold_warns(integration_check, pg_instance):
    check = integration_check(dict(pg_instance, dbm=True))
    # Default threshold is 10000; exceed it.
    responses = _happy_server_responses(pgss_max=50000) + _happy_dbm_responses()
    with _patch_connection(check, FakeConn(responses)):
        diagnoses = _get_diagnoses(check)
    entry = _by_name(diagnoses, DatabaseConfigurationError.high_pg_stat_statements_max.value)[0]
    assert entry['result'] == Diagnosis.DIAGNOSIS_WARNING
    assert '50000' in entry['diagnosis']


def test_unsupported_postgres_version_fails(integration_check, pg_instance):
    check = integration_check(pg_instance)
    responses = _happy_server_responses(server_version='9.5.1')
    with _patch_connection(check, FakeConn(responses)):
        diagnoses = _get_diagnoses(check)
    entry = _by_name(diagnoses, DatabaseConfigurationError.postgres_version_unsupported.value)[0]
    assert entry['result'] == Diagnosis.DIAGNOSIS_FAIL
    assert '9.5' in entry['diagnosis']


# -- Privilege diagnostics ----------------------------------------------------


def test_missing_pg_monitor_role_fails(integration_check, pg_instance):
    check = integration_check(dict(pg_instance, collect_activity_metrics=True))
    responses = _happy_server_responses()
    # Replace the pg_has_role response.
    responses = [(m, [(False,)]) if isinstance(m, str) and m == 'pg_has_role' else (m, r) for m, r in responses]
    with _patch_connection(check, FakeConn(responses)):
        diagnoses = _get_diagnoses(check)
    entry = _by_name(diagnoses, DatabaseConfigurationError.missing_pg_monitor_role.value)[0]
    assert entry['result'] == Diagnosis.DIAGNOSIS_FAIL
    assert 'pg_monitor' in entry['remediation']


def test_insufficient_privilege_on_pg_stat_activity_warns(integration_check, pg_instance):
    check = integration_check(dict(pg_instance, collect_activity_metrics=True))
    responses = _happy_server_responses()
    responses = [(m, [(3,)]) if m == "query = %s" else (m, r) for m, r in responses]
    with _patch_connection(check, FakeConn(responses)):
        diagnoses = _get_diagnoses(check)
    entry = _by_name(diagnoses, DatabaseConfigurationError.insufficient_privilege_on_pg_stat_activity.value)[0]
    assert entry['result'] == Diagnosis.DIAGNOSIS_WARNING
    assert '3' in entry['diagnosis']


# -- DBM diagnostics ----------------------------------------------------------


def _happy_dbm_responses():
    return [
        ("nspname = 'datadog'", [(1,)]),
        # USAGE on `datadog` and `public` is granted -- shared substring across both probes.
        ("has_schema_privilege", [(True,)]),
        ("extname = 'pg_stat_statements'", [(1,)]),
        # pg_stat_statements readable probe — the SQL contains the quoted view name.
        ('SELECT 1 FROM "pg_stat_statements" LIMIT 1', [(1,)]),
        (_explain_call(), _successful_explain()),
    ]


def test_dbm_disabled_skips_dbm_diagnostics(integration_check, pg_instance):
    check = integration_check(pg_instance)  # dbm defaults to False
    conn = FakeConn(_happy_server_responses() + _happy_dbm_responses())
    with _patch_connection(check, conn):
        diagnoses = _get_diagnoses(check)
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
    check = integration_check(dict(pg_instance, dbm=True))
    conn = FakeConn(_happy_server_responses() + _happy_dbm_responses())
    with _patch_connection(check, conn):
        diagnoses = _get_diagnoses(check)
    names_and_results = {(d['name'], d['result']) for d in diagnoses}
    for code in (
        DatabaseConfigurationError.missing_datadog_schema,
        DatabaseConfigurationError.missing_schema_usage_grant,
        DatabaseConfigurationError.pg_stat_statements_not_created,
        DatabaseConfigurationError.pg_stat_statements_not_readable,
        DatabaseConfigurationError.undefined_explain_function,
    ):
        assert (code.value, Diagnosis.DIAGNOSIS_SUCCESS) in names_and_results, (
            f"expected {code.value} to pass, got {[d for d in diagnoses if d['name'] == code.value]}"
        )


def test_missing_datadog_schema_fails(integration_check, pg_instance):
    check = integration_check(dict(pg_instance, dbm=True))
    dbm_responses = [
        ("nspname = 'datadog'", []),
        ("has_schema_privilege", [(True,)]),
        ("extname = 'pg_stat_statements'", [(1,)]),
        ('SELECT 1 FROM "pg_stat_statements" LIMIT 1', [(1,)]),
        (_explain_call(), _successful_explain()),
    ]
    conn = FakeConn(_happy_server_responses() + dbm_responses)
    with _patch_connection(check, conn):
        diagnoses = _get_diagnoses(check)
    entry = _by_name(diagnoses, DatabaseConfigurationError.missing_datadog_schema.value)[0]
    assert entry['result'] == Diagnosis.DIAGNOSIS_FAIL


def test_missing_pg_stat_statements_extension_fails(integration_check, pg_instance):
    check = integration_check(dict(pg_instance, dbm=True))
    dbm_responses = [
        ("nspname = 'datadog'", [(1,)]),
        ("has_schema_privilege", [(True,)]),
        ("extname = 'pg_stat_statements'", []),
        # Simulate extension missing: the readable probe would raise UndefinedTable, swallowed silently.
        (
            'SELECT 1 FROM "pg_stat_statements" LIMIT 1',
            psycopg.errors.UndefinedTable('relation "pg_stat_statements" does not exist'),
        ),
        (_explain_call(), _successful_explain()),
    ]
    conn = FakeConn(_happy_server_responses() + dbm_responses)
    with _patch_connection(check, conn):
        diagnoses = _get_diagnoses(check)
    created = _by_name(diagnoses, DatabaseConfigurationError.pg_stat_statements_not_created.value)[0]
    assert created['result'] == Diagnosis.DIAGNOSIS_FAIL
    # readable probe is suppressed when UndefinedTable raised (to avoid double-report)
    assert not _by_name(diagnoses, DatabaseConfigurationError.pg_stat_statements_not_readable.value)


def test_missing_explain_function_fails(integration_check, pg_instance):
    check = integration_check(dict(pg_instance, dbm=True))
    dbm_responses = [
        ("nspname = 'datadog'", [(1,)]),
        ("has_schema_privilege", [(True,)]),
        ("extname = 'pg_stat_statements'", [(1,)]),
        ('SELECT 1 FROM "pg_stat_statements" LIMIT 1', [(1,)]),
        (_explain_call(), psycopg.errors.UndefinedFunction('function datadog.explain_statement does not exist')),
    ]
    conn = FakeConn(_happy_server_responses() + dbm_responses)
    with _patch_connection(check, conn):
        diagnoses = _get_diagnoses(check)
    entry = _by_name(diagnoses, DatabaseConfigurationError.undefined_explain_function.value)[0]
    assert entry['result'] == Diagnosis.DIAGNOSIS_FAIL
    assert 'explain_statement' in entry['diagnosis']


def test_explain_function_with_trailing_parens_succeeds(integration_check, pg_instance):
    """explain_function configured with trailing () should not produce invalid SQL."""
    fn = 'datadog.explain_statement()'
    instance = dict(pg_instance, dbm=True, query_samples={'explain_function': fn})
    check = integration_check(instance)
    dbm_responses = [
        ("nspname = 'datadog'", [(1,)]),
        ("has_schema_privilege", [(True,)]),
        ("extname = 'pg_stat_statements'", [(1,)]),
        ('SELECT 1 FROM "pg_stat_statements" LIMIT 1', [(1,)]),
        (_explain_call('datadog.explain_statement'), _successful_explain()),
    ]
    conn = FakeConn(_happy_server_responses() + dbm_responses)
    with _patch_connection(check, conn):
        diagnoses = _get_diagnoses(check)
    entries = _by_name(diagnoses, DatabaseConfigurationError.undefined_explain_function.value)
    assert len(entries) == 1
    assert entries[0]['result'] == Diagnosis.DIAGNOSIS_SUCCESS


def test_query_samples_probes_each_monitored_database(integration_check, pg_instance):
    instance = dict(pg_instance, dbm=True, query_metrics={'enabled': False})
    check = integration_check(instance)
    connections = {
        pg_instance['dbname']: FakeConn(
            _happy_server_responses()
            + [
                ("pg_catalog.pg_database", [(pg_instance['dbname'],), ('broken_schema',), ('broken_function',)]),
                ("nspname = 'datadog'", [(1,)]),
                ("has_schema_privilege", [(True,)]),
                (_explain_call(), _successful_explain()),
            ]
        ),
        'broken_schema': FakeConn([("nspname = 'datadog'", [])]),
        'broken_function': FakeConn(
            [
                ("nspname = 'datadog'", [(1,)]),
                ("has_schema_privilege", [(True,)]),
                (
                    _explain_call(),
                    psycopg.errors.UndefinedFunction('function datadog.explain_statement does not exist'),
                ),
            ]
        ),
    }
    with mock.patch(
        'datadog_checks.postgres.diagnose.TokenAwareConnection.connect',
        side_effect=lambda **kwargs: connections[kwargs['dbname']],
    ):
        diagnoses = _get_diagnoses(check)

    missing_schema = _by_name(diagnoses, DatabaseConfigurationError.missing_datadog_schema.value)
    assert any(d['result'] == Diagnosis.DIAGNOSIS_FAIL and 'broken_schema' in d['diagnosis'] for d in missing_schema), (
        missing_schema
    )

    missing_explain = _by_name(diagnoses, DatabaseConfigurationError.undefined_explain_function.value)
    assert any(
        d['result'] == Diagnosis.DIAGNOSIS_FAIL and 'broken_function' in d['diagnosis'] for d in missing_explain
    ), missing_explain


# -- Autodiscovery-aware query-samples enumeration ---------------------------


def test_query_samples_uses_autodiscovery_when_enabled(integration_check, pg_instance):
    """When database_autodiscovery is enabled, the per-DB query-samples probes run against
    the autodiscovery set, not every non-template DB in pg_database."""
    instance = dict(
        pg_instance,
        dbm=True,
        database_autodiscovery={'enabled': True, 'include': ['app_.*'], 'max_databases': 2},
    )
    check = integration_check(instance)
    connections = {
        pg_instance['dbname']: FakeConn(_happy_server_responses() + _happy_dbm_responses()),
        'app_a': FakeConn(_happy_dbm_responses()),
        'app_b': FakeConn(_happy_dbm_responses()),
    }
    with mock.patch.object(check.autodiscovery, 'get_items', return_value=['app_a', 'app_b']):
        with mock.patch(
            'datadog_checks.postgres.diagnose.TokenAwareConnection.connect',
            side_effect=lambda **kwargs: connections[kwargs['dbname']],
        ) as connect:
            _get_diagnoses(check)
    opened_dbnames = {call.kwargs['dbname'] for call in connect.call_args_list}
    assert opened_dbnames == {pg_instance['dbname'], 'app_a', 'app_b'}


def test_query_samples_autodiscovery_empty_falls_back_to_pg_database(integration_check, pg_instance):
    """autodiscovery enabled but returns empty -> fall through to pg_database enumeration."""
    instance = dict(
        pg_instance,
        dbm=True,
        database_autodiscovery={'enabled': True, 'include': ['matches_nothing_.*']},
    )
    check = integration_check(instance)
    responses = (
        _happy_server_responses() + [("pg_catalog.pg_database", [(pg_instance['dbname'],)])] + _happy_dbm_responses()
    )
    with mock.patch.object(check.autodiscovery, 'get_items', return_value=[]):
        with _patch_connection(check, FakeConn(responses)) as connect:
            _get_diagnoses(check)
    opened_dbnames = {call.kwargs['dbname'] for call in connect.call_args_list}
    assert opened_dbnames == {pg_instance['dbname']}


def test_query_samples_autodiscovery_raises_falls_back_gracefully(integration_check, pg_instance):
    """autodiscovery enabled, get_items() raises -> fall through to pg_database without crashing."""
    instance = dict(
        pg_instance,
        dbm=True,
        database_autodiscovery={'enabled': True, 'include': ['.*']},
    )
    check = integration_check(instance)
    responses = (
        _happy_server_responses() + [("pg_catalog.pg_database", [(pg_instance['dbname'],)])] + _happy_dbm_responses()
    )
    with mock.patch.object(check.autodiscovery, 'get_items', side_effect=psycopg.OperationalError('boom')):
        with _patch_connection(check, FakeConn(responses)):
            diagnoses = _get_diagnoses(check)
    # Diagnose completed without crashing; config-validation still emits at the bottom.
    assert _by_name(diagnoses, DatabaseConfigurationError.config_validation.value)


def test_query_samples_dbstrict_short_circuits_regardless_of_autodiscovery(integration_check, pg_instance):
    """`dbstrict` wins: the probe set is always [dbname] regardless of autodiscovery state,
    matching the sample collector's runtime filter in statement_samples.py."""
    for ad_enabled in (True, False):
        ad_config = {'enabled': True, 'include': ['.*']} if ad_enabled else {'enabled': False}
        instance = dict(pg_instance, dbm=True, dbstrict=True, database_autodiscovery=ad_config)
        check = integration_check(instance)
        responses = _happy_server_responses() + _happy_dbm_responses()

        if ad_enabled and check.autodiscovery is not None:
            with mock.patch.object(check.autodiscovery, 'get_items') as gi:
                with _patch_connection(check, FakeConn(responses)) as connect:
                    _get_diagnoses(check)
                assert not gi.called, "dbstrict should short-circuit before autodiscovery"
        else:
            with _patch_connection(check, FakeConn(responses)) as connect:
                _get_diagnoses(check)
        opened_dbnames = {call.kwargs['dbname'] for call in connect.call_args_list}
        assert opened_dbnames == {pg_instance['dbname']}, "ad_enabled={}: got {}".format(ad_enabled, opened_dbnames)


# -- Per-database DBM probes (autodiscovery + cluster-level checks) ----------


def test_query_metrics_pg_stat_statements_checked_on_main_database_only(integration_check, pg_instance):
    """Statement metrics read pg_stat_statements from the main DB only, even with autodiscovery."""
    instance = dict(
        pg_instance,
        dbm=True,
        query_samples={'enabled': False},
        query_activity={'enabled': False},
        database_autodiscovery={'enabled': True, 'include': ['app_.*']},
    )
    check = integration_check(instance)
    main_dbm = [
        ("extname = 'pg_stat_statements'", [(1,)]),
        ('SELECT 1 FROM "pg_stat_statements" LIMIT 1', [(1,)]),
    ]
    with mock.patch.object(check.autodiscovery, 'get_items', return_value=['app_a', 'app_b']):
        with mock.patch(
            'datadog_checks.postgres.diagnose.TokenAwareConnection.connect',
            side_effect=_main_database_only_connection(
                pg_instance['dbname'], FakeConn(_happy_server_responses() + main_dbm)
            ),
        ) as connect:
            diagnoses = _get_diagnoses(check)

    assert {call.kwargs['dbname'] for call in connect.call_args_list} == {pg_instance['dbname']}
    rows = _by_name(diagnoses, DatabaseConfigurationError.pg_stat_statements_not_created.value)
    assert len(rows) == 1
    assert rows[0]['result'] == Diagnosis.DIAGNOSIS_SUCCESS
    assert pg_instance['dbname'] in rows[0]['diagnosis']


def test_query_metrics_pg_stat_statements_readable_checked_on_main_database_only(integration_check, pg_instance):
    """A broken pg_stat_statements view in another database should not fail query-metrics diagnose."""
    instance = dict(
        pg_instance,
        dbm=True,
        query_samples={'enabled': False},
        query_activity={'enabled': False},
        database_autodiscovery={'enabled': True, 'include': ['app_.*']},
        pg_stat_statements_view='public.wrong_view',
    )
    check = integration_check(instance)
    main_dbm = [
        ("extname = 'pg_stat_statements'", [(1,)]),
        ('"public"."wrong_view"', [(1,)]),
    ]
    with mock.patch.object(check.autodiscovery, 'get_items', return_value=['app_a', 'app_b']):
        with mock.patch(
            'datadog_checks.postgres.diagnose.TokenAwareConnection.connect',
            side_effect=_main_database_only_connection(
                pg_instance['dbname'], FakeConn(_happy_server_responses() + main_dbm)
            ),
        ) as connect:
            diagnoses = _get_diagnoses(check)

    assert {call.kwargs['dbname'] for call in connect.call_args_list} == {pg_instance['dbname']}
    rows = _by_name(diagnoses, DatabaseConfigurationError.pg_stat_statements_not_readable.value)
    assert len(rows) == 1
    assert rows[0]['result'] == Diagnosis.DIAGNOSIS_SUCCESS
    assert pg_instance['dbname'] in rows[0]['diagnosis']


def test_schema_usage_grant_fails_when_missing(integration_check, pg_instance):
    """Documented setup step `GRANT USAGE ON SCHEMA public TO datadog` must be verified --
    a catalog-only check would mask this since pg_proc joins succeed without USAGE."""
    check = integration_check(dict(pg_instance, dbm=True))

    def usage_predicate(sql, params):
        return 'has_schema_privilege' in sql and params == ('public',)

    usage_predicate.__qualname__ = "usage_predicate(public)"

    dbm_responses = [
        ("nspname = 'datadog'", [(1,)]),
        # USAGE on `datadog` granted, but USAGE on `public` denied.
        (usage_predicate, [(False,)]),
        ("has_schema_privilege", [(True,)]),
        ("extname = 'pg_stat_statements'", [(1,)]),
        ('SELECT 1 FROM "pg_stat_statements" LIMIT 1', [(1,)]),
        (_explain_call(), _successful_explain()),
    ]
    conn = FakeConn(_happy_server_responses() + dbm_responses)
    with _patch_connection(check, conn):
        diagnoses = _get_diagnoses(check)

    rows = _by_name(diagnoses, DatabaseConfigurationError.missing_schema_usage_grant.value)
    fail_rows = [d for d in rows if d['result'] == Diagnosis.DIAGNOSIS_FAIL]
    assert len(fail_rows) == 1, rows
    assert 'public' in fail_rows[0]['diagnosis']
    assert 'GRANT USAGE ON SCHEMA public' in fail_rows[0]['remediation']


def test_schema_usage_grant_per_autodiscovered_database(integration_check, pg_instance):
    """USAGE grants are per-database; missing USAGE on `datadog` in one DB only must
    produce a FAIL row scoped to that DB."""
    instance = dict(
        pg_instance,
        dbm=True,
        database_autodiscovery={'enabled': True, 'include': ['app_.*']},
    )
    check = integration_check(instance)
    healthy_dbm = _happy_dbm_responses()
    # In app_b, the datadog schema exists but USAGE is denied.
    broken_dbm = [
        ("nspname = 'datadog'", [(1,)]),
        ("has_schema_privilege", [(False,)]),
        ("extname = 'pg_stat_statements'", [(1,)]),
        ('SELECT 1 FROM "pg_stat_statements" LIMIT 1', [(1,)]),
        (_explain_call(), _successful_explain()),
    ]
    connections = {
        pg_instance['dbname']: FakeConn(_happy_server_responses() + healthy_dbm),
        'app_a': FakeConn(healthy_dbm),
        'app_b': FakeConn(broken_dbm),
    }
    with mock.patch.object(check.autodiscovery, 'get_items', return_value=['app_a', 'app_b']):
        with mock.patch(
            'datadog_checks.postgres.diagnose.TokenAwareConnection.connect',
            side_effect=lambda **kwargs: connections[kwargs['dbname']],
        ):
            diagnoses = _get_diagnoses(check)

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
    check = integration_check(dict(pg_instance, dbm=True))
    dbm_responses = [
        # datadog schema missing -> _diagnose_datadog_schema FAILs and adds to per-DB `failed`.
        ("nspname = 'datadog'", []),
        # has_schema_privilege would return False for datadog (NULL row from a missing schema),
        # but the cascade-skip means the probe never queries it for `datadog`. Public still does.
        ("has_schema_privilege", [(True,)]),
        ("extname = 'pg_stat_statements'", [(1,)]),
        ('SELECT 1 FROM "pg_stat_statements" LIMIT 1', [(1,)]),
        (_explain_call(), psycopg.errors.UndefinedFunction('function datadog.explain_statement does not exist')),
    ]
    conn = FakeConn(_happy_server_responses() + dbm_responses)
    with _patch_connection(check, conn):
        diagnoses = _get_diagnoses(check)

    schema_rows = _by_name(diagnoses, DatabaseConfigurationError.missing_datadog_schema.value)
    assert schema_rows and schema_rows[0]['result'] == Diagnosis.DIAGNOSIS_FAIL
    # USAGE rows: only `public` should appear (datadog skipped); and it should be SUCCESS.
    usage_rows = _by_name(diagnoses, DatabaseConfigurationError.missing_schema_usage_grant.value)
    assert len(usage_rows) == 1, usage_rows
    assert 'public' in usage_rows[0]['diagnosis']
    assert usage_rows[0]['result'] == Diagnosis.DIAGNOSIS_SUCCESS


def test_dbm_probe_databases_not_used_for_metrics_only(integration_check, pg_instance):
    """With query_samples disabled, query_metrics probes pg_stat_statements on the main DB only."""
    instance = dict(
        pg_instance,
        dbm=True,
        query_samples={'enabled': False},
        database_autodiscovery={'enabled': True, 'include': ['app_.*']},
    )
    check = integration_check(instance)
    metrics_only_dbm = [
        ("extname = 'pg_stat_statements'", [(1,)]),
        ('SELECT 1 FROM "pg_stat_statements" LIMIT 1', [(1,)]),
    ]
    with mock.patch.object(check.autodiscovery, 'get_items', return_value=['app_a', 'app_b']):
        with mock.patch(
            'datadog_checks.postgres.diagnose.TokenAwareConnection.connect',
            side_effect=_main_database_only_connection(
                pg_instance['dbname'], FakeConn(_happy_server_responses() + metrics_only_dbm)
            ),
        ) as connect:
            diagnoses = _get_diagnoses(check)

    opened_dbnames = {call.kwargs['dbname'] for call in connect.call_args_list}
    assert opened_dbnames == {pg_instance['dbname']}
    extension_rows = _by_name(diagnoses, DatabaseConfigurationError.pg_stat_statements_not_created.value)
    assert len(extension_rows) == 1
    assert extension_rows[0]['result'] == Diagnosis.DIAGNOSIS_SUCCESS
    assert pg_instance['dbname'] in extension_rows[0]['diagnosis']
    assert not _by_name(diagnoses, DatabaseConfigurationError.missing_schema_usage_grant.value)
    assert not _by_name(diagnoses, DatabaseConfigurationError.undefined_explain_function.value)


# -- Subfeature gating --------------------------------------------------------


def test_dbm_with_query_metrics_disabled_skips_pg_stat_statements_probes(integration_check, pg_instance):
    """query_metrics disabled -> pg_stat_statements is not a prerequisite. Don't fail a
    query-samples-only or query-activity-only DBM setup for a missing extension."""
    instance = dict(
        pg_instance,
        dbm=True,
        query_metrics={'enabled': False},
    )
    check = integration_check(instance)
    # Set up responses that would FAIL the pg_stat_statements probes if they ran.
    responses = _happy_server_responses(spl='pgaudit') + [
        ("nspname = 'datadog'", [(1,)]),
        ("has_schema_privilege", [(True,)]),
        ("extname = 'pg_stat_statements'", []),  # extension missing
        ('SELECT 1 FROM "pg_stat_statements" LIMIT 1', psycopg.errors.UndefinedTable('boom')),
        (_explain_call(), _successful_explain()),
    ]
    with _patch_connection(check, FakeConn(responses)):
        diagnoses = _get_diagnoses(check)
    gated = {
        DatabaseConfigurationError.shared_preload_libraries_missing_pg_stat_statements.value,
        DatabaseConfigurationError.track_io_timing_disabled.value,
        DatabaseConfigurationError.high_pg_stat_statements_max.value,
        DatabaseConfigurationError.pg_stat_statements_not_created.value,
        DatabaseConfigurationError.pg_stat_statements_not_readable.value,
    }
    assert not any(d['name'] in gated for d in diagnoses), [d['name'] for d in diagnoses if d['name'] in gated]
    # Samples-side probes still run.
    assert _by_name(diagnoses, DatabaseConfigurationError.undefined_explain_function.value)


def test_dbm_with_query_samples_disabled_skips_explain_probes(integration_check, pg_instance):
    """query_samples disabled -> the explain function and datadog schema are not prerequisites."""
    instance = dict(
        pg_instance,
        dbm=True,
        query_samples={'enabled': False},
    )
    check = integration_check(instance)
    responses = _happy_server_responses() + [
        # If the schema/explain probes ran they'd FAIL on these responses -- they shouldn't run.
        ("nspname = 'datadog'", []),
        ("extname = 'pg_stat_statements'", [(1,)]),
        ('SELECT 1 FROM "pg_stat_statements" LIMIT 1', [(1,)]),
        (_explain_call(), psycopg.errors.UndefinedFunction('function datadog.explain_statement does not exist')),
    ]
    with _patch_connection(check, FakeConn(responses)):
        diagnoses = _get_diagnoses(check)
    gated = {
        DatabaseConfigurationError.missing_datadog_schema.value,
        DatabaseConfigurationError.undefined_explain_function.value,
    }
    assert not any(d['name'] in gated for d in diagnoses)
    # Metrics-side probes still run.
    assert _by_name(diagnoses, DatabaseConfigurationError.pg_stat_statements_not_created.value)


def test_dbm_with_both_subfeatures_disabled_still_runs_track_activity_query_size(integration_check, pg_instance):
    """query_activity defaults to enabled and reads pg_stat_activity.query, so the
    track_activity_query_size warning still applies even when metrics+samples are off."""
    instance = dict(
        pg_instance,
        dbm=True,
        query_metrics={'enabled': False},
        query_samples={'enabled': False},
    )
    check = integration_check(instance)
    responses = _happy_server_responses(track_query_size=1024)
    with _patch_connection(check, FakeConn(responses)):
        diagnoses = _get_diagnoses(check)
    entry = _by_name(diagnoses, DatabaseConfigurationError.track_activity_query_size_too_small.value)[0]
    assert entry['result'] == Diagnosis.DIAGNOSIS_WARNING


# -- pg_stat_statements_view misconfiguration --------------------------------


def test_pg_stat_statements_readable_fails_when_view_misconfigured(integration_check, pg_instance):
    """Extension is installed but `pg_stat_statements_view` points at a nonexistent name.
    This can no longer be swallowed by the UndefinedTable fast-path; the user needs a FAIL."""
    check = integration_check(dict(pg_instance, dbm=True, pg_stat_statements_view='public.wrong_view'))
    dbm_responses = [
        ("nspname = 'datadog'", [(1,)]),
        # Extension probe succeeds.
        ("extname = 'pg_stat_statements'", [(1,)]),
        # But the configured view doesn't exist.
        ('"public"."wrong_view"', psycopg.errors.UndefinedTable('relation "public.wrong_view" does not exist')),
        (_explain_call(), _successful_explain()),
    ]
    conn = FakeConn(_happy_server_responses() + dbm_responses)
    with _patch_connection(check, conn):
        diagnoses = _get_diagnoses(check)
    entry = _by_name(diagnoses, DatabaseConfigurationError.pg_stat_statements_not_readable.value)[0]
    assert entry['result'] == Diagnosis.DIAGNOSIS_FAIL
    assert 'public.wrong_view' in entry['diagnosis']


# -- Unqualified explain_function resolution ---------------------------------


def test_unqualified_explain_function_resolves_via_search_path(integration_check, pg_instance):
    """Runtime calls `SELECT explain_statement(...)` and lets Postgres' search_path find it.
    The diagnose lookup must follow the same resolution rules rather than hardcoding `public`."""
    instance = dict(pg_instance, dbm=True, query_samples={'explain_function': 'explain_statement'})
    check = integration_check(instance)
    dbm_responses = [
        # Unqualified function -> datadog schema probe must not run (no explicit `datadog.`).
        ("nspname = 'datadog'", []),
        ("has_schema_privilege", [(True,)]),
        ("extname = 'pg_stat_statements'", [(1,)]),
        ('SELECT 1 FROM "pg_stat_statements" LIMIT 1', [(1,)]),
        (_explain_call('explain_statement'), _successful_explain()),
    ]
    conn = FakeConn(_happy_server_responses() + dbm_responses)
    with _patch_connection(check, conn):
        diagnoses = _get_diagnoses(check)
    # datadog schema probe skipped entirely (unqualified function).
    assert not _by_name(diagnoses, DatabaseConfigurationError.missing_datadog_schema.value)
    explain = _by_name(diagnoses, DatabaseConfigurationError.undefined_explain_function.value)[0]
    assert explain['result'] == Diagnosis.DIAGNOSIS_SUCCESS


def test_unqualified_explain_function_not_in_search_path_fails(integration_check, pg_instance):
    instance = dict(pg_instance, dbm=True, query_samples={'explain_function': 'explain_statement'})
    check = integration_check(instance)
    dbm_responses = [
        ("nspname = 'datadog'", []),
        ("has_schema_privilege", [(True,)]),
        ("extname = 'pg_stat_statements'", [(1,)]),
        ('SELECT 1 FROM "pg_stat_statements" LIMIT 1', [(1,)]),
        (
            _explain_call('explain_statement'),
            psycopg.errors.UndefinedFunction('function explain_statement does not exist'),
        ),
    ]
    conn = FakeConn(_happy_server_responses() + dbm_responses)
    with _patch_connection(check, conn):
        diagnoses = _get_diagnoses(check)
    explain = _by_name(diagnoses, DatabaseConfigurationError.undefined_explain_function.value)[0]
    assert explain['result'] == Diagnosis.DIAGNOSIS_FAIL
    assert 'explain_statement' in explain['diagnosis']


# -- Cascade skipping ---------------------------------------------------------


def test_cascade_skip_spl_missing_suppresses_pgss_extension_and_readable(integration_check, pg_instance):
    """When SPL lacks pg_stat_statements, the extension+readable FAILs add no information --
    `CREATE EXTENSION` can't succeed until SPL is fixed and the server restarted."""
    check = integration_check(dict(pg_instance, dbm=True))
    responses = _happy_server_responses(spl='pgaudit') + [
        ("nspname = 'datadog'", [(1,)]),
        # If the extension/readable diagnostics did run, these would fail — but they shouldn't run.
        ("extname = 'pg_stat_statements'", []),
        (
            'SELECT 1 FROM "pg_stat_statements" LIMIT 1',
            psycopg.errors.UndefinedTable('does not exist'),
        ),
        (_explain_call(), _successful_explain()),
    ]
    with _patch_connection(check, FakeConn(responses)):
        diagnoses = _get_diagnoses(check)
    # Root cause still reported.
    spl_entry = _by_name(
        diagnoses,
        DatabaseConfigurationError.shared_preload_libraries_missing_pg_stat_statements.value,
    )[0]
    assert spl_entry['result'] == Diagnosis.DIAGNOSIS_FAIL
    # Downstream diagnostics skipped entirely (no entry, not even SUCCESS).
    assert not _by_name(diagnoses, DatabaseConfigurationError.pg_stat_statements_not_created.value)
    assert not _by_name(diagnoses, DatabaseConfigurationError.pg_stat_statements_not_readable.value)


def test_cascade_skip_pg_monitor_missing_suppresses_pg_stat_activity_warning(integration_check, pg_instance):
    """Without pg_monitor, pg_stat_activity masking is a symptom -- the root cause is the role FAIL."""
    check = integration_check(dict(pg_instance, collect_activity_metrics=True))
    responses = _happy_server_responses()
    responses = [(m, [(False,)]) if isinstance(m, str) and m == 'pg_has_role' else (m, r) for m, r in responses]
    # Flip the pg_stat_activity masked-row count to non-zero, so the WARNING *would* fire absent cascade.
    responses = [(m, [(16,)]) if m == "query = %s" else (m, r) for m, r in responses]
    with _patch_connection(check, FakeConn(responses)):
        diagnoses = _get_diagnoses(check)
    role_entry = _by_name(diagnoses, DatabaseConfigurationError.missing_pg_monitor_role.value)[0]
    assert role_entry['result'] == Diagnosis.DIAGNOSIS_FAIL
    assert not _by_name(diagnoses, DatabaseConfigurationError.insufficient_privilege_on_pg_stat_activity.value)


def test_cascade_skip_missing_schema_suppresses_explain_function_in_datadog_schema(integration_check, pg_instance):
    """When `datadog` schema is missing, `datadog.explain_statement` can't exist -- the schema
    FAIL is the actionable item; don't emit an explain-function FAIL with a nonsensical fix."""
    check = integration_check(dict(pg_instance, dbm=True))
    dbm_responses = [
        ("nspname = 'datadog'", []),
        ("has_schema_privilege", [(True,)]),
        ("extname = 'pg_stat_statements'", [(1,)]),
        ('SELECT 1 FROM "pg_stat_statements" LIMIT 1', [(1,)]),
        # If the explain-function diagnostic did run, this would produce a FAIL — but it shouldn't run.
        (_explain_call(), psycopg.errors.UndefinedFunction('function datadog.explain_statement does not exist')),
    ]
    conn = FakeConn(_happy_server_responses() + dbm_responses)
    with _patch_connection(check, conn):
        diagnoses = _get_diagnoses(check)
    schema = _by_name(diagnoses, DatabaseConfigurationError.missing_datadog_schema.value)[0]
    assert schema['result'] == Diagnosis.DIAGNOSIS_FAIL
    assert not _by_name(diagnoses, DatabaseConfigurationError.undefined_explain_function.value)


def test_custom_explain_function_schema_skips_datadog_schema_check(integration_check, pg_instance):
    """If the user configured an explain_function outside the `datadog` schema, the
    `datadog` schema is not a DBM prerequisite -- the schema check short-circuits entirely
    (no success, warning, or fail row) and the function check carries the DBM verdict."""
    instance = dict(pg_instance, dbm=True, query_samples={'explain_function': 'public.my_explain'})
    check = integration_check(instance)
    dbm_responses = [
        # `datadog` schema is absent -- but since the configured function lives in `public`,
        # _diagnose_datadog_schema must early-return without hitting pg_namespace at all.
        ("nspname = 'datadog'", []),
        ("has_schema_privilege", [(True,)]),
        ("extname = 'pg_stat_statements'", [(1,)]),
        ('SELECT 1 FROM "pg_stat_statements" LIMIT 1', [(1,)]),
        (_explain_call('public.my_explain'), _successful_explain()),
    ]
    conn = FakeConn(_happy_server_responses() + dbm_responses)
    with _patch_connection(check, conn):
        diagnoses = _get_diagnoses(check)
    # No `missing-datadog-schema` diagnosis emitted at all -- success or fail would both be wrong.
    assert not _by_name(diagnoses, DatabaseConfigurationError.missing_datadog_schema.value)
    # The explain-function diagnostic ran and passed (function exists in public).
    explain = _by_name(diagnoses, DatabaseConfigurationError.undefined_explain_function.value)[0]
    assert explain['result'] == Diagnosis.DIAGNOSIS_SUCCESS


def test_custom_explain_function_guidance_uses_override(integration_check, pg_instance):
    instance = dict(pg_instance, dbm=True, query_samples={'explain_function': 'public.my_explain'})
    check = integration_check(instance)
    dbm_responses = [
        ("has_schema_privilege", [(True,)]),
        ("extname = 'pg_stat_statements'", [(1,)]),
        ('SELECT 1 FROM "pg_stat_statements" LIMIT 1', [(1,)]),
        (
            _explain_call('public.my_explain'),
            psycopg.errors.UndefinedFunction('function public.my_explain does not exist'),
        ),
    ]
    conn = FakeConn(_happy_server_responses() + dbm_responses)
    with _patch_connection(check, conn):
        diagnoses = _get_diagnoses(check)

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
    with _patch_connection(check, FakeConn(_happy_server_responses())):
        diagnoses = _get_diagnoses(check)

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
    with _patch_connection(check, FakeConn(_happy_server_responses())):
        diagnoses = _get_diagnoses(check)

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
    with _patch_connection(check, FakeConn(_happy_server_responses())):
        diagnoses = _get_diagnoses(check)

    entry = _config_validation_entries(diagnoses)[0]
    assert entry['result'] == Diagnosis.DIAGNOSIS_FAIL
    assert "1 error(s), 0 warning(s)" in entry['diagnosis']
    assert "Errors:" in entry['description']
    assert "Application name can include only ASCII characters: foo" in entry['description']
    assert entry['remediation'] == (
        "Resolve the errors and warnings listed above by editing conf.d/postgres.d/conf.yaml, then restart the agent."
    )


def test_config_validation_emits_when_connection_fails(integration_check, pg_instance):
    check = integration_check(pg_instance)
    check._validation_result = _make_validation_result(warnings=["invalid ssl option"])
    err = psycopg.OperationalError('could not connect')
    with mock.patch('datadog_checks.postgres.diagnose.TokenAwareConnection.connect', side_effect=err):
        diagnoses = _get_diagnoses(check)

    entries = _config_validation_entries(diagnoses)
    assert len(entries) == 1
    assert entries[0]['result'] == Diagnosis.DIAGNOSIS_WARNING
    # connection_failure still fires alongside config-validation.
    assert _by_name(diagnoses, DatabaseConfigurationError.connection_failure.value)


def test_config_validation_handles_missing_validation_result(integration_check, pg_instance):
    check = integration_check(pg_instance)
    check._validation_result = None
    with _patch_connection(check, FakeConn(_happy_server_responses())):
        diagnoses = _get_diagnoses(check)
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
    with _patch_connection(check, FakeConn(_happy_server_responses())):
        diagnoses = _get_diagnoses(check)
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
    with _patch_connection(check, FakeConn(_happy_server_responses())):
        diagnoses = _get_diagnoses(check)

    entry = _config_validation_entries(diagnoses)[0]
    forbidden = ("agent health", "health event", "dbm-health", "dbm_health")
    for field in ('diagnosis', 'description', 'remediation'):
        text = (entry.get(field) or "").lower()
        for token in forbidden:
            assert token not in text, "{} leaked forbidden token {!r}: {!r}".format(field, token, entry.get(field))
