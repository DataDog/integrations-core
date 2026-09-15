# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.base.constants import ServiceCheck
from datadog_checks.boundary import BoundaryCheck

from .common import HEALTH_ENDPOINT, METRIC_ENDPOINT

pytestmark = [pytest.mark.unit]


def test_default_metric_limit_is_zero():
    # Kills the core/NumberReplacer mutants at check.py:14 (DEFAULT_METRIC_LIMIT 0 -> 1 and 0 -> -1).
    assert BoundaryCheck.DEFAULT_METRIC_LIMIT == 0


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


def test_health_critical_for_non_503_error_status(aggregator, dd_run_check, get_check, instance, mock_http_response):
    # Kills the core/ReplaceComparisonOperator_Eq_GtE mutant at check.py:27 (status_code == 503 -> >= 503).
    mock_http_response(status_code=504)

    check = get_check(instance)
    with pytest.raises(Exception):
        dd_run_check(check)

    aggregator.assert_service_check(
        'boundary.controller.health', ServiceCheck.CRITICAL, tags=[f'endpoint:{HEALTH_ENDPOINT}', *instance['tags']]
    )


def test_health_endpoint_connection_error(aggregator, dd_run_check, get_check, instance, mocker):
    # Kills the core/ExceptionReplacer mutant at check.py:21 (except Exception -> except CosmicRayTestingException).
    mocker.patch('requests.Session.get', side_effect=Exception('connection refused'))

    check = get_check(instance)
    with pytest.raises(Exception):
        dd_run_check(check)

    aggregator.assert_service_check(
        'boundary.controller.health', ServiceCheck.CRITICAL, tags=[f'endpoint:{HEALTH_ENDPOINT}', *instance['tags']]
    )
