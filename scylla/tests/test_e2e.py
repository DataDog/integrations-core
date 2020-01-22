# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest

from .common import INSTANCE_DEFAULT_METRICS, MANAGER_DEFAULT_METRICS


@pytest.mark.e2e
def test_check_ok(dd_agent_check):
    aggregator = dd_agent_check(rate=True)
    for metric in INSTANCE_DEFAULT_METRICS + MANAGER_DEFAULT_METRICS:
        aggregator.assert_metric(metric)


@pytest.mark.e2e
def test_service_check(aggregator, instance):
    pass
