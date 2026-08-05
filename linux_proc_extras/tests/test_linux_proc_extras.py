# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

import pytest

from . import common

pytestmark = pytest.mark.unit


def _read_fixture(name):
    with open(os.path.join(common.FIXTURE_DIR, name)) as f:
        return f.read()


# Really a basic check to see if all metrics are there
def test_check(aggregator, check, mock_safe_os):
    check.tags = []
    check.set_paths()

    mock_safe_os.add_files(
        {
            check.proc_path_map['entropy_info']: _read_fixture("entropy_avail"),
            check.proc_path_map['inode_info']: _read_fixture("inode-nr"),
            check.proc_path_map['stat_info']: _read_fixture("proc-stat"),
            check.proc_path_map['interrupts_info']: _read_fixture("interrupts"),
        }
    )
    mock_safe_os.set_command_output(['ps', '--no-header', '-eo', 'stat'], stdout=_read_fixture("process_stats"))

    check.get_entropy_info()
    check.get_inode_info()
    check.get_stat_info()
    check.get_process_states()
    check.get_interrupts_info()

    # Assert metrics
    for metric in common.EXPECTED_METRICS:
        aggregator.assert_metric(metric)

    for irq in common.INTERRUPTS_IDS:
        for cpu_id in range(common.CPU_COUNT):
            tags = ["irq:{}".format(irq), "cpu_id:{}".format(cpu_id)]
            aggregator.assert_metric("system.linux.irq", value=None, tags=tags)

    aggregator.assert_all_metrics_covered()
