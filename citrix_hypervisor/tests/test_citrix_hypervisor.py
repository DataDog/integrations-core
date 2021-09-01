# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import logging

import mock
import pytest

from datadog_checks.base import AgentCheck
from datadog_checks.citrix_hypervisor import CitrixHypervisorCheck
from datadog_checks.dev.utils import get_metadata_metrics

SESSION_MASTER = {
    'Status': 'Success',
    'Value': 'OpaqueRef:c908ccc4-4355-4328-b07d-c85dc7242b03',
}
SESSION_SLAVE = {
    'Status': 'Failure',
    'ErrorDescription': ['HOST_IS_SLAVE', '192.168.101.102'],
}
SESSION_ERROR = {
    'Status': 'Failure',
    'ErrorDescription': ['SESSION_AUTHENTICATION_FAILED'],
}

SERVER_TYPE_SESSION_MAP = {
    'master': SESSION_MASTER,
    'slave': SESSION_SLAVE,
    'error': SESSION_ERROR,
}


def mocked_xenserver(server_type):
    xenserver = mock.MagicMock()
    xenserver.session.login_with_password.return_value = SERVER_TYPE_SESSION_MAP.get(server_type, {})
    return xenserver


def _assert_metrics(aggregator, custom_tags, count=1):
    host_tag = 'citrix_hypervisor_host:4cff6b2b-a236-42e0-b388-c78a413f5f46'
    vm_tag = 'citrix_hypervisor_vm:cc11e6e9-5071-4707-830a-b87e5618e874'
    METRICS = [
        ('host.cache_hits', [host_tag, 'cache_sr:e358b352-5dda-5261-6a91-f7b73e2bcbae']),
        ('host.cache_misses', [host_tag, 'cache_sr:e358b352-5dda-5261-6a91-f7b73e2bcbae']),
        ('host.cache_size', [host_tag, 'cache_sr:e358b352-5dda-5261-6a91-f7b73e2bcbae']),
        ('host.cache_hits', [host_tag, 'cache_sr:70039e15-abfe-85f7-a703-798b05110ee8']),
        ('host.cache_misses', [host_tag, 'cache_sr:70039e15-abfe-85f7-a703-798b05110ee8']),
        ('host.cache_size', [host_tag, 'cache_sr:70039e15-abfe-85f7-a703-798b05110ee8']),
        ('host.pif.rx', [host_tag, 'interface:aggr']),
        ('host.pif.tx', [host_tag, 'interface:aggr']),
        ('host.pif.rx', [host_tag, 'interface:eth0']),
        ('host.pif.tx', [host_tag, 'interface:eth0']),
        ('host.pif.rx', [host_tag, 'interface:eth1']),
        ('host.pif.tx', [host_tag, 'interface:eth1']),
        ('host.cpu', [host_tag, 'cpu_id:0']),
        ('host.cpu', [host_tag, 'cpu_id:0-C0']),
        ('host.cpu', [host_tag, 'cpu_id:0-C1']),
        ('host.memory.free_kib', [host_tag]),
        ('host.memory.reclaimed', [host_tag]),
        ('host.memory.reclaimed_max', [host_tag]),
        ('host.memory.total_kib', [host_tag]),
        ('host.pool.session_count', [host_tag]),
        ('host.pool.task_count', [host_tag]),
        ('host.xapi.allocation_kib', [host_tag]),
        ('host.xapi.free_memory_kib', [host_tag]),
        ('host.xapi.live_memory_kib', [host_tag]),
        ('host.xapi.memory_usage_kib', [host_tag]),
        ('host.xapi.open_fds', [host_tag]),
        ('vm.cpu', [vm_tag, 'cpu_id:0']),
        ('vm.memory', [vm_tag]),
    ]

    for m in METRICS:
        aggregator.assert_metric('citrix_hypervisor.{}'.format(m[0]), tags=m[1] + custom_tags, count=count)


@pytest.mark.parametrize(
    'side_effect, expected_session, tag',
    [
        pytest.param([mocked_xenserver('error')], {}, []),
        pytest.param([mocked_xenserver('master')], SESSION_MASTER, ['server_type:master']),
        pytest.param([mocked_xenserver('slave'), mocked_xenserver('master')], SESSION_MASTER, ['server_type:slave']),
        pytest.param([mocked_xenserver('slave'), mocked_xenserver('error')], {}, ['server_type:slave']),
        pytest.param(mock.Mock(side_effect=Exception('Error')), {}, []),
        pytest.param([mocked_xenserver('slave'), mock.Mock(side_effect=Exception('Error'))], {}, ['server_type:slave']),
    ],
)
def test_open_session(instance, side_effect, expected_session, tag):
    with mock.patch('six.moves.xmlrpc_client.Server', side_effect=side_effect):
        check = CitrixHypervisorCheck('citrix_hypervisor', {}, [instance])
        session = check.open_session()

        assert session == expected_session
        assert tag == check._additional_tags


@pytest.mark.usefixtures('mock_responses')
@pytest.mark.unit
@pytest.mark.parametrize('server_type', [pytest.param('master'), pytest.param('slave')])
def test_check(aggregator, instance, server_type):
    with mock.patch('six.moves.xmlrpc_client.Server', return_value=mocked_xenserver(server_type)):
        check = CitrixHypervisorCheck('citrix_hypervisor', {}, [instance])
        check.check(instance)

        _assert_metrics(aggregator, ['foo:bar', 'server_type:{}'.format(server_type)])

        aggregator.assert_all_metrics_covered()
        aggregator.assert_metrics_using_metadata(get_metadata_metrics())


@pytest.mark.usefixtures('mock_responses')
@pytest.mark.unit
@pytest.mark.parametrize(
    'url, expected_status',
    [
        pytest.param('mocked', AgentCheck.OK),
        pytest.param('wrong', AgentCheck.CRITICAL),
    ],
)
def test_service_check(aggregator, url, expected_status):
    instance = {'url': url}
    check = CitrixHypervisorCheck('citrix_hypervisor', {}, [instance])
    check.check(instance)

    aggregator.assert_service_check('citrix_hypervisor.can_connect', expected_status, tags=[])


@pytest.mark.usefixtures('mock_responses')
@pytest.mark.unit
def test_initialization(caplog):
    caplog.clear()
    caplog.set_level(logging.WARNING)

    # Connection succeded
    check = CitrixHypervisorCheck('citrix_hypervisor', {}, [{'url': 'mocked'}])
    check._check_connection()
    assert check._last_timestamp == 1627907477

    # Connection failure
    check = CitrixHypervisorCheck('citrix_hypervisor', {}, [{'url': 'wrong'}])
    check._check_connection()
    assert check._last_timestamp == 0
    assert "Couldn't initialize the timestamp due to HTTP error" in caplog.text
