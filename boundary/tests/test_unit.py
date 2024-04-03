# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.base.constants import ServiceCheck

from .common import HEALTH_ENDPOINT, METRIC_ENDPOINT

pytestmark = [pytest.mark.unit]


def test_without_extra_tags(aggregator, dd_run_check, get_check, instance, mock_http_response):
    instance = instance.copy()
    mock_http_response(status_code=200)
    instance.pop('tags')

    check = get_check(instance)
    dd_run_check(check)

    aggregator.assert_service_check('boundary.controller.health', ServiceCheck.OK, tags=[f'endpoint:{HEALTH_ENDPOINT}'])
    aggregator.assert_service_check(
        'boundary.openmetrics.health', ServiceCheck.OK, tags=[f'endpoint:{METRIC_ENDPOINT}']
    )


def test_health_wrong_endpoint(aggregator, dd_run_check, get_check, instance):
    instance = instance.copy()
    health_endpoint = 'http://localhost:1234'
    instance['health_endpoint'] = health_endpoint
    instance['timeout'] = 1

    check = get_check(instance)
    dd_run_check(check)

    aggregator.assert_service_check(
        'boundary.controller.health', ServiceCheck.CRITICAL, tags=[f'endpoint:{health_endpoint}', *instance['tags']]
    )
    aggregator.assert_service_check(
        'boundary.openmetrics.health', ServiceCheck.OK, tags=[f'endpoint:{METRIC_ENDPOINT}', *instance['tags']]
    )


def test_health_error(aggregator, dd_run_check, get_check, instance, mock_http_response):
    mock_http_response(status_code=404)

    check = get_check(instance)
    with pytest.raises(Exception):
        dd_run_check(check)

    aggregator.assert_service_check(
        'boundary.controller.health', ServiceCheck.CRITICAL, tags=[f'endpoint:{HEALTH_ENDPOINT}', *instance['tags']]
    )
    aggregator.assert_service_check(
        'boundary.openmetrics.health', ServiceCheck.CRITICAL, tags=[f'endpoint:{METRIC_ENDPOINT}', *instance['tags']]
    )


def test_health_warning(aggregator, dd_run_check, get_check, instance, mock_http_response):
    mock_http_response(status_code=503)

    check = get_check(instance)
    with pytest.raises(Exception):
        dd_run_check(check)

    aggregator.assert_service_check(
        'boundary.controller.health', ServiceCheck.WARNING, tags=[f'endpoint:{HEALTH_ENDPOINT}', *instance['tags']]
    )

    aggregator.assert_service_check(
        'boundary.openmetrics.health', ServiceCheck.CRITICAL, tags=[f'endpoint:{METRIC_ENDPOINT}', *instance['tags']]
    )
