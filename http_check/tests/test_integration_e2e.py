# -*- coding: utf-8 -*-

# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest

from datadog_checks.http_check import HTTPCheck

from .common import CONFIG, CONFIG_E2E


def test_check_coverage_integration(aggregator, http_check):
    # Run the check for all the instances in the config
    for instance in CONFIG['instances']:
        http_check.check(instance)

    assert_check_coverage(aggregator)


@pytest.mark.e2e
def test_check_coverage_e2e(dd_agent_check):
    aggregator = dd_agent_check(CONFIG_E2E)

    assert_check_coverage(aggregator)


def assert_check_coverage(aggregator):
    """
    Check coverage.
    """

    # HTTP connection error
    connection_err_tags = ['url:https://thereisnosuchlink.com', 'instance:conn_error']
    aggregator.assert_service_check(HTTPCheck.SC_STATUS, status=HTTPCheck.CRITICAL, tags=connection_err_tags, count=1)

    # Wrong HTTP response status code
    status_code_err_tags = ['url:http://httpbin.org/404', 'instance:http_error_status_code']
    aggregator.assert_service_check(HTTPCheck.SC_STATUS, status=HTTPCheck.CRITICAL, tags=status_code_err_tags, count=1)

    # HTTP response status code match
    status_code_match_tags = ['url:http://httpbin.org/404', 'instance:status_code_match', 'foo:bar']
    aggregator.assert_service_check(HTTPCheck.SC_STATUS, status=HTTPCheck.OK, tags=status_code_match_tags, count=1)

    # Content match & mismatching
    content_match_tags = ['url:https://github.com', 'instance:cnt_match']
    aggregator.assert_service_check(HTTPCheck.SC_STATUS, status=HTTPCheck.OK, tags=content_match_tags, count=1)

    content_mismatch_tags = ['url:https://github.com', 'instance:cnt_mismatch']
    aggregator.assert_service_check(HTTPCheck.SC_STATUS, status=HTTPCheck.CRITICAL, tags=content_mismatch_tags, count=1)

    unicode_content_match_tags = ['url:https://ja.wikipedia.org/', 'instance:cnt_match_unicode']
    aggregator.assert_service_check(HTTPCheck.SC_STATUS, status=HTTPCheck.OK, tags=unicode_content_match_tags, count=1)

    unicode_content_mismatch_tags = ['url:https://ja.wikipedia.org/', 'instance:cnt_mismatch_unicode']
    aggregator.assert_service_check(
        HTTPCheck.SC_STATUS, status=HTTPCheck.CRITICAL, tags=unicode_content_mismatch_tags, count=1
    )

    reverse_content_match_tags = ['url:https://github.com', 'instance:cnt_match_reverse']
    aggregator.assert_service_check(
        HTTPCheck.SC_STATUS, status=HTTPCheck.CRITICAL, tags=reverse_content_match_tags, count=1
    )

    reverse_content_mismatch_tags = ['url:https://github.com', 'instance:cnt_mismatch_reverse']
    aggregator.assert_service_check(
        HTTPCheck.SC_STATUS, status=HTTPCheck.OK, tags=reverse_content_mismatch_tags, count=1
    )

    unicode_reverse_content_match_tags = ['url:https://ja.wikipedia.org/', 'instance:cnt_match_unicode_reverse']
    aggregator.assert_service_check(
        HTTPCheck.SC_STATUS, status=HTTPCheck.CRITICAL, tags=unicode_reverse_content_match_tags, count=1
    )

    unicode_reverse_content_mismatch_tags = ['url:https://ja.wikipedia.org/', 'instance:cnt_mismatch_unicode_reverse']
    aggregator.assert_service_check(
        HTTPCheck.SC_STATUS, status=HTTPCheck.OK, tags=unicode_reverse_content_mismatch_tags, count=1
    )
