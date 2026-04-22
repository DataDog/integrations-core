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


def _is_gcp_auth_available():
    try:
        import google.auth  # noqa: F401

        return True
    except ImportError:
        return False


def fake_consumer_offsets_for_times(partitions, offset=-1):
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
        pytest.param(
            {'sasl_oauth_token_provider': {'method': 'aws_msk_iam'}},
            does_not_raise(),
            mock_client,
            id="valid AWS MSK IAM config",
        ),
        pytest.param(
            {'sasl_oauth_token_provider': {'method': 'gcp_cloud_managed_kafka'}},
            does_not_raise(),
            mock_client,
            id="valid GCP Cloud Managed Kafka config",
            marks=pytest.mark.skipif(not _is_gcp_auth_available(), reason="google-auth not installed"),
        ),
        pytest.param(
            {
                'sasl_oauth_token_provider': {
                    'method': 'gcp_cloud_managed_kafka',
                    'gcp_credentials_file': '/path/to/sa.json',
                }
            },
            does_not_raise(),
            mock_client,
            id="valid GCP Cloud Managed Kafka config with credentials file",
            marks=pytest.mark.skipif(not _is_gcp_auth_available(), reason="google-auth not installed"),
        ),
        pytest.param(
            {'sasl_oauth_token_provider': {'method': 'invalid_method'}},
            pytest.raises(
                Exception,
                match="Invalid method 'invalid_method' for sasl_oauth_token_provider. "
                "Must be 'aws_msk_iam', 'gcp_cloud_managed_kafka', or 'oidc'",
            ),
            None,
            id="invalid method",
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
        value=0,
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


def test_add_broker_timestamps_purges_stale_offsets_on_reset(kafka_instance, check):
    # When the highwater offset goes backwards (topic recreated / retention
    # wipe / offset reset), cached (offset, timestamp) pairs with offsets
    # above the new highwater are stale and must be purged — otherwise they
    # poison interpolation and pin estimated_consumer_lag to a wall-clock
    # offset equal to how long ago the reset happened.
    check = check(kafka_instance)
    broker_timestamps = {"topic1_0": {1_000_000: 100.0, 999_000: 99.0}}
    check._add_broker_timestamps(broker_timestamps, {("topic1", 0): 170})

    timestamps = broker_timestamps["topic1_0"]
    assert 1_000_000 not in timestamps
    assert 999_000 not in timestamps
    assert 170 in timestamps


def test_add_broker_timestamps_evicts_by_oldest_timestamp(kafka_instance, check):
    # Eviction must drop the entry with the oldest timestamp, not the smallest
    # offset. Evicting by min(offset) would discard fresh post-reset entries
    # and keep poisonous ones.
    kafka_instance['timestamp_history_size'] = 2
    check = check(kafka_instance)
    broker_timestamps = {"topic1_0": {500: 50.0, 400: 999.0}}
    check._add_broker_timestamps(broker_timestamps, {("topic1", 0): 600})

    timestamps = broker_timestamps["topic1_0"]
    assert 500 not in timestamps  # oldest by timestamp
    assert 400 in timestamps
    assert 600 in timestamps


def test_count_consumer_contexts(check, kafka_instance):
    kafka_consumer_check = check(kafka_instance)
    consumer_offsets = {
        'consumer_group1': {('topic1', 'partition0'): 1, ('topic1', 'partition1'): 2},  # 2 contexts
        'consumer_group2': {('topic2', 'partition0'): 3},  # 1 context
    }
    assert kafka_consumer_check.count_consumer_contexts(consumer_offsets) == 3


@pytest.mark.parametrize(
    'oauth_config, expected_auth_keys',
    [
        pytest.param(
            {'method': 'aws_msk_iam'},
            ['oauth_cb'],  # AWS MSK IAM uses oauth_cb callback, not sasl.oauthbearer.method
            id="AWS MSK IAM authentication",
        ),
        pytest.param(
            {'method': 'gcp_cloud_managed_kafka'},
            ['oauth_cb'],  # GCP Cloud Managed Kafka uses oauth_cb callback
            id="GCP Cloud Managed Kafka authentication",
            marks=pytest.mark.skipif(not _is_gcp_auth_available(), reason="google-auth not installed"),
        ),
        pytest.param(
            {'method': 'oidc', 'url': 'http://fake.url', 'client_id': 'test_id', 'client_secret': 'test_secret'},
            {
                'sasl.oauthbearer.method': 'oidc',
                'sasl.oauthbearer.client.id': 'test_id',
                'sasl.oauthbearer.token.endpoint.url': 'http://fake.url',
                'sasl.oauthbearer.client.secret': 'test_secret',
            },
            id="OIDC authentication",
        ),
    ],
)
def test_oauth_authentication_config(oauth_config, expected_auth_keys, kafka_instance, check):
    """Test that OAuth authentication configuration is correctly set for both AWS MSK IAM and OIDC."""
    kafka_instance.update(
        {
            'monitor_unlisted_consumer_groups': True,
            'security_protocol': 'SASL_SSL',
            'sasl_mechanism': 'OAUTHBEARER',
            'sasl_oauth_token_provider': oauth_config,
        }
    )
    kafka_consumer_check = check(kafka_instance)
    auth_config = kafka_consumer_check.client._KafkaClient__get_authentication_config()

    # Verify security protocol is set
    assert auth_config['security.protocol'] == 'sasl_ssl'
    assert auth_config['sasl.mechanism'] == 'OAUTHBEARER'

    # Verify OAuth-specific configuration
    if isinstance(expected_auth_keys, dict):
        # OIDC: verify exact key-value pairs
        for key, value in expected_auth_keys.items():
            assert auth_config[key] == value
    else:
        # AWS MSK IAM: verify oauth_cb callback is present and callable
        for key in expected_auth_keys:
            assert key in auth_config
            if key == 'oauth_cb':
                assert callable(auth_config[key])


@pytest.mark.parametrize(
    'oauth_config, mock_boto3_region, expected_region, should_succeed',
    [
        pytest.param(
            {'method': 'aws_msk_iam', 'aws_region': 'us-west-2'},
            None,  # Explicitly configured region should be used regardless of boto3
            'us-west-2',
            True,
            id="explicit region in config",
        ),
        pytest.param(
            {'method': 'aws_msk_iam'},
            'eu-central-1',  # Region detected by boto3
            'eu-central-1',
            True,
            id="region from boto3 auto-detection",
        ),
        pytest.param(
            {'method': 'aws_msk_iam'},
            None,  # No region configured or detected
            None,
            False,
            id="no region available - should fail",
        ),
    ],
)
def test_aws_msk_iam_region_handling(
    oauth_config, mock_boto3_region, expected_region, should_succeed, kafka_instance, check
):
    """Test that AWS MSK IAM authentication properly handles region configuration."""
    kafka_instance.update(
        {
            'monitor_unlisted_consumer_groups': True,
            'security_protocol': 'SASL_SSL',
            'sasl_mechanism': 'OAUTHBEARER',
            'sasl_oauth_token_provider': oauth_config,
        }
    )

    kafka_consumer_check = check(kafka_instance)

    # Get the OAuth callback from the authentication config
    auth_config = kafka_consumer_check.client._KafkaClient__get_authentication_config()
    assert 'oauth_cb' in auth_config
    oauth_callback = auth_config['oauth_cb']

    # Mock boto3 session and MSKAuthTokenProvider
    with mock.patch('datadog_checks.kafka_consumer.client.boto3') as mock_boto3_module:
        mock_session = mock.Mock()
        mock_session.region_name = mock_boto3_region
        mock_boto3_module.session.Session.return_value = mock_session

        with mock.patch('datadog_checks.kafka_consumer.client.MSKAuthTokenProvider') as mock_auth_provider:
            mock_auth_provider.generate_auth_token.return_value = ('fake_token', 900000)

            if should_succeed:
                # Should successfully generate token
                token, expiry = oauth_callback(None)
                assert token == 'fake_token'
                assert expiry == 900  # 900000ms / 1000 = 900s

                # Verify the correct region was used
                mock_auth_provider.generate_auth_token.assert_called_once_with(expected_region)
            else:
                # Should fail with clear error message about missing region
                with pytest.raises(Exception, match="AWS region could not be determined"):
                    oauth_callback(None)


@pytest.mark.skipif(not _is_gcp_auth_available(), reason="google-auth not installed")
@pytest.mark.parametrize(
    'oauth_config, use_credentials_file',
    [
        pytest.param(
            {'method': 'gcp_cloud_managed_kafka'},
            False,
            id="GCP default credentials",
        ),
        pytest.param(
            {'method': 'gcp_cloud_managed_kafka', 'gcp_credentials_file': '/path/to/sa.json'},
            True,
            id="GCP explicit credentials file",
        ),
    ],
)
def test_gcp_cloud_managed_kafka_token_handling(oauth_config, use_credentials_file, kafka_instance, check):
    """Test that GCP Cloud Managed Kafka authentication properly generates tokens."""
    kafka_instance.update(
        {
            'monitor_unlisted_consumer_groups': True,
            'security_protocol': 'SASL_SSL',
            'sasl_mechanism': 'OAUTHBEARER',
            'sasl_oauth_token_provider': oauth_config,
        }
    )

    kafka_consumer_check = check(kafka_instance)

    auth_config = kafka_consumer_check.client._KafkaClient__get_authentication_config()
    assert 'oauth_cb' in auth_config
    oauth_callback = auth_config['oauth_cb']

    import base64
    import json
    from datetime import datetime, timezone

    mock_credentials = mock.Mock()
    mock_credentials.token = 'fake_gcp_token'
    mock_credentials.expiry = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    mock_credentials.service_account_email = 'sa@test.iam.gserviceaccount.com'

    with mock.patch('datadog_checks.kafka_consumer.client.google.auth') as mock_google_auth:
        mock_google_auth.default.return_value = (mock_credentials, 'test-project')
        mock_google_auth.load_credentials_from_file.return_value = (mock_credentials, 'test-project')
        mock_google_auth.transport.requests.Request.return_value = mock.Mock()

        token, expiry = oauth_callback(None)

        parts = token.split('.')
        assert len(parts) == 3

        def _b64decode(s):
            return base64.urlsafe_b64decode(s + '=' * (-len(s) % 4))

        header = json.loads(_b64decode(parts[0]))
        claims = json.loads(_b64decode(parts[1]))
        raw_token = _b64decode(parts[2]).decode()

        assert header == {'typ': 'JWT', 'alg': 'GOOG_OAUTH2_TOKEN'}
        assert claims['iss'] == 'Google'
        assert claims['sub'] == 'sa@test.iam.gserviceaccount.com'
        assert claims['exp'] == mock_credentials.expiry.timestamp()
        assert raw_token == 'fake_gcp_token'
        assert expiry == mock_credentials.expiry.timestamp()

        if use_credentials_file:
            mock_google_auth.load_credentials_from_file.assert_called_once_with(
                '/path/to/sa.json', scopes=['https://www.googleapis.com/auth/cloud-platform']
            )
            mock_google_auth.default.assert_not_called()
        else:
            mock_google_auth.default.assert_called_once_with(scopes=['https://www.googleapis.com/auth/cloud-platform'])
            mock_google_auth.load_credentials_from_file.assert_not_called()

        mock_credentials.refresh.assert_called_once()


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


def test_kafka_cluster_id_override(check, kafka_instance, dd_run_check, aggregator):
    """When kafka_cluster_id_override is set, metrics use the override and include original_kafka_cluster_id."""
    mock_client = seed_mock_client(cluster_id="auto-detected-id")
    kafka_instance["kafka_cluster_id_override"] = "my-override-id"
    kafka_consumer_check = check(kafka_instance)
    kafka_consumer_check.client = mock_client

    dd_run_check(kafka_consumer_check)

    expected_override_tags = ['kafka_cluster_id:my-override-id', 'original_kafka_cluster_id:auto-detected-id']
    for metric_name in ("kafka.broker_offset", "kafka.consumer_offset", "kafka.consumer_lag"):
        for metric in aggregator.metrics(metric_name):
            for tag in expected_override_tags:
                assert tag in metric.tags, f"{tag} not in {metric.tags} for {metric_name}"
