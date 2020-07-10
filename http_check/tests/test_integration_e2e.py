# -*- coding: utf-8 -*-

# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest

from datadog_checks.dev.utils import get_metadata_metrics
from datadog_checks.http_check import HTTPCheck

from .common import CONFIG, CONFIG_E2E


def test_check_coverage_integration(aggregator, http_check):
    # Run the check for all the instances in the config
    for instance in CONFIG['instances']:
        http_check.check(instance)

    assert_check_coverage(aggregator)


@pytest.mark.e2e
def test_check_coverage_e2e(dd_agent_check, mock_http_e2e_hosts):
    aggregator = dd_agent_check(CONFIG_E2E)

    assert_check_coverage(aggregator)
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())


def assert_check_coverage(aggregator):
    """
    Check coverage.
    """

    # HTTP connection error
    connection_err_tags = ['url:https://thereisnosuchlink.com', 'instance:conn_error']
    aggregator.assert_service_check(HTTPCheck.SC_STATUS, status=HTTPCheck.CRITICAL, tags=connection_err_tags, count=1)

    # Wrong HTTP response status code
    status_code_err_tags = ['url:https://valid.mock/404', 'instance:http_error_status_code']
    aggregator.assert_service_check(HTTPCheck.SC_STATUS, status=HTTPCheck.CRITICAL, tags=status_code_err_tags, count=1)

    # HTTP response status code match
    status_code_match_tags = ['url:https://valid.mock/404', 'instance:status_code_match', 'foo:bar']
    aggregator.assert_service_check(HTTPCheck.SC_STATUS, status=HTTPCheck.OK, tags=status_code_match_tags, count=1)

    # Content match & mismatching
    content_match_tags = ['url:https://valid.mock/', 'instance:cnt_match']
    aggregator.assert_service_check(HTTPCheck.SC_STATUS, status=HTTPCheck.OK, tags=content_match_tags, count=1)

    content_mismatch_tags = ['url:https://valid.mock/', 'instance:cnt_mismatch']
    aggregator.assert_service_check(HTTPCheck.SC_STATUS, status=HTTPCheck.CRITICAL, tags=content_mismatch_tags, count=1)

    unicode_content_match_tags = ['url:https://valid.mock/unicode.html', 'instance:cnt_match_unicode']
    aggregator.assert_service_check(HTTPCheck.SC_STATUS, status=HTTPCheck.OK, tags=unicode_content_match_tags, count=1)

    unicode_content_mismatch_tags = ['url:https://valid.mock/unicode.html', 'instance:cnt_mismatch_unicode']
    aggregator.assert_service_check(
        HTTPCheck.SC_STATUS, status=HTTPCheck.CRITICAL, tags=unicode_content_mismatch_tags, count=1
    )

    reverse_content_match_tags = ['url:https://valid.mock', 'instance:cnt_match_reverse']
    aggregator.assert_service_check(
        HTTPCheck.SC_STATUS, status=HTTPCheck.CRITICAL, tags=reverse_content_match_tags, count=1
    )

    reverse_content_mismatch_tags = ['url:https://valid.mock', 'instance:cnt_mismatch_reverse']
    aggregator.assert_service_check(
        HTTPCheck.SC_STATUS, status=HTTPCheck.OK, tags=reverse_content_mismatch_tags, count=1
    )

    unicode_reverse_content_match_tags = ['url:https://valid.mock/unicode.html', 'instance:cnt_match_unicode_reverse']
    aggregator.assert_service_check(
        HTTPCheck.SC_STATUS, status=HTTPCheck.CRITICAL, tags=unicode_reverse_content_match_tags, count=1
    )

    unicode_reverse_content_mismatch_tags = [
        'url:https://valid.mock/unicode.html',
        'instance:cnt_mismatch_unicode_reverse',
    ]
    aggregator.assert_service_check(
        HTTPCheck.SC_STATUS, status=HTTPCheck.OK, tags=unicode_reverse_content_mismatch_tags, count=1
    )
