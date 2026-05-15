# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json
from contextlib import contextmanager

import pytest

from datadog_checks.base import ConfigurationError
from datadog_checks.base.utils.diagnose import Diagnosis
from datadog_checks.sqlserver import SQLServer
from datadog_checks.sqlserver.connection_errors import SQLConnectionError
from datadog_checks.sqlserver.const import ENGINE_EDITION_AZURE_MANAGED_INSTANCE, ENGINE_EDITION_SQL_DATABASE
from datadog_checks.sqlserver.diagnose import (
    SQLSERVER_SETUP_DOCS_URL,
    SQLSERVER_TROUBLESHOOTING_DOCS_URL,
    SQLServerConfigurationError,
)

from .common import CHECK_NAME

pytestmark = pytest.mark.unit


class FakeCursor:
    """Cursor stub that dispatches SQL and params to canned results."""

    def __init__(self, responses):
        self._responses = responses
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
            if not ok:
                continue
            if isinstance(result, Exception):
                raise result
            self._rows = list(result)
            return
        raise AssertionError("unexpected query: {!r} params={!r}".format(sql, params))

    def fetchone(self):
        return self._rows[0] if self._rows else None

    def fetchall(self):
        return list(self._rows)


class FakeConnection:
    DEFAULT_DATABASE = "master"

    def __init__(self, responses=None, open_error=None):
        self._responses = responses or []
        self._open_error = open_error
        self.opened = 0
        self.closed = 0

    @contextmanager
    def open_managed_default_connection(self, key_prefix):
        if self._open_error is not None:
            raise self._open_error
        self.opened += 1
        try:
            yield
        finally:
            self.closed += 1

    def get_managed_cursor(self, key_prefix):
        return FakeCursor(self._responses)

    def get_host_with_port(self):
        return "localhost,1433"


def _permission(name):
    def predicate(sql, params):
        return "HAS_PERMS_BY_NAME" in sql and params == (name,)

    predicate.__qualname__ = "_permission({!r})".format(name)
    return predicate


def _get_diagnoses(check):
    check.diagnosis.clear()
    return [d._asdict() for d in check.diagnosis.run_explicit()]


def _by_name(diagnoses, name):
    return [d for d in diagnoses if d['name'] == name]


def _check(instance_minimal_defaults, responses, **instance_overrides):
    instance = dict(instance_minimal_defaults, **instance_overrides)
    check = SQLServer(CHECK_NAME, {}, [instance])
    check._connection = FakeConnection(responses)
    return check


def _happy_responses(
    *,
    major_version=16,
    engine_edition=2,
    view_database_state=True,
    view_database_performance_state=True,
    connect_any_database=True,
    view_any_definition=True,
    is_rds=False,
    autodiscovered_databases=(),
):
    return [
        ("SERVERPROPERTY('ProductMajorVersion')", [(major_version, engine_edition)]),
        ("sys.dm_os_performance_counters", [(1,)]),
        (_permission("VIEW SERVER STATE"), [(1,)]),
        (_permission("VIEW DATABASE STATE"), [(1 if view_database_state else 0,)]),
        ("sys.dm_exec_sessions", [(1,)]),
        (_permission("VIEW DATABASE PERFORMANCE STATE"), [(1 if view_database_performance_state else 0,)]),
        ("sys.dm_io_virtual_file_stats", [(1,)]),
        (_permission("CONNECT ANY DATABASE"), [(1 if connect_any_database else 0,)]),
        (_permission("VIEW ANY DEFINITION"), [(1 if view_any_definition else 0,)]),
        ("'rdsadmin'", [("rdsadmin",)] if is_rds else []),
        ("msdb.dbo.backupset", []),
        ("msdb.dbo.sysjobs", []),
        ("msdb.dbo.sysjobhistory", []),
        ("msdb.dbo.sysjobactivity", []),
        ("msdb.dbo.syssessions", []),
        ("database_id > 4", [(name,) for name in autodiscovered_databases]),
        ("SELECT TOP 1 1", [(1,)]),
        (lambda sql, params: sql.startswith("USE "), []),
    ]


def _assert_result(diagnoses, code, result):
    rows = _by_name(diagnoses, code.value)
    assert rows, "missing diagnosis for {}".format(code.value)
    assert rows[0]['result'] == result, rows


def _replace_response(responses, matcher_key, new_result):
    """Return responses with the entry whose matcher matches matcher_key replaced with new_result.

    String matcher_keys compare equal to string matchers; callable matcher_keys compare via __qualname__.
    """
    target = getattr(matcher_key, '__qualname__', matcher_key)
    return [
        (matcher, new_result) if getattr(matcher, '__qualname__', matcher) == target else (matcher, result)
        for matcher, result in responses
    ]


def test_standard_diagnostics_success(instance_minimal_defaults):
    check = _check(instance_minimal_defaults, _happy_responses())

    diagnoses = _get_diagnoses(check)

    for code in (
        SQLServerConfigurationError.connection_failure,
        SQLServerConfigurationError.sqlserver_version_unsupported,
        SQLServerConfigurationError.performance_counters_not_readable,
        SQLServerConfigurationError.missing_view_server_state,
        SQLServerConfigurationError.missing_msdb_select,
    ):
        _assert_result(diagnoses, code, Diagnosis.DIAGNOSIS_SUCCESS)
    assert not _by_name(diagnoses, SQLServerConfigurationError.missing_connect_any_database.value)
    assert not _by_name(diagnoses, SQLServerConfigurationError.missing_view_any_definition.value)
    assert check._connection.opened == 1
    assert check._connection.closed == 1


def test_connection_failure(instance_minimal_defaults):
    check = SQLServer(CHECK_NAME, {}, [instance_minimal_defaults])
    check._connection = FakeConnection(open_error=SQLConnectionError("login failed for user"))

    diagnoses = _get_diagnoses(check)

    rows = _by_name(diagnoses, SQLServerConfigurationError.connection_failure.value)
    assert len(rows) == 1
    assert rows[0]['result'] == Diagnosis.DIAGNOSIS_FAIL
    assert "login failed for user" in rows[0]['diagnosis']
    assert SQLSERVER_SETUP_DOCS_URL in rows[0]['remediation']
    assert SQLSERVER_TROUBLESHOOTING_DOCS_URL in rows[0]['remediation']


def test_connection_configuration_error(instance_minimal_defaults):
    check = SQLServer(CHECK_NAME, {}, [instance_minimal_defaults])
    check._connection = FakeConnection(open_error=ConfigurationError("invalid connection string"))

    diagnoses = _get_diagnoses(check)

    rows = _by_name(diagnoses, SQLServerConfigurationError.connection_failure.value)
    assert len(rows) == 1
    assert rows[0]['result'] == Diagnosis.DIAGNOSIS_FAIL
    assert "invalid connection string" in rows[0]['diagnosis']


def test_unsupported_version_fails(instance_minimal_defaults):
    check = _check(instance_minimal_defaults, _happy_responses(major_version=10))

    diagnoses = _get_diagnoses(check)

    row = _by_name(diagnoses, SQLServerConfigurationError.sqlserver_version_unsupported.value)[0]
    assert row['result'] == Diagnosis.DIAGNOSIS_FAIL
    assert "below the minimum supported version" in row['diagnosis']


def test_performance_counter_permission_failure(instance_minimal_defaults):
    responses = _happy_responses()
    responses[1] = ("sys.dm_os_performance_counters", Exception("permission denied"))
    check = _check(instance_minimal_defaults, responses)

    diagnoses = _get_diagnoses(check)

    row = _by_name(diagnoses, SQLServerConfigurationError.performance_counters_not_readable.value)[0]
    assert row['result'] == Diagnosis.DIAGNOSIS_FAIL
    assert "sys.dm_os_performance_counters" in row['diagnosis']
    assert "permission denied" in row['rawerror']


def test_missing_view_server_state_fails(instance_minimal_defaults):
    responses = _happy_responses()
    responses[2] = (_permission("VIEW SERVER STATE"), [(0,)])
    check = _check(instance_minimal_defaults, responses)

    diagnoses = _get_diagnoses(check)

    row = _by_name(diagnoses, SQLServerConfigurationError.missing_view_server_state.value)[0]
    assert row['result'] == Diagnosis.DIAGNOSIS_FAIL
    assert "VIEW SERVER STATE" in row['diagnosis']


def test_dbm_diagnostics_success(instance_minimal_defaults):
    check = _check(instance_minimal_defaults, _happy_responses(), dbm=True)

    diagnoses = _get_diagnoses(check)

    _assert_result(diagnoses, SQLServerConfigurationError.missing_connect_any_database, Diagnosis.DIAGNOSIS_SUCCESS)
    _assert_result(diagnoses, SQLServerConfigurationError.missing_view_any_definition, Diagnosis.DIAGNOSIS_SUCCESS)


def test_missing_connect_any_database_fails_for_dbm(instance_minimal_defaults):
    check = _check(instance_minimal_defaults, _happy_responses(connect_any_database=False), dbm=True)

    diagnoses = _get_diagnoses(check)

    row = _by_name(diagnoses, SQLServerConfigurationError.missing_connect_any_database.value)[0]
    assert row['result'] == Diagnosis.DIAGNOSIS_FAIL
    assert "CONNECT ANY DATABASE" in row['diagnosis']


def test_connect_any_database_warns_before_sqlserver_2014(instance_minimal_defaults):
    check = _check(instance_minimal_defaults, _happy_responses(major_version=11), dbm=True)

    diagnoses = _get_diagnoses(check)

    row = _by_name(diagnoses, SQLServerConfigurationError.missing_connect_any_database.value)[0]
    assert row['result'] == Diagnosis.DIAGNOSIS_WARNING
    assert "unavailable before SQL Server 2014" in row['diagnosis']


def test_missing_view_any_definition_fails_for_dbm(instance_minimal_defaults):
    check = _check(instance_minimal_defaults, _happy_responses(view_any_definition=False), dbm=True)

    diagnoses = _get_diagnoses(check)

    row = _by_name(diagnoses, SQLServerConfigurationError.missing_view_any_definition.value)[0]
    assert row['result'] == Diagnosis.DIAGNOSIS_FAIL
    assert "VIEW ANY DEFINITION" in row['diagnosis']


def test_missing_msdb_select_fails_when_enabled_feature_needs_msdb(instance_minimal_defaults):
    responses = _replace_response(_happy_responses(), "msdb.dbo.backupset", Exception("permission denied"))
    check = _check(instance_minimal_defaults, responses)

    diagnoses = _get_diagnoses(check)

    row = _by_name(diagnoses, SQLServerConfigurationError.missing_msdb_select.value)[0]
    assert row['result'] == Diagnosis.DIAGNOSIS_FAIL
    assert "msdb.dbo.backupset" in row['diagnosis']
    assert "permission denied" in row['rawerror']


def test_agent_jobs_adds_msdb_job_table_probes(instance_minimal_defaults):
    check = _check(
        instance_minimal_defaults,
        _happy_responses(),
        dbm=True,
        agent_jobs={'enabled': True},
    )

    diagnoses = _get_diagnoses(check)

    row = _by_name(diagnoses, SQLServerConfigurationError.missing_msdb_select.value)[0]
    assert row['result'] == Diagnosis.DIAGNOSIS_SUCCESS
    assert "msdb.dbo.sysjobs" in row['diagnosis']
    assert "msdb.dbo.sysjobhistory" in row['diagnosis']
    assert "msdb.dbo.sysjobactivity" in row['diagnosis']
    assert "msdb.dbo.syssessions" in row['diagnosis']


def test_agent_jobs_skips_syssessions_on_rds(instance_minimal_defaults):
    check = _check(
        instance_minimal_defaults,
        _happy_responses(is_rds=True),
        dbm=True,
        agent_jobs={'enabled': True},
    )

    diagnoses = _get_diagnoses(check)

    row = _by_name(diagnoses, SQLServerConfigurationError.missing_msdb_select.value)[0]
    assert row['result'] == Diagnosis.DIAGNOSIS_SUCCESS
    assert "msdb.dbo.syssessions" not in row['diagnosis']


def test_agent_jobs_missing_syssessions_select_fails(instance_minimal_defaults):
    responses = _replace_response(_happy_responses(), "msdb.dbo.syssessions", Exception("permission denied"))
    check = _check(instance_minimal_defaults, responses, dbm=True, agent_jobs={'enabled': True})

    diagnoses = _get_diagnoses(check)

    row = _by_name(diagnoses, SQLServerConfigurationError.missing_msdb_select.value)[0]
    assert row['result'] == Diagnosis.DIAGNOSIS_FAIL
    assert "msdb.dbo.syssessions" in row['diagnosis']
    assert "permission denied" in row['rawerror']


def test_azure_sql_database_skips_server_and_msdb_specific_dbm_diagnostics(instance_minimal_defaults):
    check = _check(instance_minimal_defaults, _happy_responses(engine_edition=5), dbm=True)

    diagnoses = _get_diagnoses(check)

    assert not _by_name(diagnoses, SQLServerConfigurationError.missing_connect_any_database.value)
    assert not _by_name(diagnoses, SQLServerConfigurationError.missing_view_any_definition.value)
    assert not _by_name(diagnoses, SQLServerConfigurationError.missing_msdb_select.value)


def test_azure_sql_database_uses_view_database_state_probe(instance_minimal_defaults):
    responses = _replace_response(
        _happy_responses(engine_edition=5),
        _permission("VIEW SERVER STATE"),
        [(0,)],
    )
    check = _check(instance_minimal_defaults, responses)

    diagnoses = _get_diagnoses(check)

    row = _by_name(diagnoses, SQLServerConfigurationError.missing_view_server_state.value)[0]
    assert row['result'] == Diagnosis.DIAGNOSIS_SUCCESS
    assert "VIEW DATABASE STATE" in row['diagnosis']


def test_azure_sql_database_missing_view_database_state_fails(instance_minimal_defaults):
    check = _check(
        instance_minimal_defaults,
        _happy_responses(engine_edition=5, view_database_state=False),
    )

    diagnoses = _get_diagnoses(check)

    row = _by_name(diagnoses, SQLServerConfigurationError.missing_view_server_state.value)[0]
    assert row['result'] == Diagnosis.DIAGNOSIS_FAIL
    assert "VIEW DATABASE STATE" in row['diagnosis']
    assert "VIEW SERVER STATE" not in row['diagnosis']


def test_azure_sql_database_view_database_state_failure(instance_minimal_defaults):
    responses = _replace_response(
        _happy_responses(engine_edition=5),
        "sys.dm_exec_sessions",
        Exception("permission denied"),
    )
    check = _check(instance_minimal_defaults, responses)

    diagnoses = _get_diagnoses(check)

    row = _by_name(diagnoses, SQLServerConfigurationError.missing_view_server_state.value)[0]
    assert row['result'] == Diagnosis.DIAGNOSIS_FAIL
    assert "VIEW DATABASE STATE" in row['diagnosis']
    assert "VIEW SERVER STATE" not in row['diagnosis']
    assert "permission denied" in row['rawerror']


def test_only_custom_queries_skips_baseline_probes(instance_minimal_defaults):
    check = _check(instance_minimal_defaults, _happy_responses(), only_custom_queries=True)

    diagnoses = _get_diagnoses(check)

    assert not _by_name(diagnoses, SQLServerConfigurationError.performance_counters_not_readable.value)
    assert not _by_name(diagnoses, SQLServerConfigurationError.missing_view_server_state.value)
    assert not _by_name(diagnoses, SQLServerConfigurationError.missing_msdb_select.value)
    _assert_result(diagnoses, SQLServerConfigurationError.connection_failure, Diagnosis.DIAGNOSIS_SUCCESS)
    _assert_result(diagnoses, SQLServerConfigurationError.sqlserver_version_unsupported, Diagnosis.DIAGNOSIS_SUCCESS)


def test_only_custom_queries_still_probes_dbm_baseline(instance_minimal_defaults):
    check = _check(instance_minimal_defaults, _happy_responses(), only_custom_queries=True, dbm=True)

    diagnoses = _get_diagnoses(check)

    assert not _by_name(diagnoses, SQLServerConfigurationError.performance_counters_not_readable.value)
    _assert_result(diagnoses, SQLServerConfigurationError.missing_view_server_state, Diagnosis.DIAGNOSIS_SUCCESS)
    _assert_result(diagnoses, SQLServerConfigurationError.missing_connect_any_database, Diagnosis.DIAGNOSIS_SUCCESS)
    _assert_result(diagnoses, SQLServerConfigurationError.missing_view_any_definition, Diagnosis.DIAGNOSIS_SUCCESS)


def test_only_custom_queries_skips_database_metric_msdb_probes(instance_minimal_defaults):
    check = _check(
        instance_minimal_defaults,
        _happy_responses(),
        only_custom_queries=True,
        database_metrics={'db_backup_metrics': {'enabled': True}},
    )

    diagnoses = _get_diagnoses(check)

    assert not _by_name(diagnoses, SQLServerConfigurationError.missing_msdb_select.value)


def test_stored_procedure_skips_regular_metric_probes(instance_minimal_defaults):
    check = _check(
        instance_minimal_defaults,
        _happy_responses(),
        stored_procedure='pyStoredProc',
        database_autodiscovery=True,
    )

    diagnoses = _get_diagnoses(check)

    assert not _by_name(diagnoses, SQLServerConfigurationError.performance_counters_not_readable.value)
    assert not _by_name(diagnoses, SQLServerConfigurationError.missing_view_server_state.value)
    assert not _by_name(diagnoses, SQLServerConfigurationError.missing_connect_any_database.value)
    assert not _by_name(diagnoses, SQLServerConfigurationError.missing_view_any_definition.value)
    assert not _by_name(diagnoses, SQLServerConfigurationError.missing_msdb_select.value)
    _assert_result(diagnoses, SQLServerConfigurationError.connection_failure, Diagnosis.DIAGNOSIS_SUCCESS)
    _assert_result(diagnoses, SQLServerConfigurationError.sqlserver_version_unsupported, Diagnosis.DIAGNOSIS_SUCCESS)


def test_stored_procedure_still_probes_dbm_diagnostics(instance_minimal_defaults):
    check = _check(instance_minimal_defaults, _happy_responses(), stored_procedure='pyStoredProc', dbm=True)

    diagnoses = _get_diagnoses(check)

    assert not _by_name(diagnoses, SQLServerConfigurationError.performance_counters_not_readable.value)
    _assert_result(diagnoses, SQLServerConfigurationError.missing_view_server_state, Diagnosis.DIAGNOSIS_SUCCESS)
    _assert_result(diagnoses, SQLServerConfigurationError.missing_connect_any_database, Diagnosis.DIAGNOSIS_SUCCESS)
    _assert_result(diagnoses, SQLServerConfigurationError.missing_view_any_definition, Diagnosis.DIAGNOSIS_SUCCESS)


def test_get_diagnoses_returns_json(instance_minimal_defaults):
    check = _check(instance_minimal_defaults, _happy_responses())

    parsed = json.loads(check.get_diagnoses())

    assert any(d['name'] == SQLServerConfigurationError.connection_failure.value for d in parsed)


def test_view_database_performance_state_skipped_on_non_azure(instance_minimal_defaults):
    check = _check(instance_minimal_defaults, _happy_responses(), dbm=True)

    diagnoses = _get_diagnoses(check)

    assert not _by_name(diagnoses, SQLServerConfigurationError.missing_view_database_performance_state.value)


def test_view_database_performance_state_success_on_azure_sql_database(instance_minimal_defaults):
    check = _check(
        instance_minimal_defaults,
        _happy_responses(engine_edition=ENGINE_EDITION_SQL_DATABASE),
        dbm=True,
    )

    diagnoses = _get_diagnoses(check)

    _assert_result(
        diagnoses,
        SQLServerConfigurationError.missing_view_database_performance_state,
        Diagnosis.DIAGNOSIS_SUCCESS,
    )


def test_view_database_performance_state_missing_permission_fails(instance_minimal_defaults):
    check = _check(
        instance_minimal_defaults,
        _happy_responses(engine_edition=ENGINE_EDITION_AZURE_MANAGED_INSTANCE, view_database_performance_state=False),
        dbm=True,
    )

    diagnoses = _get_diagnoses(check)

    row = _by_name(diagnoses, SQLServerConfigurationError.missing_view_database_performance_state.value)[0]
    assert row['result'] == Diagnosis.DIAGNOSIS_FAIL
    assert "VIEW DATABASE PERFORMANCE STATE" in row['diagnosis']


def test_view_database_performance_state_probe_failure(instance_minimal_defaults):
    responses = _replace_response(
        _happy_responses(engine_edition=ENGINE_EDITION_AZURE_MANAGED_INSTANCE),
        "sys.dm_io_virtual_file_stats",
        Exception("permission denied"),
    )
    check = _check(instance_minimal_defaults, responses, dbm=True)

    diagnoses = _get_diagnoses(check)

    row = _by_name(diagnoses, SQLServerConfigurationError.missing_view_database_performance_state.value)[0]
    assert row['result'] == Diagnosis.DIAGNOSIS_FAIL
    assert "sys.dm_io_virtual_file_stats" in row['diagnosis']
    assert "permission denied" in row['rawerror']


def test_view_database_performance_state_skipped_when_no_dependent_collection(instance_minimal_defaults):
    check = _check(
        instance_minimal_defaults,
        _happy_responses(engine_edition=ENGINE_EDITION_SQL_DATABASE),
        database_metrics={'file_stats_metrics': {'enabled': False}},
    )

    diagnoses = _get_diagnoses(check)

    assert not _by_name(diagnoses, SQLServerConfigurationError.missing_view_database_performance_state.value)


def test_odbc_driver_not_installed_fails(instance_minimal_defaults, monkeypatch):
    from datadog_checks.sqlserver import diagnose as diagnose_module

    monkeypatch.setattr(diagnose_module, "_list_pyodbc_drivers", lambda: ["FreeTDS"])
    check = _check(
        instance_minimal_defaults,
        _happy_responses(),
        connector='odbc',
        driver='{ODBC Driver 18 for SQL Server}',
    )

    diagnoses = _get_diagnoses(check)

    row = _by_name(diagnoses, SQLServerConfigurationError.odbc_driver_not_installed.value)[0]
    assert row['result'] == Diagnosis.DIAGNOSIS_FAIL
    assert "ODBC Driver 18 for SQL Server" in row['diagnosis']
    assert "FreeTDS" in row['diagnosis']


def test_odbc_driver_installed_does_not_fail(instance_minimal_defaults, monkeypatch):
    from datadog_checks.sqlserver import diagnose as diagnose_module

    monkeypatch.setattr(diagnose_module, "_list_pyodbc_drivers", lambda: ["ODBC Driver 18 for SQL Server"])
    check = _check(
        instance_minimal_defaults,
        _happy_responses(),
        connector='odbc',
        driver='{ODBC Driver 18 for SQL Server}',
    )

    diagnoses = _get_diagnoses(check)

    assert not _by_name(diagnoses, SQLServerConfigurationError.odbc_driver_not_installed.value)


def test_odbc_driver_check_skipped_for_adodbapi(instance_minimal_defaults, monkeypatch):
    from datadog_checks.sqlserver import diagnose as diagnose_module

    monkeypatch.setattr(diagnose_module, "_list_pyodbc_drivers", lambda: [])
    check = _check(
        instance_minimal_defaults,
        _happy_responses(),
        connector='adodbapi',
        adoprovider='MSOLEDBSQL19',
    )

    diagnoses = _get_diagnoses(check)

    assert not _by_name(diagnoses, SQLServerConfigurationError.odbc_driver_not_installed.value)


def test_odbc_driver_check_skipped_when_pyodbc_unavailable(instance_minimal_defaults, monkeypatch):
    from datadog_checks.sqlserver import diagnose as diagnose_module

    monkeypatch.setattr(diagnose_module, "_list_pyodbc_drivers", lambda: None)
    check = _check(
        instance_minimal_defaults,
        _happy_responses(),
        connector='odbc',
        driver='{ODBC Driver 18 for SQL Server}',
    )

    diagnoses = _get_diagnoses(check)

    assert not _by_name(diagnoses, SQLServerConfigurationError.odbc_driver_not_installed.value)


def test_per_database_access_success(instance_minimal_defaults):
    check = _check(
        instance_minimal_defaults,
        _happy_responses(autodiscovered_databases=("db_a", "db_b")),
        database_autodiscovery=True,
    )

    diagnoses = _get_diagnoses(check)

    row = _by_name(diagnoses, SQLServerConfigurationError.per_database_access.value)[0]
    assert row['result'] == Diagnosis.DIAGNOSIS_SUCCESS
    assert "2" in row['diagnosis']


def test_per_database_access_reports_failed_database(instance_minimal_defaults):
    def use_db_bad(sql, params):
        return sql == "USE [db_bad]"

    def use_db_ok(sql, params):
        return sql == "USE [db_ok]"

    responses = _happy_responses(autodiscovered_databases=("db_ok", "db_bad"))
    responses.insert(0, (use_db_bad, Exception("USE failed for db_bad")))
    responses.insert(1, (use_db_ok, []))

    check = _check(instance_minimal_defaults, responses, database_autodiscovery=True)

    diagnoses = _get_diagnoses(check)

    row = _by_name(diagnoses, SQLServerConfigurationError.per_database_access.value)[0]
    assert row['result'] == Diagnosis.DIAGNOSIS_FAIL
    assert "db_bad" in row['diagnosis']
    assert "USE failed for db_bad" in row['rawerror']


def test_per_database_access_applies_autodiscovery_filters(instance_minimal_defaults):
    check = _check(
        instance_minimal_defaults,
        _happy_responses(autodiscovered_databases=("included_db", "skipped_db")),
        database_autodiscovery=True,
        autodiscovery_include=['included.*'],
        autodiscovery_exclude=['skipped.*'],
    )

    diagnoses = _get_diagnoses(check)

    row = _by_name(diagnoses, SQLServerConfigurationError.per_database_access.value)[0]
    assert row['result'] == Diagnosis.DIAGNOSIS_SUCCESS
    assert "1" in row['diagnosis']


def test_per_database_access_skipped_without_autodiscovery(instance_minimal_defaults):
    check = _check(instance_minimal_defaults, _happy_responses())

    diagnoses = _get_diagnoses(check)

    assert not _by_name(diagnoses, SQLServerConfigurationError.per_database_access.value)


def test_per_database_access_skipped_on_azure_sql_database(instance_minimal_defaults):
    check = _check(
        instance_minimal_defaults,
        _happy_responses(engine_edition=ENGINE_EDITION_SQL_DATABASE),
        database_autodiscovery=True,
        dbm=True,
    )

    diagnoses = _get_diagnoses(check)

    assert not _by_name(diagnoses, SQLServerConfigurationError.per_database_access.value)
