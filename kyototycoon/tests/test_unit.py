# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from copy import deepcopy

import pytest
import requests

from datadog_checks.kyototycoon import KyotoTycoonCheck

from .common import DEFAULT_INSTANCE, TAGS

pytestmark = pytest.mark.unit


def test_check_raises_when_report_url_missing():
    # Kills core/ReplaceBinaryOperator_Mod_* mutants at kyototycoon.py:50 (the %r
    # formatting of the error message becomes +,-,*,/,//,**,>>,<<,|,&,^, changing the message or raising TypeError).
    kt = KyotoTycoonCheck('kyototycoon', {}, {})
    with pytest.raises(Exception, match=r'^Invalid Kyoto Tycoon report url None$'):
        kt.check({})


def test_check_appends_instance_tag_to_tags():
    # Kills core/ReplaceBinaryOperator_Mod_* mutants at kyototycoon.py:58 (the %s
    # formatting of the instance tag becomes +,-,*,/,//,**,>>,<<,|,&,^, changing the tag or raising TypeError).
    instance = deepcopy(DEFAULT_INSTANCE)
    instance['report_url'] = 'not-a-valid-url'
    instance['name'] = 'myname'
    kt = KyotoTycoonCheck('kyototycoon', {}, {})
    with pytest.raises(Exception):
        kt.check(instance)
    assert instance['tags'] == TAGS + ['instance:myname']


def test_check_appends_instance_tag_to_service_check_tags(aggregator):
    # Kills core/ReplaceBinaryOperator_Mod_* mutants at kyototycoon.py:61 (the %s
    # formatting of the service check tag becomes +,-,*,/,//,**,>>,<<,|,&,^, changing the tag or raising TypeError).
    instance = deepcopy(DEFAULT_INSTANCE)
    instance['report_url'] = 'not-a-valid-url'
    instance['name'] = 'myname'
    kt = KyotoTycoonCheck('kyototycoon', {}, {})
    with pytest.raises(Exception):
        kt.check(instance)
    aggregator.assert_service_check(
        KyotoTycoonCheck.SERVICE_CHECK_NAME,
        status=KyotoTycoonCheck.CRITICAL,
        tags=TAGS + ['instance:myname'],
        count=1,
    )


def test_check_logs_critical_service_check_on_non_http_exception(aggregator):
    # Kills core/ExceptionReplacer at kyototycoon.py:69: disabling the generic `except
    # Exception` clause means a non-HTTPError failure (e.g. a malformed URL) never triggers the CRITICAL service check.
    instance = deepcopy(DEFAULT_INSTANCE)
    instance['report_url'] = 'not-a-valid-url'
    kt = KyotoTycoonCheck('kyototycoon', {}, {})
    with pytest.raises(requests.exceptions.MissingSchema):
        kt.check(instance)
    aggregator.assert_service_check(
        KyotoTycoonCheck.SERVICE_CHECK_NAME, status=KyotoTycoonCheck.CRITICAL, tags=TAGS, count=1
    )


def test_check_logs_critical_service_check_on_http_error(aggregator, mock_http_response):
    # Kills core/ExceptionReplacer at kyototycoon.py:66: an HTTP 5xx response must be caught,
    # re-raised as HTTPError, and still trigger the CRITICAL service check.
    mock_http_response(status_code=500)
    instance = deepcopy(DEFAULT_INSTANCE)
    kt = KyotoTycoonCheck('kyototycoon', {}, {})
    with pytest.raises(requests.exceptions.HTTPError):
        kt.check(instance)
    aggregator.assert_service_check(
        KyotoTycoonCheck.SERVICE_CHECK_NAME, status=KyotoTycoonCheck.CRITICAL, tags=TAGS, count=1
    )


def test_check_continues_past_lines_without_a_tab(aggregator, mock_http_response):
    # Kills core/ReplaceContinueWithBreak at kyototycoon.py:80: turning `continue` into
    # `break` would abandon the report on the first tab-less line instead of skipping it.
    mock_http_response(content='not-a-metric-line\nrepl_delay\t5\n')
    instance = deepcopy(DEFAULT_INSTANCE)
    kt = KyotoTycoonCheck('kyototycoon', {}, {})
    kt.check(instance)
    aggregator.assert_metric('kyototycoon.replication.delay', tags=TAGS, count=1)


def test_check_parses_metric_line_with_extra_tabs_using_maxsplit_one(aggregator, mock_http_response):
    # Kills core/NumberReplacer at kyototycoon.py:82: split('\t', 1) -> split('\t', 2)
    # would fail to unpack a line that contains more than one tab.
    mock_http_response(content='unknown_metric\tval1\tval2\nrepl_delay\t5\n')
    instance = deepcopy(DEFAULT_INSTANCE)
    kt = KyotoTycoonCheck('kyototycoon', {}, {})
    kt.check(instance)
    aggregator.assert_metric('kyototycoon.replication.delay', tags=TAGS, count=1)


def test_check_parses_db_stat_with_extra_equals_using_maxsplit_one(aggregator, mock_http_response):
    # Kills core/NumberReplacer at kyototycoon.py:98: split('=', 1) -> split('=', 2)
    # would fail to unpack a db-stat token that contains more than one '='.
    mock_http_response(content='db_0\tcount=5 unknown=1=2\n')
    instance = deepcopy(DEFAULT_INSTANCE)
    kt = KyotoTycoonCheck('kyototycoon', {}, {})
    kt.check(instance)
    aggregator.assert_metric('kyototycoon.records', tags=TAGS + ['db:0'], count=1)


def test_check_reports_rate_and_total_metrics_for_recognized_key(aggregator, mock_http_response):
    # Kills core/ReplaceBinaryOperator_Mod_* mutants at kyototycoon.py:89 and :107 (the %s
    # formatting of the RATES/TOTALS metric names becomes +,-,*,/,//,**,>>,<<,|,&,^) and
    # core/ZeroIterationForLoop at kyototycoon.py:106 (totals.items() -> [] drops every TOTALS rate metric).
    mock_http_response(content='cnt_get\t5\n')
    instance = deepcopy(DEFAULT_INSTANCE)
    kt = KyotoTycoonCheck('kyototycoon', {}, {})
    kt.check(instance)
    aggregator.assert_metric('kyototycoon.ops.get.hits_per_s', tags=TAGS, count=1)
    aggregator.assert_metric('kyototycoon.ops.get.total_per_s', tags=TAGS, count=1)
