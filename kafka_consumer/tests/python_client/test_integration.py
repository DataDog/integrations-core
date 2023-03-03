# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.dev.utils import get_metadata_metrics

from ..common import KAFKA_CONNECT_STR, assert_check_kafka

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


def test_consumer_config_error(caplog, check, dd_run_check):
    instance = {'kafka_connect_str': KAFKA_CONNECT_STR, 'tags': ['optional:tag1']}
    kafka_consumer_check = check(instance)

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
def test_monitor_broker_highwatermarks(dd_run_check, check, aggregator, is_enabled, metric_count, topic_tags):
    instance = {
        'kafka_connect_str': KAFKA_CONNECT_STR,
        'consumer_groups': {'my_consumer': {'marvel': None}},
        'monitor_all_broker_highwatermarks': is_enabled,
    }
    dd_run_check(check(instance))

    # After refactor and library migration, write unit tests to assert expected metric values
    aggregator.assert_metric('kafka.broker_offset', count=metric_count)

    for tag in topic_tags:
        aggregator.assert_metric_has_tag('kafka.broker_offset', tag, count=2)

    aggregator.assert_metric_has_tag_prefix('kafka.broker_offset', 'partition', count=metric_count)
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
