# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

import pytest

from .common import lab_hosts

pytestmark = [
    pytest.mark.e2e,
    pytest.mark.skipif(
        not os.environ.get('USE_PANOS_LAB'), reason='Lab-only: set USE_PANOS_LAB and the PANOS_* variables'
    ),
]


def test_lab(dd_agent_check):
    aggregator = dd_agent_check(rate=True)

    for host in lab_hosts():
        tags = [f'device_ip:{host}']
        aggregator.assert_metric('pan_firewall.can_connect', value=1, tags=tags, at_least=1)
        aggregator.assert_metric('pan_firewall.api.authentication.status', value=0, tags=tags, at_least=1)
