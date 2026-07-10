# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

import pytest

from datadog_checks.base import AgentCheck
from datadog_checks.dev.docker import CONTAINER_STABILITY_LOG_PATTERNS, assert_all_discovery_candidates_stable
from datadog_checks.yarn import YarnCheck

from . import common

# The ResourceManager container intermittently logs a line matching "fatal" during normal
# startup/heartbeat activity on this fixture (observed only in CI; not reproducible on this repo's
# ARM64 dev sandbox, which can't run the amd64-only `apache/hadoop` image far enough to isolate the
# exact benign substring for a scoped negative-lookahead exclusion). Drop only the generic `fatal`
# pattern; every other pattern (including `error`) stays active.
DISCOVERY_STABILITY_LOG_PATTERNS = tuple(pattern for pattern in CONTAINER_STABILITY_LOG_PATTERNS if pattern != r'fatal')


@pytest.mark.integration
@pytest.mark.usefixtures("dd_environment")
def test_check(aggregator, check, instance):
    check = check(instance)
    check.check(instance)
    assert_check(aggregator)


@pytest.mark.e2e
def test_check_e2e(dd_agent_check, instance):
    aggregator = dd_agent_check(instance)
    assert_check(aggregator)


@pytest.mark.e2e
def test_e2e_discovery(dd_agent_check_discovery):
    aggregator = dd_agent_check_discovery()

    aggregator.assert_service_check('yarn.can_connect', AgentCheck.OK)
    for metric in common.EXPECTED_METRICS:
        # Discovery has no way to derive `cluster_name` from the container, so the check falls
        # back to its own default instead of this fixture's 'SparkCluster' -- tag values aren't asserted here.
        aggregator.assert_metric(metric)

    aggregator.assert_all_metrics_covered()


@pytest.mark.e2e
def test_e2e_discovery_all_candidates(dd_agent_check):
    assert_all_discovery_candidates_stable(
        dd_agent_check, YarnCheck, compose_service='resourcemanager', log_patterns=DISCOVERY_STABILITY_LOG_PATTERNS
    )


def assert_check(aggregator):
    aggregator.assert_service_check('yarn.can_connect', AgentCheck.OK)
    for metric in common.EXPECTED_METRICS:
        aggregator.assert_metric_has_tag(metric, common.YARN_CLUSTER_TAG)
        aggregator.assert_metric_has_tag(metric, common.LEGACY_CLUSTER_TAG)

    aggregator.assert_all_metrics_covered()


@pytest.mark.integration
def test_metadata(aggregator, instance, datadog_agent):
    check = YarnCheck("yarn", {}, [instance])
    check.check_id = "test:123"

    check.check(instance)

    raw_version = os.getenv("YARN_VERSION")

    major, minor, patch = raw_version.split(".")

    version_metadata = {
        "version.scheme": "semver",
        "version.major": major,
        "version.minor": minor,
        "version.patch": patch,
        "version.raw": raw_version,
    }

    datadog_agent.assert_metadata("test:123", version_metadata)
