# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json
import time

import mock
import pytest
import requests

from datadog_checks.kafka_consumer.connectors import (
    KafkaConnectCollector,
    _short_class_name,
)

pytestmark = [pytest.mark.unit]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_collector(
    connect_urls=None,
    collect_task_metrics=False,
    cache_store=None,
):
    """Build a KafkaConnectCollector backed by MagicMock check/config/log."""
    check = mock.MagicMock()
    check.OK = 0
    check.WARNING = 1
    check.CRITICAL = 2

    if cache_store is None:
        cache_store = {}

    def read_cache(key):
        return cache_store.get(key, '')

    def write_cache(key, value):
        cache_store[key] = value

    check.read_persistent_cache.side_effect = read_cache
    check.write_persistent_cache.side_effect = write_cache

    config = mock.MagicMock()
    config._kafka_connect_urls = connect_urls or []
    config._kafka_connect_confluent_cloud_environment_id = None
    config._kafka_connect_confluent_cloud_cluster_id = None
    config._kafka_connect_confluent_cloud_url = 'https://api.confluent.cloud'
    config._kafka_connect_username = None
    config._kafka_connect_password = None
    config._kafka_connect_tls_verify = True
    config._kafka_connect_tls_ca_cert = None
    config._kafka_connect_tls_cert = None
    config._kafka_connect_tls_key = None
    config._kafka_connect_oauth_token_provider = None
    config._kafka_connect_collect_task_metrics = collect_task_metrics
    config._kafka_configs_refresh_interval = 3600
    config._request_timeout = 10
    config._custom_tags = []
    config._kafka_cluster_id_override = None
    config._auto_detected_cluster_id = ''

    log = mock.MagicMock()
    return KafkaConnectCollector(check, config, log), check, config, cache_store


SAMPLE_CONNECTORS_RESPONSE = {
    'demo-source': {
        'info': {
            'type': 'source',
            'config': {
                'connector.class': 'org.apache.kafka.connect.mirror.MirrorSourceConnector',
                'tasks.max': '2',
                'topics': 'demo-orders',
            },
        },
        'status': {
            'connector': {'state': 'RUNNING'},
            'tasks': [
                {'id': 0, 'state': 'RUNNING', 'worker_id': 'connect:8083'},
                {'id': 1, 'state': 'RUNNING', 'worker_id': 'connect:8083'},
            ],
        },
    },
    'demo-heartbeat': {
        'info': {
            'type': 'source',
            'config': {'connector.class': 'org.apache.kafka.connect.mirror.MirrorHeartbeatConnector'},
        },
        'status': {
            'connector': {'state': 'PAUSED'},
            'tasks': [{'id': 0, 'state': 'PAUSED', 'worker_id': 'connect:8083'}],
        },
    },
}


# ---------------------------------------------------------------------------
# _short_class_name
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# _truncate_connector_config
# ---------------------------------------------------------------------------


def test_truncate_connector_config_important_keys_first():
    collector, _, _, _ = make_collector()
    cfg = {
        'connector.class': 'io.confluent.SomeSink',
        'tasks.max': '3',
        'random.key.a': 'va',
        'random.key.b': 'vb',
    }
    result = collector._truncate_connector_config(cfg)
    keys = list(result.keys())
    assert keys.index('connector.class') < keys.index('random.key.a')
    assert 'connector.class' in result
    assert 'tasks.max' in result


def test_truncate_connector_config_cap_at_30():
    collector, _, _, _ = make_collector()
    cfg = {f'key.{i}': str(i) for i in range(50)}
    cfg['connector.class'] = 'SomeClass'
    result = collector._truncate_connector_config(cfg)
    assert len(result) == 30
    assert 'connector.class' in result


# ---------------------------------------------------------------------------
# _emit_connector_metrics
# ---------------------------------------------------------------------------


def test_emit_connector_metrics_gauges():
    collector, check, _, _ = make_collector()
    collector._emit_connector_metrics(SAMPLE_CONNECTORS_RESPONSE, ['connect_url:http://localhost:8083'])

    emitted = {call.args[0] for call in check.gauge.call_args_list}
    assert 'connector.running' in emitted
    assert 'connector.task.count' in emitted
    assert 'connector.tasks' in emitted


def test_emit_connector_metrics_running_state():
    collector, check, _, _ = make_collector()
    collector._emit_connector_metrics(SAMPLE_CONNECTORS_RESPONSE, [])

    running_calls = [
        c
        for c in check.gauge.call_args_list
        if c.args[0] == 'connector.running' and 'connector:demo-source' in c.kwargs.get('tags', [])
    ]
    assert running_calls, "no connector.running gauge for demo-source"
    assert running_calls[0].args[1] == 1

    paused_calls = [
        c
        for c in check.gauge.call_args_list
        if c.args[0] == 'connector.running' and 'connector:demo-heartbeat' in c.kwargs.get('tags', [])
    ]
    assert paused_calls, "no connector.running gauge for demo-heartbeat"
    assert paused_calls[0].args[1] == 0


def test_task_metrics_gated_by_flag():
    collector_off, check_off, _, _ = make_collector(collect_task_metrics=False)
    collector_off._emit_connector_metrics(SAMPLE_CONNECTORS_RESPONSE, [])
    per_task = [c for c in check_off.gauge.call_args_list if c.args[0] == 'connector.task.running']
    assert per_task == [], "expected no per-task gauges when flag is False"

    collector_on, check_on, _, _ = make_collector(collect_task_metrics=True)
    collector_on._emit_connector_metrics(SAMPLE_CONNECTORS_RESPONSE, [])
    per_task = [c for c in check_on.gauge.call_args_list if c.args[0] == 'connector.task.running']
    assert per_task, "expected per-task gauges when flag is True"


# ---------------------------------------------------------------------------
# _get_events_to_send (dedup logic)
# ---------------------------------------------------------------------------


def test_dedup_unchanged_content_not_reemitted():
    collector, _, _, cache_store = make_collector()
    items = {'connector-a': '{"config":"stable"}'}

    first = collector._get_events_to_send('test_key', items)
    assert 'connector-a' in first

    second = collector._get_events_to_send('test_key', items)
    assert 'connector-a' not in second, "unchanged content should not re-emit within TTL"


def test_dedup_changed_content_reemitted():
    collector, _, _, _ = make_collector()
    collector._get_events_to_send('test_key', {'connector-a': '{"config":"v1"}'})
    second = collector._get_events_to_send('test_key', {'connector-a': '{"config":"v2"}'})
    assert 'connector-a' in second


def test_dedup_ttl_expiry_triggers_reemit():
    collector, _, _, cache_store = make_collector()
    items = {'connector-a': '{"config":"stable"}'}
    collector._get_events_to_send('test_key', items)

    # Manually expire the cache entry
    cached = json.loads(cache_store['test_key'])
    cached['connector-a']['expire_at'] = time.time() - 1
    cache_store['test_key'] = json.dumps(cached)

    third = collector._get_events_to_send('test_key', items)
    assert 'connector-a' in third, "should re-emit after TTL expiry"


# ---------------------------------------------------------------------------
# _emit_connector_config_events — timestamp not in hash
# ---------------------------------------------------------------------------


def test_collection_timestamp_excluded_from_hash():
    """Verify that config events with identical content don't re-emit on the next cycle."""
    collector, check, _, _ = make_collector(connect_urls=['http://localhost:8083'])

    collector._emit_connector_config_events(SAMPLE_CONNECTORS_RESPONSE, 'cluster-1', 'http://localhost:8083')
    first_count = check.event_platform_event.call_count

    # Second call with same data — should not emit again within TTL
    collector._emit_connector_config_events(SAMPLE_CONNECTORS_RESPONSE, 'cluster-1', 'http://localhost:8083')
    second_count = check.event_platform_event.call_count

    assert second_count == first_count, f"expected no new events on second call, got {second_count - first_count} more"


# ---------------------------------------------------------------------------
# collect() — connectivity status dict
# ---------------------------------------------------------------------------


def test_collect_returns_connected_true_on_success():
    collector, _, _, _ = make_collector(connect_urls=['http://localhost:8083'])
    with mock.patch.object(collector, '_collect_rest'):
        result = collector.collect('cluster-1')

    assert result == {'http://localhost:8083': True}


def test_collect_returns_connected_false_on_failure():
    collector, _, _, _ = make_collector(connect_urls=['http://localhost:8083'])
    with mock.patch.object(collector, '_collect_rest', side_effect=requests.ConnectionError("refused")):
        result = collector.collect('cluster-1')

    assert result == {'http://localhost:8083': False}


# ---------------------------------------------------------------------------
# Older-worker compat — list response → warning, no crash
# ---------------------------------------------------------------------------


def test_older_worker_list_response_warns_and_returns():
    collector, check, _, _ = make_collector(connect_urls=['http://localhost:8083'])
    mock_resp = mock.MagicMock()
    mock_resp.json.return_value = ['connector-a', 'connector-b']  # old-style list

    session_mock = mock.MagicMock()
    session_mock.get.return_value = mock_resp
    collector._session = session_mock

    # Should not raise, should not emit metrics
    collector._collect_rest('http://localhost:8083', 'cluster-1')

    assert check.gauge.call_count == 0
    collector.log.warning.assert_called_once()


# ---------------------------------------------------------------------------
# _collect_rest — full success path with mocked HTTP session
# ---------------------------------------------------------------------------


def test_collect_rest_success_emits_metrics_and_events():
    collector, check, _, _ = make_collector(connect_urls=['http://localhost:8083'])
    mock_resp = mock.MagicMock()
    mock_resp.json.return_value = SAMPLE_CONNECTORS_RESPONSE

    session_mock = mock.MagicMock()
    session_mock.get.return_value = mock_resp
    collector._session = session_mock

    with mock.patch.object(collector, '_collect_plugins'):
        collector._collect_rest('http://localhost:8083', 'cluster-1')

    count_calls = [c for c in check.gauge.call_args_list if c.args[0] == 'connector.count']
    assert count_calls, "expected connector.count gauge"
    assert count_calls[0].args[1] == 2
    assert check.event_platform_event.call_count > 0


# ---------------------------------------------------------------------------
# _collect_plugins — success and skip-when-cached paths
# ---------------------------------------------------------------------------


def test_collect_plugins_emits_event_on_first_call():
    collector, check, _, _ = make_collector(connect_urls=['http://localhost:8083'])
    plugins = [{'class': 'org.apache.kafka.connect.file.FileStreamSinkConnector', 'type': 'sink', 'version': '3.3.0'}]

    mock_resp = mock.MagicMock()
    mock_resp.json.return_value = plugins

    session_mock = mock.MagicMock()
    session_mock.get.return_value = mock_resp
    collector._session = session_mock

    collector._collect_plugins('http://localhost:8083', 'cluster-1')
    assert check.event_platform_event.call_count == 1
    payload = json.loads(check.event_platform_event.call_args[0][0])
    assert payload['config_type'] == 'connector_plugins'


def test_collect_plugins_skips_when_ttl_not_expired(monkeypatch):
    collector, check, _, cache_store = make_collector(connect_urls=['http://localhost:8083'])

    from urllib.parse import quote

    from datadog_checks.kafka_consumer.connectors import CONNECTOR_PLUGINS_CACHE_KEY

    safe_url = quote('http://localhost:8083', safe='')
    fetch_cache_key = f'{CONNECTOR_PLUGINS_CACHE_KEY}:{safe_url}'
    cache_store[fetch_cache_key] = json.dumps({'plugins': time.time() + 9999})

    collector._collect_plugins('http://localhost:8083', 'cluster-1')
    assert check.event_platform_event.call_count == 0


# ---------------------------------------------------------------------------
# _get_items_to_fetch and _mark_items_fetched
# ---------------------------------------------------------------------------


def test_get_items_to_fetch_returns_all_on_empty_cache():
    collector, _, _, _ = make_collector()
    result = collector._get_items_to_fetch('nonexistent_key', ['a', 'b'])
    assert result == ['a', 'b']


def test_get_items_to_fetch_skips_unexpired_items():
    collector, _, _, cache_store = make_collector()
    future = time.time() + 9999
    cache_store['test_key'] = json.dumps({'item-a': future, 'item-b': 0})
    result = collector._get_items_to_fetch('test_key', ['item-a', 'item-b'])
    assert result == ['item-b']
    assert 'item-a' not in result


def test_mark_items_fetched_writes_expiry():
    collector, _, _, cache_store = make_collector()
    collector._mark_items_fetched('test_key', ['item-a'], ttl_base=100, ttl_jitter=0)
    cached = json.loads(cache_store['test_key'])
    assert 'item-a' in cached
    assert cached['item-a'] > time.time()


def test_mark_items_fetched_evicts_oldest_when_over_max():
    collector, _, _, cache_store = make_collector()
    existing = {f'key-{i}': time.time() + i for i in range(10)}
    cache_store['test_key'] = json.dumps(existing)
    collector._mark_items_fetched('test_key', ['new-key'], ttl_base=100, ttl_jitter=0, max_cache_size=5)
    cached = json.loads(cache_store['test_key'])
    assert len(cached) <= 5
    assert 'new-key' in cached


def test_get_items_to_fetch_handles_corrupt_cache():
    collector, _, _, cache_store = make_collector()
    cache_store['bad_key'] = 'not-valid-json'
    result = collector._get_items_to_fetch('bad_key', ['item'])
    assert result == ['item']


def test_get_events_to_send_handles_corrupt_cache():
    collector, _, _, cache_store = make_collector()
    cache_store['bad_key'] = 'not-valid-json'
    result = collector._get_events_to_send('bad_key', {'item': 'content'})
    assert result == ['item']


def test_get_events_to_send_empty_items():
    collector, _, _, _ = make_collector()
    result = collector._get_events_to_send('some_key', {})
    assert result == []


# ---------------------------------------------------------------------------
# _get_tags and _original_cluster_id_field
# ---------------------------------------------------------------------------


def test_get_tags_without_cluster_id():
    collector, _, config, _ = make_collector()
    config._custom_tags = ['env:prod']
    config._kafka_cluster_id_override = None
    tags = collector._get_tags()
    assert tags == ['env:prod']


def test_get_tags_with_cluster_id():
    collector, _, config, _ = make_collector()
    config._custom_tags = []
    config._kafka_cluster_id_override = None
    tags = collector._get_tags('cluster-abc')
    assert 'kafka_cluster_id:cluster-abc' in tags


def test_get_tags_with_cluster_id_override():
    collector, _, config, _ = make_collector()
    config._custom_tags = []
    config._kafka_cluster_id_override = 'override-id'
    config._auto_detected_cluster_id = 'real-id'
    tags = collector._get_tags('override-id')
    assert 'original_kafka_cluster_id:real-id' in tags


def test_original_cluster_id_field_when_override_set():
    collector, _, config, _ = make_collector()
    config._kafka_cluster_id_override = 'override-id'
    config._auto_detected_cluster_id = 'real-id'
    result = collector._original_cluster_id_field()
    assert result == {'original_kafka_cluster_id': 'real-id'}


def test_original_cluster_id_field_when_no_override():
    collector, _, config, _ = make_collector()
    config._kafka_cluster_id_override = None
    result = collector._original_cluster_id_field()
    assert result == {}


# ---------------------------------------------------------------------------
# _configure_session — auth and TLS configuration paths
# ---------------------------------------------------------------------------


def test_configure_session_sets_basic_auth():
    collector, _, config, _ = make_collector()
    config._kafka_connect_username = 'user'
    config._kafka_connect_password = 'pass'
    config._kafka_connect_tls_verify = True
    config._kafka_connect_tls_ca_cert = None
    config._kafka_connect_tls_cert = None
    config._kafka_connect_tls_key = None

    session = mock.MagicMock()
    collector._configure_session(session)
    assert session.auth == ('user', 'pass')


def test_configure_session_tls_verify_false():
    collector, _, config, _ = make_collector()
    config._kafka_connect_username = None
    config._kafka_connect_password = None
    config._kafka_connect_tls_verify = False
    config._kafka_connect_tls_ca_cert = None
    config._kafka_connect_tls_cert = None
    config._kafka_connect_tls_key = None

    session = mock.MagicMock()
    collector._configure_session(session)
    assert session.verify is False


def test_configure_session_tls_ca_cert():
    collector, _, config, _ = make_collector()
    config._kafka_connect_username = None
    config._kafka_connect_password = None
    config._kafka_connect_tls_verify = True
    config._kafka_connect_tls_ca_cert = '/path/to/ca.crt'
    config._kafka_connect_tls_cert = None
    config._kafka_connect_tls_key = None

    session = mock.MagicMock()
    collector._configure_session(session)
    assert session.verify == '/path/to/ca.crt'


def test_configure_session_client_cert_and_key():
    collector, _, config, _ = make_collector()
    config._kafka_connect_username = None
    config._kafka_connect_password = None
    config._kafka_connect_tls_verify = True
    config._kafka_connect_tls_ca_cert = None
    config._kafka_connect_tls_cert = '/path/to/cert.pem'
    config._kafka_connect_tls_key = '/path/to/key.pem'

    session = mock.MagicMock()
    collector._configure_session(session)
    assert session.cert == ('/path/to/cert.pem', '/path/to/key.pem')


def test_configure_session_cert_only():
    collector, _, config, _ = make_collector()
    config._kafka_connect_username = None
    config._kafka_connect_password = None
    config._kafka_connect_tls_verify = True
    config._kafka_connect_tls_ca_cert = None
    config._kafka_connect_tls_cert = '/path/to/cert.pem'
    config._kafka_connect_tls_key = None

    session = mock.MagicMock()
    collector._configure_session(session)
    assert session.cert == '/path/to/cert.pem'


# ---------------------------------------------------------------------------
# collect() — OAuth failure path
# ---------------------------------------------------------------------------


def test_collect_oauth_failure_returns_empty():
    collector, _, config, _ = make_collector(connect_urls=['http://localhost:8083'])
    config._kafka_connect_oauth_token_provider = {'url': 'http://auth', 'client_id': 'id', 'client_secret': 'sec'}

    with mock.patch.object(collector, '_refresh_oauth_token', side_effect=Exception("auth failed")):
        result = collector.collect('cluster-1')

    assert result == {}


# ---------------------------------------------------------------------------
# _refresh_oauth_token
# ---------------------------------------------------------------------------


def test_refresh_oauth_token_sets_header():
    collector, _, config, _ = make_collector(connect_urls=['http://localhost:8083'])
    config._kafka_connect_oauth_token_provider = {
        'url': 'http://auth/token',
        'client_id': 'client',
        'client_secret': 'secret',
    }
    config._request_timeout = 10

    session_mock = mock.MagicMock()
    session_mock.headers = {}
    collector._session = session_mock

    with mock.patch(
        'datadog_checks.kafka_consumer.connectors._fetch_oidc_token',
        return_value=('mytoken', time.time() + 300),
    ):
        collector._refresh_oauth_token()

    assert session_mock.headers['Authorization'] == 'Bearer mytoken'


def test_refresh_oauth_token_skips_when_still_valid():
    collector, _, config, _ = make_collector(connect_urls=['http://localhost:8083'])
    config._kafka_connect_oauth_token_provider = {
        'url': 'http://auth/token',
        'client_id': 'client',
        'client_secret': 'secret',
    }
    config._request_timeout = 10

    collector._oauth_token = 'existing-token'
    collector._oauth_token_expiry = time.time() + 3600

    with mock.patch('datadog_checks.kafka_consumer.connectors._fetch_oidc_token') as mock_fetch:
        collector._refresh_oauth_token()

    mock_fetch.assert_not_called()


def test_refresh_oauth_token_no_op_when_no_provider():
    collector, _, config, _ = make_collector()
    config._kafka_connect_oauth_token_provider = None

    with mock.patch('datadog_checks.kafka_consumer.connectors._fetch_oidc_token') as mock_fetch:
        collector._refresh_oauth_token()

    mock_fetch.assert_not_called()


def test_refresh_oauth_token_sets_custom_headers():
    collector, _, config, _ = make_collector(connect_urls=['http://localhost:8083'])
    config._kafka_connect_oauth_token_provider = {
        'url': 'http://auth/token',
        'client_id': 'client',
        'client_secret': 'secret',
        'custom_headers': {'X-Tenant': 'tenant-1'},
    }
    config._request_timeout = 10

    session_mock = mock.MagicMock()
    session_mock.headers = {}
    collector._session = session_mock

    with mock.patch(
        'datadog_checks.kafka_consumer.connectors._fetch_oidc_token',
        return_value=('mytoken', time.time() + 300),
    ):
        collector._refresh_oauth_token()

    assert session_mock.headers.get('X-Tenant') == 'tenant-1'


# ---------------------------------------------------------------------------
# _fetch_oidc_token — standalone function
# ---------------------------------------------------------------------------


def test_fetch_oidc_token_returns_token_and_expiry():
    from datadog_checks.kafka_consumer.connectors import _fetch_oidc_token

    oauth_config = {
        'url': 'http://auth/token',
        'client_id': 'cid',
        'client_secret': 'csec',
    }

    mock_resp = mock.MagicMock()
    mock_resp.json.return_value = {'access_token': 'tok123', 'expires_in': 600}

    session_mock = mock.MagicMock()
    session_mock.post.return_value = mock_resp

    token, expires_at = _fetch_oidc_token(oauth_config, session_mock, timeout=10)
    assert token == 'tok123'
    assert expires_at > time.time()
    assert expires_at < time.time() + 700


def test_fetch_oidc_token_uses_scope_and_ca_cert():
    from datadog_checks.kafka_consumer.connectors import _fetch_oidc_token

    oauth_config = {
        'url': 'http://auth/token',
        'client_id': 'cid',
        'client_secret': 'csec',
        'scope': 'openid',
        'tls_ca_cert': '/path/to/ca.crt',
    }

    mock_resp = mock.MagicMock()
    mock_resp.json.return_value = {'access_token': 'tok456', 'expires_in': 300}

    session_mock = mock.MagicMock()
    session_mock.post.return_value = mock_resp

    token, _ = _fetch_oidc_token(oauth_config, session_mock, timeout=5)
    assert token == 'tok456'
    call_kwargs = session_mock.post.call_args.kwargs
    assert call_kwargs['verify'] == '/path/to/ca.crt'
    assert call_kwargs['data']['scope'] == 'openid'


# ---------------------------------------------------------------------------
# _get_session — session creation when None
# ---------------------------------------------------------------------------


def test_get_session_creates_session_on_first_call():
    collector, _, _, _ = make_collector()
    assert collector._session is None
    session = collector._get_session()
    assert session is not None
    assert collector._session is session
    # Calling again returns the same instance
    assert collector._get_session() is session


# ---------------------------------------------------------------------------
# _mark_items_fetched — defaults and exception paths
# ---------------------------------------------------------------------------


def test_mark_items_fetched_uses_defaults_when_none():
    collector, _, _, cache_store = make_collector()
    # Call without explicit ttl_base/ttl_jitter → should use CONFIGS_REFRESH_INTERVAL defaults
    collector._mark_items_fetched('test_key', ['item-a'])
    cached = json.loads(cache_store['test_key'])
    assert 'item-a' in cached
    assert cached['item-a'] > time.time()


def test_mark_items_fetched_handles_corrupt_cache():
    collector, _, _, cache_store = make_collector()
    cache_store['bad_key'] = 'not-valid-json'
    # Should not raise
    collector._mark_items_fetched('bad_key', ['item'], ttl_base=100, ttl_jitter=0)
    cached = json.loads(cache_store['bad_key'])
    assert 'item' in cached


def test_mark_items_fetched_handles_write_failure():
    collector, check, _, _ = make_collector()
    check.write_persistent_cache.side_effect = Exception("disk full")
    # Should not raise
    collector._mark_items_fetched('test_key', ['item'], ttl_base=100, ttl_jitter=0)
    collector.log.debug.assert_called()


# ---------------------------------------------------------------------------
# _get_events_to_send — write failure path
# ---------------------------------------------------------------------------


def test_get_events_to_send_handles_write_failure():
    collector, check, _, _ = make_collector()
    check.write_persistent_cache.side_effect = Exception("disk full")
    # Should not raise, should return the items to send
    result = collector._get_events_to_send('test_key', {'item': 'content'})
    assert result == ['item']
    collector.log.debug.assert_called()


# ---------------------------------------------------------------------------
# _collect_confluent_cloud — URL construction and delegation
# ---------------------------------------------------------------------------


def test_collect_confluent_cloud_constructs_correct_url():
    collector, _, config, _ = make_collector()
    config._kafka_connect_confluent_cloud_environment_id = 'env-abc123'
    config._kafka_connect_confluent_cloud_cluster_id = 'lkc-xyz789'
    config._kafka_connect_confluent_cloud_url = 'https://api.confluent.cloud'

    with mock.patch.object(collector, '_collect_rest') as mock_rest:
        collector._collect_confluent_cloud('cluster-1')

    mock_rest.assert_called_once_with(
        'https://api.confluent.cloud/connect/v1/environments/env-abc123/clusters/lkc-xyz789',
        'cluster-1',
    )


def test_collect_confluent_cloud_custom_base_url():
    collector, _, config, _ = make_collector()
    config._kafka_connect_confluent_cloud_environment_id = 'env-abc123'
    config._kafka_connect_confluent_cloud_cluster_id = 'lkc-xyz789'
    config._kafka_connect_confluent_cloud_url = 'https://private.confluent.example.com/'

    with mock.patch.object(collector, '_collect_rest') as mock_rest:
        collector._collect_confluent_cloud('cluster-1')

    mock_rest.assert_called_once_with(
        'https://private.confluent.example.com/connect/v1/environments/env-abc123/clusters/lkc-xyz789',
        'cluster-1',
    )


def test_collect_confluent_cloud_success_reported_in_connectivity():
    collector, _, config, _ = make_collector()
    config._kafka_connect_oauth_token_provider = None
    config._kafka_connect_confluent_cloud_environment_id = 'env-abc123'
    config._kafka_connect_confluent_cloud_cluster_id = 'lkc-xyz789'
    config._kafka_connect_confluent_cloud_url = 'https://api.confluent.cloud'

    with mock.patch.object(collector, '_collect_confluent_cloud'):
        result = collector.collect('cluster-1')

    assert result == {'confluent_cloud:env-abc123:lkc-xyz789': True}


def test_collect_confluent_cloud_failure_reported_in_connectivity():
    collector, _, config, _ = make_collector()
    config._kafka_connect_oauth_token_provider = None
    config._kafka_connect_confluent_cloud_environment_id = 'env-abc123'
    config._kafka_connect_confluent_cloud_cluster_id = 'lkc-xyz789'
    config._kafka_connect_confluent_cloud_url = 'https://api.confluent.cloud'

    with mock.patch.object(
        collector, '_collect_confluent_cloud', side_effect=requests.ConnectionError("refused")
    ):
        result = collector.collect('cluster-1')

    assert result == {'confluent_cloud:env-abc123:lkc-xyz789': False}


