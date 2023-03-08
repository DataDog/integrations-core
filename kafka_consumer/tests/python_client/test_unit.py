# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import copy
import logging
from contextlib import nullcontext as does_not_raise

import mock
import pytest

from datadog_checks.dev.utils import get_metadata_metrics
from datadog_checks.kafka_consumer import KafkaCheck
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
    with pytest.raises(Exception):
        dd_run_check(check(instance))


def test_gssapi_config(kafka_instance, dd_run_check, check, caplog):
    instance = copy.deepcopy(kafka_instance)
    instance['sasl_mechanism'] = 'GSSAPI'
    instance['security_protocol'] = 'SASL_PLAINTEXT'
    instance['sasl_kerberos_service_name'] = 'kafka'
    instance['sasl_kerberos_domain_name'] = "Not none"

    # TODO: Mock GSSAPI here instead of expecting fail
    with pytest.raises(Exception):
        dd_run_check(check(instance))

    expected_warning = "Configuration option `sasl_kerberos_domain_name` has been deprecated"
    assert expected_warning in caplog.text


def test_tls_config_ok(check, kafka_instance_tls):
    with mock.patch('datadog_checks.base.utils.tls.ssl') as ssl:
        # mock TLS context
        tls_context = mock.MagicMock()
        ssl.SSLContext.return_value = tls_context

        kafka_consumer_check = check(kafka_instance_tls)
        with mock.patch('datadog_checks.kafka_consumer.KafkaCheck.get_tls_context', return_value=tls_context):
            assert kafka_consumer_check.client._tls_context == tls_context
            assert kafka_consumer_check.client._tls_context.check_hostname is True
            assert kafka_consumer_check.client._tls_context.tls_cert is not None


@pytest.mark.parametrize(
    'sasl_oauth_token_provider, expected_exception, mocked_admin_client',
    [
        pytest.param(
            {},
            pytest.raises(Exception, match="sasl_oauth_token_provider required for OAUTHBEARER sasl"),
            None,
            id="No sasl_oauth_token_provider",
        ),
        pytest.param(
            {'sasl_oauth_token_provider': {}},
            pytest.raises(Exception, match="The `url` setting of `auth_token` reader is required"),
            None,
            id="Empty sasl_oauth_token_provider, url missing",
        ),
        pytest.param(
            {'sasl_oauth_token_provider': {'url': 'http://fake.url'}},
            pytest.raises(Exception, match="The `client_id` setting of `auth_token` reader is required"),
            None,
            id="client_id missing",
        ),
        pytest.param(
            {'sasl_oauth_token_provider': {'url': 'http://fake.url', 'client_id': 'id'}},
            pytest.raises(Exception, match="The `client_secret` setting of `auth_token` reader is required"),
            None,
            id="client_secret missing",
        ),
        pytest.param(
            {'sasl_oauth_token_provider': {'url': 'http://fake.url', 'client_id': 'id', 'client_secret': 'secret'}},
            does_not_raise(),
            mock.MagicMock(),
            id="valid config",
        ),
    ],
)
def test_oauth_config(sasl_oauth_token_provider, expected_exception, mocked_admin_client, check, dd_run_check):
    instance = {
        'kafka_connect_str': KAFKA_CONNECT_STR,
        'monitor_unlisted_consumer_groups': True,
        'security_protocol': 'SASL_PLAINTEXT',
        'sasl_mechanism': 'OAUTHBEARER',
    }
    instance.update(sasl_oauth_token_provider)

    with expected_exception:
        with mock.patch(
            'datadog_checks.kafka_consumer.client.confluent_kafka_client.AdminClient',
            return_value=mocked_admin_client,
        ):
            dd_run_check(check(instance))


@pytest.mark.skip(reason='Add a test that not only check the parameter but also run the check')
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
    'instance, expected_exception, exception_msg, metric_count',
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
            {'kafka_connect_str': [KAFKA_CONNECT_STR, '127.0.0.1:9093']},
            does_not_raise(),
            'ConfigurationError: Cannot fetch consumer offsets because no consumer_groups are specified and '
            'monitor_unlisted_consumer_groups is False',
            0,
            id="monitor_unlisted_consumer_groups is False",
        ),
        pytest.param(
            {'kafka_connect_str': KAFKA_CONNECT_STR, 'consumer_groups': {}},
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
            {'kafka_connect_str': [KAFKA_CONNECT_STR, '127.0.0.1:9093'], 'monitor_unlisted_consumer_groups': True},
            does_not_raise(),
            '',
            4,
            id="Valid list kafka_connect_str",
        ),
        pytest.param(
            {'kafka_connect_str': KAFKA_CONNECT_STR, 'monitor_unlisted_consumer_groups': True},
            does_not_raise(),
            '',
            4,
            id="Valid str kafka_connect_str",
        ),
        pytest.param(
            {'kafka_connect_str': 'invalid'},
            pytest.raises(Exception),
            'ConfigurationError: Cannot fetch consumer offsets because no consumer_groups are specified and '
            'monitor_unlisted_consumer_groups is False',
            0,
            id="Invalid str kafka_connect_str",
        ),
        pytest.param(
            {'kafka_connect_str': KAFKA_CONNECT_STR, 'consumer_groups': {}, 'monitor_unlisted_consumer_groups': True},
            does_not_raise(),
            '',
            4,
            id="Empty consumer_groups and monitor_unlisted_consumer_groups true",
        ),
        pytest.param(
            {'kafka_connect_str': KAFKA_CONNECT_STR, 'consumer_groups': {'my_consumer': None}},
            does_not_raise(),
            '',
            4,
            id="One consumer group, all topics and partitions",
        ),
        pytest.param(
            {'kafka_connect_str': KAFKA_CONNECT_STR, 'consumer_groups': {'my_consumer': {'marvel': None}}},
            does_not_raise(),
            '',
            2,
            id="One consumer group, one topic, all partitions",
        ),
        pytest.param(
            {'kafka_connect_str': KAFKA_CONNECT_STR, 'consumer_groups': {'my_consumer': {'marvel': [1]}}},
            does_not_raise(),
            '',
            1,
            id="One consumer group, one topic, one partition",
        ),
    ],
)
def test_config(dd_run_check, check, instance, aggregator, expected_exception, exception_msg, metric_count, caplog):
    caplog.set_level(logging.DEBUG)
    with expected_exception:
        dd_run_check(check(instance))

    for m in metrics:
        aggregator.assert_metric(m, count=metric_count)

    assert exception_msg in caplog.text
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())


# TODO: After these tests are finished and the revamp is complete,
# the tests should be refactored to be parameters instead of separate tests
@mock.patch("datadog_checks.kafka_consumer.kafka_consumer.GenericKafkaClient")
def test_when_consumer_lag_less_than_zero_then_emit_event(
    mock_generic_client, check, kafka_instance, dd_run_check, aggregator
):
    # Given
    # consumer_offset = {(consumer_group, topic, partition): offset}
    consumer_offset = {("consumer_group1", "topic1", "partition1"): 2}
    # highwater_offset = {(topic, partition): offset}
    highwater_offset = {("topic1", "partition1"): 1}
    mock_client = mock.MagicMock()
    mock_client.get_consumer_offsets_dict.return_value = consumer_offset
    mock_client.get_highwater_offsets_dict.return_value = highwater_offset
    mock_client.get_partitions_for_topic.return_value = ['partition1']
    mock_generic_client.return_value = mock_client

    # When
    kafka_consumer_check = check(kafka_instance)
    dd_run_check(kafka_consumer_check)

    # Then
    aggregator.assert_metric(
        "kafka.broker_offset", count=1, tags=['optional:tag1', 'partition:partition1', 'topic:topic1']
    )
    aggregator.assert_metric(
        "kafka.consumer_offset",
        count=1,
        tags=['consumer_group:consumer_group1', 'optional:tag1', 'partition:partition1', 'topic:topic1'],
    )
    aggregator.assert_metric(
        "kafka.consumer_lag",
        count=1,
        tags=['consumer_group:consumer_group1', 'optional:tag1', 'partition:partition1', 'topic:topic1'],
    )
    aggregator.assert_event(
        "Consumer group: consumer_group1, "
        "topic: topic1, partition: partition1 has negative consumer lag. "
        "This should never happen and will result in the consumer skipping new messages "
        "until the lag turns positive.",
        count=1,
        tags=['consumer_group:consumer_group1', 'optional:tag1', 'partition:partition1', 'topic:topic1'],
    )


@mock.patch("datadog_checks.kafka_consumer.kafka_consumer.GenericKafkaClient")
def test_when_partition_is_none_then_emit_warning_log(
    mock_generic_client, check, kafka_instance, dd_run_check, aggregator, caplog
):
    # Given
    # consumer_offset = {(consumer_group, topic, partition): offset}
    consumer_offset = {("consumer_group1", "topic1", "partition1"): 2}
    # highwater_offset = {(topic, partition): offset}
    highwater_offset = {("topic1", "partition1"): 1}
    mock_client = mock.MagicMock()
    mock_client.get_consumer_offsets_dict.return_value = consumer_offset
    mock_client.get_highwater_offsets_dict.return_value = highwater_offset
    mock_client.get_partitions_for_topic.return_value = None
    mock_generic_client.return_value = mock_client
    caplog.set_level(logging.WARNING)

    # When
    kafka_consumer_check = check(kafka_instance)
    dd_run_check(kafka_consumer_check)

    # Then
    aggregator.assert_metric(
        "kafka.broker_offset", count=1, tags=['optional:tag1', 'partition:partition1', 'topic:topic1']
    )
    aggregator.assert_metric("kafka.consumer_offset", count=0)
    aggregator.assert_metric("kafka.consumer_lag", count=0)
    aggregator.assert_event(
        "Consumer group: consumer_group1, "
        "topic: topic1, partition: partition1 has negative consumer lag. "
        "This should never happen and will result in the consumer skipping new messages "
        "until the lag turns positive.",
        count=0,
    )

    expected_warning = (
        "Consumer group: consumer_group1 has offsets for topic: topic1, "
        "partition: partition1, but that topic has no partitions "
        "in the cluster, so skipping reporting these offsets"
    )

    assert expected_warning in caplog.text


@mock.patch("datadog_checks.kafka_consumer.kafka_consumer.GenericKafkaClient")
def test_when_partition_not_in_partitions_then_emit_warning_log(
    mock_generic_client, check, kafka_instance, dd_run_check, aggregator, caplog
):
    # Given
    # consumer_offset = {(consumer_group, topic, partition): offset}
    consumer_offset = {("consumer_group1", "topic1", "partition1"): 2}
    # highwater_offset = {(topic, partition): offset}
    highwater_offset = {("topic1", "partition1"): 1}
    mock_client = mock.MagicMock()
    mock_client.get_consumer_offsets_dict.return_value = consumer_offset
    mock_client.get_highwater_offsets_dict.return_value = highwater_offset
    mock_client.get_partitions_for_topic.return_value = ['partition2']
    mock_generic_client.return_value = mock_client
    caplog.set_level(logging.WARNING)

    # When
    kafka_consumer_check = check(kafka_instance)
    dd_run_check(kafka_consumer_check)

    # Then
    aggregator.assert_metric(
        "kafka.broker_offset", count=1, tags=['optional:tag1', 'partition:partition1', 'topic:topic1']
    )
    aggregator.assert_metric("kafka.consumer_offset", count=0)
    aggregator.assert_metric("kafka.consumer_lag", count=0)
    aggregator.assert_event(
        "Consumer group: consumer_group1, "
        "topic: topic1, partition: partition1 has negative consumer lag. "
        "This should never happen and will result in the consumer skipping new messages "
        "until the lag turns positive.",
        count=0,
    )

    expected_warning = (
        "Consumer group: consumer_group1 has offsets for topic: topic1, partition: partition1, "
        "but that topic partition isn't included in the cluster partitions, "
        "so skipping reporting these offsets"
    )

    assert expected_warning in caplog.text


@mock.patch("datadog_checks.kafka_consumer.kafka_consumer.GenericKafkaClient")
def test_when_highwater_metric_count_hit_context_limit_then_no_more_highwater_metrics(
    mock_generic_client, kafka_instance, dd_run_check, aggregator, caplog
):
    # Given
    # consumer_offset = {(consumer_group, topic, partition): offset}
    consumer_offset = {("consumer_group1", "topic1", "partition1"): 2}
    # highwater_offset = {(topic, partition): offset}
    highwater_offset = {("topic1", "partition1"): 3, ("topic2", "partition2"): 3}
    mock_client = mock.MagicMock()
    mock_client.get_consumer_offsets_dict.return_value = consumer_offset
    mock_client.get_highwater_offsets_dict.return_value = highwater_offset
    mock_client.get_partitions_for_topic.return_value = ['partition1']
    mock_generic_client.return_value = mock_client
    caplog.set_level(logging.WARNING)

    # When
    kafka_consumer_check = KafkaCheck('kafka_consumer', {'max_partition_contexts': 1}, [kafka_instance])
    dd_run_check(kafka_consumer_check)

    # Then
    aggregator.assert_metric("kafka.broker_offset", count=1)
    aggregator.assert_metric("kafka.consumer_offset", count=0)
    aggregator.assert_metric("kafka.consumer_lag", count=0)

    expected_warning = "Discovered 3 metric contexts"

    assert expected_warning in caplog.text


@mock.patch("datadog_checks.kafka_consumer.kafka_consumer.GenericKafkaClient")
def test_when_consumer_metric_count_hit_context_limit_then_no_more_consumer_metrics(
    mock_generic_client, kafka_instance, dd_run_check, aggregator, caplog
):
    # Given
    # consumer_offset = {(consumer_group, topic, partition): offset}
    consumer_offset = {("consumer_group1", "topic1", "partition1"): 2, ("consumer_group1", "topic2", "partition2"): 2}
    # highwater_offset = {(topic, partition): offset}
    highwater_offset = {("topic1", "partition1"): 3, ("topic2", "partition2"): 3}
    mock_client = mock.MagicMock()
    mock_client.get_consumer_offsets_dict.return_value = consumer_offset
    mock_client.get_highwater_offsets_dict.return_value = highwater_offset
    mock_client.get_partitions_for_topic.return_value = ['partition1']
    mock_generic_client.return_value = mock_client
    caplog.set_level(logging.DEBUG)

    # When
    kafka_consumer_check = KafkaCheck('kafka_consumer', {'max_partition_contexts': 3}, [kafka_instance])
    dd_run_check(kafka_consumer_check)

    # Then
    aggregator.assert_metric("kafka.broker_offset", count=2)
    aggregator.assert_metric("kafka.consumer_offset", count=1)
    aggregator.assert_metric("kafka.consumer_lag", count=0)

    expected_warning = "Discovered 4 metric contexts"
    assert expected_warning in caplog.text

    expected_debug = "Reported contexts number 1 greater than or equal to contexts limit of 1"
    assert expected_debug in caplog.text
