# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

import mock
import pytest

from datadog_checks.base.errors import CheckException
from datadog_checks.cert_manager import CertManagerCheck

from .common import ACME_METRICS, CERT_METRICS, CONTROLLER_METRICS, MOCK_INSTANCE


def get_response(filename):
    metrics_file_path = os.path.join(os.path.dirname(__file__), 'fixtures', filename)
    with open(metrics_file_path, 'r') as f:
        response = f.read()
    return response


@pytest.fixture()
def mock_metrics():
    text_data = get_response('cert_manager.txt')
    with mock.patch(
        'requests.get',
        return_value=mock.MagicMock(
            status_code=200, iter_lines=lambda **kwargs: text_data.split("\n"), headers={'Content-Type': "text/plain"}
        ),
    ):
        yield


@pytest.fixture()
def error_metrics():
    with mock.patch(
        'requests.get',
        return_value=mock.MagicMock(status_code=502, headers={'Content-Type': "text/plain"}),
    ):
        yield


@pytest.mark.unit
def test_config():
    with pytest.raises(CheckException):
        CertManagerCheck('cert_manager', {}, [{}])

    # this should not fail
    CertManagerCheck('cert_manager', {}, [MOCK_INSTANCE])


@pytest.mark.unit
def test_check(aggregator, instance, mock_metrics):
    check = CertManagerCheck('cert_manager', {}, [MOCK_INSTANCE])
    check.check(MOCK_INSTANCE)

    EXPECTED_METRICS = dict(CERT_METRICS)
    EXPECTED_METRICS.update(CONTROLLER_METRICS)
    EXPECTED_METRICS.update(ACME_METRICS)

    for metric_name, metric_type in EXPECTED_METRICS.items():
        aggregator.assert_metric(metric_name, metric_type=metric_type)

    aggregator.assert_all_metrics_covered()

    aggregator.assert_service_check(
        'cert_manager.prometheus.health',
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
            'cert_manager.prometheus.health',
            status=CertManagerCheck.CRITICAL,
            tags=['endpoint:http://fake.tld/prometheus'],
            count=1,
        )
