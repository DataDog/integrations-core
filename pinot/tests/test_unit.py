# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.base.constants import ServiceCheck
from datadog_checks.dev.utils import get_metadata_metrics
from datadog_checks.pinot import PinotCheck

from .common import (
    BROKER_INSTANCE,
    BROKER_METRICS,
    BROKER_NAMESPACE,
    CONTROLLER_INSTANCE,
    CONTROLLER_METRICS,
    CONTROLLER_NAMESPACE,
    MINION_INSTANCE,
    MINION_METRICS,
    MINION_NAMESPACE,
    SERVER_INSTANCE,
    SERVER_METRICS,
    SERVER_NAMESPACE,
    get_fixture_path,
)

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    'instance, metrics, fixture_name, namespace',
    [
        (CONTROLLER_INSTANCE, CONTROLLER_METRICS, 'controller_metrics.txt', CONTROLLER_NAMESPACE),
        (SERVER_INSTANCE, SERVER_METRICS, 'server_metrics.txt', SERVER_NAMESPACE),
        (BROKER_INSTANCE, BROKER_METRICS, 'broker_metrics.txt', BROKER_NAMESPACE),
        (MINION_INSTANCE, MINION_METRICS, 'minion_metrics.txt', MINION_NAMESPACE),
    ],
)
def test_check_mock_pinot_openmetrics(
    dd_run_check, aggregator, fixture_name, metrics, mock_http_response, instance, namespace
):
    mock_http_response(file_path=get_fixture_path(fixture_name))
    check = PinotCheck('pinot', {}, [instance])
    dd_run_check(check)

    for metric in metrics:
        aggregator.assert_metric(metric)
        aggregator.assert_metric_has_tag(metric, 'test:test')

    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
    aggregator.assert_service_check(f'{namespace}.openmetrics.health', ServiceCheck.OK)
    assert len(aggregator.service_check_names) == 1


def test_empty_instance(dd_run_check):
    with pytest.raises(
        Exception,
        match=(
            'Must specify at least one of the following: '
            'controller_endpoint, server_endpoint, broker_endpoint, minion_endpoint.'
        ),
    ):
        check = PinotCheck('pinot', {}, [{}])
        dd_run_check(check)


def test_multiple_endpoints(dd_run_check, aggregator, mock_http_response):
    """Test that multiple endpoints can be configured in a single instance."""
    mock_http_response(file_path=get_fixture_path('controller_metrics.txt'))

    instance = {
        'controller_endpoint': 'http://localhost:8009/metrics',
        'server_endpoint': 'http://localhost:8008/metrics',
        'tags': ['test:multi'],
    }
    check = PinotCheck('pinot', {}, [instance])
    dd_run_check(check)

    # Each endpoint has its own namespace and service check
    aggregator.assert_service_check('pinot.controller.openmetrics.health', ServiceCheck.OK)
    aggregator.assert_service_check('pinot.server.openmetrics.health', ServiceCheck.OK)
    assert len(aggregator.service_check_names) == 2
