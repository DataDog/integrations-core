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
    aws_region=None,
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
    config._kafka_connect_aws_region = aws_region
    config._kafka_connect_aws_role_arn = None
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
    assert 'connector.tasks_running' in emitted
    assert 'connector.tasks_failed' in emitted
    assert 'connector.tasks_paused' in emitted
    assert 'connector.tasks_unassigned' in emitted


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
# can_connect service check
# ---------------------------------------------------------------------------


def test_can_connect_ok_on_success():
    collector, check, _, _ = make_collector(connect_urls=['http://localhost:8083'])
    with mock.patch.object(collector, '_collect_rest'):
        collector.collect('cluster-1')

    sc_calls = [c for c in check.service_check.call_args_list if c.args[0] == 'connector.can_connect']
    assert sc_calls, "expected a can_connect service check"
    assert sc_calls[0].args[1] == check.OK


def test_can_connect_critical_on_failure():
    collector, check, _, _ = make_collector(connect_urls=['http://localhost:8083'])
    with mock.patch.object(collector, '_collect_rest', side_effect=requests.ConnectionError("refused")):
        collector.collect('cluster-1')

    sc_calls = [c for c in check.service_check.call_args_list if c.args[0] == 'connector.can_connect']
    assert sc_calls[0].args[1] == check.CRITICAL
    assert 'ConnectionError' in sc_calls[0].kwargs.get('message', '')


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
