# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import logging
import pytest

from datadog_checks.citrix_hypervisor.metrics import build_metric


logger = logging.getLogger(__name__)

@pytest.mark.unit
@pytest.mark.parametrize(
    'raw_metric, expected_name, expected_tags',
    [
        pytest.param(
            'AVERAGE:host:123-abc:pool_task_count', 'host.pool.task_count.avg', ['citrix_hypervisor_host:123-abc']
        ),
        pytest.param(
            'MIN:host:123-abc:xapi_free_memory_kib', 'host.xapi.free_memory_kib.min', ['citrix_hypervisor_host:123-abc']
        ),
        pytest.param(
            'AVERAGE:host:123-abc:sr_123-abc-456-def_cache_size',
            'host.cache_size.avg',
            ['citrix_hypervisor_host:123-abc', 'cache_sr:123-abc-456-def'],
        ),
        pytest.param('AVERAGE:vm:456-def:memory', 'vm.memory.avg', ['citrix_hypervisor_vm:456-def']),
    ],
)
def test_build_metric_good(raw_metric, expected_name, expected_tags, caplog):
    caplog.clear()
    caplog.set_level(logging.DEBUG)
    name, tags = build_metric(raw_metric, logger)

    expected_log = 'Found metric {} ({})'.format(name, raw_metric)

    assert name == expected_name
    assert tags == expected_tags

    assert expected_log == caplog.text
