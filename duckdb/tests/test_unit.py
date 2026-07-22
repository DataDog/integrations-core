# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import importlib
import logging
import shutil
import sys

import duckdb
import pytest

from datadog_checks.base import AgentCheck  # noqa: F401
from datadog_checks.base.errors import CheckException
from datadog_checks.base.stubs.aggregator import AggregatorStub  # noqa: F401
from datadog_checks.duckdb import DuckdbCheck
from datadog_checks.duckdb import check as check_module

from . import common

pytestmark = pytest.mark.unit


def test_empty_instance(dd_run_check):
    with pytest.raises(
        Exception,
        match='InstanceConfig`:\ndb_name\n  Field required',
    ):
        check = DuckdbCheck('duckdb', {}, [{}])
        dd_run_check(check)


def test_default_connection_attempt_is_three():
    # Kills the core/NumberReplacer mutants at check.py:39 (connection_attempt default 3 -> 4/2).
    check = DuckdbCheck('duckdb', {}, [common.DEFAULT_INSTANCE])
    assert check.connection_attempt == 3


def test_initial_query_errors_is_zero():
    # Kills the core/NumberReplacer mutants at check.py:45 (_query_errors initial value 0 -> 1/-1).
    check = DuckdbCheck('duckdb', {}, [common.DEFAULT_INSTANCE])
    assert check._query_errors == 0


def test_missing_duckdb_dependency_raises_check_exception():
    # Kills core/ExceptionReplacer at check.py:17 and the core/ReplaceBinaryOperator_Mod_* mutants at
    # check.py:22: forcing the module-level `import duckdb` to fail must still raise a formatted CheckException.
    original_module_dict = dict(check_module.__dict__)
    real_duckdb = sys.modules.get('duckdb')
    sys.modules['duckdb'] = None
    try:
        with pytest.raises(CheckException, match='Duckdb was not imported correctly'):
            importlib.reload(check_module)
    finally:
        sys.modules['duckdb'] = real_duckdb
        check_module.__dict__.clear()
        check_module.__dict__.update(original_module_dict)


def test_check_raises_when_duckdb_unavailable(monkeypatch):
    # Kills the core/ReplaceComparisonOperator_Is_IsNot and core/AddNot mutants at check.py:60, and the
    # core/ReplaceBinaryOperator_Mod_* mutants at check.py:63 (message formatting with dk_import_error).
    check = DuckdbCheck('duckdb', {}, [common.DEFAULT_INSTANCE])
    monkeypatch.setattr(check_module, 'duckdb', None)
    with pytest.raises(CheckException, match='Duckdb was not imported correctly.*Error is'):
        check.check(None)


def test_check_metrics_submitted_exactly_once(dd_run_check, aggregator):
    # Kills core/AddNot at check.py:71 (if conn) and core/ReplaceBreakWithContinue at check.py:74: a
    # successful connection must submit each metric exactly once, then stop retrying.
    check = DuckdbCheck('duckdb', {}, [common.DEFAULT_INSTANCE])
    dd_run_check(check)

    for metric in common.METRICS_MAP:
        aggregator.assert_metric(metric, count=1)


def test_check_retry_loop_stops_after_single_attempt(caplog, monkeypatch):
    # Kills the core/ReplaceBinaryOperator_Add_* and core/NumberReplacer/ZeroIterationForLoop mutants at
    # check.py:68, and the core/ReplaceComparisonOperator_Lt_* mutants at check.py:77 (attempt < max_retries),
    # by asserting the exact number of retries and log messages when connection_attempt=1.
    caplog.set_level(logging.WARNING)
    sleep_calls = []
    monkeypatch.setattr(check_module.time, 'sleep', lambda seconds: sleep_calls.append(seconds))

    check = DuckdbCheck('duckdb', {}, [common.WRONG_INSTANCE | {'connection_attempt': 1}])
    for init in check.check_initializations:
        init()
    check.check(None)

    assert sleep_calls == []
    assert caplog.text.count('Unable to connect to the database') == 1
    assert caplog.text.count('Max connection retries reached') == 1


def test_check_retry_loop_sleeps_between_failed_attempts(caplog, monkeypatch):
    # Kills the core/NumberReplacer mutants at check.py:66 (retry_delay 5 -> 6/4) and
    # core/ExceptionReplacer at check.py:75, by verifying the sleep delay and retry count with two attempts.
    caplog.set_level(logging.WARNING)
    sleep_calls = []
    monkeypatch.setattr(check_module.time, 'sleep', lambda seconds: sleep_calls.append(seconds))

    check = DuckdbCheck('duckdb', {}, [common.WRONG_INSTANCE | {'connection_attempt': 2}])
    for init in check.check_initializations:
        init()
    check.check(None)

    assert sleep_calls == [5]
    assert caplog.text.count('Unable to connect to the database') == 2
    assert caplog.text.count('Max connection retries reached') == 1


def test_connect_opens_database_in_read_only_mode(tmp_path):
    # Kills core/ReplaceTrueWithFalse at check.py:124: writes must be rejected on a read-only connection.
    # Uses a throwaway copy of the fixture database since a successful write under the mutant would
    # otherwise permanently modify the shared, checked-in sample.db file.
    db_copy = tmp_path / "sample.db"
    shutil.copyfile(common.DB, db_copy)

    check = DuckdbCheck('duckdb', {}, [{'db_name': str(db_copy)}])
    with check.connect() as conn:
        with pytest.raises(duckdb.Error):
            conn.execute("CREATE TABLE should_fail (id INTEGER);")


def test_connect_logs_generic_error_for_invalid_database_file(caplog, tmp_path):
    # Kills core/ExceptionReplacer at check.py:127, core/AddNot at check.py:128 and check.py:121, by
    # pointing at a file that exists but isn't a valid DuckDB database.
    caplog.set_level(logging.DEBUG)
    invalid_db = tmp_path / "invalid.db"
    invalid_db.write_text("this is not a duckdb database file")

    check = DuckdbCheck('duckdb', {}, [{'db_name': str(invalid_db), 'connection_attempt': 1}])
    for init in check.check_initializations:
        init()
    check.check(None)

    assert 'Unable to connect to DuckDB database' in caplog.text
    assert 'Lock conflict detected' not in caplog.text
    # Kills core/AddNot at check.py:133 (if conn -> if not conn): with `conn` still None, the mutant
    # calls `conn.close()` and raises AttributeError instead of letting the generator return unyielded.
    assert "generator didn't yield" in caplog.text


def test_initialize_config_extends_tags_with_instance_tags():
    # Kills core/ReplaceComparisonOperator_IsNot_Is and core/AddNot at check.py:147 (self.tags is not None).
    instance = common.DEFAULT_INSTANCE | {'tags': ['env:test']}
    check = DuckdbCheck('duckdb', {}, [instance])
    check.initialize_config()
    assert 'env:test' in check._tags


def test_execute_query_raw_returns_no_rows_and_counts_error_for_empty_result():
    # Kills the core/AddNot/NumberReplacer mutants at check.py:86 (len(...) < 1), and the
    # core/NumberReplacer mutants at check.py:87 (_query_errors += 1), for an empty result set.
    check = DuckdbCheck('duckdb', {}, [common.DEFAULT_INSTANCE])
    with check.connect() as conn:
        check._connection = conn
        rows = list(check._execute_query_raw("select version() where 1=0;"))

    assert rows == []
    assert check._query_errors == 1


def test_execute_query_raw_processes_every_row_for_multi_row_result():
    # Kills core/ReplaceComparisonOperator_Lt_NotEq at check.py:86: a 2-row result is `< 1` False (all
    # rows processed, no error counted) but `!= 1` True (rows dropped, error counted) under the mutant.
    check = DuckdbCheck('duckdb', {}, [common.DEFAULT_INSTANCE])
    with check.connect() as conn:
        check._connection = conn
        rows = list(
            check._execute_query_raw(
                "select name from duckdb_settings() where name='memory_limit' or name='worker_threads';"
            )
        )

    assert len(rows) == 2
    assert check._query_errors == 0


def test_execute_query_raw_extracts_name_group_from_pattern(caplog):
    # Kills the core/NumberReplacer mutants at check.py:98 (group(1) -> group(2)/group(0)) and
    # core/AddNot at check.py:94, by checking the extracted setting name in the debug log for a
    # non-version query with exactly one row.
    caplog.set_level(logging.DEBUG)
    check = DuckdbCheck('duckdb', {}, [common.DEFAULT_INSTANCE])
    with check.connect() as conn:
        check._connection = conn
        rows = list(check._execute_query_raw("select value from duckdb_settings() where name = 'worker_threads';"))

    # worker_threads defaults to the host CPU count, which differs across machines and CI
    # runners. We deliberately assert the result SHAPE (one numeric row) instead of a specific
    # value; the mutant-killing check is the extracted setting name in the debug log below.
    assert len(rows) == 1 and rows[0][0].isdigit()
    assert 'From query: "worker_threads"' in caplog.text


def test_queries_processor_does_not_submit_version_for_non_version_query_names(datadog_agent):
    # Kills the core/AddNot mutant at check.py:110, using query names that sort both below
    # ('memory_limit') and above ('worker_threads') the string 'version'.
    check = DuckdbCheck('duckdb', {}, [common.DEFAULT_INSTANCE])
    check.check_id = 'test:query-routing'

    check._queries_processor(('v9.9.9',), 'memory_limit')
    check._queries_processor(('v9.9.9',), 'worker_threads')

    datadog_agent.assert_metadata_count(0)


def test_queries_processor_submits_version_for_non_interned_version_string(datadog_agent):
    # Kills core/ReplaceComparisonOperator_Eq_Is at check.py:110: a `query_name` built at runtime
    # (not a literal) is `== 'version'` True but `is 'version'` False, since it isn't the same
    # interned string object as the literal used elsewhere in check.py.
    check = DuckdbCheck('duckdb', {}, [common.DEFAULT_INSTANCE])
    check.check_id = 'test:query-routing-non-interned'
    runtime_built_version = ''.join(['ver', 'sion'])

    check._queries_processor(('v2.3.4',), runtime_built_version)

    datadog_agent.assert_metadata(
        'test:query-routing-non-interned',
        {
            'version.scheme': 'semver',
            'version.major': '2',
            'version.minor': '3',
            'version.patch': '4',
            'version.raw': '2.3.4',
        },
    )


def test_submit_version_sets_semver_metadata_for_three_part_version(datadog_agent):
    # Kills core/NumberReplacer at check.py:159/163/164/165 (slice/index offsets) and the
    # core/ReplaceComparisonOperator_GtE_Gt mutant at check.py:162, using a version with 3 distinct parts.
    check = DuckdbCheck('duckdb', {}, [common.DEFAULT_INSTANCE])
    check.check_id = 'test:version-3-parts'
    check.submit_version(('v2.3.4',))
    datadog_agent.assert_metadata(
        'test:version-3-parts',
        {
            'version.scheme': 'semver',
            'version.major': '2',
            'version.minor': '3',
            'version.patch': '4',
            'version.raw': '2.3.4',
        },
    )


def test_submit_version_uses_first_row_of_multi_row_result(datadog_agent):
    # Kills core/NumberReplacer at check.py:158 (row[0] -> row[-1]): with a 2-element row, the first
    # element is the real version and the last is not, so the two indices diverge.
    check = DuckdbCheck('duckdb', {}, [common.DEFAULT_INSTANCE])
    check.check_id = 'test:version-first-row'
    check.submit_version(('v2.3.4', 'not_a_version'))
    datadog_agent.assert_metadata(
        'test:version-first-row',
        {
            'version.scheme': 'semver',
            'version.major': '2',
            'version.minor': '3',
            'version.patch': '4',
            'version.raw': '2.3.4',
        },
    )


def test_submit_version_logs_malformed_for_two_part_version(caplog, datadog_agent):
    # Kills the core/ReplaceComparisonOperator_GtE_NotEq/Lt/LtE mutants, core/AddNot, and
    # core/ReplaceComparisonOperator_GtE_IsNot at check.py:162, using a version with only 2 parts.
    caplog.set_level(logging.DEBUG)
    check = DuckdbCheck('duckdb', {}, [common.DEFAULT_INSTANCE])
    check.check_id = 'test:version-2-parts'
    check.submit_version(('v1.1',))

    assert 'Malformed DuckDB version format' in caplog.text
    assert 'Could not retrieve version metadata' not in caplog.text
    datadog_agent.assert_metadata_count(0)


def test_submit_version_uses_first_three_parts_for_four_part_version(datadog_agent):
    # Kills the core/ReplaceComparisonOperator_GtE_Eq/Is mutants at check.py:162, using a version with
    # 4 parts, where the extra trailing part must be ignored.
    check = DuckdbCheck('duckdb', {}, [common.DEFAULT_INSTANCE])
    check.check_id = 'test:version-4-parts'
    check.submit_version(('v1.2.3.4',))
    datadog_agent.assert_metadata(
        'test:version-4-parts',
        {
            'version.scheme': 'semver',
            'version.major': '1',
            'version.minor': '2',
            'version.patch': '3',
            'version.raw': '1.2.3',
        },
    )


def test_submit_version_handles_processing_exception_without_raising(caplog, datadog_agent):
    # Kills core/ExceptionReplacer at check.py:177: a malformed row must be swallowed and logged, not raised.
    caplog.set_level(logging.WARNING)
    check = DuckdbCheck('duckdb', {}, [common.DEFAULT_INSTANCE])
    check.check_id = 'test:version-error'
    check.submit_version(())

    assert 'Could not retrieve version metadata' in caplog.text
    datadog_agent.assert_metadata_count(0)


def test_submit_version_skipped_when_metadata_collection_disabled(datadog_agent):
    # Kills core/RemoveDecorator at check.py:152: the metadata_entrypoint decorator is what gates
    # submit_version on the Agent's enable_metadata_collection setting.
    datadog_agent._config['enable_metadata_collection'] = False
    check = DuckdbCheck('duckdb', {}, [common.DEFAULT_INSTANCE])
    check.check_id = 'test:version-disabled'
    check.submit_version(('v2.3.4',))
    datadog_agent.assert_metadata_count(0)


def test_executor_error_handler_increments_query_errors_by_one():
    # Kills the core/NumberReplacer mutants at check.py:182 (_query_errors += 1 -> += 2/0).
    check = DuckdbCheck('duckdb', {}, [common.DEFAULT_INSTANCE])
    check._executor_error_handler('boom')
    assert check._query_errors == 1
