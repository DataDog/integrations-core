# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import os

from mock import mock_open, patch
import pytest

from datadog_checks.linux_proc_extras import MoreUnixCheck


CHECK_NAME = 'linux_proc_extras'

HERE = os.path.abspath(os.path.dirname(__file__))
FIXTURE_DIR = os.path.join(HERE, "fixtures")

INODE_GAUGES = [
    'system.inodes.total',
    'system.inodes.used'
]

PROC_COUNTS = [
    'system.linux.context_switches',
    'system.linux.processes_created',
    'system.linux.interrupts'
]

ENTROPY_GAUGES = [
    'system.entropy.available'
]

PROCESS_STATS_GAUGES = [
    'system.processes.states',
    'system.processes.priorities'
]


@pytest.fixture
def aggregator():
    from datadog_checks.stubs import aggregator
    aggregator.reset()
    return aggregator


@pytest.fixture
def check():
    return MoreUnixCheck(CHECK_NAME, {}, {})


# Really a basic check to see if all metrics are there
def test_check(aggregator, check):

    check.tags = []
    check.set_paths()

    with open(os.path.join(FIXTURE_DIR, "entropy_avail")) as f:
        m = mock_open(read_data=f.read())
        with patch('__builtin__.open', m):
            check.get_entropy_info()

    with open(os.path.join(FIXTURE_DIR, "inode-nr")) as f:
        m = mock_open(read_data=f.read())
        with patch('__builtin__.open', m):
            check.get_inode_info()

    with open(os.path.join(FIXTURE_DIR, "proc-stat")) as f:
        m = mock_open(read_data=f.read())
        with patch('__builtin__.open', m):
            check.get_stat_info()

    with open(os.path.join(FIXTURE_DIR, "process_stats")) as f:
        with patch(
            'datadog_checks.linux_proc_extras.linux_proc_extras.get_subprocess_output',
            return_value=(f.read(), "", 0)
        ):
            check.get_process_states()

    # Assert metrics
    for metric in PROC_COUNTS + INODE_GAUGES + ENTROPY_GAUGES + PROCESS_STATS_GAUGES:
        aggregator.assert_metric(metric)

    aggregator.assert_all_metrics_covered()
