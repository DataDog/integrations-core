# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest


@pytest.mark.e2e
def test_api_down(dd_agent_check, aggregator, instance):
    with pytest.raises(Exception):
        aggregator = dd_agent_check(instance)
    aggregator.assert_metric(
        "proxmox.api.up", 0, tags=['proxmox_server:http://localhost:8006/api2/json', 'proxmox_status:down', 'testing']
    )
