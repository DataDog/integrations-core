# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

import pytest

from .common import lab_hosts, lab_panorama_host

pytestmark = [
    pytest.mark.e2e,
    pytest.mark.skipif(
        not os.environ.get('USE_PANOS_LAB'), reason='Lab-only: set USE_PANOS_LAB and the PANOS_* variables'
    ),
]


def values_with_tag(aggregator, name, tag):
    """`assert_metric(tags=...)` matches the exact tag set, so select the series that carry `tag` among their tags."""
    return [metric.value for metric in aggregator.metrics(name) if tag in metric.tags]


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
