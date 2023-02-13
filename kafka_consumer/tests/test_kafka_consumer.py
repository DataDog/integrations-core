# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import copy
from contextlib import nullcontext as does_not_raise

import mock
import pytest

from datadog_checks.base import ConfigurationError
from datadog_checks.kafka_consumer import KafkaCheck
from datadog_checks.kafka_consumer.kafka_consumer import OAuthTokenProvider

from .common import BROKER_METRICS, CONSUMER_METRICS, KAFKA_CONNECT_STR, KAFKA_VERSION

metrics = BROKER_METRICS + CONSUMER_METRICS

pytestmark = [pytest.mark.integration]


@pytest.mark.unit
def test_gssapi(kafka_instance, dd_run_check):
    instance = copy.deepcopy(kafka_instance)
    instance['sasl_mechanism'] = 'GSSAPI'
    instance['security_protocol'] = 'SASL_PLAINTEXT'
    instance['sasl_kerberos_service_name'] = 'kafka'
    kafka_consumer_check = KafkaCheck('kafka_consumer', {}, [instance])
    # assert the check doesn't fail with:
    # Exception: Could not find main GSSAPI shared library.
    with pytest.raises(Exception, match='check_version'):
        dd_run_check(kafka_consumer_check)


@pytest.mark.unit
def test_tls_config_ok(kafka_instance_tls):
    with mock.patch('datadog_checks.base.utils.tls.ssl') as ssl:
        with mock.patch('kafka.KafkaAdminClient') as kafka_admin_client:
            # mock Kafka Client
            kafka_admin_client.return_value = mock.MagicMock()
            # mock TLS context
            tls_context = mock.MagicMock()
            ssl.SSLContext.return_value = tls_context

            kafka_consumer_check = KafkaCheck('kafka_consumer', {}, [kafka_instance_tls])
            client = kafka_consumer_check.kafka_client

            assert tls_context.check_hostname is True
            assert tls_context.tls_cert is not None
            assert tls_context.check_hostname is True
            assert client is not None
            assert kafka_admin_client.call_args_list[0].kwargs['ssl_context'] == tls_context


@pytest.mark.parametrize(
    'sasl_oauth_token_provider, expected_exception',
    [
        pytest.param(
            {},
            pytest.raises(AssertionError, match="sasl_oauth_token_provider required for OAUTHBEARER sasl"),
            id="No sasl_oauth_token_provider",
        ),
        pytest.param(
            {'sasl_oauth_token_provider': {}},
            pytest.raises(ConfigurationError, match="The `url` setting of `auth_token` reader is required"),
            id="Empty sasl_oauth_token_provider, url missing",
        ),
        pytest.param(
            {'sasl_oauth_token_provider': {'url': 'http://fake.url'}},
            pytest.raises(ConfigurationError, match="The `client_id` setting of `auth_token` reader is required"),
            id="client_id missing",
        ),
        pytest.param(
            {'sasl_oauth_token_provider': {'url': 'http://fake.url', 'client_id': 'id'}},
            pytest.raises(ConfigurationError, match="The `client_secret` setting of `auth_token` reader is required"),
            id="client_secret missing",
        ),
        pytest.param(
            {'sasl_oauth_token_provider': {'url': 'http://fake.url', 'client_id': 'id', 'client_secret': 'secret'}},
            pytest.raises(Exception, match="NoBrokersAvailable"),  # Mock the expected response after library migration
            id="valid config",
        ),
    ],
)
def test_oauth_config(sasl_oauth_token_provider, expected_exception):
    instance = {
        'kafka_connect_str': KAFKA_CONNECT_STR,
        'monitor_unlisted_consumer_groups': True,
        'security_protocol': 'SASL_PLAINTEXT',
        'sasl_mechanism': 'OAUTHBEARER',
    }
    instance.update(sasl_oauth_token_provider)
    check = KafkaCheck('kafka_consumer', {}, [instance])

    with expected_exception:
        check.check(instance)


@pytest.mark.unit
def test_oauth_token_client_config(kafka_instance):
    instance = copy.deepcopy(kafka_instance)
    instance['kafka_client_api_version'] = "3.3.2"
    instance['security_protocol'] = "SASL_PLAINTEXT"
    instance['sasl_mechanism'] = "OAUTHBEARER"
    instance['sasl_oauth_token_provider'] = {
        "url": "http://fake.url",
        "client_id": "id",
        "client_secret": "secret",
    }

    with mock.patch('kafka.KafkaAdminClient') as kafka_admin_client:
        kafka_consumer_check = KafkaCheck('kafka_consumer', {}, [instance])
        _ = kafka_consumer_check.kafka_client
        params = kafka_admin_client.call_args_list[0].kwargs

        assert params['security_protocol'] == 'SASL_PLAINTEXT'
        assert params['sasl_mechanism'] == 'OAUTHBEARER'
        assert params['sasl_oauth_token_provider'].reader._client_id == "id"
        assert params['sasl_oauth_token_provider'].reader._client_secret == "secret"
        assert params['sasl_oauth_token_provider'].reader._url == "http://fake.url"
        assert isinstance(params['sasl_oauth_token_provider'], OAuthTokenProvider)


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

    version_data = [str(part) for part in KAFKA_VERSION.split('.')]
    version_parts = {'version.{}'.format(name): part for name, part in zip(('major', 'minor', 'patch'), version_data)}
    version_parts['version.scheme'] = 'semver'
    version_parts['version.raw'] = '.'.join(version_data)

    dd_run_check(kafka_consumer_check)
    datadog_agent.assert_metadata('test:123', version_parts)


# Get rid of dd_environment when we refactor and fix expected behaviors in the check
@pytest.mark.usefixtures('dd_environment')
@pytest.mark.parametrize(
    'instance, expected_exception, metric_count',
    [
        pytest.param({}, pytest.raises(Exception), 0, id="Empty instance"),
        pytest.param(
            {'kafka_connect_str': 12},
            pytest.raises(ConfigurationError, match='kafka_connect_str should be string or list of strings'),
            0,
            id="Invalid Non-string kafka_connect_str",
        ),
        # TODO fix this: This should raise ConfigurationError
        pytest.param(
            {'kafka_connect_str': [KAFKA_CONNECT_STR, '127.0.0.1:9093']},
            does_not_raise(),
            0,
            id="monitor_unlisted_consumer_groups is False",
        ),
        # TODO fix this: This should raise ConfigurationError
        pytest.param(
            {'kafka_connect_str': KAFKA_CONNECT_STR, 'consumer_groups': {}},
            does_not_raise(),
            0,
            id="Empty consumer_groups",
        ),
        pytest.param(
            {'kafka_connect_str': None},
            pytest.raises(ConfigurationError, match='kafka_connect_str should be string or list of strings'),
            0,
            id="Invalid Nonetype kafka_connect_str",
        ),
        pytest.param(
            {'kafka_connect_str': [KAFKA_CONNECT_STR, '127.0.0.1:9093'], 'monitor_unlisted_consumer_groups': True},
            does_not_raise(),
            4,
            id="Valid list kafka_connect_str",
        ),
        pytest.param(
            {'kafka_connect_str': KAFKA_CONNECT_STR, 'monitor_unlisted_consumer_groups': True},
            does_not_raise(),
            4,
            id="Valid str kafka_connect_str",
        ),
        pytest.param({'kafka_connect_str': 'invalid'}, pytest.raises(Exception), 0, id="Invalid str kafka_connect_str"),
        pytest.param(
            {'kafka_connect_str': KAFKA_CONNECT_STR, 'consumer_groups': {}, 'monitor_unlisted_consumer_groups': True},
            does_not_raise(),
            4,
            id="Empty consumer_groups and monitor_unlisted_consumer_groups true",
        ),
        pytest.param(
            {'kafka_connect_str': KAFKA_CONNECT_STR, 'consumer_groups': {'my_consumer': None}},
            does_not_raise(),
            4,
            id="One consumer group, all topics and partitions",
        ),
        pytest.param(
            {'kafka_connect_str': KAFKA_CONNECT_STR, 'consumer_groups': {'my_consumer': {'marvel': None}}},
            does_not_raise(),
            2,
            id="One consumer group, one topic, all partitions",
        ),
        pytest.param(
            {'kafka_connect_str': KAFKA_CONNECT_STR, 'consumer_groups': {'my_consumer': {'marvel': [1]}}},
            does_not_raise(),
            1,
            id="One consumer group, one topic, one partition",
        ),
    ],
)
def test_config(dd_run_check, instance, aggregator, expected_exception, metric_count):
    check = KafkaCheck('kafka_consumer', {}, [instance])
    with expected_exception:
        check.check(instance)

    for m in metrics:
        aggregator.assert_metric(m, count=metric_count)


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
