# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.ibm_ace import IbmAceCheck
from datadog_checks.ibm_ace.subscription import FlowMonitoringSubscription, ResourceStatisticsSubscription

from .common import skip_windows_ci

pytestmark = [skip_windows_ci, pytest.mark.usefixtures('dd_environment'), pytest.mark.unit]


@pytest.mark.parametrize(
    "expected_res_stats, expected_msg_flows",
    [
        pytest.param(False, False, id="Metric collection disabled"),
        pytest.param(True, False, id="Resource stats collection enabled; message_flows disabled"),
        pytest.param(False, True, id="Resource stats collection disabled; message_flows enabled"),
        pytest.param(True, True, id="Resource stats collection enabled; message_flows enabled"),
    ],
)
def test_config(dd_run_check, aggregator, expected_res_stats, expected_msg_flows):
    test_instance = {
        'mq_server': 'localhost',
        'mq_port': 11414,
        'channel': 'DEV.ADMIN.SVRCONN',
        'queue_manager': 'QM1',
        'mq_user': 'admin',
        'mq_password': 'passw0rd',
        'resource_statistics': expected_res_stats,
        'message_flows': expected_msg_flows,
        'tags': ['foo:bar'],
    }

    check = IbmAceCheck('ibm_ace', {}, [test_instance])
    dd_run_check(check)

    if not expected_res_stats and not expected_msg_flows:
        assert len(check._subscriptions) == 0
    if expected_res_stats and expected_msg_flows:
        assert len(check._subscriptions) == 2
        assert isinstance(check._subscriptions[0], ResourceStatisticsSubscription)
        assert isinstance(check._subscriptions[1], FlowMonitoringSubscription)
    if expected_res_stats and not expected_msg_flows:
        assert len(check._subscriptions) == 1
        assert isinstance(check._subscriptions[0], ResourceStatisticsSubscription)
    if expected_msg_flows and not expected_res_stats:
        assert len(check._subscriptions) == 1
        assert isinstance(check._subscriptions[0], FlowMonitoringSubscription)

    assert check.config.resource_statistics == expected_res_stats
    assert check.config.message_flows == expected_msg_flows
