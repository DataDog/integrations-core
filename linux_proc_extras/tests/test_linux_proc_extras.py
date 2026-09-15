# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

import pytest
from mock import mock_open, patch

from datadog_checks.base.stubs.aggregator import AggregatorStub
from datadog_checks.base.stubs.datadog_agent import DatadogAgentStub
from datadog_checks.linux_proc_extras import MoreUnixCheck

from . import common

pytestmark = pytest.mark.unit


# Really a basic check to see if all metrics are there
def test_check(aggregator, check):
    check.tags = []
    check.set_paths()

    with open(os.path.join(common.FIXTURE_DIR, "entropy_avail")) as f:
        m = mock_open(read_data=f.read())
        with patch('datadog_checks.linux_proc_extras.linux_proc_extras.open', m):
            check.get_entropy_info()

    with open(os.path.join(common.FIXTURE_DIR, "inode-nr")) as f:
        m = mock_open(read_data=f.read())
        with patch('datadog_checks.linux_proc_extras.linux_proc_extras.open', m):
            check.get_inode_info()

    with open(os.path.join(common.FIXTURE_DIR, "proc-stat")) as f:
        m = mock_open(read_data=f.read())
        with patch('datadog_checks.linux_proc_extras.linux_proc_extras.open', m):
            check.get_stat_info()

    with open(os.path.join(common.FIXTURE_DIR, "fips_enabled")) as f:
        m = mock_open(read_data=f.read())
        with patch('datadog_checks.linux_proc_extras.linux_proc_extras.open', m):
            check.get_fips_info()

    with open(os.path.join(common.FIXTURE_DIR, "process_stats")) as f:
        with patch(
            'datadog_checks.linux_proc_extras.linux_proc_extras.get_subprocess_output', return_value=(f.read(), "", 0)
        ):
            check.get_process_states()

    with open(os.path.join(common.FIXTURE_DIR, "interrupts")) as f:
        m = mock_open(read_data=f.read())
        with patch('datadog_checks.linux_proc_extras.linux_proc_extras.open', m):
            check.get_interrupts_info()

    # Assert metrics
    for metric in common.EXPECTED_METRICS:
        aggregator.assert_metric(metric)

    for irq in common.INTERRUPTS_IDS:
        for cpu_id in range(common.CPU_COUNT):
            tags = ["irq:{}".format(irq), "cpu_id:{}".format(cpu_id)]
            aggregator.assert_metric("system.linux.irq", value=None, tags=tags)

    aggregator.assert_all_metrics_covered()


@pytest.mark.parametrize('content, expected_value', [('1\n', 1.0), ('0\n', 0.0)])
def test_fips_info(aggregator: AggregatorStub, check: MoreUnixCheck, content: str, expected_value: float) -> None:
    m = mock_open(read_data=content)
    with patch('datadog_checks.linux_proc_extras.linux_proc_extras.open', m):
        check.get_fips_info()

    m.assert_called_once_with('/proc/sys/crypto/fips_enabled', 'r')
    aggregator.assert_metric('system.crypto.fips_enabled', value=expected_value, count=1, tags=[common.EXPECTED_TAG])
    aggregator.assert_all_metrics_covered()


def test_fips_info_honors_procfs_path(
    aggregator: AggregatorStub, check: MoreUnixCheck, datadog_agent: DatadogAgentStub
) -> None:
    with patch.dict(datadog_agent._config, {'procfs_path': '/host/proc'}):
        check.set_paths()

    m = mock_open(read_data='1\n')
    with patch('datadog_checks.linux_proc_extras.linux_proc_extras.open', m):
        check.get_fips_info()

    m.assert_called_once_with('/host/proc/sys/crypto/fips_enabled', 'r')
    aggregator.assert_metric('system.crypto.fips_enabled', value=1.0, count=1, tags=[common.EXPECTED_TAG])
    aggregator.assert_all_metrics_covered()


def test_fips_info_missing_file(aggregator: AggregatorStub, check: MoreUnixCheck) -> None:
    with patch('datadog_checks.linux_proc_extras.linux_proc_extras.open', side_effect=FileNotFoundError):
        check.get_fips_info()

    aggregator.assert_metric('system.crypto.fips_enabled', value=0.0, count=1, tags=[common.EXPECTED_TAG])
    aggregator.assert_all_metrics_covered()


def test_fips_info_unreadable(aggregator: AggregatorStub, check: MoreUnixCheck) -> None:
    with patch('datadog_checks.linux_proc_extras.linux_proc_extras.open', side_effect=PermissionError):
        check.get_fips_info()

    aggregator.assert_metric('system.crypto.fips_enabled', count=0)


def test_fips_info_unparseable(aggregator: AggregatorStub, check: MoreUnixCheck) -> None:
    m = mock_open(read_data='not a number\n')
    with patch('datadog_checks.linux_proc_extras.linux_proc_extras.open', m):
        check.get_fips_info()

    aggregator.assert_metric('system.crypto.fips_enabled', count=0)
