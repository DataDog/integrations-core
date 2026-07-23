# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import platform

import pytest

from datadog_checks.dev.docker import CONTAINER_STABILITY_LOG_PATTERNS, assert_all_discovery_candidates_stable
from datadog_checks.scylla import ScyllaCheck

from .common import FLAKY_METRICS, INSTANCE_DEFAULT_METRICS_V2

# Probing scylla-db's internal storage RPC port (7000) with a plain HTTP GET
# makes Scylla's own RPC layer log an ERROR ("rpc - client <addr>: server
# connection dropped: connection is closed") once it rejects the unrecognized
# protocol magic.
DISCOVERY_STABILITY_LOG_PATTERNS = tuple(
    r'error(?!.*rpc - client \S+: server connection dropped: connection is closed)' if pattern == 'error' else pattern
    for pattern in CONTAINER_STABILITY_LOG_PATTERNS
)


def assert_metrics(aggregator):
    for metric in INSTANCE_DEFAULT_METRICS_V2:
        if metric in FLAKY_METRICS:
            aggregator.assert_metric(metric, at_least=0)
        else:
            aggregator.assert_metric(metric)

    aggregator.assert_all_metrics_covered()
    aggregator.assert_service_check('scylla.openmetrics.health', ScyllaCheck.OK)


@pytest.mark.skipif(platform.python_version() < "3", reason='OpenMetrics V2 is only available with Python 3')
def test_check_ok_omv2(dd_agent_check, instance):
    aggregator = dd_agent_check(instance, rate=True)
    assert_metrics(aggregator)


@pytest.mark.skipif(platform.python_version() < "3", reason='OpenMetrics V2 is only available with Python 3')
@pytest.mark.e2e
def test_e2e_discovery(dd_agent_check_discovery):
    aggregator = dd_agent_check_discovery(rate=True)
    assert_metrics(aggregator)


@pytest.mark.e2e
def test_e2e_discovery_all_candidates(dd_agent_check):
    assert_all_discovery_candidates_stable(
        dd_agent_check, ScyllaCheck, compose_service='scylla-db', log_patterns=DISCOVERY_STABILITY_LOG_PATTERNS
    )
