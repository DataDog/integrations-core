# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from typing import Any  # noqa: F401

import pytest

from datadog_checks.base import AgentCheck
from datadog_checks.base.stubs.aggregator import AggregatorStub  # noqa: F401
from datadog_checks.dev.jmx import JVM_E2E_METRICS_NEW
from datadog_checks.dev.utils import get_metadata_metrics

from .common import CHECK_CONFIG
from .metrics import METRICS


@pytest.mark.e2e
def test_e2e(dd_agent_check):
    # type: (Any) -> None

    aggregator = dd_agent_check(CHECK_CONFIG, rate=True)  # type: AggregatorStub

    for instance in CHECK_CONFIG['instances']:
        tags = [
            'instance:hudi-{}-{}'.format(instance['host'], instance['port']),
            'jmx_server:{}'.format(instance['host']),
        ]
        aggregator.assert_service_check('hudi.can_connect', status=AgentCheck.OK, tags=tags)

    for metric in METRICS:
        aggregator.assert_metric(metric)

    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics(), exclude=JVM_E2E_METRICS_NEW)
