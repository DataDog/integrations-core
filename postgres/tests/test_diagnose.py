# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import json
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


# -- record_warning regression ------------------------------------------------


def test_record_warning_emits_diagnosis(integration_check, pg_instance):
    check = integration_check(pg_instance)
    code = DatabaseConfigurationError.pg_stat_statements_not_loaded
    check.diagnosis.clear()

    check.record_warning(code, "pg_stat_statements is not loaded")

    # Legacy path still populated.
    assert check._warnings_by_code[code] == "pg_stat_statements is not loaded"
    # Diagnosis populated with matching metadata.
    diagnoses = check.diagnosis.diagnoses
    assert len(diagnoses) == 1
    d = diagnoses[0]
    assert d.result == Diagnosis.DIAGNOSIS_WARNING
    assert d.name == code.value
    assert d.diagnosis == "pg_stat_statements is not loaded"
    assert d.description == DIAGNOSTIC_METADATA[code]["description"]
    assert "shared_preload_libraries" in d.remediation
    assert "troubleshooting" in d.remediation


def test_record_warning_unknown_code_still_emits(integration_check, pg_instance):
    """A code without DIAGNOSTIC_METADATA entry should still produce a diagnosis with a doc URL."""
    check = integration_check(pg_instance)
    # Fabricate a code-like object missing from metadata by using a code from the enum that
    # we'll temporarily exclude.
    fake = DatabaseConfigurationError.autodiscovered_databases_exceeds_limit
    check.diagnosis.clear()
    with mock.patch.dict(DIAGNOSTIC_METADATA, clear=False) as metadata:
        metadata.pop(fake, None)
        check.record_warning(fake, "too many dbs")
    diagnoses = check.diagnosis.diagnoses
    assert len(diagnoses) == 1
    assert diagnoses[0].name == fake.value
    # Remediation always contains the docs URL as a fallback.
    assert "https://docs.datadoghq.com" in diagnoses[0].remediation


def test_get_diagnoses_returns_json(integration_check, pg_instance):
    check = integration_check(pg_instance)
    # record_warning -> cached diagnosis, then run_explicit invoked by get_diagnoses.
    check.diagnosis.clear()
    check.record_warning(DatabaseConfigurationError.pg_stat_statements_not_loaded, "pg_stat_statements is not loaded")
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


def test_connection_fails_dbm_enabled_reports_once_per_orchestrator(integration_check, pg_instance):
    """With dbm=true, both orchestrators try to connect. Each failure is reported."""
    check = integration_check(dict(pg_instance, dbm=True))
    err = psycopg.OperationalError('boom')
    with mock.patch('datadog_checks.postgres.diagnose.TokenAwareConnection.connect', side_effect=err):
        diagnoses = _get_diagnoses(check)
    conn_diags = _by_name(diagnoses, DatabaseConfigurationError.connection_failure.value)
    assert all(d['result'] == Diagnosis.DIAGNOSIS_FAIL for d in conn_diags)
    assert len(conn_diags) == 2


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
    check = integration_check(pg_instance)
    conn = FakeConn(_happy_server_responses())
    with _patch_connection(check, conn):
        diagnoses = _get_diagnoses(check)

    names_and_results = {(d['name'], d['result']) for d in diagnoses}
    # All server-config + privilege diagnostics should be SUCCESS.
    for code in (
        DatabaseConfigurationError.postgres_version_unsupported,
        DatabaseConfigurationError.shared_preload_libraries_missing_pg_stat_statements,
        DatabaseConfigurationError.track_activity_query_size_too_small,
        DatabaseConfigurationError.track_io_timing_disabled,
        DatabaseConfigurationError.high_pg_stat_statements_max,
        DatabaseConfigurationError.missing_pg_monitor_role,
        DatabaseConfigurationError.insufficient_privilege_on_pg_stat_activity,
    ):
        assert (code.value, Diagnosis.DIAGNOSIS_SUCCESS) in names_and_results, (
            f"expected {code.value} to pass, got {[d for d in diagnoses if d['name'] == code.value]}"
        )


def test_shared_preload_libraries_missing_fails(integration_check, pg_instance):
    check = integration_check(pg_instance)
    responses = _happy_server_responses(spl='pgaudit')
    with _patch_connection(check, FakeConn(responses)):
        diagnoses = _get_diagnoses(check)
    spl = _by_name(
        diagnoses,
        DatabaseConfigurationError.shared_preload_libraries_missing_pg_stat_statements.value,
    )
    assert spl and spl[0]['result'] == Diagnosis.DIAGNOSIS_FAIL
    assert 'pg_stat_statements' in spl[0]['diagnosis']


def test_track_activity_query_size_too_small_warns(integration_check, pg_instance):
    check = integration_check(pg_instance)
    responses = _happy_server_responses(track_query_size=1024)
    with _patch_connection(check, FakeConn(responses)):
        diagnoses = _get_diagnoses(check)
    entry = _by_name(diagnoses, DatabaseConfigurationError.track_activity_query_size_too_small.value)[0]
    assert entry['result'] == Diagnosis.DIAGNOSIS_WARNING
    assert str(RECOMMENDED_TRACK_ACTIVITY_QUERY_SIZE) in entry['diagnosis']


def test_track_io_timing_off_warns(integration_check, pg_instance):
    check = integration_check(pg_instance)
    responses = _happy_server_responses(track_io='off')
    with _patch_connection(check, FakeConn(responses)):
        diagnoses = _get_diagnoses(check)
    entry = _by_name(diagnoses, DatabaseConfigurationError.track_io_timing_disabled.value)[0]
    assert entry['result'] == Diagnosis.DIAGNOSIS_WARNING


def test_pg_stat_statements_max_above_threshold_warns(integration_check, pg_instance):
    check = integration_check(pg_instance)
    # Default threshold is 10000; exceed it.
    responses = _happy_server_responses(pgss_max=50000)
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
    check = integration_check(pg_instance)
    responses = _happy_server_responses()
    # Replace the pg_has_role response.
    responses = [(m, [(False,)]) if isinstance(m, str) and m == 'pg_has_role' else (m, r) for m, r in responses]
    with _patch_connection(check, FakeConn(responses)):
        diagnoses = _get_diagnoses(check)
    entry = _by_name(diagnoses, DatabaseConfigurationError.missing_pg_monitor_role.value)[0]
    assert entry['result'] == Diagnosis.DIAGNOSIS_FAIL
    assert 'pg_monitor' in entry['remediation']


def test_insufficient_privilege_on_pg_stat_activity_warns(integration_check, pg_instance):
    check = integration_check(pg_instance)
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
        ("extname = 'pg_stat_statements'", [(1,)]),
        # pg_stat_statements readable probe — the SQL contains the quoted view name.
        ('SELECT 1 FROM "pg_stat_statements" LIMIT 1', [(1,)]),
        ("p.proname", [(1,)]),
    ]


def test_dbm_disabled_skips_dbm_diagnostics(integration_check, pg_instance):
    check = integration_check(pg_instance)  # dbm defaults to False
    conn = FakeConn(_happy_server_responses() + _happy_dbm_responses())
    with _patch_connection(check, conn):
        diagnoses = _get_diagnoses(check)
    # No dbm-category diagnoses should appear.
    dbm_names = {
        DatabaseConfigurationError.missing_datadog_schema.value,
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
        ("extname = 'pg_stat_statements'", [(1,)]),
        ('SELECT 1 FROM "pg_stat_statements" LIMIT 1', [(1,)]),
        ("p.proname", [(1,)]),
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
        ("extname = 'pg_stat_statements'", []),
        # Simulate extension missing: the readable probe would raise UndefinedTable, swallowed silently.
        (
            'SELECT 1 FROM "pg_stat_statements" LIMIT 1',
            psycopg.errors.UndefinedTable('relation "pg_stat_statements" does not exist'),
        ),
        ("p.proname", [(1,)]),
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
        ("extname = 'pg_stat_statements'", [(1,)]),
        ('SELECT 1 FROM "pg_stat_statements" LIMIT 1', [(1,)]),
        ("p.proname", []),
    ]
    conn = FakeConn(_happy_server_responses() + dbm_responses)
    with _patch_connection(check, conn):
        diagnoses = _get_diagnoses(check)
    entry = _by_name(diagnoses, DatabaseConfigurationError.undefined_explain_function.value)[0]
    assert entry['result'] == Diagnosis.DIAGNOSIS_FAIL
    assert 'explain_statement' in entry['diagnosis']


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
        ('explain_statement', ('public', 'explain_statement')),
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
