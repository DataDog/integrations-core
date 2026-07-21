# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import copy
import os
import socket
import time
from urllib.parse import urlparse

import mock
import pytest

from datadog_checks.base import OpenMetricsBaseCheck
from datadog_checks.base.errors import CheckException
from datadog_checks.haproxy import HAProxyCheck
from datadog_checks.haproxy.checkv2 import HaproxyCheckV2
from datadog_checks.haproxy.legacy.const import BUFSIZE, Services
from datadog_checks.haproxy.legacy.haproxy import HAProxyCheckLegacy, StickTable

from . import common
from .legacy import common as legacy_common

pytestmark = pytest.mark.unit

BASE_CONFIG = {'url': 'http://localhost/admin?stats', 'collect_status_metrics': True, 'enable_service_check': True}


def assert_agg_statuses(
    aggregator, count_status_by_service=True, collate_status_tags_per_host=False, disable_service_tag=False
):
    if disable_service_tag:
        expected_statuses = legacy_common.AGG_STATUSES_BY_SERVICE_DISABLE_SERVICE_TAG
    else:
        expected_statuses = (
            legacy_common.AGG_STATUSES_BY_SERVICE if count_status_by_service else legacy_common.AGG_STATUSES
        )
    for tags, value in expected_statuses:
        if collate_status_tags_per_host:
            aggregator.assert_metric('haproxy.count_per_status', tags=tags, count=0)
        else:
            aggregator.assert_metric('haproxy.count_per_status', value=value, tags=tags)


def mock_socket_responses(*calls):
    # Each call is either a single command's response text, or a tuple of response texts for a
    # multi-command batch (joined by the blank-line separator `_run_socket_commands` expects).
    side_effect = []
    for call in calls:
        body = '\n\n'.join(call) if isinstance(call, (list, tuple)) else call
        side_effect.append(body.encode('ascii'))
        side_effect.append(b'')
    return side_effect


def test_default_metric_limit_is_zero():
    # Kills the core/NumberReplacer mutant at check.py:12 (DEFAULT_METRIC_LIMIT 0 -> -1).
    assert HAProxyCheck.DEFAULT_METRIC_LIMIT == 0


def test_v2_default_metric_limit_is_zero():
    # Kills the core/NumberReplacer mutant at checkv2.py:13 (DEFAULT_METRIC_LIMIT 0 -> -1).
    assert HaproxyCheckV2.DEFAULT_METRIC_LIMIT == 0


def test_new_routes_first_instance_to_legacy_by_default():
    # Kills the core/NumberReplacer mutant at check.py:15 (instances[0] -> instances[-1]) and the
    # core/ReplaceFalseWithTrue mutant at check.py:19 (use_prometheus default False -> True) by
    # asserting the first, prometheus-less instance decides routing to the legacy implementation.
    haproxy_check = HAProxyCheck(
        'haproxy', {}, [{'url': 'http://localhost/stats'}, {'use_openmetrics': True}]
    )
    assert isinstance(haproxy_check, HAProxyCheckLegacy)


def test_new_routes_to_openmetrics_v2_when_requested():
    haproxy_check = HAProxyCheck('haproxy', {}, [{'use_openmetrics': True, 'openmetrics_endpoint': 'http://x/metrics'}])
    assert isinstance(haproxy_check, HaproxyCheckV2)


def test_default_instances_sets_histogram_and_monotonic_flags():
    # Kills the core/ReplaceTrueWithFalse mutants at check.py:34-36 (send_histograms_buckets,
    # send_distribution_counts_as_monotonic and send_distribution_sums_as_monotonic all default True).
    captured = {}

    def fake_init(self, name, init_config, instances, default_instances=None, default_namespace=None):
        captured['default_instances'] = default_instances

    with mock.patch.object(OpenMetricsBaseCheck, '__init__', fake_init):
        HAProxyCheck('haproxy', {}, [{'use_prometheus': True}])

    haproxy_defaults = captured['default_instances']['haproxy']
    assert haproxy_defaults['send_histograms_buckets'] is True
    assert haproxy_defaults['send_distribution_counts_as_monotonic'] is True
    assert haproxy_defaults['send_distribution_sums_as_monotonic'] is True


def test_bufsize_constant():
    # Kills the core/NumberReplacer mutants at legacy/const.py:10 (BUFSIZE 8192 -> 8191/8193).
    assert BUFSIZE == 8192


def test_sticktable_parse_valid_line():
    # Kills the core/RemoveDecorator mutant at haproxy.py:26 (@classmethod removed from StickTable.parse)
    # and the core/AddNot/ReplaceUnaryOperator_Delete_Not mutants at haproxy.py:29 (`if not items`).
    line = "# table: mybackend, type: ip, size:1000, used:5"
    assert StickTable.parse(line) == StickTable(name='mybackend', type='ip', size=1000, used=5)


def test_sticktable_parse_invalid_line_returns_none():
    assert StickTable.parse("this is not a stick table line") is None


def test_legacy_init_defaults(check):
    # Kills the core/ReplaceTrueWithFalse mutant at haproxy.py:41 (HTTP_CONFIG_REMAPPER invert True -> False).
    assert HAProxyCheckLegacy.HTTP_CONFIG_REMAPPER['disable_ssl_validation'] == {
        'name': 'tls_verify',
        'invert': True,
        'default': False,
    }

    haproxy_check = check({'url': 'http://localhost/stats'})
    # Kills the core/ReplaceFalseWithTrue mutant at haproxy.py:54 (collect_aggregates_only default True).
    assert haproxy_check.collect_aggregates_only is True
    # Kills the core/ReplaceTrueWithFalse mutant at haproxy.py:55 (collect_status_metrics default False).
    assert haproxy_check.collect_status_metrics is False
    # Kills the core/ReplaceTrueWithFalse mutant at haproxy.py:57 (collate_status_tags_per_host default False).
    assert haproxy_check.collate_status_tags_per_host is False
    # Kills the core/ReplaceTrueWithFalse mutant at haproxy.py:59 (tag_service_check_by_host default False).
    assert haproxy_check.tag_service_check_by_host is False
    # Kills the core/NumberReplacer mutants at haproxy.py:61 (startup_grace_seconds default 0 -> 1/-1).
    assert haproxy_check.startup_grace_period == 0
    # Kills the core/ReplaceTrueWithFalse mutant at haproxy.py:64 (active_tag default False).
    assert haproxy_check.include_active_tag is False


def test_run_socket_commands_uses_tcp_socket_for_tcp_scheme(check):
    # Kills the core/ReplaceComparisonOperator_Eq_* mutants at haproxy.py:167 (`scheme == 'tcp'`),
    # the core/NumberReplacer mutants at haproxy.py:170-171 (host/port index swap) and the
    # core/ReplaceBinaryOperator mutants at haproxy.py:177 (`b';'.join(commands) + b"\r\n"`).
    haproxy_check = check({'url': 'tcp://127.0.0.1:9999'})
    sock = mock.Mock()
    sock.recv.side_effect = mock_socket_responses('reply')
    with mock.patch('socket.socket', return_value=sock) as sock_ctor:
        haproxy_check._run_socket_commands(urlparse('tcp://127.0.0.1:9999'), (b'cmd',))
    sock_ctor.assert_called_once_with(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect.assert_called_once_with(('127.0.0.1', 9999))
    sock.send.assert_called_once_with(b'cmd\r\n')


def test_run_socket_commands_uses_unix_socket_for_unix_scheme(check):
    haproxy_check = check({'url': 'unix:///tmp/mock.sock'})
    sock = mock.Mock()
    sock.recv.side_effect = mock_socket_responses('reply')
    with mock.patch('socket.socket', return_value=sock) as sock_ctor:
        haproxy_check._run_socket_commands(urlparse('unix:///tmp/mock.sock'), (b'cmd',))
    sock_ctor.assert_called_once_with(socket.AF_UNIX, socket.SOCK_STREAM)
    sock.connect.assert_called_once_with('/tmp/mock.sock')


def test_run_socket_commands_raises_on_mismatched_response_count(check):
    # Kills the core/ReplaceComparisonOperator_NotEq_* and core/AddNot mutants at haproxy.py:188
    # (`len(responses) != len(commands)`) by sending fewer responses than requested commands.
    haproxy_check = check({'url': 'tcp://127.0.0.1:9999'})
    sock = mock.Mock()
    sock.recv.side_effect = mock_socket_responses('only one chunk')
    with mock.patch('socket.socket', return_value=sock):
        with pytest.raises(CheckException):
            haproxy_check._run_socket_commands(urlparse('tcp://127.0.0.1:9999'), (b'show info', b'show stat'))


def test_check_dispatches_to_socket_for_tcp_scheme(check):
    # Kills the core/ReplaceComparisonOperator_* and core/ReplaceOrWithAnd mutants at haproxy.py:72
    # (`parsed_url.scheme == 'unix' or parsed_url.scheme == 'tcp'`) by asserting a tcp:// url is
    # served over a socket, never over HTTP.
    instance = {'url': 'tcp://127.0.0.1:9999', 'collect_aggregates_only': False}
    haproxy_check = check(instance)
    sock = mock.Mock()
    sock.recv.side_effect = mock_socket_responses(('Uptime_sec: 100', '# pxname,svname,status,\na,FRONTEND,OPEN,'))
    with mock.patch('socket.socket', return_value=sock) as sock_ctor, mock.patch('requests.Session.get') as http_get:
        haproxy_check.check(instance)
    sock_ctor.assert_called()
    http_get.assert_not_called()


def test_check_dispatches_to_http_for_non_socket_scheme(check, haproxy_mock):
    instance = {'url': 'http://localhost/stats', 'collect_aggregates_only': False}
    haproxy_check = check(instance)
    with mock.patch('socket.socket') as sock_ctor:
        haproxy_check.check(instance)
    sock_ctor.assert_not_called()


def test_check_skips_processing_before_grace_period_elapses(check, aggregator):
    # Kills the core/ReplaceComparisonOperator_Lt_* and core/AddNot mutants at haproxy.py:84
    # (`uptime < self.startup_grace_period`) by asserting no metrics are submitted while the
    # collected socket uptime is still below the configured grace period.
    instance = {
        'url': 'tcp://127.0.0.1:9999',
        'collect_aggregates_only': False,
        'collect_status_metrics': True,
        'startup_grace_seconds': 999999,
    }
    haproxy_check = check(instance)
    sock = mock.Mock()
    sock.recv.side_effect = mock_socket_responses(('Uptime_sec: 100', '# pxname,svname,status,\na,FRONTEND,OPEN,'))
    with mock.patch('socket.socket', return_value=sock):
        haproxy_check.check(instance)
    assert aggregator.metric_names == []


def test_check_processes_after_grace_period_elapses(check, aggregator):
    instance = {
        'url': 'tcp://127.0.0.1:9999',
        'collect_aggregates_only': False,
        'collect_status_metrics': True,
        'startup_grace_seconds': 10,
    }
    haproxy_check = check(instance)
    sock = mock.Mock()
    sock.recv.side_effect = mock_socket_responses(('Uptime_sec: 100', '# pxname,svname,status,\na,FRONTEND,OPEN,'))
    with mock.patch('socket.socket', return_value=sock):
        haproxy_check.check(instance)
    aggregator.assert_metric('haproxy.count_per_status', value=1, tags=['status:open', 'service:a', 'haproxy_service:a'])


def test_check_processes_stick_table_metrics_when_tables_present(check, aggregator):
    # Kills the core/AddNot mutant at haproxy.py:87 (`if tables:`) by asserting stick table
    # metrics are only submitted once a non-empty table list has been collected over the socket.
    instance = {'url': 'tcp://127.0.0.1:9999'}
    haproxy_check = check(instance)
    sock = mock.Mock()
    sock.recv.side_effect = mock_socket_responses(
        ('Version: 2.1.0', '# pxname,svname,status,'), '# table: mybackend, type: ip, size:1000, used:5'
    )
    with mock.patch('socket.socket', return_value=sock):
        haproxy_check.check(instance)
    aggregator.assert_metric('haproxy.sticktable.size', value=1000, tags=['haproxy_service:mybackend', 'stick_type:ip'])
    aggregator.assert_metric('haproxy.sticktable.used', value=5, tags=['haproxy_service:mybackend', 'stick_type:ip'])


def test_set_metadata_skips_when_version_not_found(check, datadog_agent):
    # Kills the core/AddNot mutant at haproxy.py:95 (`if version:`) using a collection method
    # that returns a falsy version, which must not record any metadata.
    haproxy_check = check({'url': 'http://localhost/admin?stats'})
    haproxy_check.check_id = 'test:no-version'
    haproxy_check._set_metadata(lambda _: '', 'irrelevant raw info')
    datadog_agent.assert_metadata_count(0)


def test_set_metadata_records_version_when_found(check, datadog_agent):
    haproxy_check = check({'url': 'http://localhost/admin?stats'})
    haproxy_check.check_id = 'test:with-version'
    haproxy_check._set_metadata(lambda _: '2.1.0', 'irrelevant raw info')
    datadog_agent.assert_metadata(
        'test:with-version',
        {'version.scheme': 'semver', 'version.major': '2', 'version.minor': '1', 'version.patch': '0', 'version.raw': '2.1.0'},
    )


def test_fetch_url_data_builds_stats_url(check):
    # Kills the core/ReplaceBinaryOperator mutants at haproxy.py:104 (`"%s%s" % (self.url, STATS_URL)`).
    haproxy_check = check({'url': 'http://localhost/admin?stats'})
    with mock.patch('requests.Session.get', return_value=mock.Mock(content=b'line1\nline2')) as http_get:
        data = haproxy_check._fetch_url_data()
    assert http_get.call_args.args[0] == 'http://localhost/admin?stats/;csv;norefresh'
    assert data == ['line1', 'line2']


def test_decode_response_handles_bytes_and_str():
    # Kills the core/AddNot mutant at haproxy.py:119 (`if callable(decode_fn):`) by exercising
    # both a bytes response (decodable) and an already-decoded str response.
    assert HAProxyCheckLegacy._decode_response(mock.Mock(content=b'a\nb')) == ['a', 'b']
    assert HAProxyCheckLegacy._decode_response(mock.Mock(content='a\nb')) == ['a', 'b']


def test_parse_uptime_computes_seconds():
    # Kills the core/NumberReplacer and core/ReplaceBinaryOperator mutants at haproxy.py:128-131
    # (`days * 86400 + hours * 3600 + minutes * 60 + seconds`).
    seconds = HAProxyCheckLegacy._parse_uptime('uptime = 2d 3h4m5s')
    assert seconds == 2 * 86400 + 3 * 3600 + 4 * 60 + 5


def test_collect_info_from_http_finds_version_and_uptime(check):
    # Kills the core/AddNot mutants at haproxy.py:144,146,149,151 (substring checks and the
    # early-break once both version and uptime are found) and the core/ReplaceComparisonOperator_*
    # mutants at haproxy.py:155 (`raw_uptime == ""`).
    haproxy_check = check({'url': 'http://the_url_does_not_matter/'})
    content = b"HAProxy version 2.1.0, released\nuptime = 1d 0h0m0s\n"
    with mock.patch('requests.Session.get', return_value=mock.Mock(content=content)):
        uptime = haproxy_check._collect_info_from_http()
    assert uptime == 86400


def test_collect_info_from_http_without_uptime_line(check):
    haproxy_check = check({'url': 'http://the_url_does_not_matter/'})
    content = b"nothing useful here\n"
    with mock.patch('requests.Session.get', return_value=mock.Mock(content=content)):
        uptime = haproxy_check._collect_info_from_http()
    assert uptime is None


def test_fetch_socket_data_sends_show_table_for_supported_versions(check):
    # Kills the core/ReplaceComparisonOperator_* and core/ReplaceAndWithOr mutants at haproxy.py:209
    # (`len(haproxy_major_version) == 2 and haproxy_major_version >= (1, 5)`).
    haproxy_check = check({'url': 'tcp://127.0.0.1:9999'})
    sock = mock.Mock()
    sock.recv.side_effect = mock_socket_responses(
        ('Version: 2.1.0', '# pxname,svname,status,'), '# table: mybackend, type: ip, size:1000, used:5'
    )
    with mock.patch('socket.socket', return_value=sock):
        info, stat, tables = haproxy_check._fetch_socket_data(urlparse('tcp://127.0.0.1:9999'))
    assert tables == ['# table: mybackend, type: ip, size:1000, used:5']


def test_fetch_socket_data_skips_show_table_for_unsupported_versions(check):
    haproxy_check = check({'url': 'tcp://127.0.0.1:9999'})
    sock = mock.Mock()
    sock.recv.side_effect = mock_socket_responses(('Version: 1.4.0', '# pxname,svname,status,'))
    with mock.patch('socket.socket', return_value=sock):
        info, stat, tables = haproxy_check._fetch_socket_data(urlparse('tcp://127.0.0.1:9999'))
    assert tables == []


def test_fetch_socket_data_handles_missing_version(check):
    # Kills the core/ExceptionReplacer mutant at haproxy.py:211 (`except (IndexError, ValueError)`)
    # using an info payload without a `Version` key, which makes version parsing raise ValueError.
    haproxy_check = check({'url': 'tcp://127.0.0.1:9999'})
    sock = mock.Mock()
    sock.recv.side_effect = mock_socket_responses(('Uptime_sec: 5', '# pxname,svname,status,'))
    with mock.patch('socket.socket', return_value=sock):
        info, stat, tables = haproxy_check._fetch_socket_data(urlparse('tcp://127.0.0.1:9999'))
    assert tables == []


def test_fetch_socket_data_handles_empty_table_response(check):
    # Kills the core/ExceptionReplacer mutant at haproxy.py:213 (`except CheckException`) using a
    # supported version whose "show table" call returns no output at all.
    haproxy_check = check({'url': 'tcp://127.0.0.1:9999'})
    sock = mock.Mock()
    sock.recv.side_effect = [
        b'Version: 2.1.0\n\n# pxname,svname,status,\n\n',
        b'',
        b'',
    ]
    with mock.patch('socket.socket', return_value=sock):
        info, stat, tables = haproxy_check._fetch_socket_data(urlparse('tcp://127.0.0.1:9999'))
    assert tables == []


def test_collect_uptime_from_socket_finds_uptime_key(check):
    # Kills the core/ZeroIterationForLoop mutant at haproxy.py:220 and the core/ReplaceComparisonOperator_*
    # mutants at haproxy.py:222 (`key == 'Uptime_sec'`).
    haproxy_check = check({'url': 'tcp://127.0.0.1:9999'})
    assert haproxy_check._collect_uptime_from_socket(['Some: other', 'Uptime_sec: 42']) == 42


def test_sanitize_lines_merges_quoted_newlines():
    # Kills the core/NumberReplacer mutants at haproxy.py:311,315,320,327 (double-quote counters)
    # and the core/ReplaceComparisonOperator_Is_* mutants at haproxy.py:314 (`c is char`).
    data = ['a,"b', 'c",d', 'e,f']
    assert HAProxyCheckLegacy._sanitize_lines(data) == ['a,"bc",d', 'e,f']


def test_gather_quoted_values_merges_embedded_commas():
    # Kills the core/AddNot mutant at haproxy.py:356 (`val.startswith('"') and not val.endswith('"')`)
    # and the core/ReplaceBinaryOperator mutant at haproxy.py:360 (`previous + val`).
    values = ['a', '"b', 'c"', 'd']
    assert HAProxyCheckLegacy._gather_quoted_values(values) == ['a', '"bc"', 'd']


def test_line_to_dict_parses_values_and_normalizes_status(check):
    haproxy_check = check({'url': 'http://localhost/admin?stats'})
    fields = ['pxname', 'svname', 'status']
    data_dict = haproxy_check._line_to_dict(fields, 'a,i-1,UP 1/2,')
    assert data_dict == {'pxname': 'a', 'svname': 'i-1', 'status': 'up'}


def test_update_data_dict_computes_session_pct():
    # Kills the core/ReplaceBinaryOperator_Div_Mul mutant at haproxy.py:377 (`(scur / slim) * 100`).
    data_dict = {'scur': 5.0, 'slim': 20.0}
    HAProxyCheckLegacy._update_data_dict(data_dict, 'BACKEND')
    assert data_dict['spct'] == 25.0
    assert data_dict['back_or_front'] == 'BACKEND'


def test_update_data_dict_ignores_division_errors():
    # Kills the core/ExceptionReplacer mutant at haproxy.py:378 (`except (TypeError, ZeroDivisionError)`).
    data_dict = {'scur': 5.0, 'slim': 0.0}
    HAProxyCheckLegacy._update_data_dict(data_dict, 'BACKEND')
    assert 'spct' not in data_dict


def test_is_aggregate_matches_frontend_and_backend_only():
    # Kills the core/RemoveDecorator mutant at haproxy.py:381 (@staticmethod removed from _is_aggregate).
    assert HAProxyCheckLegacy._is_aggregate({'svname': 'FRONTEND'}) is True
    assert HAProxyCheckLegacy._is_aggregate({'svname': 'BACKEND'}) is True
    assert HAProxyCheckLegacy._is_aggregate({'svname': 'i-1'}) is False


def test_should_process_respects_collect_aggregates_only_modes(check):
    # Kills the core/AddNot mutant at haproxy.py:397 and the core/ReplaceComparisonOperator_NotEq_*
    # mutants at haproxy.py:399,402 (`_should_process` branch dispatch).
    aggregates_only = check({'url': 'http://localhost/admin?stats', 'collect_aggregates_only': True})
    assert aggregates_only._should_process({'svname': 'BACKEND'}) is True
    assert aggregates_only._should_process({'svname': 'i-1'}) is False

    both = check({'url': 'http://localhost/admin?stats', 'collect_aggregates_only': 'both'})
    assert both._should_process({'svname': 'BACKEND'}) is True

    hosts_only = check({'url': 'http://localhost/admin?stats', 'collect_aggregates_only': False})
    assert hosts_only._should_process({'svname': 'BACKEND'}) is False
    assert hosts_only._should_process({'svname': 'i-1'}) is True


def test_tag_match_patterns_without_filters_returns_false():
    # Kills the core/AddNot mutant at haproxy.py:413 (`if not filters:`).
    assert HAProxyCheckLegacy._tag_match_patterns('svc', []) is False


def test_tag_match_patterns_matches_any_rule():
    assert HAProxyCheckLegacy._tag_match_patterns('svc-1', ['^other$', r'^svc-\d+$']) is True


def test_tag_from_regex_without_regex_or_service_name(check):
    # Kills the core/ReplaceUnaryOperator_Delete_Not and core/ReplaceOrWithAnd mutants at haproxy.py:427
    # (`if not self.tags_regex or not service_name:`).
    without_regex = check({'url': 'http://localhost/admin?stats'})
    assert without_regex._tag_from_regex('anything') == []

    with_regex = check({'url': 'http://localhost/admin?stats', 'tags_regex': r'(?P<x>.*)'})
    assert with_regex._tag_from_regex('') == []


def test_tag_from_regex_returns_empty_when_no_match(check):
    # Kills the core/AddNot mutant at haproxy.py:432 (`if not match:`).
    haproxy_check = check({'url': 'http://localhost/admin?stats', 'tags_regex': r'^only_(?P<x>[a-z]+)$'})
    assert haproxy_check._tag_from_regex('nomatch-here') == []


def test_normalize_status_matches_known_prefix():
    # Kills the core/RemoveDecorator mutant at haproxy.py:439 (@staticmethod removed from _normalize_status)
    # and the core/AddNot mutant at haproxy.py:449 (`if formatted_status.startswith(normalized_status):`).
    assert HAProxyCheckLegacy._normalize_status('UP 1/2') == 'up'
    assert HAProxyCheckLegacy._normalize_status('no check') == 'no_check'


def test_service_exclusion_filtering(check, aggregator, haproxy_mock):
    # Kills the core/ReplaceTrueWithFalse/ReplaceFalseWithTrue mutants at haproxy.py:406-408
    # (`_is_service_excl_filtered`) using a service that is excluded and must produce no metrics.
    config = {'url': 'http://localhost/admin?stats', 'collect_status_metrics': True, 'services_exclude': ['^b$']}
    haproxy_check = check(config)
    haproxy_check.check(config)
    aggregator.assert_metric(
        'haproxy.backend_hosts', tags=['haproxy_service:b', 'service:b', 'available:true'], count=0
    )


def test_service_inclusion_overrides_exclusion(check, aggregator, haproxy_mock):
    config = {
        'url': 'http://localhost/admin?stats',
        'collect_status_metrics': True,
        'services_exclude': ['^b$'],
        'services_include': ['^b$'],
    }
    haproxy_check = check(config)
    haproxy_check.check(config)
    aggregator.assert_metric(
        'haproxy.backend_hosts', tags=['haproxy_service:b', 'service:b', 'available:true'], count=1
    )


def test_submit_metric_tuple_dispatches_rate_vs_gauge(check, aggregator):
    # Kills the core/ReplaceComparisonOperator_* mutants at haproxy.py:594 (`metric_type == 'rate'`)
    # and the core/ReplaceBinaryOperator mutants at haproxy.py:592 (`"haproxy.%s.%s" % (...)`).
    haproxy_check = check({'url': 'http://localhost/admin?stats'})
    haproxy_check._submit_metric_tuple('rate', 'session.rate', 'BACKEND', '5', ['t:1'])
    haproxy_check._submit_metric_tuple('gauge', 'session.current', 'BACKEND', '5', ['t:1'])
    aggregator.assert_metric('haproxy.backend.session.rate', metric_type=aggregator.RATE, value=5, tags=['t:1'])
    aggregator.assert_metric('haproxy.backend.session.current', metric_type=aggregator.GAUGE, value=5, tags=['t:1'])


def test_process_stick_table_metrics_skips_unparseable_lines(check, aggregator):
    # Kills the core/ReplaceBreakWithContinue mutant at haproxy.py:608 and the core/ReplaceBinaryOperator
    # mutants at haproxy.py:612 (`"haproxy_service:%s" % table.name`).
    haproxy_check = check({'url': 'http://localhost/admin?stats'})
    haproxy_check._process_stick_table_metrics(['not a table line', '# table: mytable, type: ip, size:10, used:2'])
    aggregator.assert_metric('haproxy.sticktable.size', value=10, tags=['haproxy_service:mytable', 'stick_type:ip'])
    assert len(aggregator.metric_names) == 2


def test_process_stick_table_metrics_respects_exclusion_filter(check, aggregator):
    # Kills the core/AddNot mutant at haproxy.py:609 (`if self._is_service_excl_filtered(table.name):`).
    haproxy_check = check({'url': 'http://localhost/admin?stats', 'services_exclude': ['^mytable$']})
    haproxy_check._process_stick_table_metrics(['# table: mytable, type: ip, size:10, used:2'])
    assert aggregator.metric_names == []


def test_create_event_for_down_status(check):
    # Kills the core/ReplaceComparisonOperator_Eq_* mutants at haproxy.py:655,659 (`status == 'down'`/`'up'`)
    # and the core/ReplaceBinaryOperator mutants at haproxy.py:657,665,667,672 (title/tag/timestamp formatting).
    haproxy_check = check({'url': 'http://localhost/admin?stats'})
    haproxy_check.hostname = 'myhost'
    with mock.patch('time.time', return_value=1000.0):
        event = haproxy_check._create_event('down', 'i-4', 30, 'b', Services.BACKEND, custom_tags=['env:prod'])
    assert event['alert_type'] == 'error'
    assert event['msg_title'] == 'myhost reported b:i-4 DOWN'
    assert event['tags'] == ['haproxy_service:b', 'backend:i-4', 'env:prod', 'service:b']
    assert event['timestamp'] == 970


def test_create_event_for_up_status(check):
    haproxy_check = check({'url': 'http://localhost/admin?stats'})
    haproxy_check.hostname = 'myhost'
    event = haproxy_check._create_event('up', 'i-4', 0, 'b', Services.BACKEND)
    assert event['alert_type'] == 'success'
    assert event['msg_title'] == 'myhost reported b:i-4 back and UP'


def test_create_event_for_other_status(check):
    haproxy_check = check({'url': 'http://localhost/admin?stats'})
    haproxy_check.hostname = 'myhost'
    event = haproxy_check._create_event('maint', 'i-4', 0, 'b', Services.BACKEND)
    assert event['alert_type'] == 'info'


def test_process_event_fires_on_first_observed_up_or_down_status(check, aggregator):
    # Kills the core/AddNot mutant at haproxy.py:633 (`if status is None:`) and the comparison/AddNot
    # mutants at haproxy.py:637 (`status != data_status and data_status in ('up', 'down')`).
    haproxy_check = check({'url': 'http://localhost/admin?stats'})
    haproxy_check.hostname = 'myhost'
    data = {'svname': 'i-4', 'pxname': 'b', 'status': 'down', 'back_or_front': 'BACKEND', 'lastchg': '30'}
    haproxy_check._process_event(data)
    assert len(aggregator.events) == 1
    assert aggregator.events[0]['msg_title'] == 'myhost reported b:i-4 DOWN'


def test_process_event_skips_non_up_down_status(check, aggregator):
    haproxy_check = check({'url': 'http://localhost/admin?stats'})
    data = {'svname': 'i-4', 'pxname': 'b', 'status': 'maint', 'back_or_front': 'BACKEND', 'lastchg': '30'}
    haproxy_check._process_event(data)
    assert aggregator.events == []


def test_process_event_skips_unchanged_status_on_second_call(check, aggregator):
    haproxy_check = check({'url': 'http://localhost/admin?stats'})
    data = {'svname': 'i-4', 'pxname': 'b', 'status': 'down', 'back_or_front': 'BACKEND', 'lastchg': '30'}
    haproxy_check._process_event(data)
    haproxy_check._process_event(data)
    assert len(aggregator.events) == 1


def test_process_service_check_ok_status_has_no_message(check, aggregator):
    # Kills the core/ReplaceComparisonOperator_IsNot_* mutants at haproxy.py:707
    # (`status is not AgentCheck.OK`) using an `up` status, which must not produce a message.
    haproxy_check = check({'url': 'http://localhost/admin?stats'})
    haproxy_check.hostname = 'myhost'
    data = {'pxname': 'b', 'svname': 'i-1', 'status': 'up', 'back_or_front': 'BACKEND'}
    haproxy_check._process_service_check(data)
    checks = aggregator.service_checks('haproxy.backend_up')
    assert len(checks) == 1
    assert checks[0].message == ''


def test_process_service_check_non_ok_status_has_message(check, aggregator):
    haproxy_check = check({'url': 'http://localhost/admin?stats'})
    haproxy_check.hostname = 'myhost'
    data = {'pxname': 'b', 'svname': 'i-1', 'status': 'down', 'back_or_front': 'BACKEND'}
    haproxy_check._process_service_check(data)
    checks = aggregator.service_checks('haproxy.backend_up')
    assert len(checks) == 1
    assert checks[0].message != ''


def test_handle_legacy_service_tag_appends_by_default(check):
    # Kills the core/AddNot and default-value mutants at haproxy.py:714-715
    # (`if not self.instance.get('disable_legacy_service_tag', False):`).
    haproxy_check = check({'url': 'http://localhost/admin?stats'})
    tags = []
    haproxy_check._handle_legacy_service_tag(tags, 'myservice')
    assert tags == ['service:myservice']


def test_handle_legacy_service_tag_skips_when_disabled(check):
    haproxy_check = check({'url': 'http://localhost/admin?stats', 'disable_legacy_service_tag': True})
    tags = []
    haproxy_check._handle_legacy_service_tag(tags, 'myservice')
    assert tags == []


def test_count_per_status_agg_only(aggregator, check, haproxy_mock):
    config = copy.deepcopy(BASE_CONFIG)
    config['count_status_by_service'] = False

    haproxy_check = check(config)
    haproxy_check.check(config)

    aggregator.assert_metric('haproxy.count_per_status', value=2, tags=['status:open'])
    aggregator.assert_metric('haproxy.count_per_status', value=4, tags=['status:up'])
    aggregator.assert_metric('haproxy.count_per_status', value=2, tags=['status:down'])
    aggregator.assert_metric('haproxy.count_per_status', value=1, tags=['status:maint'])
    aggregator.assert_metric('haproxy.count_per_status', value=0, tags=['status:nolb'])
    aggregator.assert_metric('haproxy.count_per_status', value=1, tags=['status:no_check'])

    assert_agg_statuses(aggregator, count_status_by_service=False)


def test_count_per_status_by_service(aggregator, check, haproxy_mock):
    config = copy.deepcopy(BASE_CONFIG)
    haproxy_check = check(config)
    haproxy_check.check(config)

    aggregator.assert_metric(
        'haproxy.count_per_status', value=1, tags=['status:open', 'service:a', 'haproxy_service:a']
    )
    aggregator.assert_metric('haproxy.count_per_status', value=3, tags=['status:up', 'service:b', 'haproxy_service:b'])
    aggregator.assert_metric(
        'haproxy.count_per_status', value=1, tags=['status:open', 'service:b', 'haproxy_service:b']
    )
    aggregator.assert_metric(
        'haproxy.count_per_status', value=1, tags=['status:down', 'service:b', 'haproxy_service:b']
    )
    aggregator.assert_metric(
        'haproxy.count_per_status', value=1, tags=['status:maint', 'service:b', 'haproxy_service:b']
    )
    tags = [
        'status:up',
        'service:be_edge_http_sre-production_elk-kibana',
        'haproxy_service:be_edge_http_sre-production_elk-kibana',
    ]
    aggregator.assert_metric('haproxy.count_per_status', value=1, tags=tags)
    tags = [
        'status:down',
        'service:be_edge_http_sre-production_elk-kibana',
        'haproxy_service:be_edge_http_sre-production_elk-kibana',
    ]
    aggregator.assert_metric('haproxy.count_per_status', value=1, tags=tags)
    tags = [
        'status:no_check',
        'service:be_edge_http_sre-production_elk-kibana',
        'haproxy_service:be_edge_http_sre-production_elk-kibana',
    ]
    aggregator.assert_metric('haproxy.count_per_status', value=1, tags=tags)
    assert_agg_statuses(aggregator)


def test_count_per_status_by_service_and_host(aggregator, check, haproxy_mock):
    config = copy.deepcopy(BASE_CONFIG)
    config['collect_status_metrics_by_host'] = True
    haproxy_check = check(config)
    haproxy_check.check(config)

    tags = ['backend:FRONTEND', 'status:open', 'service:a', 'haproxy_service:a']
    aggregator.assert_metric('haproxy.count_per_status', value=1, tags=tags)
    tags = ['backend:FRONTEND', 'status:open', 'service:b', 'haproxy_service:b']
    aggregator.assert_metric('haproxy.count_per_status', value=1, tags=tags)
    for backend in ['i-1', 'i-2', 'i-3']:
        tags = ['backend:%s' % backend, 'status:up', 'service:b', 'haproxy_service:b']
        aggregator.assert_metric('haproxy.count_per_status', value=1, tags=tags)
    tags = ['backend:i-4', 'status:down', 'service:b', 'haproxy_service:b']
    aggregator.assert_metric('haproxy.count_per_status', value=1, tags=tags)
    tags = ['backend:i-5', 'status:maint', 'service:b', 'haproxy_service:b']
    aggregator.assert_metric('haproxy.count_per_status', value=1, tags=tags)
    tags = [
        'backend:i-1',
        'status:up',
        'service:be_edge_http_sre-production_elk-kibana',
        'haproxy_service:be_edge_http_sre-production_elk-kibana',
    ]
    aggregator.assert_metric('haproxy.count_per_status', value=1, tags=tags)
    tags = [
        'backend:i-2',
        'status:down',
        'service:be_edge_http_sre-production_elk-kibana',
        'haproxy_service:be_edge_http_sre-production_elk-kibana',
    ]
    aggregator.assert_metric('haproxy.count_per_status', value=1, tags=tags)
    tags = [
        'backend:i-3',
        'status:no_check',
        'service:be_edge_http_sre-production_elk-kibana',
        'haproxy_service:be_edge_http_sre-production_elk-kibana',
    ]
    aggregator.assert_metric('haproxy.count_per_status', value=1, tags=tags)

    assert_agg_statuses(aggregator)


def test_count_per_status_by_service_and_collate_per_host(aggregator, check, haproxy_mock):
    config = copy.deepcopy(BASE_CONFIG)
    config['collect_status_metrics_by_host'] = True
    config['collate_status_tags_per_host'] = True
    haproxy_check = check(config)
    haproxy_check.check(config)

    tags = ['backend:FRONTEND', 'status:available', 'service:a', 'haproxy_service:a']
    aggregator.assert_metric('haproxy.count_per_status', value=1, tags=tags)
    tags = ['backend:FRONTEND', 'status:available', 'service:b', 'haproxy_service:b']
    aggregator.assert_metric('haproxy.count_per_status', value=1, tags=tags)
    for backend in ['i-1', 'i-2', 'i-3']:
        tags = ['backend:%s' % backend, 'status:available', 'service:b', 'haproxy_service:b']
        aggregator.assert_metric('haproxy.count_per_status', value=1, tags=tags)
    tags = ['backend:i-4', 'status:unavailable', 'service:b', 'haproxy_service:b']
    aggregator.assert_metric('haproxy.count_per_status', value=1, tags=tags)
    tags = ['backend:i-5', 'status:unavailable', 'service:b', 'haproxy_service:b']
    aggregator.assert_metric('haproxy.count_per_status', value=1, tags=tags)
    tags = [
        'backend:i-1',
        'status:available',
        'service:be_edge_http_sre-production_elk-kibana',
        'haproxy_service:be_edge_http_sre-production_elk-kibana',
    ]
    aggregator.assert_metric('haproxy.count_per_status', value=1, tags=tags)
    tags = [
        'backend:i-2',
        'status:unavailable',
        'service:be_edge_http_sre-production_elk-kibana',
        'haproxy_service:be_edge_http_sre-production_elk-kibana',
    ]
    aggregator.assert_metric('haproxy.count_per_status', value=1, tags=tags)
    tags = [
        'backend:i-3',
        'status:unavailable',
        'service:be_edge_http_sre-production_elk-kibana',
        'haproxy_service:be_edge_http_sre-production_elk-kibana',
    ]
    aggregator.assert_metric('haproxy.count_per_status', value=1, tags=tags)

    assert_agg_statuses(aggregator, collate_status_tags_per_host=True)


def test_count_per_status_by_service_and_collate_per_host_evil(aggregator, check, haproxy_mock_evil):
    # Reuses the pathological quoted/newline CSV fixture to exercise `_sanitize_lines` and
    # `_gather_quoted_values` (haproxy.py:306-366) end-to-end through a full check run.
    config = copy.deepcopy(BASE_CONFIG)
    config['collect_status_metrics_by_host'] = True
    config['collate_status_tags_per_host'] = True
    haproxy_check = check(config)
    haproxy_check.check(config)

    tags = ['backend:FRONTEND', 'status:available', 'service:a', 'haproxy_service:a']
    aggregator.assert_metric('haproxy.count_per_status', value=1, tags=tags)
    tags = ['backend:FRONTEND', 'status:available', 'service:b', 'haproxy_service:b']
    aggregator.assert_metric('haproxy.count_per_status', value=1, tags=tags)
    for backend in ['i-1', 'i-2', 'i-3']:
        tags = ['backend:%s' % backend, 'status:available', 'service:b', 'haproxy_service:b']
        aggregator.assert_metric('haproxy.count_per_status', value=1, tags=tags)
    tags = ['backend:i-4', 'status:unavailable', 'service:b', 'haproxy_service:b']
    aggregator.assert_metric('haproxy.count_per_status', value=1, tags=tags)
    tags = ['backend:i-5', 'status:unavailable', 'service:b', 'haproxy_service:b']
    aggregator.assert_metric('haproxy.count_per_status', value=1, tags=tags)

    assert_agg_statuses(aggregator, collate_status_tags_per_host=True)


def test_count_per_status_collate_per_host(aggregator, check, haproxy_mock):
    config = copy.deepcopy(BASE_CONFIG)
    config['collect_status_metrics_by_host'] = True
    config['collate_status_tags_per_host'] = True
    config['count_status_by_service'] = False
    haproxy_check = check(config)
    haproxy_check.check(config)

    aggregator.assert_metric('haproxy.count_per_status', value=2, tags=['backend:FRONTEND', 'status:available'])
    aggregator.assert_metric('haproxy.count_per_status', value=2, tags=['backend:i-1', 'status:available'])
    aggregator.assert_metric('haproxy.count_per_status', value=1, tags=['backend:i-2', 'status:available'])
    aggregator.assert_metric('haproxy.count_per_status', value=1, tags=['backend:i-2', 'status:unavailable'])
    aggregator.assert_metric('haproxy.count_per_status', value=1, tags=['backend:i-3', 'status:available'])
    aggregator.assert_metric('haproxy.count_per_status', value=1, tags=['backend:i-3', 'status:unavailable'])
    aggregator.assert_metric('haproxy.count_per_status', value=1, tags=['backend:i-4', 'status:unavailable'])
    aggregator.assert_metric('haproxy.count_per_status', value=1, tags=['backend:i-5', 'status:unavailable'])

    assert_agg_statuses(aggregator, count_status_by_service=False, collate_status_tags_per_host=True)


def test_count_hosts_statuses_per_host_no_events(aggregator, check, haproxy_mock, mock_data):
    # Kills the core/AddNot mutants at haproxy.py:386,388,389 (`_update_hosts_statuses_if_needed`).
    config = copy.deepcopy(BASE_CONFIG)
    config.update(
        {
            'collect_aggregates_only': True,
            'process_events': False,
            'collect_status_metrics': True,
            'collect_status_metrics_by_host': True,
        }
    )
    haproxy_check = check(config)
    haproxy_check.check(config)
    haproxy_check._process_data(mock_data)

    expected_hosts_statuses = {
        ('b', 'FRONTEND', 'FRONTEND', 'open'): 1,
        ('a', 'FRONTEND', 'FRONTEND', 'open'): 1,
        ('b', 'BACKEND', 'i-1', 'up'): 1,
        ('b', 'BACKEND', 'i-2', 'up'): 1,
        ('b', 'BACKEND', 'i-3', 'up'): 1,
        ('b', 'BACKEND', 'i-4', 'down'): 1,
        ('b', 'BACKEND', 'i-5', 'maint'): 1,
    }
    assert dict(haproxy_check.hosts_statuses) == expected_hosts_statuses


def test_optional_tags(aggregator, check, haproxy_mock):
    config = copy.deepcopy(BASE_CONFIG)
    config['tags'] = ['new-tag', 'my:new:tag']
    haproxy_check = check(config)
    haproxy_check.check(config)

    aggregator.assert_metric_has_tag('haproxy.backend.session.current', 'new-tag')
    aggregator.assert_metric_has_tag('haproxy.backend.session.current', 'my:new:tag')
    aggregator.assert_metric_has_tag('haproxy.count_per_status', 'my:new:tag')
    tags = ['service:a', 'haproxy_service:a', 'new-tag', 'my:new:tag', 'backend:BACKEND']
    aggregator.assert_service_check('haproxy.backend_up', tags=tags)


def test_regex_tags(aggregator, check, haproxy_mock):
    # Kills the core/ReplaceBinaryOperator mutants at haproxy.py:437 (`"%s:%s" % (name, value)`).
    config = copy.deepcopy(BASE_CONFIG)
    config['tags'] = ['region:infra']
    config['tags_regex'] = r'be_(?P<security>edge_http|http)?_(?P<team>[a-z]+)\-(?P<env>[a-z]+)_(?P<app>.*)'
    haproxy_check = check(config)
    haproxy_check.check(config)

    expected_tags = [
        'service:be_edge_http_sre-production_elk-kibana',
        'haproxy_service:be_edge_http_sre-production_elk-kibana',
        'type:BACKEND',
        'instance_url:http://localhost/admin?stats',
        'region:infra',
        'security:edge_http',
        'app:elk-kibana',
        'env:production',
        'team:sre',
        'backend:BACKEND',
    ]

    aggregator.assert_metric('haproxy.backend.session.current', value=1, count=1, tags=expected_tags)
    aggregator.assert_metric_has_tag('haproxy.backend.session.current', 'app:elk-kibana', 1)


def test_version_failure(aggregator, check, datadog_agent):
    config = copy.deepcopy(BASE_CONFIG)
    haproxy_check = check(config)
    filepath = os.path.join(common.HERE, 'fixtures', 'mock_data')
    with open(filepath, 'rb') as f:
        data = f.read()
    with mock.patch('requests.Session.get') as m:
        m.side_effect = [RuntimeError("Ooops"), mock.Mock(content=data)]
        haproxy_check.check(config)

    # Version failed, but we should have some metrics
    aggregator.assert_metric(
        'haproxy.count_per_status', value=1, tags=['status:open', 'service:a', 'haproxy_service:a']
    )
    # But no metadata
    datadog_agent.assert_metadata_count(0)


def test_count_per_status_by_service_disable_service_tag(aggregator, check, haproxy_mock):
    config = copy.deepcopy(BASE_CONFIG)
    config['disable_legacy_service_tag'] = True
    haproxy_check = check(config)
    haproxy_check.check(config)

    aggregator.assert_metric('haproxy.count_per_status', value=1, tags=['status:open', 'haproxy_service:a'])
    aggregator.assert_metric('haproxy.count_per_status', value=3, tags=['status:up', 'haproxy_service:b'])
    aggregator.assert_metric('haproxy.count_per_status', value=1, tags=['status:open', 'haproxy_service:b'])
    aggregator.assert_metric('haproxy.count_per_status', value=1, tags=['status:down', 'haproxy_service:b'])
    aggregator.assert_metric('haproxy.count_per_status', value=1, tags=['status:maint', 'haproxy_service:b'])
    tags = ['status:up', 'haproxy_service:be_edge_http_sre-production_elk-kibana']
    aggregator.assert_metric('haproxy.count_per_status', value=1, tags=tags)
    tags = ['status:down', 'haproxy_service:be_edge_http_sre-production_elk-kibana']
    aggregator.assert_metric('haproxy.count_per_status', value=1, tags=tags)
    tags = ['status:no_check', 'haproxy_service:be_edge_http_sre-production_elk-kibana']
    aggregator.assert_metric('haproxy.count_per_status', value=1, tags=tags)
    assert_agg_statuses(aggregator, disable_service_tag=True)


def test_enterprise_version_collection(datadog_agent, check, haproxy_mock_enterprise_version_info):
    haproxy_check = check(copy.deepcopy(BASE_CONFIG))
    haproxy_check.check_id = 'test:123'
    haproxy_check._collect_info_from_http()
    expected_version_metadata = {
        'version.scheme': 'semver',
        'version.major': '2',
        'version.minor': '1',
        'version.patch': '0',
        'version.raw': '2.1.0-1.0.0-223.130',
        'version.release': '1.0.0',
    }
    datadog_agent.assert_metadata('test:123', expected_version_metadata)


@pytest.mark.parametrize(
    "response",
    [
        pytest.param("Key: 0\n\n# attr1,attr2\n", id="normal"),
        pytest.param("Key: 0\n\n# attr1,attr2\n\n", id="extra-newline"),
        pytest.param("Key: 0\n\n# attr1,attr2", id="missing-newline"),
    ],
)
def test_response_parsing(check, response):
    """
    The Unix socket response parsing logic must be lenient enough on missing or extra newlines.
    """
    instance = {
        'url': 'unix:///tmp/mock.sock',
        'collect_aggregates_only': False,
    }
    haproxy_check = check(instance)
    sock = mock.Mock()
    sock.recv.side_effect = [response.encode('utf-8'), b'']
    with mock.patch('socket.socket', return_value=sock):
        haproxy_check.check(instance)
