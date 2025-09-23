# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest


@pytest.mark.e2e
def test_esxi_metric_up(vcsim_instance, dd_agent_check, aggregator):
    dd_agent_check(vcsim_instance)
    aggregator.assert_metric('esxi.host.can_connect', 1, count=1, tags=["esxi_url:127.0.0.1:8989"])
