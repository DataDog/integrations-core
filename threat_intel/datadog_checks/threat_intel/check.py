# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json

from datadog_checks.base import AgentCheck, ConfigurationError
from datadog_checks.base.utils.time import get_current_datetime, get_timestamp

from . import constants


class ThreatIntelCheck(AgentCheck):
    __NAMESPACE__ = "threat_intel"

    def __init__(self, name, init_config, instances):
        super(ThreatIntelCheck, self).__init__(name, init_config, instances)
        self.api_key = self.instance.get("api_key")
        self.ip_addresses = self.instance.get("ip_addresses", [])
        self.max_age_in_days = self.instance.get("max_age_in_days", 90)
        self.check_initializations.append(self.validate_config)

    def validate_config(self) -> None:
        if not self.api_key:
            raise ConfigurationError("AbuseIPDB API key is required.")
        if not self.ip_addresses:
            raise ConfigurationError("At least one IP address must be configured.")

    def query_ip(self, ip_address: str) -> dict | None:
        """Query the AbuseIPDB API for threat intelligence on an IP address."""
        url = constants.ABUSEIPDB_API_URL
        headers = {"Key": self.api_key, "Accept": "application/json"}
        params = {
            "ipAddress": ip_address,
            "maxAgeInDays": str(self.max_age_in_days),
        }
        try:
            response = self.http.get(url, headers=headers, params=params)
            response.raise_for_status()
            return response.json()
        except Exception:
            self.log.error("Failed to query AbuseIPDB for IP %s", ip_address)
            raise

    def check(self, _):
        current_time = get_current_datetime()
        has_error = False
        for ip_address in self.ip_addresses:
            try:
                result = self.query_ip(ip_address)
                if result and "data" in result:
                    data = result["data"]
                    log_data = {
                        "timestamp": get_timestamp(current_time),
                        "message": json.dumps(
                            {
                                "ip_address": data.get("ipAddress"),
                                "abuse_confidence_score": data.get("abuseConfidenceScore"),
                                "country_code": data.get("countryCode"),
                                "isp": data.get("isp"),
                                "domain": data.get("domain"),
                                "total_reports": data.get("totalReports"),
                                "is_whitelisted": data.get("isWhitelisted"),
                                "last_reported_at": data.get("lastReportedAt"),
                            }
                        ),
                        "ddsource": "threat_intel",
                    }
                    self.send_log(log_data)
            except Exception:
                has_error = True

        if has_error:
            self.service_check(
                constants.SERVICE_CHECK_NAME,
                AgentCheck.CRITICAL,
                message="Failed to query one or more IP addresses.",
            )
        else:
            self.service_check(constants.SERVICE_CHECK_NAME, AgentCheck.OK)
