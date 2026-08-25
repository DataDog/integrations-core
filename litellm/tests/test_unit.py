# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.base.constants import ServiceCheck

# from datadog_checks.dev.utils import get_metadata_metrics
from datadog_checks.litellm import LitellmCheck

from .common import (
    ENDPOINT_METRICS,
    METRICS,
    OM_MOCKED_INSTANCE,
    RENAMED_METRICS_V1_75,
    get_fixture_path,
)


def test_litellm_mock_metrics(dd_run_check, aggregator, mock_http_response):
    mock_http_response(file_path=get_fixture_path('metrics.txt'))
    check = LitellmCheck('litellm', {}, [OM_MOCKED_INSTANCE])
    dd_run_check(check)

    for metric in METRICS:
        aggregator.assert_metric(metric)
    aggregator.assert_all_metrics_covered()
    # aggregator.assert_metrics_using_metadata(get_metadata_metrics())
    aggregator.assert_service_check('litellm.openmetrics.health', ServiceCheck.OK)


def test_litellm_mock_invalid_endpoint(dd_run_check, aggregator, mock_http_response):
    mock_http_response(status_code=503)
    check = LitellmCheck('litellm', {}, [OM_MOCKED_INSTANCE])
    with pytest.raises(Exception):
        dd_run_check(check)

    aggregator.assert_service_check('litellm.openmetrics.health', ServiceCheck.CRITICAL)


def test_litellm_health_endpoint(aggregator, mock_http_response):
    mock_http_response(file_path=get_fixture_path('health.txt'))

    instance = OM_MOCKED_INSTANCE.copy()
    instance['litellm_health_endpoint'] = 'http://litellm:4000/health'

    check = LitellmCheck('litellm', {}, [instance])
    check.check_health_endpoint()

    for metric in ENDPOINT_METRICS:
        aggregator.assert_metric(metric)
        aggregator.assert_metric_has_tag(metric, 'health_endpoint:http://litellm:4000/health')


def test__build_tags_basic():
    check = LitellmCheck('litellm', {}, [{'foo': 'bar'}])
    endpoint = {'model': 'foo', 'custom_llm_provider': 'bar'}
    tags = check._build_tags(endpoint)
    assert 'llm_model:foo' in tags
    assert 'custom_llm_provider:bar' in tags


def test__build_tags_with_extra():
    check = LitellmCheck('litellm', {}, [{}])
    endpoint = {'model': 'foo', 'custom_llm_provider': 'bar'}
    tags = check._build_tags(endpoint, ['extra:tag'])
    assert 'llm_model:foo' in tags
    assert 'custom_llm_provider:bar' in tags
    assert 'extra:tag' in tags


def test__build_tags_with_multiple_extra():
    check = LitellmCheck('litellm', {}, [{}])
    endpoint = {'model': 'foo', 'custom_llm_provider': 'bar'}
    extra_tags = ['extra:tag', 'health_endpoint:http://localhost']
    tags = check._build_tags(endpoint, extra_tags)
    assert 'llm_model:foo' in tags
    assert 'custom_llm_provider:bar' in tags
    for t in extra_tags:
        assert t in tags


def test__extract_error_type_found():
    check = LitellmCheck('litellm', {}, [{}])
    error_msg = 'litellm.AuthenticationError: something went wrong'
    assert check._extract_error_type(error_msg) == 'AuthenticationError'


def test__extract_error_type_not_found():
    check = LitellmCheck('litellm', {}, [{}])
    error_msg = 'no litellm error here'
    assert check._extract_error_type(error_msg) == 'unknown'


def test_litellm_renamed_metrics(dd_run_check, aggregator, mock_http_response):
    # Some metrics were renamed here: https://github.com/BerriAI/litellm/pull/13271
    mock_http_response(file_path=get_fixture_path('renamed_metrics.txt'))
    check = LitellmCheck('litellm', {}, [OM_MOCKED_INSTANCE])
    dd_run_check(check)
    for metric in RENAMED_METRICS_V1_75:
        aggregator.assert_metric(metric)
    aggregator.assert_all_metrics_covered()
    aggregator.assert_service_check('litellm.openmetrics.health', ServiceCheck.OK)
