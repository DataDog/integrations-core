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


def test_lab(dd_agent_check):
    aggregator = dd_agent_check(rate=True)

    panorama_host = lab_panorama_host()
    if panorama_host:
        # Panorama mode: the firewalls are discovered, so their IPs are not known here. Every `can_connect` series
        # (one per discovered firewall, tagged with the `device_ip` Panorama reports) must be 1, and there is one.
        aggregator.assert_metric(
            'pan_firewall.panorama.can_connect', value=1, tags=[f'panorama_host:{panorama_host}'], at_least=1
        )
        firewalls = aggregator.metrics('pan_firewall.can_connect')
        assert firewalls
        assert [(m.tags, m.value) for m in firewalls if m.value != 1] == []
        return

    for host in lab_hosts():
        tags = [f'device_ip:{host}']
        aggregator.assert_metric('pan_firewall.can_connect', value=1, tags=tags, at_least=1)
        aggregator.assert_metric('pan_firewall.api.authentication.status', value=0, tags=tags, at_least=1)
