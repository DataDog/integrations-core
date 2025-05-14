# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import logging

import mock
import psutil
import pytest

from datadog_checks.gunicorn import GUnicornCheck

from .common import CHECK_NAME, INSTANCE


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
    mock_process.cmdline.side_effect = psutil.NoSuchProcess(1234)  # 1234 is the pid
    mock_process.name.return_value = "dd-test-gunicorn"  # For the debug log message

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

    assert "Process dd-test-gunicorn disappeared while scanning" in caplog.text
