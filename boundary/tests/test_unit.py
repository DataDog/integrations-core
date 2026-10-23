# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.base.constants import ServiceCheck

from .common import HEALTH_ENDPOINT, METRIC_ENDPOINT

pytestmark = [pytest.mark.unit]


def test_without_extra_tags(aggregator, dd_run_check, get_check, instance, fake_http, fake_http_response):
    instance = instance.copy()
    fake_http_response(HEALTH_ENDPOINT)
    fake_http_response(METRIC_ENDPOINT)
    instance.pop('tags')

    check = get_check(instance)
    dd_run_check(check)

    fake_http.assert_all_responses_consumed()
    assert [(r.method, r.url) for r in fake_http.requests] == [('GET', HEALTH_ENDPOINT), ('GET', METRIC_ENDPOINT)]
    aggregator.assert_service_check('boundary.controller.health', ServiceCheck.OK, tags=[f'endpoint:{HEALTH_ENDPOINT}'])
    aggregator.assert_service_check(
        'boundary.openmetrics.health', ServiceCheck.OK, tags=[f'endpoint:{METRIC_ENDPOINT}']
    )


def test_health_error(aggregator, dd_run_check, get_check, instance, fake_http, fake_http_response):
    fake_http_response(HEALTH_ENDPOINT, status_code=404)
    fake_http_response(METRIC_ENDPOINT, status_code=404)

    check = get_check(instance)
    with pytest.raises(Exception, match='404 Client Error'):
        dd_run_check(check)
    fake_http.assert_all_responses_consumed()
    assert [(r.method, r.url) for r in fake_http.requests] == [('GET', HEALTH_ENDPOINT), ('GET', METRIC_ENDPOINT)]

    aggregator.assert_service_check(
        'boundary.controller.health', ServiceCheck.CRITICAL, tags=[f'endpoint:{HEALTH_ENDPOINT}', *instance['tags']]
    )
    aggregator.assert_service_check(
        'boundary.openmetrics.health', ServiceCheck.CRITICAL, tags=[f'endpoint:{METRIC_ENDPOINT}', *instance['tags']]
    )


def test_health_warning(aggregator, dd_run_check, get_check, instance, fake_http, fake_http_response):
    fake_http_response(HEALTH_ENDPOINT, status_code=503)
    fake_http_response(METRIC_ENDPOINT, status_code=503)

    check = get_check(instance)
    with pytest.raises(Exception, match='503 Server Error'):
        dd_run_check(check)
    fake_http.assert_all_responses_consumed()
    assert [(r.method, r.url) for r in fake_http.requests] == [('GET', HEALTH_ENDPOINT), ('GET', METRIC_ENDPOINT)]

    aggregator.assert_service_check(
        'boundary.controller.health', ServiceCheck.WARNING, tags=[f'endpoint:{HEALTH_ENDPOINT}', *instance['tags']]
    )

    aggregator.assert_service_check(
        'boundary.openmetrics.health', ServiceCheck.CRITICAL, tags=[f'endpoint:{METRIC_ENDPOINT}', *instance['tags']]
    )
