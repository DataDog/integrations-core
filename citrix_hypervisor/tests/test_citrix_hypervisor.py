# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from typing import Any, Dict

import pytest

from datadog_checks.base.stubs.aggregator import AggregatorStub
from datadog_checks.citrix_hypervisor import CitrixHypervisorCheck
from datadog_checks.dev.utils import get_metadata_metrics


def _assert_metrics(aggregator, count=1, custom_tags=[]):
    host_tag = 'citrix_hypervisor_host:4cff6b2b-a236-42e0-b388-c78a413f5f46'
    vm_tag = 'citrix_hypervisor_vm:cc11e6e9-5071-4707-830a-b87e5618e874'
    METRICS = [
        ('host.cache_hits.avg', [host_tag, 'cache_sr:e358b352-5dda-5261-6a91-f7b73e2bcbae']),
        ('host.cache_misses.avg', [host_tag, 'cache_sr:e358b352-5dda-5261-6a91-f7b73e2bcbae']),
        ('host.cache_size.avg', [host_tag, 'cache_sr:e358b352-5dda-5261-6a91-f7b73e2bcbae']),
        ('host.cache_hits.avg', [host_tag, 'cache_sr:70039e15-abfe-85f7-a703-798b05110ee8']),
        ('host.cache_misses.avg', [host_tag, 'cache_sr:70039e15-abfe-85f7-a703-798b05110ee8']),
        ('host.cache_size.avg', [host_tag, 'cache_sr:70039e15-abfe-85f7-a703-798b05110ee8']),
        ('host.cpu.avg', [host_tag]),
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
        ('vm.cpu.avg', [vm_tag]),
        ('vm.memory.avg', [vm_tag]),
    ]

    for m in METRICS:
        aggregator.assert_metric('citrix_hypervisor.{}'.format(m[0]), tags=m[1] + custom_tags, count=count)


@pytest.mark.usefixtures('mock_responses')
@pytest.mark.unit
def test_check(aggregator, instance):
    # type: (AggregatorStub, Dict[str, Any]) -> None
    check = CitrixHypervisorCheck('citrix_hypervisor', {}, [instance])
    check.check(instance)

    _assert_metrics(aggregator)

    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
