# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from datadog_checks.dev.replay.redaction import REDACTED, scrub_json, scrub_request_record, scrub_tag, scrub_url


def test_scrub_json_redacts_sensitive_keys_recursively():
    assert scrub_json(
        {
            'api_key': 'abc123',
            'nested': {'password': 'secret', 'safe': 'value'},
            'items': [{'client_secret': 'hidden'}],
            'session_id': 'sensitive-session-id',
        }
    ) == {
        'api_key': REDACTED,
        'nested': {'password': REDACTED, 'safe': 'value'},
        'items': [{'client_secret': REDACTED}],
        'session_id': REDACTED,
    }


def test_scrub_json_preserves_metric_keys_with_session_tokens():
    assert scrub_json(
        {
            'global': {
                'proxy.process.http2.session_die_active': '12',
                'proxy.process.http2.session_die_inactive': 3.5,
                'proxy.process.http2.session_id': 'sensitive-session-id',
            },
            'password': 'secret',
        }
    ) == {
        'global': {
            'proxy.process.http2.session_die_active': '12',
            'proxy.process.http2.session_die_inactive': 3.5,
            'proxy.process.http2.session_id': REDACTED,
        },
        'password': REDACTED,
    }


def test_scrub_url_redacts_sensitive_query_values():
    assert scrub_url('http://example.com/metrics?api_key=abc123&name=demo') == (
        'http://example.com/metrics?api_key=%3CREDACTED%3E&name=demo'
    )


def test_scrub_request_record_redacts_headers_url_and_json_body():
    record = scrub_request_record(
        {
            'method': 'GET',
            'url': 'http://example.com/metrics?token=abc123&name=demo',
            'status': 200,
            'headers': {'Authorization': 'Bearer abcdefghijklmnop', 'Content-Type': 'application/json'},
            'body': '{"password": "secret", "value": 1}',
        }
    )

    assert record['url'] == 'http://example.com/metrics?token=%3CREDACTED%3E&name=demo'
    assert record['headers']['Authorization'] == REDACTED
    assert record['body'] == '{"password": "<REDACTED>", "value": 1}'


def test_scrub_request_record_redacts_request_identity_fields():
    record = scrub_request_record(
        {
            'method': 'post',
            'url': 'http://example.com/api',
            'request_headers': {'X-Api-Key': 'abc123'},
            'request_json': {'access_token': 'secret-token', 'safe': 'value'},
            'request_data': 'client_secret=hidden&name=demo',
            'status': 200,
            'headers': {'Content-Type': 'application/json'},
            'body': '{}',
        }
    )

    assert record['method'] == 'POST'
    assert record['request_headers']['X-Api-Key'] == REDACTED
    assert record['request_json'] == {'access_token': REDACTED, 'safe': 'value'}
    assert 'hidden' not in record['request_data']


def test_scrub_request_record_preserves_openmetrics_session_sample_value():
    record = scrub_request_record(
        {
            'method': 'GET',
            'url': 'http://example.com/metrics?token=secret-token&name=demo',
            'status': 200,
            'headers': {'Content-Type': 'text/plain; version=0.0.4'},
            'body': '\n'.join(
                [
                    '# HELP traffic_server_process_http2_session_die_active Closed HTTP/2 connections',
                    '# TYPE traffic_server_process_http2_session_die_active counter',
                    'traffic_server_process_http2_session_die_active{session="active",password="secret"} 12',
                ]
            ),
        }
    )

    assert record['url'] == 'http://example.com/metrics?token=%3CREDACTED%3E&name=demo'
    assert ' 12' in record['body']
    assert 'session_die_active' in record['body']
    assert f'session="{REDACTED}"' in record['body']
    assert f'password="{REDACTED}"' in record['body']
    assert 'secret' not in record['body']


def test_scrub_tag_redacts_sensitive_tag_values():
    assert scrub_tag('token:abc123') == f'token:{REDACTED}'
    assert scrub_tag('session_id:abc123') == f'session_id:{REDACTED}'
    assert scrub_tag('session_die_active:12') == 'session_die_active:12'
    assert scrub_tag('env:test') == 'env:test'
