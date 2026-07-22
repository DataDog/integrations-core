# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.base.constants import ServiceCheck
from datadog_checks.dev.docker import CONTAINER_STABILITY_LOG_PATTERNS
from datadog_checks.dev.kubernetes import assert_all_discovery_candidates_stable_kubernetes
from datadog_checks.velero import VeleroCheck

from .common import OPTIONAL_METRICS, TEST_METRICS

BENIGN_DISCOVERY_ERROR_LOG_PATTERNS = (
    r'BackupStorageLocation is in unavailable state, skip syncing backup from it',
    r'Current BackupStorageLocations available/unavailable/unknown:',
)

# Velero can log backup-storage-location state transitions at error level while its controllers settle.
DISCOVERY_STABILITY_LOG_PATTERNS = tuple(
    r'(?m)^(?![^\n]*(?:{}))[^\n]*error'.format('|'.join(BENIGN_DISCOVERY_ERROR_LOG_PATTERNS))
    if pattern == 'error'
    else pattern
    for pattern in CONTAINER_STABILITY_LOG_PATTERNS
)


def assert_metrics(aggregator):
    for metric, _ in TEST_METRICS.items():
        if metric in OPTIONAL_METRICS:
            aggregator.assert_metric(name=metric, at_least=0)
        else:
            aggregator.assert_metric(name=metric, at_least=1)

    aggregator.assert_service_check('velero.openmetrics.health', ServiceCheck.OK)


@pytest.mark.e2e
def test_check_velero_e2e(dd_agent_check):
    assert_metrics(dd_agent_check(rate=True))


@pytest.mark.e2e
def test_e2e_discovery(dd_agent_check_discovery):
    # The Velero server and node-agent pods produce one discovered instance each.
    aggregator = dd_agent_check_discovery(check_rate=True, discovery_min_instances=2)
    assert_metrics(aggregator)


@pytest.mark.e2e
def test_e2e_discovery_all_candidates(dd_agent_check, velero_kubeconfig, velero_node_agent_name):
    targets = (
        {'pod_selector': 'name=velero'},
        {'pod_name': velero_node_agent_name},
    )
    for target in targets:
        assert_all_discovery_candidates_stable_kubernetes(
            dd_agent_check,
            VeleroCheck,
            velero_kubeconfig,
            namespace='velero',
            log_patterns=DISCOVERY_STABILITY_LOG_PATTERNS,
            **target,
        )
