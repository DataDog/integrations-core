# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from pathlib import Path

import pytest

from datadog_checks.base.constants import ServiceCheck
from datadog_checks.bentoml import BentomlCheck
from datadog_checks.dev.utils import get_metadata_metrics

from .common import ENDPOINT_METRICS, METRICS, OM_MOCKED_INSTANCE, get_fixture_path


def test_bentoml_mock_metrics(dd_run_check, aggregator, fake_http, fake_http_response):
    fake_http_response('http://bentoml:3000/metrics', Path(get_fixture_path('metrics.txt')).read_bytes())
    fake_http_response('http://bentoml:3000//livez')
    fake_http_response('http://bentoml:3000//readyz')

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
    fake_http.assert_all_responses_consumed()
    assert [(r.method, r.url) for r in fake_http.requests] == [
        ('GET', 'http://bentoml:3000/metrics'),
        ('GET', 'http://bentoml:3000//livez'),
        ('GET', 'http://bentoml:3000//readyz'),
    ]


def test_bentoml_mock_invalid_endpoint(dd_run_check, aggregator, fake_http, fake_http_response):
    fake_http_response('http://bentoml:3000/metrics', status_code=503)
    check = BentomlCheck('bentoml', {}, [OM_MOCKED_INSTANCE])
    with pytest.raises(Exception):
        dd_run_check(check)
    aggregator.assert_service_check('bentoml.openmetrics.health', ServiceCheck.CRITICAL)
    fake_http.assert_all_responses_consumed()
    assert [(r.method, r.url) for r in fake_http.requests] == [('GET', 'http://bentoml:3000/metrics')]


def test_bentoml_mock_valid_endpoint_invalid_health(dd_run_check, aggregator, fake_http, fake_http_response):
    fake_http_response('http://bentoml:3000/metrics', Path(get_fixture_path('metrics.txt')).read_bytes())
    fake_http_response('http://bentoml:3000//livez', status_code=500)
    fake_http_response('http://bentoml:3000//readyz', status_code=500)

    check = BentomlCheck('bentoml', {}, [OM_MOCKED_INSTANCE])
    dd_run_check(check)

    for metric in METRICS:
        aggregator.assert_metric(metric)
    for metric in ENDPOINT_METRICS:
        aggregator.assert_metric(metric, value=0, tags=['test:tag', 'status_code:500'])

    aggregator.assert_service_check('bentoml.openmetrics.health', ServiceCheck.OK)
    fake_http.assert_all_responses_consumed()
    assert [(r.method, r.url) for r in fake_http.requests] == [
        ('GET', 'http://bentoml:3000/metrics'),
        ('GET', 'http://bentoml:3000//livez'),
        ('GET', 'http://bentoml:3000//readyz'),
    ]
