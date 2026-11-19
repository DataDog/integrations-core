# (C) Datadog, Inc. 2010-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import mock
import pytest

from datadog_checks.base import AgentCheck, ConfigurationError
from datadog_checks.base.errors import CheckException
from datadog_checks.base.utils.http_exceptions import (
    HTTPClientConnectionError,
    HTTPClientConnectTimeoutError,
    HTTPClientReadTimeoutError,
)
from datadog_checks.druid import DruidCheck

pytestmark = pytest.mark.unit


def test_missing_url_config(aggregator):
    check = DruidCheck('druid', {}, [{}])

    with pytest.raises(ConfigurationError):
        check.check({})


def test_service_check_can_connect_success(aggregator, instance, fake_http_response):
    check = DruidCheck('druid', {}, [instance])
    fake_http_response('http://hello-world.com:8899/status/properties', json_data={'abc': '123'})

    resp = check._get_process_properties('http://hello-world.com:8899', ['foo:bar'])
    assert resp == {'abc': '123'}

    aggregator.assert_service_check(
        'druid.service.can_connect',
        AgentCheck.OK,
        tags=['url:http://hello-world.com:8899/status/properties', 'foo:bar'],
    )


@pytest.mark.parametrize(
    "error, expected_warning",
    [
        pytest.param(HTTPClientConnectionError('connection refused'), "Couldn't connect", id='connection error'),
        # A connect timeout must keep the connection warning it got when requests reported it as a connection error.
        pytest.param(HTTPClientConnectTimeoutError('connect timed out'), "Couldn't connect", id='connect timeout'),
        pytest.param(HTTPClientReadTimeoutError('read timed out'), 'Connection timeout', id='read timeout'),
        pytest.param(None, "Couldn't connect", id='error status'),
    ],
)
def test_service_check_can_connect_failure(
    aggregator, instance, fake_http, fake_http_response, error, expected_warning
):
    check = DruidCheck('druid', {}, [instance])
    url = 'http://hello-world.com:8899/status/properties'
    if error is None:
        fake_http_response(url, status_code=500)
    else:
        fake_http.register_response('GET', url, error)

    with pytest.raises(CheckException):
        check._get_process_properties('http://hello-world.com:8899', ['foo:bar'])

    assert len(check.warnings) == 1
    assert check.warnings[0].startswith(expected_warning)

    aggregator.assert_service_check(
        'druid.service.can_connect',
        AgentCheck.CRITICAL,
        tags=['url:http://hello-world.com:8899/status/properties', 'foo:bar'],
    )


@pytest.mark.parametrize(
    'case, health_mock_value, expected_service_check_status, expected_metric_value',
    [('health OK', True, AgentCheck.OK, 1), ('health NOK', False, AgentCheck.CRITICAL, 0)],
)
def test_submit_status_service_check(
    aggregator, instance, case, health_mock_value, expected_service_check_status, expected_metric_value
):
    check = DruidCheck('druid', {}, [instance])

    check._make_request = mock.MagicMock(return_value=health_mock_value)

    check._submit_health_status('http://hello-world.com:8899', ['foo:bar'])

    tags = ['url:http://hello-world.com:8899/status/health', 'foo:bar']
    aggregator.assert_service_check('druid.service.health', expected_service_check_status, tags=tags)

    aggregator.assert_metric('druid.service.health', value=expected_metric_value, count=1, tags=tags)
    aggregator.assert_all_metrics_covered()
