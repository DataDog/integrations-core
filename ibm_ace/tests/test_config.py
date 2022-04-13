# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.ibm_ace import IbmAceCheck

from .common import skip_windows_ci

pytestmark = [skip_windows_ci, pytest.mark.usefixtures('dd_environment'), pytest.mark.unit]


@pytest.mark.parametrize(
    "test_instance, expected_res_stats, expected_msg_flows",
    [
        pytest.param(
            {
                'mq_server': 'localhost',
                'mq_port': 11414,
                'channel': 'DEV.ADMIN.SVRCONN',
                'queue_manager': 'QM1',
                'mq_user': 'admin',
                'mq_password': 'passw0rd',
                'resource_statistics': False,
                'message_flows': False,
                'tags': ['foo:bar'],
            },
            False,
            False,
            id="Metric collection disabled",
        ),
        pytest.param(
            {
                'mq_server': 'localhost',
                'mq_port': 11414,
                'channel': 'DEV.ADMIN.SVRCONN',
                'queue_manager': 'QM1',
                'mq_user': 'admin',
                'mq_password': 'passw0rd',
                'resource_statistics': True,
                'message_flows': False,
                'tags': ['foo:bar'],
            },
            True,
            False,
            id="Resource stats collection enabled; message_flows disabled",
        ),
        pytest.param(
            {
                'mq_server': 'localhost',
                'mq_port': 11414,
                'channel': 'DEV.ADMIN.SVRCONN',
                'queue_manager': 'QM1',
                'mq_user': 'admin',
                'mq_password': 'passw0rd',
                'resource_statistics': False,
                'message_flows': True,
                'tags': ['foo:bar'],
            },
            False,
            True,
            id="Resource stats collection disabled; message_flows enabled",
        ),
    ],
)
def test_config(dd_run_check, aggregator, test_instance, expected_res_stats, expected_msg_flows):

    check = IbmAceCheck('ibm_ace', {}, [test_instance])
    dd_run_check(check)

    assert check.config.resource_statistics == expected_res_stats
    assert check.config.message_flows == expected_msg_flows
