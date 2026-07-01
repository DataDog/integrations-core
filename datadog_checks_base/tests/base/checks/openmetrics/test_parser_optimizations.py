# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Tests for the optimized _next_unquoted_char replacement.

Verifies that the optimized version produces the same results as the
original prometheus_client implementation across representative inputs.
"""

from datadog_checks.base.checks.openmetrics.parser_optimizations import (
    _next_unquoted_char,
)


class TestNextUnquotedChar:
    """Tests for the optimized _next_unquoted_char function."""

    def test_find_single_char(self):
        assert _next_unquoted_char('foo{bar="baz"} 1', '{') == 3

    def test_find_closing_brace(self):
        assert _next_unquoted_char('bar="baz"} 1', '}') == 9

    def test_find_equals(self):
        assert _next_unquoted_char('label="value"', '=') == 5

    def test_find_comma(self):
        assert _next_unquoted_char('a="1",b="2"', ',') == 5

    def test_find_space(self):
        assert _next_unquoted_char('metric{l="v"} 42', ' ') == 13

    def test_find_multiple_targets(self):
        assert _next_unquoted_char('label=value,next', '=,}') == 5

    def test_find_multiple_targets_comma_first(self):
        assert _next_unquoted_char('value,next=foo', '=,}') == 5

    def test_find_multiple_targets_brace(self):
        assert _next_unquoted_char('value}', '=,}') == 5

    def test_not_found(self):
        assert _next_unquoted_char('no_special_chars', '{') == -1

    def test_empty_string(self):
        assert _next_unquoted_char('', '{') == -1

    def test_startidx(self):
        assert _next_unquoted_char('a{b{c', '{', 2) == 3

    def test_startidx_at_target(self):
        assert _next_unquoted_char('a{b', '{', 1) == 1

    def test_startidx_past_end(self):
        assert _next_unquoted_char('abc', '{', 10) == -1

    def test_whitespace_default(self):
        assert _next_unquoted_char('foo bar', None) == 3

    def test_whitespace_tab(self):
        assert _next_unquoted_char('foo\tbar', None) == 3

    def test_first_char_is_target(self):
        assert _next_unquoted_char('{foo}', '{') == 0

    def test_last_char_is_target(self):
        assert _next_unquoted_char('foo}', '}') == 3

    def test_multiple_occurrences_returns_first(self):
        assert _next_unquoted_char('a{b{c', '{') == 1

    def test_skip_target_char_inside_quotes(self):
        # comma inside quoted value must not be returned
        assert _next_unquoted_char('a="apn,gw",b', ',') == 10

    def test_skip_brace_inside_quotes(self):
        assert _next_unquoted_char('label="val}ue"}', '}') == 14

    def test_skip_equals_inside_quotes(self):
        assert _next_unquoted_char('label="a=b"} 1', '}') == 11

    def test_escaped_quote_not_treated_as_delimiter(self):
        # backslash-escaped quote does not close the quoted region
        assert _next_unquoted_char(r'label="val\"still,inside",next', ',') == 25


class TestNextUnquotedCharWithRealMetrics:
    """Tests using real Prometheus metric line patterns."""

    def test_simple_gauge(self):
        line = 'envoy_server_live 1'
        assert _next_unquoted_char(line, '{') == -1
        assert _next_unquoted_char(line, ' ') == 17

    def test_labeled_metric(self):
        line = 'envoy_cluster_upstream_cx_active{envoy_cluster_name="service1"} 0'
        assert _next_unquoted_char(line, '{') == 32
        assert _next_unquoted_char(line, '}', 33) == 62

    def test_multi_label_metric(self):
        line = 'http_requests_total{method="GET",code="200"} 1027'
        assert _next_unquoted_char(line, '{') == 19
        assert _next_unquoted_char(line, '=', 20) == 26
        labels_text = 'method="GET",code="200"'
        assert _next_unquoted_char(labels_text, '=,}') == 6
        assert _next_unquoted_char(labels_text, ',}', 12) == 12

    def test_histogram_bucket(self):
        line = 'http_request_duration_seconds_bucket{le="0.5"} 24054'
        assert _next_unquoted_char(line, '{') == 36
        assert _next_unquoted_char(line, '}', 37) == 45

    def test_help_line_split(self):
        line = '# HELP http_requests_total The total number of HTTP requests.'
        assert _next_unquoted_char(line, None) == 1

    def test_type_line_split(self):
        line = '# TYPE http_requests_total counter'
        assert _next_unquoted_char(line, None) == 1


class TestParseFullMetricText:
    """Integration tests that parse complete metric text through the patched parser."""

    def test_parse_simple_metrics(self):
        from prometheus_client.parser import text_string_to_metric_families

        text = '# HELP test_gauge A test gauge.\n# TYPE test_gauge gauge\ntest_gauge 42\n'
        families = list(text_string_to_metric_families(text))
        assert len(families) == 1
        assert families[0].name == 'test_gauge'
        assert families[0].samples[0].value == 42

    def test_parse_labeled_metrics(self):
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

    def test_parse_histogram(self):
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

    def test_parse_escaped_label_value(self):
        from prometheus_client.parser import text_string_to_metric_families

        text = '# HELP test_metric A test.\n# TYPE test_metric gauge\ntest_metric{label="value with \\"quotes\\""} 1\n'
        families = list(text_string_to_metric_families(text))
        assert len(families) == 1
        assert families[0].samples[0].labels == {'label': 'value with "quotes"'}

    def test_parse_multiple_families(self):
        from prometheus_client.parser import text_string_to_metric_families

        text = (
            '# HELP gauge_one First.\n'
            '# TYPE gauge_one gauge\n'
            'gauge_one 1\n'
            '# HELP gauge_two Second.\n'
            '# TYPE gauge_two gauge\n'
            'gauge_two{env="prod"} 2\n'
        )
        families = list(text_string_to_metric_families(text))
        assert len(families) == 2
        assert families[0].name == 'gauge_one'
        assert families[1].name == 'gauge_two'

    def test_parse_empty_label_value(self):
        from prometheus_client.parser import text_string_to_metric_families

        text = '# HELP test_metric A test.\n# TYPE test_metric gauge\ntest_metric{label=""} 1\n'
        families = list(text_string_to_metric_families(text))
        assert families[0].samples[0].labels == {'label': ''}

    def test_parse_newline_in_label_value(self):
        from prometheus_client.parser import text_string_to_metric_families

        text = '# HELP test_metric A test.\n# TYPE test_metric gauge\ntest_metric{label="line1\\nline2"} 1\n'
        families = list(text_string_to_metric_families(text))
        assert families[0].samples[0].labels == {'label': 'line1\nline2'}

    def test_parse_comma_in_label_value(self):
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
