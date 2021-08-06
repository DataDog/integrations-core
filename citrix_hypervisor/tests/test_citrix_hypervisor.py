# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import logging

import pytest

from datadog_checks.base import AgentCheck
from datadog_checks.citrix_hypervisor import CitrixHypervisorCheck
from datadog_checks.dev.utils import get_metadata_metrics


def _assert_metrics(aggregator, custom_tags, count=1):
    host_tag = 'citrix_hypervisor_host:4cff6b2b-a236-42e0-b388-c78a413f5f46'
    vm_tag = 'citrix_hypervisor_vm:cc11e6e9-5071-4707-830a-b87e5618e874'
    METRICS = [
        ('host.cache_hits.avg', [host_tag, 'cache_sr:e358b352-5dda-5261-6a91-f7b73e2bcbae']),
        ('host.cache_misses.avg', [host_tag, 'cache_sr:e358b352-5dda-5261-6a91-f7b73e2bcbae']),
        ('host.cache_size.avg', [host_tag, 'cache_sr:e358b352-5dda-5261-6a91-f7b73e2bcbae']),
        ('host.cache_hits.avg', [host_tag, 'cache_sr:70039e15-abfe-85f7-a703-798b05110ee8']),
        ('host.cache_misses.avg', [host_tag, 'cache_sr:70039e15-abfe-85f7-a703-798b05110ee8']),
        ('host.cache_size.avg', [host_tag, 'cache_sr:70039e15-abfe-85f7-a703-798b05110ee8']),
        ('host.pif.rx.avg', [host_tag, 'interface:aggr']),
        ('host.pif.tx.avg', [host_tag, 'interface:aggr']),
        ('host.pif.rx.avg', [host_tag, 'interface:eth0']),
        ('host.pif.tx.avg', [host_tag, 'interface:eth0']),
        ('host.pif.rx.avg', [host_tag, 'interface:eth1']),
        ('host.pif.tx.avg', [host_tag, 'interface:eth1']),
        ('host.cpu.avg', [host_tag, 'cpu_id:0']),
        ('host.cpu.avg', [host_tag, 'cpu_id:0-C0']),
        ('host.cpu.avg', [host_tag, 'cpu_id:0-C1']),
        ('host.memory.free_kib.avg', [host_tag]),
        ('host.memory.reclaimed.avg', [host_tag]),
        ('host.memory.reclaimed_max.avg', [host_tag]),
        ('host.memory.total_kib.avg', [host_tag]),
        ('host.pool.session_count.avg', [host_tag]),
        ('host.pool.task_count.avg', [host_tag]),
        ('host.xapi.allocation_kib.avg', [host_tag]),
        ('host.xapi.free_memory_kib.avg', [host_tag]),
        ('host.xapi.live_memory_kib.avg', [host_tag]),
        ('host.xapi.memory_usage_kib.avg', [host_tag]),
        ('host.xapi.open_fds.avg', [host_tag]),
        ('vm.cpu.avg', [vm_tag, 'cpu_id:0']),
        ('vm.memory.avg', [vm_tag]),
    ]

    for m in METRICS:
        aggregator.assert_metric('citrix_hypervisor.{}'.format(m[0]), tags=m[1] + custom_tags, count=count)


@pytest.mark.usefixtures('mock_responses')
@pytest.mark.unit
def test_check(aggregator, instance):
    check = CitrixHypervisorCheck('citrix_hypervisor', {}, [instance])
    check.check(instance)

    _assert_metrics(aggregator, ['foo:bar'])

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
