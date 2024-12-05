# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest


@pytest.mark.e2e
@pytest.mark.usefixtures('dd_environment')
def test_generate_metrics(dd_agent_check, instance):
    """
    Test that we collect the expected metrics.
    """

    aggregator = dd_agent_check(instance, rate=True)
    aggregator.assert_metric('proxmox.cpu_current', at_least=1)
