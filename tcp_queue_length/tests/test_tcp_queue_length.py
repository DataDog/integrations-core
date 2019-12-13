# (C) Datadog, Inc. 2019
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.tcp_queue_length import TcpQueueLengthCheck


def test_check(aggregator, instance):
    check = TcpQueueLengthCheck('tcp_queue_length', {}, {})
    check.check(instance)

    aggregator.assert_all_metrics_covered()
