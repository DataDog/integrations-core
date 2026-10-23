# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json
from pathlib import Path

import pytest

from datadog_checks.base.constants import ServiceCheck
from datadog_checks.dev.utils import get_metadata_metrics
from datadog_checks.litellm import LitellmCheck

from .common import (
    ENDPOINT_METRICS,
    METRICS,
    METRICS_V1_95,
    OM_MOCKED_INSTANCE,
    RENAMED_METRICS_V1_75,
    get_fixture_path,
)


def test_litellm_mock_metrics(dd_run_check, aggregator, fake_http, fake_http_response):
    fake_http_response(OM_MOCKED_INSTANCE['openmetrics_endpoint'], Path(get_fixture_path('metrics.txt')).read_bytes())
    check = LitellmCheck('litellm', {}, [OM_MOCKED_INSTANCE])
    dd_run_check(check)

    fake_http.assert_all_responses_consumed()
    for metric in METRICS:
        aggregator.assert_metric(metric)
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
    aggregator.assert_service_check('litellm.openmetrics.health', ServiceCheck.OK)


def test_litellm_mock_invalid_endpoint(dd_run_check, aggregator, fake_http, fake_http_response):
    fake_http_response(OM_MOCKED_INSTANCE['openmetrics_endpoint'], status_code=503)
    check = LitellmCheck('litellm', {}, [OM_MOCKED_INSTANCE])
    with pytest.raises(Exception, match='503 Server Error'):
        dd_run_check(check)
    fake_http.assert_all_responses_consumed()

    aggregator.assert_service_check('litellm.openmetrics.health', ServiceCheck.CRITICAL)


def test_litellm_health_endpoint(aggregator, fake_http, fake_http_response):
    fake_http_response(
        'http://litellm:4000/health', json_data=json.loads(Path(get_fixture_path('health.txt')).read_bytes())
    )

    instance = OM_MOCKED_INSTANCE.copy()
    instance['litellm_health_endpoint'] = 'http://litellm:4000/health'

    check = LitellmCheck('litellm', {}, [instance])
    check.check_health_endpoint()
    fake_http.assert_all_responses_consumed()

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


def test_litellm_v1_95_metrics(dd_run_check, aggregator, fake_http, fake_http_response):
    fake_http_response(
        OM_MOCKED_INSTANCE['openmetrics_endpoint'], Path(get_fixture_path('metrics_v1_95.txt')).read_bytes()
    )
    check = LitellmCheck('litellm', {}, [OM_MOCKED_INSTANCE])
    dd_run_check(check)

    fake_http.assert_all_responses_consumed()
    for metric in METRICS_V1_95:
        aggregator.assert_metric(metric)
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
    aggregator.assert_service_check('litellm.openmetrics.health', ServiceCheck.OK)


def test_litellm_renamed_metrics(dd_run_check, aggregator, fake_http, fake_http_response):
    # Some metrics were renamed here: https://github.com/BerriAI/litellm/pull/13271
    fake_http_response(
        OM_MOCKED_INSTANCE['openmetrics_endpoint'], Path(get_fixture_path('renamed_metrics.txt')).read_bytes()
    )
    check = LitellmCheck('litellm', {}, [OM_MOCKED_INSTANCE])
    dd_run_check(check)
    fake_http.assert_all_responses_consumed()
    for metric in RENAMED_METRICS_V1_75:
        aggregator.assert_metric(metric)
    aggregator.assert_all_metrics_covered()
    aggregator.assert_service_check('litellm.openmetrics.health', ServiceCheck.OK)
