# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import base64
import unittest
from unittest.mock import MagicMock

from datadog_checks.sonatype_nexus.api_client import SonatypeNexusClient

REQUEST_URL = "requests.Session.get"
URL = "https://example.com"
ACCEPT_HEADER = "application/json"


def test_call_sonatype_nexus_api_success():
    instance_check = MagicMock()

    mock_http = MagicMock()
    instance_check.http = mock_http

    sonatype_nexus_client = SonatypeNexusClient(instance_check)

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = '{"key": "value"}'
    mock_response.json.return_value = {"key": "value"}
    mock_response.raise_for_status.return_value = None

    mock_http.get.return_value = mock_response

    URL = "https://example.com/api"
    response = sonatype_nexus_client.call_sonatype_nexus_api(URL)

    mock_http.get.assert_called_once_with(URL)

    assert response == mock_response
    assert response.status_code == 200

    instance_check.ingest_event.assert_called_once_with(
        status=0,
        tags=["tag:sonatype_nexus_authentication_validation"],
        message="Successfully called the Sonatype Nexus API.",
        title="Sonatype Nexus Authentication validations",
        source_type="sonatype_nexus.authentication_validation",
    )


def test_raises_error_if_instance_check_is_none():
    with unittest.TestCase().assertRaises(AttributeError):
        SonatypeNexusClient(None)


def test_http_client_initialization():
    instance_check = MagicMock()
    instance_check._username = "test_username"
    instance_check._password = "test_password"

    mock_http = MagicMock()
    mock_http.options = {"headers": {}}
    instance_check.http = mock_http

    client = SonatypeNexusClient(instance_check)

    assert client.http == mock_http

    assert "Authorization" in mock_http.options["headers"]

    auth_header = mock_http.options["headers"]["Authorization"]
    assert auth_header.startswith("Basic ")

    decoded = base64.b64decode(auth_header.split(" ")[1]).decode("ascii")
    assert decoded == f"{instance_check._username}:{instance_check._password}"

    assert mock_http.options["headers"]["Accept"] == ACCEPT_HEADER
    assert mock_http.options["headers"]["Content-Type"] == ACCEPT_HEADER


def test_http_client_configuration():
    instance_check = MagicMock()
    instance_check._username = "test_username"
    instance_check._password = "test_password"

    instance_check.http = MagicMock()
    instance_check.http.options = {"headers": {}}

    _ = SonatypeNexusClient(instance_check)
    token = base64.b64encode(f'{instance_check._username}:{instance_check._password}'.encode()).decode('ascii')

    expected_headers = {
        "Accept": ACCEPT_HEADER,
        "Content-Type": ACCEPT_HEADER,
        "Authorization": f"Basic {token}",
    }

    for key, value in expected_headers.items():
        assert instance_check.http.options["headers"].get(key) == value

    assert set(expected_headers.keys()).issubset(set(instance_check.http.options["headers"].keys()))

    assert len(instance_check.http.options["headers"]) == len(expected_headers)
