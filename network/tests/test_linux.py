# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import copy

import mock
import pytest
from six import PY3

from datadog_checks.base.utils.platform import Platform

from . import common

if PY3:
    long = int


CONNECTION_QUEUES_METRICS = [
    'system.net.tcp.recv_q',
    'system.net.tcp.send_q'
]


@pytest.mark.skipif(not Platform.is_linux, reason="Only works on Linux systems")
def test_collect_cx_queues(is_linux, is_bsd, check, aggregator):
    instance = copy.deepcopy(common.INSTANCE)
    instance['collect_connection_queues'] = True
    instance['collect_connection_state'] = True
    check_instance = check(instance)

    check_instance.check({})

    for metric in CONNECTION_QUEUES_METRICS:
        aggregator.assert_metric(metric)
    for metric in common.EXPECTED_METRICS:
        aggregator.assert_metric(metric)
    aggregator.assert_all_metrics_covered()
