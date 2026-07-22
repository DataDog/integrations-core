# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Tests for the v0.21.1 parser optimizations."""

import pytest

from datadog_checks.base.checks.openmetrics.parser_optimizations import (
    _parse_labels,
    _parse_sample,
)


@pytest.mark.parametrize(
    'labels_string, expected',
    [
        pytest.param('method="GET"', {'method': 'GET'}, id='single'),
        pytest.param('method="GET",code="200"', {'method': 'GET', 'code': '200'}, id='multiple'),
        pytest.param('label=""', {'label': ''}, id='empty_value'),
        pytest.param('nolabels', {}, id='no_equals'),
        pytest.param('label="val\\"ue"', {'label': 'val"ue'}, id='escaped_quote'),
        pytest.param('label="line1\\nline2"', {'label': 'line1\nline2'}, id='escaped_newline'),
        pytest.param('label="a\\\\b"', {'label': 'a\\b'}, id='escaped_backslash'),
        pytest.param('func="apn,gw",proto="tcp"', {'func': 'apn,gw', 'proto': 'tcp'}, id='comma_in_value'),
        pytest.param(' method ="GET"', {'method': 'GET'}, id='spaces_around_name'),
    ],
)
def test_parse_labels(labels_string, expected):
    assert _parse_labels(labels_string) == expected


@pytest.mark.parametrize(
    'text, expected_name, expected_labels, expected_value',
    [
        pytest.param('test_gauge 42', 'test_gauge', {}, 42, id='simple'),
        pytest.param(
            'http_requests_total{method="GET",code="200"} 1027',
            'http_requests_total', {'method': 'GET', 'code': '200'}, 1027,
            id='labeled',
        ),
        pytest.param(
            'http_request_duration_seconds_bucket{le="0.5"} 24054',
            'http_request_duration_seconds_bucket', {'le': '0.5'}, 24054,
            id='histogram_bucket',
        ),
        pytest.param(
            'temperature{location="outside"} 28.5',
            'temperature', {'location': 'outside'}, 28.5,
            id='float_value',
        ),
        pytest.param('test_metric\t42', 'test_metric', {}, 42, id='tab_separator'),
        pytest.param(
            'metric{label="val}ue"} 1',
            'metric', {'label': 'val}ue'}, 1,
            id='brace_in_value',
        ),
        pytest.param(
            'metric{func="apn,gw",proto="tcp"} 8',
            'metric', {'func': 'apn,gw', 'proto': 'tcp'}, 8,
            id='comma_in_value',
        ),
    ],
)
def test_parse_sample(text, expected_name, expected_labels, expected_value):
    sample = _parse_sample(text)
    assert sample.name == expected_name
    assert sample.labels == expected_labels
    assert sample.value == expected_value


def test_parse_sample_with_timestamp():
    sample = _parse_sample('test_metric 1.0 1234567890000')
    assert sample.name == 'test_metric'
    assert sample.value == 1.0
    assert sample.timestamp == 1234567890.0


@pytest.mark.parametrize(
    'text, expected_count',
    [
        pytest.param(
            '# HELP test_gauge A test gauge.\n# TYPE test_gauge gauge\ntest_gauge 42\n',
            1, id='simple',
        ),
        pytest.param(
            '# HELP gauge_one First.\n# TYPE gauge_one gauge\ngauge_one 1\n'
            '# HELP gauge_two Second.\n# TYPE gauge_two gauge\ngauge_two{env="prod"} 2\n',
            2, id='multiple_families',
        ),
    ],
)
def test_parse_full_metric_text(text, expected_count):
    from prometheus_client.parser import text_string_to_metric_families

    families = list(text_string_to_metric_families(text))
    assert len(families) == expected_count


def test_parse_full_labeled_metrics():
    from prometheus_client.parser import text_string_to_metric_families

    text = (
        '# HELP http_requests_total Total requests.\n'
        '# TYPE http_requests_total counter\n'
        'http_requests_total{method="GET",code="200"} 1027\n'
        'http_requests_total{method="POST",code="200"} 3\n'
    )
    families = list(text_string_to_metric_families(text))
    assert len(families) == 1
    assert len(families[0].samples) == 2
    assert families[0].samples[0].labels == {'method': 'GET', 'code': '200'}
    assert families[0].samples[0].value == 1027
    assert families[0].samples[1].labels == {'method': 'POST', 'code': '200'}


def test_parse_full_histogram():
    from prometheus_client.parser import text_string_to_metric_families

    text = (
        '# HELP rpc_duration_seconds RPC duration.\n'
        '# TYPE rpc_duration_seconds histogram\n'
        'rpc_duration_seconds_bucket{le="0.5"} 2000\n'
        'rpc_duration_seconds_bucket{le="1.0"} 2500\n'
        'rpc_duration_seconds_bucket{le="+Inf"} 3000\n'
        'rpc_duration_seconds_sum 5000\n'
        'rpc_duration_seconds_count 3000\n'
    )
    families = list(text_string_to_metric_families(text))
    assert len(families) == 1
    assert families[0].type == 'histogram'
    assert len(families[0].samples) == 5


def test_parse_full_escaped_label_value():
    from prometheus_client.parser import text_string_to_metric_families

    text = '# HELP test_metric A test.\n# TYPE test_metric gauge\ntest_metric{label="value with \\"quotes\\""} 1\n'
    families = list(text_string_to_metric_families(text))
    assert len(families) == 1
    assert families[0].samples[0].labels == {'label': 'value with "quotes"'}


def test_parse_full_empty_label_value():
    from prometheus_client.parser import text_string_to_metric_families

    text = '# HELP test_metric A test.\n# TYPE test_metric gauge\ntest_metric{label=""} 1\n'
    families = list(text_string_to_metric_families(text))
    assert families[0].samples[0].labels == {'label': ''}


def test_parse_full_newline_in_label_value():
    from prometheus_client.parser import text_string_to_metric_families

    text = '# HELP test_metric A test.\n# TYPE test_metric gauge\ntest_metric{label="line1\\nline2"} 1\n'
    families = list(text_string_to_metric_families(text))
    assert families[0].samples[0].labels == {'label': 'line1\nline2'}


def test_parse_full_comma_in_label_value():
    from prometheus_client.parser import text_string_to_metric_families

    text = (
        '# HELP apn_active_connections Active connections.\n'
        '# TYPE apn_active_connections gauge\n'
        'apn_active_connections{func="apn,gw",proto="tcp"} 8\n'
    )
    families = list(text_string_to_metric_families(text))
    assert len(families) == 1
    assert families[0].samples[0].labels == {'func': 'apn,gw', 'proto': 'tcp'}
    assert families[0].samples[0].value == 8
