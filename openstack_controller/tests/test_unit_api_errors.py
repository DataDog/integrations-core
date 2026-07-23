# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import openstack.exceptions
import pytest

from datadog_checks.base.utils.http_exceptions import HTTPStatusError
from datadog_checks.dev.http import MockHTTPResponse
from datadog_checks.openstack_controller.api.errors import (
    OpenStackHTTPResponse,
    OpenStackSDKError,
    http_status_code,
    translate_openstack_error,
    translate_openstack_errors,
)


def test_translate_openstack_http_exception_returns_agnostic_http_status_error() -> None:
    response = MockHTTPResponse(status_code=503, url='http://openstack.example/v3/projects')
    error = openstack.exceptions.HttpException(response=response)

    translated = translate_openstack_error(error)

    assert isinstance(translated, HTTPStatusError)
    assert isinstance(translated.response, OpenStackHTTPResponse)
    assert translated.response is not response
    assert translated.response.status_code == 503
    assert translated.response.url == 'http://openstack.example/v3/projects'


def test_translate_openstack_sdk_exception_returns_local_sdk_error() -> None:
    translated = translate_openstack_error(openstack.exceptions.SDKException('boom'))

    assert isinstance(translated, OpenStackSDKError)
    assert str(translated) == 'boom'


def test_http_status_code_uses_error_response_before_fallback_response() -> None:
    error = HTTPStatusError('boom', response=MockHTTPResponse(status_code=404))
    fallback_response = MockHTTPResponse(status_code=500)

    assert http_status_code(error, response=fallback_response) == 404


def test_http_status_code_uses_fallback_response() -> None:
    error = HTTPStatusError('boom')
    fallback_response = MockHTTPResponse(status_code=401)

    assert http_status_code(error, response=fallback_response) == 401


def test_translate_openstack_errors_decorator_translates_sdk_exception() -> None:
    response = MockHTTPResponse(status_code=409)

    @translate_openstack_errors
    def raises_openstack_error() -> None:
        raise openstack.exceptions.HttpException(response=response)

    with pytest.raises(HTTPStatusError) as error:
        raises_openstack_error()

    assert http_status_code(error.value) == 409
