# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.base.constants import ServiceCheck
from datadog_checks.dev.docker import assert_all_discovery_candidates_stable
from datadog_checks.dev.utils import assert_service_checks
from datadog_checks.falco import FalcoCheck


def test_check_falco_e2e(dd_agent_check, instance):
    aggregator = dd_agent_check(instance, rate=True)
    aggregator.assert_service_check('falco.openmetrics.health', ServiceCheck.OK, count=2)
    assert_service_checks(aggregator)


@pytest.mark.e2e
def test_e2e_discovery(dd_agent_check_discovery) -> None:
    aggregator = dd_agent_check_discovery(check_rate=True)
    aggregator.assert_service_check('falco.openmetrics.health', ServiceCheck.OK, count=2)
    assert_service_checks(aggregator)


@pytest.mark.e2e
def test_e2e_discovery_all_candidates(dd_agent_check) -> None:
    assert_all_discovery_candidates_stable(dd_agent_check, FalcoCheck)
