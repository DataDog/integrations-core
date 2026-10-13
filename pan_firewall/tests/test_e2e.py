# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

import pytest

from datadog_checks.dev.utils import get_metadata_metrics

from .common import E2E_FIREWALL_IPS, E2E_PANORAMA_IP, lab_hosts, lab_panorama_host

LAB = bool(os.environ.get('USE_PANOS_LAB'))

pytestmark = pytest.mark.e2e
lab_only = pytest.mark.skipif(not LAB, reason='Lab-only: set USE_PANOS_LAB and the PANOS_* variables')
docker_only = pytest.mark.skipif(LAB, reason='Runs against the docker fakes, not the lab')


def values_with_tag(aggregator, name, tag):
    """`assert_metric(tags=...)` matches the exact tag set, so select the series that carry `tag` among their tags."""
    return [metric.value for metric in aggregator.metrics(name) if tag in metric.tags]


@lab_only
def test_lab(dd_agent_check):
    aggregator = dd_agent_check(rate=True)

    panorama_host = lab_panorama_host()
    if panorama_host:
        # Panorama mode: the firewalls are discovered, so their IPs are not known here. Every `can_connect` series
        # (one per discovered firewall, tagged with the `device_ip` Panorama reports) must be 1, and there is one.
        panorama = values_with_tag(aggregator, 'pan_firewall.panorama.can_connect', f'panorama_host:{panorama_host}')
        assert panorama and set(panorama) == {1}
        firewalls = aggregator.metrics('pan_firewall.can_connect')
        assert firewalls
        assert [(m.tags, m.value) for m in firewalls if m.value != 1] == []
        return

    for host in lab_hosts():
        tag = f'device_ip:{host}'
        connected = values_with_tag(aggregator, 'pan_firewall.can_connect', tag)
        auth = values_with_tag(aggregator, 'pan_firewall.api.authentication.status', tag)
        assert connected and set(connected) == {1}, host
        assert auth and set(auth) == {0}, host


# The docker fakes serve each firewall twice: at its container address (the static instance) and, in Panorama mode, as
# the address Panorama reports for it. Each is a different `device_ip`, so the two instances stay distinguishable.
MIB = 1024**2
DOCKER_FIREWALLS = {
    'fw-a': {'static': E2E_FIREWALL_IPS['fw-a'], 'panorama': '10.60.0.10', 'cpu_user': 8.2},
    'fw-b': {'static': E2E_FIREWALL_IPS['fw-b'], 'panorama': '10.60.0.11', 'cpu_user': 8.1},
}


@docker_only
def test_docker(dd_agent_check):
    aggregator = dd_agent_check(rate=True)

    aggregator.assert_metrics_using_metadata(get_metadata_metrics())

    for firewall in DOCKER_FIREWALLS.values():
        for mode in ('static', 'panorama'):
            tag = f'device_ip:{firewall[mode]}'
            connected = values_with_tag(aggregator, 'pan_firewall.can_connect', tag)
            auth = values_with_tag(aggregator, 'pan_firewall.api.authentication.status', tag)
            cpu_user = values_with_tag(aggregator, 'pan_firewall.mgmt.cpu.user', tag)
            memory_total = values_with_tag(aggregator, 'pan_firewall.mgmt.memory.total', tag)
            assert connected and set(connected) == {1}, tag
            assert auth and set(auth) == {0}, tag
            assert cpu_user and set(cpu_user) == {firewall['cpu_user']}, tag
            assert memory_total and memory_total == [pytest.approx(15734.7 * MIB)] * len(memory_total), tag

    panorama = values_with_tag(aggregator, 'pan_firewall.panorama.can_connect', f'panorama_host:{E2E_PANORAMA_IP}')
    assert panorama and set(panorama) == {1}

    # One device event per firewall reaches the NDM metadata intake, in both modes.
    events = aggregator.get_event_platform_events('network-devices-metadata')
    device_ips = {device['ip_address'] for event in events for device in event.get('devices', [])}
    assert device_ips >= {firewall[mode] for firewall in DOCKER_FIREWALLS.values() for mode in ('static', 'panorama')}
