# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.base.stubs import tagger
from datadog_checks.base.stubs.aggregator import AggregatorStub
from datadog_checks.dev.docker import CONTAINER_STABILITY_LOG_PATTERNS
from datadog_checks.dev.kubernetes import assert_all_discovery_candidates_stable_kubernetes
from datadog_checks.dev.utils import get_metadata_metrics
from datadog_checks.strimzi import StrimziCheck
from tests.common import (
    E2E_CLUSTER_OPERATOR_METRICS,
    FLAKY_E2E_METRICS,
    TOPIC_OPERATOR_METRICS,
    USER_OPERATOR_METRICS,
)

pytestmark = pytest.mark.e2e

# Each role is identified by its kube_container_name tag, not its image — all three
# containers share quay.io/strimzi/operator, so image/port matching alone can't tell them apart.
DISCOVERY_ROLES = (
    'strimzi-cluster-operator',
    'topic-operator',
    'user-operator',
)

# The user-operator periodically logs a benign ERROR when reconciling the test fixture's
# KafkaUser resource (ACL rules not supported by the Kafka cluster config). Exclude it
# from the stability log scan so it doesn't flag a false-positive crash.
DISCOVERY_STABILITY_LOG_PATTERNS = tuple(
    r'error(?!.*reconciliation failed)' if p == 'error' else p for p in CONTAINER_STABILITY_LOG_PATTERNS
)


def assert_strimzi_e2e_telemetry(aggregator: AggregatorStub) -> None:
    for endpoint_metrics in (
        E2E_CLUSTER_OPERATOR_METRICS,
        TOPIC_OPERATOR_METRICS,
        USER_OPERATOR_METRICS,
    ):
        for expected_metric in endpoint_metrics:
            if expected_metric in FLAKY_E2E_METRICS:
                aggregator.assert_metric(expected_metric, at_least=0)
            else:
                aggregator.assert_metric(expected_metric)

    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())

    for namespace in ("cluster_operator", "topic_operator", "user_operator"):
        aggregator.assert_service_check(
            f"strimzi.{namespace}.openmetrics.health",
            status=StrimziCheck.OK,
        )
    assert len(aggregator.service_check_names) == 3


@pytest.mark.flaky
def test_check(dd_agent_check):
    aggregator = dd_agent_check(rate=True)
    assert_strimzi_e2e_telemetry(aggregator)

    # Because rate=True, each service check is emitted twice.
    for namespace in ("cluster_operator", "topic_operator", "user_operator"):
        aggregator.assert_service_check(
            f"strimzi.{namespace}.openmetrics.health",
            status=StrimziCheck.OK,
            count=2,
        )


@pytest.mark.e2e
def test_e2e_discovery(dd_agent_check_discovery):
    aggregator = dd_agent_check_discovery(
        check_rate=True,
        discovery_min_instances=3,
        discovery_timeout=60,
    )
    assert_strimzi_e2e_telemetry(aggregator)


@pytest.mark.e2e
@pytest.mark.parametrize('role', DISCOVERY_ROLES)
def test_e2e_discovery_all_candidates(dd_agent_check, strimzi_kubeconfig, role):
    service_id = f'docker://{role}'
    tagger.set_tags({f'container_id://{role}': [f'kube_container_name:{role}']})
    try:
        assert_all_discovery_candidates_stable_kubernetes(
            dd_agent_check,
            StrimziCheck,
            strimzi_kubeconfig,
            namespace='kafka',
            pod_selector=(
                f'name={role}' if role == 'strimzi-cluster-operator' else 'app.kubernetes.io/name=entity-operator'
            ),
            service_id=service_id,
            container_name=role,
            log_patterns=DISCOVERY_STABILITY_LOG_PATTERNS,
        )
    finally:
        tagger.reset()
