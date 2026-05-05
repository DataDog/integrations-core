# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.base.constants import ServiceCheck

from .common import assert_metrics


@pytest.mark.e2e
def test_e2e_discovery(dd_agent_check):
    aggregator = dd_agent_check(
        {"init_config": {}, "instances": []},
        rate=True,
        discovery_min_instances=1,
        discovery_timeout=30,
    )
    aggregator.assert_service_check('cockroachdb.openmetrics.health', ServiceCheck.OK)


def test_metrics(dd_agent_check, instance):
    aggregator = dd_agent_check(instance, rate=True)
    assert_metrics(aggregator)
