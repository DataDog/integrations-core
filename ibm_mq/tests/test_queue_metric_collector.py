# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import logging

import pymqi
import pytest
from dateutil import tz
from mock import Mock, patch

from datadog_checks.ibm_mq.collectors import QueueMetricCollector
from datadog_checks.ibm_mq.config import IBMMQConfig
from datadog_checks.ibm_mq.stats.queue_stats import QueueStats

from . import common

pytestmark = pytest.mark.unit


def test_filtered_queues_none_without_queue_patterns_or_regex(instance, get_check):
    check = get_check(instance)
    collector = check.queue_metric_collector
    collector.discover_queues(Mock())
    assert collector.filtered_queues is None


def test_filtered_queues_tracks_monitored_queues_queue_patterns(instance):
    instance['queue_patterns'] = ['pattern']
    instance['auto_discover_queues'] = False
    config = IBMMQConfig(instance, {})
    collector = QueueMetricCollector(config, Mock(), Mock(), Mock(), Mock(), Mock())
    collector._discover_queues = Mock(return_value=['pattern_queue'])
    queue_manager = Mock()
    collector.discover_queues(queue_manager)
    assert collector.filtered_queues == {'pattern_queue', common.QUEUE}


def test_filtered_queues_tracks_monitored_queues_queue_regex(instance):
    instance['queue_regex'] = [r'^pat.*$']
    instance['auto_discover_queues'] = False
    instance['queues'] = []
    config = IBMMQConfig(instance, {})
    collector = QueueMetricCollector(config, Mock(), Mock(), Mock(), Mock(), Mock())
    collector._discover_queues = Mock(return_value=['pattern_queue', 'other_queue'])
    queue_manager = Mock()
    collector.discover_queues(queue_manager)
    assert collector.filtered_queues == {'pattern_queue'}


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


@pytest.mark.parametrize(
    "auto_discover_queues_via_names, error_code",
    [
        (False, 2033),
        (False, 2085),
        (False, 9999),
        (True, 2033),
        (True, 2085),
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
def test_discover_queues_and_handle_errors(instance, auto_discover_queues_via_names, error_code, caplog, get_check):
    # Test direct discovery method (_discover_queues) with known MQ errors
    # Should not raise, should log debug, should not call _submit_discovery_error_metric
    instance['auto_discover_queues_via_names'] = auto_discover_queues_via_names
    instance['auto_discover_queues'] = True
    instance['queues'] = []

    check = get_check(instance)
    collector = check.queue_metric_collector
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
            if auto_discover_queues_via_names:
                assert any(
                    "Error inquiring queue names for pattern" in record.message
                    for record in caplog.records
                    if record.levelname == "DEBUG"
                )
                assert collector._submit_discovery_error_metric.called
            else:
                assert any(
                    "No queue info available" in record.message
                    for record in caplog.records
                    if record.levelname == "DEBUG"
                )
                assert not collector._submit_discovery_error_metric.called
        elif error_code == 2085:  # MQRC_UNKNOWN_OBJECT_NAME
            if auto_discover_queues_via_names:
                assert any(
                    "Error inquiring queue names for pattern" in record.message
                    for record in caplog.records
                    if record.levelname == "DEBUG"
                )
                assert collector._submit_discovery_error_metric.called
            else:
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


@pytest.mark.parametrize(
    "auto_discover_queues_via_names, side_effect_attr",
    [
        (False, "MQCMD_INQUIRE_Q"),
        (True, "MQCMD_INQUIRE_Q_NAMES"),
    ],
    ids=["direct_method", "via_names_method"],
)
def test_discover_queues_disconnects_on_exception(
    instance, auto_discover_queues_via_names, side_effect_attr, get_check
):
    instance['auto_discover_queues_via_names'] = auto_discover_queues_via_names
    instance['auto_discover_queues'] = True

    check = get_check(instance)
    collector = check.queue_metric_collector
    queue_manager = Mock()
    pcf_mock = Mock()
    with patch('datadog_checks.ibm_mq.collectors.queue_metric_collector.pymqi.PCFExecute', return_value=pcf_mock):
        error = pymqi.MQMIError(2, 9999)
        setattr(pcf_mock, side_effect_attr, Mock(side_effect=error))
        collector.discover_queues(queue_manager)
        assert pcf_mock.disconnect.called


@pytest.mark.parametrize(
    "auto_discover_queues_via_names, patch_method, return_value",
    [
        (False, "MQCMD_INQUIRE_Q", []),
        (True, "MQCMD_INQUIRE_Q_NAMES", [{}]),
    ],
    ids=["direct_method", "via_names_method"],
)
def test_discover_queues_warns_when_no_queues_found(
    instance, auto_discover_queues_via_names, patch_method, return_value, caplog, get_check
):
    instance['auto_discover_queues_via_names'] = auto_discover_queues_via_names
    instance['auto_discover_queues'] = True
    instance['queues'] = []

    check = get_check(instance)
    collector = check.queue_metric_collector

    queue_manager = Mock()
    with patch('datadog_checks.ibm_mq.collectors.queue_metric_collector.pymqi.PCFExecute') as PCFExecute:
        getattr(PCFExecute.return_value, patch_method).return_value = return_value
        with caplog.at_level(logging.WARNING):
            result = collector.discover_queues(queue_manager)
        assert any(
            "No matching queue of type MQQT_LOCAL or MQQT_REMOTE for pattern" in record.message
            for record in caplog.records
            if record.levelname == "WARNING"
        )
        assert result == set()


@pytest.mark.parametrize(
    "auto_discover_queues_via_names, expected_method, not_expected_method, expected_queue",
    [
        (False, "_discover_queues", "_discover_queues_via_names", "queue1"),
        (True, "_discover_queues_via_names", "_discover_queues", "queue2"),
    ],
    ids=["direct_method", "via_names_method"],
)
def test_discover_queues_uses_correct_method_based_on_config(
    instance, auto_discover_queues_via_names, expected_method, not_expected_method, expected_queue, get_check
):
    instance['auto_discover_queues_via_names'] = auto_discover_queues_via_names
    instance['auto_discover_queues'] = True
    instance['queues'] = []

    check = get_check(instance)
    collector = check.queue_metric_collector
    queue_manager = Mock()

    collector._discover_queues = Mock(return_value=['queue1'])
    collector._discover_queues_via_names = Mock(return_value=['queue2'])

    result = collector.discover_queues(queue_manager)
    getattr(collector, expected_method).assert_called()
    getattr(collector, not_expected_method).assert_not_called()
    assert expected_queue in result


def test_discover_queues_resilience_with_broken_queue(instance, aggregator, get_check):
    instance['auto_discover_queues'] = True
    instance['queues'] = []
    check = get_check(instance)
    collector = check.queue_metric_collector

    queue_manager = Mock()
    good_queues = ['GOOD.QUEUE.1', 'GOOD.QUEUE.2']
    broken_queue = 'BROKEN.QUEUE.1'
    all_queues = good_queues + [broken_queue]

    collector.config.auto_discover_queues_via_names = False

    with patch('datadog_checks.ibm_mq.collectors.queue_metric_collector.pymqi.PCFExecute') as PCFExecute:
        pcf_mock = PCFExecute.return_value
        pcf_mock.MQCMD_INQUIRE_Q.side_effect = pymqi.MQMIError(2, 2035)  # Common MQRC_NOT_AUTHORIZED

        result_direct = collector.discover_queues(queue_manager)
        assert result_direct == set()

    collector.config.auto_discover_queues_via_names = True

    with patch('datadog_checks.ibm_mq.collectors.queue_metric_collector.pymqi.PCFExecute') as PCFExecute:
        pcf_mock = PCFExecute.return_value

        pcf_mock.MQCMD_INQUIRE_Q_NAMES.return_value = [
            {pymqi.CMQCFC.MQCACF_Q_NAMES: [queue.encode() for queue in all_queues]}
        ]

        def mock_inquire_q(args):
            queue_name = args[pymqi.CMQC.MQCA_Q_NAME].decode()
            if queue_name == broken_queue:
                raise pymqi.MQMIError(2, 2035)  # Common MQRC_NOT_AUTHORIZED
            else:
                return [{pymqi.CMQC.MQCA_Q_NAME: queue_name.encode()}]

        pcf_mock.MQCMD_INQUIRE_Q.side_effect = mock_inquire_q

        result_via_names = collector.discover_queues(queue_manager)
        assert result_via_names == set(good_queues)
        assert broken_queue not in result_via_names
        aggregator.assert_metric(
            'ibm_mq.queue.discovery.error',
            1,
            tags=['queue:BROKEN.QUEUE.1', 'ibm_error_code:2035', 'ibm_error:MQRC_NOT_AUTHORIZED'],
        )


@pytest.mark.parametrize(
    'add_description_tags,normalize_description_tags,queue_desc,expected_desc_tag',
    [
        (False, True, b'Test Description', None),  # Disabled
        (True, True, b'Test Description', 'queue_desc:test_description'),  # Enabled + normalized
        (True, False, b'Test Description', 'queue_desc:Test Description'),  # Enabled + raw
        (True, True, b'', None),  # Empty description
        (True, False, b'Caf\xc6', 'queue_desc:Caf\ufffd'),  # Non-UTF-8 bytes — must not crash
    ],
)
def test_queue_description_tags(
    instance, add_description_tags, normalize_description_tags, queue_desc, expected_desc_tag, get_check
):
    """Test queue description tags with different config options."""
    instance['add_description_tags'] = add_description_tags
    instance['normalize_description_tags'] = normalize_description_tags

    check = get_check(instance)
    collector = check.queue_metric_collector

    queue_manager = Mock()
    queue_name = 'TEST.QUEUE'

    with patch('datadog_checks.ibm_mq.collectors.queue_metric_collector.pymqi.PCFExecute') as PCFExecute:
        pcf_mock = PCFExecute.return_value

        queue_info = {
            pymqi.CMQC.MQCA_Q_NAME: queue_name.encode(),
            pymqi.CMQC.MQIA_USAGE: pymqi.CMQC.MQUS_NORMAL,
            pymqi.CMQC.MQIA_CURRENT_Q_DEPTH: 10,
            pymqi.CMQC.MQIA_MAX_Q_DEPTH: 100,
        }
        if queue_desc:
            queue_info[pymqi.CMQC.MQCA_Q_DESC] = queue_desc

        pcf_mock.MQCMD_INQUIRE_Q.return_value = [queue_info]
        collector.send_metric = Mock()

        base_tags = collector.config.tags + [f'queue:{queue_name}']
        enriched_tags = collector.queue_stats(queue_manager, queue_name, base_tags)

        if expected_desc_tag:
            assert expected_desc_tag in enriched_tags
        else:
            desc_tags = [t for t in enriched_tags if t.startswith('queue_desc:')]
            assert len(desc_tags) == 0


def _raw_queue_statistics_message(queue_names):
    blocks = []
    for name in queue_names:
        blocks.append(
            {
                pymqi.CMQC.MQCA_Q_NAME: name.encode('utf-8'),
                pymqi.CMQC.MQIA_Q_TYPE: pymqi.CMQC.MQQT_LOCAL,
                pymqi.CMQC.MQIA_DEFINITION_TYPE: pymqi.CMQC.MQQDT_PREDEFINED,
            }
        )
    return {
        pymqi.CMQCFC.MQCAMO_START_DATE: b'2020-01-01',
        pymqi.CMQCFC.MQCAMO_START_TIME: b'12.00.00',
        pymqi.CMQCFC.MQGACF_Q_STATISTICS_DATA: blocks,
    }


@pytest.mark.parametrize(
    'filter_on, filtered_names, expected_queue_names',
    [
        (True, {'QUEUE.A'}, ['QUEUE.A']),
        (True, {'QUEUE.B'}, ['QUEUE.B']),
        (True, set(), []),
        (False, {'QUEUE.A'}, ['QUEUE.A', 'QUEUE.B']),
        (True, None, ['QUEUE.A', 'QUEUE.B']),
    ],
)
def test_queue_stats_respects_filter_flag_and_names(filter_on, filtered_names, expected_queue_names):
    raw = _raw_queue_statistics_message(['QUEUE.A', 'QUEUE.B'])
    stats = QueueStats(raw, filtered_names, timezone=tz.UTC, filter_queue_statistics_metrics=filter_on)
    assert [q.name for q in stats.queues] == expected_queue_names


def test_collect_queue_metrics_issues_bulk_wildcard_commands_not_per_queue(instance):
    """AGENT-16599 issue 2: per-queue PCF collection is collapsed to one wildcard command per
    queue manager. This guards against a regression to O(N) commands — the class of cost defect
    that went unnoticed for years because nothing in the suite counted PCF commands."""
    instance['collect_reset_queue_metrics'] = True
    config = IBMMQConfig(instance, {})
    collector = QueueMetricCollector(config, Mock(), Mock(), Mock(), Mock(), Mock())

    queues = {'APP.QUEUE.{}'.format(i) for i in range(50)}
    collector.discover_queues = Mock(return_value=queues)
    collector.queue_manager_stats = Mock()

    def bulk_rows(*args, **kwargs):
        # One response row per queue, keyed by MQCA_Q_NAME (as a real wildcard PCF reply is).
        return [{pymqi.CMQC.MQCA_Q_NAME: q.encode()} for q in queues]

    pcf = Mock()
    pcf.MQCMD_INQUIRE_Q.side_effect = bulk_rows
    pcf.MQCMD_INQUIRE_Q_STATUS.side_effect = bulk_rows
    pcf.MQCMD_RESET_Q_STATS.side_effect = bulk_rows

    with patch('datadog_checks.ibm_mq.collectors.queue_metric_collector.pymqi.PCFExecute', return_value=pcf):
        collector.collect_queue_metrics(Mock())

    # One command of each type per queue manager, regardless of the 50 queues — not one per queue.
    assert pcf.MQCMD_INQUIRE_Q.call_count == 1
    assert pcf.MQCMD_INQUIRE_Q_STATUS.call_count == 1
    assert pcf.MQCMD_RESET_Q_STATS.call_count == 1
    # Each is a generic (wildcard) query.
    assert pcf.MQCMD_INQUIRE_Q.call_args[0][0][pymqi.CMQC.MQCA_Q_NAME] == b'*'
    assert pcf.MQCMD_INQUIRE_Q_STATUS.call_args[0][0][pymqi.CMQC.MQCA_Q_NAME] == b'*'


def test_collect_queue_metrics_falls_back_per_queue_when_bulk_unavailable(instance):
    """If a bulk wildcard command yields no data (e.g. the queue manager errors), each queue must
    still be collected via a per-queue PCF call, preserving behaviour and per-queue error isolation."""
    instance['collect_reset_queue_metrics'] = False
    config = IBMMQConfig(instance, {})
    collector = QueueMetricCollector(config, Mock(), Mock(), Mock(), Mock(), Mock())

    queues = {'APP.QUEUE.0', 'APP.QUEUE.1'}
    collector.discover_queues = Mock(return_value=queues)
    collector.queue_manager_stats = Mock()

    # Bulk calls return nothing (empty) -> maps are empty -> per-queue fallback for every queue.
    pcf = Mock()
    pcf.MQCMD_INQUIRE_Q.return_value = []
    pcf.MQCMD_INQUIRE_Q_STATUS.return_value = []

    with patch('datadog_checks.ibm_mq.collectors.queue_metric_collector.pymqi.PCFExecute', return_value=pcf):
        collector.collect_queue_metrics(Mock())

    # 1 bulk INQUIRE_Q + 1 bulk INQUIRE_Q_STATUS, then a per-queue call of each for the 2 queues.
    assert pcf.MQCMD_INQUIRE_Q.call_count == 1 + len(queues)
    assert pcf.MQCMD_INQUIRE_Q_STATUS.call_count == 1 + len(queues)
    # The fallback calls target specific queues, not the wildcard.
    fallback_names = {call[0][0][pymqi.CMQC.MQCA_Q_NAME] for call in pcf.MQCMD_INQUIRE_Q_STATUS.call_args_list}
    assert fallback_names == {b'*'} | {q.encode() for q in queues}
