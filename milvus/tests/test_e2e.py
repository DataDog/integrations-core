# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.base.constants import ServiceCheck
from datadog_checks.dev.docker import CONTAINER_STABILITY_LOG_PATTERNS, assert_all_discovery_candidates_stable
from datadog_checks.milvus import MilvusCheck

from . import common

SKIPPED_METRICS = [
    'milvus.datacoord.import_tasks',
    'milvus.datacoord.index.task',
]  # these metrics need a more complex setup to appear

# Milvus standalone logs benign "error"-keyed WARN messages while its internal coordinators
# come up asynchronously (e.g. etcd leader elections, gRPC clients retrying until ready), so the
# generic "error" pattern is dropped in favor of the more specific crash indicators.
DISCOVERY_STABILITY_LOG_PATTERNS = tuple(pattern for pattern in CONTAINER_STABILITY_LOG_PATTERNS if pattern != 'error')


def assert_standalone_metrics(aggregator):
    for metric in common.STANDALONE_TEST_METRICS:
        if metric in SKIPPED_METRICS:
            continue
        aggregator.assert_metric(name=metric)

    aggregator.assert_service_check('milvus.openmetrics.health', ServiceCheck.OK)


@pytest.mark.e2e
def test_check_milvus_e2e(dd_agent_check, instance):
    aggregator = dd_agent_check(instance, rate=True)
    assert_standalone_metrics(aggregator)


@pytest.mark.e2e
def test_e2e_discovery(dd_agent_check_discovery):
    aggregator = dd_agent_check_discovery(rate=True)
    assert_standalone_metrics(aggregator)


@pytest.mark.e2e
def test_e2e_discovery_all_candidates(dd_agent_check):
    assert_all_discovery_candidates_stable(
        dd_agent_check, MilvusCheck, compose_service='milvus', log_patterns=DISCOVERY_STABILITY_LOG_PATTERNS
    )
