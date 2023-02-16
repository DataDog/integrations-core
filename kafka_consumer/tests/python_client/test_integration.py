# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import pytest

from datadog_checks.kafka_consumer import KafkaCheck

from ..common import KAFKA_CONNECT_STR, assert_check_kafka

pytestmark = [pytest.mark.integration]


@pytest.mark.usefixtures('dd_environment')
def test_check_kafka(aggregator, kafka_instance, dd_run_check):
    """
    Testing Kafka_consumer check.
    """
    kafka_consumer_check = KafkaCheck('kafka_consumer', {}, [kafka_instance])
    dd_run_check(kafka_consumer_check)
    assert_check_kafka(aggregator, kafka_instance['consumer_groups'])


@pytest.mark.usefixtures('dd_environment')
def test_can_send_event(aggregator, kafka_instance, dd_run_check):
    """
    Testing Kafka_consumer check.
    """
    kafka_consumer_check = KafkaCheck('kafka_consumer', {}, [kafka_instance])
    kafka_consumer_check.send_event("test", "test", [], "test", "test")
    aggregator.assert_event("test", exact_match=False, count=1)


@pytest.mark.usefixtures('dd_environment')
def test_check_kafka_metrics_limit(aggregator, kafka_instance, dd_run_check):
    """
    Testing Kafka_consumer check.
    """
    kafka_consumer_check = KafkaCheck('kafka_consumer', {'max_partition_contexts': 1}, [kafka_instance])
    dd_run_check(kafka_consumer_check)

    assert len(aggregator._metrics) == 1


@pytest.mark.usefixtures('dd_environment')
def test_consumer_config_error(caplog, dd_run_check):
    instance = {'kafka_connect_str': KAFKA_CONNECT_STR, 'tags': ['optional:tag1']}
    kafka_consumer_check = KafkaCheck('kafka_consumer', {}, [instance])

    dd_run_check(kafka_consumer_check, extract_message=True)
    assert 'monitor_unlisted_consumer_groups is False' in caplog.text


@pytest.mark.usefixtures('dd_environment')
def test_no_topics(aggregator, kafka_instance, dd_run_check):
    kafka_instance['consumer_groups'] = {'my_consumer': {}}
    kafka_consumer_check = KafkaCheck('kafka_consumer', {}, [kafka_instance])
    dd_run_check(kafka_consumer_check)

    assert_check_kafka(aggregator, {'my_consumer': {'marvel': [0]}})


@pytest.mark.usefixtures('dd_environment')
def test_no_partitions(aggregator, kafka_instance, dd_run_check):
    kafka_instance['consumer_groups'] = {'my_consumer': {'marvel': []}}
    kafka_consumer_check = KafkaCheck('kafka_consumer', {}, [kafka_instance])
    dd_run_check(kafka_consumer_check)

    assert_check_kafka(aggregator, {'my_consumer': {'marvel': [0]}})


@pytest.mark.usefixtures('dd_environment')
def test_version_metadata(datadog_agent, kafka_instance, dd_run_check):
    kafka_consumer_check = KafkaCheck('kafka_consumer', {}, [kafka_instance])
    kafka_consumer_check.check_id = 'test:123'

    kafka_client = kafka_consumer_check.client.create_kafka_admin_client()
    version_data = [str(part) for part in kafka_client._client.check_version()]
    kafka_client.close()
    version_parts = {f'version.{name}': part for name, part in zip(('major', 'minor', 'patch'), version_data)}
    version_parts['version.scheme'] = 'semver'
    version_parts['version.raw'] = '.'.join(version_data)

    dd_run_check(kafka_consumer_check)
    datadog_agent.assert_metadata('test:123', version_parts)


@pytest.mark.parametrize(
    'is_enabled, metric_count, topic_tags',
    [
        pytest.param(True, 4, ['topic:marvel', 'topic:dc'], id="Enabled"),
        pytest.param(False, 2, ['topic:marvel'], id="Disabled"),
    ],
)
@pytest.mark.usefixtures('dd_environment')
def test_monitor_broker_highwatermarks(dd_run_check, aggregator, is_enabled, metric_count, topic_tags):
    instance = {
        'kafka_connect_str': KAFKA_CONNECT_STR,
        'consumer_groups': {'my_consumer': {'marvel': None}},
        'monitor_all_broker_highwatermarks': is_enabled,
    }
    check = KafkaCheck('kafka_consumer', {}, [instance])
    dd_run_check(check)

    # After refactor and library migration, write unit tests to assert expected metric values
    aggregator.assert_metric('kafka.broker_offset', count=metric_count)
    for tag in topic_tags:
        aggregator.assert_metric_has_tag('kafka.broker_offset', tag, count=2)

    aggregator.assert_metric_has_tag_prefix('kafka.broker_offset', 'partition', count=metric_count)
