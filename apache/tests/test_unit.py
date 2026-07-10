# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import mock
import pytest

from datadog_checks.apache import Apache

pytestmark = pytest.mark.unit


def mock_response(lines, headers=None):
    response = mock.MagicMock()
    response.iter_lines.return_value = lines
    response.headers = headers or {}
    return response


def test_disable_ssl_validation_default_enables_tls_verify(check):
    # Kills the core/ReplaceFalseWithTrue mutant at apache.py:51 (disable_ssl_validation default False -> True).
    check = check({'apache_status_url': 'http://myhost:1234/server-status'})
    assert check.http.options['verify'] is True


def test_http_config_remapper_timeout_defaults(check):
    # Kills the core/NumberReplacer mutants at apache.py:52-53 (receive_timeout default 15,
    # connect_timeout default 5).
    check = check({'apache_status_url': 'http://myhost/server-status'})
    assert check.http.options['timeout'] == (5.0, 15.0)


def test_check_default_tags_include_host_and_apache_host(aggregator, check, monkeypatch):
    # Kills the core/ReplaceFalseWithTrue mutant at apache.py:68 (disable_generic_tags default False -> True)
    # and the core/ReplaceBinaryOperator mutants at apache.py:76-78 (%s host/apache_host/port tag formatting).
    monkeypatch.setenv('DDEV_SKIP_GENERIC_TAGS_CHECK', 'true')
    instance = {'apache_status_url': 'http://myhost:1234/server-status', 'tags': ['instance:test']}
    check = check(instance)
    with mock.patch('datadog_checks.base.utils.http.requests.Session') as session:
        session.return_value.get.return_value = mock_response(['IdleWorkers: 3'])
        check.check(instance)

    sc_tags = ['host:myhost', 'apache_host:myhost', 'port:1234', 'instance:test']
    aggregator.assert_service_check('apache.can_connect', Apache.OK, tags=sc_tags)


def test_check_disable_generic_tags_true_uses_apache_host_and_default_port(aggregator, check):
    # Kills the core/NumberReplacer mutant at apache.py:73 (apache_port fallback 80) and the
    # core/ReplaceBinaryOperator mutants at apache.py:81 (%s apache_host/port tag formatting for
    # disable_generic_tags=True).
    instance = {
        'apache_status_url': 'http://myhost/server-status',
        'tags': ['instance:x'],
        'disable_generic_tags': True,
    }
    check = check(instance)
    with mock.patch('datadog_checks.base.utils.http.requests.Session') as session:
        session.return_value.get.return_value = mock_response(['IdleWorkers: 1'])
        check.check(instance)

    sc_tags = ['apache_host:myhost', 'port:80', 'instance:x']
    aggregator.assert_service_check('apache.can_connect', Apache.OK, tags=sc_tags)


def test_log_debug_uses_correct_timeout_tuple_indices(check):
    # Kills the core/NumberReplacer mutants at apache.py:85-86 (swapped indices into
    # self.http.options['timeout']).
    instance = {'apache_status_url': 'http://myhost/server-status', 'disable_generic_tags': True}
    check = check(instance)
    check.log = mock.MagicMock()
    with mock.patch('datadog_checks.base.utils.http.requests.Session') as session:
        session.return_value.get.return_value = mock_response(['IdleWorkers: 1'])
        check.check(instance)

    check.log.debug.assert_any_call('apache check initiating request, connect timeout %d receive %d', 5.0, 15.0)


def test_connection_exception_submits_critical_service_check(aggregator, check):
    # Kills the core/ExceptionReplacer mutant at apache.py:92 (except Exception -> a nonexistent exception type).
    instance = {'apache_status_url': 'http://myhost/server-status', 'disable_generic_tags': True}
    check = check(instance)
    with mock.patch('datadog_checks.base.utils.http.requests.Session') as session:
        session.return_value.get.side_effect = Exception('boom')
        with pytest.raises(Exception):
            check.check(instance)

    aggregator.assert_service_check('apache.can_connect', Apache.CRITICAL, tags=['apache_host:myhost', 'port:80'])


def test_check_reads_response_lines_as_unicode(check):
    # Kills the core/ReplaceTrueWithFalse mutant at apache.py:106 (iter_lines(decode_unicode=True)).
    instance = {'apache_status_url': 'http://myhost/server-status', 'disable_generic_tags': True}
    check = check(instance)
    response = mock_response(['IdleWorkers: 1'])
    with mock.patch('datadog_checks.base.utils.http.requests.Session') as session:
        session.return_value.get.return_value = response
        check.check(instance)

    response.iter_lines.assert_called_once_with(chunk_size=16384, decode_unicode=True, delimiter=None)


def test_malformed_metric_lines_are_skipped_without_crashing(aggregator, check):
    # Kills the core/ReplaceComparisonOperator mutants at apache.py:108 (len(values) == 2), the
    # core/ExceptionReplacer mutant at apache.py:123 (except ValueError), and the
    # core/ReplaceContinueWithBreak mutant at apache.py:124 (continue -> break after a bad value).
    instance = {'apache_status_url': 'http://myhost/server-status', 'tags': [], 'disable_generic_tags': True}
    check = check(instance)
    with mock.patch('datadog_checks.base.utils.http.requests.Session') as session:
        session.return_value.get.return_value = mock_response(
            ['NoColonAtAll', 'A: B: C', 'BadMetric: notanumber', 'IdleWorkers: 4']
        )
        check.check(instance)

    aggregator.assert_metric('apache.performance.idle_workers', tags=[], value=4)


def test_scoreboard_metric_does_not_stop_the_metric_loop(aggregator, check):
    # Kills the core/ReplaceComparisonOperator_Eq_Is mutant at apache.py:112 (metric == 'Scoreboard') and the
    # core/ReplaceContinueWithBreak mutant at apache.py:114: a `break` there would drop every metric line
    # that follows the Scoreboard line instead of just skipping the Scoreboard line itself.
    instance = {'apache_status_url': 'http://myhost/server-status', 'tags': [], 'disable_generic_tags': True}
    check = check(instance)
    with mock.patch('datadog_checks.base.utils.http.requests.Session') as session:
        session.return_value.get.return_value = mock_response(['Scoreboard: ..._W', 'IdleWorkers: 7'])
        check.check(instance)

    aggregator.assert_metric('apache.performance.idle_workers', tags=[], value=7)
    aggregator.assert_metric('apache.scoreboard.sending_reply', tags=[], value=1)


def test_server_version_line_takes_precedence_over_header(aggregator, check):
    # Kills the core/ReplaceComparisonOperator_Eq_Is mutant at apache.py:117 (metric == 'ServerVersion'), the
    # core/ReplaceTrueWithFalse mutant at apache.py:119 (version_submitted = True), and the
    # core/ReplaceContinueWithBreak mutant at apache.py:120 (continue -> break).
    instance = {'apache_status_url': 'http://myhost/server-status', 'tags': [], 'disable_generic_tags': True}
    check = check(instance)
    check._submit_metadata = mock.MagicMock()
    with mock.patch('datadog_checks.base.utils.http.requests.Session') as session:
        session.return_value.get.return_value = mock_response(
            ['ServerVersion: Apache/2.4.7', 'IdleWorkers: 9'], headers={'Server': 'Apache/9.9.9'}
        )
        check.check(instance)

    check._submit_metadata.assert_called_once_with('Apache/2.4.7')
    aggregator.assert_metric('apache.performance.idle_workers', tags=[], value=9)


def test_missing_server_version_line_falls_back_to_header(check):
    # Kills the core/ReplaceFalseWithTrue mutant at apache.py:104 (version_submitted init) and the
    # core/ReplaceUnaryOperator (Delete_Not) / core/AddNot mutants at apache.py:154 (if not version_submitted).
    instance = {'apache_status_url': 'http://myhost/server-status', 'tags': [], 'disable_generic_tags': True}
    check = check(instance)
    check._submit_metadata = mock.MagicMock()
    with mock.patch('datadog_checks.base.utils.http.requests.Session') as session:
        session.return_value.get.return_value = mock_response(['IdleWorkers: 5'], headers={'Server': 'Apache/2.2.3'})
        check.check(instance)

    check._submit_metadata.assert_called_once_with('Apache/2.2.3')


def test_total_kbytes_converted_to_bytes_other_metrics_untouched(aggregator, check):
    # Kills the core/ReplaceComparisonOperator (Eq_Lt/Eq_Is/Eq_IsNot/Eq_GtE) and core/AddNot mutants at
    # apache.py:127 on `metric == 'Total kBytes'`, plus the core/ReplaceBinaryOperator and core/NumberReplacer
    # mutants at apache.py:128 (value * 1024 -> value - 1024 / value * 1023).
    instance = {'apache_status_url': 'http://myhost/server-status', 'tags': [], 'disable_generic_tags': True}
    check = check(instance)
    with mock.patch('datadog_checks.base.utils.http.requests.Session') as session:
        session.return_value.get.return_value = mock_response(['Total kBytes: 2', 'Total Accesses: 5', 'Uptime: 3'])
        check.check(instance)

    aggregator.assert_metric('apache.net.bytes', tags=[], value=2048)
    aggregator.assert_metric('apache.net.bytes_per_s', tags=[], value=2048)
    aggregator.assert_metric('apache.net.request_per_s', tags=[], value=5)
    aggregator.assert_metric('apache.performance.uptime', tags=[], value=3)


def test_no_metrics_retries_with_auto_suffix(aggregator, check):
    # Kills the core/ReplaceComparisonOperator, core/ReplaceUnaryOperator, core/AddNot,
    # core/ReplaceAndWithOr and core/NumberReplacer mutant cluster at apache.py:143-144 (the
    # `url[-5:] != '?auto'` retry guard and the `'%s?auto' % url` suffix formatting).
    instance = {'apache_status_url': 'http://myhost/server-status', 'tags': [], 'disable_generic_tags': True}
    check = check(instance)
    with mock.patch('datadog_checks.base.utils.http.requests.Session') as session:
        session.return_value.get.side_effect = [
            mock_response(['NothingUseful: true']),
            mock_response(['IdleWorkers: 2']),
        ]
        check.check(instance)

    assert check.assumed_url[instance['apache_status_url']] == 'http://myhost/server-status?auto'
    aggregator.assert_metric('apache.performance.idle_workers', tags=[], value=2)


def test_no_metrics_with_auto_url_raises_check_exception(check):
    # Kills the core/NumberReplacer mutant at apache.py:103 (metric_count init) and the
    # core/ReplaceBinaryOperator mutant cluster at apache.py:151 (the CheckException message formatting).
    instance = {'apache_status_url': 'http://myhost/server-status?auto', 'disable_generic_tags': True}
    check = check(instance)
    with mock.patch('datadog_checks.base.utils.http.requests.Session') as session:
        session.return_value.get.return_value = mock_response(['NothingUseful: true'])
        with pytest.raises(Exception) as excinfo:
            check.check(instance)

    assert str(excinfo.value) == (
        "No metrics were fetched for this instance. Make sure that http://myhost/server-status?auto is the proper url."
    )


def test_submit_scoreboard_emits_metric_per_key(aggregator, check):
    # Kills the core/ZeroIterationForLoop mutant at apache.py:180 (SCOREBOARD_KEYS.items() -> []).
    check = check({})
    check._submit_scoreboard('..._W', [])

    aggregator.assert_metric('apache.scoreboard.waiting_for_connection', tags=[], value=1)
    aggregator.assert_metric('apache.scoreboard.sending_reply', tags=[], value=1)
    aggregator.assert_metric('apache.scoreboard.open_slot', tags=[], value=3)


def test_submit_metadata_logs_when_version_unparseable(check):
    # Kills the core/ReplaceUnaryOperator (Delete_Not), core/AddNot and core/ReplaceOrWithAnd mutants at
    # apache.py:168 (`if not match or not match.groups():`) for a value that fails to match entirely.
    check = check({})
    check.log = mock.MagicMock()

    check._submit_metadata('garbage-value-no-match')

    check.log.info.assert_called_once_with(
        "Cannot parse the complete Apache version from %s.", "garbage-value-no-match"
    )


def test_submit_metadata_parses_version_from_capture_group(check, datadog_agent):
    # Kills the core/NumberReplacer mutant at apache.py:172 (match.group(1) -> match.group(2)/match.group(0)).
    check = check({})
    check.check_id = 'test:123'

    check._submit_metadata('Apache/2.4.6 (Unix)')

    datadog_agent.assert_metadata(
        'test:123',
        {'version.scheme': 'semver', 'version.major': '2', 'version.minor': '4', 'version.patch': '6'},
    )
