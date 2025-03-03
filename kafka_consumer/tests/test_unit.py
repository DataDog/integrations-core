# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import logging
from contextlib import nullcontext as does_not_raise

import mock
import pytest

from datadog_checks.kafka_consumer import KafkaCheck
from datadog_checks.kafka_consumer.client import KafkaClient
from datadog_checks.kafka_consumer.kafka_consumer import _get_interpolated_timestamp

pytestmark = [pytest.mark.unit]


def fake_consumer_offsets_for_times(partitions):
    """In our testing environment the offset is 80 for all partitions and topics."""

    return [(t, p, 80) for t, p in partitions]


def seed_mock_client():
    """Set some common defaults for the mock client to kafka."""
    client = mock.create_autospec(KafkaClient)
    client.list_consumer_groups.return_value = ["consumer_group1"]
    client.get_partitions_for_topic.return_value = ['partition1']
    client.list_consumer_group_offsets.return_value = [("consumer_group1", [("topic1", "partition1", 2)])]
    client.describe_consumer_groups.return_value = ('consumer_group', 'STABLE')
    client.consumer_get_cluster_id_and_list_topics.return_value = (
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
