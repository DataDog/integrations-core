# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import concurrent.futures
import logging
from contextlib import nullcontext as does_not_raise

import mock
import pytest
from confluent_kafka.admin._group import ConsumerGroupListing, ListConsumerGroupsResult

from datadog_checks.kafka_consumer import KafkaCheck

pytestmark = [pytest.mark.unit]


@pytest.mark.parametrize(
    'extra_config, expected_http_kwargs',
    [
        pytest.param(
            {'ssl_check_hostname': False}, {'tls_validate_hostname': False}, id='legacy validate_hostname param'
        ),
    ],
)
def test_tls_config_legacy(extra_config, expected_http_kwargs, check, kafka_instance):
    kafka_instance.update(extra_config)
    kafka_consumer_check = check(kafka_instance)
    kafka_consumer_check.get_tls_context()
    actual_options = {
        k: v for k, v in kafka_consumer_check._tls_context_wrapper.config.items() if k in expected_http_kwargs
    }
    assert expected_http_kwargs == actual_options


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
def test_oauth_config(
    sasl_oauth_token_provider, expected_exception, mocked_admin_client, check, dd_run_check, kafka_instance
):
    kafka_instance.update(
        {
            'monitor_unlisted_consumer_groups': True,
            'security_protocol': 'SASL_PLAINTEXT',
            'sasl_mechanism': 'OAUTHBEARER',
        }
    )
    kafka_instance.update(sasl_oauth_token_provider)

    with expected_exception:
        with mock.patch(
            'datadog_checks.kafka_consumer.kafka_consumer.KafkaClient',
            return_value=mocked_admin_client,
        ):
            dd_run_check(check(kafka_instance))


# TODO: After these tests are finished and the revamp is complete,
# the tests should be refactored to be parameters instead of separate tests
@mock.patch("datadog_checks.kafka_consumer.kafka_consumer.KafkaClient")
def test_when_consumer_lag_less_than_zero_then_emit_event(
    mock_generic_client, check, kafka_instance, dd_run_check, aggregator
):
    # Given
    # consumer_offset = {(consumer_group, topic, partition): offset}
    consumer_offset = {("consumer_group1", "topic1", "partition1"): 2}
    # highwater_offset = {(topic, partition): offset}
    highwater_offset = {("topic1", "partition1"): 1}
    mock_client = mock.MagicMock()
    mock_client.get_consumer_offsets.return_value = consumer_offset
    mock_client.get_highwater_offsets.return_value = highwater_offset
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


@mock.patch("datadog_checks.kafka_consumer.kafka_consumer.KafkaClient")
def test_when_partition_is_none_then_emit_warning_log(
    mock_generic_client, check, kafka_instance, dd_run_check, aggregator, caplog
):
    # Given
    # consumer_offset = {(consumer_group, topic, partition): offset}
    consumer_offset = {("consumer_group1", "topic1", "partition1"): 2}
    # highwater_offset = {(topic, partition): offset}
    highwater_offset = {("topic1", "partition1"): 1}
    mock_client = mock.MagicMock()
    mock_client.get_consumer_offsets.return_value = consumer_offset
    mock_client.get_highwater_offsets.return_value = highwater_offset
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


@mock.patch("datadog_checks.kafka_consumer.kafka_consumer.KafkaClient")
def test_when_partition_not_in_partitions_then_emit_warning_log(
    mock_generic_client, check, kafka_instance, dd_run_check, aggregator, caplog
):
    # Given
    # consumer_offset = {(consumer_group, topic, partition): offset}
    consumer_offset = {("consumer_group1", "topic1", "partition1"): 2}
    # highwater_offset = {(topic, partition): offset}
    highwater_offset = {("topic1", "partition1"): 1}
    mock_client = mock.MagicMock()
    mock_client.get_consumer_offsets.return_value = consumer_offset
    mock_client.get_highwater_offsets.return_value = highwater_offset
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


@mock.patch("datadog_checks.kafka_consumer.kafka_consumer.KafkaClient")
def test_when_highwater_metric_count_hit_context_limit_then_no_more_highwater_metrics(
    mock_generic_client, kafka_instance, dd_run_check, aggregator, caplog
):
    # Given
    # consumer_offset = {(consumer_group, topic, partition): offset}
    consumer_offset = {("consumer_group1", "topic1", "partition1"): 2}
    # highwater_offset = {(topic, partition): offset}
    highwater_offset = {("topic1", "partition1"): 3, ("topic2", "partition2"): 3}
    mock_client = mock.MagicMock()
    mock_client.get_consumer_offsets.return_value = consumer_offset
    mock_client.get_highwater_offsets.return_value = highwater_offset
    mock_client.get_partitions_for_topic.return_value = ['partition1']
    mock_generic_client.return_value = mock_client
    caplog.set_level(logging.WARNING)

    # When
    kafka_consumer_check = KafkaCheck('kafka_consumer', {'max_partition_contexts': 2}, [kafka_instance])
    dd_run_check(kafka_consumer_check)

    # Then
    aggregator.assert_metric("kafka.broker_offset", count=2)
    aggregator.assert_metric("kafka.consumer_offset", count=0)
    aggregator.assert_metric("kafka.consumer_lag", count=0)

    expected_warning = "Discovered 3 metric contexts"

    assert expected_warning in caplog.text


@mock.patch("datadog_checks.kafka_consumer.kafka_consumer.KafkaClient")
def test_when_consumer_metric_count_hit_context_limit_then_no_more_consumer_metrics(
    mock_generic_client, kafka_instance, dd_run_check, aggregator, caplog
):
    # Given
    # consumer_offset = {(consumer_group, topic, partition): offset}
    consumer_offset = {("consumer_group1", "topic1", "partition1"): 2, ("consumer_group1", "topic2", "partition2"): 2}
    # highwater_offset = {(topic, partition): offset}
    highwater_offset = {("topic1", "partition1"): 3, ("topic2", "partition2"): 3}
    mock_client = mock.MagicMock()
    mock_client.get_consumer_offsets.return_value = consumer_offset
    mock_client.get_highwater_offsets.return_value = highwater_offset
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


def test_when_empty_string_consumer_group_then_skip(kafka_instance):
    consumer_groups_result = ListConsumerGroupsResult(
        valid=[
            ConsumerGroupListing(group_id="", is_simple_consumer_group=True),  # Should be filtered out
            ConsumerGroupListing(group_id="my_consumer", is_simple_consumer_group=True),
        ]
    )
    kafka_instance['monitor_unlisted_consumer_groups'] = True
    future = concurrent.futures.Future()
    future.set_result(consumer_groups_result)

    with mock.patch("datadog_checks.kafka_consumer.client.AdminClient.list_consumer_groups", return_value=future):
        kafka_consumer_check = KafkaCheck('kafka_consumer', {}, [kafka_instance])
        assert kafka_consumer_check.client._get_consumer_groups() == ["my_consumer"]
