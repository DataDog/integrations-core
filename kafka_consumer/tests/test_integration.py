# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import logging
from contextlib import nullcontext as does_not_raise

import pytest
from tests.common import assert_check_kafka, metrics

from datadog_checks.dev.utils import get_metadata_metrics

pytestmark = [pytest.mark.integration, pytest.mark.usefixtures('dd_environment')]


def test_check_kafka(aggregator, check, kafka_instance, dd_run_check):
    """
    Testing Kafka_consumer check.
    """
    dd_run_check(check(kafka_instance))
    assert_check_kafka(aggregator, kafka_instance['consumer_groups'])


def test_can_send_event(aggregator, check, kafka_instance, dd_run_check):
    """
    Testing Kafka_consumer check.
    """
    kafka_consumer_check = check(kafka_instance)
    kafka_consumer_check.send_event("test", "test", [], "test", "test")
    aggregator.assert_event("test", exact_match=False, count=1)


def test_check_kafka_metrics_limit(aggregator, check, kafka_instance, dd_run_check):
    """
    Testing Kafka_consumer check.
    """
    dd_run_check(check(kafka_instance, {'max_partition_contexts': 1}))

    assert len(aggregator._metrics) == 1


def test_consumer_config_error(caplog, check, dd_run_check, kafka_instance):
    del kafka_instance['consumer_groups']
    kafka_consumer_check = check(kafka_instance)

    dd_run_check(kafka_consumer_check, extract_message=True)
    assert 'monitor_unlisted_consumer_groups is False' in caplog.text


def test_no_topics(aggregator, check, kafka_instance, dd_run_check):
    kafka_instance['consumer_groups'] = {'my_consumer': {}}
    dd_run_check(check(kafka_instance))

    assert_check_kafka(aggregator, {'my_consumer': {'marvel': [0]}})


def test_no_partitions(aggregator, check, kafka_instance, dd_run_check):
    kafka_instance['consumer_groups'] = {'my_consumer': {'marvel': []}}
    dd_run_check(check(kafka_instance))

    assert_check_kafka(aggregator, {'my_consumer': {'marvel': [0]}})


@pytest.mark.parametrize(
    'is_enabled, metric_count, topic_tags',
    [
        pytest.param(True, 4, ['topic:marvel', 'topic:dc'], id="Enabled"),
        pytest.param(False, 2, ['topic:marvel'], id="Disabled"),
    ],
)
def test_monitor_broker_highwatermarks(
    dd_run_check, check, aggregator, kafka_instance, is_enabled, metric_count, topic_tags
):
    kafka_instance['consumer_groups'] = {'my_consumer': {'marvel': None}}
    kafka_instance['monitor_all_broker_highwatermarks'] = is_enabled
    dd_run_check(check(kafka_instance))

    # After refactor and library migration, write unit tests to assert expected metric values
    aggregator.assert_metric('kafka.broker_offset', count=metric_count)

    for tag in topic_tags:
        for partition in range(2):
            aggregator.assert_metric(
                'kafka.broker_offset',
                metric_type=aggregator.GAUGE,
                tags=[tag, f"partition:{partition}", "optional:tag1"],
                count=1,
            )

    aggregator.assert_metrics_using_metadata(get_metadata_metrics())


@pytest.mark.parametrize(
    'override, expected_exception, exception_msg, metric_count',
    [
        pytest.param(
            {'kafka_connect_str': 12},
            pytest.raises(
                Exception, match='ConfigurationError: `kafka_connect_str` should be string or list of strings'
            ),
            '',
            0,
            id="Invalid Non-string kafka_connect_str",
        ),
        pytest.param(
            {'consumer_groups': {}},
            does_not_raise(),
            'ConfigurationError: Cannot fetch consumer offsets because no consumer_groups are specified and '
            'monitor_unlisted_consumer_groups is False',
            0,
            id="Empty consumer_groups",
        ),
        pytest.param(
            {'kafka_connect_str': None},
            pytest.raises(Exception, match='kafka_connect_str\n  none is not an allowed value'),
            '',
            0,
            id="Invalid Nonetype kafka_connect_str",
        ),
        pytest.param(
            {'kafka_connect_str': ['localhost:9092', 'localhost:9093'], 'monitor_unlisted_consumer_groups': True},
            does_not_raise(),
            '',
            4,
            id="Valid list kafka_connect_str",
        ),
        pytest.param(
            {'monitor_unlisted_consumer_groups': True},
            does_not_raise(),
            '',
            4,
            id="Valid str kafka_connect_str",
        ),
        pytest.param(
            {'consumer_groups': {}, 'monitor_unlisted_consumer_groups': True},
            does_not_raise(),
            '',
            4,
            id="Empty consumer_groups and monitor_unlisted_consumer_groups true",
        ),
        pytest.param(
            {'consumer_groups': {'my_consumer': None}},
            does_not_raise(),
            '',
            4,
            id="One consumer group, all topics and partitions",
        ),
        pytest.param(
            {'consumer_groups': {'my_consumer': {'marvel': None}}},
            does_not_raise(),
            '',
            2,
            id="One consumer group, one topic, all partitions",
        ),
        pytest.param(
            {'consumer_groups': {'my_consumer': {'marvel': [1]}}},
            does_not_raise(),
            '',
            1,
            id="One consumer group, one topic, one partition",
        ),
    ],
)
def test_config(
    dd_run_check, check, kafka_instance, override, aggregator, expected_exception, exception_msg, metric_count, caplog
):
    caplog.set_level(logging.DEBUG)
    kafka_instance.update(override)
    with expected_exception:
        dd_run_check(check(kafka_instance))

    for m in metrics:
        aggregator.assert_metric(m, count=metric_count)

    assert exception_msg in caplog.text
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())


@pytest.mark.parametrize(
    'consumer_groups_config, broker_offset_count, consumer_offset_count, consumer_lag_count, expected_warning',
    [
        pytest.param(
            {
                'consumer_groups': {},
                'consumer_groups_regex': {'.+': {}},
            },
            4,
            4,
            4,
            '',
            id="All consumer offsets, empty topics",
        ),
        pytest.param(
            {
                'consumer_groups': {},
                'consumer_groups_regex': {'.+': {'.+': []}},
            },
            4,
            4,
            4,
            '',
            id="All consumer offsets, all topics",
        ),
        pytest.param(
            {
                'consumer_groups': {},
                'consumer_groups_regex': {'.+': {'!.+': []}},
            },
            0,
            0,
            0,
            '',
            id="All consumer offsets, no topics",
        ),
        pytest.param(
            {
                'consumer_groups': {},
                'consumer_groups_regex': {'!.+': {'!.+': []}},
            },
            0,
            0,
            0,
            '',
            id="No consumer offsets, No topics",
        ),
        pytest.param(
            {
                'consumer_groups': {},
                'consumer_groups_regex': {'!.+': {}},
            },
            0,
            0,
            0,
            '',
            id="No consumer offsets, empty topics",
        ),
        pytest.param(
            {
                'consumer_groups': {},
                'consumer_groups_regex': {'my_consumer': {'dc': [0]}},
            },
            1,
            1,
            1,
            '',
            id="Specified consumer group, topic, and partition",
        ),
        pytest.param(
            {
                'consumer_groups': {},
                'consumer_groups_regex': {'my_consumer': {'dc': []}},
            },
            2,
            2,
            2,
            '',
            id="Specified consumer group, topic",
        ),
        pytest.param(
            {
                'consumer_groups': {},
                'consumer_groups_regex': {'m.+': {}, '.+': {}},
            },
            4,
            4,
            4,
            '',
            id="Multiple consumer_groups specified",
        ),
        pytest.param(
            {
                'consumer_groups': {},
                'consumer_groups_regex': {'!.+': {}},
                'monitor_unlisted_consumer_groups': True,
            },
            4,
            4,
            4,
            'Using both monitor_unlisted_consumer_groups and consumer_groups or consumer_groups_regex',
            id="No specified consumer groups, but monitor_unlisted_consumer_groups true",
        ),
        pytest.param(
            {
                'consumer_groups': {},
                'consumer_groups_regex': {'my_consumer': {'dc': []}},
                'monitor_unlisted_consumer_groups': True,
            },
            4,
            4,
            4,
            'Using both monitor_unlisted_consumer_groups and consumer_groups or consumer_groups_regex',
            id="Specified topics, but monitor_unlisted_consumer_groups true",
        ),
        pytest.param(
            {
                'consumer_groups': {},
                'consumer_groups_regex': {'my_consume*': {'dc': []}},
                'monitor_unlisted_consumer_groups': False,
            },
            2,
            2,
            2,
            '',
            id="Specified topic, monitor_unlisted_consumer_groups false",
        ),
        pytest.param(
            {
                'consumer_groups': {'my_consumer': {'marvel': []}},
                'consumer_groups_regex': {'my_consumer': {'dc': []}},
                'monitor_unlisted_consumer_groups': False,
            },
            4,
            4,
            4,
            'Using consumer_groups and consumer_groups_regex',
            id="Mixing both consumer_groups and consumer_groups_regex",
        ),
        pytest.param(
            {
                'consumer_groups': {'my_consumer': {'marvel': []}},
                'consumer_groups_regex': {'my_consumer': {'dc': []}},
                'monitor_unlisted_consumer_groups': True,
            },
            4,
            4,
            4,
            'Using both monitor_unlisted_consumer_groups and consumer_groups or consumer_groups_regex',
            id="Mixing consumer_groups, consumer_groups_regex, and monitor_unlisted_consumer_groups",
        ),
        pytest.param(
            {
                'consumer_groups': {'my_consumer': {'dc': []}},
                'consumer_groups_regex': {'my_consumer': {'dc': []}},
            },
            2,
            2,
            2,
            '',
            id="Using the same consumer_groups and consumer_groups_regex values",
        ),
    ],
)
@pytest.mark.skipif(LEGACY_CLIENT, reason='not implemented with python-kafka')
def test_regex_consumer_groups(
    consumer_groups_regex_config,
    broker_offset_count,
    consumer_offset_count,
    consumer_lag_count,
    expected_warning,
    caplog,
    kafka_instance,
    dd_run_check,
    aggregator,
    check,
):
    caplog.set_level(logging.WARN)
    # Given
    kafka_instance.update(consumer_groups_regex_config)

    # When
    dd_run_check(check(kafka_instance))

    # Then
    aggregator.assert_metric("kafka.broker_offset", count=broker_offset_count)
    aggregator.assert_metric("kafka.consumer_offset", count=consumer_offset_count)
    aggregator.assert_metric("kafka.consumer_lag", count=consumer_lag_count)

    assert expected_warning in caplog.text
