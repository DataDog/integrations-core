# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import copy
from contextlib import nullcontext as does_not_raise

import mock
import pytest

from datadog_checks.base import ConfigurationError
from datadog_checks.dev.utils import get_metadata_metrics
from datadog_checks.kafka_consumer.client.kafka_python_client import OAuthTokenProvider

from ..common import KAFKA_CONNECT_STR, metrics

pytestmark = [pytest.mark.unit]


def test_gssapi(kafka_instance, dd_run_check, check):
    instance = copy.deepcopy(kafka_instance)
    instance['sasl_mechanism'] = 'GSSAPI'
    instance['security_protocol'] = 'SASL_PLAINTEXT'
    instance['sasl_kerberos_service_name'] = 'kafka'
    # assert the check doesn't fail with:
    # Exception: Could not find main GSSAPI shared library.
    with pytest.raises(Exception, match='check_version'):
        dd_run_check(check(instance))


def test_tls_config_ok(check, kafka_instance_tls):
    with mock.patch('datadog_checks.base.utils.tls.ssl') as ssl:
        with mock.patch('kafka.KafkaAdminClient') as kafka_admin_client:

            # mock Kafka Client
            kafka_admin_client.return_value = mock.MagicMock()

            # mock TLS context
            tls_context = mock.MagicMock()
            ssl.SSLContext.return_value = tls_context

            kafka_consumer_check = check(kafka_instance_tls)
            kafka_consumer_check.client._create_kafka_client(clazz=kafka_admin_client)

            assert tls_context.check_hostname is True
            assert tls_context.tls_cert is not None
            assert tls_context.check_hostname is True
            assert kafka_consumer_check.client.create_kafka_admin_client is not None


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
def test_oauth_config(sasl_oauth_token_provider, check, expected_exception):
    instance = {
        'kafka_connect_str': KAFKA_CONNECT_STR,
        'monitor_unlisted_consumer_groups': True,
        'security_protocol': 'SASL_PLAINTEXT',
        'sasl_mechanism': 'OAUTHBEARER',
    }
    instance.update(sasl_oauth_token_provider)

    with expected_exception:
        check(instance).check(instance)


def test_oauth_token_client_config(check, kafka_instance):
    kafka_instance['kafka_client_api_version'] = "3.3.2"
    kafka_instance['security_protocol'] = "SASL_PLAINTEXT"
    kafka_instance['sasl_mechanism'] = "OAUTHBEARER"
    kafka_instance['sasl_oauth_token_provider'] = {
        "url": "http://fake.url",
        "client_id": "id",
        "client_secret": "secret",
    }

    with mock.patch('kafka.KafkaAdminClient') as kafka_admin_client:
        kafka_consumer_check = check(kafka_instance)
        kafka_consumer_check.client._create_kafka_client(clazz=kafka_admin_client)
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
def test_tls_config_legacy(extra_config, expected_http_kwargs, check, kafka_instance):
    instance = kafka_instance
    instance.update(extra_config)

    kafka_consumer_check = check(instance)
    kafka_consumer_check.get_tls_context()
    actual_options = {
        k: v for k, v in kafka_consumer_check._tls_context_wrapper.config.items() if k in expected_http_kwargs
    }
    assert expected_http_kwargs == actual_options


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
def test_config(check, instance, aggregator, expected_exception, metric_count):
    with expected_exception:
        check(instance).check(instance)

    for m in metrics:
        aggregator.assert_metric(m, count=metric_count)

    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
