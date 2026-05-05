# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.base.constants import ServiceCheck
from datadog_checks.dev.utils import assert_service_checks


def test_metrics(dd_agent_check, dd_environment):
    aggregator = dd_agent_check()
    aggregator.assert_metric('quarkus.process.cpu.usage')
    aggregator.assert_service_check('quarkus.openmetrics.health', ServiceCheck.OK, count=1)
    assert_service_checks(aggregator)


def test_e2e_discovery(dd_agent_check):
    aggregator = dd_agent_check(
        {"init_config": {}, "instances": []},
        rate=True,
        discovery_min_instances=1,
        discovery_timeout=30,
    )
    aggregator.assert_service_check('quarkus.openmetrics.health', ServiceCheck.OK)
