# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.base.utils.discovery import Port, Service
from datadog_checks.envoy import Envoy


def generated_instances(service: Service) -> list[dict]:
    return [config['instances'][0] for config in Envoy.generate_configs(service)]


def test_openmetrics_endpoint_candidates_generated_for_all_ports() -> None:
    service = Service(
        id='envoy',
        host='127.0.0.1',
        ports=(Port(number=8001), Port(number=9901), Port(number=8080)),
    )

    openmetrics_ports = {
        int(instance['openmetrics_endpoint'].rsplit(':', 1)[1].split('/')[0])
        for instance in generated_instances(service)
        if 'openmetrics_endpoint' in instance
    }

    assert openmetrics_ports == {8001, 9901, 8080}


def test_openmetrics_endpoint_disables_server_info_for_all_candidates() -> None:
    # Port hints never confirm admin status, so no candidate should default to collecting server info.
    service = Service(
        id='envoy',
        host='127.0.0.1',
        ports=(Port(number=8001), Port(number=9901), Port(number=8080)),
    )

    instances_by_port = {
        int(instance['openmetrics_endpoint'].rsplit(':', 1)[1].split('/')[0]): instance
        for instance in generated_instances(service)
        if 'openmetrics_endpoint' in instance
    }

    assert instances_by_port[8080]['collect_server_info'] is False
    assert instances_by_port[8001]['collect_server_info'] is False
    assert instances_by_port[9901]['collect_server_info'] is False


def test_ipv6_host_is_bracketed_in_generated_endpoint() -> None:
    # The generated template leaves IPv6 hosts unbracketed; the override must repair it.
    service = Service(
        id='envoy',
        host='fd00::1',
        ports=(Port(number=8080),),
    )

    instances = generated_instances(service)

    assert len(instances) == 1
    assert instances[0]['openmetrics_endpoint'] == 'http://[fd00::1]:8080/stats/prometheus'
    assert instances[0]['collect_server_info'] is False
