# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.base.utils.discovery import Port, Service
from datadog_checks.envoy import Envoy


def generated_instances(service: Service) -> list[dict]:
    return [config['instances'][0] for config in Envoy.generate_configs(service)]


def test_stats_url_candidates_restricted_to_admin_ports():
    service = Service(
        id='envoy',
        host='127.0.0.1',
        ports=(Port(number=8001), Port(number=9901), Port(number=8080)),
    )

    stats_url_ports = {
        int(instance['stats_url'].rsplit(':', 1)[1].split('/')[0])
        for instance in generated_instances(service)
        if 'stats_url' in instance
    }

    assert stats_url_ports == {8001, 9901}


def test_stats_url_candidate_not_generated_for_arbitrary_port():
    service = Service(id='envoy', host='127.0.0.1', ports=(Port(number=8080),))

    instances = generated_instances(service)

    assert not any('stats_url' in instance for instance in instances)


def test_openmetrics_endpoint_candidates_generated_for_all_ports():
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


def test_openmetrics_endpoint_disables_server_info_on_non_admin_port():
    # A fallback openmetrics_endpoint candidate on a non-admin port carries the same
    # misidentification risk /server_info probing was restricted for on stats_url: it must
    # not be left to default to collecting server info against an arbitrary upstream.
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
    assert instances_by_port[8001]['collect_server_info'] is True
    assert instances_by_port[9901]['collect_server_info'] is True
