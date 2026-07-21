# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest

from datadog_checks.dev.docker import assert_all_discovery_candidates_stable
from datadog_checks.squid import SquidCheck

from .common import EXPECTED_METRICS, SERVICE_CHECK


@pytest.mark.e2e
def test_check_ok(dd_agent_check, instance):
    aggregator = dd_agent_check(instance, rate=True)

    expected_tags = ["name:ok_instance", "custom_tag"]
    aggregator.assert_service_check(SERVICE_CHECK, tags=expected_tags, status=SquidCheck.OK)

    for metric in EXPECTED_METRICS:
        aggregator.assert_metric("squid.cachemgr." + metric, tags=expected_tags)
    aggregator.assert_all_metrics_covered()


@pytest.mark.e2e
def test_e2e_discovery(dd_agent_check_discovery):
    aggregator = dd_agent_check_discovery(rate=True)

    # The discovered `name` tag is synthesized as `squid-{service.host}` (the container's
    # dynamic docker IP), and Autodiscovery also injects its own container tags, so exact
    # tag matching isn't used here, unlike test_check_ok above.
    aggregator.assert_service_check(SERVICE_CHECK, status=SquidCheck.OK)

    for metric in EXPECTED_METRICS:
        aggregator.assert_metric("squid.cachemgr." + metric)
    aggregator.assert_all_metrics_covered()


@pytest.mark.e2e
def test_e2e_discovery_all_candidates(dd_agent_check):
    assert_all_discovery_candidates_stable(dd_agent_check, SquidCheck)
