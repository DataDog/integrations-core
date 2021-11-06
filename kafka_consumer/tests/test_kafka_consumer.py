# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import copy
import os

import mock
import pytest

from datadog_checks.kafka_consumer import KafkaCheck
from datadog_checks.kafka_consumer.legacy_0_10_2 import LegacyKafkaCheck_0_10_2
from datadog_checks.kafka_consumer.new_kafka_consumer import NewKafkaConsumerCheck

from .common import KAFKA_CONNECT_STR, is_legacy_check, is_supported

pytestmark = pytest.mark.skipif(
    not is_supported('kafka'), reason='kafka consumer offsets not supported in current environment'
)


BROKER_METRICS = ['kafka.broker_offset']

CONSUMER_METRICS = ['kafka.consumer_offset', 'kafka.consumer_lag']


@pytest.mark.unit
def test_uses_legacy_implementation_when_legacy_version_specified(kafka_instance):
    instance = copy.deepcopy(kafka_instance)
    instance['kafka_client_api_version'] = '0.10.1'
    kafka_consumer_check = KafkaCheck('kafka_consumer', {}, [instance])
    kafka_consumer_check._init_check_based_on_kafka_version()

    assert isinstance(kafka_consumer_check.sub_check, LegacyKafkaCheck_0_10_2)


@pytest.mark.unit
def test_uses_new_implementation_when_new_version_specified(kafka_instance):
    instance = copy.deepcopy(kafka_instance)
    instance['kafka_client_api_version'] = '0.10.2'
    kafka_consumer_check = KafkaCheck('kafka_consumer', {}, [instance])
    kafka_consumer_check._init_check_based_on_kafka_version()

    assert isinstance(kafka_consumer_check.sub_check, NewKafkaConsumerCheck)


@pytest.mark.unit
def test_tls_config_ok(kafka_instance_tls):
    with mock.patch('datadog_checks.base.utils.tls.ssl') as ssl:
        with mock.patch('kafka.KafkaClient') as kafka_client:

            # mock Kafka Client
            kafka_client.return_value = mock.MagicMock()

            # mock TLS context
            tls_context = mock.MagicMock()
            ssl.SSLContext.return_value = tls_context

            kafka_consumer_check = KafkaCheck('kafka_consumer', {}, [kafka_instance_tls])
            kafka_consumer_check._create_kafka_client(clazz=kafka_client)

            assert tls_context.check_hostname is True
            assert tls_context.tls_cert is not None
            assert tls_context.check_hostname is True
            assert kafka_consumer_check.create_kafka_client is not None


@pytest.mark.parametrize(
    'extra_config, expected_http_kwargs',
    [
        pytest.param(
            {'ssl_check_hostname': False}, {'tls_validate_hostname': False}, id='legacy validate_hostname param'
        ),
    ],
)
def test_tls_config_legacy(extra_config, expected_http_kwargs, kafka_instance):
    instance = kafka_instance
    instance.update(extra_config)

    kafka_consumer_check = KafkaCheck('kafka_consumer', {}, [instance])

    kafka_consumer_check.get_tls_context()
    actual_options = {
        k: v for k, v in kafka_consumer_check._tls_context_wrapper.config.items() if k in expected_http_kwargs
    }
    assert expected_http_kwargs == actual_options


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_check_kafka(aggregator, kafka_instance, dd_run_check):
    """
    Testing Kafka_consumer check.
    """
    kafka_consumer_check = KafkaCheck('kafka_consumer', {}, [kafka_instance])
    dd_run_check(kafka_consumer_check)

    assert_check_kafka(aggregator, kafka_instance['consumer_groups'])


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_check_kafka_metrics_limit(aggregator, kafka_instance, dd_run_check):
    """
    Testing Kafka_consumer check.
    """
    kafka_consumer_check = KafkaCheck('kafka_consumer', {'max_partition_contexts': 1}, [kafka_instance])
    dd_run_check(kafka_consumer_check)

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


@pytest.mark.skipif(is_legacy_check(), reason="This test does not apply to the legacy check.")
@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_consumer_config_error(caplog, dd_run_check):
    instance = {'kafka_connect_str': KAFKA_CONNECT_STR, 'kafka_consumer_offsets': True, 'tags': ['optional:tag1']}
    kafka_consumer_check = KafkaCheck('kafka_consumer', {}, [instance])

    dd_run_check(kafka_consumer_check, extract_message=True)
    assert 'monitor_unlisted_consumer_groups is False' in caplog.text


@pytest.mark.skipif(is_legacy_check(), reason="This test does not apply to the legacy check.")
@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_no_topics(aggregator, kafka_instance, dd_run_check):
    kafka_instance['consumer_groups'] = {'my_consumer': {}}
    kafka_consumer_check = KafkaCheck('kafka_consumer', {}, [kafka_instance])
    dd_run_check(kafka_consumer_check)

    assert_check_kafka(aggregator, {'my_consumer': {'marvel': [0]}})


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_no_partitions(aggregator, kafka_instance, dd_run_check):
    kafka_instance['consumer_groups'] = {'my_consumer': {'marvel': []}}
    kafka_consumer_check = KafkaCheck('kafka_consumer', {}, [kafka_instance])
    dd_run_check(kafka_consumer_check)

    assert_check_kafka(aggregator, {'my_consumer': {'marvel': [0]}})


@pytest.mark.skipif(os.environ.get('KAFKA_VERSION', '').startswith('0.9'), reason='Old Kafka version')
@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_version_metadata(datadog_agent, kafka_instance, dd_run_check):
    kafka_consumer_check = KafkaCheck('kafka_consumer', {}, [kafka_instance])
    kafka_consumer_check.check_id = 'test:123'

    kafka_client = kafka_consumer_check.create_kafka_client()
    version_data = [str(part) for part in kafka_client.check_version()]
    kafka_client.close()
    version_parts = {'version.{}'.format(name): part for name, part in zip(('major', 'minor', 'patch'), version_data)}
    version_parts['version.scheme'] = 'semver'
    version_parts['version.raw'] = '.'.join(version_data)

    dd_run_check(kafka_consumer_check)
    datadog_agent.assert_metadata('test:123', version_parts)
