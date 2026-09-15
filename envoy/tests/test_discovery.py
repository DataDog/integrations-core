# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.base.utils.discovery import Port, Service
from datadog_checks.envoy import Envoy

pytestmark = [pytest.mark.unit]


def generated_instances(service: Service) -> list[dict]:
    return [config['instances'][0] for config in Envoy.generate_configs(service)]


@pytest.fixture
def service_with_admin_and_fallback_ports() -> Service:
    # Ports are ordered differently from the [8001, 9901] hint list, so a test asserting
    # generated order can't pass just because the fixture happens to match hint order.
    return Service(id='envoy', host='127.0.0.1', ports=(Port(number=8080), Port(number=9901), Port(number=8001)))


def test_openmetrics_endpoint_candidates_generated_for_all_ports(
    service_with_admin_and_fallback_ports: Service,
) -> None:
    instances = generated_instances(service_with_admin_and_fallback_ports)

    ports = [
        int(instance['openmetrics_endpoint'].rsplit(':', 1)[1].split('/')[0])
        for instance in instances
        if 'openmetrics_endpoint' in instance
    ]

    # Port hints are probed in hint order before any other exposed port, and discovery stops at the
    # first candidate that yields a metric, so hint order is behaviorally significant, not incidental.
    assert ports == [8001, 9901, 8080]


def test_openmetrics_endpoint_disables_server_info_for_all_candidates(
    service_with_admin_and_fallback_ports: Service,
) -> None:
    # Port hints never confirm admin status, so no candidate should default to collecting server info.
    instances = generated_instances(service_with_admin_and_fallback_ports)

    assert all(instance['collect_server_info'] is False for instance in instances)


def test_ipv6_host_is_bracketed_in_generated_endpoint() -> None:
    # Service.host brackets IPv6 hosts itself on interpolation (datadog_checks.base.utils.discovery).
    service = Service(id='envoy', host='fd00::1', ports=(Port(number=8080),))

    instances = generated_instances(service)

    assert len(instances) == 1
    assert instances[0]['openmetrics_endpoint'] == 'http://[fd00::1]:8080/stats/prometheus'
    assert instances[0]['collect_server_info'] is False
