# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from unittest.mock import Mock

import pytest
import requests

from datadog_checks.base.constants import ServiceCheck
from datadog_checks.bentoml import BentomlCheck
from datadog_checks.dev.utils import get_metadata_metrics

from .common import (
    ENDPOINT_METRICS,
    METRICS,
    OM_MOCKED_INSTANCE,
    get_fixture_path,
)


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
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metric_has_tag('bentoml.service.request.count', 'bentoml_endpoint:/summarize')
    aggregator.assert_service_check('bentoml.openmetrics.health', ServiceCheck.OK)


def test_bentoml_mock_invalid_endpoint(dd_run_check, aggregator, mock_http_response):
    mock_http_response(status_code=503)
    check = BentomlCheck('bentoml', {}, [OM_MOCKED_INSTANCE])
    with pytest.raises(Exception):
        dd_run_check(check)

    aggregator.assert_service_check('bentoml.openmetrics.health', ServiceCheck.CRITICAL)


def test_bentoml_mock_valid_endpoint_invalid_health(dd_run_check, aggregator, mock_http_response):
    session_get_mock = mock_http_response(file_path=get_fixture_path('metrics.txt'))
    metrics_response = session_get_mock.return_value

    _err = Mock()
    _err.status_code = 500
    _http_err = requests.HTTPError("500 Internal Server Error")
    _http_err.response = _err
    _err.raise_for_status.side_effect = _http_err

    def dispatch(url, **_):
        if '/livez' in url or '/readyz' in url:
            return _err
        return metrics_response

    session_get_mock.side_effect = dispatch

    check = BentomlCheck('bentoml', {}, [OM_MOCKED_INSTANCE])
    dd_run_check(check)

    for metric in ENDPOINT_METRICS:
        aggregator.assert_metric(metric, value=0, tags=['test:tag', 'status_code:500'])

    aggregator.assert_service_check('bentoml.openmetrics.health', ServiceCheck.OK)
