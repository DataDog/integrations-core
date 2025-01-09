# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import unittest
from base64 import b64encode
from unittest.mock import patch, MagicMock, Mock

import requests

from datadog_checks.base import ConfigurationError
from datadog_checks.sonatype_nexus.api_client import SonatypeNexusClient


REQUEST_URL = 'requests.Session.get'
URL = 'https://example.com'


def test_call_sonatype_nexus_api_success():
    instance_check = MagicMock()
    sonatype_nexus_client = SonatypeNexusClient(instance_check)
    with patch(REQUEST_URL) as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        response = sonatype_nexus_client.call_sonatype_nexus_api(URL)
        assert response == mock_response


def test_call_sonatype_nexus_api_configuration_error():
    instance_check = MagicMock()
    sonatype_nexus_client = SonatypeNexusClient(instance_check)
    with patch(REQUEST_URL) as mock_get:
        mock_get.side_effect = ConfigurationError('Test error')
        with unittest.TestCase().assertRaises(ConfigurationError):
            sonatype_nexus_client.call_sonatype_nexus_api(URL)
        instance_check.ingest_service_check_and_event.assert_called_once()


def test_call_sonatype_nexus_api_generic_exception():
    instance_check = MagicMock()
    sonatype_nexus_client = SonatypeNexusClient(instance_check)
    with patch(REQUEST_URL) as mock_get:
        mock_get.side_effect = Exception('Test error')
        with unittest.TestCase().assertRaises(Exception):
            sonatype_nexus_client.call_sonatype_nexus_api(URL)
        instance_check.log.exception.assert_called_once()


def test_returns_session_object():
    client = SonatypeNexusClient(Mock())
    session = client.get_requests_retry_session()
    assert isinstance(session, requests.Session)


def test_session_has_correct_headers():
    client = SonatypeNexusClient(Mock())
    session = client.get_requests_retry_session()
    expected_headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
    }
    assert all(item in session.headers.items() for item in expected_headers.items())


def test_authorization_header_is_correctly_formatted():
    username = "test_username"
    password = "test_password"
    instance_check = Mock()
    instance_check._username = username
    instance_check._password = password
    client = SonatypeNexusClient(instance_check)
    session = client.get_requests_retry_session()
    expected_token = b64encode(f"{username}:{password}".encode()).decode("ascii")
    assert session.headers["Authorization"] == f"Basic {expected_token}"


def test_raises_error_if_instance_check_is_none():
    with unittest.TestCase().assertRaises(AttributeError):
        SonatypeNexusClient(None)


def test_handles_none_username_or_password():
    instance_check = Mock()

    # Test with None username
    instance_check._username = None
    instance_check._password = "test_password"
    client = SonatypeNexusClient(instance_check)
    session = client.get_requests_retry_session()
    assert "Authorization" in session.headers
    assert session.headers["Authorization"].startswith("Basic ")

    # Test with None password
    instance_check._username = "test_username"
    instance_check._password = None
    client = SonatypeNexusClient(instance_check)
    session = client.get_requests_retry_session()
    assert "Authorization" in session.headers
    assert session.headers["Authorization"].startswith("Basic ")

    # Check the actual encoded value
    expected_token = b64encode("test_username:None".encode()).decode("ascii")
    assert session.headers["Authorization"] == f"Basic {expected_token}"
