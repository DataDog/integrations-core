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
