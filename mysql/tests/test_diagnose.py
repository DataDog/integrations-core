# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from contextlib import contextmanager

import mock
import pymysql
import pytest

from datadog_checks.base.utils.diagnose import Diagnosis
from datadog_checks.mysql import MySql
from datadog_checks.mysql.diagnose import MySqlDiagnoseCode
from datadog_checks.mysql.util import DatabaseConfigurationError

from . import common

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# fakes
# ---------------------------------------------------------------------------


class FakeCursor:
    """Cursor stub. Responses is a list of (matcher, result) pairs where matcher
    is either a substring of the SQL or a callable (sql, params) -> bool, and
    result is either a list of rows OR an Exception (raised) OR a callable
    (sql, params) -> list/Exception."""

    def __init__(self, responses):
        self._responses = responses
        self._rows = []

    def execute(self, sql, params=None):
        for matcher, result in self._responses:
            ok = matcher(sql, params) if callable(matcher) else matcher in sql
            if not ok:
                continue
            value = result(sql, params) if callable(result) else result
            if isinstance(value, Exception):
                raise value
            self._rows = list(value)
            return
        raise AssertionError("unexpected query: {!r} params={!r}".format(sql, params))

    def fetchone(self):
        return self._rows[0] if self._rows else None

    def fetchall(self):
        return list(self._rows)

    def nextset(self):
        return False

    def close(self):
        pass


class FakeConnection:
    def __init__(self, responses):
        self._responses = responses
        self.closed = 0

    def cursor(self, *args, **kwargs):
        return FakeCursor(self._responses)

    def close(self):
        self.closed += 1


@contextmanager
def _patched_connect(responses=None, connect_error=None):
    """Patch the diagnose module's connection factory and `_get_connection_args` so the
    probe never touches a real socket."""

    def fake_connect(**kwargs):
        if connect_error is not None:
            raise connect_error
        return FakeConnection(responses or [])

    with (
        mock.patch("datadog_checks.mysql.diagnose.connect_with_session_variables", side_effect=fake_connect),
        mock.patch.object(MySql, "_get_connection_args", return_value={}),
    ):
        yield


def _diagnoses(check):
    check.diagnosis.clear()
    return [d._asdict() for d in check.diagnosis.run_explicit()]


def _by_name(diagnoses, name):
    return [d for d in diagnoses if d["name"] == name]


def _make_check(instance):
    instance.setdefault("host", common.HOST)
    instance.setdefault("username", common.USER)
    instance.setdefault("password", common.PASS)
    instance.setdefault("port", common.PORT)
    instance.setdefault("disable_generic_tags", True)
    return MySql(common.CHECK_NAME, {}, [instance])


# ---------------------------------------------------------------------------
# response builders
# ---------------------------------------------------------------------------


def _variable(name):
    """Matcher for parameterized `SHOW GLOBAL VARIABLES LIKE %s` lookups."""

    def predicate(sql, params):
        return "SHOW GLOBAL VARIABLES LIKE" in sql and params and params[0] == name

    predicate.__qualname__ = "_variable({!r})".format(name)
    return predicate


def _happy_responses(*, version="8.0.36", performance_schema_on=True, mariadb=False, dbm=True):
    """A response list with every probe in a healthy state."""
    version_comment = "MariaDB Server" if mariadb else "MySQL Community Server - GPL"
    if mariadb and "MariaDB" not in version:
        version = "{}-MariaDB".format(version)
    responses = [
        ("SELECT VERSION()", [(version, version_comment)]),
        ("SHOW /*!50000 ENGINE*/ INNODB STATUS", [(1,)]),
        ("performance_schema.setup_consumers LIMIT 1", [(1,)]),
        (_variable("performance_schema"), [("performance_schema", "ON" if performance_schema_on else "OFF")]),
        ("SHOW REPLICA STATUS", []),
        ("SHOW SLAVE STATUS", []),
        ("mysql.innodb_index_stats", [(1,)]),
    ]
    if dbm and performance_schema_on:
        responses += [
            (
                "WHERE name LIKE 'events_statements_%'",
                [("events_statements_current", "YES"), ("events_statements_history_long", "YES")],
            ),
            ("name='events_waits_current'", [("YES",)]),
            ("WHERE name LIKE 'statement/%%' AND timed='YES'", [(50,)]),
            (_variable("max_digest_length"), [("max_digest_length", "4096")]),
            (_variable("performance_schema_max_digest_length"), [("performance_schema_max_digest_length", "4096")]),
            (
                _variable("performance_schema_max_sql_text_length"),
                [("performance_schema_max_sql_text_length", "4096")],
            ),
            ("information_schema.SCHEMATA", [("datadog",)]),
            ("CALL datadog.explain_statement", [(1,)]),
            ("ROUTINE_TYPE='PROCEDURE'", [(1,)]),
        ]
    return responses


def _replace(responses, key, new_result):
    """Replace the first response whose matcher matches `key` (str-equal or via callable name)."""
    target_name = getattr(key, "__qualname__", key)
    for i, (matcher, _result) in enumerate(responses):
        if getattr(matcher, "__qualname__", matcher) == target_name:
            responses[i] = (matcher, new_result)
            return responses
    raise AssertionError("no matcher equals {!r}".format(key))


def _oerr(code, msg):
    return pymysql.err.OperationalError(code, msg)


# ---------------------------------------------------------------------------
# tests
# ---------------------------------------------------------------------------


def test_connection_failure_access_denied():
    check = _make_check({"dbm": False})
    with _patched_connect(connect_error=_oerr(1045, "Access denied for user 'datadog'@'%'")):
        diagnoses = _diagnoses(check)

    rows = _by_name(diagnoses, MySqlDiagnoseCode.connection_failure.value)
    assert len(rows) == 1
    assert rows[0]["result"] == Diagnosis.DIAGNOSIS_FAIL
    assert "access denied" in rows[0]["diagnosis"]
    # No further probes run when the connection itself fails.
    assert not _by_name(diagnoses, MySqlDiagnoseCode.mysql_version_unsupported.value)


def test_connection_failure_host_unreachable():
    check = _make_check({"dbm": False})
    with _patched_connect(connect_error=_oerr(2003, "Can't connect to MySQL server on 'db' (110)")):
        diagnoses = _diagnoses(check)

    row = _by_name(diagnoses, MySqlDiagnoseCode.connection_failure.value)[0]
    assert row["result"] == Diagnosis.DIAGNOSIS_FAIL
    assert "host unreachable" in row["diagnosis"]


def test_happy_path_without_dbm():
    check = _make_check({"dbm": False})
    with _patched_connect(_happy_responses(dbm=False)):
        diagnoses = _diagnoses(check)

    for code in (
        MySqlDiagnoseCode.connection_failure,
        MySqlDiagnoseCode.mysql_version_unsupported,
        MySqlDiagnoseCode.missing_grant_process,
        MySqlDiagnoseCode.missing_grant_performance_schema_select,
    ):
        rows = _by_name(diagnoses, code.value)
        assert rows and rows[0]["result"] == Diagnosis.DIAGNOSIS_SUCCESS, code

    # DBM probes should not appear at all when dbm=false.
    assert not _by_name(diagnoses, DatabaseConfigurationError.events_statements_consumer_missing.value)
    assert not _by_name(diagnoses, DatabaseConfigurationError.explain_plan_fq_procedure_missing.value)
    assert not _by_name(diagnoses, MySqlDiagnoseCode.missing_datadog_schema.value)


def test_happy_path_with_dbm():
    check = _make_check({"dbm": True})
    with _patched_connect(_happy_responses(dbm=True)):
        diagnoses = _diagnoses(check)

    for code in (
        MySqlDiagnoseCode.connection_failure,
        MySqlDiagnoseCode.mysql_version_unsupported,
        DatabaseConfigurationError.performance_schema_not_enabled,
        DatabaseConfigurationError.events_statements_consumer_missing,
        DatabaseConfigurationError.events_waits_current_not_enabled,
        DatabaseConfigurationError.events_statements_time_instrumentation_not_enabled,
        MySqlDiagnoseCode.missing_datadog_schema,
        DatabaseConfigurationError.explain_plan_fq_procedure_missing,
        MySqlDiagnoseCode.missing_execute_on_datadog,
        MySqlDiagnoseCode.enable_events_statements_procedure_missing,
        MySqlDiagnoseCode.performance_schema_digest_too_small,
        MySqlDiagnoseCode.performance_schema_sql_text_too_small,
    ):
        rows = _by_name(diagnoses, code.value)
        assert rows and rows[0]["result"] == Diagnosis.DIAGNOSIS_SUCCESS, code


def test_unsupported_version_fails():
    check = _make_check({"dbm": False})
    with _patched_connect(_happy_responses(version="5.5.50", dbm=False)):
        diagnoses = _diagnoses(check)

    row = _by_name(diagnoses, MySqlDiagnoseCode.mysql_version_unsupported.value)[0]
    assert row["result"] == Diagnosis.DIAGNOSIS_FAIL
    assert "below the minimum supported" in row["diagnosis"]


def test_mariadb_minimum_version():
    check = _make_check({"dbm": False})
    with _patched_connect(_happy_responses(version="10.3.5", mariadb=True, dbm=False)):
        diagnoses = _diagnoses(check)

    row = _by_name(diagnoses, MySqlDiagnoseCode.mysql_version_unsupported.value)[0]
    assert row["result"] == Diagnosis.DIAGNOSIS_FAIL
    assert "MariaDB" in row["diagnosis"]


def test_missing_process_grant():
    check = _make_check({"dbm": False})
    responses = _replace(
        _happy_responses(dbm=False),
        "SHOW /*!50000 ENGINE*/ INNODB STATUS",
        _oerr(1227, "Access denied; you need (at least one of) the PROCESS privilege"),
    )
    with _patched_connect(responses):
        diagnoses = _diagnoses(check)

    row = _by_name(diagnoses, MySqlDiagnoseCode.missing_grant_process.value)[0]
    assert row["result"] == Diagnosis.DIAGNOSIS_FAIL
    assert "PROCESS" in row["diagnosis"]


def test_missing_performance_schema_select_grant():
    check = _make_check({"dbm": False})
    responses = _replace(
        _happy_responses(dbm=False),
        "performance_schema.setup_consumers LIMIT 1",
        _oerr(1142, "SELECT command denied to user 'datadog'@'%' for table 'setup_consumers'"),
    )
    with _patched_connect(responses):
        diagnoses = _diagnoses(check)

    row = _by_name(diagnoses, MySqlDiagnoseCode.missing_grant_performance_schema_select.value)[0]
    assert row["result"] == Diagnosis.DIAGNOSIS_FAIL


def test_missing_replication_client_grant():
    check = _make_check({"dbm": True})
    responses = _replace(
        _happy_responses(),
        "SHOW REPLICA STATUS",
        _oerr(1227, "Access denied; you need (at least one of) the SUPER, REPLICATION CLIENT privilege(s)"),
    )
    with _patched_connect(responses):
        diagnoses = _diagnoses(check)

    row = _by_name(diagnoses, MySqlDiagnoseCode.missing_grant_replication_client.value)[0]
    assert row["result"] == Diagnosis.DIAGNOSIS_FAIL


def test_replication_probe_skipped_when_replication_disabled():
    check = _make_check({"dbm": False, "options": {"replication": False}})
    with _patched_connect(_happy_responses(dbm=False)):
        diagnoses = _diagnoses(check)

    assert not _by_name(diagnoses, MySqlDiagnoseCode.missing_grant_replication_client.value)


def test_performance_schema_off_cascade_skip():
    check = _make_check({"dbm": True})
    with _patched_connect(_happy_responses(performance_schema_on=False)):
        diagnoses = _diagnoses(check)

    # Root cause is FAIL...
    ps = _by_name(diagnoses, DatabaseConfigurationError.performance_schema_not_enabled.value)[0]
    assert ps["result"] == Diagnosis.DIAGNOSIS_FAIL
    # ...and no consumer/instrument/procedure probes were even run.
    cascaded = [
        DatabaseConfigurationError.events_statements_consumer_missing.value,
        DatabaseConfigurationError.events_waits_current_not_enabled.value,
        DatabaseConfigurationError.events_statements_time_instrumentation_not_enabled.value,
        MySqlDiagnoseCode.missing_datadog_schema.value,
        DatabaseConfigurationError.explain_plan_fq_procedure_missing.value,
    ]
    for code in cascaded:
        assert not _by_name(diagnoses, code), code


def test_explain_procedure_missing_fails():
    check = _make_check({"dbm": True})
    responses = _replace(
        _happy_responses(),
        "CALL datadog.explain_statement",
        _oerr(1305, "PROCEDURE datadog.explain_statement does not exist"),
    )
    with _patched_connect(responses):
        diagnoses = _diagnoses(check)

    row = _by_name(diagnoses, DatabaseConfigurationError.explain_plan_fq_procedure_missing.value)[0]
    assert row["result"] == Diagnosis.DIAGNOSIS_FAIL


def test_explain_procedure_execute_denied_fails_execute_grant():
    check = _make_check({"dbm": True})
    responses = _replace(
        _happy_responses(),
        "CALL datadog.explain_statement",
        _oerr(1370, "execute command denied to user 'datadog'@'%' for routine 'datadog.explain_statement'"),
    )
    with _patched_connect(responses):
        diagnoses = _diagnoses(check)

    # Procedure-exists probe should pass (since the error proves it exists)...
    assert (
        _by_name(diagnoses, DatabaseConfigurationError.explain_plan_fq_procedure_missing.value)[0]["result"]
        == Diagnosis.DIAGNOSIS_SUCCESS
    )
    # ...and execute-grant probe should fail.
    exec_row = _by_name(diagnoses, MySqlDiagnoseCode.missing_execute_on_datadog.value)[0]
    assert exec_row["result"] == Diagnosis.DIAGNOSIS_FAIL


def test_datadog_schema_missing_skips_procedure_probes():
    check = _make_check({"dbm": True})
    responses = _replace(_happy_responses(), "information_schema.SCHEMATA", [])
    with _patched_connect(responses):
        diagnoses = _diagnoses(check)

    assert _by_name(diagnoses, MySqlDiagnoseCode.missing_datadog_schema.value)[0]["result"] == Diagnosis.DIAGNOSIS_FAIL
    # Procedure probes get skipped because there's no schema to look in.
    assert not _by_name(diagnoses, DatabaseConfigurationError.explain_plan_fq_procedure_missing.value)
    assert not _by_name(diagnoses, MySqlDiagnoseCode.enable_events_statements_procedure_missing.value)


def test_enable_consumers_procedure_warning_when_missing():
    check = _make_check({"dbm": True})
    responses = _replace(_happy_responses(), "ROUTINE_TYPE='PROCEDURE'", [])
    with _patched_connect(responses):
        diagnoses = _diagnoses(check)

    row = _by_name(diagnoses, MySqlDiagnoseCode.enable_events_statements_procedure_missing.value)[0]
    assert row["result"] == Diagnosis.DIAGNOSIS_WARNING


def test_digest_too_small_warning():
    check = _make_check({"dbm": True})
    responses = _replace(_happy_responses(), _variable("max_digest_length"), [("max_digest_length", "1024")])
    with _patched_connect(responses):
        diagnoses = _diagnoses(check)

    row = _by_name(diagnoses, MySqlDiagnoseCode.performance_schema_digest_too_small.value)[0]
    assert row["result"] == Diagnosis.DIAGNOSIS_WARNING
    assert "max_digest_length=1024" in row["diagnosis"]


def test_sql_text_length_skipped_on_mariadb():
    check = _make_check({"dbm": True})
    with _patched_connect(_happy_responses(mariadb=True, version="10.6.5")):
        diagnoses = _diagnoses(check)

    assert not _by_name(diagnoses, MySqlDiagnoseCode.performance_schema_sql_text_too_small.value)


def test_index_metrics_grant_probe_runs_by_default():
    check = _make_check({"dbm": False})
    with _patched_connect(_happy_responses(dbm=False)):
        diagnoses = _diagnoses(check)

    row = _by_name(diagnoses, MySqlDiagnoseCode.missing_grant_innodb_index_stats.value)[0]
    assert row["result"] == Diagnosis.DIAGNOSIS_SUCCESS


def test_index_metrics_grant_probe_skips_when_disabled():
    check = _make_check({"dbm": False, "index_metrics": {"enabled": False}})
    responses = [
        (m, r)
        for m, r in _happy_responses(dbm=False)
        if (isinstance(m, str) and "mysql.innodb_index_stats" not in m) or callable(m)
    ]
    with _patched_connect(responses):
        diagnoses = _diagnoses(check)

    assert not _by_name(diagnoses, MySqlDiagnoseCode.missing_grant_innodb_index_stats.value)


def test_index_metrics_grant_probe_fails_on_denied():
    check = _make_check({"dbm": False})
    responses = _happy_responses(dbm=False)
    responses = _replace(responses, "mysql.innodb_index_stats", _oerr(1142, "SELECT command denied"))
    with _patched_connect(responses):
        diagnoses = _diagnoses(check)

    row = _by_name(diagnoses, MySqlDiagnoseCode.missing_grant_innodb_index_stats.value)[0]
    assert row["result"] == Diagnosis.DIAGNOSIS_FAIL


def test_query_samples_disabled_skips_explain_probe():
    check = _make_check({"dbm": True, "query_samples": {"enabled": False}})
    # No sample-only responses provided -- the test fails if they're queried.
    responses = _happy_responses()
    responses = [
        (m, r)
        for m, r in responses
        if (isinstance(m, str) and "CALL datadog.explain_statement" not in m and "ROUTINE_TYPE" not in m) or callable(m)
    ]
    responses = [
        (m, r)
        for m, r in responses
        if (
            isinstance(m, str)
            and "WHERE name LIKE 'events_statements_%'" not in m
            and "WHERE name LIKE 'statement/%%' AND timed='YES'" not in m
            and "information_schema.SCHEMATA" not in m
        )
        or callable(m)
    ]
    with _patched_connect(responses):
        diagnoses = _diagnoses(check)

    assert not _by_name(diagnoses, DatabaseConfigurationError.events_statements_consumer_missing.value)
    assert not _by_name(diagnoses, DatabaseConfigurationError.events_statements_time_instrumentation_not_enabled.value)
    assert not _by_name(diagnoses, DatabaseConfigurationError.explain_plan_fq_procedure_missing.value)
    assert not _by_name(diagnoses, MySqlDiagnoseCode.missing_datadog_schema.value)


def test_query_samples_honor_custom_procedure_schema():
    check = _make_check(
        {
            "dbm": True,
            "query_samples": {
                "fully_qualified_explain_procedure": "monitoring.explain_statement",
                "events_statements_enable_procedure": "monitoring.enable_events_statements_consumers",
            },
        }
    )
    responses = _happy_responses()
    responses = _replace(responses, "information_schema.SCHEMATA", [("monitoring",)])
    responses = _replace(responses, "CALL datadog.explain_statement", AssertionError("queried default explain proc"))
    responses = _replace(responses, "ROUTINE_TYPE='PROCEDURE'", [(1,)])
    responses += [("CALL monitoring.explain_statement", [(1,)])]

    with _patched_connect(responses):
        diagnoses = _diagnoses(check)

    schema_row = _by_name(diagnoses, MySqlDiagnoseCode.missing_datadog_schema.value)[0]
    assert schema_row["result"] == Diagnosis.DIAGNOSIS_SUCCESS
    assert "monitoring" in schema_row["diagnosis"]
    explain_row = _by_name(diagnoses, DatabaseConfigurationError.explain_plan_fq_procedure_missing.value)[0]
    assert explain_row["result"] == Diagnosis.DIAGNOSIS_SUCCESS


def test_schema_collection_warning_on_partial_select():
    check = _make_check({"dbm": False, "collect_schemas": {"enabled": True}})
    responses = _happy_responses(dbm=False)
    responses += [
        ("SHOW DATABASES", [("app",), ("audit",), ("mysql",)]),
        ("information_schema.TABLES", [("app",)]),
    ]
    with _patched_connect(responses):
        diagnoses = _diagnoses(check)

    row = _by_name(diagnoses, MySqlDiagnoseCode.missing_grant_schema_select.value)[0]
    assert row["result"] == Diagnosis.DIAGNOSIS_WARNING
    assert "audit" in row["diagnosis"]
