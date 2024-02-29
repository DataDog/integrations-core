# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json
import logging
from collections import defaultdict
from contextlib import nullcontext as does_not_raise

import mock
import pytest

from datadog_checks.dev.utils import get_metadata_metrics

from . import common
from .common import assert_check_kafka, metrics

pytestmark = [pytest.mark.integration, pytest.mark.usefixtures('dd_environment')]


def mocked_read_persistent_cache(cache_key):
    cached_offsets = defaultdict(dict)
    cached_offsets["marvel_0"][25] = 150
    cached_offsets["marvel_0"][40] = 200
    cached_offsets["marvel_1"][25] = 150
    cached_offsets["marvel_1"][40] = 200
    cached_offsets["dc_0"][25] = 150
    cached_offsets["dc_0"][40] = 200
    cached_offsets["dc_1"][25] = 150
    cached_offsets["dc_1"][40] = 200
    return json.dumps(cached_offsets)


def mocked_time():
    return 400


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


def test_consumer_config_error(check, dd_run_check, kafka_instance):
    del kafka_instance['consumer_groups']
    kafka_consumer_check = check(kafka_instance)

    with pytest.raises(Exception, match="monitor_unlisted_consumer_groups is False"):
        dd_run_check(kafka_consumer_check, extract_message=True)


def test_invalid_config_raises_exception(check, dd_run_check, kafka_instance):
    kafka_instance['kafka_connect_str'] = "localhost:9091"
    kafka_consumer_check = check(kafka_instance)

    with pytest.raises(
        Exception, match="Unable to connect to the AdminClient. This is likely due to an error in the configuration."
    ):
        dd_run_check(kafka_consumer_check, extract_message=True)


def test_no_topics(aggregator, check, kafka_instance, dd_run_check):
    kafka_instance['consumer_groups'] = {'my_consumer': {}}
    dd_run_check(check(kafka_instance))

    assert_check_kafka(aggregator, {'my_consumer': {'marvel': [0]}})


def test_no_partitions(aggregator, check, kafka_instance, dd_run_check):
    kafka_instance['consumer_groups'] = {'my_consumer': {'marvel': []}}
    dd_run_check(check(kafka_instance))

    assert_check_kafka(aggregator, {'my_consumer': {'marvel': [0]}})


@pytest.mark.parametrize(
    'is_enabled, broker_offset_metric_count, topic_tags',
    [
        pytest.param(True, 6, ['topic:marvel', 'topic:dc'], id="Monitor all broker highwatermarks Enabled"),
        pytest.param(False, 2, ['topic:marvel'], id="Monitor all broker highwatermarks Disabled"),
    ],
)
def test_monitor_broker_highwatermarks(
    dd_run_check, check, aggregator, kafka_instance, is_enabled, broker_offset_metric_count, topic_tags
):
    kafka_instance['consumer_groups'] = {'my_consumer': {'marvel': None}}
    kafka_instance['monitor_all_broker_highwatermarks'] = is_enabled
    dd_run_check(check(kafka_instance))
    cluster_id = common.get_cluster_id()

    # After refactor and library migration, write unit tests to assert expected metric values
    aggregator.assert_metric('kafka.broker_offset', count=broker_offset_metric_count)

    for tag in topic_tags:
        for partition in range(2):
            aggregator.assert_metric(
                'kafka.broker_offset',
                metric_type=aggregator.GAUGE,
                tags=[tag, f"partition:{partition}", f"kafka_cluster_id:{cluster_id}", "optional:tag1"],
                count=1,
            )

    aggregator.assert_metrics_using_metadata(get_metadata_metrics())


@pytest.mark.parametrize(
    'override, expected_exception, metric_count',
    [
        pytest.param(
            {'kafka_connect_str': 12},
            pytest.raises(
                Exception, match='ConfigurationError: `kafka_connect_str` should be string or list of strings'
            ),
            0,
            id="Invalid Non-string kafka_connect_str",
        ),
        pytest.param(
            {'consumer_groups': {}},
            pytest.raises(
                Exception,
                match='ConfigurationError: Cannot fetch consumer offsets because no consumer_groups are specified and '
                'monitor_unlisted_consumer_groups is False',
            ),
            0,
            id="Empty consumer_groups",
        ),
        pytest.param(
            {'kafka_connect_str': ['localhost:9092', 'localhost:9093'], 'monitor_unlisted_consumer_groups': True},
            does_not_raise(),
            4,
            id="Valid list kafka_connect_str",
        ),
        pytest.param(
            {'monitor_unlisted_consumer_groups': True},
            does_not_raise(),
            4,
            id="Valid str kafka_connect_str",
        ),
        pytest.param(
            {'consumer_groups': {}, 'monitor_unlisted_consumer_groups': True},
            does_not_raise(),
            4,
            id="Empty consumer_groups and monitor_unlisted_consumer_groups true",
        ),
        pytest.param(
            {'consumer_groups': {'my_consumer': None}},
            does_not_raise(),
            4,
            id="One consumer group, all topics and partitions",
        ),
        pytest.param(
            {'consumer_groups': {'my_consumer': {'marvel': None}}},
            does_not_raise(),
            2,
            id="One consumer group, one topic, all partitions",
        ),
        pytest.param(
            {'consumer_groups': {'nonsense': {'marvel': None}}},
            does_not_raise(),
            0,
            id="Nonexistent consumer group, resulting in no metrics",
        ),
        pytest.param(
            {'consumer_groups': {'my_consumer': {'marvel': [1]}}},
            does_not_raise(),
            1,
            id="One consumer group, one topic, one partition",
        ),
        pytest.param(
            {'consumer_groups': {'my_consumer': {'unconsumed_topic': None}}},
            does_not_raise(),
            0,
            id="One consumer group and one unconsumed topic for that consumer",
        ),
    ],
)
def test_config(dd_run_check, check, kafka_instance, override, aggregator, expected_exception, metric_count):
    kafka_instance.update(override)
    with expected_exception:
        dd_run_check(check(kafka_instance))

    for m in metrics:
        aggregator.assert_metric(m, count=metric_count)

    aggregator.assert_metrics_using_metadata(get_metadata_metrics())


@mock.patch('datadog_checks.kafka_consumer.kafka_consumer.time', mocked_time)
@pytest.mark.parametrize(
    'consumer_groups_regex_config, broker_offset_count, consumer_offset_count, consumer_lag_count, \n'
    'consumer_lag_seconds_count, expected_warning',
    [
        pytest.param(
            {
                'consumer_groups': {},
                'consumer_groups_regex': {'.+': {}},
            },
            4,
            4,
            4,
            0,
            '',
            id="All consumer offsets, empty topics",
        ),
        pytest.param(
            {
                'consumer_groups': {},
                'consumer_groups_regex': {'.+': {}},
                'data_streams_enabled': 'true',
            },
            4,
            4,
            4,
            4,
            '',
            id="All consumer offsets, empty topics with data streams enabled",
        ),
        pytest.param(
            {
                'consumer_groups': {},
                'consumer_groups_regex': {'.+': {'.+': []}},
            },
            4,
            4,
            4,
            0,
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
            0,
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
            0,
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
            0,
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
            0,
            'Using both monitor_unlisted_consumer_groups and consumer_groups or consumer_groups_regex',
            id="No specified consumer groups, but monitor_unlisted_consumer_groups true",
        ),
        pytest.param(
            {
                'consumer_groups': {'my_consumer': {'dc': []}},
                'consumer_groups_regex': {},
                'monitor_unlisted_consumer_groups': True,
            },
            4,
            4,
            4,
            0,
            'Using both monitor_unlisted_consumer_groups and consumer_groups or consumer_groups_regex',
            id="Specified topics on consumer_groups, but monitor_unlisted_consumer_groups true",
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
            0,
            'Using both monitor_unlisted_consumer_groups and consumer_groups or consumer_groups_regex',
            id="Specified topics on consumer_groups_regex, but monitor_unlisted_consumer_groups true",
        ),
        pytest.param(
            {
                'consumer_groups': {},
                'consumer_groups_regex': {'my_consume.+': {'dc': []}},
                'monitor_unlisted_consumer_groups': False,
            },
            2,
            2,
            2,
            0,
            '',
            id="Specified topic, monitor_unlisted_consumer_groups false",
        ),
        pytest.param(
            {
                'consumer_groups': {},
                'consumer_groups_regex': {'foo': {'bar': []}, 'my_consume.+': {'dc': []}},
                'monitor_unlisted_consumer_groups': False,
            },
            2,
            2,
            2,
            0,
            '',
            id="Specified topic with an extra nonmatching consumer group regex, monitor_unlisted_consumer_groups false",
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
            0,
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
            0,
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
            0,
            '',
            id="Using the same consumer_groups and consumer_groups_regex values",
        ),
        pytest.param(
            {
                'consumer_groups': {},
                'consumer_groups_regex': {'my_consumer': {'unconsumed_*': []}},
            },
            0,
            0,
            0,
            0,
            '',
            id="Specified consumer with unconsumed topic regex for that consumer",
        ),
    ],
)
def test_regex_consumer_groups(
    consumer_groups_regex_config,
    broker_offset_count,
    consumer_offset_count,
    consumer_lag_count,
    consumer_lag_seconds_count,
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
    check = check(kafka_instance)
    with mock.patch('datadog_checks.base.AgentCheck.read_persistent_cache') as mock_load_broker_timestamps:
        mock_load_broker_timestamps.return_value = mocked_read_persistent_cache("")
        dd_run_check(check)

    # Then
    aggregator.assert_metric("kafka.broker_offset", count=broker_offset_count)
    aggregator.assert_metric("kafka.consumer_offset", count=consumer_offset_count)
    aggregator.assert_metric("kafka.consumer_lag", count=consumer_lag_count)
    aggregator.assert_metric("kafka.estimated_consumer_lag", count=consumer_lag_seconds_count)

    assert expected_warning in caplog.text
