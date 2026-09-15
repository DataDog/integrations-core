# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.base.constants import ServiceCheck
from datadog_checks.bentoml import BentomlCheck
from datadog_checks.dev.http import MockResponse
from datadog_checks.dev.utils import get_metadata_metrics

from .common import (
    ENDPOINT_METRICS,
    METRICS,
    OM_MOCKED_INSTANCE,
    get_fixture_path,
)

pytestmark = pytest.mark.unit


def test_bentoml_mock_metrics(dd_run_check, aggregator, mock_http_response):
    mock_http_response(file_path=get_fixture_path('metrics.txt'))

    check = BentomlCheck('bentoml', {}, [OM_MOCKED_INSTANCE])
    dd_run_check(check)

    for metric in METRICS:
        aggregator.assert_metric(metric)

    for metric in ENDPOINT_METRICS:
        aggregator.assert_metric(metric, value=1, tags=['test:tag', 'status_code:200'])

    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
    aggregator.assert_metric_has_tag('bentoml.service.request.count', 'bentoml_endpoint:/summarize')
    aggregator.assert_service_check('bentoml.openmetrics.health', ServiceCheck.OK)


def test_bentoml_mock_invalid_endpoint(dd_run_check, aggregator, mock_http_response):
    mock_http_response(status_code=503)
    check = BentomlCheck('bentoml', {}, [OM_MOCKED_INSTANCE])
    with pytest.raises(Exception):
        dd_run_check(check)

    aggregator.assert_service_check('bentoml.openmetrics.health', ServiceCheck.CRITICAL)


def test_bentoml_mock_valid_endpoint_invalid_health(dd_run_check, aggregator, mock_http_response_per_endpoint):
    mock_http_response_per_endpoint(
        {
            'http://bentoml:3000/metrics': [MockResponse(file_path=get_fixture_path('metrics.txt'))],
            'http://bentoml:3000//livez': [MockResponse(status_code=500)],
            'http://bentoml:3000//readyz': [MockResponse(status_code=500)],
        }
    )

    check = BentomlCheck('bentoml', {}, [OM_MOCKED_INSTANCE])
    dd_run_check(check)

    for metric in METRICS:
        aggregator.assert_metric(metric)

    for metric in ENDPOINT_METRICS:
        aggregator.assert_metric(metric, value=0, tags=['test:tag', 'status_code:500'])

    aggregator.assert_service_check('bentoml.openmetrics.health', ServiceCheck.OK)


def test_default_metric_limit_is_zero():
    # Kills the core/NumberReplacer mutant at check.py:12 (DEFAULT_METRIC_LIMIT 0 -> -1).
    assert BentomlCheck.DEFAULT_METRIC_LIMIT == 0


def test_extract_base_url_strips_only_the_last_path_segment():
    # Kills the core/AddNot and core/NumberReplacer mutants at check.py:23: with a nested
    # path, rsplit('/', 1) must drop exactly the last segment, not zero or two segments.
    instance = {'openmetrics_endpoint': 'http://bentoml:3000/api/metrics', 'tags': ['test:tag']}
    check = BentomlCheck('bentoml', {}, [instance])
    assert check.base_url == 'http://bentoml:3000/api'


def test_check_health_endpoint_handles_exception_without_response_attribute(aggregator, mocker):
    # Kills the core/ReplaceAndWithOr mutant at check.py:50: an exception without a
    # `.response` attribute must short-circuit instead of raising AttributeError.
    check = BentomlCheck('bentoml', {}, [OM_MOCKED_INSTANCE])
    mocker.patch('datadog_checks.base.utils.http.RequestsWrapper.get', side_effect=ValueError('boom'))

    check.check_health_endpoint()

    for metric in ENDPOINT_METRICS:
        aggregator.assert_metric(metric, value=0, tags=['test:tag'])
