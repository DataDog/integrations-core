# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

import pytest
from mock import mock_open, patch

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
