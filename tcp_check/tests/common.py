# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

from datadog_checks.tcp_check import TCPCheck

HERE = os.path.dirname(os.path.abspath(__file__))

CHECK_NAME = "tcp_check"

INSTANCE = {'host': '127.0.0.1', 'port': 8000, 'timeout': 1.5, 'name': 'UpService', 'tags': ['foo:bar']}

INSTANCE_KO = {'host': '127.0.0.1', 'port': 65530, 'timeout': 1.5, 'name': 'DownService', 'tags': ["foo:bar"]}


def _test_check(aggregator):
    expected_tags = ['foo:bar', 'target_host:127.0.0.1', 'port:8000', 'instance:UpService']
    aggregator.assert_metric('network.tcp.can_connect', value=1, tags=expected_tags)
    aggregator.assert_service_check('tcp.can_connect', status=TCPCheck.OK, tags=expected_tags)
    aggregator.assert_all_metrics_covered()
    assert len(aggregator.service_checks('tcp.can_connect')) == 1
