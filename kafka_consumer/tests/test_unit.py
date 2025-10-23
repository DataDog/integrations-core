# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import base64
import json
import logging
from contextlib import nullcontext as does_not_raise

import mock
import pytest
from confluent_kafka import TopicPartition
from google.protobuf import descriptor_pb2
from google.protobuf.message import DecodeError

from datadog_checks.kafka_consumer import KafkaCheck
from datadog_checks.kafka_consumer.client import KafkaClient
from datadog_checks.kafka_consumer.kafka_consumer import (
    DATA_STREAMS_MESSAGES_CACHE_KEY,
    _get_interpolated_timestamp,
    build_avro_schema,
    build_protobuf_schema,
    build_schema,
    deserialize_message,
    resolve_start_offsets,
)

pytestmark = [pytest.mark.unit]


def fake_consumer_offsets_for_times(partitions):
    """In our testing environment the offset is 80 for all partitions and topics."""

    return [(t, p, 80) for t, p in partitions]


def seed_mock_client(cluster_id="cluster_id"):
    """Set some common defaults for the mock client to kafka."""
    client = mock.create_autospec(KafkaClient)
    client.list_consumer_groups.return_value = ["consumer_group1", "datadog-agent"]
    client.get_partitions_for_topic.return_value = ['partition1']
    client.list_consumer_group_offsets.return_value = [("consumer_group1", [("topic1", "partition1", 2)])]
    client.describe_consumer_group.return_value = 'STABLE'
    client.consumer_get_cluster_id_and_list_topics.return_value = (
        cluster_id,
        # topics
        [
            # Used in unit tets
            ('topic1', ["partition1"]),
            ('topic2', ["partition2"]),
            # Copied from integration tests
            ('dc', [0, 1]),
            ('unconsumed_topic', [0, 1]),
            ('marvel', [0, 1]),
            ('__consumer_offsets', [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]),
        ],
    )
    client.consumer_offsets_for_times = fake_consumer_offsets_for_times
    return client


@pytest.mark.parametrize(
    'legacy_config, kafka_client_config, value',
    [
        pytest.param("ssl_check_hostname", "_tls_validate_hostname", False, id='legacy validate_hostname param false'),
        pytest.param("ssl_check_hostname", "_tls_validate_hostname", True, id='legacy validate_hostname param true'),
        pytest.param("ssl_cafile", "_tls_ca_cert", "ca_file", id='legacy tls_ca_cert param'),
        pytest.param("ssl_certfile", "_tls_cert", "cert", id='legacy tls_cert param'),
        pytest.param("ssl_keyfile", "_tls_private_key", "private_key", id='legacy tls_private_key param'),
        pytest.param(
            "ssl_password",
            "_tls_private_key_password",
            "private_key_password",
            id='legacy tls_private_key_password param',
        ),
    ],
)
def test_tls_config_legacy(legacy_config, kafka_client_config, value, check):
    kafka_consumer_check = check({legacy_config: value})
    assert getattr(kafka_consumer_check.config, kafka_client_config) == value


@pytest.mark.parametrize(
    'ssl_check_hostname_value, tls_validate_hostname_value, expected_value',
    [
        pytest.param(True, True, True, id='Both true'),
        pytest.param(False, False, False, id='Both false'),
        pytest.param(False, True, True, id='only tls_validate_hostname_value true'),
        pytest.param(True, False, False, id='only tls_validate_hostname_value false'),
        pytest.param(False, "true", True, id='tls_validate_hostname true as string'),
        pytest.param(False, "false", False, id='tls_validate_hostname false as string'),
    ],
)
def test_tls_validate_hostname_conflict(
    ssl_check_hostname_value, tls_validate_hostname_value, expected_value, check, kafka_instance
):
    kafka_instance.update(
        {"ssl_check_hostname": ssl_check_hostname_value, "tls_validate_hostname": tls_validate_hostname_value}
    )
    kafka_consumer_check = check(kafka_instance)
    assert kafka_consumer_check.config._tls_validate_hostname == expected_value


@pytest.mark.parametrize(
    'tls_verify, expected',
    [
        pytest.param({}, "true", id='given empty tls_verify, expect default string true'),
        pytest.param({'tls_verify': True}, "true", id='given True tls_verify, expect string true'),
        pytest.param(
            {
                'tls_verify': False,
                "tls_cert": None,
                "tls_ca_cert": None,
                "tls_private_key": None,
                "tls_private_key_password": None,
            },
            "false",
            id='given False tls_verify and other TLS options none, expect string false',
        ),
        pytest.param(
            {'tls_verify': False, "tls_private_key_password": "password"},
            "true",
            id='given False tls_verify but TLS password, expect string true',
        ),
    ],
)
def test_tls_verify_is_string(tls_verify, expected, check, kafka_instance):
    kafka_instance.update(tls_verify)
    kafka_consumer_check = check(kafka_instance)
    config = kafka_consumer_check.config

    assert config._tls_verify == expected


mock_client = mock.MagicMock()
mock_client.get_highwater_offsets.return_value = ({}, "")
mock_client.consumer_get_cluster_id_and_list_topics.return_value = (
    "cluster_id",
    # topics
    [
        # Used in unit tets
        ('topic1', ["partition1"]),
        ('topic2', ["partition2"]),
        # Copied from integration tests
        ('dc', [0, 1]),
        ('unconsumed_topic', [0, 1]),
        ('marvel', [0, 1]),
        ('__consumer_offsets', [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]),
    ],
)


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
            mock_client,
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
def test_when_consumer_lag_less_than_zero_then_emit_event(check, kafka_instance, dd_run_check, aggregator):
    # Given
    mock_client = seed_mock_client()
    # We need the consumer offset to be higher than the highwater offset.
    mock_client.list_consumer_group_offsets.return_value = [("consumer_group1", [("topic1", "partition1", 81)])]
    kafka_consumer_check = check(kafka_instance)
    kafka_consumer_check.client = mock_client

    # When
    dd_run_check(kafka_consumer_check)

    # Then
    aggregator.assert_metric(
        "kafka.broker_offset",
        count=1,
        tags=['optional:tag1', 'partition:partition1', 'topic:topic1', 'kafka_cluster_id:cluster_id'],
    )
    aggregator.assert_metric(
        "kafka.consumer_offset",
        count=1,
        tags=[
            'consumer_group:consumer_group1',
            'optional:tag1',
            'partition:partition1',
            'topic:topic1',
            'kafka_cluster_id:cluster_id',
        ],
    )
    aggregator.assert_metric(
        "kafka.consumer_lag",
        count=1,
        tags=[
            'consumer_group:consumer_group1',
            'optional:tag1',
            'partition:partition1',
            'topic:topic1',
            'kafka_cluster_id:cluster_id',
        ],
    )
    aggregator.assert_event(
        "Consumer group: consumer_group1, "
        "topic: topic1, partition: partition1 has negative consumer lag. "
        "This should never happen and will result in the consumer skipping new messages "
        "until the lag turns positive.",
        count=1,
        tags=[
            'consumer_group:consumer_group1',
            'optional:tag1',
            'partition:partition1',
            'topic:topic1',
            'kafka_cluster_id:cluster_id',
        ],
    )


def test_when_collect_consumer_group_state_is_enabled(check, kafka_instance, dd_run_check, aggregator):
    mock_client = seed_mock_client()
    kafka_instance["collect_consumer_group_state"] = True
    kafka_consumer_check = check(kafka_instance)
    kafka_consumer_check.client = mock_client

    dd_run_check(kafka_consumer_check)

    aggregator.assert_metric(
        "kafka.consumer_offset",
        count=1,
        tags=[
            'consumer_group:consumer_group1',
            'optional:tag1',
            'partition:partition1',
            'topic:topic1',
            'kafka_cluster_id:cluster_id',
            'consumer_group_state:STABLE',
        ],
    )
    aggregator.assert_metric(
        "kafka.consumer_lag",
        count=1,
        tags=[
            'consumer_group:consumer_group1',
            'optional:tag1',
            'partition:partition1',
            'topic:topic1',
            'kafka_cluster_id:cluster_id',
            'consumer_group_state:STABLE',
        ],
    )


def test_when_no_partitions_then_emit_warning_log(check, kafka_instance, dd_run_check, aggregator, caplog):
    # Given
    caplog.set_level(logging.WARNING)

    mock_client = seed_mock_client()
    mock_client.get_partitions_for_topic.return_value = []
    kafka_consumer_check = check(kafka_instance)
    kafka_consumer_check.client = mock_client

    # When
    dd_run_check(kafka_consumer_check)

    # Then
    aggregator.assert_metric(
        "kafka.broker_offset",
        count=1,
        tags=['optional:tag1', 'partition:partition1', 'topic:topic1', 'kafka_cluster_id:cluster_id'],
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


def test_when_partition_not_in_partitions_then_emit_warning_log(
    check, kafka_instance, dd_run_check, aggregator, caplog
):
    # Given
    caplog.set_level(logging.WARNING)

    mock_client = seed_mock_client()
    mock_client.get_partitions_for_topic.return_value = ['partition2']
    kafka_consumer_check = check(kafka_instance)
    kafka_consumer_check.client = mock_client

    # When
    dd_run_check(kafka_consumer_check)

    # Then
    aggregator.assert_metric(
        "kafka.broker_offset",
        count=1,
        tags=['optional:tag1', 'partition:partition1', 'topic:topic1', 'kafka_cluster_id:cluster_id'],
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


def test_when_highwater_metric_count_hit_context_limit_then_no_more_highwater_metrics(
    check, kafka_instance, dd_run_check, aggregator, caplog
):
    # Given
    caplog.set_level(logging.WARNING)

    mock_client = seed_mock_client()
    kafka_consumer_check = check(kafka_instance, init_config={'max_partition_contexts': 2})
    kafka_consumer_check.client = mock_client

    # When
    dd_run_check(kafka_consumer_check)

    # Then
    aggregator.assert_metric("kafka.broker_offset", count=1)
    aggregator.assert_metric("kafka.consumer_offset", count=1)
    aggregator.assert_metric("kafka.consumer_lag", count=0)

    expected_warning = "Discovered 2 metric contexts"

    assert expected_warning in caplog.text


def test_when_consumer_metric_count_hit_context_limit_then_no_more_consumer_metrics(
    check, kafka_instance, dd_run_check, aggregator, caplog
):
    # Given
    caplog.set_level(logging.DEBUG)

    mock_client = seed_mock_client()
    mock_client.list_consumer_group_offsets.return_value = [
        ("consumer_group1", [("topic1", "partition1", 2)]),
        ("consumer_group1", [("topic2", "partition2", 2)]),
    ]
    kafka_consumer_check = check(kafka_instance, init_config={'max_partition_contexts': 3})
    kafka_consumer_check.client = mock_client

    # When
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
    kafka_instance["monitor_unlisted_consumer_groups"] = True
    with mock.patch(
        "datadog_checks.kafka_consumer.kafka_consumer.KafkaClient.list_consumer_groups",
        return_value=["", "my_consumer"],
    ):
        kafka_consumer_check = KafkaCheck('kafka_consumer', {}, [kafka_instance])
        assert kafka_consumer_check._get_consumer_groups() == ["my_consumer"]


def test_get_interpolated_timestamp():
    assert _get_interpolated_timestamp({0: 100, 10: 200}, 5) == 150
    assert _get_interpolated_timestamp({10: 100, 20: 200}, 5) == 50
    assert _get_interpolated_timestamp({0: 100, 10: 200}, 15) == 250
    assert _get_interpolated_timestamp({10: 200}, 15) is None


@pytest.mark.parametrize(
    'persistent_cache_contents, instance_overrides, consumer_lag_seconds_count',
    [
        pytest.param(
            "",
            {
                'consumer_groups': {},
                'data_streams_enabled': 'true',
                'monitor_unlisted_consumer_groups': True,
            },
            0,
            id='Read from cache failed',
        ),
    ],
)
def test_load_broker_timestamps_empty(
    persistent_cache_contents,
    instance_overrides,
    consumer_lag_seconds_count,
    kafka_instance,
    dd_run_check,
    caplog,
    aggregator,
    check,
):
    kafka_instance.update(instance_overrides)
    mock_client = seed_mock_client()
    check = check(kafka_instance)
    check.client = mock_client
    check.read_persistent_cache = mock.Mock(return_value=persistent_cache_contents)
    dd_run_check(check)

    caplog.set_level(logging.WARN)
    expected_warning = " Could not read broker timestamps from cache"

    assert expected_warning in caplog.text
    aggregator.assert_metric("kafka.estimated_consumer_lag", count=consumer_lag_seconds_count)
    assert check.read_persistent_cache.mock_calls == [mock.call("broker_timestamps_")]


def test_client_init(kafka_instance, check, dd_run_check):
    """
    We only open a connection to datadog-agent consumer once.

    Doing so more often degrades performance, as described in this issue:
    https://github.com/DataDog/integrations-core/issues/19564
    """
    mock_client = seed_mock_client()
    check = check(kafka_instance)
    check.client = mock_client
    dd_run_check(check)

    assert check.client.open_consumer.mock_calls == [mock.call("datadog-agent")]


def test_resolve_start_offsets():
    highwater_offsets = {
        ("topic1", 0): 100,
        ("topic1", 1): 200,
        ("topic2", 0): 150,
    }
    assert resolve_start_offsets(highwater_offsets, "topic1", 0, 80, 10) == [TopicPartition("topic1", 0, 80)]
    assert resolve_start_offsets(highwater_offsets, "topic2", 0, -1, 10) == [TopicPartition("topic2", 0, 141)]
    assert sorted(resolve_start_offsets(highwater_offsets, "topic1", -1, -1, 10)) == [
        TopicPartition("topic1", 0, 81),
        TopicPartition("topic1", 1, 191),
    ]


class MockedMessage:
    def __init__(self, value, key=None, offset=0):
        self.v = value
        self.k = key
        self.o = offset

    def value(self):
        return self.v

    def key(self):
        return self.k

    def partition(self):
        return 0

    def offset(self):
        return self.o


def test_deserialize_message():
    message = b'{"name": "Peter Parker", "age": 18, "transaction_amount": 123, "currency": "dollar"}'
    # schema ID is 350, which is 0x015E in hex.
    # A magic byte (0x00) is added and the schema ID (4-byte big-endian integer).
    message_with_schema = (
        b'\x00\x00\x00\x01\x5e{"name": "Peter Parker", "age": 18, "transaction_amount": 123, "currency": "dollar"}'
    )
    key = b'{"name": "Peter Parker"}'
    assert deserialize_message(MockedMessage(message, key), 'json', '', False, 'json', '', False) == (
        '{"name": "Peter Parker", "age": 18, "transaction_amount": 123, "currency": "dollar"}',
        None,
        '{"name": "Peter Parker"}',
        None,
    )
    assert deserialize_message(MockedMessage(message_with_schema), 'json', '', False, 'json', '', False) == (
        '{"name": "Peter Parker", "age": 18, "transaction_amount": 123, "currency": "dollar"}',
        350,
        '',
        None,
    )
    invalid_json = b'{"name": "Peter Parker", "age": 18, "transaction_amount": 123, "currency": "dollar"'
    assert deserialize_message(MockedMessage(invalid_json, key), 'json', '', False, 'json', '', False) == (
        None,
        None,
        None,
        None,
    )

    invalid_utf8 = b'{"name": "Peter Parker", "age": 18, "transaction_amount": 123, "currency": "dollar"\xff'
    assert deserialize_message(MockedMessage(invalid_utf8, key), 'json', '', False, 'json', '', False) == (
        None,
        None,
        None,
        None,
    )

    # Test Avro deserialization
    avro_schema = (
        '{"type": "record", "name": "Book", "namespace": "com.book", '
        '"fields": [{"name": "isbn", "type": "long"}, {"name": "title", "type": "string"}, '
        '{"name": "author", "type": "string"}]}'
    )
    avro_message = b'\xd0\xf5\xe4\xd6\xa3\xb9\x046The Go Programming Language\x18Alan Donovan'
    parsed_avro_schema = build_schema('avro', avro_schema)
    assert deserialize_message(
        MockedMessage(avro_message, key), 'avro', parsed_avro_schema, False, 'json', '', False
    ) == (
        '{"isbn": 9780134190440, "title": "The Go Programming Language", "author": "Alan Donovan"}',
        None,
        '{"name": "Peter Parker"}',
        None,
    )

    # Test Protobuf deserialization
    protobuf_schema = (
        'CmoKDHNjaGVtYS5wcm90bxIIY29tLmJvb2siSAoEQm9vaxISCgRpc2JuGAEgASgDUgRpc2Ju'
        'EhQKBXRpdGxlGAIgASgJUgV0aXRsZRIWCgZhdXRob3IYAyABKAlSBmF1dGhvcmIGcHJvdG8z'
    )
    protobuf_message = (
        b'\x08\xe8\xba\xb2\xeb\xd1\x9c\x02\x12\x1b\x54\x68\x65\x20\x47\x6f\x20\x50\x72\x6f\x67\x72\x61\x6d\x6d\x69\x6e\x67\x20\x4c\x61\x6e\x67\x75\x61\x67\x65'
        b'\x1a\x0c\x41\x6c\x61\x6e\x20\x44\x6f\x6e\x6f\x76\x61\x6e'
    )
    parsed_protobuf_schema = build_schema('protobuf', protobuf_schema)
    assert deserialize_message(
        MockedMessage(protobuf_message, key), 'protobuf', parsed_protobuf_schema, False, 'json', '', False
    ) == (
        '{\n  "isbn": "9780134190440",\n  "title": "The Go Programming Language",\n  "author": "Alan Donovan"\n}',
        None,
        '{"name": "Peter Parker"}',
        None,
    )

    # Test invalid Avro messages
    # Empty message (returns empty string, not None)
    assert deserialize_message(MockedMessage(b'', key), 'avro', parsed_avro_schema, False, 'json', '', False) == (
        '',
        None,
        '{"name": "Peter Parker"}',
        None,
    )

    # Corrupted message (truncated)
    corrupted_avro = b'\xd0\xf5\xe4\xd6\xa3\xb9\x046The Go Programming Language'  # Missing author field
    assert deserialize_message(
        MockedMessage(corrupted_avro, key), 'avro', parsed_avro_schema, False, 'json', '', False
    ) == (
        None,
        None,
        None,
        None,
    )

    # Wrong data type (string instead of long for isbn)
    wrong_type_avro = b'\x02\x12\x1bThe Go Programming Language\x18Alan Donovan'  # Wrong encoding for isbn
    assert deserialize_message(
        MockedMessage(wrong_type_avro, key), 'avro', parsed_avro_schema, False, 'json', '', False
    ) == (
        None,
        None,
        None,
        None,
    )

    # Random bytes
    random_avro = b'\xff\xfe\xfd\xfc\xfb\xfa\xf9\xf8\xf7\xf6\xf5\xf4\xf3\xf2\xf1\xf0'
    assert deserialize_message(
        MockedMessage(random_avro, key), 'avro', parsed_avro_schema, False, 'json', '', False
    ) == (
        None,
        None,
        None,
        None,
    )

    # Completely invalid Avro message (random bytes)
    invalid_avro = b'\xff\xfe\xfd\xfc\xfb\xfa\xf9\xf8\xf7\xf6\xf5\xf4\xf3\xf2\xf1\xf0'
    assert deserialize_message(
        MockedMessage(invalid_avro, key), 'avro', parsed_avro_schema, False, 'json', '', False
    ) == (
        None,
        None,
        None,
        None,
    )

    # Avro message with wrong data types (string where long expected)
    wrong_type_avro = b'\x02\x12\x1bThe Go Programming Language\x18Alan Donovan'  # Wrong encoding for isbn
    assert deserialize_message(
        MockedMessage(wrong_type_avro, key), 'avro', parsed_avro_schema, False, 'json', '', False
    ) == (
        None,
        None,
        None,
        None,
    )

    # Test invalid Protobuf messages
    # Empty message (returns empty string, not None)
    assert deserialize_message(
        MockedMessage(b'', key), 'protobuf', parsed_protobuf_schema, False, 'json', '', False
    ) == (
        '',
        None,
        '{"name": "Peter Parker"}',
        None,
    )

    # Random bytes
    random_protobuf = b'\xff\xfe\xfd\xfc\xfb\xfa\xf9\xf8\xf7\xf6\xf5\xf4\xf3\xf2\xf1\xf0'
    assert deserialize_message(
        MockedMessage(random_protobuf, key), 'protobuf', parsed_protobuf_schema, False, 'json', '', False
    ) == (
        None,
        None,
        None,
        None,
    )

    # Completely invalid Protobuf message (random bytes)
    invalid_protobuf = b'\xff\xfe\xfd\xfc\xfb\xfa\xf9\xf8\xf7\xf6\xf5\xf4\xf3\xf2\xf1\xf0'
    assert deserialize_message(
        MockedMessage(invalid_protobuf, key), 'protobuf', parsed_protobuf_schema, False, 'json', '', False
    ) == (None, None, None, None)

    # Protobuf message with wrong field number (field 99 instead of 1)
    wrong_field_protobuf = (
        b'\x99\x01\xe8\xba\xb2\xeb\xd1\x9c\x02\x12\x1bThe Go Programming Language\x1a\x0cAlan Donovan'
    )
    assert deserialize_message(
        MockedMessage(wrong_field_protobuf, key), 'protobuf', parsed_protobuf_schema, False, 'json', '', False
    ) == (None, None, None, None)

    # Protobuf message with truncated varint
    truncated_varint_protobuf = b'\x08\xff\xff\xff\xff\xff\xff\xff\xff\xff'  # Incomplete varint
    assert deserialize_message(
        MockedMessage(truncated_varint_protobuf, key), 'protobuf', parsed_protobuf_schema, False, 'json', '', False
    ) == (None, None, None, None)


def test_strict_avro_validation():
    """Test that Avro deserialization fails when not all bytes are consumed."""
    key = b'{"name": "Peter Parker"}'

    # Test case 1: Simple primitive string schema with extra bytes
    # A primitive string in Avro is encoded as: varint length + UTF-8 bytes
    # An empty string is just: 0x00 (zero length)
    # If we have 0x00 followed by extra bytes (e.g., magic byte + 4 bytes + stuff),
    # the string decoder will read the empty string but leave bytes unconsumed
    string_schema = '"string"'
    parsed_string_schema = build_schema('avro', string_schema)

    # Message: 0x00 (empty string) + 0x00 (magic byte) + 4 bytes + some random data
    # The Avro string decoder will only consume the first 0x00, leaving the rest
    message_with_extra_bytes = b'\x00\x00\x00\x00\x01\x5e\x12\x34\x56\x78'

    # This should now fail because not all bytes are consumed
    result = deserialize_message(
        MockedMessage(message_with_extra_bytes, key), 'avro', parsed_string_schema, False, 'json', '', False
    )
    assert result == (None, None, None, None), "Expected deserialization to fail due to unconsumed bytes"

    # Test case 2: Avro message with trailing garbage bytes after valid data
    avro_schema = (
        '{"type": "record", "name": "Book", "namespace": "com.book", '
        '"fields": [{"name": "isbn", "type": "long"}, {"name": "title", "type": "string"}, '
        '{"name": "author", "type": "string"}]}'
    )
    parsed_avro_schema = build_schema('avro', avro_schema)

    # Valid Avro message + trailing garbage
    valid_avro_message = b'\xd0\xf5\xe4\xd6\xa3\xb9\x046The Go Programming Language\x18Alan Donovan'
    message_with_trailing_bytes = valid_avro_message + b'\xff\xfe\xfd\xfc'

    # This should now fail because of the trailing bytes
    result = deserialize_message(
        MockedMessage(message_with_trailing_bytes, key), 'avro', parsed_avro_schema, False, 'json', '', False
    )
    assert result == (None, None, None, None), "Expected deserialization to fail due to trailing bytes"

    # Test case 3: Simple int schema with extra bytes
    int_schema = '"int"'
    parsed_int_schema = build_schema('avro', int_schema)

    # Message: 0x02 (int value 1) + extra bytes
    message_int_with_extra = b'\x02\xde\xad\xbe\xef'

    result = deserialize_message(
        MockedMessage(message_int_with_extra, key), 'avro', parsed_int_schema, False, 'json', '', False
    )
    assert result == (None, None, None, None), "Expected deserialization to fail due to unconsumed bytes"

    # Test case 4: Verify that valid messages still work
    valid_string_message = b'\x0aHello'  # Length 5 (encoded as 0x0a = 10/2 = 5) + "Hello"
    result = deserialize_message(
        MockedMessage(valid_string_message, key), 'avro', parsed_string_schema, False, 'json', '', False
    )
    assert result[0] == '"Hello"', "Expected valid string message to deserialize correctly"
    assert result[1] is None

    valid_int_message = b'\x02'  # int value 1
    result = deserialize_message(
        MockedMessage(valid_int_message, key), 'avro', parsed_int_schema, False, 'json', '', False
    )
    assert result[0] == '1', "Expected valid int message to deserialize correctly"


def test_strict_protobuf_validation():
    """Test that Protobuf deserialization fails when not all bytes are consumed."""
    key = b'{"name": "Peter Parker"}'

    # Build the same Book schema used in other tests
    protobuf_schema = (
        'CmoKDHNjaGVtYS5wcm90bxIIY29tLmJvb2siSAoEQm9vaxISCgRpc2JuGAEgASgDUgRpc2Ju'
        'EhQKBXRpdGxlGAIgASgJUgV0aXRsZRIWCgZhdXRob3IYAyABKAlSBmF1dGhvcmIGcHJvdG8z'
    )
    parsed_protobuf_schema = build_schema('protobuf', protobuf_schema)

    # Test case 1: Valid Protobuf message with trailing garbage bytes
    valid_protobuf_message = (
        b'\x08\xe8\xba\xb2\xeb\xd1\x9c\x02\x12\x1b\x54\x68\x65\x20\x47\x6f\x20\x50\x72\x6f\x67\x72\x61\x6d\x6d\x69\x6e\x67\x20\x4c\x61\x6e\x67\x75\x61\x67\x65'
        b'\x1a\x0c\x41\x6c\x61\x6e\x20\x44\x6f\x6e\x6f\x76\x61\x6e'
    )
    message_with_trailing_bytes = valid_protobuf_message + b'\xff\xfe\xfd\xfc'

    # This should now fail because of the trailing bytes
    result = deserialize_message(
        MockedMessage(message_with_trailing_bytes, key), 'protobuf', parsed_protobuf_schema, False, 'json', '', False
    )
    assert result == (None, None, None, None), "Expected deserialization to fail due to trailing bytes"

    # Test case 2: Message with extra fields that aren't in the schema
    # Protobuf will parse this but leave bytes unconsumed if there are truly extra bytes beyond valid fields
    # Adding a completely invalid trailing byte sequence
    message_with_invalid_trailer = valid_protobuf_message + b'\x00\x00\x00\x01\x5e'

    result = deserialize_message(
        MockedMessage(message_with_invalid_trailer, key),
        'protobuf',
        parsed_protobuf_schema,
        False,
        'json',
        '',
        False,
    )
    assert result == (None, None, None, None), "Expected deserialization to fail due to unconsumed bytes"

    # Test case 3: Verify that valid messages still work
    result = deserialize_message(
        MockedMessage(valid_protobuf_message, key), 'protobuf', parsed_protobuf_schema, False, 'json', '', False
    )
    assert result[0] is not None, "Expected valid protobuf message to deserialize correctly"
    assert 'The Go Programming Language' in result[0]


def test_schema_registry_explicit_configuration():
    """Test that explicit schema registry configuration is enforced."""
    key = b'{"name": "Peter Parker"}'

    # Test Avro with value_uses_schema_registry=True
    avro_schema = (
        '{"type": "record", "name": "Book", "namespace": "com.book", '
        '"fields": [{"name": "isbn", "type": "long"}, {"name": "title", "type": "string"}, '
        '{"name": "author", "type": "string"}]}'
    )
    parsed_avro_schema = build_schema('avro', avro_schema)

    # Valid Avro message WITHOUT schema registry format
    avro_message_no_sr = b'\xd0\xf5\xe4\xd6\xa3\xb9\x046The Go Programming Language\x18Alan Donovan'

    # When uses_schema_registry=False, this should work
    result = deserialize_message(
        MockedMessage(avro_message_no_sr, key), 'avro', parsed_avro_schema, False, 'json', '', False
    )
    assert result[0] is not None, "Should succeed when uses_schema_registry=False"
    assert result[1] is None, "Should have no schema ID"

    # When uses_schema_registry=True, this should fail (missing magic byte and schema ID)
    result = deserialize_message(
        MockedMessage(avro_message_no_sr, key), 'avro', parsed_avro_schema, True, 'json', '', False
    )
    assert result == (None, None, None, None), "Should fail when uses_schema_registry=True"

    # Valid Avro message WITH schema registry format (schema ID 350 = 0x015E)
    avro_message_with_sr = (
        b'\x00\x00\x00\x01\x5e\xd0\xf5\xe4\xd6\xa3\xb9\x046The Go Programming Language\x18Alan Donovan'
    )

    # When uses_schema_registry=True, this should work
    result = deserialize_message(
        MockedMessage(avro_message_with_sr, key), 'avro', parsed_avro_schema, True, 'json', '', False
    )
    assert result[0] is not None, "Should succeed when uses_schema_registry=True"
    assert result[1] == 350, "Should extract schema ID 350"
    assert 'The Go Programming Language' in result[0]

    # Test with wrong magic byte
    wrong_magic_byte = b'\x01\x00\x00\x01\x5e\xd0\xf5\xe4\xd6\xa3\xb9\x046The Go Programming Language\x18Alan Donovan'
    result = deserialize_message(
        MockedMessage(wrong_magic_byte, key), 'avro', parsed_avro_schema, True, 'json', '', False
    )
    assert result == (None, None, None, None), "Should fail with wrong magic byte"

    # Test with message too short (less than 5 bytes)
    too_short = b'\x00\x00\x01'
    result = deserialize_message(MockedMessage(too_short, key), 'avro', parsed_avro_schema, True, 'json', '', False)
    assert result == (None, None, None, None), "Should fail when message too short for SR format"

    # Test Protobuf with value_uses_schema_registry=True
    protobuf_schema = (
        'CmoKDHNjaGVtYS5wcm90bxIIY29tLmJvb2siSAoEQm9vaxISCgRpc2JuGAEgASgDUgRpc2Ju'
        'EhQKBXRpdGxlGAIgASgJUgV0aXRsZRIWCgZhdXRob3IYAyABKAlSBmF1dGhvcmIGcHJvdG8z'
    )
    parsed_protobuf_schema = build_schema('protobuf', protobuf_schema)

    # Valid Protobuf message WITHOUT schema registry format
    protobuf_message_no_sr = (
        b'\x08\xe8\xba\xb2\xeb\xd1\x9c\x02\x12\x1b\x54\x68\x65\x20\x47\x6f\x20\x50\x72\x6f\x67\x72\x61\x6d\x6d\x69\x6e\x67\x20\x4c\x61\x6e\x67\x75\x61\x67\x65'
        b'\x1a\x0c\x41\x6c\x61\x6e\x20\x44\x6f\x6e\x6f\x76\x61\x6e'
    )

    # When uses_schema_registry=False, this should work
    result = deserialize_message(
        MockedMessage(protobuf_message_no_sr, key), 'protobuf', parsed_protobuf_schema, False, 'json', '', False
    )
    assert result[0] is not None, "Protobuf should succeed when uses_schema_registry=False"
    assert result[1] is None, "Should have no schema ID"

    # When uses_schema_registry=True, this should fail
    result = deserialize_message(
        MockedMessage(protobuf_message_no_sr, key), 'protobuf', parsed_protobuf_schema, True, 'json', '', False
    )
    assert result == (None, None, None, None), "Protobuf should fail when uses_schema_registry=True but no SR format"

    # Valid Protobuf message WITH schema registry format
    protobuf_message_with_sr = (
        b'\x00\x00\x00\x01\x5e'
        b'\x08\xe8\xba\xb2\xeb\xd1\x9c\x02\x12\x1b\x54\x68\x65\x20\x47\x6f\x20\x50\x72\x6f\x67\x72\x61\x6d\x6d\x69\x6e\x67\x20\x4c\x61\x6e\x67\x75\x61\x67\x65'
        b'\x1a\x0c\x41\x6c\x61\x6e\x20\x44\x6f\x6e\x6f\x76\x61\x6e'
    )

    # When uses_schema_registry=True, this should work
    result = deserialize_message(
        MockedMessage(protobuf_message_with_sr, key),
        'protobuf',
        parsed_protobuf_schema,
        True,
        'json',
        '',
        False,
    )
    assert result[0] is not None, "Protobuf should succeed when uses_schema_registry=True with SR format"
    assert result[1] == 350, "Should extract schema ID 350"
    assert 'The Go Programming Language' in result[0]

    # Test key_uses_schema_registry=True
    # When key has no schema registry format but key_uses_schema_registry=True, key decoding should fail
    # but value should still succeed
    result = deserialize_message(
        MockedMessage(avro_message_no_sr, key), 'avro', parsed_avro_schema, False, 'json', '', True
    )
    # Value should succeed, but key should fail (returning None for key fields)
    assert result[0] is not None, "Value should succeed"
    assert result[2] is None, "Key should fail when key_uses_schema_registry=True but no SR format"
    assert result[3] is None, "Key schema ID should be None when key fails"


def mocked_time():
    return 400


@mock.patch('datadog_checks.kafka_consumer.kafka_consumer.time', mocked_time)
@pytest.mark.parametrize(
    'messages, value_format, value_schema, persistent_cache_read_content, '
    'expected_persistent_cache_writes, expected_logs',
    [
        pytest.param(
            [
                MockedMessage(
                    b'{"name": "Peter Parker", "age": 18, "transaction_amount": 123, "currency": "dollar"}',
                    b'{"name": "Peter Parker"}',
                    12,
                ),
                MockedMessage(
                    b'{"name": "Bruce Banner", "age": 45, "transaction_amount": 456, "currency": "dollar"}',
                    b'',
                    13,
                ),
                None,
            ],
            'json',
            '',
            "config_1_id,config_id_2",
            [],
            [],
            id='Does not retrieve messages a second time',
        ),
        pytest.param(
            [
                MockedMessage(
                    b'{"name": "Peter Parker", "age": 18, "transaction_amount": 123, "currency": "dollar"}',
                    b'{"name": "Peter Parker"}',
                    12,
                ),
                MockedMessage(
                    b'{"name": "Bruce Banner", "age": 45, "transaction_amount": 456, "currency": "dollar"}',
                    b'',
                    13,
                ),
                None,
            ],
            'json',
            '',
            "",
            ["config_1_id"],
            [
                {
                    'timestamp': 400,
                    'technology': 'kafka',
                    'cluster': 'cluster_id',
                    'config_id': 'config_1_id',
                    'topic': 'topic1',
                    'partition': '0',
                    'offset': '12',
                    'feature': 'data_streams_messages',
                    'message_value': '{"name": "Peter Parker", "age": 18, \
"transaction_amount": 123, "currency": "dollar"}',
                    'message_key': '{"name": "Peter Parker"}',
                },
                {
                    'timestamp': 400,
                    'technology': 'kafka',
                    'cluster': 'cluster_id',
                    'config_id': 'config_1_id',
                    'topic': 'topic1',
                    'partition': '0',
                    'offset': '13',
                    'feature': 'data_streams_messages',
                    'message_value': '{"name": "Bruce Banner", "age": 45, \
"transaction_amount": 456, "currency": "dollar"}',
                },
                {
                    'timestamp': 400,
                    'technology': 'kafka',
                    'cluster': 'cluster_id',
                    'config_id': 'config_1_id',
                    'topic': 'topic1',
                    'message': 'No more messages to retrieve',
                    'live_messages_error': 'No more messages to retrieve',
                    'feature': 'data_streams_messages',
                },
            ],
            id='Retrieves messages from Kafka',
        ),
        # This is the serialized Protobuf representing:
        # syntax = "proto3";
        # package com.book;
        # message Book {
        #     int64 isbn = 1;
        #     string title = 2;
        #     string author = 3;
        # }
        pytest.param(
            [
                MockedMessage(
                    b'\x08\xe8\xba\xb2\xeb\xd1\x9c\x02\x12\x1b\x54\x68\x65\x20\x47\x6f\x20\x50\x72\x6f\x67\x72\x61\x6d\x6d\x69\x6e\x67\x20\x4c\x61\x6e\x67\x75\x61\x67\x65\x1a\x0c\x41\x6c\x61\x6e\x20\x44\x6f\x6e\x6f\x76\x61\x6e',
                    b'{"name": "Peter Parker"}',
                    12,
                ),
                None,
            ],
            'protobuf',
            'CmoKDHNjaGVtYS5wcm90bxIIY29tLmJvb2siSAoEQm9vaxISCgRpc2JuGAEgASgDUgRpc2JuEhQKBXRpdGxlGAIgASgJUgV0aXRsZRIWCgZhdXRob3IYAyABKAlSBmF1dGhvcmIGcHJvdG8z',
            "",
            ["config_1_id"],
            [
                {
                    'timestamp': 400,
                    'technology': 'kafka',
                    'cluster': 'cluster_id',
                    'config_id': 'config_1_id',
                    'topic': 'topic1',
                    'partition': '0',
                    'offset': '12',
                    'feature': 'data_streams_messages',
                    'message_value': (
                        '{\n  "isbn": "9780134190440",\n  "title": "The Go Programming Language",\n  '
                        '"author": "Alan Donovan"\n}'
                    ),
                    'message_key': '{"name": "Peter Parker"}',
                },
                {
                    'timestamp': 400,
                    'technology': 'kafka',
                    'cluster': 'cluster_id',
                    'config_id': 'config_1_id',
                    'topic': 'topic1',
                    'message': 'No more messages to retrieve',
                    'live_messages_error': 'No more messages to retrieve',
                    'feature': 'data_streams_messages',
                },
            ],
            id='Retrieves Protobuf messages from Kafka',
        ),
        pytest.param(
            [
                MockedMessage(
                    b'\xd0\xf5\xe4\xd6\xa3\xb9\x046The Go Programming Language\x18Alan Donovan',
                    b'{"name": "Peter Parker"}',
                    12,
                ),
                None,
            ],
            'avro',
            (
                '{"type": "record", "name": "Book", "namespace": "com.book", '
                '"fields": [{"name": "isbn", "type": "long"}, {"name": "title", "type": "string"}, '
                '{"name": "author", "type": "string"}]}'
            ),
            "",
            ["config_1_id"],
            [
                {
                    'timestamp': 400,
                    'technology': 'kafka',
                    'cluster': 'cluster_id',
                    'config_id': 'config_1_id',
                    'topic': 'topic1',
                    'partition': '0',
                    'offset': '12',
                    'feature': 'data_streams_messages',
                    'message_value': (
                        '{"isbn": 9780134190440, "title": "The Go Programming Language", "author": "Alan Donovan"}'
                    ),
                    'message_key': '{"name": "Peter Parker"}',
                },
                {
                    'timestamp': 400,
                    'technology': 'kafka',
                    'cluster': 'cluster_id',
                    'config_id': 'config_1_id',
                    'topic': 'topic1',
                    'message': 'No more messages to retrieve',
                    'live_messages_error': 'No more messages to retrieve',
                    'feature': 'data_streams_messages',
                },
            ],
            id='Retrieves Avro messages from Kafka',
        ),
    ],
)
def test_data_streams_messages(
    messages,
    value_format,
    value_schema,
    persistent_cache_read_content,
    expected_persistent_cache_writes,
    expected_logs,
    kafka_instance,
    dd_run_check,
    check,
):
    (
        kafka_instance.update(
            {
                'consumer_groups': {},
                'monitor_unlisted_consumer_groups': True,
                'live_messages_configs': [
                    {
                        'kafka': {
                            'cluster': 'cluster_id',
                            'topic': 'topic1',
                            'partition': 0,
                            'start_offset': 0,
                            'n_messages': 3,
                            'value_format': value_format,
                            'value_schema': value_schema,
                            'key_format': 'json',
                            'key_schema': '',
                        },
                        'id': 'config_1_id',
                    }
                ],
            }
        ),
    )
    mock_client = seed_mock_client(cluster_id="Cluster_id")
    mock_client.get_next_message.side_effect = messages
    check = check(kafka_instance)
    check.client = mock_client

    def mocked_read_persistent_cache(key):
        if key == DATA_STREAMS_MESSAGES_CACHE_KEY:
            return persistent_cache_read_content
        return ""

    check.read_persistent_cache = mock.Mock(side_effect=mocked_read_persistent_cache)
    check.write_persistent_cache = mock.Mock()
    check.send_log = mock.Mock()

    dd_run_check(check)

    for content in expected_persistent_cache_writes:
        assert mock.call(DATA_STREAMS_MESSAGES_CACHE_KEY, content) in check.write_persistent_cache.mock_calls
    assert [mock.call(log) for log in expected_logs] == check.send_log.mock_calls


def test_build_schema():
    """Test build_schema function with various valid and invalid schemas."""

    # Test JSON format (should return None)
    assert build_schema('json', '') is None
    assert build_schema('json', '{"some": "json"}') is None
    assert build_schema('json', None) is None

    # Test valid Avro schema
    valid_avro_schema = (
        '{"type": "record", "name": "Book", "namespace": "com.book", '
        '"fields": [{"name": "isbn", "type": "long"}, {"name": "title", "type": "string"}, '
        '{"name": "author", "type": "string"}]}'
    )
    avro_result = build_schema('avro', valid_avro_schema)
    assert avro_result is not None
    assert avro_result['type'] == 'record'
    assert avro_result['name'] == 'Book'
    assert avro_result['namespace'] == 'com.book'

    # Test valid Protobuf schema
    valid_protobuf_schema = (
        'CmoKDHNjaGVtYS5wcm90bxIIY29tLmJvb2siSAoEQm9vaxISCgRpc2JuGAEgASgDUgRpc2Ju'
        'EhQKBXRpdGxlGAIgASgJUgV0aXRsZRIWCgZhdXRob3IYAyABKAlSBmF1dGhvcmIGcHJvdG8z'
    )
    protobuf_result = build_schema('protobuf', valid_protobuf_schema)
    assert protobuf_result is not None
    # The result should be a protobuf message class instance
    assert hasattr(protobuf_result, 'isbn')
    assert hasattr(protobuf_result, 'title')
    assert hasattr(protobuf_result, 'author')

    # Test unknown format
    assert build_schema('unknown_format', 'some_schema') is None


def test_build_schema_error_cases():
    """Test build_schema with various error cases and edge cases."""

    # Test Avro error cases
    # Invalid JSON syntax
    with pytest.raises(json.JSONDecodeError):
        build_schema('avro', '{"invalid": json}')

    # Valid JSON but incomplete schema (fastavro is permissive)
    result = build_schema('avro', '{"type": "record"}')  # Missing name and fields
    assert result is not None

    # Test Protobuf error cases
    # Invalid base64 encoding
    with pytest.raises(base64.binascii.Error):
        build_schema('protobuf', 'invalid-base64!')

    # Valid base64 but invalid protobuf schema
    # This is a valid base64 string that doesn't represent a valid FileDescriptorSet
    with pytest.raises(DecodeError):  # Will be a protobuf DecodeError
        build_schema('protobuf', 'SGVsbG8gV29ybGQ=')  # "Hello World" in base64

    # Valid base64 but empty schema (should cause IndexError)
    # Create a minimal but empty FileDescriptorSet
    empty_descriptor = descriptor_pb2.FileDescriptorSet()
    empty_descriptor_bytes = empty_descriptor.SerializeToString()
    empty_descriptor_b64 = base64.b64encode(empty_descriptor_bytes).decode('utf-8')

    with pytest.raises(IndexError):  # Should fail when trying to access file[0]
        build_schema('protobuf', empty_descriptor_b64)


def test_build_schema_none_handling():
    """Test that build_schema functions properly handle None values."""

    # Test Avro schema with None - should raise TypeError
    with pytest.raises(TypeError):
        build_avro_schema(None)

    # Test Protobuf schema with None - should raise TypeError or base64.binascii.Error
    with pytest.raises((TypeError, base64.binascii.Error)):
        build_protobuf_schema(None)


def test_count_consumer_contexts(check, kafka_instance):
    kafka_consumer_check = check(kafka_instance)
    consumer_offsets = {
        'consumer_group1': {('topic1', 'partition0'): 1, ('topic1', 'partition1'): 2},  # 2 contexts
        'consumer_group2': {('topic2', 'partition0'): 3},  # 1 context
    }
    assert kafka_consumer_check.count_consumer_contexts(consumer_offsets) == 3


def test_consumer_group_state_fetched_once_per_group(check, kafka_instance, dd_run_check, aggregator):
    mock_client = seed_mock_client()
    # Set up two partitions for same topic to check multiple contexts in same consumer group
    partitions = ['partition1', 'partition2']
    offsets = [2, 3]
    topic = 'topic1'
    consumer_group = 'consumer_group1'
    mock_client.consumer_get_cluster_id_and_list_topics.return_value = (
        'cluster_id',
        [(topic, partitions)],
    )
    mock_client.get_partitions_for_topic.return_value = partitions
    consumer_group_offsets = [(topic, p, o) for p, o in zip(partitions, offsets)]
    mock_client.list_consumer_group_offsets.return_value = [
        (
            consumer_group,
            consumer_group_offsets,
        )
    ]
    kafka_instance["collect_consumer_group_state"] = True
    kafka_consumer_check = check(kafka_instance)
    kafka_consumer_check.client = mock_client

    dd_run_check(kafka_consumer_check)

    # Check that the consumer group state is fetched only once
    assert mock_client.describe_consumer_group.call_count == 1

    # Check that both partitions include the state tag
    for metric in ("kafka.consumer_offset", "kafka.consumer_lag"):
        for partition in partitions:
            aggregator.assert_metric_has_tags(
                metric,
                tags=[f'partition:{partition}', 'consumer_group_state:STABLE'],
            )
