# (C) Datadog, Inc. 2019
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.tcp_check import TCPCheck


@pytest.mark.e2e
def test_e2e(dd_agent_check, instance):
    aggregator = dd_agent_check(instance, rate=True)

    expected_tags = ['foo:bar', 'target_host:datadoghq.com', 'port:80', 'instance:UpService']
    aggregator.assert_metric('network.tcp.can_connect', value=1, tags=expected_tags)
    aggregator.assert_service_check('tcp.can_connect', status=TCPCheck.OK, tags=expected_tags)
