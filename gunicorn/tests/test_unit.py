# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import logging
import sys

import mock
import psutil
import pytest

from datadog_checks.gunicorn import GUnicornCheck
from datadog_checks.gunicorn.gunicorn import GUnicornCheckError, get_gunicorn_version

from .common import CHECK_NAME, INSTANCE

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    'stdout, stderr, expect_metadata_count',
    [('gunicorn (version 19.9.0)', '', 5), ('', 'gunicorn (version 19.9.0)', 5), ('foo bar', '', 0), ('', '', 0)],
)
def test_collect_metadata_parsing_matching(aggregator, datadog_agent, stdout, stderr, expect_metadata_count):
    """Test all metadata collection code paths"""
    check = GUnicornCheck(CHECK_NAME, {}, [INSTANCE])
    check.check_id = 'test:123'

    with mock.patch('datadog_checks.gunicorn.gunicorn.get_gunicorn_version', return_value=(stdout, stderr, 0)):
        check.check(INSTANCE)

    datadog_agent.assert_metadata_count(expect_metadata_count)


def test_process_disappearing_during_scan(aggregator, caplog):
    """Test handling of processes that disappear during scanning"""
    caplog.clear()
    # Create a mock process that will raise NoSuchProcess when cmdline() is called
    mock_process = mock.Mock()
    mock_process.cmdline.side_effect = psutil.NoSuchProcess(1234, name="dd-test-gunicorn")
    mock_process.pid = 1234

    check = GUnicornCheck(CHECK_NAME, {}, [INSTANCE])
    caplog.set_level(logging.DEBUG)

    # Mock process_iter to return our disappearing process
    with mock.patch('psutil.process_iter', return_value=[mock_process]):
        check.check(INSTANCE)

    # Verify the service check shows critical since no processes were found
    aggregator.assert_service_check(
        "gunicorn.is_running",
        check.CRITICAL,
        tags=['app:' + INSTANCE['proc_name']],
        message="No gunicorn process with name {} found, skipping worker metrics".format(INSTANCE['proc_name']),
    )

    assert "Process dd-test-gunicorn (pid=1234) disappeared while scanning" in caplog.text


def test_get_gunicorn_version_captures_text_output(tmp_path):
    script = tmp_path / "fake_gunicorn.py"
    script.write_text("print('gunicorn (version 19.9.0)')\n")
    cmd = "{} {}".format(sys.executable, script)

    # Kills core/ReplaceTrueWithFalse at gunicorn.py:27 (capture_output/text=True must yield captured str output).
    stdout, stderr, returncode = get_gunicorn_version(cmd)

    assert returncode == 0
    assert isinstance(stdout, str)
    assert "gunicorn (version 19.9.0)" in stdout


def test_cpu_sleep_secs_default():
    # Kills core/NumberReplacer at gunicorn.py:39 (CPU_SLEEP_SECS must stay 0.1).
    assert GUnicornCheck.CPU_SLEEP_SECS == 0.1


def test_check_raises_for_instance_missing_proc_name():
    check = GUnicornCheck(CHECK_NAME, {}, [INSTANCE])

    with mock.patch('psutil.process_iter', return_value=[]):
        # Kills core/ReplaceOrWithAnd at gunicorn.py:60 (a truthy instance missing proc_name must still raise).
        with pytest.raises(GUnicornCheckError):
            check.check({'tags': ['foo']})

        # Kills core/ReplaceBinaryOperator_Mod_* at gunicorn.py:61 (message must be built via %, not +/-/*/...).
        with pytest.raises(GUnicornCheckError, match="^instance must specify: proc_name$"):
            check.check({})


def test_check_reports_critical_with_message_when_no_workers_found(aggregator):
    check = GUnicornCheck(CHECK_NAME, {}, [INSTANCE])
    check.check_id = 'test:123'

    master = mock.Mock()
    master.cmdline.return_value = ['gunicorn: master [{}]'.format(INSTANCE['proc_name'])]
    master.children.return_value = []

    with mock.patch('psutil.process_iter', return_value=[master]):
        with mock.patch('datadog_checks.gunicorn.gunicorn.get_gunicorn_version', return_value=('', '', 0)):
            check.check(INSTANCE)

    tags = ['app:' + INSTANCE['proc_name']]
    # Kills core/ReplaceBinaryOperator_Mod_*/Add_* at gunicorn.py:73/74/85/86 (message/tag building must use %/+).
    # Kills core/AddNot and core/NumberReplacer at gunicorn.py:75 (status must be CRITICAL when both counts are zero).
    aggregator.assert_service_check(
        "gunicorn.is_running",
        check.CRITICAL,
        tags=tags,
        message="0 working and 0 idle workers for {}".format(INSTANCE['proc_name']),
    )
    aggregator.assert_metric("gunicorn.workers", value=0, tags=tags + ['state:working'], count=1)
    aggregator.assert_metric("gunicorn.workers", value=0, tags=tags + ['state:idle'], count=1)


def test_check_reports_ok_when_only_working_workers_present(aggregator):
    check = GUnicornCheck(CHECK_NAME, {}, [INSTANCE])
    check.check_id = 'test:123'

    working_proc_1 = mock.Mock(pid=101)
    working_proc_1.cpu_times.side_effect = [(1.0, 0.0), (2.0, 0.0)]
    working_proc_2 = mock.Mock(pid=102)
    working_proc_2.cpu_times.side_effect = [(1.0, 0.0), (2.0, 0.0)]

    master = mock.Mock()
    master.cmdline.return_value = ['gunicorn: master [{}]'.format(INSTANCE['proc_name'])]
    master.children.return_value = [working_proc_1, working_proc_2]

    with mock.patch('psutil.process_iter', return_value=[master]):
        with mock.patch('datadog_checks.gunicorn.gunicorn.get_gunicorn_version', return_value=('', '', 0)):
            check.check(INSTANCE)

    # Kills core/ReplaceAndWithOr at gunicorn.py:75 (status must stay OK when only idle is zero, not both counts).
    aggregator.assert_service_check("gunicorn.is_running", check.OK, tags=['app:' + INSTANCE['proc_name']])


def test_check_reports_ok_when_only_idle_workers_present(aggregator):
    check = GUnicornCheck(CHECK_NAME, {}, [INSTANCE])
    check.check_id = 'test:123'

    idle_proc_1 = mock.Mock(pid=201)
    idle_proc_1.cpu_times.side_effect = [(1.0, 0.0), (1.0, 0.0)]
    idle_proc_2 = mock.Mock(pid=202)
    idle_proc_2.cpu_times.side_effect = [(1.0, 0.0), (1.0, 0.0)]

    master = mock.Mock()
    master.cmdline.return_value = ['gunicorn: master [{}]'.format(INSTANCE['proc_name'])]
    master.children.return_value = [idle_proc_1, idle_proc_2]

    with mock.patch('psutil.process_iter', return_value=[master]):
        with mock.patch('datadog_checks.gunicorn.gunicorn.get_gunicorn_version', return_value=('', '', 0)):
            check.check(INSTANCE)

    # Kills core/ReplaceComparisonOperator_Eq_GtE at gunicorn.py:75 (idle >= 0 is always true, so status must stay
    # OK when working is zero but idle is not, not just when idle is also zero).
    aggregator.assert_service_check("gunicorn.is_running", check.OK, tags=['app:' + INSTANCE['proc_name']])


def test_get_workers_from_procs_returns_children_of_each_master_proc():
    check = GUnicornCheck(CHECK_NAME, {}, [INSTANCE])

    master_1 = mock.Mock()
    master_1.children.return_value = ['child1', 'child2']
    master_2 = mock.Mock()
    master_2.children.return_value = ['child3']

    # Kills core/ZeroIterationForLoop at gunicorn.py:103 (loop must actually iterate over master_procs).
    result = check._get_workers_from_procs([master_1, master_2])

    assert result == ['child1', 'child2', 'child3']


def test_count_workers_with_no_worker_procs_returns_zero_zero():
    check = GUnicornCheck(CHECK_NAME, {}, [INSTANCE])

    # Kills core/NumberReplacer at gunicorn.py:108/109 (initial working/idle counters must start at 0).
    assert check._count_workers([]) == (0, 0)


def test_count_workers_classifies_by_cpu_time_change():
    check = GUnicornCheck(CHECK_NAME, {}, [INSTANCE])

    idle_proc_1 = mock.Mock(pid=1)
    idle_proc_1.cpu_times.side_effect = [(1.0, 0.0), (1.0, 0.0)]
    idle_proc_2 = mock.Mock(pid=2)
    idle_proc_2.cpu_times.side_effect = [(1.0, 0.0), (1.0, 0.0)]
    working_proc = mock.Mock(pid=3)
    working_proc.cpu_times.side_effect = [(1.0, 0.0), (5.0, 0.0)]
    decreasing_cpu_proc = mock.Mock(pid=4)
    decreasing_cpu_proc.cpu_times.side_effect = [(5.0, 0.0), (3.0, 0.0)]

    # Kills core/ReplaceUnaryOperator_Delete_Not and core/AddNot at gunicorn.py:111 (must not early-return
    # for non-empty input).
    # Kills core/ReplaceComparisonOperator_Eq_*/AddNot at gunicorn.py:139 and core/NumberReplacer at
    # gunicorn.py:140/142 (idle vs working classification and counters, including a lower second reading).
    working, idle = check._count_workers([idle_proc_1, idle_proc_2, working_proc, decreasing_cpu_proc])

    assert (working, idle) == (2, 2)


def test_count_workers_skips_procs_that_disappear_during_initial_scan():
    check = GUnicornCheck(CHECK_NAME, {}, [INSTANCE])

    disappearing_proc = mock.Mock(pid=1, name='disappearing')
    disappearing_proc.cpu_times.side_effect = psutil.NoSuchProcess(1)
    stable_proc = mock.Mock(pid=2)
    stable_proc.cpu_times.side_effect = [(1.0, 0.0), (1.0, 0.0)]

    # Kills core/ExceptionReplacer and core/ReplaceContinueWithBreak at gunicorn.py:120/122 (a proc
    # disappearing while collecting initial cpu times must be skipped, not crash or abort the scan).
    working, idle = check._count_workers([disappearing_proc, stable_proc])

    assert (working, idle) == (0, 1)


def test_count_workers_skips_pids_missing_initial_cpu_time():
    check = GUnicornCheck(CHECK_NAME, {}, [INSTANCE])

    flaky_proc = mock.Mock(pid=3)
    flaky_proc.cpu_times.side_effect = [psutil.NoSuchProcess(3), (2.0, 0.0)]
    stable_proc = mock.Mock(pid=4)
    stable_proc.cpu_times.side_effect = [(1.0, 0.0), (1.0, 0.0)]

    # Kills core/AddNot and core/ReplaceContinueWithBreak at gunicorn.py:130/132 (a pid missing from the
    # initial cpu-time snapshot must be skipped, not misclassified or abort the scan).
    working, idle = check._count_workers([flaky_proc, stable_proc])

    assert (working, idle) == (0, 1)


def test_count_workers_skips_procs_that_error_during_second_scan():
    check = GUnicornCheck(CHECK_NAME, {}, [INSTANCE])

    erroring_proc = mock.Mock(pid=5)
    erroring_proc.cpu_times.side_effect = [(1.0, 0.0), RuntimeError("boom")]
    stable_proc = mock.Mock(pid=6)
    stable_proc.cpu_times.side_effect = [(1.0, 0.0), (1.0, 0.0)]

    # Kills core/ExceptionReplacer and core/ReplaceContinueWithBreak at gunicorn.py:135/138 (an error
    # re-reading cpu time on the second pass must be skipped, not abort the whole scan).
    working, idle = check._count_workers([erroring_proc, stable_proc])

    assert (working, idle) == (0, 1)


def test_get_master_proc_by_name_matches_exact_cmdline():
    check = GUnicornCheck(CHECK_NAME, {}, [INSTANCE])

    matching_proc = mock.Mock()
    matching_proc.cmdline.return_value = ['gunicorn: master [web1]']
    non_matching_proc = mock.Mock()
    non_matching_proc.cmdline.return_value = ['something else']
    empty_cmdline_proc = mock.Mock()
    empty_cmdline_proc.cmdline.return_value = []
    matches_only_at_last_index_proc = mock.Mock()
    matches_only_at_last_index_proc.cmdline.return_value = ['not the master', 'gunicorn: master [web1]']
    lexicographically_smaller_proc = mock.Mock()
    lexicographically_smaller_proc.cmdline.return_value = ['aaa']

    with mock.patch(
        'psutil.process_iter',
        return_value=[
            matching_proc,
            non_matching_proc,
            empty_cmdline_proc,
            matches_only_at_last_index_proc,
            lexicographically_smaller_proc,
        ],
    ):
        # Kills core/ReplaceComparisonOperator_*/AddNot/ReplaceAndWithOr at gunicorn.py:152 (must match exact
        # non-empty cmdline[0] against the master name, nothing looser).
        # Kills core/NumberReplacer at gunicorn.py:152 (must compare cmdline[0], not cmdline[-1]).
        # Kills core/ReplaceComparisonOperator_Eq_LtE at gunicorn.py:152 ("aaa" <= master_name is true, so a
        # cmdline[0] that merely sorts before master_name must not match).
        result = check._get_master_proc_by_name('web1')

    assert result == [matching_proc]


def test_get_master_proc_by_name_skips_procs_with_psutil_errors(caplog):
    check = GUnicornCheck(CHECK_NAME, {}, [INSTANCE])
    caplog.set_level(logging.DEBUG)

    erroring_proc = mock.Mock()
    erroring_proc.pid = 1234
    erroring_proc.cmdline.side_effect = psutil.AccessDenied(1234)

    with mock.patch('psutil.process_iter', return_value=[erroring_proc]):
        # Kills core/ExceptionReplacer at gunicorn.py:156 (psutil.Error subclasses must be caught while
        # scanning, not propagate and crash the check).
        result = check._get_master_proc_by_name('web1')

    assert result == []

    # Kills core/ReplaceTrueWithFalse at gunicorn.py:157 (exc_info=True must attach a truthy traceback tuple;
    # exc_info=False stores the literal False, so this must check truthiness, not just "is not None").
    matching_records = [r for r in caplog.records if "Cannot read information from process" in r.getMessage()]
    assert matching_records and matching_records[0].exc_info


def test_get_master_proc_name_formats_with_percent():
    check = GUnicornCheck(CHECK_NAME, {}, [INSTANCE])

    # Kills core/ReplaceBinaryOperator_Mod_Add at gunicorn.py:168 (name must be interpolated via %, not +).
    assert GUnicornCheck._get_master_proc_name('web1') == 'gunicorn: master [web1]'
    # Kills core/RemoveDecorator at gunicorn.py:161 (@staticmethod must not implicitly bind self when
    # called through an instance).
    assert check._get_master_proc_name('web1') == 'gunicorn: master [web1]'


def test_collect_metadata_skipped_when_metadata_collection_disabled(aggregator, datadog_agent):
    check = GUnicornCheck(CHECK_NAME, {}, [INSTANCE])
    check.check_id = 'test:123'

    with mock.patch('psutil.process_iter', return_value=[]):
        with mock.patch.object(check, 'is_metadata_collection_enabled', return_value=False):
            with mock.patch(
                'datadog_checks.gunicorn.gunicorn.get_gunicorn_version',
                return_value=('gunicorn (version 19.9.0)', '', 0),
            ):
                check.check(INSTANCE)

    # Kills core/RemoveDecorator at gunicorn.py:170 (@AgentCheck.metadata_entrypoint must gate metadata
    # collection on is_metadata_collection_enabled).
    datadog_agent.assert_metadata_count(0)
