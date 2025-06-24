# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pymqi
import pytest
from mock import Mock, patch

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


def make_collector(instance=None):
    if instance is None:
        instance = {'queues': []}
    config = IBMMQConfig(instance, {})
    return QueueMetricCollector(config, Mock(), Mock(), Mock(), Mock(), Mock())


def test_discover_queues_handles_known_mq_errors(instance):
    collector = make_collector(instance)
    queue_manager = Mock()
    pcf_mock = Mock()
    pcf_mock.MQCMD_INQUIRE_Q_NAMES.return_value = [{3011: [b'QUEUE1']}]
    error = pymqi.MQMIError(2, 2033)
    pcf_mock.MQCMD_INQUIRE_Q.side_effect = error

    with patch('datadog_checks.ibm_mq.collectors.queue_metric_collector.pymqi.PCFExecute', return_value=pcf_mock):
        collector._submit_discovery_error_metric = Mock()
        collector.log = Mock()
        collector._discover_queues(queue_manager, 'pattern')
        assert not collector._submit_discovery_error_metric.called
        assert collector.log.debug.called


def test_discover_queues_submits_error_metric_on_unexpected_mq_error(instance):
    collector = make_collector(instance)
    queue_manager = Mock()
    pcf_mock = Mock()
    pcf_mock.MQCMD_INQUIRE_Q_NAMES.return_value = [{3011: [b'QUEUE1']}]
    error = pymqi.MQMIError(2, 9999)
    pcf_mock.MQCMD_INQUIRE_Q.side_effect = error

    with patch('datadog_checks.ibm_mq.collectors.queue_metric_collector.pymqi.PCFExecute', return_value=pcf_mock):
        collector._submit_discovery_error_metric = Mock()
        collector.log = Mock()
        collector._discover_queues(queue_manager, 'pattern')
        assert collector._submit_discovery_error_metric.called


def test_discover_queues_disconnects_on_exception(instance):
    collector = make_collector(instance)
    queue_manager = Mock()
    pcf_mock = Mock()
    with patch('datadog_checks.ibm_mq.collectors.queue_metric_collector.pymqi.PCFExecute', return_value=pcf_mock):
        # Simulate exception in queue discovery
        pcf_mock.MQCMD_INQUIRE_Q_NAMES.side_effect = Exception("fail")
        collector.log = Mock()
        collector._discover_queues(queue_manager, 'pattern')
        assert pcf_mock.disconnect.called


def test_discover_queues_warns_when_no_queues_found(instance):
    collector = make_collector(instance)
    queue_manager = Mock()
    with patch('datadog_checks.ibm_mq.collectors.queue_metric_collector.pymqi.PCFExecute') as PCFExecute:
        PCFExecute.return_value.MQCMD_INQUIRE_Q_NAMES.return_value = [{}]
        collector.warning = Mock()
        result = collector._discover_queues(queue_manager, 'pattern')
        assert collector.warning.called
        assert result == []
