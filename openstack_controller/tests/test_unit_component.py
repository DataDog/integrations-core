# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import mock
import openstack.exceptions
import pytest

from datadog_checks.base import AgentCheck
from datadog_checks.base.utils.http_exceptions import HTTPRequestError, HTTPStatusError
from datadog_checks.openstack_controller.components.component import Component


class DummyComponent(Component):
    ID = Component.Id.COMPUTE
    TYPES = Component.Types.COMPUTE
    SERVICE_CHECK = 'openstack.test.service_check'

    @Component.http_error(report_service_check=True)
    def report_with_service_check(self, exc, tags=None):
        raise exc

    @Component.http_error()
    def report_metric(self, exc):
        raise exc


@pytest.fixture
def component():
    return DummyComponent(mock.MagicMock())


# Expected HTTP failures are swallowed, logged at DEBUG, and surfaced as CRITICAL service checks.
CAUGHT_HTTP_EXCEPTIONS = [
    pytest.param(openstack.exceptions.HttpException(), id='sdk HttpException'),
    pytest.param(HTTPRequestError('boom'), id='agnostic HTTPRequestError'),
    pytest.param(HTTPStatusError('boom'), id='agnostic HTTPStatusError'),
]

# Generic handler fallthroughs are logged at ERROR with no service check.
FELL_THROUGH_EXCEPTIONS = [
    pytest.param(openstack.exceptions.SDKException(), id='non-http SDKException'),
    pytest.param(ValueError('boom'), id='unrelated exception'),
]


@pytest.mark.parametrize('exc', CAUGHT_HTTP_EXCEPTIONS)
def test_http_error_reports_critical_for_http_exceptions(component, exc):
    assert component.report_with_service_check(exc, tags=['tag']) is None
    component.check.service_check.assert_called_once_with(
        DummyComponent.SERVICE_CHECK, AgentCheck.CRITICAL, tags=['tag']
    )
    component.check.log.error.assert_not_called()


@pytest.mark.parametrize('exc', CAUGHT_HTTP_EXCEPTIONS)
def test_http_error_swallows_http_exceptions_without_service_check(component, exc):
    assert component.report_metric(exc) is None
    component.check.service_check.assert_not_called()
    component.check.log.error.assert_not_called()


@pytest.mark.parametrize('exc', FELL_THROUGH_EXCEPTIONS)
def test_http_error_lets_non_http_exceptions_fall_through(component, exc):
    assert component.report_with_service_check(exc, tags=['tag']) is None
    component.check.service_check.assert_not_called()
    component.check.log.error.assert_called_once()
