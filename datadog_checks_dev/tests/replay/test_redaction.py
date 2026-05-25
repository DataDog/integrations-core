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
        }
    ) == {
        'api_key': REDACTED,
        'nested': {'password': REDACTED, 'safe': 'value'},
        'items': [{'client_secret': REDACTED}],
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


def test_scrub_tag_redacts_sensitive_tag_values():
    assert scrub_tag('token:abc123') == f'token:{REDACTED}'
    assert scrub_tag('env:test') == 'env:test'
