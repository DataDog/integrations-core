# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import logging

import mock
import pytest

from datadog_checks.citrix_hypervisor import metrics

logger = logging.getLogger(__name__)


@pytest.mark.unit
@pytest.mark.parametrize(
    'raw_metric, expected_name, expected_tags',
    [
        pytest.param(
            'AVERAGE:host:123-abc:pool_task_count', 'host.pool.task_count', ['citrix_hypervisor_host:123-abc']
        ),
        pytest.param(
            'AVERAGE:host:123-abc:sr_123-abc-456-def_cache_size',
            'host.cache_size',
            ['citrix_hypervisor_host:123-abc', 'cache_sr:123-abc-456-def'],
        ),
        pytest.param('AVERAGE:vm:456-def:memory', 'vm.memory', ['citrix_hypervisor_vm:456-def']),
    ],
)
def test_build_metric_good(raw_metric, expected_name, expected_tags, caplog):
    caplog.clear()
    caplog.set_level(logging.DEBUG)

    new_regex_metrics = metrics.REGEX_METRICS + [
        {
            'regex': '([a-z0-9-]+)_id1_([a-z0-9-]+)_id2',
            'name': '.test_id',
            'tags': (
                'id1',
                'id2',
            ),
        }
    ]

    with mock.patch('datadog_checks.citrix_hypervisor.metrics.REGEX_METRICS', new_regex_metrics):
        name, tags = metrics.build_metric(raw_metric, logger)

        expected_log = 'Found metric {} ({})'.format(name, raw_metric)

        assert name == expected_name
        assert tags == expected_tags

        assert expected_log in caplog.text


@pytest.mark.unit
@pytest.mark.parametrize(
    'raw_metric, expected_log',
    [
        pytest.param('AVG:stuff:id:metric_name', 'Unknown format for metric {}'),
        pytest.param('MIN:host:123-abc:xapi_free_memory_kib', 'Unknown format for metric {}'),
        pytest.param('bad_format', 'Unknown format for metric {}'),
        pytest.param('AVERAGE:stuff:id:metric_name', 'Ignoring metric {}'),
    ],
)
def test_build_metric_error(raw_metric, expected_log, caplog):
    caplog.clear()
    caplog.set_level(logging.DEBUG)

    name, tags = metrics.build_metric(raw_metric, logger)

    assert name is None
    assert tags is None
    assert expected_log.format(raw_metric) in caplog.text
