# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import copy

import mock
import pytest

from datadog_checks.base.utils.http_exceptions import HTTPClientConnectionError
from datadog_checks.dev.utils import get_metadata_metrics
from datadog_checks.kafka_consumer import KafkaCheck
from datadog_checks.kafka_consumer.connectors import CONNECTOR_EVENT_TOPICS_MAX, TOPICS_FETCH_MAX_PER_RUN

from .common import CONNECT_URL
from .conftest import SAMPLE_CONNECTORS_RESPONSE, connectors_url, topics_url

pytestmark = [pytest.mark.unit]


def dsm_events(aggregator, config_type):
    """Return the captured data-streams-message events of the given config_type."""
    return [
        event
        for event in aggregator.get_event_platform_events('data-streams-message')
        if event.get('config_type') == config_type
    ]


def metrics_with_tag(aggregator, name, tag):
    """Return submitted metric stubs for `name` that carry `tag`."""
    return [metric for metric in aggregator.metrics(name) if tag in metric.tags]


def requests_to(fake_http, url_suffix, method='GET'):
    """Return the recorded requests whose URL ends with `url_suffix`."""
    return [request for request in fake_http.requests if request.method == method and request.url.endswith(url_suffix)]


def connector_request_options(fake_http):
    """Return the options of the first Connect /connectors request."""
    for request in requests_to(fake_http, '/connectors'):
        return request.options
    raise AssertionError("no /connectors request was made")


def fail_all_topics(error_or_status):
    """Build a `register_overrides` that fails every sample connector's topics request."""

    def register(respond, fail):
        for name in SAMPLE_CONNECTORS_RESPONSE:
            url = topics_url(CONNECT_URL, name)
            if isinstance(error_or_status, Exception):
                fail(url, error_or_status)
            else:
                respond(url, status_code=error_or_status)

    return register


def test_connector_metrics_emitted(run_connect_check, aggregator):
    run_connect_check(connectors_response=SAMPLE_CONNECTORS_RESPONSE)

    aggregator.assert_metric('kafka.connector.count', value=2)
    aggregator.assert_metric('kafka.connector.task.count')
    aggregator.assert_metric('kafka.connector.tasks')
    aggregator.assert_metric('kafka.connector.task.running')
    aggregator.assert_metric('kafka.connector.running', count=0)


def test_connector_state_tag_lowercased(run_connect_check, aggregator):
    run_connect_check(connectors_response=SAMPLE_CONNECTORS_RESPONSE)

    source = metrics_with_tag(aggregator, 'kafka.connector.task.count', 'connector:demo-source')
    heartbeat = metrics_with_tag(aggregator, 'kafka.connector.task.count', 'connector:demo-heartbeat')
    assert 'connector_state:running' in source[0].tags
    assert 'connector_state:paused' in heartbeat[0].tags


def test_task_state_tag_on_task_metrics(run_connect_check, aggregator):
    run_connect_check(connectors_response=SAMPLE_CONNECTORS_RESPONSE)

    aggregator.assert_metric_has_tag('kafka.connector.tasks', 'task_state:running')
    aggregator.assert_metric_has_tag('kafka.connector.tasks', 'task_state:paused')


def test_connector_class_tag_uses_short_name(run_connect_check, aggregator):
    run_connect_check(connectors_response=SAMPLE_CONNECTORS_RESPONSE)

    source = metrics_with_tag(aggregator, 'kafka.connector.task.count', 'connector:demo-source')
    assert 'connector_class:MirrorSourceConnector' in source[0].tags


def test_custom_tags_applied_to_connector_metrics(run_connect_check, aggregator):
    run_connect_check(connectors_response=SAMPLE_CONNECTORS_RESPONSE, instance_extra={'tags': ['custom_tag:foo']})

    aggregator.assert_metric_has_tag('kafka.connector.count', 'custom_tag:foo')


def test_cluster_id_override_recorded_in_events(run_connect_check, aggregator):
    run_connect_check(
        connectors_response=SAMPLE_CONNECTORS_RESPONSE,
        instance_extra={'kafka_cluster_id_override': 'override-id'},
    )

    events = dsm_events(aggregator, 'connector')
    assert events
    assert all(event['kafka_cluster_id'] == 'override-id' for event in events)
    assert all('original_kafka_cluster_id' in event for event in events)


def test_config_only_allowlisted_keys_left_unredacted(run_connect_check, aggregator):
    connectors = {
        'my-sink': {
            'info': {
                'type': 'sink',
                'config': {
                    'connector.class': 'io.confluent.SomeSink',
                    'connection.password': 'secret123',
                    'sasl.jaas.config': 'org.apache.kafka.common.security.plain.PlainLoginModule ...',
                    'db.host': 'db.internal.example.com',
                    'transforms': 'insertField',
                    'transforms.insertField.type': 'org.apache.kafka.connect.transforms.InsertField$Value',
                    'transforms.insertField.static.value': 'not-framework-defined',
                    'tasks.max': '2',
                    'topics': 'orders',
                },
            },
            'status': {'connector': {'state': 'RUNNING'}, 'tasks': []},
        }
    }
    run_connect_check(connectors_response=connectors)

    events = dsm_events(aggregator, 'connector')
    assert len(events) == 1
    cfg = events[0]['config']
    assert cfg['connection.password'] == '[hidden]'
    assert cfg['sasl.jaas.config'] == '[hidden]'
    assert cfg['db.host'] == '[hidden]'
    assert cfg['transforms.insertField.static.value'] == '[hidden]'
    assert cfg['connector.class'] == 'io.confluent.SomeSink'
    assert cfg['tasks.max'] == '2'
    assert cfg['topics'] == 'orders'
    assert cfg['transforms'] == 'insertField'
    assert cfg['transforms.insertField.type'] == 'org.apache.kafka.connect.transforms.InsertField$Value'


def test_config_allowlist_covers_known_connector_plugin_keys(run_connect_check, aggregator):
    connectors = {
        'debezium-source': {
            'info': {
                'type': 'source',
                'config': {
                    'connector.class': 'io.debezium.connector.postgresql.PostgresConnector',
                    'database.hostname': 'postgres.internal.example.com',
                    'database.port': '5432',
                    'database.user': 'debezium',
                    'database.password': 'super-secret',
                    'table.include.list': 'public.orders,public.customers',
                    'snapshot.mode': 'initial',
                    's3.bucket.name': 'my-bucket',
                    'insert.mode': 'upsert',
                },
            },
            'status': {'connector': {'state': 'RUNNING'}, 'tasks': []},
        }
    }
    run_connect_check(connectors_response=connectors)

    events = dsm_events(aggregator, 'connector')
    assert len(events) == 1
    cfg = events[0]['config']
    assert cfg['database.hostname'] == 'postgres.internal.example.com'
    assert cfg['database.port'] == '5432'
    assert cfg['table.include.list'] == 'public.orders,public.customers'
    assert cfg['snapshot.mode'] == 'initial'
    assert cfg['s3.bucket.name'] == 'my-bucket'
    assert cfg['insert.mode'] == 'upsert'
    assert cfg['database.user'] == '[hidden]'
    assert cfg['database.password'] == '[hidden]'


def test_config_sensitive_substring_overrides_allowlist(run_connect_check, aggregator):
    connectors = {
        'my-sink': {
            'info': {
                'type': 'sink',
                # 'mode' is allowlisted, but a plugin author naming a secret key
                # 'mode.secret.token' should still be hidden by the substring safety net.
                'config': {'connector.class': 'io.confluent.SomeSink', 'mode.secret.token': 'abc123'},
            },
            'status': {'connector': {'state': 'RUNNING'}, 'tasks': []},
        }
    }
    run_connect_check(connectors_response=connectors)

    events = dsm_events(aggregator, 'connector')
    assert len(events) == 1
    assert events[0]['config']['mode.secret.token'] == '[hidden]'


def test_failed_connector_and_task_trace_included_in_config_event(run_connect_check, aggregator):
    connectors = {
        'my-sink': {
            'info': {
                'type': 'sink',
                'config': {'connector.class': 'io.confluent.SomeSink'},
            },
            'status': {
                'connector': {'state': 'FAILED', 'trace': 'org.apache.kafka.connect.errors.ConnectException'},
                'tasks': [
                    {'id': 0, 'state': 'FAILED', 'trace': 'java.lang.NullPointerException'},
                    {'id': 1, 'state': 'FAILED'},
                    {'id': 2, 'state': 'RUNNING'},
                ],
            },
        }
    }
    run_connect_check(connectors_response=connectors)

    events = dsm_events(aggregator, 'connector')
    assert len(events) == 1
    event = events[0]
    assert event['connector_trace'] == 'org.apache.kafka.connect.errors.ConnectException'
    assert event['task_traces'] == [{'task_id': 0, 'trace': 'java.lang.NullPointerException'}]


def test_connector_trace_absent_when_running(run_connect_check, aggregator):
    run_connect_check(connectors_response=SAMPLE_CONNECTORS_RESPONSE)

    events = dsm_events(aggregator, 'connector')
    assert events
    assert all(event['connector_trace'] is None for event in events)
    assert all(event['task_traces'] == [] for event in events)


def test_connector_topics_included_in_config_event(run_connect_check, aggregator):
    run_connect_check(
        connectors_response=SAMPLE_CONNECTORS_RESPONSE,
        topics_response={'demo-source': ['demo-orders'], 'demo-heartbeat': []},
    )

    events = dsm_events(aggregator, 'connector')
    source_event = next(event for event in events if event['connector'] == 'demo-source')
    heartbeat_event = next(event for event in events if event['connector'] == 'demo-heartbeat')
    assert source_event['topics'] == ['demo-orders']
    assert heartbeat_event['topics'] == []


def test_connector_topics_truncated_in_config_event(run_connect_check, aggregator):
    topics = [f'topic-{i:04d}' for i in range(CONNECTOR_EVENT_TOPICS_MAX + 50)]
    run_connect_check(
        connectors_response=SAMPLE_CONNECTORS_RESPONSE,
        topics_response={'demo-source': topics, 'demo-heartbeat': []},
    )

    events = dsm_events(aggregator, 'connector')
    source_event = next(event for event in events if event['connector'] == 'demo-source')
    assert source_event['topics'] == sorted(topics)[:CONNECTOR_EVENT_TOPICS_MAX]


def test_connector_topics_requested_per_connector(run_connect_check, fake_http):
    run_connect_check(connectors_response=SAMPLE_CONNECTORS_RESPONSE)

    assert len(requests_to(fake_http, '/connectors/demo-source/topics')) == 1
    assert len(requests_to(fake_http, '/connectors/demo-heartbeat/topics')) == 1


def test_topics_not_refetched_within_refresh_interval(run_connect_check, fake_http):
    run_connect_check(connectors_response=SAMPLE_CONNECTORS_RESPONSE, runs=2)

    topic_fetches = requests_to(fake_http, '/topics')
    assert len(topic_fetches) == 2, "topics should only be fetched once per connector across both runs"


def test_connector_topics_fetch_capped_per_run(run_connect_check, fake_http):
    connector_count = TOPICS_FETCH_MAX_PER_RUN + 50
    connectors = {
        f'conn-{i}': {
            'info': {'type': 'source', 'config': {'connector.class': 'org.example.Connector'}},
            'status': {'connector': {'state': 'RUNNING'}, 'tasks': []},
        }
        for i in range(connector_count)
    }

    run_connect_check(connectors_response=connectors, runs=2)

    topic_fetches = requests_to(fake_http, '/topics')
    assert len(topic_fetches) == connector_count, "leftover connectors should be fetched on a later run"


def test_config_event_survives_topics_fetch_failure(run_connect_check, aggregator):
    run_connect_check(
        connectors_response=SAMPLE_CONNECTORS_RESPONSE,
        register_overrides=fail_all_topics(HTTPClientConnectionError("refused")),
    )

    events = dsm_events(aggregator, 'connector')
    assert events
    assert all(event['topics'] == [] for event in events)


@pytest.mark.parametrize(
    'failure',
    [HTTPClientConnectionError("refused"), 503],
    ids=['connection_error', 'server_error'],
)
def test_topics_transient_failure_retried_next_run(run_connect_check, fake_http, failure):
    run_connect_check(
        connectors_response=SAMPLE_CONNECTORS_RESPONSE,
        register_overrides=fail_all_topics(failure),
        runs=2,
    )

    topic_fetches = requests_to(fake_http, '/topics')
    assert len(topic_fetches) == 4, "a transient topics failure should be retried on the next run, not backed off"


@pytest.mark.parametrize('status_code', [404, 405])
def test_topics_unsupported_endpoint_backed_off(run_connect_check, fake_http, status_code):
    run_connect_check(
        connectors_response=SAMPLE_CONNECTORS_RESPONSE,
        register_overrides=fail_all_topics(status_code),
        runs=2,
    )

    topic_fetches = requests_to(fake_http, '/topics')
    assert len(topic_fetches) == 2, "an unsupported topics endpoint should be backed off after one attempt"


def test_task_traces_sort_handles_missing_task_id(run_connect_check, aggregator):
    connectors = {
        'my-sink': {
            'info': {'type': 'sink', 'config': {'connector.class': 'io.confluent.SomeSink'}},
            'status': {
                'connector': {'state': 'RUNNING'},
                'tasks': [
                    {'id': None, 'state': 'FAILED', 'trace': 'trace-a'},
                    {'id': None, 'state': 'FAILED', 'trace': 'trace-b'},
                    {'id': 2, 'state': 'FAILED', 'trace': 'trace-c'},
                ],
            },
        }
    }
    run_connect_check(connectors_response=connectors)

    events = dsm_events(aggregator, 'connector')
    assert len(events) == 1
    # Mixed None/int task ids must not raise; the real integer id sorts ahead of the None ids.
    assert [t['task_id'] for t in events[0]['task_traces']] == [2, None, None]


def test_config_event_not_reemitted_when_unchanged(run_connect_check, aggregator):
    run_connect_check(connectors_response=SAMPLE_CONNECTORS_RESPONSE, runs=2)

    events = dsm_events(aggregator, 'connector')
    assert len(events) == 2, "unchanged connector configs should not re-emit on the second run"


def test_config_event_reemitted_when_config_changes(run_connect_check, aggregator):
    changed = copy.deepcopy(SAMPLE_CONNECTORS_RESPONSE)
    changed['demo-source']['info']['config']['tasks.max'] = '5'
    run_connect_check(connectors_per_run=[SAMPLE_CONNECTORS_RESPONSE, changed], runs=2)

    events = dsm_events(aggregator, 'connector')
    source_events = [event for event in events if event['connector'] == 'demo-source']
    heartbeat_events = [event for event in events if event['connector'] == 'demo-heartbeat']
    assert len(source_events) == 2
    assert len(heartbeat_events) == 1


def test_connector_plugins_event_emitted_once_within_refresh_interval(run_connect_check, aggregator, fake_http):
    plugins = [{'class': 'org.apache.kafka.connect.file.FileStreamSinkConnector', 'type': 'sink', 'version': '3.3.0'}]
    run_connect_check(connectors_response=SAMPLE_CONNECTORS_RESPONSE, plugins_response=plugins, runs=2)

    assert len(dsm_events(aggregator, 'connector_plugins')) == 1
    assert len(requests_to(fake_http, '/connector-plugins')) == 1


def test_connectivity_reported_in_heartbeat_on_success(run_connect_check, aggregator):
    run_connect_check(connectors_response=SAMPLE_CONNECTORS_RESPONSE)

    heartbeats = dsm_events(aggregator, 'heartbeat')
    assert heartbeats[-1]['connect_api_status'] == {CONNECT_URL: True}


def test_connectivity_false_when_endpoint_unreachable(run_connect_check, aggregator):
    run_connect_check(
        register_overrides=lambda respond, fail: fail(connectors_url(CONNECT_URL), HTTPClientConnectionError("refused"))
    )

    heartbeats = dsm_events(aggregator, 'heartbeat')
    assert heartbeats[-1]['connect_api_status'] == {CONNECT_URL: False}
    aggregator.assert_metric('kafka.connector.count', count=0)


def test_partial_failure_across_endpoints(run_connect_check, aggregator):
    def register(respond, fail):
        respond(connectors_url('http://ok:8083'), json_data=SAMPLE_CONNECTORS_RESPONSE)
        fail(connectors_url('http://bad:8083'), HTTPClientConnectionError("refused"))

    run_connect_check(
        instance_extra={'kafka_connect_url': ['http://ok:8083', 'http://bad:8083']},
        topics_response=dict.fromkeys(SAMPLE_CONNECTORS_RESPONSE, []),
        register_overrides=register,
    )

    heartbeats = dsm_events(aggregator, 'heartbeat')
    assert heartbeats[-1]['connect_api_status'] == {'http://ok:8083': True, 'http://bad:8083': False}


def test_legacy_worker_list_response_skipped(run_connect_check, aggregator):
    run_connect_check(connectors_response=['demo-source', 'demo-heartbeat'])

    aggregator.assert_metric('kafka.connector.count', count=0)
    assert dsm_events(aggregator, 'connector') == []


def test_collection_survives_corrupt_cache(run_connect_check, aggregator):
    def corrupt(key):
        return 'not-valid-json' if 'connector' in key else ''

    with mock.patch.object(KafkaCheck, 'read_persistent_cache', side_effect=corrupt):
        run_connect_check(connectors_response=SAMPLE_CONNECTORS_RESPONSE)

    aggregator.assert_metric('kafka.connector.count', value=2)
    assert len(dsm_events(aggregator, 'connector')) == 2


def test_collection_survives_cache_write_failure(run_connect_check, aggregator):
    def fail_write(key, value):
        if 'connector' in key:
            raise Exception("disk full")

    with mock.patch.object(KafkaCheck, 'write_persistent_cache', side_effect=fail_write):
        run_connect_check(connectors_response=SAMPLE_CONNECTORS_RESPONSE)

    aggregator.assert_metric('kafka.connector.count', value=2)
    assert len(dsm_events(aggregator, 'connector')) == 2


def test_requests_have_no_auth_header_without_oauth(run_connect_check, fake_http):
    run_connect_check(connectors_response=SAMPLE_CONNECTORS_RESPONSE)

    assert 'extra_headers' not in connector_request_options(fake_http)


def test_basic_auth_sent_in_requests(run_connect_check, fake_http):
    run_connect_check(
        connectors_response=SAMPLE_CONNECTORS_RESPONSE,
        instance_extra={'kafka_connect_username': 'user', 'kafka_connect_password': 'pass'},
    )

    assert connector_request_options(fake_http)['auth'] == ('user', 'pass')


@pytest.mark.parametrize(
    'instance_extra, kwarg, expected',
    [
        ({'kafka_connect_tls_verify': False}, 'verify', False),
        ({'kafka_connect_tls_ca_cert': '/path/to/ca.crt'}, 'verify', '/path/to/ca.crt'),
        (
            {'kafka_connect_tls_cert': '/path/to/cert.pem', 'kafka_connect_tls_key': '/path/to/key.pem'},
            'cert',
            ('/path/to/cert.pem', '/path/to/key.pem'),
        ),
        ({'kafka_connect_tls_cert': '/path/to/cert.pem'}, 'cert', '/path/to/cert.pem'),
    ],
    ids=['tls_verify_false', 'tls_ca_cert', 'client_cert_and_key', 'cert_only'],
)
def test_tls_settings_applied_to_requests(run_connect_check, fake_http, instance_extra, kwarg, expected):
    run_connect_check(connectors_response=SAMPLE_CONNECTORS_RESPONSE, instance_extra=instance_extra)

    assert connector_request_options(fake_http)[kwarg] == expected


def test_oauth_token_attached_to_requests(run_connect_check, fake_http):
    oauth = {'url': 'http://auth/token', 'client_id': 'client', 'client_secret': 'secret'}
    run_connect_check(
        connectors_response=SAMPLE_CONNECTORS_RESPONSE,
        instance_extra={'kafka_connect_oauth_token_provider': oauth},
        oauth_token_response={'access_token': 'mytoken', 'expires_in': 600},
    )

    assert connector_request_options(fake_http)['extra_headers']['Authorization'] == 'Bearer mytoken'


def test_oauth_custom_headers_attached_to_requests(run_connect_check, fake_http):
    oauth = {
        'url': 'http://auth/token',
        'client_id': 'client',
        'client_secret': 'secret',
        'custom_headers': {'X-Tenant': 'tenant-1'},
    }
    run_connect_check(
        connectors_response=SAMPLE_CONNECTORS_RESPONSE,
        instance_extra={'kafka_connect_oauth_token_provider': oauth},
        oauth_token_response={'access_token': 'mytoken', 'expires_in': 600},
    )

    assert connector_request_options(fake_http)['extra_headers']['X-Tenant'] == 'tenant-1'


def test_oauth_token_request_uses_scope_and_ca_cert(run_connect_check, fake_http):
    oauth = {
        'url': 'http://auth/token',
        'client_id': 'cid',
        'client_secret': 'csec',
        'scope': 'openid',
        'tls_ca_cert': '/path/to/ca.crt',
    }
    run_connect_check(
        connectors_response=SAMPLE_CONNECTORS_RESPONSE,
        instance_extra={'kafka_connect_oauth_token_provider': oauth},
        oauth_token_response={'access_token': 'tok', 'expires_in': 300},
    )

    [token_request] = requests_to(fake_http, 'http://auth/token', method='POST')
    assert token_request.options['verify'] == '/path/to/ca.crt'
    assert token_request.options['data']['scope'] == 'openid'


def test_oauth_token_reused_until_expiry(run_connect_check, fake_http):
    oauth = {'url': 'http://auth/token', 'client_id': 'client', 'client_secret': 'secret'}
    run_connect_check(
        connectors_response=SAMPLE_CONNECTORS_RESPONSE,
        instance_extra={'kafka_connect_oauth_token_provider': oauth},
        oauth_token_response={'access_token': 'mytoken', 'expires_in': 3600},
        runs=2,
    )

    assert len(requests_to(fake_http, 'http://auth/token', method='POST')) == 1


def test_oauth_failure_marks_all_endpoints_unreachable(run_connect_check, aggregator):
    oauth = {'url': 'http://auth/token', 'client_id': 'client', 'client_secret': 'secret'}
    run_connect_check(
        instance_extra={'kafka_connect_oauth_token_provider': oauth},
        register_overrides=lambda respond, fail: respond('http://auth/token', method='POST', status_code=401),
    )

    heartbeats = dsm_events(aggregator, 'heartbeat')
    assert heartbeats[-1]['connect_api_status'] == {CONNECT_URL: False}
    aggregator.assert_metric('kafka.connector.count', count=0)


def test_connector_metrics_match_metadata(run_connect_check, aggregator):
    run_connect_check(connectors_response=SAMPLE_CONNECTORS_RESPONSE)

    aggregator.assert_metrics_using_metadata(get_metadata_metrics())


# ---------------------------------------------------------------------------
# Single-expand fallback (e.g. Confluent Cloud)
# ---------------------------------------------------------------------------

CONFLUENT_CLOUD_URL = 'https://api.confluent.cloud/connect/v1/environments/env-abc123/clusters/lkc-xyz789'


def test_single_expand_sections_merged(run_connect_check, aggregator, fake_http):
    """A Connect endpoint honoring one expand value per request still yields complete metrics."""
    info_only = {
        'my-conn': {
            'info': {
                'type': 'source',
                'config': {'connector.class': 'io.confluent.SomeSource'},
            },
            'status': None,
        }
    }
    status_only = {
        'my-conn': {
            'status': {
                'connector': {'state': 'RUNNING'},
                'tasks': [{'id': 0, 'state': 'RUNNING'}],
                'type': 'source',
            }
        }
    }

    def register(respond, fail):
        url = connectors_url(CONFLUENT_CLOUD_URL)
        respond(url, json_data=info_only)
        respond(url, json_data=status_only, match_options={'params': {'expand': 'status'}})

    run_connect_check(
        instance_extra={'kafka_connect_url': CONFLUENT_CLOUD_URL},
        topics_response={'my-conn': []},
        register_overrides=register,
    )

    aggregator.assert_metric('kafka.connector.count', value=1)
    aggregator.assert_metric('kafka.connector.task.count', value=1)
    aggregator.assert_metric_has_tag('kafka.connector.task.count', 'connector_state:running')
    aggregator.assert_metric('kafka.connector.task.running', value=1)

    # The info section arrives via the supplementary fetch; assert it survived the merge
    # by checking the config event derived from it.
    events = dsm_events(aggregator, 'connector')
    assert len(events) == 1
    assert events[0]['connector'] == 'my-conn'
    assert events[0]['connector_type'] == 'source'
    assert events[0]['connector_state'] == 'RUNNING'
    assert events[0]['config']['connector.class'] == 'io.confluent.SomeSource'

    # A supplementary /connectors fetch is issued because the combined call returns a null section.
    assert len(requests_to(fake_http, '/connectors')) == 2


def test_oss_combined_response_makes_single_connectors_request(run_connect_check, aggregator, fake_http):
    """When the combined call returns both sections, no supplementary fetch is issued."""
    run_connect_check(connectors_response=SAMPLE_CONNECTORS_RESPONSE)

    assert len(requests_to(fake_http, '/connectors')) == 1


def test_combined_expand_list_ignored_falls_back_to_single_expand(run_connect_check, aggregator, fake_http):
    """A combined ``expand`` list is serialized as repeated query params, which Confluent Cloud's
    expansions endpoint doesn't honor — it returns the plain connector-name list instead of the
    expanded dict. The collector must retry with a single expand value rather than treating that
    response as an unsupported (pre-2.3) worker.
    """
    name_list = ['my-conn']
    info_only = {'my-conn': {'info': {'type': 'source', 'config': {'connector.class': 'io.confluent.SomeSource'}}}}
    status_only = {
        'my-conn': {
            'status': {'connector': {'state': 'RUNNING'}, 'tasks': [{'id': 0, 'state': 'RUNNING'}], 'type': 'source'}
        }
    }

    def register(respond, fail):
        url = connectors_url(CONFLUENT_CLOUD_URL)
        respond(url, json_data=name_list)
        respond(url, json_data=info_only, match_options={'params': {'expand': 'info'}})
        respond(url, json_data=status_only, match_options={'params': {'expand': 'status'}})

    run_connect_check(
        instance_extra={'kafka_connect_url': CONFLUENT_CLOUD_URL},
        topics_response={'my-conn': []},
        register_overrides=register,
    )

    aggregator.assert_metric('kafka.connector.count', value=1)
    aggregator.assert_metric('kafka.connector.task.count', value=1)
    aggregator.assert_metric_has_tag('kafka.connector.task.count', 'connector_state:running')

    events = dsm_events(aggregator, 'connector')
    assert len(events) == 1
    assert events[0]['connector'] == 'my-conn'
    assert events[0]['config']['connector.class'] == 'io.confluent.SomeSource'

    assert len(requests_to(fake_http, '/connectors')) == 3
