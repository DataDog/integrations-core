# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import logging

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


def make_collector(instance=None, logger=None):
    if instance is None:
        instance = {'queues': []}
    config = IBMMQConfig(instance, {})
    if logger is None:
        logger = Mock()
    return QueueMetricCollector(config, Mock(), Mock(), Mock(), Mock(), logger)


@pytest.mark.parametrize(
    "auto_discover_queues_via_names, error_code",
    [
        (False, 2033),
        (False, 2034),
        (False, 9999),
        (True, 2033),
        (True, 2034),
        (True, 9999),
    ],
    ids=[
        "false_msg_available",
        "false_unknown_object_name",
        "false_unknown_error",
        "true_msg_available",
        "true_unknown_object_name",
        "true_unknown_error",
    ],
)
def test_discover_queues_and_handle_errors(instance, auto_discover_queues_via_names, error_code, caplog):
    # Test direct discovery method (_discover_queues) with known MQ errors
    # Should not raise, should log debug, should not call _submit_discovery_error_metric
    instance['auto_discover_queues_via_names'] = auto_discover_queues_via_names
    instance['auto_discover_queues'] = True  # Enable auto discovery so the methods are called

    # Create a real logger that can be captured by caplog
    logger = logging.getLogger('test_ibm_mq')
    logger.setLevel(logging.DEBUG)

    collector = make_collector(instance, logger)
    queue_manager = Mock()
    pcf_mock = Mock()
    error = pymqi.MQMIError(2, error_code)

    if auto_discover_queues_via_names:
        pcf_mock.MQCMD_INQUIRE_Q_NAMES.side_effect = error
    else:
        pcf_mock.MQCMD_INQUIRE_Q.side_effect = error

    with patch('datadog_checks.ibm_mq.collectors.queue_metric_collector.pymqi.PCFExecute', return_value=pcf_mock):
        collector._submit_discovery_error_metric = Mock()
        with caplog.at_level(logging.DEBUG):
            collector.discover_queues(queue_manager)

        if error_code == 2033:
            assert any(
                "No queue info available" in record.message for record in caplog.records if record.levelname == "DEBUG"
            )
            assert not collector._submit_discovery_error_metric.called
        elif error_code == 2034:
            assert any(
                "No matching queue of type" in record.message
                for record in caplog.records
                if record.levelname == "DEBUG"
            )
            assert not collector._submit_discovery_error_metric.called
        else:
            if auto_discover_queues_via_names:
                assert any(
                    "Error inquiring queue names for pattern" in record.message
                    for record in caplog.records
                    if record.levelname == "DEBUG"
                )
                assert collector._submit_discovery_error_metric.called
            else:
                assert any(
                    "Error discovering queue" in record.message
                    for record in caplog.records
                    if record.levelname == "WARNING"
                )
                assert not collector._submit_discovery_error_metric.called


# @pytest.mark.parametrize(
#     "auto_discover_queues_via_names, patch_method, side_effect_attr",
#     [
#         (False, "MQCMD_INQUIRE_Q", "MQCMD_INQUIRE_Q"),
#         (True, "MQCMD_INQUIRE_Q_NAMES", "MQCMD_INQUIRE_Q_NAMES"),
#     ],
#     ids=["direct_method", "via_names_method"],
# )
# def test_discover_queues_disconnects_on_exception(
#     instance, auto_discover_queues_via_names, patch_method, side_effect_attr
# ):
#     # Test both direct and via_names discovery methods disconnect on exception
#     instance['auto_discover_queues_via_names'] = auto_discover_queues_via_names
#     collector = make_collector(instance)
#     queue_manager = Mock()
#     pcf_mock = Mock()
#     with patch('datadog_checks.ibm_mq.collectors.queue_metric_collector.pymqi.PCFExecute', return_value=pcf_mock):
#         # Simulate exception in queue discovery
#         setattr(pcf_mock, side_effect_attr, Mock(side_effect=Exception("fail")))
#         collector.log = Mock()
#         collector.discover_queues(queue_manager)
#         assert pcf_mock.disconnect.called


# @pytest.mark.parametrize(
#     "auto_discover_queues_via_names, patch_method, return_value",
#     [
#         (False, "MQCMD_INQUIRE_Q", []),
#         (True, "MQCMD_INQUIRE_Q_NAMES", [{}]),
#     ],
#     ids=["direct_method", "via_names_method"],
# )
# def test_discover_queues_warns_when_no_queues_found(
#     instance, auto_discover_queues_via_names, patch_method, return_value
# ):
#     # Test both direct and via_names discovery methods warn when no queues found
#     instance['auto_discover_queues_via_names'] = auto_discover_queues_via_names
#     collector = make_collector(instance)
#     queue_manager = Mock()
#     with patch('datadog_checks.ibm_mq.collectors.queue_metric_collector.pymqi.PCFExecute') as PCFExecute:
#         getattr(PCFExecute.return_value, patch_method).return_value = return_value
#         collector.warning = Mock()
#         result = collector.discover_queues(queue_manager)
#         assert collector.warning.called
#         assert result == set()  # discover_queues returns a set


# @pytest.mark.parametrize(
#     "auto_discover_queues_via_names, expected_method, not_expected_method, expected_queue",
#     [
#         (False, "_discover_queues", "_discover_queues", "queue1"),
#         (True, "_discover_queues_via_names", "_discover_queues", "queue2"),
#     ],
#     ids=["direct_method", "via_names_method"],
# )
# def test_discover_queues_uses_correct_method_based_on_config(
#     instance, auto_discover_queues_via_names, expected_method, not_expected_method, expected_queue
# ):
#     # Test that the correct discovery method is chosen based on configuration
#     collector = make_collector(instance)
#     queue_manager = Mock()

#     collector._discover_queues = Mock(return_value=['queue1'])
#     collector._discover_queues_via_names = Mock(return_value=['queue2'])
#     collector.log = Mock()
#     collector.config.auto_discover_queues_via_names = auto_discover_queues_via_names

#     result = collector.discover_queues(queue_manager)
#     getattr(collector, expected_method).assert_called()
#     getattr(collector, not_expected_method).assert_not_called()
#     assert expected_queue in result
