# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json
import time

import mock
import pytest

from datadog_checks.kafka_consumer.client import KafkaClient
from datadog_checks.kafka_consumer.config import KafkaConfig
from datadog_checks.kafka_consumer.connectors import (
    CONNECTOR_PLUGINS_CACHE_KEY,
    _short_class_name,
)

from .conftest import SAMPLE_CONNECTORS_RESPONSE

pytestmark = [pytest.mark.unit]


def _seed_mock_kafka_client():
    """Minimal Kafka client mock sufficient for the connector-focused tests."""
    client = mock.create_autospec(KafkaClient)
    client.consumer_get_cluster_id_and_list_topics.return_value = ('cluster-1', [])
    client.list_consumer_groups.return_value = []
    client.list_consumer_group_offsets.return_value = []
    client._cluster_metadata = None
    return client


@pytest.mark.parametrize(
    'full_class, expected',
    [
        ('org.apache.kafka.connect.mirror.MirrorSourceConnector', 'MirrorSourceConnector'),
        ('MirrorSourceConnector', 'MirrorSourceConnector'),
        ('', ''),
    ],
)
def test_short_class_name(full_class, expected):
    assert _short_class_name(full_class) == expected


def test_sensitive_keys_redacted_in_config_event(check, kafka_instance, dd_run_check):
    """Full config is captured but sensitive keys are replaced with [hidden]."""
    # Arrange
    kafka_instance['kafka_connect_url'] = 'http://localhost:8083'
    kafka_instance['enable_cluster_monitoring'] = True
    kafka_consumer_check = check(kafka_instance)
    kafka_consumer_check.client = _seed_mock_kafka_client()

    connectors_data = {
        'my-sink': {
            'info': {
                'type': 'sink',
                'config': {
                    'connector.class': 'io.confluent.SomeSink',
                    'connection.password': 'secret123',
                    'sasl.jaas.config': 'org.apache.kafka.common.security.plain.PlainLoginModule ...',
                    'tasks.max': '2',
                    'topics': 'orders',
                },
            },
            'status': {'connector': {'state': 'RUNNING'}, 'tasks': []},
        }
    }
    mock_resp = mock.MagicMock()
    mock_resp.json.return_value = connectors_data
    kafka_consumer_check._connector_collector.http = mock.MagicMock()
    kafka_consumer_check._connector_collector.http.get.return_value = mock_resp

    # Act
    with mock.patch.object(kafka_consumer_check._connector_collector, '_collect_plugins'):
        with mock.patch.object(kafka_consumer_check.metadata_collector, 'collect_all_metadata'):
            with mock.patch.object(kafka_consumer_check, 'event_platform_event') as mock_event:
                dd_run_check(kafka_consumer_check)

    # Assert
    connector_events = [
        json.loads(c.args[0])
        for c in mock_event.call_args_list
        if json.loads(c.args[0]).get('config_type') == 'connector'
    ]
    assert len(connector_events) == 1
    cfg = connector_events[0]['config']
    assert cfg['connection.password'] == '[hidden]'
    assert cfg['sasl.jaas.config'] == '[hidden]'
    assert cfg['connector.class'] == 'io.confluent.SomeSink'
    assert cfg['topics'] == 'orders'
    assert cfg['tasks.max'] == '2'


def test_emit_connector_metrics_gauges(make_collector):
    collector, check, _, _ = make_collector()
    collector._emit_connector_metrics(SAMPLE_CONNECTORS_RESPONSE, ['connect_url:http://localhost:8083'])

    emitted = {call.args[0] for call in check.gauge.call_args_list}
    assert 'connector.running' not in emitted
    assert 'connector.task.count' in emitted
    assert 'connector.tasks' in emitted
    assert 'connector.task.running' in emitted


def test_emit_connector_metrics_connector_state_tag(make_collector):
    collector, check, _, _ = make_collector()
    collector._emit_connector_metrics(SAMPLE_CONNECTORS_RESPONSE, [])

    task_count_calls = [c for c in check.gauge.call_args_list if c.args[0] == 'connector.task.count']
    source_calls = [c for c in task_count_calls if 'connector:demo-source' in c.kwargs.get('tags', [])]
    assert source_calls, "no connector.task.count for demo-source"
    assert 'connector_state:RUNNING' in source_calls[0].kwargs['tags']

    heartbeat_calls = [c for c in task_count_calls if 'connector:demo-heartbeat' in c.kwargs.get('tags', [])]
    assert heartbeat_calls, "no connector.task.count for demo-heartbeat"
    assert 'connector_state:PAUSED' in heartbeat_calls[0].kwargs['tags']


def test_task_metrics_always_collected(make_collector):
    collector, check, _, _ = make_collector()
    collector._emit_connector_metrics(SAMPLE_CONNECTORS_RESPONSE, [])
    per_task = [c for c in check.gauge.call_args_list if c.args[0] == 'connector.task.running']
    assert per_task, "expected per-task gauges to always be emitted"


def test_dedup_unchanged_content_not_reemitted(make_collector):
    collector, _, _, cache_store = make_collector()
    items = {'connector-a': '{"config":"stable"}'}

    first = collector.cache.get_events_to_send('test_key', items)
    assert 'connector-a' in first

    second = collector.cache.get_events_to_send('test_key', items)
    assert 'connector-a' not in second, "unchanged content should not re-emit within TTL"


def test_dedup_changed_content_reemitted(make_collector):
    collector, _, _, _ = make_collector()
    collector.cache.get_events_to_send('test_key', {'connector-a': '{"config":"v1"}'})
    second = collector.cache.get_events_to_send('test_key', {'connector-a': '{"config":"v2"}'})
    assert 'connector-a' in second


def test_dedup_ttl_expiry_triggers_reemit(make_collector):
    collector, _, _, cache_store = make_collector()
    items = {'connector-a': '{"config":"stable"}'}
    collector.cache.get_events_to_send('test_key', items)

    cached = json.loads(cache_store['test_key'])
    cached['connector-a']['expire_at'] = time.time() - 1
    cache_store['test_key'] = json.dumps(cached)

    third = collector.cache.get_events_to_send('test_key', items)
    assert 'connector-a' in third, "should re-emit after TTL expiry"


def test_collection_timestamp_excluded_from_hash(check, kafka_instance, dd_run_check):
    """Verify that config events with identical content don't re-emit on the next cycle."""
    # Arrange
    kafka_instance['kafka_connect_url'] = 'http://localhost:8083'
    kafka_instance['enable_cluster_monitoring'] = True
    kafka_consumer_check = check(kafka_instance)
    kafka_consumer_check.client = _seed_mock_kafka_client()

    mock_resp = mock.MagicMock()
    mock_resp.json.return_value = SAMPLE_CONNECTORS_RESPONSE
    kafka_consumer_check._connector_collector.http = mock.MagicMock()
    kafka_consumer_check._connector_collector.http.get.return_value = mock_resp

    def _connector_event_count(call_args_list):
        return sum(1 for c in call_args_list if json.loads(c.args[0]).get('config_type') == 'connector')

    # Act — two consecutive runs with identical connector data
    with mock.patch.object(kafka_consumer_check._connector_collector, '_collect_plugins'):
        with mock.patch.object(kafka_consumer_check.metadata_collector, 'collect_all_metadata'):
            with mock.patch.object(kafka_consumer_check, 'event_platform_event') as mock_event:
                dd_run_check(kafka_consumer_check)
                first_count = _connector_event_count(mock_event.call_args_list)

                dd_run_check(kafka_consumer_check)
                second_count = _connector_event_count(mock_event.call_args_list)

    # Assert — connector config events are deduplicated on the second run
    new_events = second_count - first_count
    assert second_count == first_count, f"expected no new connector events on second call, got {new_events} more"


def test_collect_returns_connected_true_on_success(make_collector):
    collector, _, _, _ = make_collector(connect_urls=['http://localhost:8083'])
    with mock.patch.object(collector, '_collect_rest'):
        result = collector.collect('cluster-1')

    assert result == {'http://localhost:8083': True}


def test_collect_returns_connected_false_on_failure(make_collector):
    collector, _, _, _ = make_collector(connect_urls=['http://localhost:8083'])
    with mock.patch.object(collector, '_collect_rest', side_effect=ConnectionError("refused")):
        result = collector.collect('cluster-1')

    assert result == {'http://localhost:8083': False}


def test_older_worker_list_response_warns_and_returns(make_collector):
    collector, check, _, _ = make_collector(connect_urls=['http://localhost:8083'])
    mock_resp = mock.MagicMock()
    mock_resp.json.return_value = ['connector-a', 'connector-b']

    collector.http.get.return_value = mock_resp

    collector._collect_rest('http://localhost:8083', 'cluster-1')

    assert check.gauge.call_count == 0
    collector.log.warning.assert_called_once()


def test_collect_rest_success_emits_metrics_and_events(make_collector):
    collector, check, _, _ = make_collector(connect_urls=['http://localhost:8083'])
    mock_resp = mock.MagicMock()
    mock_resp.json.return_value = SAMPLE_CONNECTORS_RESPONSE

    collector.http.get.return_value = mock_resp

    with mock.patch.object(collector, '_collect_plugins'):
        collector._collect_rest('http://localhost:8083', 'cluster-1')

    count_calls = [c for c in check.gauge.call_args_list if c.args[0] == 'connector.count']
    assert count_calls, "expected connector.count gauge"
    assert count_calls[0].args[1] == 2
    assert check.event_platform_event.call_count > 0


def test_collect_plugins_emits_event_on_first_call(make_collector):
    collector, check, _, _ = make_collector(connect_urls=['http://localhost:8083'])
    plugins = [{'class': 'org.apache.kafka.connect.file.FileStreamSinkConnector', 'type': 'sink', 'version': '3.3.0'}]

    mock_resp = mock.MagicMock()
    mock_resp.json.return_value = plugins

    collector.http.get.return_value = mock_resp

    collector._collect_plugins('http://localhost:8083', 'cluster-1')
    assert check.event_platform_event.call_count == 1
    payload = json.loads(check.event_platform_event.call_args[0][0])
    assert payload['config_type'] == 'connector_plugins'


def test_collect_plugins_skips_when_ttl_not_expired(make_collector, monkeypatch):
    collector, check, _, cache_store = make_collector(connect_urls=['http://localhost:8083'])

    from urllib.parse import quote

    safe_url = quote('http://localhost:8083', safe='')
    fetch_cache_key = f'{CONNECTOR_PLUGINS_CACHE_KEY}:{safe_url}'
    cache_store[fetch_cache_key] = json.dumps({'plugins': time.time() + 9999})

    collector._collect_plugins('http://localhost:8083', 'cluster-1')
    assert check.event_platform_event.call_count == 0


def test_get_items_to_fetch_returns_all_on_empty_cache(make_collector):
    collector, _, _, _ = make_collector()
    result = collector.cache.get_items_to_fetch('nonexistent_key', ['a', 'b'])
    assert result == ['a', 'b']


def test_get_items_to_fetch_skips_unexpired_items(make_collector):
    collector, _, _, cache_store = make_collector()
    future = time.time() + 9999
    cache_store['test_key'] = json.dumps({'item-a': future, 'item-b': 0})
    result = collector.cache.get_items_to_fetch('test_key', ['item-a', 'item-b'])
    assert result == ['item-b']
    assert 'item-a' not in result


def test_mark_items_fetched_writes_expiry(make_collector):
    collector, _, _, cache_store = make_collector()
    collector.cache.mark_items_fetched('test_key', ['item-a'], ttl_base=100, ttl_jitter=0)
    cached = json.loads(cache_store['test_key'])
    assert 'item-a' in cached
    assert cached['item-a'] > time.time()


def test_mark_items_fetched_evicts_oldest_when_over_max(make_collector):
    collector, _, _, cache_store = make_collector()
    existing = {f'key-{i}': time.time() + i for i in range(10)}
    cache_store['test_key'] = json.dumps(existing)
    collector.cache.mark_items_fetched('test_key', ['new-key'], ttl_base=100, ttl_jitter=0, max_cache_size=5)
    cached = json.loads(cache_store['test_key'])
    assert len(cached) <= 5
    assert 'new-key' in cached


def test_get_items_to_fetch_handles_corrupt_cache(make_collector):
    collector, _, _, cache_store = make_collector()
    cache_store['bad_key'] = 'not-valid-json'
    result = collector.cache.get_items_to_fetch('bad_key', ['item'])
    assert result == ['item']


def test_get_events_to_send_handles_corrupt_cache(make_collector):
    collector, _, _, cache_store = make_collector()
    cache_store['bad_key'] = 'not-valid-json'
    result = collector.cache.get_events_to_send('bad_key', {'item': 'content'})
    assert result == ['item']


def test_get_events_to_send_empty_items(make_collector):
    collector, _, _, _ = make_collector()
    result = collector.cache.get_events_to_send('some_key', {})
    assert result == []


def _make_kafka_config(**kwargs):
    return KafkaConfig({}, kwargs, mock.MagicMock())


def test_get_tags_without_cluster_id():
    config = _make_kafka_config(tags=['env:prod'])
    assert config._get_tags() == ['env:prod']


def test_get_tags_with_cluster_id():
    config = _make_kafka_config()
    assert 'kafka_cluster_id:cluster-abc' in config._get_tags('cluster-abc')


def test_get_tags_with_cluster_id_override():
    config = _make_kafka_config(kafka_cluster_id_override='override-id')
    config._auto_detected_cluster_id = 'real-id'
    assert 'original_kafka_cluster_id:real-id' in config._get_tags('override-id')


def test_original_cluster_id_field_when_override_set():
    config = _make_kafka_config(kafka_cluster_id_override='override-id')
    config._auto_detected_cluster_id = 'real-id'
    assert config._original_cluster_id_field() == {'original_kafka_cluster_id': 'real-id'}


def test_original_cluster_id_field_when_no_override():
    config = _make_kafka_config()
    assert config._original_cluster_id_field() == {}


def test_configure_http_sets_basic_auth(make_collector):
    collector, _, config, _ = make_collector()
    config._kafka_connect_username = 'user'
    config._kafka_connect_password = 'pass'
    config._kafka_connect_tls_verify = True
    config._kafka_connect_tls_ca_cert = None
    config._kafka_connect_tls_cert = None
    config._kafka_connect_tls_key = None

    collector._configure_http()
    assert collector._http_kwargs['auth'] == ('user', 'pass')


@pytest.mark.parametrize(
    "config_overrides,attr,expected",
    [
        ({"_kafka_connect_tls_verify": False}, "verify", False),
        ({"_kafka_connect_tls_ca_cert": "/path/to/ca.crt"}, "verify", "/path/to/ca.crt"),
        (
            {"_kafka_connect_tls_cert": "/path/to/cert.pem", "_kafka_connect_tls_key": "/path/to/key.pem"},
            "cert",
            ("/path/to/cert.pem", "/path/to/key.pem"),
        ),
        ({"_kafka_connect_tls_cert": "/path/to/cert.pem"}, "cert", "/path/to/cert.pem"),
    ],
    ids=["tls_verify_false", "tls_ca_cert", "client_cert_and_key", "cert_only"],
)
def test_configure_http_tls(make_collector, config_overrides, attr, expected):
    collector, _, config, _ = make_collector()
    config._kafka_connect_username = None
    config._kafka_connect_password = None
    config._kafka_connect_tls_verify = True
    config._kafka_connect_tls_ca_cert = None
    config._kafka_connect_tls_cert = None
    config._kafka_connect_tls_key = None
    for k, v in config_overrides.items():
        setattr(config, k, v)

    collector._configure_http()
    assert collector._http_kwargs[attr] == expected


def test_collect_oauth_failure_returns_endpoints_as_false(make_collector):
    collector, _, config, _ = make_collector(connect_urls=['http://localhost:8083'])
    config._kafka_connect_oauth_token_provider = {'url': 'http://auth', 'client_id': 'id', 'client_secret': 'sec'}

    with mock.patch.object(collector, '_refresh_oauth_token', side_effect=Exception("auth failed")):
        result = collector.collect('cluster-1')

    assert result == {'http://localhost:8083': False}


def test_collect_multi_endpoint_partial_failure(make_collector):
    """One endpoint failing does not prevent the other from being collected."""
    collector, _, config, _ = make_collector(connect_urls=['http://ok:8083', 'http://bad:8083'])
    config._kafka_connect_oauth_token_provider = None

    with mock.patch.object(
        collector,
        '_collect_rest',
        side_effect=[None, ConnectionError("refused")],
    ):
        result = collector.collect('cluster-1')

    assert result == {'http://ok:8083': True, 'http://bad:8083': False}


def test_refresh_oauth_token_stores_token(make_collector):
    collector, _, config, _ = make_collector(connect_urls=['http://localhost:8083'])
    config._kafka_connect_oauth_token_provider = {
        'url': 'http://auth/token',
        'client_id': 'client',
        'client_secret': 'secret',
    }

    with mock.patch.object(collector, '_fetch_oidc_token', return_value=('mytoken', time.time() + 300)):
        collector._refresh_oauth_token()

    assert collector._oauth_token == 'mytoken'
    assert collector._get_request_kwargs()['extra_headers']['Authorization'] == 'Bearer mytoken'


def test_refresh_oauth_token_skips_when_still_valid(make_collector):
    collector, _, config, _ = make_collector(connect_urls=['http://localhost:8083'])
    config._kafka_connect_oauth_token_provider = {
        'url': 'http://auth/token',
        'client_id': 'client',
        'client_secret': 'secret',
    }

    collector._oauth_token = 'existing-token'
    collector._oauth_token_expiry = time.time() + 3600

    with mock.patch.object(collector, '_fetch_oidc_token') as mock_fetch:
        collector._refresh_oauth_token()

    mock_fetch.assert_not_called()


def test_refresh_oauth_token_no_op_when_no_provider(make_collector):
    collector, _, config, _ = make_collector()
    config._kafka_connect_oauth_token_provider = None

    with mock.patch.object(collector, '_fetch_oidc_token') as mock_fetch:
        collector._refresh_oauth_token()

    mock_fetch.assert_not_called()


def test_refresh_oauth_token_sets_custom_headers(make_collector):
    collector, _, config, _ = make_collector(connect_urls=['http://localhost:8083'])
    config._kafka_connect_oauth_token_provider = {
        'url': 'http://auth/token',
        'client_id': 'client',
        'client_secret': 'secret',
        'custom_headers': {'X-Tenant': 'tenant-1'},
    }

    with mock.patch.object(collector, '_fetch_oidc_token', return_value=('mytoken', time.time() + 300)):
        collector._refresh_oauth_token()

    extra = collector._get_request_kwargs()['extra_headers']
    assert extra.get('X-Tenant') == 'tenant-1'


def test_fetch_oidc_token_returns_token_and_expiry(make_collector):
    collector, check, _, _ = make_collector()

    oauth_config = {
        'url': 'http://auth/token',
        'client_id': 'cid',
        'client_secret': 'csec',
    }

    mock_resp = mock.MagicMock()
    mock_resp.json.return_value = {'access_token': 'tok123', 'expires_in': 600}
    check.http.post.return_value = mock_resp

    token, expires_at = collector._fetch_oidc_token(oauth_config)
    assert token == 'tok123'
    assert expires_at > time.time()
    assert expires_at < time.time() + 700


def test_fetch_oidc_token_uses_scope_and_ca_cert(make_collector):
    collector, check, _, _ = make_collector()

    oauth_config = {
        'url': 'http://auth/token',
        'client_id': 'cid',
        'client_secret': 'csec',
        'scope': 'openid',
        'tls_ca_cert': '/path/to/ca.crt',
    }

    mock_resp = mock.MagicMock()
    mock_resp.json.return_value = {'access_token': 'tok456', 'expires_in': 300}
    check.http.post.return_value = mock_resp

    token, _ = collector._fetch_oidc_token(oauth_config)
    assert token == 'tok456'
    call_kwargs = check.http.post.call_args.kwargs
    assert call_kwargs['verify'] == '/path/to/ca.crt'
    assert call_kwargs['data']['scope'] == 'openid'


def test_mark_items_fetched_uses_defaults_when_none(make_collector):
    collector, _, _, cache_store = make_collector()
    collector.cache.mark_items_fetched('test_key', ['item-a'])
    cached = json.loads(cache_store['test_key'])
    assert 'item-a' in cached
    assert cached['item-a'] > time.time()


def test_mark_items_fetched_handles_corrupt_cache(make_collector):
    collector, _, _, cache_store = make_collector()
    cache_store['bad_key'] = 'not-valid-json'
    collector.cache.mark_items_fetched('bad_key', ['item'], ttl_base=100, ttl_jitter=0)
    cached = json.loads(cache_store['bad_key'])
    assert 'item' in cached


def test_mark_items_fetched_handles_write_failure(make_collector):
    collector, check, _, _ = make_collector()
    check.write_persistent_cache.side_effect = Exception("disk full")
    collector.cache.mark_items_fetched('test_key', ['item'], ttl_base=100, ttl_jitter=0)
    collector.log.debug.assert_called()


def test_get_events_to_send_handles_write_failure(make_collector):
    collector, check, _, _ = make_collector()
    check.write_persistent_cache.side_effect = Exception("disk full")
    result = collector.cache.get_events_to_send('test_key', {'item': 'content'})
    assert result == ['item']
    collector.log.debug.assert_called()
