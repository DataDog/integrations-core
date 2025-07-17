# (C) Datadog, Inc. 2010-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import mock
import pytest
import requests

from datadog_checks.base import AgentCheck, ConfigurationError
from datadog_checks.base.errors import CheckException
from datadog_checks.druid import DruidCheck

pytestmark = pytest.mark.unit


def test_missing_url_config(aggregator):
    check = DruidCheck('druid', {}, [{}])

    with pytest.raises(ConfigurationError):
        check.check({})


def test_service_check_can_connect_success(aggregator, instance):
    check = DruidCheck('druid', {}, [instance])

    req = mock.MagicMock()
    with mock.patch('datadog_checks.base.utils.http.requests.Session', return_value=req):
        mock_resp = mock.MagicMock(status_code=200)
        mock_resp.json.return_value = {'abc': '123'}
        req.get.return_value = mock_resp

        resp = check._get_process_properties('http://hello-world.com:8899', ['foo:bar'])
        assert resp == {'abc': '123'}

    aggregator.assert_service_check(
        'druid.service.can_connect',
        AgentCheck.OK,
        tags=['url:http://hello-world.com:8899/status/properties', 'foo:bar'],
    )


@pytest.mark.parametrize("exception_class", [requests.exceptions.ConnectionError, requests.exceptions.Timeout])
def test_service_check_can_connect_failure(aggregator, instance, exception_class):
    check = DruidCheck('druid', {}, [instance])

    req = mock.MagicMock()
    with mock.patch('datadog_checks.base.utils.http.requests.Session', return_value=req):
        attrs = {'raise_for_status.side_effect': exception_class}
        req.get.side_effect = [mock.MagicMock(status_code=500, **attrs)]

        with pytest.raises(CheckException):
            properties = check._get_process_properties('http://hello-world.com:8899', ['foo:bar'])
            assert properties is None

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
