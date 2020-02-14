# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from typing import Any, Dict

import pytest

from datadog_checks.base.stubs.aggregator import AggregatorStub
from datadog_checks.rethinkdb import RethinkDBCheck

from .common import CLUSTER_STATISTICS_METRICS, SERVER_STATISTICS_METRICS, SERVERS, CONNECT_SERVER


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_check(aggregator):
    # type: (AggregatorStub) -> None
    instance = {}  # type: Dict[str, Any]
    check = RethinkDBCheck('rethinkdb', {}, [instance])
    check.check(instance)

    for metric in CLUSTER_STATISTICS_METRICS:
        aggregator.assert_metric(metric, tags=[])

    for metric in SERVER_STATISTICS_METRICS:
        for server in SERVERS:
            aggregator.assert_metric(metric, tags=['server:{}'.format(server)])

    aggregator.assert_all_metrics_covered()

    aggregator.assert_service_check('rethinkdb.can_connect', count=1, tags=['server:{}'.format(CONNECT_SERVER)])
