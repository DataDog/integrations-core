# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import copy

import pytest

from datadog_checks.base.constants import ServiceCheck
from datadog_checks.dev.utils import get_metadata_metrics
from datadog_checks.fly_io import FlyIoCheck

from .metrics import ALL_REST_METRICS, APP_UP_METRICS, MACHINE_COUNT_METRICS, MOCKED_PROMETHEUS_METRICS


@pytest.mark.usefixtures('mock_http_get')
def test_check(dd_run_check, aggregator, instance):

    check = FlyIoCheck('fly_io', {}, [instance])
    dd_run_check(check)

    for metric in MOCKED_PROMETHEUS_METRICS:
        aggregator.assert_metric(metric, at_least=1, hostname="708725eaa12297")
        aggregator.assert_metric(metric, at_least=1, hostname="20976671ha2292")
        aggregator.assert_metric(metric, at_least=1, hostname="119dc024cbf534")

    for metric in ALL_REST_METRICS:
        aggregator.assert_metric(metric)

    aggregator.assert_service_check('fly_io.openmetrics.health', ServiceCheck.OK, count=1)

    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())


@pytest.mark.usefixtures('mock_http_get')
def test_no_machines_endpoint(dd_run_check, aggregator, instance):
    no_rest_api = copy.deepcopy(instance)
    del no_rest_api['machines_api_endpoint']

    check = FlyIoCheck('fly_io', {}, [no_rest_api])
    dd_run_check(check)

    for metric in MOCKED_PROMETHEUS_METRICS:
        aggregator.assert_metric(metric, at_least=1, hostname="708725eaa12297")
        aggregator.assert_metric(metric, at_least=1, hostname="20976671ha2292")
        aggregator.assert_metric(metric, at_least=1, hostname="119dc024cbf534")

    for metric in ALL_REST_METRICS:
        aggregator.assert_metric(metric, count=0)

    aggregator.assert_service_check('fly_io.openmetrics.health', ServiceCheck.OK, count=1)

    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())


@pytest.mark.usefixtures('mock_http_get')
def test_rest_api_app_metrics(dd_run_check, aggregator, instance, caplog):

    check = FlyIoCheck('fly_io', {}, [instance])
    dd_run_check(check)
    for metric in APP_UP_METRICS:
        aggregator.assert_metric(metric['name'], metric['value'], count=metric['count'], tags=metric['tags'])

    for metric in MACHINE_COUNT_METRICS:
        aggregator.assert_metric(
            metric['name'], metric['value'], count=metric['count'], tags=metric['tags'], hostname=metric['hostname']
        )
