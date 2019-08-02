# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest


@pytest.mark.e2e
def test_e2e(dd_agent_check):
    aggregator = dd_agent_check({})

    aggregator.assert_metric('systemd.unit.count')
    aggregator.assert_metric('systemd.unit.loaded.count')

    aggregator.assert_metric('systemd.unit.uptime')
    aggregator.assert_metric('systemd.unit.loaded')
    aggregator.assert_metric('systemd.unit.active')

    aggregator.assert_metric('systemd.socket.n_connections')
    aggregator.assert_metric('systemd.socket.n_accepted')

    aggregator.assert_all_metrics_covered()
