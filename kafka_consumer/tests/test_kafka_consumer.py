# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import os

import pytest

from datadog_checks.kafka_consumer import KafkaCheck

from .common import KAFKA_CONNECT_STR, is_legacy_check, is_supported

pytestmark = pytest.mark.skipif(
    not is_supported('kafka'), reason='kafka consumer offsets not supported in current environment'
)


BROKER_METRICS = ['kafka.broker_offset']

CONSUMER_METRICS = ['kafka.consumer_offset', 'kafka.consumer_lag']


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_check_kafka(aggregator, kafka_instance):
    """
    Testing Kafka_consumer check.
    """
    kafka_consumer_check = KafkaCheck('kafka_consumer', {}, [kafka_instance])
    kafka_consumer_check.check(kafka_instance)

    assert_check_kafka(aggregator, kafka_instance['consumer_groups'])


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_check_kafka_metrics_limit(aggregator, kafka_instance):
    """
    Testing Kafka_consumer check.
    """
    kafka_consumer_check = KafkaCheck('kafka_consumer', {'max_partition_contexts': 1}, [kafka_instance])
    kafka_consumer_check.check(kafka_instance)

    assert len(aggregator._metrics) == 1


@pytest.mark.e2e
def test_e2e(dd_agent_check, kafka_instance):
    aggregator = dd_agent_check(kafka_instance)

    assert_check_kafka(aggregator, kafka_instance['consumer_groups'])


def assert_check_kafka(aggregator, consumer_groups):
    for name, consumer_group in consumer_groups.items():
        for topic, partitions in consumer_group.items():
            for partition in partitions:
                tags = ["topic:{}".format(topic), "partition:{}".format(partition)] + ['optional:tag1']
                for mname in BROKER_METRICS:
                    aggregator.assert_metric(mname, tags=tags, at_least=1)
                for mname in CONSUMER_METRICS:
                    aggregator.assert_metric(mname, tags=tags + ["consumer_group:{}".format(name)], at_least=1)

    aggregator.assert_all_metrics_covered()


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_consumer_config_error(caplog):
    instance = {'kafka_connect_str': KAFKA_CONNECT_STR, 'kafka_consumer_offsets': True, 'tags': ['optional:tag1']}
    kafka_consumer_check = KafkaCheck('kafka_consumer', {}, [instance])

    if is_legacy_check(kafka_consumer_check):
        pytest.skip("This test does not apply to legacy check")

    kafka_consumer_check.check(instance)
    assert 'monitor_unlisted_consumer_groups is False' in caplog.text


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_no_topics(aggregator, kafka_instance):
    kafka_instance['consumer_groups'] = {'my_consumer': {}}
    kafka_consumer_check = KafkaCheck('kafka_consumer', {}, [kafka_instance])
    kafka_consumer_check.check(kafka_instance)

    if is_legacy_check(kafka_consumer_check):
        pytest.skip("This test does not apply to legacy check")

    assert_check_kafka(aggregator, {'my_consumer': {'marvel': [0]}})


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_no_partitions(aggregator, kafka_instance):
    kafka_instance['consumer_groups'] = {'my_consumer': {'marvel': []}}
    kafka_consumer_check = KafkaCheck('kafka_consumer', {}, [kafka_instance])
    kafka_consumer_check.check(kafka_instance)

    assert_check_kafka(aggregator, {'my_consumer': {'marvel': [0]}})


@pytest.mark.skipif(os.environ.get('KAFKA_VERSION', '').startswith('0.9'), reason='Old Kafka version')
@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_version_metadata(datadog_agent, kafka_instance):
    kafka_consumer_check = KafkaCheck('kafka_consumer', {}, [kafka_instance])
    kafka_consumer_check.check_id = 'test:123'

    version_data = [str(part) for part in kafka_consumer_check.kafka_client._client.check_version()]
    version_parts = {'version.{}'.format(name): part for name, part in zip(('major', 'minor', 'patch'), version_data)}
    version_parts['version.scheme'] = 'semver'
    version_parts['version.raw'] = '.'.join(version_data)

    kafka_consumer_check.check(kafka_instance)
    datadog_agent.assert_metadata('test:123', version_parts)
