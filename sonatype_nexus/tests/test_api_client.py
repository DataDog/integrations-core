# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import unittest
import base64
from unittest.mock import patch, MagicMock


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

def test_raises_error_if_instance_check_is_none():
    with unittest.TestCase().assertRaises(AttributeError):
        SonatypeNexusClient(None)

def test_session_creation():
    instance_check = MagicMock()
    instance_check._username = 'test_username'
    instance_check._password = 'test_password'
    client = SonatypeNexusClient(instance_check)
    with patch('requests.Session') as mock_session:
        session = client.prepare_session()
        assert isinstance(session, type(mock_session.return_value))

def test_session_headers():
    instance_check = MagicMock()
    instance_check._username = 'test_username'
    instance_check._password = 'test_password'
    client = SonatypeNexusClient(instance_check)
    with patch('requests.Session') as mock_session:
        mock_session.return_value.headers.get.side_effect = lambda key: {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": f"Basic {base64.b64encode(f'{instance_check._username}:{instance_check._password}'.encode()).decode('ascii')}"
        }.get(key)
        session = client.prepare_session()
        expected_headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": f"Basic {base64.b64encode(f'{instance_check._username}:{instance_check._password}'.encode()).decode('ascii')}"
        }
        for key, value in expected_headers.items():
            assert session.headers.get(key) == value
