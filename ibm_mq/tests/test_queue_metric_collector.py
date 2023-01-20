# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest
from mock import Mock

from datadog_checks.ibm_mq.collectors import QueueMetricCollector
from datadog_checks.ibm_mq.config import IBMMQConfig

pytestmark = pytest.mark.unit


def test_pattern_preceedes_autodiscovery(instance):
    instance['auto_discover_queues'] = True
    instance['queue_patterns'] = ['pattern']
    config = IBMMQConfig(instance, {})
    collector = QueueMetricCollector(config, Mock(), Mock(), Mock(), Mock(), Mock())
    collector._discover_queues = Mock(return_value=['pattern_queue'])
    queue_manager = Mock()

    discovered_queues = collector.discover_queues(queue_manager)
    collector._discover_queues.assert_called_once_with(queue_manager, 'pattern')
    assert discovered_queues == {'pattern_queue', 'DEV.QUEUE.1'}


def test_regex_precedes_autodiscovery(instance):
    instance['auto_discover_queues'] = True
    instance['queue_regex'] = ['pat*']
    config = IBMMQConfig(instance, {})
    collector = QueueMetricCollector(config, Mock(), Mock(), Mock(), Mock(), Mock())
    collector._discover_queues = Mock(return_value=['pattern_queue', 'other_queue'])
    queue_manager = Mock()

    discovered_queues = collector.discover_queues(queue_manager)
    collector._discover_queues.assert_called_once_with(queue_manager, '*')
    assert discovered_queues == {'pattern_queue', 'DEV.QUEUE.1'}
