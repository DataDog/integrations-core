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
        category="server-config",
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


def test_connection_fails_dbm_enabled_collapses_duplicate_probes(integration_check, pg_instance):
    """With dbm=true, both orchestrators try to connect -- but the base Diagnosis dedups the
    character-identical FAIL rows, so the user sees exactly one connection-failure entry."""
    check = integration_check(dict(pg_instance, dbm=True))
    err = psycopg.OperationalError('boom')
    with mock.patch('datadog_checks.postgres.diagnose.TokenAwareConnection.connect', side_effect=err) as connect:
        diagnoses = _get_diagnoses(check)
    # Both orchestrators still attempt a probe.
    assert connect.call_count == 2
    conn_diags = _by_name(diagnoses, DatabaseConfigurationError.connection_failure.value)
    assert len(conn_diags) == 1
    assert conn_diags[0]['result'] == Diagnosis.DIAGNOSIS_FAIL


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
    """Non-DBM orchestrator covers version + pg_monitor + pg_stat_activity; the DBM-gated
    server-config diagnostics are covered by `test_dbm_server_config_happy_path`."""
    check = integration_check(pg_instance)
    conn = FakeConn(_happy_server_responses())
    with _patch_connection(check, conn):
        diagnoses = _get_diagnoses(check)

    names_and_results = {(d['name'], d['result']) for d in diagnoses}
    for code in (
        DatabaseConfigurationError.postgres_version_unsupported,
        DatabaseConfigurationError.missing_pg_monitor_role,
        DatabaseConfigurationError.insufficient_privilege_on_pg_stat_activity,
    ):
        assert (code.value, Diagnosis.DIAGNOSIS_SUCCESS) in names_and_results, (
            f"expected {code.value} to pass, got {[d for d in diagnoses if d['name'] == code.value]}"
        )


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
    # Neither the DBM database-scoped checks nor the DBM-only server GUC checks should run
    # without dbm=true -- running them against a plain Postgres would fail a healthy instance.
    dbm_names = {
        DatabaseConfigurationError.shared_preload_libraries_missing_pg_stat_statements.value,
        DatabaseConfigurationError.track_activity_query_size_too_small.value,
        DatabaseConfigurationError.track_io_timing_disabled.value,
        DatabaseConfigurationError.high_pg_stat_statements_max.value,
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
        ("p.proname", [(1,)]),
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
    check = integration_check(pg_instance)
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
        ("extname = 'pg_stat_statements'", [(1,)]),
        ('SELECT 1 FROM "pg_stat_statements" LIMIT 1', [(1,)]),
        # If the explain-function diagnostic did run, this would produce a FAIL — but it shouldn't run.
        ("p.proname", []),
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
        ("extname = 'pg_stat_statements'", [(1,)]),
        ('SELECT 1 FROM "pg_stat_statements" LIMIT 1', [(1,)]),
        ("p.proname", [(1,)]),
    ]
    conn = FakeConn(_happy_server_responses() + dbm_responses)
    with _patch_connection(check, conn):
        diagnoses = _get_diagnoses(check)
    # No `missing-datadog-schema` diagnosis emitted at all -- success or fail would both be wrong.
    assert not _by_name(diagnoses, DatabaseConfigurationError.missing_datadog_schema.value)
    # The explain-function diagnostic ran and passed (function exists in public).
    explain = _by_name(diagnoses, DatabaseConfigurationError.undefined_explain_function.value)[0]
    assert explain['result'] == Diagnosis.DIAGNOSIS_SUCCESS


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
