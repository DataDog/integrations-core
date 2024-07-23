# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest

pytestmark = [pytest.mark.e2e]


def test_e2e_connect_ok(dd_agent_check):
    aggregator = dd_agent_check()
    aggregator.assert_metric("kubevirt_api.can_connect", value=1)


def test_e2e_check_collects_kubevirt_api_metrics(dd_agent_check):
    aggregator = dd_agent_check()

    aggregator.assert_metric("kubevirt_api.can_connect", value=1)
    aggregator.assert_metric("kubevirt_api.process.open_fds")  # gauge
    aggregator.assert_metric("kubevirt_api.promhttp.metric_handler_requests_in_flight")  # gauge
