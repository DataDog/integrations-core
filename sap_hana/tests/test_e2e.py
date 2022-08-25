# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.sap_hana import SapHanaCheck

from . import metrics
from .common import CAN_CONNECT_SERVICE_CHECK, connection_flaked


@pytest.mark.e2e
def test_check(dd_agent_check, instance):
    attempts = 3
    aggregator = dd_agent_check(instance, rate=True)
    while attempts and connection_flaked(aggregator):
        aggregator = dd_agent_check(instance, rate=True)
        attempts -= 1

    aggregator.assert_service_check(CAN_CONNECT_SERVICE_CHECK, SapHanaCheck.OK)
    for metric in metrics.STANDARD:
        aggregator.assert_metric_has_tag(metric, 'server:{}'.format(instance['server']))
        aggregator.assert_metric_has_tag(metric, 'port:{}'.format(instance['port']))

    aggregator.assert_all_metrics_covered()
