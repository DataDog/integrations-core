import unittest
from unittest.mock import Mock, patch
from datadog_checks.sonatype_nexus.datadog_client import DatadogClient

def setup_datadog_client():
    client = DatadogClient('site', {'api_key': 'key', 'app_key': 'app_key'}, Mock())
    client.ingest_service_check_and_event = Mock()
    client.log = Mock()
    return client


@patch('datadog_checks.sonatype_nexus.datadog_client.AuthenticationApi')
def test_successful_api_key_validation(mock_auth_api):
    client = setup_datadog_client()
    mock_auth_api.return_value.validate.return_value = {'valid': True}
    client.validate_datadog_configurations()
    client.log.info.assert_called_once()
    assert "Connection with datadog is successful" in client.log.info.call_args[0][0]

@patch('datadog_checks.sonatype_nexus.datadog_client.AuthenticationApi')
def test_generic_exception(mock_auth_api):
    client = setup_datadog_client()
    mock_auth_api.return_value.validate.side_effect = Exception('Test exception')
    with unittest.TestCase().assertRaises(Exception):
        client.validate_datadog_configurations()
    client.log.exception.assert_called_once()
    assert "Error occurred while validating datadog API key" in client.log.exception.call_args[0][0]
