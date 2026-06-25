# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json
import logging
from contextlib import nullcontext as does_not_raise

import mock
import pytest

from datadog_checks.kafka_consumer import KafkaCheck
from datadog_checks.kafka_consumer.client import KafkaClient
from datadog_checks.kafka_consumer.kafka_consumer import _get_interpolated_timestamp, _visvalingam_whyatt

pytestmark = [pytest.mark.unit]


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
            {'sasl_oauth_token_provider': {'method': 'invalid_method'}},
            pytest.raises(
                Exception,
                match="Invalid method 'invalid_method' for sasl_oauth_token_provider. Must be 'aws_msk_iam' or 'oidc'",
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


def test_get_interpolated_timestamp_caps_left_extrapolation():
    # Slope is 1 timestamp unit per offset; offset 0 is 1100 offsets before the oldest sample.
    # Unclamped this would extrapolate to 9000, but we cap it at oldest_sample - 600 = 9400.
    assert _get_interpolated_timestamp({1000: 10000, 1100: 10100}, 0) == 9400
    # A modest left-extrapolation that stays within the 600s budget is left untouched.
    assert _get_interpolated_timestamp({1000: 10000, 1100: 10100}, 900) == 9900
    # Interpolation between known offsets is never affected by the cap.
    assert _get_interpolated_timestamp({1000: 10000, 1100: 10100}, 1050) == 10050


def test_visvalingam_whyatt_keeps_endpoints_and_drops_collinear():
    # A perfectly linear series: every interior point is redundant, so any of them can go.
    timestamps = {0: 0.0, 10: 10.0, 20: 20.0, 30: 30.0, 40: 40.0}
    _visvalingam_whyatt(timestamps, 3)
    assert len(timestamps) == 3
    assert 0 in timestamps and 40 in timestamps  # endpoints are always preserved


def test_visvalingam_whyatt_keeps_rate_changes():
    # Constant rate up to offset 20, then a sharp acceleration: 10 is redundant, the kink at 20 isn't.
    timestamps = {0: 0.0, 10: 10.0, 20: 20.0, 30: 100.0}
    _visvalingam_whyatt(timestamps, 3)
    assert set(timestamps) == {0, 20, 30}


def test_visvalingam_whyatt_noop_when_within_target():
    timestamps = {0: 0.0, 10: 10.0}
    _visvalingam_whyatt(timestamps, 5)
    assert timestamps == {0: 0.0, 10: 10.0}


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


def test_add_broker_timestamps_compacts_when_full(kafka_instance, check):
    # When the cache reaches capacity it is compacted down to half its size, keeping the oldest and
    # newest samples and dropping the points that least affect the offset/timestamp curve.
    kafka_instance['timestamp_history_size'] = 4
    check = check(kafka_instance)
    broker_timestamps = {"topic1_0": {10: 1.0, 20: 2.0, 30: 3.0}}
    check._add_broker_timestamps(broker_timestamps, {("topic1", 0): 40})

    timestamps = broker_timestamps["topic1_0"]
    assert len(timestamps) == 2
    assert 10 in timestamps  # oldest endpoint preserved
    assert 40 in timestamps  # newest endpoint preserved


def test_add_broker_timestamps_prunes_below_earliest_consumer_offset(kafka_instance, check):
    # At compaction time, samples older than the earliest consumer offset are useless (no consumer
    # will ever interpolate there), so they are pruned — keeping one anchor at/below that offset.
    kafka_instance['timestamp_history_size'] = 4
    check = check(kafka_instance)
    broker_timestamps = {"topic1_0": {10: 1.0, 20: 2.0, 30: 3.0}}
    check._add_broker_timestamps(broker_timestamps, {("topic1", 0): 40}, {("topic1", 0): 25})

    timestamps = broker_timestamps["topic1_0"]
    assert 10 not in timestamps  # useless: below the earliest consumer offset and not the anchor
    assert 20 in timestamps  # anchor: largest sample at/below the earliest consumer offset
    assert 40 in timestamps


def test_report_lag_in_time_uses_low_watermark(kafka_instance, check, aggregator):
    # A consumer behind the low watermark can't read the out-of-retention messages between its
    # committed offset and the low watermark, so lag-in-time is interpolated from the low watermark.
    kafka_instance['data_streams_enabled'] = True
    check = check(kafka_instance)
    mock_client = seed_mock_client()
    mock_client.get_partitions_for_topic.return_value = [0]
    check.client = mock_client

    consumer_offsets = {"consumer_group1": {("topic1", 0): 5}}
    highwater_offsets = {("topic1", 0): 100}
    broker_timestamps = {"topic1_0": {50: 1000.0, 100: 1100.0}}
    low_watermark_offsets = {("topic1", 0): 50}

    check.report_consumer_offsets_and_lag(
        consumer_offsets,
        highwater_offsets,
        float('inf'),
        broker_timestamps,
        "cluster_id",
        low_watermark_offsets,
    )

    # effective offset = max(5, 50) = 50 -> consumer_timestamp 1000, producer_timestamp 1100, lag 100.
    aggregator.assert_metric("kafka.estimated_consumer_lag", value=100.0, count=1)


def test_get_low_watermark_offsets_delegates_to_client(kafka_instance, check):
    check = check(kafka_instance)
    mock_client = seed_mock_client()
    mock_client.get_topic_partitions.return_value = {"topic1": [0, 1], "__consumer_offsets": [0]}
    mock_client.get_low_watermark_offsets.return_value = {("topic1", 0): 5}
    check.client = mock_client

    result = check._get_low_watermark_offsets()

    assert result == {("topic1", 0): 5}
    # Internal topics are excluded and every non-internal partition is requested.
    assert mock_client.get_low_watermark_offsets.call_args[0][0] == {("topic1", 0), ("topic1", 1)}


def test_get_low_watermark_offsets_handles_errors(kafka_instance, check):
    check = check(kafka_instance)
    mock_client = seed_mock_client()
    mock_client.get_topic_partitions.return_value = {"topic1": [0]}
    mock_client.get_low_watermark_offsets.side_effect = Exception("boom")
    check.client = mock_client

    assert check._get_low_watermark_offsets() == {}


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


def _connection_error_events(check_instance):
    return [
        json.loads(c[0][0])
        for c in check_instance.event_platform_event.call_args_list
        if c[0][1] == 'data-streams-message' and json.loads(c[0][0]).get('config_type') == 'connection_error'
    ]


def _setup_failing_check(check, kafka_instance, dd_run_check):
    kafka_consumer_check = check(kafka_instance)
    kafka_consumer_check.client = seed_mock_client()
    kafka_consumer_check.client.request_metadata_update.side_effect = Exception('broker down')
    kafka_consumer_check.event_platform_event = mock.Mock()
    with pytest.raises(Exception, match="Unable to connect to the AdminClient"):
        dd_run_check(kafka_consumer_check)
    return kafka_consumer_check


def test_connection_error_emits_dsm_event(check, kafka_instance, dd_run_check):
    """A connection_error event is emitted when request_metadata_update fails and cluster monitoring is on."""
    kafka_instance['enable_cluster_monitoring'] = True
    kafka_consumer_check = _setup_failing_check(check, kafka_instance, dd_run_check)

    events = _connection_error_events(kafka_consumer_check)
    assert len(events) == 1
    assert events[0]['reason'] == 'broker down'
    assert events[0]['bootstrap_servers'] == kafka_instance['kafka_connect_str']
    assert 'collection_timestamp' in events[0]


def test_connection_error_includes_cluster_id_override(check, kafka_instance, dd_run_check):
    """connection_error event uses kafka_cluster_id_override when configured."""
    kafka_instance['enable_cluster_monitoring'] = True
    kafka_instance['kafka_cluster_id_override'] = 'my-cluster'
    kafka_consumer_check = _setup_failing_check(check, kafka_instance, dd_run_check)

    events = _connection_error_events(kafka_consumer_check)
    assert len(events) == 1
    assert events[0]['kafka_cluster_id'] == 'my-cluster'


def test_connection_error_not_emitted_without_cluster_monitoring(check, kafka_instance, dd_run_check):
    """No connection_error event is emitted when cluster monitoring is disabled."""
    kafka_consumer_check = _setup_failing_check(check, kafka_instance, dd_run_check)
    assert not _connection_error_events(kafka_consumer_check)


def test_connection_error_sink_failure_does_not_mask_broker_error(check, kafka_instance, dd_run_check):
    """Sink failure during connection_error emission does not mask the original AdminClient error."""
    kafka_instance['enable_cluster_monitoring'] = True
    kafka_consumer_check = check(kafka_instance)
    kafka_consumer_check.client = seed_mock_client()
    kafka_consumer_check.client.request_metadata_update.side_effect = Exception('broker down')
    kafka_consumer_check.event_platform_event = mock.Mock(side_effect=Exception('intake unavailable'))
    with pytest.raises(Exception, match="Unable to connect to the AdminClient"):
        dd_run_check(kafka_consumer_check)
