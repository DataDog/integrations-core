# (C) Datadog, Inc. 2010-2018
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
from unittest import mock

import pytest

from datadog_checks.base import AgentCheck
from datadog_checks.druid import DruidCheck

pytestmark = pytest.mark.unit


class FooException(Exception):
    pass


def test_service_check_can_connect_success(aggregator, instance):
    check = DruidCheck('druid', {}, [instance])

    with mock.patch('datadog_checks.base.utils.http.requests') as req:
        mock_resp = mock.MagicMock(status_code=200)
        mock_resp.json.return_value = {'abc': '123'}
        req.get.return_value = mock_resp

        resp = check._get_process_properties('http://hello-world.com:8899', ['foo:bar'])
        assert resp == {'abc': '123'}

    aggregator.assert_service_check(
        'druid.process.can_connect',
        AgentCheck.OK,
        tags=['url:http://hello-world.com:8899/status/properties', 'foo:bar'],
    )


def test_service_check_can_connect_failure(aggregator, instance):
    check = DruidCheck('druid', {}, [instance])

    with mock.patch('datadog_checks.base.utils.http.requests') as req:
        attrs = {'raise_for_status.side_effect': FooException()}
        req.get.side_effect = [mock.MagicMock(status_code=500, **attrs)]
        with pytest.raises(FooException):
            check._get_process_properties('http://hello-world.com:8899', ['foo:bar'])

    aggregator.assert_service_check(
        'druid.process.can_connect',
        AgentCheck.CRITICAL,
        tags=['url:http://hello-world.com:8899/status/properties', 'foo:bar'],
    )


def test_submit_status_service_check(aggregator, instance):
    check = DruidCheck('druid', {}, [instance])

    check._make_request = mock.MagicMock(return_value={"a": "b"})

    check._submit_status_service_check('http://hello-world.com:8899', ['foo:bar'])

    aggregator.assert_service_check(
        'druid.process.status', AgentCheck.CRITICAL, tags=['url:http://hello-world.com:8899/status/health', 'foo:bar']
    )
