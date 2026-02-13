# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import json
from unittest.mock import MagicMock, patch

import pytest

from datadog_checks.base import AgentCheck, ConfigurationError
from datadog_checks.threat_intel import ThreatIntelCheck

MOCK_API_RESPONSE = {
    "data": {
        "ipAddress": "192.168.1.1",
        "isPublic": True,
        "ipVersion": 4,
        "isWhitelisted": False,
        "abuseConfidenceScore": 75,
        "countryCode": "US",
        "usageType": "Data Center/Web Hosting/Transit",
        "isp": "Example ISP",
        "domain": "example.com",
        "hostnames": [],
        "totalReports": 42,
        "numDistinctUsers": 10,
        "lastReportedAt": "2025-01-15T10:30:00+00:00",
    }
}


def _mock_response(json_data=None, status_code=200, raise_for_status=None):
    mock_resp = MagicMock()
    mock_resp.json.return_value = json_data
    mock_resp.status_code = status_code
    mock_resp.raise_for_status.return_value = raise_for_status
    return mock_resp


def test_instance_check(config, instance):
    check = ThreatIntelCheck("threat_intel", config['init_config'], [instance])
    assert isinstance(check, AgentCheck)


@pytest.mark.unit
def test_validate_config_missing_api_key(config, instance):
    instance.pop("api_key")
    check = ThreatIntelCheck("threat_intel", config['init_config'], [instance])
    with pytest.raises(ConfigurationError, match="AbuseIPDB API key is required"):
        check.api_key = None
        check.validate_config()


@pytest.mark.unit
def test_validate_config_missing_ip_addresses(config, instance):
    instance.pop("ip_addresses")
    check = ThreatIntelCheck("threat_intel", config['init_config'], [instance])
    with pytest.raises(ConfigurationError, match="At least one IP address must be configured"):
        check.ip_addresses = []
        check.validate_config()


@pytest.mark.unit
def test_validate_config_success(config, instance):
    check = ThreatIntelCheck("threat_intel", config['init_config'], [instance])
    assert check.validate_config() is None


@pytest.mark.unit
def test_query_ip_success(config, instance):
    check = ThreatIntelCheck("threat_intel", config['init_config'], [instance])
    mock_resp = _mock_response(json_data=MOCK_API_RESPONSE)

    with patch('requests.Session.get', return_value=mock_resp):
        result = check.query_ip("192.168.1.1")
        assert result == MOCK_API_RESPONSE
        assert result["data"]["abuseConfidenceScore"] == 75


@pytest.mark.unit
def test_query_ip_failure(config, instance):
    check = ThreatIntelCheck("threat_intel", config['init_config'], [instance])

    with patch('requests.Session.get', side_effect=Exception("API error")):
        with pytest.raises(Exception, match="API error"):
            check.query_ip("192.168.1.1")


@pytest.mark.unit
def test_check_successful(config, datadog_agent, instance):
    check = ThreatIntelCheck("threat_intel", config['init_config'], [instance])
    mock_resp = _mock_response(json_data=MOCK_API_RESPONSE)

    with patch('requests.Session.get', return_value=mock_resp):
        check.check(None)

    logs = datadog_agent._sent_logs[check.check_id]
    assert len(logs) == 2

    for log_entry in logs:
        message = json.loads(log_entry["message"])
        assert message["ip_address"] == "192.168.1.1"
        assert message["abuse_confidence_score"] == 75
        assert message["country_code"] == "US"
        assert message["isp"] == "Example ISP"
        assert message["domain"] == "example.com"
        assert message["total_reports"] == 42
        assert log_entry["ddsource"] == "threat_intel"


@pytest.mark.unit
def test_check_with_api_error(config, instance, aggregator):
    check = ThreatIntelCheck("threat_intel", config['init_config'], [instance])

    with patch('requests.Session.get', side_effect=Exception("API error")):
        check.check(None)

    aggregator.assert_service_check(
        "threat_intel.can_connect",
        AgentCheck.CRITICAL,
        message="Failed to query one or more IP addresses.",
    )


@pytest.mark.unit
def test_check_service_check_ok(config, instance, aggregator):
    check = ThreatIntelCheck("threat_intel", config['init_config'], [instance])
    mock_resp = _mock_response(json_data=MOCK_API_RESPONSE)

    with patch('requests.Session.get', return_value=mock_resp):
        check.check(None)

    aggregator.assert_service_check("threat_intel.can_connect", AgentCheck.OK)


@pytest.mark.unit
def test_check_partial_failure(config, instance, aggregator):
    check = ThreatIntelCheck("threat_intel", config['init_config'], [instance])
    mock_resp = _mock_response(json_data=MOCK_API_RESPONSE)

    with patch(
        'requests.Session.get',
        side_effect=[mock_resp, Exception("API error")],
    ):
        check.check(None)

    aggregator.assert_service_check(
        "threat_intel.can_connect",
        AgentCheck.CRITICAL,
        message="Failed to query one or more IP addresses.",
    )
