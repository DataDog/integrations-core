# (C) Datadog, Inc. 2019
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import mock
import pytest
import requests
from mock import MagicMock

from datadog_checks.base.errors import CheckException
from datadog_checks.mesos_slave import MesosSlave


@pytest.mark.parametrize('exception_class', [requests.exceptions.Timeout, Exception])
def test_get_json_ok_case(instance, aggregator, exception_class):
    check = MesosSlave('mesos_slave', {}, [instance])

    with mock.patch('datadog_checks.base.utils.http.requests') as req:
        attrs = {'json.return_value': {'foo': 'bar'}}
        req.get.return_value = mock.MagicMock(status_code=200, **attrs)

        res = check._get_json("http://hello")
        assert res == {'foo': 'bar'}

        aggregator.assert_service_check('mesos_slave.can_connect', count=1, status=check.OK)


@pytest.mark.parametrize('exception_class', [requests.exceptions.Timeout, Exception])
def test_get_json_exception(instance, aggregator, exception_class):
    check = MesosSlave('mesos_slave', {}, [instance])

    with mock.patch('datadog_checks.base.utils.http.requests') as req:
        req.get = MagicMock(side_effect=exception_class)

        with pytest.raises(CheckException):
            res = check._get_json("http://hello")

            assert res is None

        aggregator.assert_service_check('mesos_slave.can_connect', count=1, status=check.CRITICAL)


@pytest.mark.parametrize('service_check_needed, failure_expected, service_check_count, should_raise_exception', [
    (True, True, 0, False),
    (False, True, 0, False),
    (True, False, 1, True),
    (False, False, 0, True),
])
def test_get_json_service_check_needed(instance, aggregator, service_check_needed, failure_expected, service_check_count, should_raise_exception):
    check = MesosSlave('mesos_slave', {}, [instance])
    check.service_check_needed = service_check_needed

    with mock.patch('datadog_checks.base.utils.http.requests') as req:
        req.get = MagicMock(side_effect=Exception)
        res = None
        try:
            res = check._get_json("http://hello", failure_expected=failure_expected)
            exception_raise = False
        except CheckException:
            exception_raise = True

        assert res is None
        assert exception_raise is should_raise_exception

        aggregator.assert_service_check('mesos_slave.can_connect', count=service_check_count, status=check.CRITICAL)

        assert check.service_check_needed is False
