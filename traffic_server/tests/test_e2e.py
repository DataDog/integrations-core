# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest

from datadog_checks.traffic_server import TrafficServerCheck

from .common import EXPECTED_METRICS


@pytest.mark.e2e
def test_e2e(dd_agent_check, instance, aggregator):
    dd_agent_check(instance, rate=True)
    traffic_server_tags = instance.get('tags')

    aggregator.assert_service_check('traffic_server.can_connect', TrafficServerCheck.OK)

    for metric_name in EXPECTED_METRICS:
        aggregator.assert_metric(metric_name, at_least=1)
        for tag in traffic_server_tags:
            aggregator.assert_metric_has_tag(metric_name, tag)
