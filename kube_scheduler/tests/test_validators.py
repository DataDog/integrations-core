# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest

from datadog_checks.kube_scheduler.config_models.validators import initialize_instance


class TestValidators:
    def test_openmetrics_endpoint_only(self):
        """Test that openmetrics_endpoint gets mapped to prometheus_url when prometheus_url is not present"""
        config = {"openmetrics_endpoint": "http://localhost:10251/metrics"}

        # This should not raise an exception and should map openmetrics_endpoint to prometheus_url
        result = initialize_instance(config)
        assert result["openmetrics_endpoint"] == "http://localhost:10251/metrics"
        assert result["prometheus_url"] == "http://localhost:10251/metrics"  # Should be mapped

    def test_prometheus_url_only(self):
        """Test that prometheus_url works without openmetrics_endpoint"""
        config = {"prometheus_url": "http://localhost:10251/metrics"}

        # This should not raise an exception
        result = initialize_instance(config)
        assert result["prometheus_url"] == "http://localhost:10251/metrics"
        assert result.get("openmetrics_endpoint") is None

    def test_both_endpoints(self):
        """Test that both endpoints can be provided and prometheus_url takes precedence (no mapping occurs)"""
        config = {
            "openmetrics_endpoint": "http://openmetrics.example.com:8080/metrics",
            "prometheus_url": "http://prometheus.example.com:9090/metrics",
        }

        # This should not raise an exception and prometheus_url should not be overwritten
        # The mapping should NOT occur when both are present
        result = initialize_instance(config)
        assert result["openmetrics_endpoint"] == "http://openmetrics.example.com:8080/metrics"
        assert result["prometheus_url"] == "http://prometheus.example.com:9090/metrics"  # Should remain unchanged

    def test_no_endpoints(self):
        """Test that validation fails when neither endpoint is provided"""
        config = {}

        # This should raise a ValueError
        with pytest.raises(ValueError, match="Field `openmetrics_endpoint` or `prometheus_url` must be set"):
            initialize_instance(config)
