# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

import mock
import pytest

from datadog_checks.cert_manager import CertManagerCheck
from datadog_checks.dev.http import MockResponse

from .common import ACME_METRICS, CERT_METRICS, CONTROLLER_METRICS, MOCK_INSTANCE


@pytest.fixture()
def error_metrics():
    with mock.patch(
        'requests.get',
        return_value=mock.MagicMock(status_code=502, headers={'Content-Type': "text/plain"}),
    ):
        yield


@pytest.mark.unit
def test_config():
    # this should not fail
    CertManagerCheck('cert_manager', {}, [MOCK_INSTANCE])


@pytest.mark.unit
def test_check(aggregator, dd_run_check):
    check = CertManagerCheck('cert_manager', {}, [MOCK_INSTANCE])

    def mock_requests_get(url, *args, **kwargs):
        return MockResponse(file_path=os.path.join(os.path.dirname(__file__), 'fixtures', 'cert_manager.txt'))

    with mock.patch('requests.get', side_effect=mock_requests_get, autospec=True):
        dd_run_check(check)

    expected_metrics = dict(CERT_METRICS)
    expected_metrics.update(CONTROLLER_METRICS)
    expected_metrics.update(ACME_METRICS)

    for metric_name, metric_type in expected_metrics.items():
        aggregator.assert_metric(metric_name, metric_type=metric_type)

    aggregator.assert_all_metrics_covered()

    aggregator.assert_service_check(
        'cert_manager.openmetrics.health',
        status=CertManagerCheck.OK,
        tags=['endpoint:http://fake.tld/prometheus'],
        count=1,
    )


@pytest.mark.unit
def test_openmetrics_error(aggregator, instance, error_metrics):
    check = CertManagerCheck('cert_manager', {}, [MOCK_INSTANCE])
    with pytest.raises(Exception):
        check.check(MOCK_INSTANCE)
        aggregator.assert_service_check(
            'cert_manager.openmetrics.health',
            status=CertManagerCheck.CRITICAL,
            tags=['endpoint:http://fake.tld/prometheus'],
            count=1,
        )
