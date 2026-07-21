# (C) Datadog, Inc. 2010-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

import pytest

from datadog_checks.dev.docker import CONTAINER_STABILITY_LOG_PATTERNS, assert_all_discovery_candidates_stable
from datadog_checks.zk import ZookeeperCheck

from . import common
from .conftest import get_tls
from .metrics import METRICS_36_E2E_SKIPS

# Zookeeper logs a benign ERROR-level line at startup ("Invalid configuration, only one server
# specified (ignoring)") because the test fixture's zoo.cfg defines a single `server.1` entry even
# in standalone mode. Only that specific message is excluded (rather than dropping the generic
# "error" pattern outright), so a genuinely new error-level log line from a bad candidate still
# fails the check.
DISCOVERY_STABILITY_LOG_PATTERNS = tuple(
    r'error(?!.*Invalid configuration, only one server specified)' if pattern == 'error' else pattern
    for pattern in CONTAINER_STABILITY_LOG_PATTERNS
)


@pytest.mark.e2e
def test_e2e(dd_agent_check, get_instance):
    aggregator = dd_agent_check(get_instance, rate=True)

    common.assert_stat_metrics(aggregator)
    common.assert_latency_metrics(aggregator)
    common.assert_mntr_metrics_by_version(aggregator, skip=METRICS_36_E2E_SKIPS)
    common.assert_service_checks_ok(aggregator)

    expected_mode = get_instance['expected_mode']
    mname = "zookeeper.instances.{}".format(expected_mode)
    aggregator.assert_metric(mname, value=1)
    aggregator.assert_all_metrics_covered()


@pytest.mark.e2e
def test_e2e_discovery(dd_agent_check_discovery):
    if get_tls():
        pytest.skip('discovery does not configure the TLS-only Zookeeper client port')

    aggregator = dd_agent_check_discovery(rate=True)

    # Discovery has no way to know the tags configured on a real instance (e.g. `mytag`), and a
    # discovered container also gets extra tags (docker_image, image_id, ...) that the main test
    # doesn't see, so an exact tag match isn't used here.
    common.assert_stat_metrics(aggregator, tags=["mode:standalone"], exact_tags=False)
    common.assert_latency_metrics(aggregator, tags=["mode:standalone"], exact_tags=False)
    common.assert_mntr_metrics_by_version(aggregator, skip=METRICS_36_E2E_SKIPS, check_custom_tag=False)
    # Discovery doesn't set `expected_mode`, so the `zookeeper.mode` service check is never emitted.
    common.assert_service_checks_ok(aggregator, check_mode=False)

    aggregator.assert_metric("zookeeper.instances.standalone", value=1)
    aggregator.assert_all_metrics_covered()


@pytest.mark.e2e
def test_e2e_discovery_all_candidates(dd_agent_check):
    if get_tls():
        pytest.skip('discovery does not configure the TLS-only Zookeeper client port')

    assert_all_discovery_candidates_stable(
        dd_agent_check, ZookeeperCheck, log_patterns=DISCOVERY_STABILITY_LOG_PATTERNS
    )
