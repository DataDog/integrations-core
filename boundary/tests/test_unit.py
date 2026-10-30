# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.base.constants import ServiceCheck
from datadog_checks.base.utils.http_exceptions import HTTPClientConnectionError

from .common import HEALTH_ENDPOINT, METRIC_ENDPOINT

pytestmark = [pytest.mark.unit]


def test_without_extra_tags(aggregator, dd_run_check, get_check, instance, fake_http, fake_http_response):
    instance = instance.copy()
    fake_http_response(HEALTH_ENDPOINT, status_code=200)
    fake_http_response(METRIC_ENDPOINT, status_code=200)
    instance.pop('tags')

    check = get_check(instance)
    dd_run_check(check)

    aggregator.assert_service_check('boundary.controller.health', ServiceCheck.OK, tags=[f'endpoint:{HEALTH_ENDPOINT}'])
    aggregator.assert_service_check(
        'boundary.openmetrics.health', ServiceCheck.OK, tags=[f'endpoint:{METRIC_ENDPOINT}']
    )
    fake_http.assert_all_responses_consumed()


def test_health_error(aggregator, dd_run_check, get_check, instance, fake_http, fake_http_response):
    fake_http_response(HEALTH_ENDPOINT, status_code=404)
    fake_http_response(METRIC_ENDPOINT, status_code=404)

    check = get_check(instance)
    with pytest.raises(Exception):
        dd_run_check(check)

    aggregator.assert_service_check(
        'boundary.controller.health', ServiceCheck.CRITICAL, tags=[f'endpoint:{HEALTH_ENDPOINT}', *instance['tags']]
    )
    aggregator.assert_service_check(
        'boundary.openmetrics.health', ServiceCheck.CRITICAL, tags=[f'endpoint:{METRIC_ENDPOINT}', *instance['tags']]
    )
    fake_http.assert_all_responses_consumed()


def test_health_warning(aggregator, dd_run_check, get_check, instance, fake_http, fake_http_response):
    fake_http_response(HEALTH_ENDPOINT, status_code=503)
    fake_http_response(METRIC_ENDPOINT, status_code=503)

    check = get_check(instance)
    with pytest.raises(Exception):
        dd_run_check(check)

    aggregator.assert_service_check(
        'boundary.controller.health', ServiceCheck.WARNING, tags=[f'endpoint:{HEALTH_ENDPOINT}', *instance['tags']]
    )

    aggregator.assert_service_check(
        'boundary.openmetrics.health', ServiceCheck.CRITICAL, tags=[f'endpoint:{METRIC_ENDPOINT}', *instance['tags']]
    )
    fake_http.assert_all_responses_consumed()


def test_health_unreachable(aggregator, dd_run_check, get_check, instance, fake_http, fake_http_response):
    fake_http.register_response('GET', HEALTH_ENDPOINT, HTTPClientConnectionError('connection refused'))
    fake_http_response(METRIC_ENDPOINT, status_code=200)

    check = get_check(instance)
    dd_run_check(check)

    aggregator.assert_service_check(
        'boundary.controller.health',
        ServiceCheck.CRITICAL,
        tags=[f'endpoint:{HEALTH_ENDPOINT}', *instance['tags']],
        message='connection refused',
    )
    aggregator.assert_service_check(
        'boundary.openmetrics.health', ServiceCheck.OK, tags=[f'endpoint:{METRIC_ENDPOINT}', *instance['tags']]
    )
    fake_http.assert_all_responses_consumed()
