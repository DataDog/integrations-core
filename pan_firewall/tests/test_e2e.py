# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.dev.utils import get_metadata_metrics

from .common import (
    E2E_FIREWALL_IPS,
    E2E_PANORAMA_IP,
    E2E_PANORAMA_NAMESPACE,
    MIB,
)

pytestmark = pytest.mark.e2e


def values_with_tags(aggregator, name, *tags):
    """`assert_metric(tags=...)` matches the exact tag set, so select the series that carry `tags` among their tags."""
    return [metric.value for metric in aggregator.metrics(name) if set(tags) <= set(metric.tags)]


# Both instances poll each fake firewall at its container address, which the fake Panorama reports for it. The
# Panorama instance has its own namespace, so the two instances stay distinguishable.
DOCKER_FIREWALLS = {
    'fw-a': {'ip': E2E_FIREWALL_IPS['fw-a'], 'cpu_user': 8.2},
    'fw-b': {'ip': E2E_FIREWALL_IPS['fw-b'], 'cpu_user': 8.1},
}
NAMESPACES = ('default', E2E_PANORAMA_NAMESPACE)


def test_docker(dd_agent_check):
    aggregator = dd_agent_check(rate=True)

    aggregator.assert_metrics_using_metadata(get_metadata_metrics())

    for firewall in DOCKER_FIREWALLS.values():
        for namespace in NAMESPACES:
            tags = (f'device_ip:{firewall["ip"]}', f'device_namespace:{namespace}')
            connected = values_with_tags(aggregator, 'pan_firewall.can_connect', *tags)
            auth = values_with_tags(aggregator, 'pan_firewall.api.authentication.status', *tags)
            cpu_user = values_with_tags(aggregator, 'pan_firewall.mgmt.cpu.user', *tags)
            memory_total = values_with_tags(aggregator, 'pan_firewall.mgmt.memory.total', *tags)
            assert connected and set(connected) == {1}, tags
            assert auth and set(auth) == {0}, tags
            assert cpu_user and set(cpu_user) == {firewall['cpu_user']}, tags
            assert memory_total and memory_total == [pytest.approx(15734.7 * MIB)] * len(memory_total), tags

    panorama = values_with_tags(aggregator, 'pan_firewall.panorama.can_connect', f'panorama_host:{E2E_PANORAMA_IP}')
    assert panorama and set(panorama) == {1}

    # One device event per firewall reaches the NDM metadata intake, in both modes.
    events = aggregator.get_event_platform_events('network-devices-metadata')
    devices = {(device['namespace'], device['ip_address']) for event in events for device in event.get('devices', [])}
    assert devices >= {
        (namespace, firewall['ip']) for firewall in DOCKER_FIREWALLS.values() for namespace in NAMESPACES
    }
