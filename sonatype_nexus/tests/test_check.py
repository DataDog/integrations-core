# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest
from datadog_checks.base.stubs import aggregator as __aggregator
from datadog_checks.dev.http import MockResponse
from datadog_checks.dev.utils import get_metadata_metrics
from datadog_checks.sonatype_nexus import constants
from datadog_checks.sonatype_nexus.check import SonatypeNexusCheck
from datadog_checks.sonatype_nexus.errors import EmptyResponseError


@pytest.fixture
def mock_http_response(mocker):
    yield lambda *args, **kwargs: mocker.patch(
        kwargs.pop("method", "requests.get"), return_value=MockResponse(*args, **kwargs)
    )


@pytest.mark.e2e
def test_successful_metrics_collection(dd_run_check, mock_http_response):
    status_metrics_response_data = {
        key: {"healthy": True} for key in constants.STATUS_METRICS_MAP.keys()
    }

    mock_http_response(
        "https://example.com/service/rest/v1/status/check",
        status_code=200,
        json_data=status_metrics_response_data.update(
            {"gauges": {"jvm.memory.heap.used": {"value": 123456789}}}
        ),
    )

    instance = {
        "username": "test_username",
        "password": "test_password",
        "min_collection_interval": 400,
        "server_url": "https://example.com",
    }
    check = SonatypeNexusCheck("sonatype_nexus", {}, [instance])
    dd_run_check(check)

    __aggregator.assert_all_metrics_covered()
    __aggregator.assert_metrics_using_metadata(get_metadata_metrics())


def test_empty_instance(dd_run_check):
    with pytest.raises(
        Exception,
        match="\nmin_collection_interval\n  Field required",
    ):
        check = SonatypeNexusCheck("sonatype_nexus", {}, [{}])
        dd_run_check(check)


def test_invalid_credentials(dd_run_check, mock_http_response):
    mock_http_response(
        "https://example.com/service/rest/v1/status/check",
        status_code=401,
        json_data={"error": "Invalid credentials"},
    )

    instance = {
        "username": "invalid_username",
        "password": "invalid_password",
        "min_collection_interval": 400,
        "server_url": "https://example.com",
    }

    with pytest.raises(Exception) as excinfo:
        check = SonatypeNexusCheck("sonatype_nexus", {}, [instance])
        dd_run_check(check)
    assert "InvalidAPICredentialsError" in str(excinfo.value)


def test_bad_request_error(dd_run_check, mock_http_response):
    mock_http_response(
        "https://example.com/service/rest/v1/status/check",
        status_code=400,
        json_data={"error": "Bad request"},
    )

    instance = {
        "username": "test_user",
        "password": "test_password",
        "min_collection_interval": 400,
        "server_url": "https://example.com",
    }

    with pytest.raises(Exception) as excinfo:
        check = SonatypeNexusCheck("sonatype_nexus", {}, [instance])
        dd_run_check(check)
    assert "BadRequestError" in str(excinfo.value)


def test_license_expired_error(dd_run_check, mock_http_response):
    mock_http_response(
        "https://example.com/service/rest/v1/status/check",
        status_code=402,
        json_data={"error": "License expired"},
    )

    instance = {
        "username": "test_user",
        "password": "test_password",
        "min_collection_interval": 400,
        "server_url": "https://example.com",
    }

    with pytest.raises(Exception) as excinfo:
        check = SonatypeNexusCheck("sonatype_nexus", {}, [instance])
        dd_run_check(check)
    assert "LicenseExpiredError" in str(excinfo.value)


def test_insufficient_permission_error(dd_run_check, mock_http_response):
    mock_http_response(
        "https://example.com/service/rest/v1/status/check",
        status_code=403,
        json_data={"error": "Insufficient permissions"},
    )

    instance = {
        "username": "test_user",
        "password": "test_password",
        "min_collection_interval": 400,
        "server_url": "https://example.com",
    }

    with pytest.raises(Exception) as excinfo:
        check = SonatypeNexusCheck("sonatype_nexus", {}, [instance])
        dd_run_check(check)
    assert "InsufficientAPIPermissionError" in str(excinfo.value)


def test_not_found_error(dd_run_check, mock_http_response):
    mock_http_response(
        "https://example.com/service/rest/v1/status/check",
        status_code=404,
        json_data={"error": "Resource not found"},
    )

    instance = {
        "username": "test_user",
        "password": "test_password",
        "min_collection_interval": 400,
        "server_url": "https://example.com",
    }

    with pytest.raises(Exception) as excinfo:
        check = SonatypeNexusCheck("sonatype_nexus", {}, [instance])
        dd_run_check(check)
    assert "NotFoundError" in str(excinfo.value)


def test_server_error(dd_run_check, mock_http_response):
    mock_http_response(
        "https://example.com/service/rest/v1/status/check",
        status_code=500,
        json_data={"error": "Internal server error"},
    )

    instance = {
        "username": "test_user",
        "password": "test_password",
        "min_collection_interval": 400,
        "server_url": "https://example.com",
    }

    with pytest.raises(Exception) as excinfo:
        check = SonatypeNexusCheck("sonatype_nexus", {}, [instance])
        dd_run_check(check)
    assert "ServerError" in str(excinfo.value)


def test_timeout_error(dd_run_check, mock_http_response):
    mock_http_response(
        "https://example.com/service/rest/v1/status/check",
        status_code=408,
        json_data={"error": "TimeoutError"},
    )

    instance = {
        "username": "test_user",
        "password": "test_password",
        "min_collection_interval": 400,
        "server_url": "https://example.com",
    }

    with pytest.raises(Exception) as excinfo:
        check = SonatypeNexusCheck("sonatype_nexus", {}, [instance])
        dd_run_check(check)

    assert "APIError" in str(excinfo.value)
    assert "TimeoutError" in str(excinfo.value)


def test_empty_response_error(dd_run_check, mocker):
    _ = mocker.patch(
        "datadog_checks.sonatype_nexus.api_client.SonatypeNexusClient.call_sonatype_nexus_api",
        side_effect=EmptyResponseError(),
    )

    instance = {
        "username": "test_user",
        "password": "test_password",
        "min_collection_interval": 400,
        "server_url": "https://example.com",
    }

    with pytest.raises(Exception) as excinfo:
        check = SonatypeNexusCheck("sonatype_nexus", {}, [instance])
        dd_run_check(check)
    assert "EmptyResponseError" in str(excinfo.value)
