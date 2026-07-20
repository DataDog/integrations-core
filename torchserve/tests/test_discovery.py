# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.base.utils.discovery import Port, Service
from datadog_checks.torchserve.config_models.discovery import candidates

pytestmark = pytest.mark.unit


def get_service(host="1.2.3.4"):
    return Service(
        id="svc1",
        host=host,
        ports=[
            Port(number=8080, protocol="tcp"),
            Port(number=8081, protocol="tcp"),
            Port(number=8082, protocol="tcp"),
        ],
    )


def test_candidates_yields_only_openmetrics_port():
    service = get_service()

    result = list(candidates(service))

    assert len(result) == 1
    assert result[0]["instances"][0]["openmetrics_endpoint"] == "http://1.2.3.4:8082/metrics"


def test_candidates_ignores_known_non_metrics_ports():
    """Probing the Inference (8080) or Management (8081) APIs as OpenMetrics endpoints logs an error."""
    service = get_service()

    result = list(candidates(service))

    endpoints = [instance["openmetrics_endpoint"] for candidate in result for instance in candidate["instances"]]
    assert "http://1.2.3.4:8080/metrics" not in endpoints
    assert "http://1.2.3.4:8081/metrics" not in endpoints


def test_candidates_empty_without_openmetrics_port():
    service = Service(id="svc1", host="1.2.3.4", ports=[Port(number=8080, protocol="tcp")])

    assert list(candidates(service)) == []


def test_candidates_falls_back_to_custom_metrics_port():
    """OpenMetrics may be exposed on a non-default port; that candidate is a valid fallback."""
    service = Service(
        id="svc1",
        host="1.2.3.4",
        ports=[Port(number=8080, protocol="tcp"), Port(number=8081, protocol="tcp"), Port(number=9090, protocol="tcp")],
    )

    result = list(candidates(service))

    endpoints = [instance["openmetrics_endpoint"] for candidate in result for instance in candidate["instances"]]
    assert endpoints == ["http://1.2.3.4:9090/metrics"]


def test_candidates_preserves_order_with_multiple_fallbacks():
    """The hinted 8082 port is preferred, but other fallback candidates are kept in order."""
    service = Service(
        id="svc1",
        host="1.2.3.4",
        ports=[
            Port(number=8080, protocol="tcp"),
            Port(number=9090, protocol="tcp"),
            Port(number=8082, protocol="tcp"),
            Port(number=8081, protocol="tcp"),
        ],
    )

    result = list(candidates(service))

    endpoints = [instance["openmetrics_endpoint"] for candidate in result for instance in candidate["instances"]]
    assert endpoints == ["http://1.2.3.4:8082/metrics", "http://1.2.3.4:9090/metrics"]
