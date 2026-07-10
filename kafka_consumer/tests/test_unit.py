# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import base64
import json
import logging
import marshal
from collections import defaultdict
from contextlib import nullcontext as does_not_raise

import mock
import pytest

from datadog_checks.kafka_consumer import KafkaCheck
from datadog_checks.kafka_consumer.client import KafkaClient

pytestmark = [pytest.mark.unit]


def encode_broker_timestamps(cache):
    """Encode a broker_timestamps dict the way the check persists it (marshal+base64)."""
    return base64.b64encode(marshal.dumps(cache)).decode('ascii')


def written_broker_timestamps(check):
    """Decode the broker_timestamps blob the check wrote to its persistent cache (marshal+base64)."""
    return marshal.loads(base64.b64decode(check.write_persistent_cache.call_args[0][1]))


def fake_get_partition_offsets(partitions, offset=-1):
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
    client.get_partition_offsets = fake_get_partition_offsets
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


def test_check_clears_cache_on_partial_reset(kafka_instance, check, dd_run_check):
    # When the highwater drops, all cached entries are cleared — including those below the new
    # highwater that belong to the previous topic generation and would otherwise poison interpolation.
    kafka_instance['data_streams_enabled'] = True
    kafka_instance['consumer_groups'] = {'consumer_group1': {'topic1': [0]}}
    kafka_consumer_check = check(kafka_instance)

    mock_client = seed_mock_client()
    mock_client.list_consumer_group_offsets.return_value = [("consumer_group1", [("topic1", 0, 30)])]
    mock_client.get_partition_offsets = lambda partitions, offset=-1: [("topic1", 0, 100)]
    kafka_consumer_check.client = mock_client

    # Cache has entries below (5, 50) and above (200) the new highwater of 100 — all must be cleared.
    initial_cache = {"topic1_0": {5: 1.0, 50: 2.0, 200: 3.0}}
    kafka_consumer_check.read_persistent_cache = mock.Mock(return_value=encode_broker_timestamps(initial_cache))
    kafka_consumer_check.write_persistent_cache = mock.Mock()

    dd_run_check(kafka_consumer_check)

    written = written_broker_timestamps(kafka_consumer_check)
    timestamps = written["topic1_0"]
    assert len(timestamps) == 1
    assert 100 in timestamps


def test_max_history_scales_with_partition_count(check, kafka_instance):
    kafka_consumer_check = check(kafka_instance)  # default timestamp_history_size = 1000
    assert kafka_consumer_check._max_history(0) == 1000
    assert kafka_consumer_check._max_history(1) == 1000
    assert kafka_consumer_check._max_history(6000) == 1000  # 6M / 6000 = 1000 (breakeven)
    assert kafka_consumer_check._max_history(60000) == 100  # 6M / 60000
    assert kafka_consumer_check._max_history(6_000_000) == 2  # floored at 2


def test_add_broker_timestamps_caps_total_by_budget(check, kafka_instance, monkeypatch):
    import datadog_checks.kafka_consumer.kafka_consumer as kc

    monkeypatch.setattr(kc, 'MAX_TIMESTAMP_ENTRIES', 1000)
    kafka_consumer_check = check(kafka_instance)
    # 100 partitions against a 1000-entry budget -> per-partition cap of 10.
    highwater_offsets = {("topic1", p): 500 for p in range(100)}
    broker_timestamps = defaultdict(dict)
    broker_timestamps["topic1_0"] = {i: float(i) for i in range(60)}

    kafka_consumer_check._add_broker_timestamps(broker_timestamps, highwater_offsets)

    assert len(broker_timestamps["topic1_0"]) <= 10


@pytest.mark.parametrize(
    'timestamp_history_size, initial_cache, highwater_offset, '
    'highwater_time, consumer_offset, expected_cache_size, expected_lag',
    [
        pytest.param(
            4,
            {"topic1_0": {10: 1000.0, 20: 2000.0, 30: 3000.0}},
            40,
            4000.0,
            25,
            2,
            1500.0,
            id='consumer interpolated between compacted endpoints',
        ),
        pytest.param(
            4,
            {"topic1_0": {10: 1000.0, 20: 2000.0, 30: 3000.0}},
            40,
            4000.0,
            10,
            2,
            3000.0,
            id='consumer at oldest endpoint, preserved by VW as minimum',
        ),
        pytest.param(
            4,
            {"topic1_0": {10: 1000.0, 20: 2000.0, 30: 3000.0}},
            40,
            4000.0,
            40,
            2,
            0.0,
            id='consumer at highwater, zero lag, newest endpoint preserved by VW',
        ),
        pytest.param(
            6,
            {"topic1_0": {10: 1000.0, 20: 2000.0, 30: 3000.0, 40: 4000.0, 50: 5000.0}},
            60,
            6000.0,
            35,
            3,
            2500.0,
            id='larger history size compacts to 3 entries, consumer interpolated correctly',
        ),
    ],
)
def test_check_compacts_timestamps_and_preserves_lag_accuracy(
    kafka_instance,
    check,
    dd_run_check,
    aggregator,
    timestamp_history_size,
    initial_cache,
    highwater_offset,
    highwater_time,
    consumer_offset,
    expected_cache_size,
    expected_lag,
):
    # Collinear samples (equal spacing in both offset and time) so VW can drop any interior
    # point without distorting the offset/timestamp curve or the interpolated lag.
    kafka_instance['data_streams_enabled'] = True
    kafka_instance['timestamp_history_size'] = timestamp_history_size
    kafka_instance['consumer_groups'] = {'consumer_group1': {'topic1': [0]}}
    kafka_consumer_check = check(kafka_instance)

    mock_client = seed_mock_client()
    mock_client.get_partitions_for_topic.return_value = [0]
    mock_client.list_consumer_group_offsets.return_value = [("consumer_group1", [("topic1", 0, consumer_offset)])]
    mock_client.get_partition_offsets = lambda partitions, offset=-1: [("topic1", 0, highwater_offset)]
    kafka_consumer_check.client = mock_client

    kafka_consumer_check.read_persistent_cache = mock.Mock(return_value=encode_broker_timestamps(initial_cache))
    kafka_consumer_check.write_persistent_cache = mock.Mock()

    with mock.patch('datadog_checks.kafka_consumer.kafka_consumer.time', return_value=highwater_time):
        dd_run_check(kafka_consumer_check)

    written = written_broker_timestamps(kafka_consumer_check)
    assert len(written["topic1_0"]) == expected_cache_size
    aggregator.assert_metric("kafka.estimated_consumer_lag", value=expected_lag, count=1)


def test_check_prunes_timestamps_below_earliest_consumer_offset(kafka_instance, check, dd_run_check):
    # During check(), _add_broker_timestamps prunes cached entries below the earliest consumer
    # offset (keeping one anchor), so only relevant samples are retained.
    kafka_instance['data_streams_enabled'] = True
    kafka_instance['timestamp_history_size'] = 4
    kafka_instance['consumer_groups'] = {'consumer_group1': {'topic1': [0]}}
    kafka_consumer_check = check(kafka_instance)

    mock_client = seed_mock_client()
    mock_client.list_consumer_group_offsets.return_value = [("consumer_group1", [("topic1", 0, 25)])]
    mock_client.get_partition_offsets = lambda partitions, offset=-1: [("topic1", 0, 40)]
    kafka_consumer_check.client = mock_client

    # Pre-seed the cache with 3 entries. Adding the new highwater at 40 fills the 4-entry
    # budget and triggers compaction+pruning with the earliest consumer offset (25) as the floor.
    initial_cache = {"topic1_0": {10: 1.0, 20: 2.0, 30: 3.0}}
    kafka_consumer_check.read_persistent_cache = mock.Mock(return_value=encode_broker_timestamps(initial_cache))
    kafka_consumer_check.write_persistent_cache = mock.Mock()

    dd_run_check(kafka_consumer_check)

    written = written_broker_timestamps(kafka_consumer_check)
    timestamps = written["topic1_0"]
    assert 10 not in timestamps  # pruned: below the anchor; no consumer will interpolate here
    assert 20 in timestamps  # anchor: largest sample at/below consumer floor of 25
    assert 40 in timestamps  # new highwater sample


def test_report_lag_in_time_interpolates_consumer_between_samples(kafka_instance, check, aggregator):
    # A consumer whose offset falls between two cached broker samples is interpolated correctly.
    kafka_instance['data_streams_enabled'] = True
    check = check(kafka_instance)
    mock_client = seed_mock_client()
    mock_client.get_partitions_for_topic.return_value = [0]
    check.client = mock_client

    consumer_offsets = {"consumer_group1": {("topic1", 0): 25}}
    highwater_offsets = {("topic1", 0): 40}
    broker_timestamps = {"topic1_0": {20: 2000.0, 30: 3000.0, 40: 4000.0}}

    check.report_consumer_offsets_and_lag(
        consumer_offsets,
        highwater_offsets,
        float('inf'),
        broker_timestamps,
        "cluster_id",
    )

    # Consumer at 25 interpolates between offset 20 (t=2000) and offset 30 (t=3000) → t=2500.
    # Producer at highwater=40 (t=4000); lag = 4000 - 2500 = 1500.
    aggregator.assert_metric("kafka.estimated_consumer_lag", value=1500.0, count=1)


def test_report_lag_in_time_no_lag_reported_immediately_after_reset(kafka_instance, check, aggregator):
    # After a partition reset the entire cache is cleared, leaving only the new highwater entry.
    # A single cached sample is insufficient for interpolation, so no lag is reported.
    kafka_instance['data_streams_enabled'] = True
    check = check(kafka_instance)
    mock_client = seed_mock_client()
    mock_client.get_partitions_for_topic.return_value = [0]
    check.client = mock_client

    consumer_offsets = {"consumer_group1": {("topic1", 0): 25}}
    highwater_offsets = {("topic1", 0): 40}
    broker_timestamps = {"topic1_0": {40: 4000.0}}  # only one entry — reset just happened

    check.report_consumer_offsets_and_lag(
        consumer_offsets,
        highwater_offsets,
        float('inf'),
        broker_timestamps,
        "cluster_id",
    )

    aggregator.assert_metric("kafka.estimated_consumer_lag", count=0)


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


def test_report_lag_in_time_caps_left_extrapolation_without_low_watermark(kafka_instance, check, aggregator):
    # With cluster monitoring off there is no low watermark, so the consumer offset is used as-is.
    # When it predates every cached sample, the lag is still bounded by the left-extrapolation cap
    # (cache window + LAG_EXTRAPOLATION_LIMIT_SECONDS) rather than growing without limit.
    kafka_instance['data_streams_enabled'] = True
    check = check(kafka_instance)
    mock_client = seed_mock_client()
    mock_client.get_partitions_for_topic.return_value = [0]
    check.client = mock_client

    consumer_offsets = {"consumer_group1": {("topic1", 0): 0}}
    highwater_offsets = {("topic1", 0): 1100}
    broker_timestamps = {"topic1_0": {1000: 10000.0, 1100: 10100.0}}

    check.report_consumer_offsets_and_lag(
        consumer_offsets,
        highwater_offsets,
        float('inf'),
        broker_timestamps,
        "cluster_id",
    )

    # Unclamped extrapolation would give consumer_timestamp 9000 (lag 1100). The cap raises it to
    # oldest_sample - 600 = 9400, so lag = 10100 - 9400 = 700 (cache window 100 + 600s budget).
    aggregator.assert_metric("kafka.estimated_consumer_lag", value=700.0, count=1)


def test_check_prunes_floor_uses_minimum_offset_across_groups(kafka_instance, check, dd_run_check):
    # The pruning floor for a partition is the minimum committed offset across all consumer groups,
    # not just one. Using the wrong (higher) floor would prune entries that are still needed.
    kafka_instance['data_streams_enabled'] = True
    kafka_instance['timestamp_history_size'] = 4
    kafka_instance['consumer_groups'] = {
        'group1': {'topic1': [0]},
        'group2': {'topic1': [0]},
    }
    kafka_consumer_check = check(kafka_instance)

    mock_client = seed_mock_client()
    # group1 at offset 25, group2 at offset 5 — correct floor is min(25, 5) = 5.
    mock_client.list_consumer_group_offsets.return_value = [
        ("group1", [("topic1", 0, 25)]),
        ("group2", [("topic1", 0, 5)]),
    ]
    mock_client.get_partition_offsets = lambda partitions, offset=-1: [("topic1", 0, 40)]
    kafka_consumer_check.client = mock_client

    # With floor=5 (correct min), nothing below 5 exists, so no pruning; VW keeps {10, 40}.
    # With floor=25 (wrong, single-group), entry 10 would be pruned; VW keeps {20, 40} instead.
    initial_cache = {"topic1_0": {10: 1.0, 20: 2.0, 30: 3.0}}
    kafka_consumer_check.read_persistent_cache = mock.Mock(return_value=encode_broker_timestamps(initial_cache))
    kafka_consumer_check.write_persistent_cache = mock.Mock()

    dd_run_check(kafka_consumer_check)

    written = written_broker_timestamps(kafka_consumer_check)
    timestamps = written["topic1_0"]
    assert 10 in timestamps  # floor=5 means nothing below 10 exists, so 10 is the oldest endpoint
    assert 40 in timestamps


def test_check_prunes_anchor_at_floor_boundary(kafka_instance, check, dd_run_check):
    # The pruning floor uses strict less-than, so an entry whose offset equals the floor is not
    # counted as "below" — the anchor is the largest entry strictly below the floor.
    # With floor=30 and cache {10,20,30}: below={10,20}, anchor=20, entry 10 pruned.
    # (If <= were used instead, anchor would be 30 and entry 20 would be pruned.)
    kafka_instance['data_streams_enabled'] = True
    kafka_instance['timestamp_history_size'] = 4
    kafka_instance['consumer_groups'] = {'consumer_group1': {'topic1': [0]}}
    kafka_consumer_check = check(kafka_instance)

    mock_client = seed_mock_client()
    mock_client.list_consumer_group_offsets.return_value = [("consumer_group1", [("topic1", 0, 30)])]
    mock_client.get_partition_offsets = lambda partitions, offset=-1: [("topic1", 0, 40)]
    kafka_consumer_check.client = mock_client

    initial_cache = {"topic1_0": {10: 1.0, 20: 2.0, 30: 3.0}}
    kafka_consumer_check.read_persistent_cache = mock.Mock(return_value=encode_broker_timestamps(initial_cache))
    kafka_consumer_check.write_persistent_cache = mock.Mock()

    dd_run_check(kafka_consumer_check)

    written = written_broker_timestamps(kafka_consumer_check)
    timestamps = written["topic1_0"]
    assert 10 not in timestamps  # pruned: below the anchor
    assert 20 in timestamps  # correct anchor (strict-< floor means 30 is not below 30)
    assert 40 in timestamps  # new highwater


def test_check_keeps_sole_entry_below_floor_as_anchor(kafka_instance, check, dd_run_check):
    # When only one cached entry is below the floor it is the anchor and must be kept —
    # removing it would leave the consumer with no lower bound for interpolation.
    kafka_instance['data_streams_enabled'] = True
    kafka_instance['timestamp_history_size'] = 3
    kafka_instance['consumer_groups'] = {'consumer_group1': {'topic1': [0]}}
    kafka_consumer_check = check(kafka_instance)

    mock_client = seed_mock_client()
    mock_client.list_consumer_group_offsets.return_value = [("consumer_group1", [("topic1", 0, 25)])]
    mock_client.get_partition_offsets = lambda partitions, offset=-1: [("topic1", 0, 40)]
    kafka_consumer_check.client = mock_client

    initial_cache = {"topic1_0": {20: 2.0, 30: 3.0}}
    kafka_consumer_check.read_persistent_cache = mock.Mock(return_value=encode_broker_timestamps(initial_cache))
    kafka_consumer_check.write_persistent_cache = mock.Mock()

    dd_run_check(kafka_consumer_check)

    written = written_broker_timestamps(kafka_consumer_check)
    timestamps = written["topic1_0"]
    assert 20 in timestamps  # sole entry below floor — kept as the anchor
    assert 40 in timestamps  # new highwater


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


def _offset_future(offset):
    """Build a list_offsets future whose result() returns an object with the given offset."""
    future = mock.MagicMock()
    future.result.return_value = mock.MagicMock(offset=offset)
    return future


def _raising_future(exc):
    """Build a list_offsets future whose result() raises the given exception."""
    future = mock.MagicMock()
    future.result.side_effect = exc
    return future


def test_get_partition_offsets_skips_unqueryable_partitions():
    """A partition whose list_offsets future raises is skipped; healthy partitions are still returned."""
    from confluent_kafka import KafkaException, TopicPartition

    config = mock.MagicMock()
    config._request_timeout = 5

    client = KafkaClient(config, logging.getLogger(__name__))

    futures = {
        TopicPartition(topic="healthy_topic", partition=0): _offset_future(100),
        TopicPartition(topic="bad_topic", partition=0): _raising_future(KafkaException("UNKNOWN_TOPIC_OR_PART")),
    }
    client._kafka_client = mock.MagicMock()
    client._kafka_client.list_offsets.return_value = futures

    results = client.get_partition_offsets([("healthy_topic", 0), ("bad_topic", 0)])

    # (a) no exception escaped, (b) the healthy partition's offset is returned,
    # (c) the unqueryable partition is skipped.
    assert results == [("healthy_topic", 0, 100)]


def test_get_partition_offsets_skips_partition_on_non_kafka_error():
    """A non-Kafka error on one partition's future is skipped, not propagated, so the loop survives."""
    from confluent_kafka import TopicPartition

    config = mock.MagicMock()
    config._request_timeout = 5

    client = KafkaClient(config, logging.getLogger(__name__))

    futures = {
        TopicPartition(topic="healthy_topic", partition=0): _offset_future(100),
        TopicPartition(topic="bad_topic", partition=0): _raising_future(RuntimeError("unexpected")),
    }
    client._kafka_client = mock.MagicMock()
    client._kafka_client.list_offsets.return_value = futures

    results = client.get_partition_offsets([("healthy_topic", 0), ("bad_topic", 0)])

    assert results == [("healthy_topic", 0, 100)]


def test_get_partition_offsets_raises_when_list_offsets_request_fails():
    """A request/broker-level list_offsets failure propagates, aborting highwater collection."""
    config = mock.MagicMock()
    config._request_timeout = 5

    client = KafkaClient(config, logging.getLogger(__name__))
    client._kafka_client = mock.MagicMock()
    client._kafka_client.list_offsets.side_effect = RuntimeError("connection dropped")

    with pytest.raises(RuntimeError):
        client.get_partition_offsets([("topic_a", 0)])


def test_get_partition_offsets_empty_partitions_returns_empty_without_request():
    """No partitions means no list_offsets request is issued and an empty result is returned."""
    config = mock.MagicMock()
    config._request_timeout = 5

    client = KafkaClient(config, logging.getLogger(__name__))
    client._kafka_client = mock.MagicMock()

    results = client.get_partition_offsets([])

    assert results == []
    assert client._kafka_client.list_offsets.call_count == 0


def test_get_partition_offsets_returns_all_healthy_partitions():
    """When every list_offsets future succeeds, all partition offsets are returned."""
    from confluent_kafka import IsolationLevel, TopicPartition

    config = mock.MagicMock()
    config._request_timeout = 5

    client = KafkaClient(config, logging.getLogger(__name__))

    futures = {
        TopicPartition(topic="topic_a", partition=0): _offset_future(42),
        TopicPartition(topic="topic_b", partition=1): _offset_future(7),
    }
    client._kafka_client = mock.MagicMock()
    client._kafka_client.list_offsets.return_value = futures

    results = client.get_partition_offsets([("topic_a", 0), ("topic_b", 1)])

    assert sorted(results) == [("topic_a", 0, 42), ("topic_b", 1, 7)]
    assert client._kafka_client.list_offsets.call_count == 1
    # READ_UNCOMMITTED is load-bearing: READ_COMMITTED would return the LSO, not the true high watermark.
    assert client._kafka_client.list_offsets.call_args.kwargs["isolation_level"] == IsolationLevel.READ_UNCOMMITTED
    assert client._kafka_client.list_offsets.call_args.kwargs["request_timeout"] == 5
